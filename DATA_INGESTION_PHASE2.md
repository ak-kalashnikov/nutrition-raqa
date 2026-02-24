# Real Data Ingestion Checklist - Phase 2

**Objective:** Expand the nutrition/sports health knowledge base from 8 sample documents to 1000+ real documents.

**Timeline:** 1-2 weeks (data collection) + few hours (indexing)

---

## 1. Data Sources to Download

### Primary Sources (Free, High Quality)

#### 📖 PubMed Central Open Access (PMCOA)
- **What:** ~2 million free biomedical research articles
- **Coverage:** Nutrition, exercise, recovery, supplementation, injury prevention
- **License:** Open access (free to use)
- **Quality:** Peer-reviewed, scientific
- **Scale:** Can download 100s of papers

**How to Get:**
```bash
# Option 1: Direct Download (via collector.py)
# See ingest/collector.py - fetch_urls_from_pmcoa()

# Option 2: Use PMCOA FTP
# ftp-private.ncbi.nlm.nih.gov/pub/pmc/oa_bulk/
# Download .tar.gz files, extract XML

# Option 3: Use Python library
pip install pymedcentral  # or similar
python -c "from ingest.collector import collect_pmcoa_sample; collect_pmcoa_sample(count=100)"
```

**Expected:** 50-200 high-quality nutrition research papers

---

#### 🏛️ Government Sources (USDA, CDC, NIH)
- **USDA FoodData Central**
  - Comprehensive nutrition facts
  - Link: https://fdc.nal.usda.gov/
  - Download: JSON/CSV format
  - Convert to JSONL with `ingest/processor.py`

- **NIH MyPlate Nutrition Guide**
  - Daily nutrition recommendations
  - Link: https://www.myplate.gov/
  - Scrape with `BeautifulSoup` (ethical, documented)

- **CDC Physical Activity Guidelines**
  - Evidence-based exercise recommendations
  - Link: https://www.cdc.gov/physicalactivity/
  - Multiple formats (PDF, HTML)

- **NHS Weight Management**
  - UK health authority guidance
  - Link: https://www.nhs.uk/live-well/
  - Free to use

**Expected:** 20-50 official government documents

---

#### 📚 Open Textbooks & Courses
- **OpenStax Anatomy & Physiology**
  - Free textbook (CC license)
  - Link: https://openstax.org/details/books/anatomy-and-physiology
  - Download: PDF or online
  - Extract chapters, convert to JSONL

- **Khan Academy Nutrition/Exercise (transcripts)**
  - Educational videos with transcripts
  - Link: https://www.khanacademy.org/
  - License: Creative Commons

- **LibreTexts Biology & Chemistry**
  - Free peer-reviewed textbooks
  - Link: https://libretexts.org/
  - Multiple chapters on metabolism, nutrients

**Expected:** 30-100 educational documents

---

#### 💪 ACE & Fitness Certifications
- **American Council on Exercise (ACE)**
  - Free fact sheets & guidelines
  - Link: https://www.acefitness.org/
  - Topics: Nutrition, training, recovery

- **ISSN Position Stands**
  - International Society of Sports Nutrition
  - Link: https://jissn.biomedcentral.com/
  - Many open-access position papers

**Expected:** 10-30 professional fitness documents

---

#### 🔬 Additional Sources (Pick Any)
| Source | URL | Count | License |
|--------|-----|-------|---------|
| ArXiv (Nutrition) | arxiv.org | 50-100 | CC |
| Google Scholar (alerts) | scholar.google.com | Variable | Varies |
| ResearchGate papers | researchgate.net | 20-50 | Author-dependent |
| PubMed abstracts | pubmed.ncbi.nlm.nih.gov | 500+ | Free |
| Nutrition Reviews | nutritionreviews.org | 10-30 | Some open access |

---

## 2. Conversion to JSONL Format

**Required Format:**
```json
{"id": "doc_001", "title": "Protein Synthesis...", "text": "Comprehensive text..."}
{"id": "doc_002", "title": "Hydration Guide...", "text": "Full document body..."}
```

**Conversion Scripts** (use these in `ingest/processor.py`):

