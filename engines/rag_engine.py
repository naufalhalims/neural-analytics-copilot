"""Hybrid Vector RAG Engine menggunakan Qdrant lokal + Sentence-Transformers.
Menyimpan dan mencari potongan dokumen SOP serta Log Insiden perbankan.
"""

import os
import glob
import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

class RAGEngine:
    def __init__(self, db_path: str = ":memory:", model_name: str = "all-MiniLM-L6-v2", docs_dir: str = "docs/"):
        self.db_path = db_path
        self.collection_name = "operational_knowledge"
        
        # Inisialisasi Qdrant Client (:memory: menghilangkan lock contention)
        if self.db_path == ":memory:":
            self.client = QdrantClient(":memory:")
        else:
            os.makedirs(self.db_path, exist_ok=True)
            self.client = QdrantClient(path=self.db_path)
        
        # Model Embedding Ringan (384-dim)
        print(f"[*] Loading embedding model '{model_name}'...")
        self.encoder = SentenceTransformer(model_name)
        
        # In-memory vector cache untuk kueri serupa
        self._search_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        # Buat koleksi jika belum ada
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.encoder.get_sentence_embedding_dimension(),
                    distance=models.Distance.COSINE
                )
            )
            print(f"[+] Qdrant collection '{self.collection_name}' berhasil dibuat.")
            
        # Jika mode memory, ingest langsung dokumen operasional
        if self.db_path == ":memory:" and os.path.exists(docs_dir):
            self.ingest_documents(docs_dir)
            
    def ingest_documents(self, docs_dir: str = "docs/"):
        """Membaca file Markdown di folder docs/ dan meng-index chunk ke Qdrant."""
        doc_files = glob.glob(os.path.join(docs_dir, "*.md"))
        points = []
        
        print(f"[*] Memulai ingest {len(doc_files)} dokumen operasional...")
        
        for file_path in doc_files:
            file_name = os.path.basename(file_path)
            doc_type = "SOP" if "SOP" in file_name else "INCIDENT_LOG"
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Chunking berbasis section (header Markdown ##)
            sections = content.split("## ")
            for sec in sections:
                if not sec.strip():
                    continue
                header = sec.split("\n")[0].strip()
                chunk_text = f"Dokumen: {file_name}\nBagian: {header}\n\n{sec.strip()}"
                
                vector = self.encoder.encode(chunk_text).tolist()
                point_id = str(uuid.uuid4())
                
                payload = {
                    "doc_title": file_name,
                    "doc_type": doc_type,
                    "section": header,
                    "content": chunk_text
                }
                
                points.append(models.PointStruct(id=point_id, vector=vector, payload=payload))
                
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
            print(f"[+] Berhasil meng-index {len(points)} chunks ke Qdrant.")
            
    def search(self, query: str, top_k: int = 3, doc_type_filter: str = None) -> List[Dict[str, Any]]:
        """Mencari dokumen paling relevan menggunakan Cosine Similarity dengan caching."""
        cache_key = f"{query}_{top_k}_{doc_type_filter}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
            
        query_vector = self.encoder.encode(query).tolist()
        
        query_filter = None
        if doc_type_filter:
            query_filter = models.Filter(
                must=[models.FieldCondition(key="doc_type", match=models.MatchValue(value=doc_type_filter))]
            )
            
        # Di qdrant-client >= 1.10, search() menggunakan query_points()
        hits = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k
        ).points
        
        results = []
        for hit in hits:
            results.append({
                "score": round(hit.score, 4),
                "doc_title": hit.payload.get("doc_title"),
                "doc_type": hit.payload.get("doc_type"),
                "section": hit.payload.get("section"),
                "content": hit.payload.get("content")
            })
            
        if len(self._search_cache) > 100:
            self._search_cache.pop(next(iter(self._search_cache)))
        self._search_cache[cache_key] = results
        return results
