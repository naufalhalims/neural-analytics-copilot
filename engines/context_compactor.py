#!/usr/bin/env python3
"""
engines/context_compactor.py
============================
Hermes-Style Context Compaction & Memory Engine for Neural Analytics Copilot.
Adopsi 4 pilar arsitektur Hermes Agent:
1. Turn Context Compaction (TCC) dengan ambang batas (Threshold Trigger).
2. Head & Tail Protection (Preserve objective & recent turns verbatim).
3. Zero-Loss State Summarization (Anchor metric extraction).
4. SQLite WAL Persistent Memory Store (User persona & session facts).
"""

import os
import sys
import json
import time
import sqlite3
from typing import List, Dict, Any, Optional, Tuple

# Menghubungkan ke standard db_utils jika tersedia
ECOSYSTEM_SCRIPTS = "/home/ubuntu/scripts"
if ECOSYSTEM_SCRIPTS not in sys.path:
    sys.path.append(ECOSYSTEM_SCRIPTS)

try:
    from db_utils import get_db
except ImportError:
    def get_db(db_path, timeout=10.0, row_factory=False):
        os.makedirs(os.path.dirname(os.path.abspath(str(db_path))), exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=timeout)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        if row_factory:
            conn.row_factory = sqlite3.Row
        return conn

DB_PATH = os.path.expanduser("~/apps/neural-analytics-chatbot/data/chat_memory.db")

class MemoryStore:
    """
    Persistent Memory Store ala Hermes Agent:
    Menyimpan profil pengguna (SRE vs Finance vs BPJS Auditor) dan fakta permanen
    yang diinjeksi ke system prompt tanpa merusak cache inference KV.
    """
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with get_db(self.db_path) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                session_id TEXT PRIMARY KEY,
                role TEXT DEFAULT 'analyst',
                pinned_facts TEXT DEFAULT '[]',
                updated_at REAL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                turn_count INTEGER,
                summary_snapshot TEXT,
                anchors_json TEXT,
                created_at REAL
            );
            """)
            conn.commit()

    def get_profile(self, session_id: str) -> Dict[str, Any]:
        with get_db(self.db_path, row_factory=True) as conn:
            cur = conn.cursor()
            cur.execute("SELECT role, pinned_facts FROM user_profiles WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            if row:
                return {
                    "role": row["role"],
                    "pinned_facts": json.loads(row["pinned_facts"])
                }
        return {"role": "analyst", "pinned_facts": []}

    def set_profile(self, session_id: str, role: str, pinned_facts: List[str]):
        with get_db(self.db_path) as conn:
            conn.execute("""
            INSERT INTO user_profiles (session_id, role, pinned_facts, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                role = excluded.role,
                pinned_facts = excluded.pinned_facts,
                updated_at = excluded.updated_at;
            """, (session_id, role, json.dumps(pinned_facts), time.time()))
            conn.commit()

    def save_checkpoint(self, session_id: str, turn_count: int, summary: str, anchors: Dict[str, Any]):
        with get_db(self.db_path) as conn:
            conn.execute("""
            INSERT INTO conversation_checkpoints (session_id, turn_count, summary_snapshot, anchors_json, created_at)
            VALUES (?, ?, ?, ?, ?);
            """, (session_id, turn_count, summary, json.dumps(anchors), time.time()))
            conn.commit()


class ContextCompactor:
    """
    Turn Context Compaction (TCC) Engine:
    Mencegah context window overflow pada sesi panjang dengan kompresi middle-turns
    serta menjaga protected head & tail.
    """
    def __init__(self, token_threshold: int = 1500, protected_tail_turns: int = 2):
        self.token_threshold = token_threshold
        self.protected_tail_turns = protected_tail_turns
        self.memory_store = MemoryStore()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimasi token konservatif: ~4 karakter per token."""
        return len(text) // 4 + 1

    def calculate_history_tokens(self, history: List[Dict[str, str]]) -> int:
        total = 0
        for msg in history:
            total += self.estimate_tokens(msg.get("content", ""))
        return total

    def extract_anchors(self, messages: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """Mengekstrak entity anchor (filter tanggal, kode bank, tiket insiden)."""
        anchors = {"entities": [], "metrics": [], "tickets": []}
        import re
        full_text = " ".join([m.get("content", "") for m in messages])
        
        # Regex anchor detector
        tickets = re.findall(r'INC-\d+-[A-Z]+', full_text, re.IGNORECASE)
        anchors["tickets"] = list(set([t.upper() for t in tickets]))
        
        banks = re.findall(r'\b(bca|mandiri|bni|bri|cimb|permata|artajasa|qris)\b', full_text, re.IGNORECASE)
        anchors["entities"] = list(set([b.upper() for b in banks]))
        
        dates = re.findall(r'\b(september|oktober|november|\d{4}-\d{2}-\d{2})\b', full_text, re.IGNORECASE)
        anchors["metrics"] = list(set([d.lower() for d in dates]))
        
        return anchors

    def compact_history(
        self,
        history: List[Dict[str, str]],
        session_id: Optional[str] = "default_session"
    ) -> Tuple[List[Dict[str, str]], bool]:
        """
        Menjalankan Head-Middle-Tail Compaction:
        Returns: (compacted_history, was_compacted)
        """
        if not history or len(history) <= (self.protected_tail_turns * 2 + 1):
            return history, False

        current_tokens = self.calculate_history_tokens(history)
        if current_tokens < self.token_threshold:
            return history, False

        # Protected Head: Pertahankan pesan awal yang menetapkan scope masalah
        head_msg = history[0]

        # Protected Tail: Pertahankan N interaksi terakhir (user + assistant)
        tail_cutoff = -(self.protected_tail_turns * 2)
        tail_msgs = history[tail_cutoff:]

        # Middle Window: Yang akan dikompresi
        middle_msgs = history[1:tail_cutoff]
        if not middle_msgs:
            return history, False

        # Ekstraksi Anchor Index
        anchors = self.extract_anchors(middle_msgs)

        # Hasilkan Structured Compaction Summary
        topics = []
        for m in middle_msgs:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            if role == "user":
                topics.append(f"Q: {content[:80]}")
            elif role == "assistant":
                # Ambil inti respon
                first_sentence = content.split(".")[0][:100]
                topics.append(f"A: {first_sentence}")

        summary_body = " | ".join(topics[-4:]) # 4 event paling relevan di middle
        
        summary_text = (
            f"[CONTEXT COMPACTION SUMMARY]\n"
            f"• Scope Pembahasan Sebelumnya: {summary_body}\n"
            f"• Verified Anchors: Entitas={anchors['entities']}, Tiket={anchors['tickets']}, Periode={anchors['metrics']}\n"
            f"• Context Status: Percakapan berlanjut dengan menjaga seluruh batasan filter di atas."
        )

        compacted_middle = {
            "role": "system",
            "content": summary_text
        }

        # Simpan checkpoint ke persistent SQLite
        self.memory_store.save_checkpoint(
            session_id=session_id,
            turn_count=len(history),
            summary=summary_text,
            anchors=anchors
        )

        compacted_history = [head_msg, compacted_middle] + tail_msgs
        return compacted_history, True
