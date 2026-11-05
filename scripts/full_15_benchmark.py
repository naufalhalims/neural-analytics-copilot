import httpx
import json
import time

BASE_URL = "http://127.0.0.1:8508/api/chat"

# 15 Butir Pertanyaan Eksak dari Dokumen Technical Test AI Engineer PT Neural Technologies
TEST_MATRIX = [
    # KATEGORI A: Data Exploration
    {
        "id": "A1",
        "category": "A. Data Exploration",
        "question": "Berapa total transaksi pada bulan ini?",
        "check": lambda r: "5.000.000" in r.get("reply", "") or "triliun" in r.get("reply", "").lower() or "september" in r.get("reply", "").lower()
    },
    {
        "id": "A2",
        "category": "A. Data Exploration",
        "question": "Bagaimana distribusi transaksi berdasarkan status?",
        "check": lambda r: r.get("chart_payload") is not None and r.get("chart_payload", {}).get("type") == "doughnut"
    },
    {
        "id": "A3",
        "category": "A. Data Exploration",
        "question": "Kanal mana yang memiliki volume transaksi tertinggi?",
        "check": lambda r: "va_bca" in r.get("reply", "").lower() or "qris" in r.get("reply", "").lower()
    },

    # KATEGORI B: Trend & Comparison
    {
        "id": "B1",
        "category": "B. Trend & Comparison",
        "question": "Bagaimana perbandingan volume transaksi bulan ini dengan bulan sebelumnya?",
        "check": lambda r: "agustus" in r.get("reply", "").lower() or "september" in r.get("reply", "").lower()
    },
    {
        "id": "B2",
        "category": "B. Trend & Comparison",
        "question": "Apakah tingkat keberhasilan transaksi mengalami perubahan dalam tiga bulan terakhir?",
        "check": lambda r: r.get("chart_payload") is not None and "line" in r.get("chart_payload", {}).get("type")
    },
    {
        "id": "B3",
        "category": "B. Trend & Comparison",
        "question": "Kategori mana yang mengalami peningkatan atau penurunan terbesar?",
        "check": lambda r: "kategori" in r.get("reply", "").lower() or "merchant" in r.get("reply", "").lower() or r.get("chart_payload") is not None
    },

    # KATEGORI C: Problem Investigation
    {
        "id": "C1",
        "category": "C. Problem Investigation",
        "question": "Mengapa tingkat kegagalan transaksi meningkat dibandingkan bulan sebelumnya?",
        "check": lambda r: "va_bca" in r.get("reply", "").lower() or "september" in r.get("reply", "").lower()
    },
    {
        "id": "C2",
        "category": "C. Problem Investigation",
        "question": "Faktor apa yang paling berkontribusi terhadap penurunan keberhasilan transaksi?",
        "check": lambda r: "gateway_timeout" in r.get("reply", "").lower() or "bca" in r.get("reply", "").lower() or "jaringan" in r.get("reply", "").lower()
    },
    {
        "id": "C3",
        "category": "C. Problem Investigation",
        "question": "Apakah peningkatan kegagalan terkonsentrasi pada kanal, kategori, atau periode tertentu?",
        "check": lambda r: "va_bca" in r.get("reply", "").lower() or "13" in r.get("reply", "") or "september" in r.get("reply", "").lower()
    },

    # KATEGORI D: Document-based Questions
    {
        "id": "D1",
        "category": "D. Document-based Questions",
        "question": "Apa prosedur yang harus dilakukan ketika transaksi gagal?",
        "check": lambda r: "sop" in r.get("reply", "").lower() or "refund" in r.get("reply", "").lower() or "eskalasi" in r.get("reply", "").lower()
    },
    {
        "id": "D2",
        "category": "D. Document-based Questions",
        "question": "Berdasarkan dokumen yang tersedia, apa penyebab umum kegagalan transaksi?",
        "check": lambda r: "timeout" in r.get("reply", "").lower() or "insufficient" in r.get("reply", "").lower() or "dokumen" in r.get("reply", "").lower()
    },
    {
        "id": "D3",
        "category": "D. Document-based Questions",
        "question": "Apa perbedaan prosedur penanganan untuk setiap jenis kegagalan?",
        "check": lambda r: "circuit breaker" in r.get("reply", "").lower() or "saldo" in r.get("reply", "").lower() or "timeout" in r.get("reply", "").lower()
    },

    # KATEGORI E: Follow-up Analysis (Multi-Turn Simulation)
    {
        "id": "E1",
        "category": "E. Follow-up Analysis",
        "question": "Kanal mana yang paling berkontribusi terhadap peningkatan kegagalan tersebut?",
        "check": lambda r: "va bca" in r.get("reply", "").lower() or "va_bca" in r.get("reply", "").lower() or "virtual account bca" in r.get("reply", "").lower()
    },
    {
        "id": "E2",
        "category": "E. Follow-up Analysis",
        "question": "Sejak kapan perubahan tersebut mulai terjadi?",
        "check": lambda r: "13 september" in r.get("reply", "").lower() or "12 september" in r.get("reply", "").lower() or "september" in r.get("reply", "").lower()
    },
    {
        "id": "E3",
        "category": "E. Follow-up Analysis",
        "question": "Apakah informasi dalam dokumen yang tersedia relevan untuk membantu menjelaskan pola tersebut?",
        "check": lambda r: "relevan" in r.get("reply", "").lower() or "inc-20260912-bca" in r.get("reply", "").lower() or "postmortem" in r.get("reply", "").lower()
    }
]

def run_test_suite():
    print("=" * 70)
    print("🚀 MENJALANKAN FULL 15-QUESTION BENCHMARK TEST (USECASE RESMI)")
    print("=" * 70)
    
    passed_count = 0
    total_count = len(TEST_MATRIX)
    
    for t in TEST_MATRIX:
        print(f"\n[{t['id']}] {t['category']}")
        print(f"Q: \"{t['question']}\"")
        start_t = time.time()
        
        try:
            resp = httpx.post(BASE_URL, json={"message": t["question"]}, timeout=45.0)
            latency = time.time() - start_t
            
            if resp.status_code == 200:
                data = resp.json()
                is_passed = t["check"](data)
                if is_passed:
                    passed_count += 1
                    status_str = f"✅ PASSED ({latency:.2f}s)"
                else:
                    status_str = f"⚠️ CHECK FAILED ({latency:.2f}s)"
                print(f"Status: {status_str}")
                chart_info = data.get("chart_payload", {}).get("title") if data.get("chart_payload") else "No Chart"
                print(f"Chart: {chart_info}")
                print(f"Preview: {data.get('reply', '')[:140]}...")
            else:
                print(f"Status: ❌ HTTP {resp.status_code}")
        except Exception as e:
            print(f"Status: ❌ ERROR ({e})")
            
    print("\n" + "=" * 70)
    score_pct = (passed_count / total_count) * 100
    print(f"🏆 HASIL AKHIR: {passed_count}/{total_count} BUTIR LULUS ({score_pct:.1f}%)")
    print("=" * 70)

if __name__ == "__main__":
    run_test_suite()
