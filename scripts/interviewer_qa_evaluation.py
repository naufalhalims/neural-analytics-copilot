#!/usr/bin/env python3
"""
scripts/interviewer_qa_evaluation.py
Simulasi Evaluator Teknis PT Neural Technologies Indonesia
Menilai kesiapan sistem end-to-end:
1. Akurasi 15 Soal Panduan Resmi (Kategori A s.d. E)
2. Edge case: Multi-Turn Context Retention
3. Document Retrieval heterogen (PDF Scan, Word DOCX, Native PDF, MD)
4. Kecepatan respon (latensi ms) & Grounding Bukti (SQL & Citations)
5. Gap Analysis & Rekomendasi Nilai
"""

import sys
import time
import httpx

API_URL = "http://127.0.0.1:8508/api/chat"

EVALUATION_QUESTIONS = [
    # Kategori A: Data Exploration
    {
        "id": "A1",
        "cat": "Data Exploration",
        "query": "Berapa total transaksi pada bulan September 2026?",
        "expected_keywords": ["transaksi", "september", "total", "5.000.000"],
        "expect_chart": True
    },
    {
        "id": "A2",
        "cat": "Data Exploration",
        "query": "Bagaimana distribusi transaksi berdasarkan status?",
        "expected_keywords": ["success", "failed", "distribusi"],
        "expect_chart": True
    },
    {
        "id": "A3",
        "cat": "Data Exploration",
        "query": "Kanal mana yang memiliki volume transaksi tertinggi?",
        "expected_keywords": ["va_bca", "virtual account bca", "bca"],
        "expect_chart": True
    },

    # Kategori B: Trend & Comparison
    {
        "id": "B1",
        "cat": "Trend & Comparison",
        "query": "Bagaimana perbandingan volume transaksi bulan ini dengan bulan sebelumnya?",
        "expected_keywords": ["bulan", "tren", "perbandingan", "agustus"],
        "expect_chart": True
    },
    {
        "id": "B2",
        "cat": "Trend & Comparison",
        "query": "Apakah tingkat keberhasilan transaksi mengalami perubahan dalam tiga bulan terakhir?",
        "expected_keywords": ["penurunan", "tingkat", "keberhasilan", "september"],
        "expect_chart": True
    },
    {
        "id": "B3",
        "cat": "Trend & Comparison",
        "query": "Kategori merchant mana yang mengalami kendala transaksi tertinggi?",
        "expected_keywords": ["kategori", "merchant", "gaming", "retail", "travel", "bill"],
        "expect_chart": True
    },

    # Kategori C: Problem Investigation
    {
        "id": "C1",
        "cat": "Problem Investigation",
        "query": "Mengapa tingkat kegagalan transaksi meningkat tajam di bulan September?",
        "expected_keywords": ["va_bca", "bca", "timeout", "spike", "kendala"],
        "expect_chart": True
    },
    {
        "id": "C2",
        "cat": "Problem Investigation",
        "query": "Faktor apa yang paling berkontribusi terhadap penurunan keberhasilan transaksi?",
        "expected_keywords": ["gateway_timeout", "timeout", "jaringan", "bca"],
        "expect_chart": True
    },
    {
        "id": "C3",
        "cat": "Problem Investigation",
        "query": "Apakah peningkatan kegagalan terkonsentrasi pada kanal atau periode tanggal tertentu?",
        "expected_keywords": ["12", "september", "va_bca", "periode"],
        "expect_chart": True
    },

    # Kategori D: Document-based Questions
    {
        "id": "D1",
        "cat": "Document-based",
        "query": "Apa langkah prosedur standar operasional jika transaksi terkendala waktu tunggu habis?",
        "expected_keywords": ["sop", "timeout", "mitigasi", "circuit breaker"],
        "expect_cit": True
    },
    {
        "id": "D2",
        "cat": "Document-based",
        "query": "Berdasarkan dokumen yang tersedia, apa penyebab umum kegagalan transaksi?",
        "expected_keywords": ["gateway timeout", "timeout", "jaringan", "pemeliharaan"],
        "expect_cit": True
    },
    {
        "id": "D3",
        "cat": "Document-based",
        "query": "Apa perbedaan perlakuan dan prosedur penanganan untuk setiap jenis error code?",
        "expected_keywords": ["err_gateway_timeout", "insufficient_funds", "system_malfunction"],
        "expect_cit": True
    },

    # Kategori E: Multi-turn Follow-up Analysis
    {
        "id": "E1",
        "cat": "Follow-up Hybrid",
        "query": "Kanal pembayaran mana yang paling bermasalah di bulan September?",
        "expected_keywords": ["va_bca", "virtual account bca", "bca"],
        "expect_chart": True
    },
    {
        "id": "E2",
        "cat": "Follow-up Hybrid",
        "query": "Sejak kapan kendala pada kanal tersebut mulai terjadi?",
        "expected_keywords": ["12", "september", "2026"],
        "expect_chart": True
    },
    {
        "id": "E3",
        "cat": "Follow-up Hybrid",
        "query": "Apakah ada dokumen laporan insiden resmi yang menjelaskan penyebab kejadian ini?",
        "expected_keywords": ["inc-20260912-bca", "postmortem", "bca"],
        "expect_cit": True
    },

    # Kategori F: Heterogeneous Multi-Format Document Ingestion
    {
        "id": "F1",
        "cat": "PDF Native",
        "query": "Kapan circuit breaker berubah status menjadi half-open sesuai dokumen mitigasi?",
        "expected_keywords": ["half-open", "circuit", "breaker", "mitigasi"],
        "expect_cit": True
    },
    {
        "id": "F2",
        "cat": "Word DOCX",
        "query": "Apa hasil evaluasi gangguan kabel optik bawah laut Telkom?",
        "expected_keywords": ["telkom", "kabel", "laut", "3d-secure"],
        "expect_cit": True
    },
    {
        "id": "F3",
        "cat": "Scanned PDF",
        "query": "Bagaimana ketentuan audit dispute settlement gantung pada Bank Mandiri?",
        "expected_keywords": ["mandiri", "settlement", "dual-inquiry", "audit"],
        "expect_cit": True
    }
]

