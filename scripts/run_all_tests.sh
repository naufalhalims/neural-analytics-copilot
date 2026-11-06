#!/usr/bin/env bash
# scripts/run_all_tests.sh
# Regenerasi SELURUH laporan pengujian ke folder reports/ agar halaman /testing
# selalu menampilkan hasil terbaru.
#
# Pemakaian:
#   ./scripts/run_all_tests.sh            # semua suite
#   ./scripts/run_all_tests.sh pytest     # hanya pytest
#   ./scripts/run_all_tests.sh audit      # hanya audit integritas (butuh server 8508 hidup)
#   ./scripts/run_all_tests.sh ocr        # hanya OCR benchmark
set -uo pipefail

BASE_DIR="/home/ubuntu/apps/neural-analytics-chatbot"
cd "$BASE_DIR" || exit 1
PY="./venv/bin/python"
REPORTS="reports"
mkdir -p "$REPORTS"

TARGET="${1:-all}"
FAILED=0

run_pytest() {
    echo "=============================================================="
    echo "[1/3] PYTEST SUITE (25 unit + integrasi)"
    echo "=============================================================="
    $PY -m pytest tests/ -q --junitxml="$REPORTS/junit.xml" || FAILED=1
    echo "[+] Laporan: $REPORTS/junit.xml"
}

run_audit() {
    echo "=============================================================="
    echo "[2/3] AUDIT INTEGRITAS SISTEM (ground-truth & robustness)"
    echo "=============================================================="
    if ! curl -sf --max-time 5 http://127.0.0.1:8508/health >/dev/null; then
        echo "[!] Server 8508 tidak hidup — audit dilewati (jalankan uvicorn dulu)."
        return 0
    fi
    $PY scripts/audit_system_integrity.py || FAILED=1
}

run_ocr() {
    echo "=============================================================="
    echo "[3/3] OCR & SCAN INTEGRITY BENCHMARK (seluruh PDF di vault)"
    echo "=============================================================="
    $PY scripts/benchmark_ocr_all.py || FAILED=1
    $PY scripts/generate_ocr_benchmark_report.py || FAILED=1
}

case "$TARGET" in
    pytest) run_pytest ;;
    audit)  run_audit ;;
    ocr)    run_ocr ;;
    *)      run_pytest; run_audit; run_ocr ;;
esac

echo
echo "=============================================================="
if [ "$FAILED" -eq 0 ]; then
    echo "SEMUA SUITE SELESAI — laporan tersimpan di $REPORTS/"
else
    echo "SELESAI DENGAN CATATAN — cek output di atas."
fi
echo "Lihat hasilnya di: https://neural-demo.naufalhal.tech/testing"
echo "=============================================================="
exit $FAILED
