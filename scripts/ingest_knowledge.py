"""Skrip otomatis untuk melakukan ingestion dokumen ke Qdrant Vector DB."""
import sys
import os

# Tambahkan working directory ke path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.rag_engine import RAGEngine

if __name__ == "__main__":
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(app_dir, "docs")
    db_path = os.path.join(app_dir, "data", "qdrant_db")
    
    rag = RAGEngine(db_path=db_path)
    rag.ingest_documents(docs_dir=docs_dir)
    
    # Tes query pencarian
    test_query = "Apa prosedur eskalasi transaksi gagal karena timeout?"
    print(f"\n[*] Testing Search: '{test_query}'")
    results = rag.search(test_query, top_k=2)
    for r in results:
        print(f"-> [{r['score']}] {r['doc_title']} - {r['section']}")
