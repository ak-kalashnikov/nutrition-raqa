"""API tests with Retriever and LLM stack mocked (no SentenceTransformer load)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Boot FastAPI with mocked Retriever / Groq / LLMRouter."""
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = [
        {
            "id": "d1",
            "title": "Protein timing",
            "text": "Aim for 20-40g of high-quality protein post-workout.",
            "score": 0.91,
        }
    ]
    # startup may call these depending on whether disk index exists
    mock_retriever.load_index_from_disk = MagicMock()
    mock_retriever.load_documents_many = MagicMock()
    mock_retriever.build_index = MagicMock()
    mock_retriever.save_index_to_disk = MagicMock()

    mock_llm = MagicMock()
    mock_llm.list_options.return_value = [
        {"id": "groq:llama-3.3-70b-versatile", "label": "Groq Llama"}
    ]
    mock_llm.resolve_default.return_value = "groq:llama-3.3-70b-versatile"
    mock_llm.complete.return_value = "Protein after training supports recovery."

    with (
        patch("app.main.Retriever", return_value=mock_retriever),
        patch("app.main.Groq"),
        patch("app.main.LLMRouter", return_value=mock_llm),
        patch("app.main.hub_index_store.try_download_index", return_value=False),
    ):
        # Import after patches so startup uses mocks
        import app.main as main_mod

        # Clear cached settings side effects are fine; force module globals reset via TestClient lifespan
        with TestClient(main_mod.app) as c:
            # Expose mocks for assertions
            c.mock_retriever = mock_retriever  # type: ignore[attr-defined]
            c.mock_llm = mock_llm  # type: ignore[attr-defined]
            yield c


def test_health_ok(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["retriever_initialized"] is True


def test_query_returns_sources(client: TestClient):
    resp = client.post(
        "/query",
        json={"question": "How much protein do athletes need after training?", "k": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["question"]
    assert body.get("error") is None or "error" not in body or body.get("answer")
    assert body.get("sources") or body.get("answer")
    client.mock_retriever.retrieve.assert_called()  # type: ignore[attr-defined]


def test_query_below_threshold_abstains(client: TestClient):
    client.mock_retriever.retrieve.return_value = [  # type: ignore[attr-defined]
        {
            "id": "d1",
            "title": "Protein timing",
            "text": "Aim for 20-40g of high-quality protein post-workout.",
            "score": 0.05,
        }
    ]
    client.mock_llm.complete.reset_mock()  # type: ignore[attr-defined]
    resp = client.post(
        "/query",
        json={"question": "What is the capital of the saxophone nebula?", "k": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["abstained"] is True
    assert body["sources"] == []
    assert body["source_count"] == 0
    assert "nutrition documents" in body["answer"]
    client.mock_llm.complete.assert_not_called()  # type: ignore[attr-defined]
    client.mock_retriever.append_chunks.assert_not_called()  # type: ignore[attr-defined]


def test_query_greeting_short_circuit(client: TestClient):
    resp = client.post("/query", json={"question": "hello", "k": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert "Hi" in (body.get("answer") or "") or "nutrition" in (body.get("answer") or "").lower()
    assert body.get("source_count", 0) == 0
