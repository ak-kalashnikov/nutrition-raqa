# Data Ingestion & Index Building Guide

This guide covers how to ingest nutrition, health, and fitness data from open-access sources and build a FAISS index for the RAQA system.

## Overview

The ingestion pipeline has two main stages:

1. **Collection** (`ingest/collector.py`): Fetch docs from open sources (PMCOA, gov sites, open textbooks)
2. **Processing** (`ingest/processor.py`): Chunk, embed, and build FAISS index
3. **Loading** (`app/main.py`): Load the index at startup

## Quick Start: Build Index from Existing JSONL

If you already have documents in JSONL format:

```bash
source .venv/bin/activate
python3 -m ingest.build_index \
  --jsonl data/nutrition_qa.jsonl \
  --out data/index \
  --model all-MiniLM-L6-v2
```

This creates:
- `data/index/faiss.index` — the FAISS index (can be loaded/deployed)
- `data/index/meta.jsonl` — document chunks with metadata (title, doc_id, text)

## Data Format: JSONL

Your input file should have one JSON object per line:

```json
{"id": "doc1", "title": "Protein Synthesis", "text": "Protein synthesis occurs when..."}
{"id": "doc2", "title": "Carbohydrate Loading", "text": "Athletes often carbo-load before endurance events..."}
```

**Required fields:**
- `id` or `doc_id`: unique document identifier
- `text`: document content

**Optional fields:**
- `title`: human-readable title
- `source`: where the document came from (ACE, PMCOA, NHS, etc.)
- `url`: original URL (for citation)
- `license`: license type (CC-BY, public domain, etc.)

## Adding Real Data: Open Sources

### 1. PubMed Central Open Access Subset (PMCOA)

Free, full-text biomedical articles. Includes nutrition, exercise, sports medicine.