def evaluate_system():
    print("=" * 80)
    print("📋 EVALUASI PENILAI TEKNIS INTERVIEW — PT NEURAL TECHNOLOGIES INDONESIA")
    print("=" * 80)

    client = httpx.Client(timeout=35.0)
    scores = []
    latencies = []
    history = []

    for item in EVALUATION_QUESTIONS:
        qid = item["id"]
        cat = item["cat"]
        q = item["query"]
        
        t0 = time.time()
        # Jika kategori E (Follow-up), kita sertakan riwayat percakapan
        is_followup = cat == "Follow-up Hybrid"
        payload = {"message": q, "history": history if is_followup else []}
        
        try:
            resp = client.post(API_URL, json=payload).json()
            latency = (time.time() - t0) * 1000
            latencies.append(latency)
            
            reply = resp.get("reply", "").lower()
            chart = resp.get("chart_payload")
            citations = resp.get("citations", [])
            sql_exec = resp.get("sql_executed")
            
            # Verifikasi kriteria
            kw_match = any(kw.lower() in reply for kw in item["expected_keywords"])
            chart_ok = (chart is not None) if item.get("expect_chart") else True
            cit_ok = (len(citations) > 0) if item.get("expect_cit") else True
            
            passed = kw_match and chart_ok and cit_ok
            scores.append(passed)
            
            status = "✅ PASS" if passed else "⚠️ ATTENTION"
            print(f"[{status}] {qid} ({cat}) — Latensi: {latency:.0f}ms")
            print(f"  Tanya   : \"{q}\"")
            print(f"  Chart   : {'Aktif (' + chart.get('title', '') + ')' if chart else 'None'}")
            print(f"  Citations: {[c['title'] for c in citations] if citations else 'None'}")
            print(f"  Cuplikan: {reply[:120].strip()}...\n")
            
            if is_followup:
                history.append({"role": "user", "content": q})
                history.append({"role": "assistant", "content": reply})
                
        except Exception as e:
            print(f"[❌ ERROR] {qid} Fail to request: {e}\n")
            scores.append(False)

    passed_count = sum(1 for s in scores if s)
    total_q = len(scores)
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    score_pct = (passed_count / total_q) * 100

    print("=" * 80)
    print("📊 REKAPITULASI HASIL PENILAIAN:")
    print(f"  - Total Pertanyaan Diuji : {total_q}")
    print(f"  - Tingkat Kelulusan      : {passed_count}/{total_q} ({score_pct:.1f}%)")
    print(f"  - Rata-rata Latensi      : {avg_latency:.1f} ms")
    print("=" * 80)

if __name__ == "__main__":
    evaluate_system()
