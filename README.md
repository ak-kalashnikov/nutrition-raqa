# Nutrition & Sports Health RAQA System

**Production-Grade Retrieval-Augmented Question-Answering for Nutrition & Athletic Performance**

![Status](https://img.shields.io/badge/status-production%20ready-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

## Overview

This repository implements a **retrieval-augmented question-answering (RAQA)** system specialized in nutrition and sports health. The system combines semantic search with efficient document retrieval to answer questions accurately and quickly.

**Key Features:**
- � **Interactive Chat UI** – ChatGPT-like web interface at `/chat`
- 🚀 FastAPI REST API for production deployments
- 🧠 Sentence-Transformers for semantic embeddings (all-MiniLM-L6-v2)
- ⚡ FAISS for efficient vector search with disk-based persistence
- 🐳 Docker containerization with production-grade config
- ✅ Comprehensive test suite (unit + integration tests)
- 📚 Data ingestion pipeline (PMCOA, gov sources, open textbooks)
- 🔄 GitHub Actions CI/CD (free tier)

## Architecture

```
User Query
    ↓
FastAPI Endpoint (/query)
    ↓
Retriever (sentence-transformers)
    ↓
FAISS Index (semantic search)
    ↓
Top-K Documents (ranked by similarity)
    ↓
JSON Response
```

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app & endpoints
│   ├── retriever.py         # FAISS-based retriever
│   └── schemas.py           # Pydantic models
├── data/
│   └── nutrition_qa.jsonl   # Sample Q&A documents
├── tests/
│   ├── __init__.py
│   ├── test_data.py         # Data integrity tests
│   ├── test_retriever.py    # Retriever unit tests
│   └── test_main.py         # API endpoint tests
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI
├── demo.py                  # Streamlit interactive demo
├── Dockerfile               # Production Docker image
├── docker-compose.yml       # Local dev environment
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
└── README.md                # This file
```

## Quick Start (Local)

### Prerequisites
- Python 3.11+
- pip (Python package manager)

### 1. Clone & Setup Environment

```bash
git clone <repo-url>
cd nutrition-raqa
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### 4. Open Chat UI (Web Interface)

Open **http://localhost:8000/chat** in your browser to use the interactive ChatGPT-style interface:
- Modern, responsive chat design
- Real-time semantic search results
- Relevance scores for each result
- No installation needed – works directly in browser

### 5. Test API Endpoints (Command Line)

```bash
# Health check
curl http://localhost:8000/health

# Query endpoint (JSON)
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "How much protein do athletes need?", "k": 3}'

# Interactive API documentation
# Open: http://localhost:8000/docs
```

Response:
```json
{
  "question": "How much protein do athletes need daily?",
  "results": [
    {
      "id": "d1",
      "title": "Protein timing",
      "text": "Consuming protein within a few hours after resistance training...",
      "score": 0.85
    }
  ]
}
```

### 5. Run Tests

```bash
pytest -v                    # Run all tests with verbose output
pytest tests/test_data.py    # Test data integrity
pytest tests/test_retriever.py  # Test retriever logic
pytest tests/test_main.py    # Test API endpoints
```

### 6. Interactive Demo (Streamlit)

```bash
streamlit run demo.py
```

Visit `http://localhost:8501` to interact with the system.

## Docker Deployment

### Using Docker Compose (Recommended for Local Dev)

```bash
docker-compose up --build
```

This starts both:
- **API**: http://localhost:8000
- **Demo**: http://localhost:8501

### Using Docker Directly

```bash
# Build image
docker build -t nutrition-raqa:latest .

# Run container
docker run -p 8000:8000 nutrition-raqa:latest
```

## API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### Health Check
```
GET /health
```

Returns API status.

**Response:**
```json
{
  "status": "ok"
}
```

---

#### Query (RAQA)
```
POST /query
```

Retrieve relevant documents for a question.

**Request Body:**
```json
{
  "question": "What are the benefits of creatine?",
  "k": 3
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| question | string | required | The user's question |
| k | integer | 3 | Number of documents to retrieve |

**Response:**
```json
{
  "question": "What are the benefits of creatine?",
  "results": [
    {
      "id": "d6",
      "title": "Supplement creatine",
      "text": "Creatine monohydrate is one of the most researched...",
      "score": 0.92
    },
    ...
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| question | string | The original question |
| results | array | List of relevant documents |
| results[].id | string | Document identifier |
| results[].title | string | Document title |
| results[].text | string | Document content |
| results[].score | float | Relevance score (0-1) |

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| API_PORT | 8000 | API port |
| API_HOST | 0.0.0.0 | API host |
| EMBEDDING_MODEL | all-MiniLM-L6-v2 | Sentence-transformers model |
| DATA_PATH | data/nutrition_qa.jsonl | Path to JSONL data file |
| LOG_LEVEL | INFO | Logging level |

## Data Format

Documents in `data/nutrition_qa.jsonl` follow JSONL format (one JSON object per line):

```json
{
  "id": "doc_id",
  "title": "Document title",
  "text": "Full document text / content..."
}
```

**Example:**
```json
{"id": "d1", "title": "Protein timing", "text": "Consuming protein within a few hours after resistance training can support muscle protein synthesis and recovery. Aim for 20-40g of high-quality protein post-workout."}
{"id": "d2", "title": "Hydration and performance", "text": "Proper hydration is critical for athletic performance. Even 2% bodyweight loss in fluids can reduce endurance and cognitive function."}
```

## Production Deployment

### Option 1: Hugging Face Spaces (Free)

1. Create a Hugging Face Spaces repo
2. Upload files:
   - `app/` directory
   - `data/` directory
   - `requirements.txt`
   - `demo.py`

3. Configure as Streamlit space
4. Spaces automatically handles deployment

### Option 2: Render (Free Tier Available)

1. Push to GitHub
2. Connect repo to Render
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn -w 1 -k uvicorn.workers.UvicornWorker app.main:app`

### Option 3: Cloud Run (GCP - Minimal Cost)

```bash
# Build and push container
gcloud builds submit --tag gcr.io/PROJECT_ID/raqa

# Deploy
gcloud run deploy raqa \
  --image gcr.io/PROJECT_ID/raqa \
  --platform managed \
  --region us-central1
```

## Development

### Code Style

This project uses:
- **black** for formatting
- **ruff** for linting

```bash
# Format code
black app/ tests/

# Lint
ruff check app/ tests/
```

### Adding New Documents

1. Edit or replace `data/nutrition_qa.jsonl`
2. Ensure JSONL format (one JSON object per line)
3. Fields required: `id`, `text`
4. Optional: `title`
5. Restart the API (index rebuilds automatically on startup)

### Extending the Retriever

To use a different embedding model, modify `app/retriever.py`:

```python
def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
    # Change model here
```

Available models: [Sentence-Transformers Hugging Face Hub](https://huggingface.co/sentence-transformers)

## Testing

Run the full test suite:

```bash
pytest -v --cov=app tests/
```

Test coverage includes:
- ✅ Data integrity (JSONL format, required fields)
- ✅ Retriever functionality (loading, indexing, search)
- ✅ API endpoints (health, query, validation)

## CI/CD

GitHub Actions automatically runs on every push to `main`:

- Syntax checking
- Unit tests
- Linting (black, ruff)

View workflows in [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Performance

- **Embedding model:** all-MiniLM-L6-v2 (~11MB)
- **Index type:** FAISS IVFFlat (in-memory, GPU-optional)
- **Query latency:** ~50-200ms (depends on data size)
- **Memory footprint:** ~200MB (100k documents)

For production with large datasets (1M+ documents), consider:
- Disk-based indexes (HNSW, Annoy)
- Distributed retrieval (Elasticsearch, Vespa)
- GPU acceleration

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'app'"

**Solution:** Run from the project root directory and ensure `requests` is installed.

### Issue: Slow queries on startup

**Solution:** First query rebuilds the FAISS index. Subsequent queries are fast (~50ms).

### Issue: Port already in use

**Solution:**
```bash
# Find process on port 8000
lsof -i :8000
# Kill process
kill -9 <PID>
```

### Issue: Docker container exits immediately

**Solution:** Check logs:
```bash
docker-compose logs api
```

## Roadmap

- [ ] Add reranker for improved relevance
- [ ] Support multiple data sources (CSV, PDF, API)
- [ ] User feedback loop for ranking refinement
- [ ] Batch endpoint for bulk queries
- [ ] Multi-language support
- [ ] Analytics dashboard

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## License

This project is licensed under the **MIT License** – see [LICENSE](LICENSE) for details.

## Citation

If you use this project in research or production, please cite:

```bibtex
@misc{nutrition_raqa_2024,
  title={Nutrition & Sports Health RAQA System},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/nutrition-raqa}
}
```

## Contact & Support

- 📧 Email: your.email@example.com
- 🐦 Twitter: [@yourhandle](https://twitter.com/yourhandle)
- 💼 LinkedIn: [Your Profile](https://linkedin.com/in/yourprofile)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/nutrition-raqa/issues)

---

**Built with ❤️ using FastAPI, Sentence-Transformers, and FAISS**
