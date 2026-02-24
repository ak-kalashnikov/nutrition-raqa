# Project File Structure & Purposes

Complete overview of all files in the Nutrition RAQA system and their roles.

---

## 📁 Core Application (`app/`)

### `app/main.py`
**Purpose:** FastAPI application entry point
**Key Functions:**
- `@app.on_event("startup")` – Load FAISS index from disk on server startup
- `@app.post("/query")` – Query endpoint accepting JSON, returns ranked results
- `@app.get("/health")` – Health check endpoint
- `@app.get("/chat")` – Serve chat UI HTML
- Static file mounting – Serve CSS/JS from `/static/`

**Who Uses It:** Any client hitting the API
**Dependencies:** `retriever.py`, FastAPI, Pydantic
**When to Modify:** Add new endpoints or change startup logic

---

### `app/retriever.py`
**Purpose:** Core semantic search engine
**Key Class: `Retriever`**
- `load_documents(path)` – Parse JSONL documents
- `build_index()` – Create in-memory FAISS index
- `load_index_from_disk(index_path, meta_path)` – Load pre-built index from disk
- `retrieve(query, k=3)` – Semantic search, return top-k results

**Performance:** ~100ms per query on CPU
**Dependencies:** sentence-transformers, FAISS
**When to Modify:** Change embedding model, adjust chunking logic, or add filtering

---

### `app/schemas.py`
**Purpose:** Pydantic data validation models
**Classes:**
- `QueryRequest` – Validate incoming query (question, k)
- `DocumentResult` – Individual search result (doc_id, title, text, score)
- `QueryResponse` – API response format

**When to Modify:** Change API request/response structure

---

### `app/static/chat.html`
**Purpose:** Interactive web chat interface
**Features:**
- Modern, responsive chat design (ChatGPT-inspired)
- Form for submitting questions
- Message display area with scrolling
- Links to CSS and JavaScript

**When to Modify:** Change UI layout, add new features (voice input, etc.)

---

### `app/static/chat.css`
**Purpose:** Styling for chat UI
**Features:**
- Dark theme with teal/cyan accents
- Responsive design (mobile + desktop)
- Animations and transitions
- Custom scrollbars
- Modern typography

**When to Modify:** Change colors, fix layout issues, add new components

---

### `app/static/chat.js`
**Purpose:** Client-side interactivity
**Key Functions:**
- `addMessage(text, cls)` – Add message bubble to DOM
- `formatDocResult(result, index)` – Format search result for display
- Form submit handler – Send query to `/query` API, display results
- Textarea auto-expand, keyboard shortcuts (Enter, Shift+Enter)

**When to Modify:** Add new UI interactions, change API integration

---

## 📁 Data Ingestion (`ingest/`)

### `ingest/collector.py`
**Purpose:** Download documents from online sources
**Status:** Safe templates (no auto-execution of scrapers)
**Functions:**
- `fetch_url_text(url)` – Download and parse HTML
- `collect_pmcoa_sample(count)` – Template for PMCOA abstracts
- `collect_gov_guideline()` – Template for government docs
- `collect_open_textbook()` – Template for textbooks

**When to Use:** Phase 2 - ingesting real data
**Dependencies:** requests, BeautifulSoup, readability-lxml
**Note:** Functions are documented but not auto-executed (safe by design)

---

### `ingest/processor.py`
**Purpose:** Transform documents into searchable FAISS index
**Key Functions:**
- `load_jsonl(path)` – Parse JSONL files
- `chunk_text(text, chunk_size=400, overlap=50)` – Split documents into chunks
- `embed_texts(texts, model_name)` – Generate embeddings (sentence-transformers)
- `build_faiss_index(embeddings)` – Create FAISS IndexFlatIP
- `save_index(index, path)` – Save index to disk
- `save_metadata(rows, path)` – Save chunk metadata (JSONL)
- `build_from_jsonl(jsonl_path, out_dir)` – Full pipeline

**When to Use:** Every time you add new documents
**Command:**
```bash
python3 -m ingest.build_index --jsonl data/nutrition_qa.jsonl --out data/index
```

---

### `ingest/build_index.py`
**Purpose:** CLI tool for building indexes
**Usage:**
```bash
python3 -m ingest.build_index --jsonl <path> --out <directory>
```

**Parameters:**
- `--jsonl <path>` – Input JSONL file
- `--out <directory>` – Output directory for index files

**When to Use:** Building index from JSONL documents

---

