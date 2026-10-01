#!/usr/bin/env python3
"""Stage 2: Redis cache in front of Postgres, plus orjson and no per-request validation.

The insight this stage tests: a published result never changes, so Postgres should be read once
per roll number, ever. Everything after that is a key lookup.

Three changes from stage 1:
  1. Redis read-through cache, no expiry (the data is immutable once published)
  2. orjson instead of the default encoder, returning a Response directly so FastAPI does not
     re-serialise or validate the payload
  3. single-flight on miss: when many requests want the same uncached key at once, one goes to
     the database and the rest wait for it. Set SINGLE_FLIGHT=0 to see the thundering herd.

    .venv/bin/uvicorn app_stage2:app --port 8002 --workers 12
"""
import asyncio
import os
import asyncpg
import orjson
import redis.asyncio as aioredis
from fastapi import FastAPI, Response

DSN = os.environ.get("DSN", "postgresql://postgres:bench@localhost:5434/results")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6380/0")
SINGLE_FLIGHT = os.environ.get("SINGLE_FLIGHT", "1") == "1"

app = FastAPI(title="Board results, stage 2")
SQL = ("SELECT roll_no, class, name, father_name, school, obtained, total, "
       "percentage, grade, status FROM results WHERE roll_no = $1")
_inflight: dict[int, asyncio.Future] = {}


@app.on_event("startup")
async def startup():
    app.state.pool = await asyncpg.create_pool(DSN, min_size=4, max_size=16)
    app.state.redis = aioredis.from_url(REDIS_URL, decode_responses=False)


@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()
    await app.state.redis.aclose()


async def _from_db(roll_no: int) -> bytes | None:
    row = await app.state.pool.fetchrow(SQL, roll_no)
    if row is None:
        return None
    d = dict(row)
    d["percentage"] = float(d["percentage"])
    blob = orjson.dumps(d)
    await app.state.redis.set(f"r:{roll_no}", blob)      # no TTL: results are immutable
    return blob


@app.get("/result/{roll_no}")
async def get_result(roll_no: int):
    blob = await app.state.redis.get(f"r:{roll_no}")
    if blob is not None:
        return Response(blob, media_type="application/json")

    if not SINGLE_FLIGHT:
        blob = await _from_db(roll_no)
    else:
        fut = _inflight.get(roll_no)
        if fut is None:                                   # first caller does the work
            fut = asyncio.get_running_loop().create_future()
            _inflight[roll_no] = fut
            try:
                blob = await _from_db(roll_no)
                fut.set_result(blob)
            except Exception as exc:
                fut.set_exception(exc)
                raise
            finally:
                _inflight.pop(roll_no, None)
        else:                                             # everyone else waits for that one
            blob = await fut

    if blob is None:
        return Response(orjson.dumps({"detail": "roll number not found"}),
                        status_code=404, media_type="application/json")
    return Response(blob, media_type="application/json")


@app.get("/health")
async def health():
    return Response(b'{"ok":true}', media_type="application/json")
