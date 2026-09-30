#!/usr/bin/env python3
"""
Build data/open_textbook_chunks.jsonl from a small allowlist of open-access URLs.

Run from repo root:
  python scripts/build_open_kb_jsonl.py

Requires: requests, beautifulsoup4 (already in project requirements).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Curated open Pressbooks / similar (same domain family as build_rag_database.py).
SOURCES: list[tuple[str, str]] = [
    ("Nutrition and Health", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/1a-nutrition-and-health/"),
    ("Classification of Nutrients", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/1c-classification-of-nutrients/"),
    ("Protein in Foods and Recommendations", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/6c-protein-in-foods-and-dietary-recommendations/"),
    ("Fuel Sources for Exercise", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/10b-fuel-sources-exercise/"),
    ("Nutrient Needs of Athletes", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/10c-nutrient-needs-athletes/"),
]

CHUNK_CHARS = 900
CHUNK_OVERLAP = 120
LICENSE_NOTE = "Open Washington Pressbooks (verify license at source)"


def chunk_text(text: str) -> list[str]:
    text = " ".join(text.split())
    if len(text) <= CHUNK_CHARS:
        return [text] if text else []
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + CHUNK_CHARS])
        i += CHUNK_CHARS - CHUNK_OVERLAP
    return chunks


def fetch_text(url: str) -> str:
    r = requests.get(url, timeout=25, headers={"User-Agent": "NutritionRAQA-KBBuilder/1.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")
    content_div = soup.find("div", class_="content")
    if content_div:
        t = content_div.get_text(separator=" ", strip=True)
        if len(t) > 200:
            return " ".join(t.split())
    for tag in ("article", "main"):
        el = soup.find(tag)
        if el:
            t = el.get_text(separator=" ", strip=True)
            if len(t) > 200:
                return " ".join(t.split())
    body = soup.find("body")
    if body:
        t = body.get_text(separator=" ", strip=True)
        return " ".join(t.split())[:200000]
    return ""


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out_path = root / "data" / "open_textbook_chunks.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for title, url in SOURCES:
        try:
            text = fetch_text(url)
        except Exception as e:
            print(f"skip {title}: {e}", file=sys.stderr)
            continue
        if not text:
            continue
        h = hashlib.sha256(url.encode()).hexdigest()[:12]
        for i, chunk in enumerate(chunk_text(text)):
            rows.append(
                {
                    "id": f"open-{h}-c{i}",
                    "title": title,
                    "text": chunk,
                    "source_url": url,
                    "license": LICENSE_NOTE,
                    "external_id": f"url:{url}",
                }
            )

    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} chunks to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
