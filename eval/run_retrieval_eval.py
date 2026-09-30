#!/usr/bin/env python3
"""Retrieval evaluation.

Metrics
-------
* **Recall@k**: fraction of gold questions where at least one `gold_doc_ids`
  entry appears in the top-k retrieved ids.
* **Answer in retrieved gold document**: the gold `answer` string occurs in a
  retrieved hit whose id is one of `gold_doc_ids`. This is not an LLM citation
  score. A dry run only checks that each answer occurs in the named chunk.

Usage
-----
  # Uses real SentenceTransformer + FAISS (slow / downloads model on first run)
  python eval/run_retrieval_eval.py --k 5

  # Score against an existing on-disk index
  python eval/run_retrieval_eval.py --index-dir data/index --k 5

Do not invent accuracy numbers; print only what this run measures.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "eval" / "gold_qa.jsonl"
DEFAULT_CORPUS = [
    ROOT / "data" / "nutrition_qa.jsonl",
    ROOT / "data" / "open_textbook_chunks.jsonl",
    ROOT / "data" / "pressbooks_chapters.jsonl",
]


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def recall_at_k(retrieved_ids: Sequence[str], gold_ids: Sequence[str]) -> float:
    if not gold_ids:
        return 0.0
    retrieved: Set[str] = set(retrieved_ids)
    return 1.0 if any(g in retrieved for g in gold_ids) else 0.0


def answer_in_named_docs(corpus: Dict[str, str], gold_ids: Sequence[str], answer: str) -> bool:
    if not answer or not gold_ids:
        return False
    blob = "\n".join(corpus.get(doc_id, "") for doc_id in gold_ids)
    return answer in blob


def answer_supported(hits: Sequence[Dict[str, Any]], gold_ids: Sequence[str], answer: str) -> bool:
    """True when a retrieved hit is a gold document and contains the answer string."""
    if not answer:
        return False
    gold = set(gold_ids)
    return any(
        h.get("id") in gold and answer in str(h.get("text", ""))
        for h in hits
    )


def keyword_hit(retrieved_texts: Sequence[str], keywords: Sequence[str]) -> bool:
    """Provisional heuristic: any keyword substring in any retrieved text."""
    if not keywords:
        return False
    blob = " ".join(retrieved_texts).lower()
    return any(kw.lower() in blob for kw in keywords)


def build_retriever(index_dir: Optional[Path], corpus_paths: List[Path], model_name: str):
    # Local import so `python -c` help / dry checks stay light if deps missing
    sys.path.insert(0, str(ROOT))
    from app.retriever import Retriever

    retriever = Retriever(model_name=model_name)
    if index_dir is not None:
        index_path = index_dir / "faiss.index"
        meta_path = index_dir / "meta.jsonl"
        if index_path.is_file() and meta_path.is_file():
            retriever.load_index_from_disk(str(index_path), str(meta_path))
            return retriever
        print(f"WARN: index not found under {index_dir}; building from corpus", file=sys.stderr)

    existing = [str(p) for p in corpus_paths if p.is_file()]
    if not existing:
        raise SystemExit("No corpus JSONL files found to build an index")
    retriever.load_documents_many(existing)
    retriever.build_index()
    return retriever


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Nutrition RAQA retrieval eval scaffold")
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--index-dir", type=Path, default=ROOT / "data" / "index")
    parser.add_argument(
        "--model",
        default="all-MiniLM-L6-v2",
        help="SentenceTransformer model name (ignored if you only need --dry-run)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "eval" / "retrieval_eval.json",
        help="JSON log written by a real retrieval run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate gold answers against the corpus; do not load the embedding model",
    )
    args = parser.parse_args(argv)

    gold = load_jsonl(args.gold)
    if not gold:
        print(f"ERROR: no gold rows in {args.gold}", file=sys.stderr)
        return 1

    corpus: Dict[str, str] = {}
    for path in DEFAULT_CORPUS:
        if path.is_file():
            for row in load_jsonl(path):
                corpus[str(row["id"])] = str(row.get("text", ""))

    broken = []
    for g in gold:
        if not g.get("id") or not g.get("question"):
            broken.append(str(g.get("id")))
            continue
        if not answer_in_named_docs(corpus, list(g.get("gold_doc_ids") or []), str(g.get("answer", ""))):
            broken.append(str(g.get("id")))
    if broken:
        print(f"ERROR: gold answer missing from named chunk: {broken}", file=sys.stderr)
        return 1

    n_with_ids = sum(1 for g in gold if g.get("gold_doc_ids"))
    print(f"Loaded {len(gold)} gold questions from {args.gold} ({n_with_ids} with gold_doc_ids)")

    if args.dry_run:
        print("Dry-run OK. Every answer string is in its named chunk. No retrieval scores computed.")
        return 0

    retriever = build_retriever(args.index_dir, DEFAULT_CORPUS, args.model)

    recall_scores: List[float] = []
    support_scores: List[float] = []
    per_item: List[Dict[str, Any]] = []
    for g in gold:
        q = g["question"]
        hits = retriever.retrieve(q, k=args.k)
        ids = [h.get("id", "") for h in hits]
        gold_ids = list(g.get("gold_doc_ids") or [])
        answer = str(g.get("answer", ""))

        r = recall_at_k(ids, gold_ids) if gold_ids else 0.0
        supported = answer_supported(hits, gold_ids, answer)
        recall_scores.append(r)
        support_scores.append(1.0 if supported else 0.0)
        status = "HIT" if r >= 1.0 else "MISS"
        print(f"  [{status}] {g['id']}: recall@{args.k}={r:.0f} answer_in_hit={supported} retrieved={ids}")
        per_item.append(
            {
                "id": g["id"],
                "recall_hit": r >= 1.0,
                "answer_in_retrieved_gold_doc": supported,
                "retrieved_ids": ids,
            }
        )

    mean_recall = sum(recall_scores) / len(recall_scores)
    mean_support = sum(support_scores) / len(support_scores)
    report = {
        "k": args.k,
        "n": len(gold),
        "gold": "eval/gold_qa.jsonl",
        "model": args.model,
        "recall_at_k": round(mean_recall, 6),
        "recall_hits": int(sum(recall_scores)),
        "answer_in_retrieved_gold_doc": round(mean_support, 6),
        "answer_supported_hits": int(sum(support_scores)),
        "note": (
            "Recall@k is whether a gold document id is in the top k. "
            "answer_in_retrieved_gold_doc is whether that same hit contains the gold answer string. "
            "This is not an LLM citation score."
        ),
        "items": per_item,
    }
    print(
        f"\nRecall@{args.k} (n={len(recall_scores)}): "
        f"{mean_recall:.3f}  [{sum(recall_scores):.0f}/{len(recall_scores)}]"
    )
    print(
        f"Answer string inside a retrieved gold document (n={len(support_scores)}): "
        f"{mean_support:.3f}  [{sum(support_scores):.0f}/{len(support_scores)}]"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
