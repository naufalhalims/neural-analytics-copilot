"""Hybrid Vector RAG Engine menggunakan Qdrant lokal + Sentence-Transformers.
Menyimpan dan mencari potongan dokumen SOP serta Log Insiden operasional.
"""

import os
import uuid
import re
import math
from typing import List, Dict, Any
from collections import Counter
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

EXCLUDED_INTERNAL_FILES = {"text_to_sql_exemplars.json"}


class RAGEngine:
    def __init__(self, db_path: str = ":memory:", model_name: str = "all-MiniLM-L6-v2", docs_dir: str = "vault/"):
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

        # BM25 Lexical Inverted Index Store
        self.corpus_chunks: List[Dict[str, Any]] = []
        self.doc_freqs: Dict[str, int] = Counter()
        self.avg_doc_len: float = 0.0

        self._ensure_collection()

        # Prioritaskan Isolated Dedicated Vault jika ada, fallback ke docs/
        target_dir = docs_dir if os.path.exists(docs_dir) else "docs/"
        if self.db_path == ":memory:" and os.path.exists(target_dir):
            self.ingest_documents(target_dir)

    def _get_embedding_dim(self) -> int:
        if hasattr(self.encoder, "get_embedding_dimension"):
            return int(self.encoder.get_embedding_dimension())
        return int(self.encoder.get_sentence_embedding_dimension())

    def _ensure_collection(self):
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self._get_embedding_dim(),
                    distance=models.Distance.COSINE
                )
            )
            print(f"[+] Qdrant collection '{self.collection_name}' berhasil dibuat.")

    def reset_and_ingest(self, docs_dir: str = "vault/"):
        """Reset koleksi Qdrant & indeks BM25 secara idempoten lalu ingest ulang dokumen."""
        self._search_cache.clear()
        self.corpus_chunks.clear()
        self.doc_freqs.clear()
        self.avg_doc_len = 0.0
        try:
            self.client.delete_collection(collection_name=self.collection_name)
        except Exception:
            pass
        self._ensure_collection()
        self.ingest_documents(docs_dir)

    def extract_text_from_file(self, file_path: str) -> str:
        """Ekstraksi teks cerdas multi-format: Markdown (.md), Plaintext (.txt), PDF (.pdf), Word (.docx), JSON (.json), CSV (.csv)."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".md", ".txt"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".json":
            try:
                import json
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return json.dumps(data, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[!] Error parsing JSON {file_path}: {e}")
                return ""
        elif ext == ".csv":
            try:
                import csv
                rows = []
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    for r in reader:
                        rows.append(" | ".join(r))
                return "\n".join(rows)
            except Exception as e:
                print(f"[!] Error parsing CSV {file_path}: {e}")
                return ""
        elif ext == ".pdf":
            try:
                # Prioritas 1: PyMuPDF - Ekstraksi teks & tabel digital super cepat (<20ms)
                import pymupdf
                doc = pymupdf.open(file_path)
                pages = [page.get_text() or "" for page in doc]
                doc.close()
                extracted = "\n\n".join(pages).strip()
                if extracted:
                    return extracted
            except Exception as e:
                print(f"[!] PyMuPDF warning on {file_path}: {e}")

            try:
                # Fallback: pypdf
                import pypdf
                reader = pypdf.PdfReader(file_path)
                pages = [page.extract_text() or "" for page in reader.pages]
                return "\n\n".join(pages)
            except Exception as e:
                print(f"[!] Error parsing PDF {file_path}: {e}")
                return ""
        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(file_path)
                return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            except Exception as e:
                print(f"[!] Error parsing DOCX {file_path}: {e}")
                return ""
        return ""

    @staticmethod
    def _classify_doc_type(file_name: str) -> str:
        upper = file_name.upper()
        if "SOP" in upper or "SLA" in upper or "DIRECTORY" in upper:
            return "SOP"
        if "INFRASTRUCTURE" in upper or "TOPOLOGY" in upper or "LESSONS" in upper or "BACKTEST" in upper:
            return "SYSTEM_CONFIG"
        return "INCIDENT_LOG"

    def ingest_documents(self, docs_dir: str = "vault/"):
        """Membaca file di folder vault/ (rekursif subfolder) dan meng-index chunk ke Qdrant + BM25."""
        doc_files = []
        for root, _, files in os.walk(docs_dir):
            for file in files:
                if file.lower() in EXCLUDED_INTERNAL_FILES:
                    continue
                if any(file.lower().endswith(ext) for ext in [".md", ".pdf", ".docx", ".txt", ".json", ".csv"]):
                    doc_files.append(os.path.join(root, file))

        points = []
        print(f"[*] Memulai ingest {len(doc_files)} dokumen operasional dari Dedicated Vault '{docs_dir}' (MD/PDF/DOCX)...")

        for file_path in doc_files:
            file_name = os.path.basename(file_path)
            doc_type = self._classify_doc_type(file_name)
            content = self.extract_text_from_file(file_path)
            if not content.strip():
                continue

            # Chunking berbasis section atau per-halaman/paragraf besar
            raw_sections = content.split("## ") if "## " in content else content.split("\n\n")
            for idx_sec, sec in enumerate(raw_sections):
                sec_text = sec.strip()
                if len(sec_text) < 30:
                    continue
                header = sec_text.split("\n")[0][:60].strip() or f"Bagian {idx_sec + 1}"
                chunk_text = f"Dokumen: {file_name}\nBagian: {header}\n\n{sec_text}"

                vector = self.encoder.encode(chunk_text).tolist()
                point_id = str(uuid.uuid4())

                payload = {
                    "doc_title": file_name,
                    "doc_type": doc_type,
                    "section": header,
                    "content": chunk_text
                }
                points.append(models.PointStruct(id=point_id, vector=vector, payload=payload))

                # Simpan metadata untuk BM25 Lexical Index
                tokens = re.findall(r"\w+", chunk_text.lower())
                self.corpus_chunks.append({
                    "id": point_id,
                    "tokens": tokens,
                    "length": len(tokens),
                    "payload": payload
                })

        # Build BM25 Index statistics
        if self.corpus_chunks:
            total_len = sum(c["length"] for c in self.corpus_chunks)
            self.avg_doc_len = total_len / len(self.corpus_chunks)
            for c in self.corpus_chunks:
                unique_tokens = set(c["tokens"])
                for tok in unique_tokens:
                    self.doc_freqs[tok] += 1

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
            print(f"[+] Berhasil meng-index {len(points)} chunks ke Qdrant & BM25 Inverted Index.")

    def search_bm25(self, query: str, top_k: int = 5, doc_type_filter: str = None) -> List[Dict[str, Any]]:
        """Mencari dokumen menggunakan Okapi BM25 Lexical Keyword Matching."""
        query_tokens = re.findall(r"\w+", query.lower())
        if not query_tokens or not self.corpus_chunks:
            return []

        k1 = 1.5
        b = 0.75
        N = len(self.corpus_chunks)
        scores = []

        for chunk in self.corpus_chunks:
            if doc_type_filter and chunk["payload"].get("doc_type") != doc_type_filter:
                continue

            doc_len = chunk["length"]
            term_freqs = Counter(chunk["tokens"])
            score = 0.0

            for token in query_tokens:
                if token not in term_freqs:
                    continue
                tf = term_freqs[token]
                df = self.doc_freqs.get(token, 0)
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                numerator = tf * (k1 + 1.0)
                denominator = tf + k1 * (1.0 - b + b * (doc_len / (self.avg_doc_len or 1.0)))
                score += idf * (numerator / denominator)

            if score > 0.05:
                scores.append({
                    "id": chunk["id"],
                    "bm25_score": round(score, 4),
                    "payload": chunk["payload"]
                })

        scores.sort(key=lambda x: x["bm25_score"], reverse=True)
        return scores[:top_k]

    def search(self, query: str, top_k: int = 3, doc_type_filter: str = None) -> List[Dict[str, Any]]:
        """Hybrid Search: Menggabungkan Qdrant Cosine Similarity + BM25 Lexical via Reciprocal Rank Fusion (RRF)."""
        import time as _time
        start_t = _time.perf_counter()

        cache_key = f"{query}_{top_k}_{doc_type_filter}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        # 1. Dense Semantic Vector Search (Qdrant)
        query_vector = self.encoder.encode(query).tolist()
        query_filter = None
        if doc_type_filter:
            query_filter = models.Filter(
                must=[models.FieldCondition(key="doc_type", match=models.MatchValue(value=doc_type_filter))]
            )

        hits = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=max(top_k * 2, 6)
        ).points

        dense_ranked = []
        MIN_SIMILARITY_SCORE = 0.30
        for hit in hits:
            if hit.score >= MIN_SIMILARITY_SCORE:
                dense_ranked.append({
                    "id": str(hit.id),
                    "score": hit.score,
                    "payload": hit.payload
                })

        # 2. Lexical Keyword Search (BM25)
        bm25_ranked = self.search_bm25(query, top_k=max(top_k * 2, 6), doc_type_filter=doc_type_filter)

        # 3. Reciprocal Rank Fusion (RRF) with k=60 (menggunakan composite key unik doc_title::section)
        RRF_K = 60
        rrf_scores: Dict[str, float] = {}
        candidate_map: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(dense_ranked):
            pl = item["payload"]
            cid = f"{pl.get('doc_title', '')}::{pl.get('section', item['id'])}"
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (RRF_K + rank + 1))
            candidate_map[cid] = pl

        # Bobot ekstra untuk kata kunci kritis (Exact Keyword Boosting pada nomor tiket, hotline, atau kata langka)
        boosted_terms = ["021-5705999", "artajasa", "3500ms", "bca", "half-open", "dual-inquiry", "kabel", "telkom", "optik", "pd-bca-crit-9921"]
        query_lower = query.lower()
        has_boost_term = any(t in query_lower for t in boosted_terms)

        for rank, item in enumerate(bm25_ranked):
            pl = item["payload"]
            cid = f"{pl.get('doc_title', '')}::{pl.get('section', item['id'])}"
            weight = 2.5 if has_boost_term else 1.0
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (weight / (RRF_K + rank + 1))
            if cid not in candidate_map:
                candidate_map[cid] = pl

        # Sort by RRF Score
        sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        elapsed_ms = round((_time.perf_counter() - start_t) * 1000, 2)

        results = []
        for cid, rrf_score in sorted_candidates[:top_k]:
            payload = candidate_map[cid]
            results.append({
                "score": round(rrf_score, 4),
                "rrf_score": round(rrf_score, 4),
                "doc_title": payload.get("doc_title"),
                "doc_type": payload.get("doc_type"),
                "section": payload.get("section"),
                "content": payload.get("content"),
                "retrieval_ms": elapsed_ms,
                "strategy": "Hybrid-RRF(Qdrant+BM25)"
            })

        if len(self._search_cache) > 100:
            self._search_cache.pop(next(iter(self._search_cache)))
        self._search_cache[cache_key] = results
        return results
