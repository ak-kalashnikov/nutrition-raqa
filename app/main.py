from typing import List
import asyncio
import os
import json
import logging
import time
import threading
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, RedirectResponse
from pydantic import BaseModel
from groq import Groq

from app.retriever import Retriever
from app.config import get_settings
from app import hub_index_store
from app.hub_upload_scheduler import schedule_hub_index_upload
from app.research_fetch import combined_research_chunks
from app.llm_router import LLMRouter

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("nutrition-raqa")

app = FastAPI(title="RAQA - Nutrition & Sports Health")


class QueryRequest(BaseModel):
    question: str
    k: int = settings.default_k
    llm_id: str | None = None


retriever: Retriever | None = None
groq_client = None
llm_router: LLMRouter | None = None
_index_paths: Dict[str, str] = {}

# Simple in-memory rate limiting (per IP)
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "30"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
_request_log: Dict[str, Deque[float]] = defaultdict(deque)

# Research API global throttle (all IPs)
_research_lock = threading.Lock()
_research_events: Deque[float] = deque()

# Interval for SSE comment pings while waiting on the LLM (avoids proxy idle timeouts)
SSE_KEEPALIVE_SECONDS = float(os.getenv("SSE_KEEPALIVE_SECONDS", "15"))


def _is_high_risk_query(text: str) -> bool:
    """Very lightweight safety filter for emergencies / self-harm / acute issues."""
    t = text.lower()
    high_risk_keywords = [
        "suicide",
        "kill myself",
        "self harm",
        "overdose",
        "emergency",
        "severe chest pain",
        "heart attack",
        "can't breathe",
        "cannot breathe",
    ]
    return any(kw in t for kw in high_risk_keywords)


def _research_rate_allow() -> bool:
    now = time.time()
    window = 3600.0
    cap = settings.research_global_per_hour
    with _research_lock:
        while _research_events and now - _research_events[0] > window:
            _research_events.popleft()
        if len(_research_events) >= cap:
            return False
        _research_events.append(now)
        return True


NOT_IN_DOCUMENTS = (
    "I can't answer that from the nutrition documents in this index. "
    "The closest passage scored below the relevance threshold, so this reply "
    "is not a generated answer."
)


def _maybe_expand_kb_from_research(question: str) -> None:
    """Offline helper only. Request handlers must not call this.

    When explicitly invoked by a build command, and when
    ``research_fallback_enabled`` is true, fetch abstracts, append them, and
    schedule a Hub upload. A chat question must not reach this function.
    """
    global retriever
    if retriever is None or not settings.research_fallback_enabled:
        return
    if not _research_rate_allow():
        logger.info("Research fallback skipped (global hourly cap)")
        return
    idx_path = _index_paths.get("index_path")
    meta_path = _index_paths.get("meta_path")
    if not idx_path or not meta_path:
        return
    try:
        chunks = combined_research_chunks(
            question,
            settings.research_s2_limit,
            settings.research_arxiv_limit,
            settings.research_pubmed_limit,
            settings.research_max_chunks_per_query,
        )
        if not chunks:
            return
        added = retriever.append_chunks(chunks)
        if added <= 0:
            return
        retriever.save_index_to_disk(idx_path, meta_path)
        logger.info("Research ingest added %s chunks; scheduling Hub upload", added)

        def _upload():
            rid = settings.index_hf_repo_id
            tok = settings.hf_token
            if not rid or not tok:
                return
            hub_index_store.upload_index_snapshot(
                rid,
                settings.index_hf_path,
                idx_path,
                meta_path,
                tok,
                extra_manifest={"source": "runtime_research_ingest"},
            )

        schedule_hub_index_upload(settings.hub_upload_debounce_seconds, _upload)
    except Exception as e:
        logger.warning("Research ingest failed: %s", e)


