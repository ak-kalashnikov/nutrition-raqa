"""
ingest.collector

Scaffold for collecting open-access corpora for nutrition, sports, and health.
This file contains functions to download and extract text from permissive/open sources.

Important: Always check licensing and robots.txt before harvesting content.

Planned sources (open / free to use):
- PubMed Central Open Access Subset (PMCOA)
- Government nutrition guidelines (USDA, NHS, WHO) — public domain or permissive
- Open textbooks and review articles (open access journals)
- Public PDF reports from academic societies (when explicitly allowed)

This module is a scaffold only (no scraping executed automatically). Use it
as a safe, documented starting point for ingestion pipelines.
"""
from pathlib import Path
import logging
import requests
from typing import Iterable

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_text(id: str, text: str) -> Path:
    """Save extracted text to `data/raw/{id}.txt` and return path."""
    p = DATA_DIR / f"{id}.txt"
    p.write_text(text, encoding="utf-8")
    return p


def fetch_url_text(url: str) -> str:
    """Fetch a URL and return cleaned text.

    Note: This is a very simple fetch helper. For HTML->text conversion use
    `beautifulsoup4` or `readability-lxml` and respect robots.txt.
    """
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    # Minimal cleaning — caller should parse HTML properly.
    return resp.text


def collect_gov_guideline(urls: Iterable[str]):
    """Download a list of government guideline pages (USDA, NHS, WHO).

    These sites often permit redistribution of their guidance — still verify per-page licensing.
    This function stores raw HTML; parsing and chunking happen later.
    """
    for i, url in enumerate(urls, 1):
        try:
            text = fetch_url_text(url)
            save_text(f"gov_{i}", text)
            logger.info("Saved %s", url)
        except Exception as e:
            logger.exception("Failed to fetch %s: %s", url, e)


def collect_pmcoa_sample(query: str = "nutrition", max_items: int = 50):
    """Placeholder for collecting PMCOA articles using Entrez / Europe PMC APIs.

    Implementation notes:
    - Use Europe PMC or NCBI E-utilities to search for open-access articles.
    - Download full-text XML or PDF when OA license allows.
    - Extract article sections (abstract, methods, results) for indexing.
    - Respect rate limits and store provenance metadata (PMCID, DOI, license).
    """
    # This is an explicit placeholder. Do not run heavy scraping here.
    logger.info("PMCOA collection placeholder for query=%s", query)


def collect_open_textbook(urls: Iterable[str]):
    """Download public-domain or openly licensed textbook chapters.

    Example: government publications or books under Creative Commons.
    """
    for i, url in enumerate(urls, 1):
        try:
            html = fetch_url_text(url)
            save_text(f"book_{i}", html)
        except Exception as e:
            logger.exception("Failed to fetch textbook %s: %s", url, e)


if __name__ == "__main__":
    # Example usage (no-op safe examples):
    # collect_gov_guideline(["https://www.nhs.uk/live-well/eat-well/"])
    print("Ingest collector scaffold — edit before using.")