```python
# PDF → JSONL
from pdfplumber import PDF
for page in PDF.open('nutrition_guide.pdf').pages:
    text = page.extract_text()
    doc = {"id": f"pdf_{i}", "title": "...", "text": text}
    # Write to JSONL

# HTML → JSONL
from bs4 import BeautifulSoup
soup = BeautifulSoup(html_content, 'html.parser')
text = soup.get_text()
doc = {"id": f"html_{i}", "title": "...", "text": text}
# Write to JSONL

# XML (PubMed) → JSONL
from xml.etree import ElementTree as ET
root = ET.parse('article.xml').getroot()
title = root.find('.//title-group/article-title').text
body = root.find('.//body').text
# Write to JSONL
```

**All dependencies already installed:**
```bash
grep "beautifulsoup4\|pdfplumber\|readability-lxml" requirements.txt
# Already present ✅
```

---

## 3. Building the Index with Real Data

### Step 1: Collect Documents

```bash
# Create data directory for raw documents
mkdir -p data/raw_sources

# Download (examples - use collector.py for automation)
# - PMCOA PDFs → data/raw_sources/pmcoa/
# - USDA CSV → data/raw_sources/usda/
# - Government HTML → data/raw_sources/gov/
# - Textbooks PDF → data/raw_sources/textbooks/
```

### Step 2: Convert to JSONL

```bash
# Use ingest/processor.py to convert all sources
python3 << 'EOF'
from ingest.processor import *

# Load and merge all documents
docs = []
for source in ['pmcoa', 'usda', 'gov', 'textbooks']:
    docs.extend(load_jsonl(f'data/raw_sources/{source}/documents.jsonl'))

# Save combined
with open('data/nutrition_all.jsonl', 'w') as f:
    for doc in docs:
        f.write(json.dumps(doc) + '\n')

print(f"Total documents: {len(docs)}")
EOF
```

### Step 3: Build FAISS Index

```bash
# Simple command
python3 -m ingest.build_index \
  --jsonl data/nutrition_all.jsonl \
  --out data/index

# This will:
# 1. Load documents from JSONL
# 2. Chunk each document (400 words, 50-word overlap)
# 3. Embed all chunks with all-MiniLM-L6-v2
# 4. Build FAISS index
# 5. Save index + metadata to disk
# Total time: 5-10 minutes (depending on document count)
```

### Step 4: Test with New Data

```bash
# Restart API (auto-loads new index)
pkill -f uvicorn  # Stop old server
uvicorn app.main:app --reload

# Test in browser
# Open: http://localhost:8000/chat
# Ask questions about nutrition, fitness, recovery
```

---

## 4. Data Quality Checklist

Before building the final index, validate:

- [ ] All documents have `id`, `title`, `text` fields
- [ ] No empty documents (minimum 100 words per doc)
- [ ] No duplicate documents
- [ ] No copyrighted material (only open-access/public domain)
- [ ] Relevant to nutrition & sports health domain
- [ ] Text is properly extracted (no garbled PDFs)
- [ ] JSONL is valid (test with `json.load()`)

**Validation Script:**
```bash
python3 << 'EOF'
import json

with open('data/nutrition_all.jsonl') as f:
    for i, line in enumerate(f):
        try:
            doc = json.loads(line)
            assert 'id' in doc and 'title' in doc and 'text' in doc
            assert len(doc['text']) > 100
        except Exception as e:
            print(f"Line {i} invalid: {e}")
            
print("✅ JSONL is valid")
EOF
```

---

## 5. Expected Results

### Document Growth
- **Current:** 8 sample documents
- **Target:** 500-1000+ documents
- **Result:** 5000-10000 chunks (after 400-word chunking)

### Knowledge Base Expansion
| Domain | Sample | Real Data | Coverage |
|--------|--------|-----------|----------|
| Protein | 1 doc | 50+ docs | Complete |
| Hydration | 1 doc | 20+ docs | Comprehensive |
| Carbs | 1 doc | 40+ docs | Deep |
| Minerals | 1 doc | 30+ docs | Thorough |
| Recovery | 1 doc | 60+ docs | Extensive |
| Supplements | 1 doc | 80+ docs | Very comprehensive |
| Weight mgmt | 1 doc | 50+ docs | Complete |
| Exercise | 0 docs | 150+ docs | **New domain** |

