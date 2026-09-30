import json
import os
import threading
from typing import Dict, List, Optional

import faiss
from sentence_transformers import SentenceTransformer


class Retriever:
    """Retriever with optional on-disk FAISS index and metadata.

    Usage:
      - If `index_path` and `meta_path` exist, call `load_index_from_disk`.
      - Otherwise, `load_documents(jsonl_path)` then `build_index()`.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.encoder = SentenceTransformer(self.model_name)
        self.docs: List[Dict] = []  # raw docs (one per JSONL line) when built from JSONL
        self.meta: List[Dict] = []  # per-vector metadata (always aligned to FAISS rows)
        self.index: Optional[faiss.Index] = None
        self._lock = threading.Lock()

    def load_documents(self, path: str):
        path = os.path.abspath(path)
        docs = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                docs.append(obj)
        self.docs = docs

    def load_documents_many(self, paths: List[str]):
        """Load and concatenate multiple JSONL files (skips missing paths)."""
        merged: List[Dict] = []
        for path in paths:
            if not path or not os.path.isfile(path):
                continue
            ap = os.path.abspath(path)
            with open(ap, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    merged.append(json.loads(line))
        self.docs = merged

    def build_index(self):
        """Build in-memory FAISS index from `self.docs` (one embedding per doc row)."""
        texts = [d.get("text", "") for d in self.docs]
        if not texts:
            raise ValueError("No documents to index")
        with self._lock:
            embeddings = self.encoder.encode(
                texts, convert_to_numpy=True, normalize_embeddings=True
            )
            dim = embeddings.shape[1]
            index = faiss.IndexFlatIP(dim)
            index.add(embeddings)
            self.index = index
            self.meta = []
            for i, d in enumerate(self.docs):
                self.meta.append(
                    {
                        "id": d.get("id")
                        or (
                            f"{d.get('doc_id')}-c{d.get('chunk', i)}"
                            if d.get("doc_id")
                            else f"doc{i}"
                        ),
                        "title": d.get("title", ""),
                        "text": d.get("text", ""),
                        "source_url": d.get("source_url", ""),
                        "license": d.get("license", ""),
                        "external_id": d.get("external_id", d.get("id", f"doc{i}")),
                    }
                )

    def load_index_from_disk(self, index_path: str, meta_path: str):
        """Load a FAISS index and corresponding metadata (jsonl of chunks)."""
        if not os.path.exists(index_path):
            raise FileNotFoundError(index_path)
        if not os.path.exists(meta_path):
            raise FileNotFoundError(meta_path)
        with self._lock:
            self.index = faiss.read_index(index_path)
            meta = []
            with open(meta_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    meta.append(json.loads(line))
            self.meta = meta
            self.docs = []

    def append_chunks(self, chunks: List[Dict]) -> int:
        """Embed and append rows to FAISS + meta. Chunks must include id, title, text."""
        if self.index is None:
            raise RuntimeError("Index not built or loaded")
        existing_ids = {m.get("id") for m in self.meta}
        filtered: List[Dict] = []
        for c in chunks:
            cid = c.get("id")
            if not cid or cid in existing_ids:
                continue
            text = (c.get("text") or "").strip()
            if not text:
                continue
            filtered.append(c)
        if not filtered:
            return 0
        texts = [c.get("text", "") for c in filtered]
        with self._lock:
            emb = self.encoder.encode(
                texts, convert_to_numpy=True, normalize_embeddings=True
            )
            self.index.add(emb)
            for c in filtered:
                self.meta.append(
                    {
                        "id": c.get("id"),
                        "title": c.get("title", ""),
                        "text": c.get("text", ""),
                        "source_url": c.get("source_url", ""),
                        "license": c.get("license", ""),
                        "external_id": c.get("external_id", c.get("id")),
                    }
                )
        return len(filtered)

    def save_index_to_disk(self, index_path: str, meta_path: str):
        """Persist current index and meta (caller should hold consistency expectations)."""
        with self._lock:
            if self.index is None:
                raise RuntimeError("No index to save")
            os.makedirs(os.path.dirname(os.path.abspath(index_path)), exist_ok=True)
            os.makedirs(os.path.dirname(os.path.abspath(meta_path)), exist_ok=True)
            faiss.write_index(self.index, index_path)
            with open(meta_path, "w", encoding="utf-8") as f:
                for row in self.meta:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def retrieve(self, query: str, k: int = 3) -> List[Dict]:
        if self.index is None:
            raise RuntimeError("Index not built or loaded")
        with self._lock:
            q_emb = self.encoder.encode(
                [query], convert_to_numpy=True, normalize_embeddings=True
            )
            D, I = self.index.search(q_emb, k)
            meta_snapshot = list(self.meta)
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx < 0:
                continue
            if idx >= len(meta_snapshot):
                continue
            doc = meta_snapshot[idx].copy()
            doc["score"] = float(score)
            results.append(doc)
        return results
