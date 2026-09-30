"""Data integrity tests for JSONL corpora."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

REQUIRED_FILES = (
    DATA_DIR / "nutrition_qa.jsonl",
    DATA_DIR / "open_textbook_chunks.jsonl",
    DATA_DIR / "pressbooks_chapters.jsonl",
)


@pytest.mark.parametrize("path", REQUIRED_FILES, ids=lambda p: p.name)
def test_jsonl_parses_and_has_required_fields(path: Path):
    assert path.is_file(), f"Missing data file: {path}"
    rows = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                pytest.fail(f"{path.name}:{lineno}: invalid JSON ({exc})")
            assert isinstance(obj, dict), f"{path.name}:{lineno}: expected object"
            assert "id" in obj and obj["id"], f"{path.name}:{lineno}: missing id"
            assert "text" in obj and str(obj["text"]).strip(), (
                f"{path.name}:{lineno}: missing text"
            )
            rows.append(obj)
    assert rows, f"{path.name}: expected at least one non-empty JSONL row"


def test_gold_answers_are_substrings_of_named_chunks():
    """Every gold answer must occur in the named document text."""
    gold_path = ROOT / "eval" / "gold_qa.jsonl"
    corpus: dict[str, str] = {}
    for path in REQUIRED_FILES:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                corpus[row["id"]] = row["text"]

    rows = []
    with gold_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    assert len(rows) >= 50
    seen = set()
    for row in rows:
        assert row["id"] not in seen
        seen.add(row["id"])
        answer = row.get("answer", "")
        assert answer.strip(), row["id"]
        doc_ids = row.get("gold_doc_ids") or []
        assert doc_ids, row["id"]
        blob = "\n".join(corpus[doc_id] for doc_id in doc_ids)
        assert answer in blob, f"{row['id']}: answer not in named chunk"


def test_nutrition_qa_ids_unique():
    path = DATA_DIR / "nutrition_qa.jsonl"
    ids = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ids.append(json.loads(line)["id"])
    assert len(ids) == len(set(ids))
