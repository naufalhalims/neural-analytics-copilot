"""Script QA Testing Otomatis untuk menguji 5 Kategori Pertanyaan Soal Test (A s.d. E).
Menguji:
- A. Data Exploration
- B. Trend & Comparison
- C. Problem Investigation
- D. Document-based Questions
- E. Follow-up Analysis
"""

import httpx
import json
import time

BASE_URL = "http://127.0.0.1:8508"

TEST_QUESTIONS = [
    {
        "category": "A. Data Exploration",
        "question": "Berapa total transaksi dan bagaimana distribusi status transaksi bulan ini?",
        "expected_check": lambda r: r.get("chart_payload") is not None and "status" in r.get("sql_executed", "").lower()
    },
    {
        "category": "B. Trend & Comparison",
        "question": "Bagaimana perbandingan tren volume dan tingkat kegagalan antar bulan?",
        "expected_check": lambda r: r.get("chart_payload") is not None and "month" in r.get("sql_executed", "").lower()
    },
    {
        "category": "C. Problem Investigation",
        "question": "Mengapa tingkat kegagalan transaksi meningkat di bulan September dan faktor apa yang paling berkontribusi?",
        "expected_check": lambda r: r.get("target_channel") == "VA_BCA" and len(r.get("citations", [])) > 0
    },
    {
        "category": "D. Document-based Questions",
        "question": "Apa prosedur yang harus dilakukan ketika transaksi gagal mengalami gateway timeout?",
        "expected_check": lambda r: len(r.get("citations", [])) > 0 and any("SOP" in c["title"] for c in r.get("citations", []))
    },
    {
        "category": "E. Follow-up Analysis",
        "question": "Sejak kapan lonjakan kegagalan tersebut terjadi dan bukti insiden apa yang mendukung kesimpulan?",
        "expected_check": lambda r: "12 September" in r.get("reply", "") or "INC-20260912-BCA" in r.get("reply", "") or len(r.get("citations", [])) > 0
    }
]

def run_qa_tests():
    print("=" * 70)
    print("🧪 MEMULAI AUTOMATED ADVERSARIAL QA TEST (5 KATEGORI SOAL)")
    print("=" * 70)
    
    passed_count = 0
    
    with httpx.Client(timeout=45.0) as client:
        for idx, t in enumerate(TEST_QUESTIONS, 1):
            cat = t["category"]
            q = t["question"]
            print(f"\n[Test #{idx}] {cat}")
            print(f"Query: \"{q}\"")
            
            t0 = time.time()
            try:
                res = client.post(f"{BASE_URL}/api/chat", json={"message": q})
                elapsed = time.time() - t0
                
                if res.status_code == 200:
                    data = res.json()
                    is_valid = t["expected_check"](data)
                    
                    status_badge = "✅ PASSED" if is_valid else "⚠️ REVIEW REQUIRED"
                    if is_valid:
                        passed_count += 1
                        
                    print(f"Status: {status_badge} (Latency: {elapsed:.2f}s)")
                    print(f"SQL Executed: {data.get('sql_executed')}")
                    print(f"Chart Rendered: {data.get('chart_payload', {}).get('title') if data.get('chart_payload') else 'None'}")
                    print(f"Highlight Channel: {data.get('target_channel')}")
                    print(f"Citations: {[c['title'] for c in data.get('citations', [])]}")
                    print(f"Reply Preview: {data.get('reply', '')[:200]}...")
                else:
                    print(f"❌ FAILED HTTP {res.status_code}: {res.text}")
            except Exception as e:
                print(f"❌ ERROR: {e}")
                
    print("\n" + "=" * 70)
    print(f"🏆 HASIL QA BENCHMARK: {passed_count}/{len(TEST_QUESTIONS)} TESTS PASSED ({(passed_count/len(TEST_QUESTIONS))*100:.1f}%)")
    print("=" * 70)

if __name__ == "__main__":
    run_qa_tests()
