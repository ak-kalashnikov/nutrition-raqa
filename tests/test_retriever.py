"""Unit tests for Retriever with a lightweight mocked encoder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


def _keyword_encoder(texts, convert_to_numpy=True, normalize_embeddings=True):
    """Deterministic bag-of-keywords embeddings (dim=8) for unit tests."""
    if isinstance(texts, str):
        texts = [texts]
    dim = 8
    keys = [
        "protein",
        "hydrat",
        "creatine",
        "carbohydrate",
        "vitamin",
        "lipid",
        "mineral",
        "water",
    ]
    rows = []
    for text in texts:
        lower = (text or "").lower()
        v = np.zeros(dim, dtype=np.float32)
        for i, key in enumerate(keys):
            if key in lower:
                v[i] = 1.0
        if not v.any():
            # stable fallback so FAISS always gets a vector
            v[0] = 0.1
        if normalize_embeddings:
            n = float(np.linalg.norm(v))
            if n > 0:
                v = v / n
        rows.append(v)
    return np.stack(rows)


@pytest.fixture
def tiny_jsonl(tmp_path: Path) -> Path:
    path = tmp_path / "docs.jsonl"
    rows = [
        {
            "id": "d1",
            "title": "Protein timing",
            "text": "Consuming protein after resistance training supports recovery. Aim for 20-40g.",
        },
        {
            "id": "d2",
            "title": "Hydration",
            "text": "Proper hydration matters; 2% bodyweight fluid loss can reduce endurance.",
        },
        {
            "id": "d3",
            "title": "Creatine",
            "text": "Creatine monohydrate is a well-studied supplement with maintenance dosing.",
        },
    ]
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            import json

            f.write(json.dumps(row) + "\n")
    return path


def test_build_index_and_retrieve_returns_hits(tiny_jsonl: Path):
    mock_st = MagicMock()
    mock_st.encode.side_effect = _keyword_encoder

    with patch("app.retriever.SentenceTransformer", return_value=mock_st):
        from app.retriever import Retriever

        retriever = Retriever(model_name="mock-model")
        retriever.load_documents(str(tiny_jsonl))
        retriever.build_index()

        hits = retriever.retrieve("How much protein after training?", k=2)

    assert hits, "expected at least one retrieval hit"
    assert all("id" in h and "score" in h and "text" in h for h in hits)
    assert hits[0]["id"] == "d1"
    assert len(hits) <= 2


def test_retrieve_hydration_prefers_hydration_doc(tiny_jsonl: Path):
    mock_st = MagicMock()
    mock_st.encode.side_effect = _keyword_encoder

    with patch("app.retriever.SentenceTransformer", return_value=mock_st):
        from app.retriever import Retriever

        retriever = Retriever(model_name="mock-model")
        retriever.load_documents(str(tiny_jsonl))
        retriever.build_index()
        hits = retriever.retrieve("athletic hydration and fluid loss", k=1)

    assert hits[0]["id"] == "d2"


def test_build_index_requires_documents():
    mock_st = MagicMock()
    mock_st.encode.side_effect = _keyword_encoder

    with patch("app.retriever.SentenceTransformer", return_value=mock_st):
        from app.retriever import Retriever

        retriever = Retriever(model_name="mock-model")
        with pytest.raises(ValueError, match="No documents"):
            retriever.build_index()
