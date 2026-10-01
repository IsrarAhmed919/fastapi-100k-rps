#!/usr/bin/env python3
"""Load generator with honest percentiles. No dependencies beyond the standard library.

Reports p50, p95 and p99 rather than a mean, because the mean hides the student whose request
took four seconds. Uses persistent keep-alive connections, which is what a real client does.

    .venv/bin/python bench.py --url http://127.0.0.1:8000/result/{} --conns 64 --seconds 15
"""
import argparse, asyncio, random, statistics, time


async def worker(host, port, path_tpl, ids, stop_at, lat, errors):
    try:
        reader, writer = await asyncio.open_connection(host, port)
    except Exception:
        errors.append("connect"); return
    while time.perf_counter() < stop_at:
        path = path_tpl.format(random.choice(ids))
        req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: keep-alive\r\n\r\n"
        t0 = time.perf_counter()
        try:
            writer.write(req.encode()); await writer.drain()
            length, status = None, None
            while True:                                   # headers
                line = await reader.readline()
                if not line:
                    raise ConnectionError("closed")
                if status is None and line.startswith(b"HTTP/"):
                    status = int(line.split()[1])
                if line.lower().startswith(b"content-length:"):
                    length = int(line.split(b":")[1])
                if line in (b"\r\n", b"\n"):
                    break
            if length:
                await reader.readexactly(length)
            lat.append(time.perf_counter() - t0)
            if status and status >= 500:
                errors.append(str(status))
        except Exception as exc:
            errors.append(type(exc).__name__)
            try:
                reader, writer = await asyncio.open_connection(host, port)
            except Exception:
                return
    writer.close()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="e.g. http://127.0.0.1:8000/result/{}")
    ap.add_argument("--conns", type=int, default=64)
    ap.add_argument("--seconds", type=float, default=15)
    ap.add_argument("--id-min", type=int, default=100_000)
    ap.add_argument("--id-max", type=int, default=499_999)
    ap.add_argument("--hot", type=int, default=0,
                    help="if set, draw from this many distinct ids to simulate a hot key set")
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    rest = args.url.split("://", 1)[1]
    hostport, path_tpl = rest.split("/", 1)
    path_tpl = "/" + path_tpl
    host, _, port = hostport.partition(":")
    port = int(port or 80)

    ids = (random.sample(range(args.id_min, args.id_max), args.hot) if args.hot
           else list(range(args.id_min, args.id_max)))

    lat, errors = [], []
    stop_at = time.perf_counter() + args.seconds
    t0 = time.perf_counter()
    await asyncio.gather(*[worker(host, port, path_tpl, ids, stop_at, lat, errors)
                           for _ in range(args.conns)])
    elapsed = time.perf_counter() - t0

    if not lat:
        print(f"no successful requests. errors: {errors[:5]}"); return
    lat.sort()
    pct = lambda p: lat[int(len(lat) * p) - 1] * 1000
    print(f"{args.label or args.url}")
    print(f"  requests      {len(lat):,} in {elapsed:.1f}s")
    print(f"  throughput    {len(lat)/elapsed:,.0f} req/s   ({args.conns} connections)")
    print(f"  latency p50   {pct(.50):7.2f} ms")
    print(f"  latency p95   {pct(.95):7.2f} ms")
    print(f"  latency p99   {pct(.99):7.2f} ms")
    print(f"  errors        {len(errors)}")


if __name__ == "__main__":
    asyncio.run(main())