### Performance Impact
- **Query Speed:** Still ~100ms (FAISS is efficient)
- **Relevance:** Much higher (more data = better retrieval)
- **Coverage:** 50x more documents to search
- **Reliability:** Scientific sources instead of synthetic data

---

## 6. Licensing & Attribution

✅ **All recommended sources are free to use:**
- PMCOA: Public domain / Open access
- USDA: Public domain (US government)
- CDC/NIH: Public domain (US government)
- OpenStax: Creative Commons BY
- LibreTexts: Creative Commons
- ACE fact sheets: Free educational use

**Attribution:** Add a `SOURCES.md` file:
```markdown
## Data Sources

This knowledge base includes content from:
- PubMed Central Open Access (~X documents)
- USDA FoodData Central (~X documents)
- CDC/NIH Guidelines (~X documents)
- OpenStax Biology Textbook (~X documents)
- International Society of Sports Nutrition (~X documents)

All sources are open access and free to use.
```

---

## 7. Optional: Fine-Tune Embeddings (Advanced)

If you want even better retrieval after adding real data:

```bash
# Train domain-specific embeddings on your nutrition corpus
# This would improve semantic understanding of nutrition terms

# Library: sentence-transformers
pip install sentence-transformers

# Example (from ST documentation):
from sentence_transformers import SentenceTransformer, InputExample, losses
from sentence_transformers.evaluation import InformationRetrievalEvaluator

model = SentenceTransformer('all-MiniLM-L6-v2')
# Fine-tune on nutrition domain...
model.fit(train_objectives=[(train_dataloader, train_loss)], 
          evaluator=evaluator, 
          epochs=1, 
          evaluation_steps=500)
model.save('models/nutrition-embeddings')
```

**Note:** Optional – default model is already very good. Skip if time-constrained.

---

## 8. Timeline & Effort Estimate

| Task | Timeline | Effort | Notes |
|------|----------|--------|-------|
| Download PMCOA (100 papers) | 2-3 hours | Low | Script or automated fetch |
| Download USDA data | 1 hour | Low | CSV export, mostly automated |
| Download gov/NHS docs | 2-3 hours | Medium | Web scraping + PDF extraction |
| Download textbooks | 2-3 hours | Medium | Manual + Python extraction |
| Convert all to JSONL | 2-3 hours | Medium | Use processor.py templates |
| Validate JSONL quality | 1 hour | Low | Run validation script |
| Build FAISS index | 10-15 min | Low | Automated build |
| Test with real queries | 30 min | Low | Try in chat UI |
| **Total** | **1-2 weeks** | **Medium** | Mostly automated |

---

## 9. Quick Start Command

Once you've collected documents:

```bash
# Convert all raw documents to JSONL (manually or with collector.py)
find data/raw_sources -name "*.pdf" -o -name "*.html" | xargs python3 ingest/processor.py convert

# Build single combined JSONL
cat data/raw_sources/*/*.jsonl > data/nutrition_real.jsonl

# Build index
python3 -m ingest.build_index --jsonl data/nutrition_real.jsonl --out data/index

# Restart API
uvicorn app.main:app --reload

# Done! Try: http://localhost:8000/chat
```

---

## 10. Success Criteria

- [ ] 500+ documents collected
- [ ] All converted to valid JSONL
- [ ] Index builds without errors
- [ ] Query returns relevant results
- [ ] Chat UI feels knowledgeable
- [ ] API performance still <200ms

**When complete:** You have a production-grade knowledge base. Ready to deploy to Hugging Face Spaces.

---

## Resources & References

- **INGESTION.md** – Detailed data source guide (300+ lines)
- **ingest/collector.py** – Sample collection templates
- **ingest/processor.py** – JSONL conversion utilities
- **README.md** – Full system documentation

---

**Next:** Once real data is added, proceed to Phase 2 deployment (HF Spaces) and Projects B & C.
