#!/usr/bin/env python3
"""
scripts/test_simple_queries_retrieval.py
Menguji Retrieval & Respons Mesin pada Kueri Super Sederhana (1-3 Kata):
1. "bca kenapa"
2. "total transaksi"
3. "refund sop"
4. "kategori boncos"
5. "error timeout"
6. "mandiri gantung"
7. "tren september"
"""

import time
import httpx

API_URL = "http://127.0.0.1:8508/api/chat"

SIMPLE_QUERIES = [
    {
        "query": "bca kenapa",
        "desc": "Kueri 2 kata: menanyakan masalah kanal BCA",
        "expected_check": lambda r: "bca" in r["reply"].lower() and ("timeout" in r["reply"].lower() or "september" in r["reply"].lower() or "switch" in r["reply"].lower())
    },
    {
        "query": "total transaksi",
        "desc": "Kueri 2 kata: menanyakan total volume data",
        "expected_check": lambda r: "5.000.000" in r["reply"] or "transaksi" in r["reply"].lower()
    },
    {
        "query": "refund sop",
        "desc": "Kueri 2 kata: menanyakan aturan pengembalian dana",
        "expected_check": lambda r: "refund" in r["reply"].lower() and ("1x24" in r["reply"].lower() or "sop" in r["reply"].lower() or "dana" in r["reply"].lower())
    },
    {
        "query": "kategori boncos",
        "desc": "Kueri 2 kata slang: menanyakan kategori merchant bermasalah",
        "expected_check": lambda r: "kategori" in r["reply"].lower() or "merchant" in r["reply"].lower()
    },
    {
        "query": "error timeout",
        "desc": "Kueri 2 kata teknis: menanyakan kode kegagalan gateway timeout",
        "expected_check": lambda r: "timeout" in r["reply"].lower() and ("bca" in r["reply"].lower() or "sop" in r["reply"].lower() or "mitigasi" in r["reply"].lower())
    },
    {
        "query": "mandiri gantung",
        "desc": "Kueri 2 kata: menanyakan settlement saldo gantung Bank Mandiri",
        "expected_check": lambda r: "mandiri" in r["reply"].lower() and ("settlement" in r["reply"].lower() or "inquiry" in r["reply"].lower() or "1x12" in r["reply"].lower())
    },
    {
        "query": "tren september",
        "desc": "Kueri 2 kata: menanyakan tren transaksi bulan September",
        "expected_check": lambda r: "september" in r["reply"].lower() and ("kegagalan" in r["reply"].lower() or "transaksi" in r["reply"].lower() or "tren" in r["reply"].lower())
    }
]

def run_simple_test():
    print("=" * 80)
    print("⚡ PENGUJIAN KUERI PENDEK / SUPER SIMPEL (1-2 KATA)")
    print("=" * 80)

    client = httpx.Client(timeout=35.0)
    passed_count = 0

    for item in SIMPLE_QUERIES:
        q = item["query"]
        desc = item["desc"]
        t0 = time.time()
        
        try:
            res = client.post(API_URL, json={"message": q, "history": []}).json()
            latency = (time.time() - t0) * 1000
            
            tool_meta = res.get("tool_metadata", {})
            reply = res.get("reply", "")
            chart = res.get("chart_payload")
            citations = res.get("citations", [])
            
            is_ok = item["expected_check"](res)
            if is_ok:
                passed_count += 1
                status = "✅ PASS"
            else:
                status = "⚠️ CHECK"
                
            print(f"[{status}] \"{q}\" ({latency:.0f} ms) — {desc}")
            print(f"  Jev Decision : {tool_meta.get('jev_intent_detected')} (Confidence: {tool_meta.get('jev_confidence')})")
            print(f"  Chart        : {chart.get('title') if chart else 'None'}")
            print(f"  Citations    : {[c['title'] for c in citations] if citations else 'None'}")
            print(f"  Cuplikan     : {reply[:130].strip()}...\n")
            
        except Exception as e:
            print(f"[❌ ERROR] \"{q}\": {e}\n")

    print("=" * 80)
    print(f"📊 HASIL KUERI PENDEK: {passed_count}/{len(SIMPLE_QUERIES)} Lulus ({(passed_count/len(SIMPLE_QUERIES))*100:.1f}%)")
    print("=" * 80)

if __name__ == "__main__":
    run_simple_test()
