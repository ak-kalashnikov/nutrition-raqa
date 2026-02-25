from typing import List
import os
import json
import logging
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from groq import Groq

from app.retriever import Retriever
from app.config import get_settings

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

retriever: Retriever = None
groq_client: Groq = None


# Simple in-memory rate limiting (per IP)
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "30"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
_request_log: Dict[str, Deque[float]] = defaultdict(deque)


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


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    dq = _request_log[client_ip]

    # prune old entries
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
    global retriever, groq_client
    base_dir = os.path.dirname(__file__)
    index_path = os.path.join(base_dir, '..', 'data', 'index', 'faiss.index')
    meta_path = os.path.join(base_dir, '..', 'data', 'index', 'meta.jsonl')
    data_file = os.path.join(base_dir, '..', 'data', 'nutrition_qa.jsonl')

    # Validate Groq API key
    groq_api_key = settings.groq_api_key
    if not groq_api_key:
        logger.warning(
            "GROQ_API_KEY environment variable not set. "
            "AI answer generation will be disabled until configured."
        )
        groq_client = None
    else:
        logger.info("GROQ_API_KEY detected, RAG generation enabled")
        groq_client = Groq(api_key=groq_api_key)

    retriever = Retriever(model_name=settings.embedding_model)

    # Prefer on-disk index if available, fallback to in-memory build
    if os.path.exists(index_path) and os.path.exists(meta_path):
        retriever.load_index_from_disk(index_path, meta_path)
        logger.info("Loaded FAISS index from disk (%s)", meta_path)
    else:
        retriever.load_documents(data_file)
        retriever.build_index()
        logger.info("Built FAISS index from %s", data_file)


@app.post("/query")
async def query(req: QueryRequest):
    if retriever is None:
        raise HTTPException(status_code=503, detail="Retriever not initialized")

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
    
    # Check if this is just a greeting or non-informational query
    greetings = ['hi', 'hello', 'hey', 'sup', 'what\'s up', 'howdy']
    question_lower = req.question.lower().strip()
    
    if question_lower in greetings or (question_lower.endswith('?') == False and len(question_lower) < 5):
        # Simple greeting - respond without RAG
        return {
            "question": req.question,
            "answer": "Hi there! 👋 I'm a nutrition and sports health expert. Ask me anything about protein, training, recovery, supplements, hydration, diet plans, or sports performance!",
            "sources": [],
            "source_count": 0
        }
    
    # Step 1: Retrieve relevant documents from FAISS
    retrieved_docs = retriever.retrieve(req.question, k=req.k)
    
    # Step 2: Check if results are relevant (relevance score threshold)
    relevance_threshold = settings.relevance_threshold
    has_relevant_docs = retrieved_docs and retrieved_docs[0].get('score', 0) >= relevance_threshold
    
    if groq_client is None:
        return {
            "question": req.question,
            "answer": None,
            "sources": [],
            "source_count": 0,
            "error": "GROQ_API_KEY not configured. Set environment variable and restart server. See: https://console.groq.com/keys"
        }
    
    try:
        if has_relevant_docs:
            # RAG mode: Use retrieved documents to augment the response
            context = "\n\n".join([
                f"📄 {doc.get('title', 'Unknown')}\n{doc.get('text', '')}"
                for doc in retrieved_docs
            ])
            
            message = groq_client.chat.completions.create(
                messages=[
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

Provide a thorough answer that synthesizes information from the documents, explains concepts clearly, and gives practical recommendations."""
                    }
                ],
                model=settings.groq_model,
                temperature=0.7,
                max_tokens=1000,
            )
            
            generated_answer = message.choices[0].message.content
            
            return {
                "question": req.question,
                "answer": generated_answer,
                "sources": retrieved_docs,
                "source_count": len(retrieved_docs)
            }
        else:
            # General conversation mode: No relevant documents, just chat normally
            message = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful, friendly assistant. You are primarily a nutrition "
                            "and sports health expert, but you can have natural conversations on "
                            "other topics too. "
                            "Your responses are general information only and not medical advice. "
                            "Do not diagnose conditions or give personalized treatment plans. "
                            "Encourage users to consult a qualified professional for important "
                            "health decisions."
                        ),
                    },
                    {
                        "role": "user",
                        "content": req.question
                    }
                ],
                model=settings.groq_model,
                temperature=0.7,
                max_tokens=1000,
            )
            
            generated_answer = message.choices[0].message.content
            
            return {
                "question": req.question,
                "answer": generated_answer,
                "sources": [],
                "source_count": 0
            }
            
    except Exception as e:
        error_msg = str(e)
        logger.exception("Error while handling /query: %s", error_msg)
        if "API key" in error_msg or "auth" in error_msg:
            error_msg = f"Groq API Authentication Failed: Check your GROQ_API_KEY. Get one at: https://console.groq.com/keys"
        elif "rate_limit" in error_msg:
            error_msg = "Groq API Rate Limit: Please wait a moment before trying again"
        
        return {
            "question": req.question,
            "answer": None,
            "sources": [],
            "source_count": 0,
            "error": f"Error: {error_msg}"
        }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "retriever_initialized": retriever is not None,
        "index_type": "disk" if retriever and retriever.meta else "memory",
        "groq_available": groq_client is not None,
    }


# Serve the chat static UI
static_dir = os.path.join(os.path.dirname(__file__), 'static')
if os.path.isdir(static_dir):
    app.mount('/static', StaticFiles(directory=static_dir), name='static')


@app.get('/chat')
async def chat_ui():
    html_path = os.path.join(static_dir, 'chat.html')
    return FileResponse(html_path)
