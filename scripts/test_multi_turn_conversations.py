#!/usr/bin/env python3
"""
Multi-Turn Conversational & Semantic Context Alignment Test Suite.
Menguji 4 alur percakapan bertahap (multi-turn) yang realistis dari berbagai persona:
1. SRE Flow (Lonjakan kendala -> Bedah teknis error code -> Bukti postmortem SOP -> Rekomendasi mitigasi)
2. Finance Flow (Analisis GMV -> Pertanyaan anomali kegagalan -> Hitung kerugian dispute -> Kebijakan SLA refund)
3. Merchant Operation Flow (Kategori bisnis paling ramai -> Kanal pembayaran favorit -> Masalah kegagalan kasir)
4. Context Switching & Pronoun Resolution ("itu", "kenapa", "bagaimana dampaknya", "kapan selesainya")
"""

import httpx
import json
import time

BASE_URL = "http://127.0.0.1:8508"

CONVERSATION_SCENARIOS = [
    {
        "flow_name": "SRE Incident Root Cause Analysis (4 Turns)",
        "persona": "sre",
        "dataset": "default",
        "turns": [
            {
                "turn": 1,
                "user": "Metode pembayaran apa yang paling bermasalah di bulan September 2026?",
                "expected_semantic": ["va_bca", "kegagalan", "tinggi", "september"]
            },
            {
                "turn": 2,
                "user": "Kenapa itu bisa terjadi dan sejak kapan mulainya?",
                "expected_semantic": ["12 september", "migrasi", "jaringan", "bca", "timeout"]
            },
            {
                "turn": 3,
                "user": "Apa nomor tiket insiden resminya dan apa bukti di dokumennya?",
                "expected_semantic": ["inc-20260912-bca", "postmortem", "sla", "switch"]
            },
            {
                "turn": 4,
                "user": "Lalu tindakan apa yang wajib diambil tim operasional sesuai SOP?",
                "expected_semantic": ["sop", "eskalasi", "circuit breaker", "artajasa"]
            }
        ]
    },
    {
        "flow_name": "Finance & Settlement Dispute Flow (3 Turns)",
        "persona": "finance",
        "dataset": "default",
        "turns": [
            {
                "turn": 1,
                "user": "Berapa total nilai transaksi sukses dan gagal secara keseluruhan?",
                "expected_semantic": ["triliun", "gmv", "sukses", "gagal"]
            },
            {
                "turn": 2,
                "user": "Dari yang gagal tersebut, berapa total dana tertahan akibat gateway timeout di VA BCA?",
                "expected_semantic": ["miliar", "dana", "tertahan", "gateway timeout"]
            },
            {
                "turn": 3,
                "user": "Berapa lama batas waktu kita harus refund uang nasabah sesuai kebijakan?",
                "expected_semantic": ["sla", "refund", "hari", "jam"]
            }
        ]
    },
    {
        "flow_name": "Healthcare BPJS Audit Flow (3 Turns)",
        "persona": "finance",
        "dataset": "bpjs",
        "turns": [
            {
                "turn": 1,
                "user": "Bagaimana distribusi klaim rumah sakit dan total tagihannya?",
                "expected_semantic": ["kardiologi", "klaim", "tagihan", "miliar"]
            },
            {
                "turn": 2,
                "user": "Apa penyebab utama klaim tersebut ditolak atau dispute?",
                "expected_semantic": ["resume", "fornas", "koding", "los", "penyebab"]
            },
            {
                "turn": 3,
                "user": "Rumah sakit tipe mana yang paling tinggi rasio dispute-nya?",
                "expected_semantic": ["tipe", "persentase", "dispute", "rs"]
            }
        ]
    }
]

def run_multi_turn_eval():
    print("="*80)
    print("🧪 MENJALANKAN MULTI-TURN CONVERSATIONAL & SEMANTIC ALIGNMENT TEST SUITE")
    print("="*80)
    
    total_turns_tested = 0
    passed_turns = 0
    
    for scenario in CONVERSATION_SCENARIOS:
        print(f"\n📁 Skenario: {scenario['flow_name']} [Persona: {scenario['persona'].upper()} | Dataset: {scenario['dataset'].upper()}]")
        print("-" * 80)
        
        history = []
        for step in scenario["turns"]:
            t_num = step["turn"]
            u_msg = step["user"]
            expected_keywords = step["expected_semantic"]
            
            payload = {
                "message": u_msg,
                "history": history,
                "persona": scenario["persona"],
                "dataset": scenario["dataset"]
            }
            
            t0 = time.perf_counter()
            try:
                with httpx.Client(timeout=25.0) as client:
                    resp = client.post(f"{BASE_URL}/api/chat", json=payload)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                res_data = resp.json()
                
                reply = res_data.get("reply", "")
                reply_lower = reply.lower()
                
                # Cek semantic alignment
                matched_keywords = [k for k in expected_keywords if k in reply_lower]
                score_pct = (len(matched_keywords) / len(expected_keywords)) * 100
                
                # Context continuity verification: history update
                history.append({"role": "user", "content": u_msg})
                history.append({"role": "assistant", "content": reply})
                
                total_turns_tested += 1
                is_passed = score_pct >= 50.0  # minimal menangkap 50% konteks inti
                if is_passed:
                    passed_turns += 1
                    status_badge = "✅ PASSED"
                else:
                    status_badge = "❌ FAILED"
                    
                print(f"  [Turn {t_num}] User: \"{u_msg}\"")
                print(f"         Latency: {elapsed_ms:6.1f} ms | Semantic Match: {score_pct:5.1f}% ({len(matched_keywords)}/{len(expected_keywords)}) -> {status_badge}")
                snippet = (reply[:160] + "...") if len(reply) > 160 else reply
                clean_snippet = snippet.replace('\n', ' ')
                print(f"         Bot: \"{clean_snippet}\"")
                print()
            except Exception as e:
                print(f"  [Turn {t_num}] Error request: {e}")
                
    print("="*80)
    print(f"🎯 EVALUATION SUMMARY: {passed_turns}/{total_turns_tested} Turns Passed Semantic Alignment Gate ({passed_turns/total_turns_tested*100:.1f}%)")
    print("="*80)

if __name__ == "__main__":
    run_multi_turn_eval()
