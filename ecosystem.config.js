module.exports = {
  apps: [
    {
      name: "neural-chatbot",
      cwd: "/home/ubuntu/apps/neural-analytics-chatbot",
      script: "/home/ubuntu/apps/neural-analytics-chatbot/venv/bin/uvicorn",
      args: "app:app --host 127.0.0.1 --port 8508 --workers 2 --proxy-headers --forwarded-allow-ips='*'",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      restart_delay: 4000,
      env: {
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};
