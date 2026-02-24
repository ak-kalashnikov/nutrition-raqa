#!/usr/bin/env python3
"""
Streamlit demo for Nutrition & Sports Health RAQA system.
Deploy to Hugging Face Spaces for free public access.
"""
import streamlit as st
import requests
import json
from typing import List

st.set_page_config(
    page_title="Nutrition & Sports Health QA",
    page_icon="💪",
    layout="wide"
)

# Title and description
st.title("💪 Nutrition & Sports Health Q&A")
st.markdown("""
This is a retrieval-augmented question-answering (RAQA) system that helps answer questions about nutrition and sports health based on evidence-based knowledge.

**How it works:**
1. Enter your question about nutrition or sports health
2. The system retrieves the most relevant documents from its knowledge base
3. Results are ranked by relevance score

**Domain:** Nutrition, sports performance, training, recovery, supplementation
""")

st.divider()

# Configuration
API_URL = st.sidebar.text_input(
    "API Base URL",
    value="http://localhost:8000",
    help="FastAPI server endpoint"
)

num_results = st.sidebar.slider(
    "Number of results",
    min_value=1,
    max_value=10,
    value=3
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**About:** This RAQA system uses sentence-transformers for semantic search and FAISS for efficient retrieval."
)

# Main query interface
st.header("Ask a Question")

question = st.text_input(
    "Your question:",
    placeholder="e.g., How much protein do athletes need daily?",
    help="Ask any question about nutrition or sports health"
)

col1, col2 = st.columns(2)
with col1:
    search_button = st.button("🔍 Search", use_container_width=True)
with col2:
    example_button = st.button("📋 Show Examples", use_container_width=True)

st.divider()

# Example questions
if example_button:
    st.subheader("Example Questions")
    examples = [
        "What are the benefits of creatine supplementation?",
        "How does sleep affect athletic recovery?",
        "What is the optimal carbohydrate intake for endurance training?",
        "How important is hydration during exercise?",
        "What nutrients are critical for muscle growth?"
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            question = ex
            search_button = True

# Search and display results
if search_button and question.strip():
    try:
        st.info(f"Searching for: **{question}**")
        
        # Call API
        response = requests.post(
            f"{API_URL}/query",
            json={"question": question, "k": num_results},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        if results:
            st.success(f"Found {len(results)} relevant document(s)")
            
            # Display results
            for idx, doc in enumerate(results, 1):
                with st.expander(
                    f"📄 {idx}. {doc.get('title', 'Untitled')} (Score: {doc.get('score', 0):.2%})",
                    expanded=(idx == 1)
                ):
                    st.markdown(f"**ID:** {doc.get('id', 'N/A')}")
                    st.markdown(f"**Title:** {doc.get('title', 'N/A')}")
                    st.markdown(f"**Relevance Score:** {doc.get('score', 0):.2%}")
                    st.markdown("---")
                    st.markdown(f"**Content:**\n\n{doc.get('text', 'N/A')}")
        else:
            st.warning("No results found. Try a different question.")
            
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Could not connect to API at {API_URL}")
        st.info("Make sure the API server is running. See README for instructions.")
    except requests.exceptions.Timeout:
        st.error("⏱️ API request timed out. Please try again.")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

st.divider()

# Footer
st.markdown("""
---
**Repository:** [GitHub - NLP RAQA](https://github.com/yourusername/nutrition-raqa)

**License:** MIT

**Questions or feedback?** Open an issue or reach out!
""")
