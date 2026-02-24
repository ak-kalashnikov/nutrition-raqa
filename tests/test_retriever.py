import pytest
import os
import tempfile
import json
from app.retriever import Retriever


@pytest.fixture
def sample_data_file():
    """Create a temporary data file with sample documents."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl', encoding='utf-8') as f:
        f.write('{"id": "1", "title": "Protein", "text": "Protein is essential for muscle growth and tissue repair."}\n')
        f.write('{"id": "2", "title": "Hydration", "text": "Staying hydrated improves athletic performance and recovery."}\n')
        f.write('{"id": "3", "title": "Sleep", "text": "Sleep is critical for muscle recovery and adaptation."}\n')
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def retriever(sample_data_file):
    """Create a Retriever instance with sample data."""
    ret = Retriever(model_name="all-MiniLM-L6-v2")
    ret.load_documents(sample_data_file)
    ret.build_index()
    return ret


def test_retriever_loads_documents(sample_data_file):
    """Test that retriever correctly loads documents."""
    ret = Retriever()
    ret.load_documents(sample_data_file)
    assert len(ret.docs) == 3
    assert ret.docs[0]['id'] == "1"
    assert "Protein" in ret.docs[0]['title']


def test_retriever_builds_index(retriever):
    """Test that index is built correctly."""
    assert retriever.index is not None
    assert retriever.embeddings is not None
    assert retriever.embeddings.shape[0] == 3


def test_retriever_retrieves_results(retriever):
    """Test that retriever returns relevant documents."""
    results = retriever.retrieve("How important is protein?", k=2)
    assert len(results) <= 2
    assert all('score' in r for r in results)
    assert all(0 <= r['score'] <= 1 for r in results)
    # Top result should be about protein
    assert len(results) > 0
    assert "Protein" in results[0]['title']


def test_retriever_k_parameter(retriever):
    """Test that k parameter limits results."""
    results_k1 = retriever.retrieve("nutrition", k=1)
    results_k3 = retriever.retrieve("nutrition", k=3)
    assert len(results_k1) == 1
    assert len(results_k3) <= 3


def test_retriever_handles_empty_query(retriever):
    """Test retriever with empty query."""
    results = retriever.retrieve("", k=1)
    assert len(results) > 0