### `ingest/__init__.py`
**Purpose:** Python package marker
**Do Not Modify:** Standard Python package initialization

---

## 📁 Data (`data/`)

### `data/nutrition_qa.jsonl`
**Purpose:** Sample nutrition documents (8 documents, provided for demonstration)
**Format:** JSON Lines (one JSON object per line)
**Example:**
```json
{"id": "d1", "title": "Protein Synthesis...", "text": "Full document body..."}
```

**Contents:**
- Protein timing and recovery
- Hydration and electrolytes
- Carbohydrate loading
- Iron and minerals
- Sleep optimization
- Creatine supplementation
- Weight management
- Pre-workout nutrition

**When to Replace:** Add more documents by creating `nutrition_all.jsonl` with real data (Phase 2)

---

### `data/index/faiss.index`
**Purpose:** Pre-built FAISS vector index
**Size:** ~5MB (384-dimensional embeddings)
**Auto-Generated:** When you run `python3 -m ingest.build_index`
**Contains:** ~9 chunks from sample documents, ready for semantic search

**When to Rebuild:** After adding new documents

---

### `data/index/meta.jsonl`
**Purpose:** Chunk-level metadata for search results
**Format:** JSON Lines (one metadata object per chunk)
**Example:**
```json
{"doc_id": "d1", "title": "Protein...", "chunk_idx": 0, "text": "Extracted chunk text..."}
```

**Auto-Generated:** When you run `python3 -m ingest.build_index`

---

## 🧪 Tests (`tests/`)

### `tests/test_data.py`
**Purpose:** Validate data integrity
**Tests:**
- Load and parse JSONL
- Validate document structure
- Check for empty/malformed documents

**Run:**
```bash
pytest tests/test_data.py -v
```

---

### `tests/test_retriever.py`
**Purpose:** Unit tests for semantic search engine
**Tests:**
- Build FAISS index from documents
- Embedding generation
- Vector search and ranking
- Metadata tracking

**Run:**
```bash
pytest tests/test_retriever.py -v
```

---

### `tests/test_main.py`
**Purpose:** Integration tests for FastAPI endpoints
**Tests:**
- Health check endpoint
- Query endpoint (JSON response)
- Chat endpoint (HTML response)

**Note:** Some tests skip on test client (startup event limitation)
**Run:**
```bash
pytest tests/test_main.py -v
```

---

### `tests/__init__.py`
**Purpose:** Python package marker
**Do Not Modify:** Standard initialization

---

## 🐳 Infrastructure

### `Dockerfile`
**Purpose:** Build production Docker image
**What It Does:**
- Python 3.11 slim base image
- Install dependencies
- Copy application code
- Set entry point

**When to Modify:** Change Python version or dependencies

---

### `docker-compose.yml`
**Purpose:** Local development environment
**Services:**
- `api` – FastAPI application

**Usage:**
```bash
docker-compose up -d
```

---

### `requirements.txt`
**Purpose:** Python package dependencies
**Key Packages:**
- `fastapi` – Web framework
- `sentence-transformers` – Embedding model
- `faiss-cpu` – Vector search
- `pydantic` – Data validation
- `pytest` – Testing

**When to Modify:** Add new Python packages
**Install:**
```bash
pip install -r requirements.txt
```

---

## 📚 Documentation

### `README.md`
**Purpose:** Main project documentation
**Sections:**
- Project overview
- Architecture diagram
- Quick start guide
- API endpoints
- Deployment instructions
- Contributing guidelines

**Audience:** Anyone discovering the project
**When to Update:** Major changes, new features

---

### `QUICKSTART.md`
**Purpose:** 5-minute usage guide
**Sections:**
- Start server
- Open chat UI
- API usage (curl examples)
- Update knowledge base
- Deploy live

**Audience:** Users wanting to run locally
**Length:** ~100 lines

---

### `INGESTION.md`
**Purpose:** Comprehensive data sourcing guide
**Sections:** (300+ lines)
- Available data sources (PMCOA, USDA, CDC, NHS, ACE, textbooks)
- License information
- Download instructions
- Conversion to JSONL
- Ingestion workflow
- Troubleshooting

**Audience:** Phase 2 - data collection team

---

### `DEPLOYMENT.md`
**Purpose:** Cloud deployment guides
**Sections:**
- Hugging Face Spaces (free demo)
- Render (free backend)
- AWS/GCP (production)
- Docker deployment
- Environment variables

**Audience:** DevOps / deployment team

---

