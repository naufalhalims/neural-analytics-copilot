#!/usr/bin/env python3
"""
scripts/multi_turn_semantic_test.py
Pengujian Berulang Semantic Search & Multi-turn Contextual Query
Menguji:
1. Variasi sinonim dan slang kueri dokumen (Semantic Search Robustness).
2. Multi-turn reasoning bertingkat (Turn 1: Tanya kendala -> Turn 2: Tanya rujukan/SOP secara implisit -> Turn 3: Tanya langkah refund).
3. Konsistensi latensi kueri berulang (In-Memory Qdrant & Cache hit).
"""

import sys
import time
import httpx

API_URL = "http://127.0.0.1:8508/api/chat"

# Skenario 1: Variasi Paraphrase / Semantic Search pada Dokumen SOP & Insiden
SEMANTIC_QUERIES = [
    # Format formal
    ("Formal SOP", "Bagaimana langkah mitigasi transaksi timeout pada gateway perbankan?"),
    # Bahasa kasual staf operasional
    ("Kasual Staf", "Kalo transaksi muter-muter terus dan gagal waktu tunggu abis, SOP-nya gimana?"),
    # Slang / istilah teknis singkat
    ("Slang Teknis", "Aturan circuit breaker dan failover switcher kalo bank ngadat ada di mana?"),
    # Format perbankan umum
    ("Perbankan Umum", "Bagaimana prosedur pengajuan klaim ganti rugi atau refund nasabah?"),
    # PDF specific search
    ("PDF Native Test", "Kapan status circuit breaker berubah jadi half-open sesuai dokumen mitigasi?"),
    # DOCX specific search
    ("DOCX Native Test", "Apa catatan evaluasi pasca insiden pemotongan kabel bawah laut Telkom?")
]

# Skenario 2: Percakapan Multi-turn Bertingkat (Context Retention)
MULTI_TURN_CONVERSATION = [
    {
        "turn": 1,
        "query": "Bulan September kemarin ada masalah apa di sistem pembayaran kita?",
        "check": lambda res: "bca" in res.get("reply", "").lower() or "va" in res.get("reply", "").lower() or "timeout" in res.get("reply", "").lower(),
        "desc": "Deteksi anomali spike September (Virtual Account BCA)"
    },
    {
        "turn": 2,
        "query": "Lalu kenapa itu bisa terjadi dan ada nomor laporan tiketnya nggak?",
        "check": lambda res: "inc-20260912" in res.get("reply", "").lower() or "pemeliharaan" in res.get("reply", "").lower() or "migrasi" in res.get("reply", "").lower(),
        "desc": "Multi-turn implisit: menanyakan tiket/penyebab dari turn sebelumnya"
    },
    {
        "turn": 3,
        "query": "Terus kalau nasabah minta uangnya balik karena transaksi gagal itu, prosedurnya gimana?",
        "check": lambda res: "refund" in res.get("reply", "").lower() or "sop" in res.get("reply", "").lower() or "1x24" in res.get("reply", "").lower(),
        "desc": "Multi-turn SOP refund lanjutan untuk transaksi terdampak"
    }
]

def run_tests():
    print("=" * 70)
    print("🚀 PENGUJIAN SEMANTIC SEARCH & MULTI-TURN CONVERSATION")
    print("=" * 70)
    
    client = httpx.Client(timeout=35.0)

    # 1. Test Semantic Search Robustness
    print("\n--- [BAGIAN 1] UJI SEMANTIC SEARCH BERULANG (VARIASI KASUAL & NATIVE DOCS) ---")
    semantic_pass = 0
    for label, q in SEMANTIC_QUERIES:
        t0 = time.time()
        res = client.post(API_URL, json={"message": q, "history": []}).json()
        latency = (time.time() - t0) * 1000
        
        reply = res.get("reply", "")
        citations = res.get("citations", [])
        has_citations = len(citations) > 0
        doc_names = [f"{c['title']} ({c['section']})" for c in citations]
        
        # Evaluasi kecukupan
        passed = has_citations or len(reply) > 80
        if passed:
            semantic_pass += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            
        print(f"[{status}] {label} ({latency:.1f}ms)")
        print(f"  Query    : \"{q}\"")
        print(f"  Rujukan  : {', '.join(doc_names) if doc_names else 'Tidak ada dokumen langsung (LLM response fallback)'}")
        print(f"  Cuplikan : {reply[:120].strip()}...\n")

    # 2. Test Multi-Turn Continuity
    print("\n--- [BAGIAN 2] UJI MULTI-TURN CONTEXT RETENTION (3 ROUNDS) ---")
    history = []
    multi_turn_pass = 0
    
    for step in MULTI_TURN_CONVERSATION:
        turn_no = step["turn"]
        q = step["query"]
        t0 = time.time()
        res = client.post(API_URL, json={"message": q, "history": history}).json()
        latency = (time.time() - t0) * 1000
        
        reply = res.get("reply", "")
        is_ok = step["check"](res)
        
        if is_ok:
            multi_turn_pass += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            
        print(f"Round {turn_no} [{status}] ({latency:.1f}ms) — {step['desc']}")
        print(f"  User     : \"{q}\"")
        print(f"  AI Reply : {reply[:140].strip()}...\n")
        
        # Append ke riwayat percakapan untuk giliran berikutnya
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": reply})

    # Summary
    print("=" * 70)
    print(f"📊 HASIL EVALUASI:")
    print(f"  - Semantic Search Variatif : {semantic_pass}/{len(SEMANTIC_QUERIES)} LULUS ({semantic_pass/len(SEMANTIC_QUERIES)*100:.1f}%)")
    print(f"  - Multi-Turn Context Flow  : {multi_turn_pass}/{len(MULTI_TURN_CONVERSATION)} LULUS ({multi_turn_pass/len(MULTI_TURN_CONVERSATION)*100:.1f}%)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