@app.middleware("http")
async def no_cache_ui(request: Request, call_next):
    response = await call_next(request)
    if request.url.path in {"/", "/chat"} or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    dq = _request_log[client_ip]

    while dq and now - dq[0] > RATE_LIMIT_WINDOW_SECONDS:
        dq.popleft()

    if len(dq) >= RATE_LIMIT_MAX_REQUESTS:
        logger.warning("Rate limit exceeded for IP %s", client_ip)
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down and try again shortly."},
        )

    dq.append(now)
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup_event():
    global retriever, groq_client, llm_router, _index_paths
    base_dir = os.path.dirname(__file__)
    index_dir = os.path.join(base_dir, "..", "data", "index")
    index_path = os.path.join(index_dir, "faiss.index")
    meta_path = os.path.join(index_dir, "meta.jsonl")
    data_file = os.path.join(base_dir, "..", "data", "nutrition_qa.jsonl")
    _index_paths = {"index_dir": index_dir, "index_path": index_path, "meta_path": meta_path}

    os.makedirs(index_dir, exist_ok=True)

    if settings.index_hf_repo_id and settings.hf_token:
        if hub_index_store.try_download_index(
            settings.index_hf_repo_id,
            settings.index_hf_path,
            index_dir,
            settings.hf_token,
        ):
            logger.info("Loaded FAISS index files from Hub repo %s", settings.index_hf_repo_id)

    groq_api_key = settings.groq_api_key
    if not groq_api_key:
        logger.warning(
            "GROQ_API_KEY not set — Groq models disabled unless other providers are configured."
        )
        groq_client = None
    else:
        groq_client = Groq(api_key=groq_api_key)

    default_llm = settings.default_llm_id or f"groq:{settings.groq_model}"
    llm_router = LLMRouter(
        groq_client=groq_client,
        hf_token=settings.hf_token,
        gemini_key=settings.gemini_api_key,
        default_llm_id=default_llm,
    )
    if not llm_router.list_options():
        logger.warning(
            "No LLM providers available — set GROQ_API_KEY, HF_TOKEN, and/or GEMINI_API_KEY."
        )

    retriever = Retriever(model_name=settings.embedding_model)

    if os.path.exists(index_path) and os.path.exists(meta_path):
        retriever.load_index_from_disk(index_path, meta_path)
        logger.info("Loaded FAISS index from disk (%s)", meta_path)
    else:
        paths: List[str] = [data_file]
        extra = settings.extra_corpus_jsonl or ""
        for part in extra.split(","):
            part = part.strip()
            if not part:
                continue
            extra_abs = part if os.path.isabs(part) else os.path.join(base_dir, "..", part)
            if os.path.isfile(extra_abs):
                paths.append(extra_abs)
        retriever.load_documents_many(paths)
        retriever.build_index()
        logger.info("Built FAISS index from %s", paths)
        try:
            retriever.save_index_to_disk(index_path, meta_path)
        except OSError as e:
            logger.warning("Could not persist initial index to disk: %s", e)


def _build_query_result(req: QueryRequest) -> dict:
    """Synchronous RAG + LLM pipeline; used by /query and /query/stream."""
    if retriever is None or llm_router is None:
        return {
            "question": req.question,
            "answer": None,
            "sources": [],
            "source_count": 0,
            "error": "Service not fully initialized.",
        }

    if _is_high_risk_query(req.question):
        logger.info("High-risk query detected; returning safety response")
        return {
            "question": req.question,
            "answer": (
                "I’m not able to help with emergencies or serious crises. "
                "If you or someone else may be in danger, please contact your local "
                "emergency number or a qualified health professional immediately."
            ),
            "sources": [],
            "source_count": 0,
        }

    greetings = ["hi", "hello", "hey", "sup", "what's up", "howdy"]
    question_lower = req.question.lower().strip()

    if question_lower in greetings or (
        question_lower.endswith("?") is False and len(question_lower) < 5
    ):
        return {
            "question": req.question,
            "answer": "Hi there! 👋 I'm a nutrition and sports health expert. Ask me anything about protein, training, recovery, supplements, hydration, diet plans, or sports performance!",
            "sources": [],
            "source_count": 0,
        }

    retrieved_docs = retriever.retrieve(req.question, k=req.k)
    relevance_threshold = settings.relevance_threshold
    top_score = retrieved_docs[0].get("score", 0) if retrieved_docs else 0
    has_relevant_docs = bool(retrieved_docs) and top_score >= relevance_threshold

    if not has_relevant_docs:
        logger.info(
            "Abstaining: top score %.3f is below threshold %.3f",
            top_score,
            relevance_threshold,
        )
        return {
            "question": req.question,
            "answer": NOT_IN_DOCUMENTS,
            "sources": [],
            "source_count": 0,
            "abstained": True,
            "top_score": top_score,
        }

    if not llm_router.list_options():
        return {
            "question": req.question,
            "answer": None,
            "sources": retrieved_docs,
            "source_count": len(retrieved_docs),
            "error": "No model is enabled on this server yet.",
        }

    try:
        context = "\n\n".join(
            [
                f"📄 {doc.get('title', 'Unknown')}\n{doc.get('text', '')}"
                for doc in retrieved_docs
            ]
        )
        messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a nutrition and sports health expert. "
                        "Use ONLY the information in the provided documents to answer. "
                        "If something is not clearly supported by the documents, say that you "
                        "cannot be certain rather than guessing. "
                        "Your answers are for general educational purposes only and do not "
                        "constitute medical or nutritional advice. "
                        "Do NOT diagnose conditions, prescribe medications, or provide "
                        "personalized treatment plans. Encourage users to consult a licensed "
                        "health professional for medical decisions."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""Based on these nutrition and sports health documents:

