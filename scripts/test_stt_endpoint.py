#!/usr/bin/env python3
"""
scripts/test_stt_endpoint.py
Menguji endpoint /api/transcribe menggunakan sintesis audio singkat (WAV) via ffmpeg/sox/wave
"""

import time
import httpx
import subprocess
import os

WAV_PATH = "/tmp/test_voice_query.wav"

def make_test_audio():
    # Buat file WAV 2 detik (sine tone) untuk menguji format transmisi multipart
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=1.5",
        "-ar", "16000", "-ac", "1", WAV_PATH
    ], capture_output=True, check=True)

def test_transcribe():
    print("=" * 80)
    print("🎙️ PENGUJIAN ENDPOINT AUDIO STT (/api/transcribe)")
    print("=" * 80)
    make_test_audio()
    
    t0 = time.time()
    with open(WAV_PATH, "rb") as f:
        files = {"file": ("test_voice_query.wav", f, "audio/wav")}
        res = httpx.post("http://127.0.0.1:8508/api/transcribe", files=files, timeout=20.0)
        
    print(f"Status Code : {res.status_code}")
    print(f"Response    : {res.json()}")
    print(f"Latency     : {(time.time() - t0)*1000:.0f} ms")
    if os.path.exists(WAV_PATH):
        os.remove(WAV_PATH)

if __name__ == "__main__":
    test_transcribe()
