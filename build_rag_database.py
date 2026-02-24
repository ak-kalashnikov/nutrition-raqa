#!/usr/bin/env python3
"""
Build comprehensive RAG database from nutrition science resources.
Downloads open-access content and creates FAISS index.
"""

import os
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import time

# Create directories
DATA_DIR = Path("data")
INDEX_DIR = DATA_DIR / "index"
DATA_DIR.mkdir(exist_ok=True)
INDEX_DIR.mkdir(exist_ok=True)

def fetch_pressbook_chapters():
    """Fetch chapters from Open Washington Pressbooks - Nutrition Science"""
    chapters = [
        ("Nutrition and Health", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/1a-nutrition-and-health/"),
        ("Introduction to Molecules", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/1b-introduction-to-molecules/"),
        ("Classification of Nutrients", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/1c-classification-of-nutrients/"),
        ("Dietary Reference Intakes", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/1d-dietary-reference-intakes/"),
        ("Understanding Food Labels", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/1e-understanding-food-labels/"),
        ("Tools for Achieving a Healthy Diet", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/1f-tools-for-healthy-diet/"),
        ("The Digestive System", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/3c-digestive-system/"),
        ("Types of Carbohydrates", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/4a-types-of-carbohydrates/"),
        ("Carbohydrate Food Sources and Guidelines", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/4b-carbohydrate-food-sources-guidelines/"),
        ("Digestion and Absorption of Carbohydrates", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/4c-digestion-absorption-carbohydrates/"),
        ("Glucose Regulation and Utilization", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/4d-glucose-regulation-utilization-body/"),
        ("Fiber Types and Health Benefits", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/4e-fiber/"),
        ("The Functions of Fats", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/5a-function-of-fats/"),
        ("Lipid Types and Structures", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/5b-lipid-types-structures/"),
        ("Fatty Acid Types and Food Sources", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/5c-fatty-acid-types-food-sources/"),
        ("Lipid Recommendations and Heart Health", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/5f-lipid-recommendations-heart-health/"),
        ("Protein Structure", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/6a-protein-structure/"),
        ("Protein Functions", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/6b-protein-functions/"),
        ("Protein in Foods and Dietary Recommendations", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/6c-protein-in-foods-and-dietary-recommendations/"),
        ("Protein Digestion and Absorption", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/6d-protein-digestion-absorption/"),
        ("Health Consequences of Protein Imbalance", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/6e-consequences-too-little-much-protein/"),
        ("Energy Balance and Body Weight", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/__unknown__/"),
        ("Measures of Body Composition and Health", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/__unknown__-2/"),
        ("Vitamins and Minerals Classification", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/8a-classification-vitamins-minerals/"),
        ("Sources of Vitamins and Minerals", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/8b-sources-of-vitamins-minerals/"),
        ("Dietary Supplements", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/8c-dietary-supplements/"),
        ("Calcium and Bone Health", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/9b-calcium/"),
        ("Vitamin D Important to Bone Health", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/9d-vitamin-d/"),
        ("Nutrition and Physical Activity", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/unit-10-intro-physical-activity/"),
        ("Essential Elements and Benefits of Fitness", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/__unknown__-7/"),
        ("Fuel Sources for Exercise", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/10b-fuel-sources-exercise/"),
        ("Nutrient Needs of Athletes", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/10c-nutrient-needs-athletes/"),
        ("Nutrition in Pregnancy and Lactation", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/11a-nutrition-in-pregnancy-and-lactation/"),
        ("Nutrition in Older Adults", "https://openwa.pressbooks.pub/nutritionscience2e0630/chapter/11f-older-adults/"),
    ]
    
    documents = []
    for title, url in chapters:
        try:
            print(f"Fetching: {title}...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract main content
            content_div = soup.find('div', class_='content')
            if not content_div:
                content_div = soup.find('article')
            if not content_div:
                content_div = soup.find('main')
            
            if content_div:
                text = content_div.get_text(separator=' ', strip=True)
                text = ' '.join(text.split())  # Clean whitespace
                
                if len(text) > 200:  # Only include if substantial content
                    documents.append({
                        "doc_id": f"pressbooks_{len(documents):03d}",
                        "title": title,
                        "source": "Open Washington Pressbooks - Nutrition Science",
                        "text": text,
                        "chunk": 0
                    })
            
            time.sleep(0.5)  # Be respectful to server
        except Exception as e:
            print(f"  Error fetching {title}: {e}")
    
    return documents


def chunk_text(text, chunk_size=400, overlap=50):
    """Split text into overlapping chunks"""
    chunks = []
    words = text.split()
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        if len(chunk_words) > 50:  # Only include meaningful chunks
            chunks.append(' '.join(chunk_words))
    
    return chunks


def create_documents_from_chunks(documents):
    """Create JSONL entries from documents with chunking"""
    jsonl_entries = []
    doc_counter = 0
    
    for doc in documents:
        chunks = chunk_text(doc['text'])
        
        for chunk_idx, chunk in enumerate(chunks):
            entry = {
                "doc_id": f"doc_{doc_counter}",
                "title": doc['title'],
                "source": doc.get('source', 'Pressbooks'),
                "chunk": chunk_idx,
                "text": chunk,
                "score": 0.0  # Will be calculated by retriever
            }
            jsonl_entries.append(entry)
        
        doc_counter += 1
    
    return jsonl_entries


def save_database(documents, output_file):
    """Save documents to JSONL file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for doc in documents:
            f.write(json.dumps(doc) + '\n')
    
    print(f"✓ Saved {len(documents)} documents to {output_file}")


def main():
    print("=" * 60)
    print("Building RAG Database from Nutrition Resources")
    print("=" * 60)
    
    # Fetch content
    print("\n1. Fetching Pressbooks chapters...")
    pressbooks_docs = fetch_pressbook_chapters()
    print(f"   ✓ Fetched {len(pressbooks_docs)} chapters")
    
    # Create chunks
    print("\n2. Creating document chunks...")
    all_docs = pressbooks_docs
    chunked_docs = create_documents_from_chunks(all_docs)
    print(f"   ✓ Created {len(chunked_docs)} chunks")
    
    # Save to JSONL
    print("\n3. Saving to JSONL database...")
    db_file = DATA_DIR / "nutrition_qa.jsonl"
    save_database(chunked_docs, db_file)
    
    print("\n" + "=" * 60)
    print(f"✓ Database ready with {len(chunked_docs)} documents")
    print(f"  Location: {db_file}")
    print("\nNext step:")
    print("  1. Restart your server (Ctrl+C, then run uvicorn)")
    print("  2. Server will automatically build FAISS index")
    print("=" * 60)


if __name__ == "__main__":
    main()
