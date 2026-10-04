import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings with sensible defaults for local and prod."""

    # API
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    # Groq / LLM
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    default_llm_id: str | None = os.getenv("DEFAULT_LLM_ID")

    # Hugging Face Hub (index persistence + optional Inference API)
    hf_token: str | None = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    index_hf_repo_id: str | None = os.getenv("INDEX_HF_REPO_ID")
    index_hf_path: str = os.getenv("INDEX_HF_PATH", "latest")
    hub_upload_debounce_seconds: float = float(os.getenv("HUB_UPLOAD_DEBOUNCE_SECONDS", "90"))

    # Google Gemini (optional)
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")

    # Retrieval / RAG
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    relevance_threshold: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.4"))
    default_k: int = int(os.getenv("TOP_K", "3"))

    # Research ingest is off on the request path. A user question must not
    # append chunks or upload the index. An explicit offline build may opt in.
    research_fallback_enabled: bool = os.getenv("RESEARCH_FALLBACK_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    research_max_chunks_per_query: int = int(os.getenv("RESEARCH_MAX_CHUNKS_PER_QUERY", "12"))
    research_global_per_hour: int = int(os.getenv("RESEARCH_GLOBAL_PER_HOUR", "40"))
    research_s2_limit: int = int(os.getenv("RESEARCH_S2_LIMIT", "5"))
    research_arxiv_limit: int = int(os.getenv("RESEARCH_ARXIV_LIMIT", "3"))
    research_pubmed_limit: int = int(os.getenv("RESEARCH_PUBMED_LIMIT", "5"))

    # Extra JSONL merged at startup when no Hub index (optional)
    extra_corpus_jsonl: str | None = os.getenv(
        "EXTRA_CORPUS_JSONL",
        "data/open_textbook_chunks.jsonl,data/pressbooks_chapters.jsonl",
    )

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
