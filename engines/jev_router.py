"""
engines/jev_router.py
Modul Fast-Path Decision Engine berbasis TypeSafe Jev System One.
Menggunakan variabel environment TYPESAFE_API_KEY untuk klasifikasi intent, routing kueri,
dan tool pre-dispatch sub-milidetik (<100ms) dengan in-memory LRU & local heuristic fallback.
"""

import os
import time
import httpx
from typing import Dict, Any

TYPESAFE_API_KEY = os.environ.get("TYPESAFE_API_KEY", "").strip()
TYPESAFE_URL = os.environ.get("TYPESAFE_URL", "https://api.typesafe.ai/v1/systemone")
TYPESAFE_MODEL = os.environ.get("TYPESAFE_MODEL", "jev-latest")

# Candidate Choices untuk System One Decision
ROUTING_CHOICES = {
    "SQL_AGGREGATE": "Pertanyaan statistik angka, total volume, GMV, perbandingan bulan, distribusi status transaksi (DuckDB)",
    "RCA_INVESTIGATION": "Pertanyaan investigasi penyebab lonjakan kegagalan, anomali tanggal tertentu, anomali kanal perbankan (Spike Z-Score & Postmortem)",
    "SOP_PROCEDURE": "Pertanyaan langkah penanganan operasional kasir/staf, SLA rekonsiliasi, kebijakan auto-refund, perbedaan error code (Qdrant Vector)",
    "MERCHANT_ANALYSIS": "Pertanyaan perbandingan performa per kategori merchant (Retail, Gaming, Travel, Bill Payment)",
    "GENERAL_OVERVIEW": "Sapaan umum, ringkasan menyeluruh kesehatan sistem perbankan"
}

_JEV_CACHE: Dict[str, Dict[str, Any]] = {}


class JevDecisionEngine:
    def __init__(self, api_key: str = TYPESAFE_API_KEY):
        self.api_key = (api_key or "").strip()
        self.url = TYPESAFE_URL
        self.model = TYPESAFE_MODEL

    async def decide_intent(self, query: str, context: str = "") -> Dict[str, Any]:
        """
        Menentukan jalur eksekusi alat tercepat menggunakan TypeSafe Jev System One.
        Jika API key tidak dikonfigurasi atau jaringan lambat (>600ms), fallback otomatis ke rule-based heuristik lokal (<1ms).
        """
        cache_key = query.strip().lower()
        if cache_key in _JEV_CACHE:
            cached = dict(_JEV_CACHE[cache_key])
            cached["cached"] = True
            cached["latency_ms"] = 0
            return cached

        t0 = time.time()

        if self.api_key:
            elements = [
                {"index": str(i + 1), "label": f"{k}: {v}", "operations": ["SELECT"]}
                for i, (k, v) in enumerate(ROUTING_CHOICES.items())
            ]

            body = {
                "model": self.model,
                "state": {
                    "page": {"url": "local://neural-analytics", "title": "Intent Decision", "text": context or query},
                    "elements": elements,
                    "recent_actions": []
                },
                "questions": {
                    "decision": {
                        "type": "choice",
                        "criteria": ROUTING_CHOICES,
                        "instructions": {"goal": f"Tentukan kategori intent terbaik untuk pertanyaan analitik: '{query}'"}
                    }
                }
            }

            try:
                async with httpx.AsyncClient(timeout=0.6) as client:
                    res = await client.post(
                        self.url,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self.api_key}"
                        },
                        json=body
                    )
                    if res.status_code == 200:
                        data = res.json()
                        ans = data.get("answers", {}).get("decision", {})
                        chosen = ans.get("choice") or "SQL_AGGREGATE"
                        confidence = ans.get("confidence", 0.95)
                        elapsed = round((time.time() - t0) * 1000, 1)

                        result = {
                            "intent": chosen,
                            "confidence": confidence,
                            "source": "typesafe_jev_cloud",
                            "latency_ms": elapsed,
                            "cached": False
                        }
                        _JEV_CACHE[cache_key] = result
                        return result
            except Exception:
                pass

        # Fast Heuristic Speculation (Sub-1ms)
        lower = query.lower()
        if any(w in lower for w in ["kategori", "merchant", "sektor", "bisnis"]):
            chosen = "MERCHANT_ANALYSIS"
        elif any(w in lower for w in ["kenapa", "mengapa", "penyebab", "investigasi", "sejak kapan", "spike", "anomali", "kendala"]):
            chosen = "RCA_INVESTIGATION"
        elif any(w in lower for w in ["sop", "prosedur", "refund", "aturan", "kebijakan", "ganti rugi", "perbedaan"]):
            chosen = "SOP_PROCEDURE"
        elif any(w in lower for w in ["total", "berapa", "distribusi", "volume", "status", "perbandingan", "bulan"]):
            chosen = "SQL_AGGREGATE"
        else:
            chosen = "GENERAL_OVERVIEW"

        elapsed = round((time.time() - t0) * 1000, 1)
        result = {
            "intent": chosen,
            "confidence": 0.92,
            "source": "typesafe_jev_local_speculative",
            "latency_ms": elapsed,
            "cached": False
        }
        _JEV_CACHE[cache_key] = result
        return result
