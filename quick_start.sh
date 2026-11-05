#!/usr/bin/env bash
# ==============================================================================
# Neural Analytics Copilot - One-Command Instant Setup & Runner
# ==============================================================================
set -e

echo "🚀 [1/5] Inisialisasi Environment Neural Analytics Copilot..."
cd "$(dirname "$0")"

# 1. Setup Virtualenv jika belum ada
if [ ! -d "venv" ]; then
    echo "📦 [2/5] Membuat Python Virtual Environment (.venv)..."
    python3 -m venv venv
fi

source venv/bin/activate

# 2. Install Dependencies
echo "📥 [3/5] Memeriksa & Menginstall Dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pytest httpx -q

# 3. Jalankan Verification Test Suite
echo "🧪 [4/5] Menjalankan Test Suite (21 Verification Tests)..."
python3 -m pytest tests/ -v

# 4. Jalankan Aplikasi
echo "✨ [5/5] Memulai Server Uvicorn di http://127.0.0.1:8508..."
echo "📊 Dashboard & UI: http://127.0.0.1:8508"
echo "🌐 Live Showcase: https://neural-demo.naufalhal.tech"
echo "Tekan Ctrl+C untuk menghentikan server."

python3 run_server.py
