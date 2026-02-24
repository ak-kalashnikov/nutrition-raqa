import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_query_endpoint(client):
    """Test /query endpoint with valid request."""
    payload = {
        "question": "What is protein?",
        "k": 2
    }
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert "results" in data
    assert data["question"] == "What is protein?"


def test_query_endpoint_default_k(client):
    """Test /query endpoint uses default k=3."""
    payload = {"question": "nutrition"}
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) <= 3


def test_query_endpoint_custom_k(client):
    """Test /query endpoint with custom k value."""
    payload = {
        "question": "health",
        "k": 1
    }
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) <= 1


def test_query_endpoint_missing_question(client):
    """Test /query endpoint without question field."""
    payload = {"k": 2}
    response = client.post("/query", json=payload)
    assert response.status_code == 422  # Validation error


def test_query_returns_document_structure(client):
    """Test that query results contain required fields."""
    payload = {"question": "training", "k": 1}
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    results = response.json()["results"]
    if len(results) > 0:
        doc = results[0]
        assert "id" in doc
        assert "text" in doc
        assert "score" in doc
