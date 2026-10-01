#!/bin/bash
cd "$(dirname "$0")"
stop() { pgrep -f "uvicorn app_stage1" | xargs -r kill 2>/dev/null; sleep 3; }
run() {
  stop
  POOL_MAX=$1 nohup .venv/bin/uvicorn app_stage1:app --host 127.0.0.1 --port 8001 \
      --workers $2 --log-level warning > stage1.log 2>&1 &
  sleep 8
  # warm-up first: JIT-free Python still benefits from warm caches and an established pool
  timeout 40 .venv/bin/python bench.py --url "http://127.0.0.1:8001/result/{}" --conns 64 --seconds 5 >/dev/null
  timeout 60 .venv/bin/python bench.py --url "http://127.0.0.1:8001/result/{}" \
      --conns 64 --seconds 15 --label "pool=$1 workers=$2" | grep -E "throughput|p50|p99"
}
run 32 1
run 32 1
run 32 8
run 32 12
stop