{context}

Answer this question comprehensively and in detail:
{req.question}

Provide a thorough answer that synthesizes information from the documents, explains concepts clearly, and gives practical recommendations.""",
                },
            ]
        generated_answer = llm_router.complete(
            messages, req.llm_id, temperature=0.7, max_tokens=1000
        )
        return {
            "question": req.question,
            "answer": generated_answer,
            "sources": retrieved_docs,
            "source_count": len(retrieved_docs),
            "abstained": False,
        }

    except Exception as e:
        error_msg = str(e)
        logger.exception("Error while handling /query: %s", error_msg)
        low = error_msg.lower()
        if "api key" in low or "auth" in low or "401" in low:
            error_msg = "LLM API authentication failed — check your API keys in Space secrets."
        elif "rate" in low or "429" in low:
            error_msg = "LLM rate limit — please wait and try again."

        return {
            "question": req.question,
            "answer": None,
            "sources": retrieved_docs if retrieved_docs else [],
            "source_count": len(retrieved_docs) if retrieved_docs else 0,
            "error": f"Error: {error_msg}",
        }


@app.get("/llm/options")
async def llm_options():
    if llm_router is None:
        return {"options": [], "default": None}
    return {
        "options": llm_router.catalog(),
        "default": llm_router.resolve_default(),
    }


@app.post("/query")
async def query(req: QueryRequest):
    if retriever is None:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    return _build_query_result(req)


@app.post("/query/stream")
async def query_stream(req: QueryRequest):
    """
    Same payload as /query, delivered as one terminal SSE `data:` event.
    While the LLM runs in a worker thread, sends periodic SSE comment lines
    (`: keepalive`) so proxies and load balancers do not treat the connection as idle.
    """
    if retriever is None:
        raise HTTPException(status_code=503, detail="Retriever not initialized")

    async def event_gen():
        task = asyncio.create_task(asyncio.to_thread(_build_query_result, req))
        try:
            while not task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=SSE_KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    if not task.done():
                        yield ": keepalive\n\n"
                except Exception:
                    break
            try:
                payload = task.result()
            except Exception as e:
                logger.exception("Unexpected error in /query/stream worker: %s", e)
                payload = {
                    "question": req.question,
                    "answer": None,
                    "sources": [],
                    "source_count": 0,
                    "error": f"Error: {e!s}",
                }
            yield f"data: {json.dumps(payload)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    opts = llm_router.list_options() if llm_router else []
    idx_disk = bool(
        _index_paths.get("index_path") and os.path.isfile(_index_paths["index_path"])
    )
    return {
        "status": "ok",
        "retriever_initialized": retriever is not None,
        "index_type": "disk" if idx_disk else "memory",
        "groq_available": groq_client is not None,
        "hf_token_configured": bool(settings.hf_token),
        "gemini_configured": bool(settings.gemini_api_key),
        "hub_index_repo": settings.index_hf_repo_id,
        "llm_options_count": len(opts),
    }


static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/chat")
async def chat_ui():
    html_path = os.path.join(static_dir, "chat.html")
    return FileResponse(html_path)


@app.get("/")
async def root():
    return RedirectResponse(url="/chat")
