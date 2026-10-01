#!/bin/bash
# Isolate the two variables: connection-pool size and worker processes.
cd "$(dirname "$0")"
stop() { pgrep -f "uvicorn app_stage1" | xargs -r kill 2>/dev/null; sleep 2; }
run() {   # $1 pool  $2 workers
  stop
  POOL_MAX=$1 nohup .venv/bin/uvicorn app_stage1:app --host 127.0.0.1 --port 8001 \
      --workers $2 --log-level warning > stage1.log 2>&1 &
  sleep 8
  timeout 60 .venv/bin/python bench.py --url "http://127.0.0.1:8001/result/{}" \
      --conns 64 --seconds 10 --label "pool=$1 workers=$2" | grep -E "throughput|p99"
}
run 8 1
run 32 1
run 64 1
run 32 4
run 32 8
stop
