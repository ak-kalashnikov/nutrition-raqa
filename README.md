---
title: Nutrition RAQA
emoji: 🥗
colorFrom: gray
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Educational nutrition Q&A from a textbook index
---

# Nutrition RAQA

Retrieval-augmented question answering over an open nutrition textbook, plus three short sports-nutrition notes. This repository is the continuation of the February 2026 project. The May 2026 `Nutrition_bot` code (multi-provider chat, streaming, textbook chunks, and retrieval eval) is merged here. `Nutrition_bot` is not a second product.

## What a question does

1. Embed the question with `all-MiniLM-L6-v2`.
2. Search a FAISS `IndexFlatIP` index.
3. If the top score is below `RELEVANCE_THRESHOLD` (default 0.4), return a fixed refusal. The language model is not called, and the index is not modified.
4. If the score clears the threshold and an API key is configured, `LLMRouter` answers from those passages only. Providers: Groq, Hugging Face Inference, Gemini.

Endpoints: `/health`, `/query`, `/query/stream` (one Server-Sent Event after the answer is finished), `/chat`.

## Corpus

| File | What it is |
|---|---|
| `data/nutrition_qa.jsonl` | 3 short notes (protein timing, hydration, creatine). |
| `data/open_textbook_chunks.jsonl` | 85 chunks from *Nutrition: Science and Everyday Application*. |
| `data/pressbooks_chapters.jsonl` | 190 chunks from the February corpus: chapters that were not already in the 85. Same textbook, CC BY-NC 4.0. |

The February file had 222 overlapping windows and 34 chapter titles. Chapters already present in the 85-chunk file were not copied again.

`ingest/` can build an index from JSONL. `ingest/collector.py` does not download PubMed Central; that path is a placeholder.

## Retrieval result

Run:

```bash
python eval/run_retrieval_eval.py --k 5
```

The committed log is `eval/retrieval_eval.json`, written after the 190 February chapters were added. Recall@5 is 48/52 (0.923077) with `all-MiniLM-L6-v2`. The misses are `g17`, `g29`, `g33`, and `g44`. The same 48 questions have the gold answer string inside a retrieved gold document. That number is not a score of generated answers. Adding the extra chapters lowered Recall@5 from 50/52 on the smaller corpus.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Copy `.env.example` to `.env` if you want a model. Without keys, retrieval and refusal still run; generation returns an error asking for a key.

`docker-compose.yml` serves the API on port 8000. The image command listens on 7860 for Hugging Face Spaces.

## License

Application code: MIT (`LICENSE`). Textbook text remains CC BY-NC 4.0, as stored on the chunk rows.
