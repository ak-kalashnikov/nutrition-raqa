"""
ingest.processor

Functions to parse source documents, chunk text, encode with sentence-transformers,
and build/save a FAISS index with document metadata.

This is a conservative, easy-to-run implementation for local use.
"""
from pathlib import Path
import json
from typing import List, Dict

from sentence_transformers import SentenceTransformer
import faiss


def load_jsonl(path: Path) -> List[Dict]:
    docs = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            docs.append(json.loads(line))
    return docs


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i+chunk_size]
        chunks.append(' '.join(chunk))
        i += chunk_size - overlap
    return chunks


def embed_texts(texts: List[str], model_name: str = 'all-MiniLM-L6-v2'):
    encoder = SentenceTransformer(model_name)
    embs = encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return embs


def build_faiss_index(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def save_index(index, path: Path):
    faiss.write_index(index, str(path))


def save_metadata(rows: List[Dict], path: Path):
    with open(path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def build_from_jsonl(jsonl_path: Path, out_dir: Path, model_name: str = 'all-MiniLM-L6-v2'):
    out_dir.mkdir(parents=True, exist_ok=True)
    docs = load_jsonl(jsonl_path)
    texts = []
    meta = []
    for d in docs:
        doc_id = d.get('id') or d.get('doc_id') or f"doc_{len(meta)}"
        title = d.get('title','')
        text = d.get('text','')
        chunks = chunk_text(text)
        for i, c in enumerate(chunks):
            texts.append(c)
            meta.append({'doc_id': doc_id, 'title': title, 'chunk': i, 'text': c})

    embeddings = embed_texts(texts, model_name=model_name)
    index = build_faiss_index(embeddings)
    save_index(index, out_dir / 'faiss.index')
    save_metadata(meta, out_dir / 'meta.jsonl')
    return out_dir / 'faiss.index', out_dir / 'meta.jsonl'


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--jsonl', required=True, help='Input JSONL file with id,title,text')
    p.add_argument('--out', default='data/index', help='Output directory for index and metadata')
    p.add_argument('--model', default='all-MiniLM-L6-v2')
    args = p.parse_args()
    print('Building index... this may take a while on first run')
    build_from_jsonl(Path(args.jsonl), Path(args.out), model_name=args.model)
    print('Done')
