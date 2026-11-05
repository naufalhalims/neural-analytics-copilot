#!/usr/bin/env python3
"""
tests/test_context_compactor.py
===============================
Unit test & stress test untuk ContextCompactor & MemoryStore (Hermes Architecture).
"""

import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from engines.context_compactor import ContextCompactor, MemoryStore

class TestContextCompactor(unittest.TestCase):
    def setUp(self):
        self.compactor = ContextCompactor(token_threshold=100, protected_tail_turns=1)
        self.memory = MemoryStore("/tmp/test_chat_memory.db")

    def test_01_memory_store_profile_persistence(self):
        """Memastikan role & pinned facts tersimpan dan terbaca stabil."""
        session_id = "test_sre_lead"
        self.memory.set_profile(session_id, role="Lead SRE", pinned_facts=["SLA: 99.9%", "Prioritas: VA BCA"])
        
        profile = self.memory.get_profile(session_id)
        self.assertEqual(profile["role"], "Lead SRE")
        self.assertIn("SLA: 99.9%", profile["pinned_facts"])

    def test_02_under_threshold_no_compaction(self):
        """Kueri pendek di bawah threshold tidak boleh dikompresi."""
        history = [
            {"role": "user", "content": "Halo apa kabar?"},
            {"role": "assistant", "content": "Halo! Sistem analitik siap melayani."}
        ]
        compacted, was_compacted = self.compactor.compact_history(history, "sess_1")
        self.assertFalse(was_compacted)
        self.assertEqual(len(compacted), 2)

    def test_03_over_threshold_head_tail_preserved(self):
        """Saat melebihi batas token, Head dan Tail wajib utuh sementara Middle diringkas."""
        history = [
            {"role": "user", "content": "HEAD_GOAL: Fokus investigasi transaksi September 2026 di kanal VA BCA."},
            {"role": "assistant", "content": "Baik, fokus ke September 2026."},
            {"role": "user", "content": "Berapa banyak transaksi gagal terkait Artajasa dengan tiket INC-20260912-BCA?"},
            {"role": "assistant", "content": "Ditemukan 212.500 transaksi gagal pada saat migrasi."},
            {"role": "user", "content": "Berapa total nilai nominal yang tertahan?"},
            {"role": "assistant", "content": "Total nominal tertahan adalah 42.5 Miliar rupiah."},
            {"role": "user", "content": "TAIL_USER: Lalu apa rekomendasi eskalasi berikutnya?"},
            {"role": "assistant", "content": "TAIL_ASSISTANT: Segera aktifkan circuit breaker sesuai SOP."}
        ]
        
        compacted, was_compacted = self.compactor.compact_history(history, "sess_sre")
        self.assertTrue(was_compacted)
        
        # Head message harus persis sama
        self.assertEqual(compacted[0]["content"], history[0]["content"])
        
        # Tail messages harus persis sama (2 pesan terakhir untuk tail_turns=1)
        self.assertEqual(compacted[-1]["content"], history[-1]["content"])
        self.assertEqual(compacted[-2]["content"], history[-2]["content"])
        
        # Harus ada pesan summary di tengah
        middle = compacted[1]
        self.assertEqual(middle["role"], "system")
        self.assertIn("[CONTEXT COMPACTION SUMMARY]", middle["content"])
        self.assertIn("INC-20260912-BCA", middle["content"])
        self.assertIn("BCA", middle["content"])

    def test_04_anchor_extraction_accuracy(self):
        """Verifikasi ekstraksi entity anchors secara presisi."""
        messages = [
            {"role": "user", "content": "Periksa tiket INC-20260912-BCA terkait Bank Mandiri dan QRIS di September"}
        ]
        anchors = self.compactor.extract_anchors(messages)
        self.assertIn("INC-20260912-BCA", anchors["tickets"])
        self.assertTrue(any(e in anchors["entities"] for e in ["MANDIRI", "QRIS"]))
        self.assertIn("september", anchors["metrics"])

if __name__ == "__main__":
    unittest.main()
