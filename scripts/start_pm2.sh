#!/bin/bash
pm2 start /home/ubuntu/apps/neural-analytics-chatbot/venv/bin/uvicorn --name "neural-chatbot" --cwd /home/ubuntu/apps/neural-analytics-chatbot -- app:app --host 127.0.0.1 --port 8508
pm2 save