### `PROJECT_SUMMARY.md`
**Purpose:** Architecture and design decisions
**Sections:**
- System architecture
- Technology choices
- Data pipeline
- API design
- Performance considerations

**Audience:** Developers reviewing architecture

---

### `PHASE1_COMPLETE.md` (NEW)
**Purpose:** Phase 1 completion summary
**Sections:**
- What was built
- Key deliverables
- Technology stack
- Performance metrics
- Testing results
- Next steps (Phase 2)

**Audience:** Portfolio reviewers, project stakeholders

---

### `DATA_INGESTION_PHASE2.md` (NEW)
**Purpose:** Detailed Phase 2 ingestion checklist
**Sections:**
- Data sources to download
- Conversion to JSONL
- Building the index
- Quality checks
- Timeline estimates
- Success criteria

**Audience:** Users adding real data in Phase 2

---

## ⚙️ Configuration

### `.env.example`
**Purpose:** Template for environment variables
**Example:**
```
MODEL_NAME=all-MiniLM-L6-v2
INDEX_PATH=data/index/faiss.index
```

**When to Use:** Copy to `.env` for local configuration

---

### `.gitignore`
**Purpose:** Exclude files from Git
**Ignores:**
- `.venv/` – Virtual environment
- `__pycache__/` – Python cache
- `*.pyc` – Compiled Python
- `.env` – Local secrets
- `data/index/` – Generated index files

---

### `setup.sh`
**Purpose:** Automated project setup
**What It Does:**
- Create virtual environment
- Install dependencies
- Create data directories
- Initialize Git

**Usage:**
```bash
bash setup.sh
```

---

## 🔄 CI/CD

### `.github/workflows/ci.yml`
**Purpose:** Automated testing on GitHub
**Runs On:** Every push and pull request
**Checks:**
- `pytest` – Run all tests
- `flake8` – Code style
- `mypy` – Type checking

**When to Modify:** Change CI requirements

---

## 📊 Summary Table

| File | Purpose | When to Modify |
|------|---------|---|
| `app/main.py` | FastAPI server | Add endpoints |
| `app/retriever.py` | Search engine | Change model/chunking |
| `app/schemas.py` | Data validation | Change API schema |
| `app/static/chat.html` | Chat UI layout | Change UI design |
| `app/static/chat.css` | Chat UI styling | Change colors/fonts |
| `app/static/chat.js` | Chat interactivity | Add features |
| `ingest/collector.py` | Data download | Phase 2 ingestion |
| `ingest/processor.py` | Indexing | Change embedding/chunking |
| `ingest/build_index.py` | CLI tool | Rarely modified |
| `requirements.txt` | Dependencies | Add packages |
| `Dockerfile` | Container image | Change Python version |
| `docker-compose.yml` | Dev environment | Add services |
| `README.md` | Main docs | Major changes |
| `QUICKSTART.md` | Quick setup | New users |
| `INGESTION.md` | Data guide | Phase 2 |
| `DEPLOYMENT.md` | Deployment | Change hosting |
| `tests/test_*.py` | Test suite | Add features |

---

## 🚀 Typical Workflows

### Workflow 1: Run Locally
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
# Open http://localhost:8000/chat
```

### Workflow 2: Add Data
```bash
# 1. Create JSONL with new documents
# 2. Run indexing
python3 -m ingest.build_index --jsonl data/nutrition_all.jsonl --out data/index
# 3. Restart server
```

### Workflow 3: Test
```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_retriever.py -v
```

### Workflow 4: Deploy
```bash
# Option 1: HF Spaces (free demo)
# Push to GitHub, create HF Spaces repo

# Option 2: Docker (any cloud)
docker build -t nutrition-raqa .
docker run -p 8000:8000 nutrition-raqa
```

---

## 📋 File Checklist for Portfolio

Essential files for GitHub/LinkedIn:

- ✅ `README.md` – Main documentation
- ✅ `QUICKSTART.md` – Easy to get started
- ✅ `PHASE1_COMPLETE.md` – Show what you built
- ✅ `DATA_INGESTION_PHASE2.md` – Show roadmap
- ✅ `app/` – Clean, production code
- ✅ `tests/` – Test coverage
- ✅ `Dockerfile` – Show DevOps knowledge
- ✅ `.github/workflows/` – Show CI/CD
- ✅ `requirements.txt` – Clear dependencies
- ✅ `.gitignore` – Professional organization

---

**Status:** All files documented  
**Last Updated:** Phase 1 Complete  
**Next:** Phase 2 (add real data via INGESTION guides)
