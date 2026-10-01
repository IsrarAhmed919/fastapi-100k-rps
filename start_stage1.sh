#!/bin/bash
cd "$(dirname "$0")"
pgrep -f "uvicorn app_stage1" | xargs -r kill 2>/dev/null; sleep 2
POOL_MAX=${POOL_MAX:-32} nohup .venv/bin/uvicorn app_stage1:app --host 127.0.0.1 --port 8001 \
    --workers ${WORKERS:-12} --log-level warning > stage1.log 2>&1 &
sleep 8
curl -s http://127.0.0.1:8001/health
