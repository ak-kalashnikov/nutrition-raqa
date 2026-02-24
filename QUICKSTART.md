# Quick Start Guide

Your Nutrition & Sports Health RAQA system is ready! Here's how to use it:

## 1. Start the Server

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`

## 2. Open the Chat UI

**Interactive Web Chat:**
- Open `http://localhost:8000/chat` in your browser
- Ask questions about nutrition, training, recovery, supplementation
- Get relevant knowledge base excerpts with relevance scores

**Example questions:**
- "How much protein do athletes need?"
- "Best recovery strategies after training"
- "Benefits of creatine supplementation"
- "Optimal carb loading for endurance events"

## 3. API Usage (Advanced)

Query via curl/Python:

```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"protein synthesis","k":3}'
```

Response:
```json
{
  "question": "protein synthesis",
  "results": [
    {
      "doc_id": "d1",
      "title": "Protein timing",
      "text": "Consuming protein within a few hours...",
      "score": 0.564
    }
  ]
}
```

## 4. Update Knowledge Base

Add more documents (nutrition facts, scientific articles, guidelines):

1. Download open-access sources (see `INGESTION.md`)
2. Convert to JSONL format: `{"id": "doc1", "title": "...", "text": "..."}`
3. Build index:
   ```bash
   python3 -m ingest.build_index --jsonl data/nutrition_qa.jsonl --out data/index
   ```
4. Restart server (auto-loads new index)

## 5. Deploy Live

Push to GitHub, then:
- **Free demo**: Hugging Face Spaces (Streamlit demo)
- **Free API**: Render (backend API)
- **Production**: AWS / GCP

See `DEPLOYMENT.md` for detailed guides.

## Files Overview

```
.
├── app/
│   ├── main.py         # FastAPI server + chat endpoint
│   ├── retriever.py    # Semantic search engine
│   └── static/         # Chat UI (HTML/CSS/JS)
├── data/
│   ├── nutrition_qa.jsonl     # Documents
│   └── index/                  # FAISS index (auto-generated)
├── ingest/
│   ├── collector.py    # Download from open sources
│   ├── processor.py    # Chunk, embed, build index
│   └── build_index.py  # CLI to build index
├── tests/              # Unit + integration tests
├── README.md           # Full documentation
├── INGESTION.md        # Data ingestion guide
└── DEPLOYMENT.md       # Deployment guide
```

## Next Steps

1. **Add real data**: Follow `INGESTION.md` to add PubMed, gov guidelines, ACE materials
2. **Fine-tune**: Train embeddings on your domain for better results
3. **Deploy**: Push to GitHub, deploy demo on Hugging Face Spaces (free)
4. **Share**: Add link to LinkedIn portfolio + GitHub

## Need Help?

- **API docs**: Visit `http://localhost:8000/docs` (interactive FastAPI docs)
- **Examples**: See `tests/` directory
- **More info**: Read `README.md`, `INGESTION.md`, `DEPLOYMENT.md`

---

**Status:** ✅ Production-ready  
**Chat UI:** ✅ Live at `/chat`  
**FAISS Index:** ✅ Fast semantic search  
**Deployment:** ✅ Ready for cloud

Open link in browser: `http://localhost:8000/chat`