**How to access:**
- [PMCOA FTP](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3484496/)
- Use [Europe PMC API](https://europepmc.org/RestfulWebService) for targeted searches

**Example: Download PMCOA articles on nutrition**

```bash
# Using Europe PMC REST API
curl "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=nutrition%20AND%20OPEN_ACCESS&format=json&pageSize=100" \
  > pmcoa_search.json
```

Parse the JSON, extract full-text URLs, download PDFs or XML, convert to JSONL.

**Data model:**
```json
{"id": "PMC1234567", "title": "Effects of Protein on Muscle Growth", "text": "...", "source": "PMCOA", "pmcid": "PMC1234567", "doi": "10.1234/example"}
```

### 2. U.S. Government Nutrition Guidelines

CDC, USDA, NIH content is public domain.

**Sources:**
- [USDA MyPlate](https://www.myplate.gov/)
- [CDC Physical Activity Guidelines](https://www.cdc.gov/physicalactivity/)
- [NIH Dietary Supplements](https://ods.od.nih.gov/)

**Crawling approach:**
```python
from ingest.collector import fetch_url_text
urls = [
  "https://www.myplate.gov/eat-healthy/what-should-you-eat",
  "https://www.cdc.gov/physicalactivity/basics/pa-health/index.htm"
]
for i, url in enumerate(urls):
    text = fetch_url_text(url)
    # Parse HTML, extract main content
    # Save to JSONL
```

### 3. NHS & WHO Guidelines

Most NHS guidance is permissive for reuse with attribution.

**Sources:**
- [NHS Live Well](https://www.nhs.uk/live-well/)
- [WHO Nutrition](https://www.who.int/health-topics/nutrition)

**License:** Typically Open Government License (OGL) or CC-BY equivalents — check per-page.

### 4. Open Textbooks and Academic Articles

- [Open Stax](https://openstax.org/) — free textbooks (CC-BY)
- [arXiv](https://arxiv.org/) — preprints (no paywall)
- [Directory of Open Access Journals (DOAJ)](https://doaj.org/)

**Example: Download from Open Stax**
```python
# Open Stax book on Human Biology includes nutrition/exercise sections
url = "https://openstax.org/books/anatomy-and-physiology/pages/1-1-overview-of-anatomy-and-physiology"
# Parse HTML and extract text
```

## Workflow: Ingest → Chunk → Embed → Index

### Step 1: Collect Documents

```bash
# Download documents to data/raw/
# Supported formats: HTML, PDF, plain text, XML (from PMCOA)
python3 ingest/collector.py --gov --pmcoa
```

Or manually place files in `data/raw/`.

### Step 2: Convert to JSONL

Parse HTML/PDF/XML and convert to JSONL:

```python
from ingest.processor import chunk_text
from pathlib import Path
import json

docs = []
for txt_file in Path("data/raw").glob("*.txt"):
    text = txt_file.read_text()
    docs.append({
        "id": txt_file.stem,
        "title": txt_file.stem.replace("_", " "),
        "text": text,
        "source": "custom"
    })

out = Path("data/nutrition_qa.jsonl")
with open(out, "w") as f:
    for d in docs:
        f.write(json.dumps(d) + "\n")
```

### Step 3: Build Index

```bash
python3 -m ingest.build_index \
  --jsonl data/nutrition_qa.jsonl \
  --out data/index
```

### Step 4: Start API Server

```bash
uvicorn app.main:app --reload
```

The server will automatically load `data/index/faiss.index` if it exists.

### Step 5: Test

```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"benefits of carbohydrate loading","k":3}'
```

## Advanced: Large-Scale Ingestion

For thousands/millions of documents:

1. **Parallel chunking & embedding**: Use `multiprocessing` or batch processing
2. **Distributed indexing**: Build partial indexes on multiple machines, merge with FAISS
3. **GPU acceleration**: Use `torch` and GPU for embedding generation (100x faster)
4. **Streaming**: Load indexes on-demand instead of keeping all in memory

Example with GPU:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
model = model.cuda()  # Use GPU
embeddings = model.encode(texts, batch_size=128, convert_to_numpy=True)
```

## Data Provenance & Licensing

**Always record:**
- **Source**: Where did the document come from? (PMCOA, NHS, etc.)
- **License**: What license applies? (CC-BY, public domain, etc.)
- **Date**: When was it retrieved/last updated?
- **URL**: Original URL for attribution and fact-checking

**Example metadata:**
```json
{
  "id": "nhs_protein_2024",
  "title": "NHS: Protein and Your Health",
  "text": "...",
  "source": "NHS",
  "license": "Open Government License (OGL)",
  "url": "https://www.nhs.uk/live-well/eat-well/",
  "retrieved_date": "2024-02-23"
}
```

## Licensing Best Practices

| Source | License | Reuse | Notes |
|--------|---------|-------|-------|
| PMCOA | Varies (mostly CC) | Check article | Author's original license applies |
| USDA/CDC | Public domain | Yes | U.S. federal content |
| NHS | OGL/CC-BY | Yes (with attribution) | UK gov content |
| WHO | CC-BY | Yes (with attribution) | UN agency content |
| arXiv | CC-BY | Yes | Authors retain copyright |
| Open Stax | CC-BY | Yes | Explicitly permissive |

**Rule of thumb:** If unsure, ask or use only CC-BY / public domain content.

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'sentence_transformers'"
**Solution:** Run inside `.venv` with requirements installed:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: Slow embedding on CPU
**Solution:** Use a faster model or GPU acceleration:
```bash
python3 -m ingest.build_index \
  --model all-MiniLM-L6-v2 \  # Fast, small
  --jsonl data/nutrition_qa.jsonl
```

### Issue: Index too large (disk space)
**Solution:**
- Use index compression: `faiss.downcast_index(index)`
- Use HNSW or other memory-efficient indexes (see [FAISS docs](https://github.com/facebookresearch/faiss))

### Issue: Low retrieval quality
**Solution:**
- Add more diverse documents
- Use reranking (fine-tune cross-encoder on your domain)
- Improve chunking (better chunk size/overlap for your domain)

## Next Steps

1. **Add real data**: Download PMCOA or gov docs and convert to JSONL
2. **Expand scope**: Add fitness/exercise, supplement science, sports medicine docs
3. **Fine-tune models**: Fine-tune embeddings or reranker on your domain
4. **Deploy**: Push index to GitHub, deploy to AWS/GCP/Render (see DEPLOYMENT.md)

## References

- [FAISS Documentation](https://github.com/facebookresearch/faiss)
- [Sentence-Transformers](https://www.sbert.net/)
- [PMCOA Browser](https://www.ncbi.nlm.nih.gov/pmc/)
- [Creative Commons Licenses](https://creativecommons.org/licenses/)
