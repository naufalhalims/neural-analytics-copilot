#!/usr/bin/env python3
"""
scripts/test_data_analyst_rca_scenario.py
Pengujian Skenario Khusus Data Analyst / Analytics Engineer
Menguji alur investigasi end-to-end:
1. Tahap 1 (Screening): Menanyakan performa umum dan kanal mana yang memiliki rasio kegagalan anomali.
2. Tahap 2 (Deep-Dive Drilldown): Menganalisis error code breakdown pada kanal anomali tersebut (VA_BCA) dan periode waktu spesifik kejadian.
3. Tahap 3 (Cross-Domain RCA): Mengaitkan temuan angka data terstruktur dengan bukti laporan teknis / dokumen insiden resmi.
"""

import time
import httpx
import json

API_URL = "http://127.0.0.1:8508/api/chat"

DATA_ANALYST_SCENARIOS = [
    {
        "step": 1,
        "title": "Tahap 1: Anomaly Screening & Prioritization",
        "query": "Sebagai Data Analyst, tolong tunjukkan kanal pembayaran mana yang memiliki failure rate paling anomali di Q3 2026 dan bagaimana perbandingannya dengan kanal lain?",
        "check": lambda res: "va_bca" in res.get("reply", "").lower() or "bca" in res.get("reply", "").lower(),
        "verify_chart": True
    },
    {
        "step": 2,
        "title": "Tahap 2: Statistical Root-Cause Breakdown & Timeline Drilldown",
        "query": "Lakukan drill-down pada kanal VA BCA tersebut: jenis failure code apa yang mendominasi kegagalan, kapan tanggal spike tertingginya, dan berapa persentase lonjakannya?",
        "check": lambda res: ("gateway_timeout" in res.get("reply", "").lower() or "timeout" in res.get("reply", "").lower()) and ("12" in res.get("reply", "") or "september" in res.get("reply", "").lower()),
        "verify_chart": True
    },
    {
        "step": 3,
        "title": "Tahap 3: Hybrid RCA (Data Metric to Postmortem Citation)",
        "query": "Apakah anomali lonjakan timeout tersebut disebabkan oleh bug aplikasi internal kita atau ada kendala eksternal dari mitra bank? Tunjukkan nomor tiket insiden dan rujukan laporan resminya!",
        "check": lambda res: "inc-20260912-bca" in res.get("reply", "").lower() or "switch" in res.get("reply", "").lower() or "mitra bank" in res.get("reply", "").lower(),
        "verify_cit": True
    }
]

def run_analyst_rca_test():
    print("=" * 80)
    print("🔬 SIMULASI SKENARIO INVESTIGASI DATA ANALYST (ROOT CAUSE ANALYSIS)")
    print("=" * 80)

    client = httpx.Client(timeout=35.0)
    history = []
    all_passed = True

    for item in DATA_ANALYST_SCENARIOS:
        step = item["step"]
        title = item["title"]
        q = item["query"]

        print(f"\n▶ [{title}]")
        print(f"  User Query : \"{q}\"")
        t0 = time.time()
        
        try:
            res = client.post(API_URL, json={"message": q, "history": history}).json()
            latency = (time.time() - t0) * 1000
            reply = res.get("reply", "")
            chart = res.get("chart_payload")
            citations = res.get("citations", [])
            tool_meta = res.get("tool_metadata", {})

            passed_content = item["check"](res)
            passed_chart = (chart is not None) if item.get("verify_chart") else True
            passed_cit = (len(citations) > 0) if item.get("verify_cit") else True
            is_ok = passed_content and passed_chart and passed_cit

            if not is_ok:
                all_passed = False

            status = "✅ PASSED" if is_ok else "❌ FAILED"
            print(f"  Status     : {status} ({latency:.0f} ms)")
            print(f"  Jev Intent : {tool_meta.get('jev_intent_detected')} (Confidence: {tool_meta.get('jev_confidence')})")
            if chart:
                print(f"  Chart Type : {chart.get('type')} — {chart.get('title')}")
            if citations:
                print(f"  Citations  : {[c['title'] for c in citations]}")
            print(f"  Preview    :\n{reply[:250].strip()}...\n")

            # Simpan riwayat percakapan untuk multi-turn berikutnya
            history.append({"role": "user", "content": q})
            history.append({"role": "assistant", "content": reply})

        except Exception as e:
            print(f"  Status     : ❌ ERROR: {e}")
            all_passed = False

    print("=" * 80)
    print(f"🎯 KESIMPULAN INVESTIGASI ANALYST: {'SEMUA TAHAP VALID & TERVERIFIKASI' if all_passed else 'DITEMUKAN CELAH'}")
    print("=" * 80)

if __name__ == "__main__":
    run_analyst_rca_test()
