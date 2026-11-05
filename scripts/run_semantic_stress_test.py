#!/usr/bin/env python3
"""
Semantic Stress Testing: Menguji Query dengan Semantik Sulit,
Slang/Bahasa Gaul Bisnis, Implied Financial Logic, Figurative Speech,
dan Contextual Ambiguity.
"""

import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8508"

def ask_bot(query: str, dataset: str = "default", history: list = None):
    payload = {
        "message": query,
        "dataset": dataset,
        "history": history or []
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=45) as resp:
        lat = (time.perf_counter() - t0) * 1000
        data = json.loads(resp.read().decode("utf-8"))
        data["_latency_ms"] = lat
        return data

# 5 Kategori Query Semantik Sulit
semantic_cases = [
    {
        "id": "SEM-01",
        "category": "Slang & Business Jargon (Boncos & Jebol)",
        "query": "Kanal mana yang paling bikin boncos dan jebol minggu-minggu ini?",
        "dataset": "default",
        "intent_expected": "Mendeteksi bahwa 'boncos & jebol' = failure rate / kerugian tertinggi (VA_BCA / kegagalan transaksi)",
    },
    {
        "id": "SEM-02",
        "category": "Indirect / Implied Metric (Cash Cow / Tulang Punggung)",
        "query": "Siapa sebenarnya tulang punggung yang menghidupi bisnis kita dari sisi volume duit?",
        "dataset": "default",
        "intent_expected": "Mendeteksi bahwa 'tulang punggung volume duit' = Top GMV / Volume Kontributor Terbesar",
    },
    {
        "id": "SEM-03",
        "category": "Medical-Operational Metaphor (BPJS Sengketa / Rebutan Klaim)",
        "query": "Poli mana yang paling sering ribut berkasnya sama verifikator BPJS?",
        "dataset": "bpjs",
        "intent_expected": "Mendeteksi bahwa 'ribut berkas sama verifikator' = Dispute Rate / Status Klaim FAILED / Fornas (Nefrologi / Kardiologi)",
    },
    {
        "id": "SEM-04",
        "category": "Multi-Hop / Comparative Relative Query",
        "query": "Apakah penyakit dengan pasien terbanyak otomatis jadi penyumbang tagihan terbesar juga?",
        "dataset": "bpjs",
        "intent_expected": "Membandingkan volume pasien per diagnosa vs total nominal tagihan (menunjukkan trade-off cuci darah vs jantung)",
    },
    {
        "id": "SEM-05",
        "category": "Temporal Idiomatic / Sejak Kapan (Causality Root Cause)",
        "query": "Mulai kapan boroknya sistem pembayaran kita mulai kelihatan bau?",
        "dataset": "default",
        "intent_expected": "Mendeteksi anomali spike / insiden September 2026 (tiket INC-20260912-BCA)",
    }
]

print("="*80)
print("🧠 SEMANTIC STRESS TESTING: EVALUASI PEMAHAMAN INTENSI SULIT & METAFORA")
print("="*80)

for sc in semantic_cases:
    print(f"\n▶ [{sc['id']}] {sc['category']}")
    print(f"  User Query : \"{sc['query']}\" (Dataset: {sc['dataset']})")
    print(f"  Ekspektasi : {sc['intent_expected']}")
    
    try:
        res = ask_bot(sc['query'], dataset=sc['dataset'])
        lat = res.get("_latency_ms", 0)
        tool_meta = res.get("tool_metadata", {})
        intent_detected = tool_meta.get("jev_intent_detected", "N/A")
        sql_exec = res.get("sql_executed")
        reply = res.get("reply", "")
        
        print(f"  ⚡ Latensi : {lat:.1f} ms | Jev Intent: {intent_detected}")
        print(f"  💾 SQL Exec: {sql_exec}")
        print(f"  📝 Snippet Jawaban:\n{reply[:350]}...\n")
        
        # Simpan full reply untuk laporan
        sc["reply"] = reply
        sc["intent_detected"] = intent_detected
        sc["sql_exec"] = sql_exec
        sc["latency"] = lat
    except Exception as e:
        print(f"  ❌ Error: {e}")
        sc["error"] = str(e)

print("="*80)
