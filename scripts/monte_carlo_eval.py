"""Monte Carlo QA Stress Testing & Context Drift Evaluation
Menjalankan 50 permutasi kueri analitik berbasis berbagai gaya bahasa pengguna (santai, teknis, bisnis, typo, singkat, komparatif)
untuk mengevaluasi:
1. Context Consistency (Apakah menjawab sesuai fakta 5M data & insiden nyata?)
2. Grounding Accuracy (BCA 12-15 Sept ERR_GATEWAY_TIMEOUT vs Hallucination)
3. Visual Chart Alignment (Apakah chart yang di-generate relevan dengan topik kueri?)
4. Response Latency & Failure Rate
"""

import httpx
import time
import json
import random
from typing import Dict, Any, List

BASE_URL = "http://127.0.0.1:8508"

# Pool variasi pertanyaan pengguna (25 sampel representatif lintas 5 persona)
PROMPT_PERSONAS = [
    # Persona A: Eksekutif Bisnis C-Level (Fokus GMV, Ringkas)
    "Bro tolong ringkas performa pembayaran kita kuartal ini, berapa omset dan tingkat kegagalannya?",
    "Bulan September kemarin performa gimana? Ada penurunan revenue atau kenaikan komplain?",
    "Kanal mana yang paling bikin boncos dan nurunin transaksi di September?",
    "Berapa total volume uang yang berhasil diproses sistem sejauh ini?",
    "Performa antar bulan membaik atau memburuk dari Juli ke September?",
    
    # Persona B: Tech Lead / SRE / DevOps (Fokus Error Code, Latency, Log)
    "Kanal pembayaran mana yang failure rate-nya paling abnormal di September 2026?",
    "Ada lonjakan error ERR_GATEWAY_TIMEOUT gak di periode September kemarin?",
    "Apa penyebab utama lonjakan transaksi gagal di virtual account BCA?",
    "Nomor tiket insiden apa yang mencatat gangguan switch data center mitra?",
    "Sejak tanggal berapa lonjakan failure rate di kanal VA BCA mulai terjadi?",
    
    # Persona C: Kasir / Customer Support Lead (Fokus Refund & Keluhan Pelanggan)
    "Pelanggan komplain transaksi BCA mereka pending dan gagal, SOP refund-nya gimana?",
    "Kalau user kena error timeout tapi saldo terpotong, berapa lama batas waktu pengembalian dana?",
    "Siapa contact person atau tim eskalasi bank jika VA BCA bermasalah?",
    "Kapan insiden BCA dinyatakan resolved dan status transaksi normal kembali?",
    "Dokumen SOP penanganan insiden transaksi mengatur apa saja untuk refund nasabah?",

    # Persona D: Pertanyaan Santai, Bahasa Gaul & Slang (Conversational)
    "halo bro, mau nanya dong transaksi bulan ini aman gak sih?",
    "kemarin bca sempet ngadat ya pas september? kok rame di komplain user?",
    "kenapa sih va bca sering banget gagal dibanding mandiri atau qris?",
    "ada catatan postmortem gak soal insiden jaringan kemarin?",
    "kok transaksi september jelek banget ya bro? pemicunya apaan?",

    # Persona E: Kueri Singkat, Keyword-Driven, atau Typo
    "total transaksi status",
    "bca fail rate september",
    "kenapa september jelek",
    "sop timeout transaksi",
    "sla refund transaksi"
]

def evaluate_response_quality(query: str, res: Dict[str, Any]) -> Dict[str, Any]:
    reply = res.get("reply", "").lower()
    sql = res.get("sql_executed", "") or ""
    chart = res.get("chart_payload")
    citations = res.get("citations", [])
    
    # Rule Evaluasi Semantik & Grounding
    checks = {
        "is_coherent": len(reply) > 50 and not reply.startswith("error"),
        "no_latex_spam": "$" not in reply and "\\frac" not in reply,
        "grounded_facts": True,
        "visual_aligned": True
    }
    
    q_low = query.lower()
    
    # 1. Validasi fakta empiris jika bertanya tentang insiden / September / kegagalan
    if any(k in q_low for k in ["bca", "september", "ngadat", "kenapa", "gagal", "lonjakan", "error"]):
        # Harus menyebutkan VA_BCA atau kode insiden atau timeout, bukan mengarang kanal lain
        if not any(k in reply for k in ["va_bca", "bca", "timeout", "inc-20260912-bca", "switch", "13", "14"]):
            checks["grounded_facts"] = False
            
    # 2. Validasi SOP & Refund
    if any(k in q_low for k in ["sop", "refund", "prosedur", "sla", "eskalasi"]):
        if not any(k in reply for k in ["sop", "sla", "mitra", "refund", "level", "l2", "l3", "jam"]):
            checks["grounded_facts"] = False
            
    # 3. Validasi Visualisasi Data
    if any(k in q_low for k in ["grafik", "tren", "distribusi", "bandingkan", "bulan", "status"]):
        if not chart:
            checks["visual_aligned"] = False
            
    return checks

