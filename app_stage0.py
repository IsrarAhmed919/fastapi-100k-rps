#!/usr/bin/env python3
"""Stage 0: the naive version, close to how most result portals are actually written.

Three deliberate mistakes, all common:
  1. a blocking `def` handler, so every request occupies a thread-pool worker
  2. a new database connection per request
  3. no caching, so an immutable row is fetched from Postgres every single time

    .venv/bin/uvicorn app_stage0:app --port 8000
"""
import os
import psycopg2
from fastapi import FastAPI, HTTPException

DSN = os.environ.get("DSN", "postgresql://postgres:bench@localhost:5434/results")
app = FastAPI(title="Board results, stage 0")


@app.get("/result/{roll_no}")
def get_result(roll_no: int):
    conn = psycopg2.connect(DSN)              # a fresh TCP connection and auth handshake per request
    try:
        cur = conn.cursor()
        cur.execute("SELECT roll_no, class, name, father_name, school, obtained, total, "
                    "percentage, grade, status FROM results WHERE roll_no = %s", (roll_no,))
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(404, "roll number not found")
    keys = ["roll_no", "class", "name", "father_name", "school", "obtained", "total",
            "percentage", "grade", "status"]
    return dict(zip(keys, (float(v) if hasattr(v, "quantize") else v for v in row)))


@app.get("/health")
def health():
    return {"ok": True}
