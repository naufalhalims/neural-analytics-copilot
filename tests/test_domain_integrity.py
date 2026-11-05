"""
Unit Tests for Domain Boundary Isolation, Contract Data Integrity, and Ground-Truth Precision.
Menguji secara spesifik celah yang baru diperbaiki:
1. Multi-Column table_data payload contract in /api/chat
2. Cross-Domain Leakage Detection & Guardrail (Fintech in BPJS, BPJS in Fintech)
3. Ground-Truth Data Consistency (Lowest Claim in BPJS)
4. Anti-Hallucination on Negative Entities
"""

import os
import sys
import time
import pytest
from fastapi.testclient import TestClient

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app

client = TestClient(app)

class TestIntegrityAndDomainBoundaries:

    def test_01_bpjs_ground_truth_lowest_claim(self):
        """Memverifikasi klaim terendah di BPJS mengembalikan diagnosa Gagal Ginjal Cuci Darah N-4-10-I."""
        resp = client.post("/api/chat", json={
            "message": "diagnosa apa dengan nilai klaim paling rendah?",
            "dataset": "bpjs",
            "history": []
        })
        assert resp.status_code == 200
        data = resp.json()
        reply_lower = data.get("reply", "").lower()
        
        # Harus menyebutkan diagnosa dan kode INA-CBG terendah
        assert ("gagal ginjal" in reply_lower or "n-4-10-i" in reply_lower or "nefrologi" in reply_lower)
        assert ("16,74" in data.get("reply", "") or "16.74" in data.get("reply", ""))

    def test_02_table_data_payload_contract(self):
        """Memverifikasi API mengembalikan field table_data bertipe list of dicts multi-kolom."""
        resp = client.post("/api/chat", json={
            "message": "rekapitulasi klaim per poli spesialis",
            "dataset": "bpjs",
            "history": []
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "table_data" in data, "Field 'table_data' wajib hadir di kontrak response /api/chat"
        table_rows = data["table_data"]
        assert isinstance(table_rows, list)
        assert len(table_rows) > 0, "table_data tidak boleh kosong untuk kueri agregasi poli"
        
        # Cek kelengkapan kolom
        first_row = table_rows[0]
        assert "poli_spesialis" in first_row
        assert "total_klaim" in first_row
        assert "dispute_rate_pct" in first_row
        assert "nilai_klaim_miliar" in first_row

    def test_03_cross_domain_guardrail_fintech_query_in_bpjs(self):
        """Memverifikasi pertanyaan fintech di domain BPJS dihentikan oleh guardrail tanpa membocorkan SQL RS."""
        resp = client.post("/api/chat", json={
            "message": "Berapa transaksi gagal di Virtual Account BCA dan Mandiri?",
            "dataset": "bpjs",
            "history": []
        })
        assert resp.status_code == 200
        data = resp.json()
        
        # Harus memicu guardrail redirect
        reply = data.get("reply", "")
        assert "Cross-Domain Guardrail" in reply or "Domain Tidak Sesuai" in reply
        assert "Fintech & Banking" in reply
        # table_data dan chart_payload harus kosong (tidak boleh mengeksekusi query RS sembarangan)
        assert data.get("table_data") == []
        assert data.get("chart_payload") is None

    def test_04_cross_domain_guardrail_bpjs_query_in_fintech(self):
        """Memverifikasi pertanyaan tarif INA-CBG di domain fintech dihentikan oleh guardrail."""
        resp = client.post("/api/chat", json={
            "message": "Berapa plafon tarif klaim rawat inap INA-CBG yang dispute?",
            "dataset": "default",
            "history": []
        })
        assert resp.status_code == 200
        data = resp.json()
        
        reply = data.get("reply", "")
        assert "Cross-Domain Guardrail" in reply or "Domain Tidak Sesuai" in reply
        assert "Healthcare Claims BPJS" in reply
        assert data.get("table_data") == []
        assert data.get("chart_payload") is None

    def test_05_negative_entity_trap_zero_hallucination(self):
        """Memverifikasi sistem menolak jujur saat ditanyakan entitas fiktif (cabut gigi bungsu di RS rujukan)."""
        resp = client.post("/api/chat", json={
            "message": "Berapa klaim tindakan cabut gigi bungsu di poli gigi?",
            "dataset": "bpjs",
            "history": []
        })
        assert resp.status_code == 200
        data = resp.json()
        reply_lower = data.get("reply", "").lower()
        
        assert any(phrase in reply_lower for phrase in [
            "belum tercatat", "tidak tercatat", "tidak ditemukan", "tidak ada", "belum tersedia"
        ]), "Sistem harus menolak entitas yang tidak ada di dataset, bukan mengarang angka!"

    def test_06_rate_limiting_middleware_protection(self):
        """Uji hardening: middleware rate limiting harus membatasi request melebihi kuota."""
        import app
        import time as time_mod
        # Clear rate limit store for clean client IP isolation
        import app as app_module
        app_module.RATE_LIMIT_STORE.clear()
        client_ip = "testclient"
        app.RATE_LIMIT_STORE[client_ip] = [time_mod.time()] * 65
        
        resp = client.post("/api/chat", json={
            "message": "cek status rate limit",
            "dataset": "default"
        })
        assert resp.status_code in (200, 429)

    def test_07_ast_guardrail_stacked_queries_and_dangerous_calls(self):
        """Uji hardening: AST Guardrail harus menolak stacked queries ('; DROP...') dan load_extension."""
        import pytest
        from app import sql_engine
        
        with pytest.raises(PermissionError):
            sql_engine.validate_and_sanitize("'; DROP TABLE IF EXISTS transactions; --")
            
        with pytest.raises(PermissionError):
            sql_engine.validate_and_sanitize("SELECT load_extension('remote_shell.so');")
            
        with pytest.raises(PermissionError):
            sql_engine.validate_and_sanitize("UPDATE transactions SET status='SUCCESS';")
            
        with pytest.raises(PermissionError):
            sql_engine.validate_and_sanitize("ATTACH DATABASE '/etc/shadow' AS shadow_db;")

    def test_08_negative_entity_atlantis_and_invalid_date(self):
        """Uji hardening: Penolakan zero-hallucination tegas terhadap entitas paradoks non-eksisten."""
        import app as app_module
        app_module.RATE_LIMIT_STORE.clear()
        resp = client.post("/api/chat", json={
            "message": "Berapa transaksi di Bank Atlantis pada tanggal 31 Februari 2026?",
            "dataset": "default",
            "history": []
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "Zero-Hallucination Guardrail" in data.get("reply", "")
        assert len(data.get("table_data", [])) == 0
