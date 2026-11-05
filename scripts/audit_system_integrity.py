#!/usr/bin/env python3
"""
Comprehensive Ground-Truth & Robustness Audit Suite
Mengevaluasi keakuratan, celah logika, bug, dan boundary safety pada endpoint /api/chat.
"""

import urllib.request
import json
import duckdb
import time

BASE_URL = "http://127.0.0.1:8508"
BPJS_PARQUET = "/home/ubuntu/apps/neural-analytics-chatbot/data/multi_domain/bpjs_claims_100k.parquet"
FINTECH_PARQUET = "/home/ubuntu/apps/neural-analytics-chatbot/data/transactions_5m.parquet"

# DuckDB ground truth engine
con = duckdb.connect()

def call_chat(message: str, dataset: str = "bpjs", history: list = None):
    payload = {
        "message": message,
        "dataset": dataset,
        "history": history or []
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as resp:
        latency_ms = (time.perf_counter() - t0) * 1000
        data = json.loads(resp.read().decode("utf-8"))
        data["_latency_ms"] = latency_ms
        return data

# Test Cases
tests = [
    {
        "id": "TEST-01",
        "name": "Ground-Truth: Diagnosa Klaim Paling Rendah (BPJS)",
        "query": "diagnosa apa dengan nilai klaim paling rendah?",
        "dataset": "bpjs",
        "expected_in_reply": ["gagal ginjal", "16,74", "n-4-10-i"],
        "check": lambda res: any(k in res["reply"].lower() for k in ["gagal ginjal", "16,74", "16.74", "n-4-10-i"])
    },
    {
        "id": "TEST-02",
        "name": "Ground-Truth: Rumah Sakit dengan Klaim Paling Rendah (BPJS)",
        "query": "rumah sakit mana dengan klaim paling rendah?",
        "dataset": "bpjs",
        "expected_in_reply": ["rsud kota bekasi", "86,83"],
        "check": lambda res: "bekasi" in res["reply"].lower() and ("86,83" in res["reply"] or "86.83" in res["reply"] or "19.856" in res["reply"] or "19856" in res["reply"])
    },
    {
        "id": "TEST-03",
        "name": "Negative Entity Trap: Diagnosa Fiktif / Cabut Gigi (BPJS)",
        "query": "Berapa total klaim dan nominal untuk tindakan cabut gigi bungsu?",
        "dataset": "bpjs",
        "expected_in_reply": ["tidak ditemukan", "tidak tercatat", "tidak ada", "belum tersedia"],
        "check": lambda res: any(k in res["reply"].lower() for k in ["tidak ditemukan", "tidak tercatat", "tidak ada", "belum tercatat", "tidak tersedia"])
    },
    {
        "id": "TEST-04",
        "name": "Negative Hospital Trap: Rumah Sakit Fiktif (BPJS)",
        "query": "Berapa total klaim di RS Siloam Semanggi?",
        "dataset": "bpjs",
        "expected_in_reply": ["tidak ditemukan", "tidak tercatat", "tidak ada"],
        "check": lambda res: any(k in res["reply"].lower() for k in ["tidak ditemukan", "tidak tercatat", "tidak ada", "belum tercatat", "bukan mitra"])
    },
    {
        "id": "TEST-05",
        "name": "Domain Boundary Isolation: Fintech Query in BPJS dataset",
        "query": "Berapa transaksi gagal di Virtual Account BCA dan Mandiri?",
        "dataset": "bpjs",
        "expected_in_reply": ["tidak ditemukan", "tidak relevan", "fintech"],
        "check": lambda res: any(k in res["reply"].lower() for k in ["tidak ditemukan", "tidak tercatat", "fintech", "bukan", "tidak ada", "faskes"])
    },
    {
        "id": "TEST-06",
        "name": "Domain Boundary Isolation: BPJS Query in Fintech dataset",
        "query": "Berapa klaim INA-CBG yang berstatus dispute?",
        "dataset": "default",
        "expected_in_reply": ["tidak tercatat", "tidak ada", "klaim", "bpjs"],
        "check": lambda res: any(k in res["reply"].lower() for k in ["tidak tercatat", "tidak ditemukan", "tidak ada", "bpjs", "pengembalian dana"])
    },
    {
        "id": "TEST-07",
        "name": "Studio Table Payload Completeness Check",
        "query": "rekapitulasi klaim per poli spesialis",
        "dataset": "bpjs",
        "check": lambda res: isinstance(res.get("table_data"), list) and len(res.get("table_data", [])) > 0
    },
    {
        "id": "TEST-08",
        "name": "Studio Chart Payload Completeness Check",
        "query": "rekapitulasi klaim per poli spesialis",
        "dataset": "bpjs",
        "check": lambda res: isinstance(res.get("chart_payload"), dict) and "labels" in res.get("chart_payload", {}) and len(res.get("chart_payload", {}).get("labels", [])) > 0
    }
]

print("="*75)
print("🔍 AUDIT KOMPREHENSIF ROBUSTNESS, DATA RELEVANCE & BUG HUNTING")
print("="*75)

results = []
for t in tests:
    print(f"\n[*] Running {t['id']}: {t['name']}")
    try:
        res = call_chat(t["query"], dataset=t.get("dataset", "bpjs"))
        passed = t["check"](res)
        latency = res.get("_latency_ms", 0)
        table_len = len(res.get("table_data") or [])
        has_chart = bool(res.get("chart_payload"))
        sql = res.get("sql_query")
        
        status = "PASS" if passed else "FAIL"
        print(f"    Status   : {status} ({latency:.1f} ms)")
        print(f"    SQL      : {sql}")
        print(f"    TableRows: {table_len} | HasChart: {has_chart}")
        print(f"    Snippet  : {res.get('reply', '')[:160]}...")
        
        results.append({
            "id": t["id"],
            "name": t["name"],
            "status": status,
            "latency": latency,
            "reply": res.get("reply"),
            "table_len": table_len,
            "has_chart": has_chart,
            "sql": sql
        })
    except Exception as e:
        print(f"    Status   : ERROR ({e})")
        results.append({
            "id": t["id"],
            "name": t["name"],
            "status": "ERROR",
            "error": str(e)
        })

print("\n" + "="*75)
print("📊 RINGKASAN HASIL AUDIT:")
pass_count = sum(1 for r in results if r["status"] == "PASS")
print(f"Total Uji: {len(results)} | Lulus: {pass_count} | Gagal/Temuan: {len(results) - pass_count}")
print("="*75)
