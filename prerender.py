#!/usr/bin/env python3
"""Stage 3: pre-render every result to a static JSON file at publish time.

The whole argument of this project in one script. A published result never changes, so there is
no reason to compute anything per request. Render once, serve bytes forever.

Files are written to /dev/shm (RAM) rather than disk, which is what a real deployment would do
for an immutable dataset of this size, and which also keeps the laptop's nearly-full disk out of
the measurement.

Sharded into subdirectories because a single directory with hundreds of thousands of entries is
slow to traverse on most filesystems.

    python3 prerender.py --count 200000 --out /dev/shm/results
"""
import argparse, os, time
import orjson
import psycopg2

DSN = os.environ.get("DSN", "postgresql://postgres:bench@localhost:5434/results")
COLS = ["roll_no", "class", "name", "father_name", "school", "obtained", "total",
        "percentage", "grade", "status"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=200_000)
    ap.add_argument("--start", type=int, default=100_000)
    ap.add_argument("--out", default="/dev/shm/results")
    args = ap.parse_args()

    t0 = time.time()
    conn = psycopg2.connect(DSN)
    cur = conn.cursor(name="prerender")           # server-side cursor: do not load 200k rows at once
    cur.itersize = 10_000
    cur.execute(f"SELECT {','.join(COLS)} FROM results WHERE roll_no >= %s "
                f"ORDER BY roll_no LIMIT %s", (args.start, args.count))

    written = 0
    for row in cur:
        d = dict(zip(COLS, row))
        d["percentage"] = float(d["percentage"])
        roll = d["roll_no"]
        shard = os.path.join(args.out, str(roll // 1000))   # 1000 files per directory
        os.makedirs(shard, exist_ok=True)
        with open(os.path.join(shard, f"{roll}.json"), "wb") as fh:
            fh.write(orjson.dumps(d))
        written += 1
        if written % 50_000 == 0:
            print(f"  {written:,} blobs, {time.time()-t0:.0f}s", flush=True)
    cur.close(); conn.close()
    total = sum(len(files) for _, _, files in os.walk(args.out))
    print(f"wrote {written:,} blobs in {time.time()-t0:.0f}s ({total:,} files on disk)")


if __name__ == "__main__":
    main()
