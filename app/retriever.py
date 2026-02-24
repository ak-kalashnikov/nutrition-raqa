import os
import json
from typing import List, Dict, Optional

from sentence_transformers import SentenceTransformer
import faiss


class Retriever:
    """Retriever with optional on-disk FAISS index and metadata.

    Usage:
      - If `index_path` and `meta_path` exist, call `load_index_from_disk`.
      - Otherwise, `load_documents(jsonl_path)` then `build_index()`.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.encoder = SentenceTransformer(self.model_name)
        self.docs: List[Dict] = []  # raw docs (one per JSONL line)
        self.meta: List[Dict] = []  # per-chunk metadata when using disk index
        self.index: Optional[faiss.Index] = None

    def load_documents(self, path: str):
        path = os.path.abspath(path)
        docs = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                docs.append(obj)
        self.docs = docs

    def build_index(self):
        """Build an in-memory FAISS index from `self.docs`.

        This creates one embedding per document (no chunking). For larger corpora,
        prefer using `ingest.processor.build_from_jsonl` which chunks and persists an index.
        """
        texts = [d.get("text", "") for d in self.docs]
        if not texts:
            raise ValueError("No documents to index")
        embeddings = self.encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
        self.index = index

    def load_index_from_disk(self, index_path: str, meta_path: str):
        """Load a FAISS index and corresponding metadata (jsonl of chunks).

        The metadata file should be JSONL where each line corresponds to an embedding
        in the FAISS index (in the same order).
        """
        if not os.path.exists(index_path):
            raise FileNotFoundError(index_path)
        if not os.path.exists(meta_path):
            raise FileNotFoundError(meta_path)
        self.index = faiss.read_index(index_path)
        meta = []
        with open(meta_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                meta.append(json.loads(line))
        self.meta = meta

    def retrieve(self, query: str, k: int = 3) -> List[Dict]:
        if self.index is None:
            raise RuntimeError("Index not built or loaded")
        q_emb = self.encoder.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        D, I = self.index.search(q_emb, k)
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx < 0:
                continue
            # If we have chunk-level metadata from disk, use it; otherwise map to docs
            if self.meta:
                if idx >= len(self.meta):
                    continue
                doc = self.meta[idx].copy()
                doc["score"] = float(score)
                results.append(doc)
            else:
                if idx >= len(self.docs):
                    continue
                doc = self.docs[idx].copy()
                doc["score"] = float(score)
                results.append(doc)
        return results
