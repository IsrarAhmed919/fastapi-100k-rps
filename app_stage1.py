#!/usr/bin/env python3
"""Stage 1: async handler plus a connection pool. Two changes from stage 0, nothing else.

  1. `async def` instead of `def`, so requests stay on the event loop rather than being handed
     to a thread-pool worker
  2. asyncpg with a pool created once at startup, so no connection handshake per request

Same query, same data, same machine. Everything else is deliberately unchanged so the
measurement attributes the difference to these two things only.

    .venv/bin/uvicorn app_stage1:app --port 8001
"""
import os
import asyncpg
from fastapi import FastAPI, HTTPException

DSN = os.environ.get("DSN", "postgresql://postgres:bench@localhost:5434/results")
POOL_MIN = int(os.environ.get("POOL_MIN", 10))
POOL_MAX = int(os.environ.get("POOL_MAX", 32))

app = FastAPI(title="Board results, stage 1")
SQL = ("SELECT roll_no, class, name, father_name, school, obtained, total, "
       "percentage, grade, status FROM results WHERE roll_no = $1")


@app.on_event("startup")
async def startup():
    app.state.pool = await asyncpg.create_pool(DSN, min_size=POOL_MIN, max_size=POOL_MAX)


@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()


@app.get("/result/{roll_no}")
async def get_result(roll_no: int):
    row = await app.state.pool.fetchrow(SQL, roll_no)
    if row is None:
        raise HTTPException(404, "roll number not found")
    d = dict(row)
    d["percentage"] = float(d["percentage"])
    return d


@app.get("/health")
async def health():
    return {"ok": True}
