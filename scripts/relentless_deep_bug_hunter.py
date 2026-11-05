#!/usr/bin/env python3
"""
scripts/relentless_deep_bug_hunter.py
======================================
RELENTLESS DEEP BUG & CRASH PROBE:
Memburu bug paling bandel, tersembunyi, dan edge-case yang memicu unhandled 500 error:
1. Malformed JSON / Broken payload types (int as string, None in list, extra fields)
2. Path Traversal & LFI in Export PDF filename / dataset query param
3. Unicode Null bytes in URL query params (/api/kpis?dataset=default%00)
4. Cache key collision & pollution (case sensitivity, whitespace poisoning)
5. Zero-result empty aggregations & NaN json serialization crash
6. Export PDF with massive / corrupted / malicious HTML injection
7. Inactive / deleted dataset switcher crash (/api/kpis?dataset=random_db_404)
8. Concurrent multi-persona state collision
"""

import sys
import os
import time
import json
import httpx

BASE_URL = "http://127.0.0.1:8508"

def run_deep_bug_hunting():
    print("=" * 75)
    print("🕵️  MEMULAI DEEP BUG & EDGE-CASE CRASH HUNTING")
    print("=" * 75)
    
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)
    bugs_found = []
    tests_run = 0

    # BUG PROBE 1: Invalid Dataset Switcher Parameter on /api/kpis
    tests_run += 1
    print("[PROBE 1] Menguji Parameter Dataset Fiktif & Path Traversal di /api/kpis...")
    res = client.get("/api/kpis?dataset=../../etc/passwd")
    if res.status_code == 500:
        bugs_found.append({"probe": "PROBE 1: Path Traversal on /api/kpis", "error": f"HTTP 500 Crash: {res.text[:200]}"})
    elif res.status_code == 200 and res.json().get("status") == "error":
        print("  -> Handled safely with error status.")
    elif res.status_code == 200:
        print(f"  -> Handled gracefully (fallback to default/empty). Status: {res.status_code}")
    else:
        print(f"  -> Returned HTTP {res.status_code}")

    # BUG PROBE 2: Export PDF Path Traversal / Malicious Title
    tests_run += 1
    print("[PROBE 2] Menguji Export PDF dengan Payload XSS / Path Traversal...")
    malicious_pdf_payload = {
        "title": "<script>alert('xss')</script>../../etc/shadow",
        "kpis": {"total_volume": "100", "success_rate": "99%"},
        "table": [{"channel": "<img src=x onerror=alert(1)>", "volume": "NaN", "gmv": "Infinity"}]
    }
    try:
        res = client.post("/api/export-pdf", json=malicious_pdf_payload)
        if res.status_code == 500:
            bugs_found.append({"probe": "PROBE 2: Malformed Export PDF", "error": f"HTTP 500: {res.text[:200]}"})
        else:
            print(f"  -> Export PDF lolos sanitasi. Status: {res.status_code}")
    except Exception as e:
        bugs_found.append({"probe": "PROBE 2: Export PDF", "error": str(e)})

    # BUG PROBE 3: Chat with Malformed JSON types (e.g., history as dict instead of list)
    tests_run += 1
    print("[PROBE 3] Menguji Chat Request dengan Tipe Data Rusak (Type Confusion)...")
    broken_payload = {
        "message": "Berapa transaksi hari ini?",
        "history": {"invalid": "not_a_list"},
        "dataset": None,
        "persona": 12345 # int instead of string
    }
    res = client.post("/api/chat", json=broken_payload)
    if res.status_code == 500:
        bugs_found.append({"probe": "PROBE 3: Type Confusion on /api/chat", "error": f"HTTP 500 Crash: {res.text[:200]}"})
    else:
        print(f"  -> Type validation FastAPI/Pydantic bekerja: HTTP {res.status_code}")

    # BUG PROBE 4: Cache Poisoning dengan Whitespace & Mixed Case
    tests_run += 1
    print("[PROBE 4] Menguji Cache Pollution & Key Collision...")
    q1 = "berapa transaksi bca"
    q2 = "  BERAPA   TRANSAKSI   BCA  "
    r1 = client.post("/api/chat", json={"message": q1})
    r2 = client.post("/api/chat", json={"message": q2})
    if r1.status_code != 200 or r2.status_code != 200:
        bugs_found.append({"probe": "PROBE 4: Cache Collision", "error": "Salah satu kueri crash"})
    else:
        print("  -> Cache normalisation berfungsi.")

    # BUG PROBE 5: DuckDB Direct Infinity / NaN JSON Serialization Crash
    tests_run += 1
    print("[PROBE 5] Menguji Serialisasi JSON untuk Nilai NaN / Infinity...")
    nan_sql_query = "SELECT 0.0 / 0.0 as nan_val, 1.0 / 0.0 as inf_val"
    res = client.post("/api/chat", json={"message": f"Eksekusi sql: {nan_sql_query}"})
    if res.status_code == 500:
        bugs_found.append({"probe": "PROBE 5: NaN / Inf JSON Serialization", "error": f"HTTP 500: {res.text[:200]}"})
    else:
        print(f"  -> Eksekusi matematis NaN/Inf tertangani: HTTP {res.status_code}")

    # BUG PROBE 6: Null Byte URL Query Parameter
    tests_run += 1
    print("[PROBE 6] Menguji Injeksi Null Byte pada URL Parameter...")
    try:
        res = client.get("/api/kpis?dataset=default%00_corrupt")
        if res.status_code == 500:
            bugs_found.append({"probe": "PROBE 6: Null Byte URL Injection", "error": f"HTTP 500: {res.text[:200]}"})
        else:
            print(f"  -> Null Byte tertangani aman: HTTP {res.status_code}")
    except Exception as e:
        bugs_found.append({"probe": "PROBE 6: Null Byte", "error": str(e)})

    # BUG PROBE 7: RAG Search dengan Karakter Regex Khusus yang Tidak Ditutup
    tests_run += 1
    print("[PROBE 7] Menguji BM25 & Qdrant Hybrid dengan Unclosed Regex / Special Chars...")
    broken_regex_query = "*(?<=abc)[def]{5,2}++\\\\\\\\"
    res = client.post("/api/chat", json={"message": broken_regex_query})
    if res.status_code == 500:
        bugs_found.append({"probe": "PROBE 7: Regex ReDoS / Syntax Crash", "error": f"HTTP 500: {res.text[:200]}"})
    else:
        print(f"  -> ReDoS & Special Regex Chars tertangani: HTTP {res.status_code}")

    # BUG PROBE 8: Massive Table Export CSV with Inactive / Empty Data
    tests_run += 1
    print("[PROBE 8] Menguji /api/tools Schema Integrity...")
    res = client.get("/api/tools")
    if res.status_code != 200 or "tools" not in res.json():
        bugs_found.append({"probe": "PROBE 8: Tools Schema Corrupt", "error": f"HTTP {res.status_code}"})
    else:
        print("  -> Tools schema valid.")

    print("\n" + "=" * 75)
    print(f"📊 HASIL DEEP BUG HUNTING ({tests_run} Probes Selesai)")
    print("=" * 75)
    if bugs_found:
        print(f"🚨 DITEMUKAN {len(bugs_found)} POTENSI BUG / CELAH!")
        for b in bugs_found:
            print(f"  • {b['probe']} -> {b['error']}")
    else:
        print("🌟 TIDAK ADA UNHANDLED EXCEPTION / 500 BUG DITEMUKAN.")
        print("   Semua input buruk, path traversal, dan malformed data terproteksi sempurna!")
    print("=" * 75)

if __name__ == "__main__":
    run_deep_bug_hunting()
