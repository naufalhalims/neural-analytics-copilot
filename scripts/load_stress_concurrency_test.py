#!/usr/bin/env python3
"""
scripts/load_stress_concurrency_test.py
Pengujian Stress Test & Concurrency Spike (10 Concurrent Requests ke DuckDB 5M rows + Qdrant)
"""

import time
import asyncio
import httpx

API_URL = "http://127.0.0.1:8508/api/chat"

CONCURRENT_QUERIES = [
    "Berapa total nilai GMV dan transaksi berhasil di Q3 2026?",
    "Kanal pembayaran mana yang failure rate-nya paling anomali?",
    "Apa akar masalah lonjakan kegagalan di VA BCA tanggal 12 September?",
    "Bagaimana panduan SOP penanganan saldo gantung Bank Mandiri?",
    "Tampilkan perbandingan tren bulanan Juli, Agustus, dan September 2026!",
    "Berapa total transaksi yang tercatat di database kita?",
    "Jelaskan perbedaan penanganan ERR_GATEWAY_TIMEOUT vs ERR_SYSTEM_MALFUNCTION!",
    "Sektor merchant mana yang paling banyak menyumbang transaksi gagal?",
    "Kalo pembeli komplain uangnya udah kepotong di kasir harus jawab apa?",
    "Tolong jelaskan isi dokumen SOP mitigasi mitra bank partner!"
]

async def send_query(client, i, q):
    t0 = time.time()
    try:
        res = await client.post(API_URL, json={"message": q, "history": []}, timeout=45.0)
        lat = (time.time() - t0) * 1000
        data = res.json()
        status_ok = res.status_code == 200 and len(data.get("reply", "")) > 50
        return {
            "index": i,
            "query": q[:35] + "...",
            "status": "PASS" if status_ok else "FAIL",
            "code": res.status_code,
            "latency_ms": lat,
            "chart": bool(data.get("chart_payload")),
            "citations": len(data.get("citations", []))
        }
    except Exception as e:
        return {
            "index": i,
            "query": q[:35] + "...",
            "status": "ERROR",
            "code": 0,
            "latency_ms": (time.time() - t0) * 1000,
            "error": str(e)
        }

async def run_stress_test():
    print("=" * 80)
    print("🚀 PENGUJIAN BEBAN KONKURENSI (STRESS TEST 10 CONCURRENT USERS)")
    print("   Menguji Thread-Safety DuckDB 5.000.000 Baris & In-Memory Qdrant")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        t_start = time.time()
        tasks = [send_query(client, i+1, q) for i, q in enumerate(CONCURRENT_QUERIES)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - t_start

    print(f"\nTotal Waktu Eksekusi 10 Request Paralel: {total_time:.2f} detik\n")
    for r in results:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon} [Req {r['index']:02d}] {r['query']:<40} | HTTP {r['code']} | Latensi: {r['latency_ms']:.0f} ms | Chart: {r.get('chart')} | Citations: {r.get('citations')}")

    success_count = sum(1 for r in results if r["status"] == "PASS")
    avg_lat = sum(r["latency_ms"] for r in results) / len(results)
    
    print("\n" + "=" * 80)
    print(f"📊 HASIL STRESS TEST:")
    print(f"  - Sukses          : {success_count}/{len(CONCURRENT_QUERIES)} ({(success_count/len(CONCURRENT_QUERIES))*100:.1f}%)")
    print(f"  - Rata-rata Latensi: {avg_lat:.0f} ms")
    print(f"  - Throughput (RPS): {len(CONCURRENT_QUERIES)/total_time:.2f} req/sec")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_stress_test())
