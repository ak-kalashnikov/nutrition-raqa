from typing import List
import os
import json

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import Groq

from app.retriever import Retriever

app = FastAPI(title="RAQA - Nutrition & Sports Health")

class QueryRequest(BaseModel):
    question: str
    k: int = 3

retriever: Retriever = None
groq_client: Groq = None


@app.on_event("startup")
async def startup_event():
    global retriever, groq_client
    base_dir = os.path.dirname(__file__)
    index_path = os.path.join(base_dir, '..', 'data', 'index', 'faiss.index')
    meta_path = os.path.join(base_dir, '..', 'data', 'index', 'meta.jsonl')
    data_file = os.path.join(base_dir, '..', 'data', 'nutrition_qa.jsonl')

    # Validate Groq API key
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("⚠️  WARNING: GROQ_API_KEY environment variable not set!")
        print("   To enable AI answer generation, set: export GROQ_API_KEY='your_key_here'")
        print("   Get a free key from: https://console.groq.com/keys")
        groq_client = None
    else:
        print("✓ GROQ_API_KEY detected, RAG generation enabled")
        groq_client = Groq(api_key=groq_api_key)

    retriever = Retriever()

    # Prefer on-disk index if available, fallback to in-memory build
    if os.path.exists(index_path) and os.path.exists(meta_path):
        retriever.load_index_from_disk(index_path, meta_path)
        print(f"✓ Loaded FAISS index from disk ({meta_path})")
    else:
        retriever.load_documents(data_file)
        retriever.build_index()
        print(f"✓ Built FAISS index from {data_file}")


@app.post("/query")
async def query(req: QueryRequest):
    if retriever is None:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
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
    relevance_threshold = 0.4
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
                        "content": "You are a nutrition and sports health expert. Based on the provided documents, give a comprehensive, detailed, and practical answer. Always cite the relevant information from the documents."
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
                model="llama-3.3-70b-versatile",
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
                        "content": "You are a helpful, friendly assistant. You're aware that you're primarily a nutrition and sports health expert, but you can have natural conversations on other topics too. Keep responses concise and conversational."
                    },
                    {
                        "role": "user",
                        "content": req.question
                    }
                ],
                model="llama-3.3-70b-versatile",
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
    return {"status": "ok"}


# Serve the chat static UI
static_dir = os.path.join(os.path.dirname(__file__), 'static')
if os.path.isdir(static_dir):
    app.mount('/static', StaticFiles(directory=static_dir), name='static')


@app.get('/chat')
async def chat_ui():
    html_path = os.path.join(static_dir, 'chat.html')
    return FileResponse(html_path)
