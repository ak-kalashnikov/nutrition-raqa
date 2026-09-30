"""API-first research fetch (Semantic Scholar, arXiv, PubMed) — no arbitrary web scraping."""

from __future__ import annotations

import logging
import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

import requests

logger = logging.getLogger("nutrition-raqa.research")

S2_HEADERS = {"Accept": "application/json"}


def _chunk_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    text = " ".join((text or "").split())
    if len(text) <= max_chars:
        return [text] if text else []
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + max_chars])
        i += max_chars - overlap
    return chunks


def fetch_semantic_scholar(query: str, limit: int = 5) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    q = urllib.parse.quote(query)
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={q}&limit={limit}&fields=title,abstract,year,externalIds,openAccessPdf,url"
    try:
        r = requests.get(url, headers=S2_HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("Semantic Scholar request failed: %s", e)
        return out
    for paper in data.get("data") or []:
        pid = paper.get("paperId") or ""
        title = paper.get("title") or "Untitled"
        abstract = paper.get("abstract") or ""
        if not abstract:
            continue
        ext = paper.get("externalIds") or {}
        doi = ext.get("DOI")
        ext_id = f"s2:{pid}" if pid else f"doi:{doi}" if doi else f"title:{hash(title)}"
        url_pub = paper.get("url") or ""
        for ci, chunk in enumerate(_chunk_text(abstract)):
            out.append(
                {
                    "id": f"{ext_id}-a{ci}",
                    "title": title,
                    "text": chunk,
                    "source_url": url_pub,
                    "license": "Semantic Scholar metadata (see S2 terms)",
                    "external_id": ext_id,
                }
            )
    return out


def fetch_arxiv(query: str, limit: int = 3) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    q = urllib.parse.quote(f"all:{query}")
    url = f"http://export.arxiv.org/api/query?search_query={q}&start=0&max_results={limit}"
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        logger.warning("arXiv request failed: %s", e)
        return out
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for ent in root.findall("atom:entry", ns):
        title_el = ent.find("atom:title", ns)
        summ_el = ent.find("atom:summary", ns)
        id_el = ent.find("atom:id", ns)
        title = (title_el.text or "").strip().replace("\n", " ")
        summary = (summ_el.text or "").strip().replace("\n", " ") if summ_el is not None else ""
        aid = (id_el.text or "").strip() if id_el is not None else ""
        if not summary:
            continue
        ext_id = aid or f"arxiv:{hash(title)}"
        for ci, chunk in enumerate(_chunk_text(summary)):
            out.append(
                {
                    "id": f"{ext_id}-s{ci}",
                    "title": title or "arXiv entry",
                    "text": chunk,
                    "source_url": aid,
                    "license": "arXiv metadata (check paper license for reuse)",
                    "external_id": ext_id,
                }
            )
    return out


def fetch_pubmed(query: str, limit: int = 5) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    try:
        es = requests.get(
            f"{base}/esearch.fcgi",
            params={"db": "pubmed", "term": query, "retmax": limit, "retmode": "json"},
            timeout=20,
        )
        es.raise_for_status()
        ids = es.json().get("esearchresult", {}).get("idlist") or []
        if not ids:
            return out
        time.sleep(0.35)
        ef = requests.get(
            f"{base}/efetch.fcgi",
            params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"},
            timeout=30,
        )
        ef.raise_for_status()
        root = ET.fromstring(ef.content)
    except Exception as e:
        logger.warning("PubMed request failed: %s", e)
        return out

    def _tag_local(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    for article in root.iter():
        if _tag_local(article.tag) != "PubmedArticle":
            continue
        pmid = ""
        title = ""
        abs_parts: list[str] = []
        for el in article.iter():
            loc = _tag_local(el.tag)
            txt = (el.text or "").strip()
            if loc == "PMID" and txt and not pmid:
                pmid = txt
            elif loc == "ArticleTitle" and txt and not title:
                title = txt
            elif loc == "AbstractText" and txt:
                label = el.attrib.get("Label")
                if label:
                    abs_parts.append(f"{label}: {txt}")
                else:
                    abs_parts.append(txt)
        abstract = " ".join(abs_parts)
        if not abstract:
            continue
        ext_id = f"pubmed:{pmid}" if pmid else f"pubmed:{hash(title)}"
        for ci, chunk in enumerate(_chunk_text(abstract)):
            out.append(
                {
                    "id": f"{ext_id}-a{ci}",
                    "title": title or f"PubMed {pmid}",
                    "text": chunk,
                    "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                    "license": "PubMed abstract (NIH)",
                    "external_id": ext_id,
                }
            )
    return out


def combined_research_chunks(
    query: str,
    s2_limit: int,
    arxiv_limit: int,
    pubmed_limit: int,
    max_total: int,
) -> list[dict[str, Any]]:
    """Return deduplicated chunk dicts ready for indexing."""
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    s2 = fetch_semantic_scholar(query, s2_limit)
    time.sleep(3.0)
    for row in s2:
        key = row.get("id") or row.get("external_id")
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(row)
        if len(merged) >= max_total:
            return merged
    for batch in (fetch_arxiv(query, arxiv_limit), fetch_pubmed(query, pubmed_limit)):
        for row in batch:
            key = row.get("id") or row.get("external_id")
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(row)
            if len(merged) >= max_total:
                return merged
    return merged
