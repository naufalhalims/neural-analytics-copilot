#!/bin/bash
cd /home/ubuntu/apps/neural-analytics-chatbot
# Jalankan Uvicorn dengan production mode (2 workers, proxy header forwarding)
exec ./venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8508 --workers 2 --proxy-headers --forwarded-allow-ips='*'