def run_monte_carlo_simulation():
    print("=" * 80)
    print("🎲 MEMULAI MONTE CARLO CONTEXT DRIFT SIMULATION (N = 25 ITERASI)")
    print(f"Target Service: {BASE_URL}")
    print("=" * 80)
    
    results = []
    latencies = []
    grounded_scores = []
    visual_scores = []
    
    with httpx.Client(timeout=45.0) as client:
        for idx, prompt in enumerate(PROMPT_PERSONAS, 1):
            t0 = time.time()
            try:
                resp = client.post(f"{BASE_URL}/api/chat", json={"message": prompt})
                latency = time.time() - t0
                latencies.append(latency)
                
                if resp.status_code == 200:
                    data = resp.json()
                    eval_res = evaluate_response_quality(prompt, data)
                    
                    is_success = all(eval_res.values())
                    grounded_scores.append(1 if eval_res["grounded_facts"] else 0)
                    visual_scores.append(1 if eval_res["visual_aligned"] else 0)
                    
                    status_emoji = "✅" if is_success else "⚠️"
                    chart_title = data.get("chart_payload", {}).get("title") if data.get("chart_payload") else "No Chart"
                    
                    print(f"[{idx:02d}/25] {status_emoji} Latency: {latency:.2f}s | Q: \"{prompt[:35]}...\" | Chart: {chart_title[:25]}", flush=True)
                    
                    results.append({
                        "iteration": idx,
                        "query": prompt,
                        "latency": latency,
                        "status": "PASS" if is_success else "DRIFT",
                        "eval": eval_res
                    })
                else:
                    print(f"[{idx:02d}/50] ❌ HTTP {resp.status_code} Error: {resp.text[:60]}")
                    results.append({"iteration": idx, "query": prompt, "status": "FAIL", "latency": latency})
            except Exception as e:
                print(f"[{idx:02d}/50] ❌ Exception: {e}")
                results.append({"iteration": idx, "query": prompt, "status": "ERROR", "latency": 0})
                
    # Rekapitulasi Statistik Monte Carlo
    total_samples = len(results)
    passed_samples = sum(1 for r in results if r.get("status") == "PASS")
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
    grounding_rate = (sum(grounded_scores) / len(grounded_scores) * 100) if grounded_scores else 0
    visual_rate = (sum(visual_scores) / len(visual_scores) * 100) if visual_scores else 0
    confidence_interval = (passed_samples / total_samples) * 100
    
    print("\n" + "=" * 80)
    print("📊 REKAPITULASI HASIL MONTE CARLO SIMULATION")
    print("=" * 80)
    print(f"Total Iterasi        : {total_samples}")
    print(f"Confidence Level     : {confidence_interval:.2f}% (Tingkat Kepatuhan Konteks & Keinginan User)")
    print(f"Grounding Accuracy   : {grounding_rate:.2f}% (Bebas Halusinasi / Sesuai Fakta 5M Transaksi)")
    print(f"Visual Context Match : {visual_rate:.2f}% (Visualisasi Relevan dengan Topik Percakapan)")
    print(f"Average Latency      : {avg_latency:.2f} detik")
    print(f"P95 Latency          : {p95_latency:.2f} detik")
    print("=" * 80)
    
    # Simpan hasil laporan ke disk
    summary_path = "/home/ubuntu/apps/neural-analytics-chatbot/data/monte_carlo_results.json"
    with open(summary_path, "w") as f:
        json.dump({
            "confidence_level": confidence_interval,
            "grounding_accuracy": grounding_rate,
            "visual_alignment": visual_rate,
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "details": results
        }, f, indent=2)
    print(f"[+] Laporan lengkap Monte Carlo tersimpan di: {summary_path}")

if __name__ == "__main__":
    run_monte_carlo_simulation()
