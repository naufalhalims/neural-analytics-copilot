#!/usr/bin/env python3
"""
Informal / Slang & Ambiguous Natural Language Synthesis Benchmark.
Menguji ketahanan sistem terhadap bahasa sehari-hari, ambigu, tidak spesifik, typo, dan slang kasir/lapangan:
1. "min ini duitnya kok gak masuk2 ya padahal pembeli udah transfer tadi siang?" (Ambigu transfer bank/VA)
2. "kemarin pas gajian rame yg komplain ya? apaan sih yg jebol?" (Ambigu spike akhir bulan & kanal error)
3. "bos mau liat rekap jualan kita, yg mana yg paling laku?" (Bahasa santai GMV/kategori bisnis)
4. "kalo bca lagi error gitu kita musti ngapain dah?" (Slang SOP & mitigasi insiden)
5. "bisa bikinin rangkuman singkat buat bos ga? yg penting2 aja" (Permintaan eksekutif tanpa menyebut kata SQL/data)
"""

import httpx
import json
import time

BASE_URL = "http://127.0.0.1:8508"

SLANG_AMBIGUOUS_QUERIES = [
    {
        "id": "SLANG-01",
        "category": "AMBIGUOUS_TRANSACTION_PENDING",
        "persona": "kasir",
        "dataset": "default",
        "user_query": "min ini duitnya kok gak masuk2 ya padahal pembeli udah transfer tadi siang?",
        "expected_intent": "Menjelaskan status mutasi, pending verifikasi perbankan, dan batas waktu 1x24 jam dengan bahasa kasir yang menenangkan"
    },
    {
        "id": "SLANG-02",
        "category": "SLANG_INCIDENT_INVESTIGATION",
        "persona": "sre",
        "dataset": "default",
        "user_query": "kemarin pas tanggal tua rame yg komplain ya? apaan sih yg jebol?",
        "expected_intent": "Mendeteksi lonjakan kegagalan di bulan September (VA BCA gateway timeout) dan menjelaskan akar masalahnya secara to-the-point"
    },
    {
        "id": "SLANG-03",
        "category": "INFORMAL_BUSINESS_PERFORMANCE",
        "persona": "all",
        "dataset": "default",
        "user_query": "bos mau liat rekap jualan kita, yg mana yg paling laku?",
        "expected_intent": "Mengagregasikan GMV / volume per kategori bisnis (Retail, F&B) dan menampilkan chart visual tanpa bingung dengan istilah 'paling laku'"
    },
    {
        "id": "SLANG-04",
        "category": "CASUAL_SOP_MITIGATION",
        "persona": "sre",
        "dataset": "default",
        "user_query": "kalo bca lagi error gitu kita musti ngapain dah?",
        "expected_intent": "Mengutip langkah mitigasi SOP (Eskalasi L2, circuit breaker, hubungi Artajasa/mitra bank) dari pertanyaan santai"
    },
    {
        "id": "SLANG-05",
        "category": "VAGUE_EXECUTIVE_SUMMARY",
        "persona": "finance",
        "dataset": "default",
        "user_query": "bisa bikinin rangkuman singkat buat bos ga? yg penting2 aja angkanya",
        "expected_intent": "Memberikan Bottom-Line Up Front (BLUF): Total 5M transaksi, GMV Rp 1,01 T, success rate 96,24%, dan catatan dispute Rp 2,92 M"
    }
]

def run_slang_benchmark():
    print("="*85)
    print("🗣️ MENJALANKAN BENCHMARK BAHASA SEHARI-HARI, SLANG, & KUERI AMBIGU")
    print("="*85)
    
    passed = 0
    total = len(SLANG_AMBIGUOUS_QUERIES)
    
    with httpx.Client(timeout=35.0) as client:
        for tc in SLANG_AMBIGUOUS_QUERIES:
            cid = tc["id"]
            cat = tc["category"]
            query = tc["user_query"]
            persona = tc["persona"]
            expected = tc["expected_intent"]
            
            t0 = time.perf_counter()
            try:
                resp = client.post(f"{BASE_URL}/api/chat", json={
                    "message": query,
                    "persona": persona,
                    "dataset": tc["dataset"]
                })
                elapsed_ms = (time.perf_counter() - t0) * 1000
                res_data = resp.json()
                reply = res_data.get("reply", "")
                sql = res_data.get("sql_executed")
                chart = bool(res_data.get("chart_payload"))
                
                # Evaluasi semantik kecukupan penanganan
                reply_lower = reply.lower()
                is_valid = False
                
                if cid == "SLANG-01":
                    # Menenangkan, sebut rekening/mutasi/1x24 jam
                    is_valid = any(k in reply_lower for k in ["tenang", "1x24", "mutasi", "rekening", "pending", "menunggu"])
                elif cid == "SLANG-02":
                    # Sebut VA BCA, September, timeout, atau lonjakan kegagalan
                    is_valid = any(k in reply_lower for k in ["va_bca", "bca", "september", "timeout", "jaringan", "lonjakan"])
                elif cid == "SLANG-03":
                    # Sebut retail, gmv, atau kategori merchant
                    is_valid = any(k in reply_lower for k in ["retail", "f&b", "kategori", "volume", "paling tinggi", "tertinggi"])
                elif cid == "SLANG-04":
                    # Sebut sop, eskalasi, circuit breaker, atau langkah penanganan
                    is_valid = any(k in reply_lower for k in ["sop", "eskalasi", "mitigasi", "circuit breaker", "artajasa", "langkah"])
                elif cid == "SLANG-05":
                    # Menangkap metrik kunci: volume transaksi, failure rate (~3,8%), atau stabilitas sistem
                    is_valid = any(k in reply_lower for k in ["5.000.000", "5 juta", "triliun", "gmv", "96", "sukses", "failure rate", "kegagalan", "3,8", "ringkasan eksekutif"])
                    
                status_badge = "✅ HANDLED PERFECTLY" if is_valid else "⚠️ PARTIALLY MISALIGNED"
                if is_valid:
                    passed += 1
                    
                print(f"\n[{cid}] {cat}")
                print(f"       User Informal: \"{query}\" (Persona: {persona})")
                print(f"       Expected Int : {expected}")
                print(f"       Latency      : {elapsed_ms:6.1f} ms | Chart: {'YA' if chart else 'TIDAK'} | SQL Executed: {sql is not None}")
                print(f"       Status       : {status_badge}")
                snippet = reply[:160].replace('\n', ' ')
                print(f"       Bot Respon   : \"{snippet}...\"")
            except Exception as e:
                print(f"[{cid}] Error: {e}")
                
    pct = (passed / total) * 100
    print("\n" + "="*85)
    print(f"🎯 SUMMARY BENCHMARK BAHASA SEHARI-HARI: {passed}/{total} Lulus ({pct:.1f}%)")
    print("="*85)

if __name__ == "__main__":
    run_slang_benchmark()
