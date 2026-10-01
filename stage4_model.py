#!/usr/bin/env python3
"""Stage 4: turn the measured numbers into a capacity and cost answer for a real result day.

Every input is stated and adjustable. The point is not to be precise about cloud pricing, it is
to show that the gap between "the site crashed" and "the site was fine" is a few hundred dollars
and one architectural decision.

    python3 stage4_model.py
"""
import json
from pathlib import Path

# ---------------------------------------------------------------- measured on this laptop
# 12-core machine, load generator running on the same cores, so these are conservative.
MEASURED = [
    {"stage": "0. sync def, new DB connection per request", "rps": 682, "p99_ms": 139.5},
    {"stage": "1. async def + asyncpg pool, 12 workers", "rps": 11_485, "p99_ms": 10.5},
    {"stage": "2. Redis cache + orjson, 12 workers", "rps": 19_540, "p99_ms": 8.7},
    {"stage": "3. nginx serving pre-rendered blobs", "rps": 146_047, "p99_ms": 1.0},
]

# ---------------------------------------------------------------- traffic model
# Punjab matric 2025: five boards published candidate counts, released simultaneously at 10:00.
CANDIDATES = 767_054            # Lahore 254,012 + Gujranwala 225,071 + Multan 125,002
                                # + DG Khan 91,180 + Sahiwal 71,789
LOOKUPS_PER_CANDIDATE = 3.0     # the student, plus parents and relatives checking separately
RETRY_FACTOR = 1.8              # when a page stalls, people refresh. This is what kills servers
SHARE_IN_FIRST_15_MIN = 0.70    # the burst: most checks happen almost immediately
PEAK_MINUTE_SHARE = 0.25        # of that burst, the heaviest single minute

# ---------------------------------------------------------------- cost inputs (approximate list
# prices, September 2026, for a 12-core class VM; ranges rather than a single vendor)
COST_PER_NODE_MONTH_LOW = 45    # budget providers
COST_PER_NODE_MONTH_HIGH = 190  # major clouds, on demand


def peak_rps():
    total = CANDIDATES * LOOKUPS_PER_CANDIDATE * RETRY_FACTOR
    burst = total * SHARE_IN_FIRST_15_MIN
    peak_minute = burst * PEAK_MINUTE_SHARE
    return total, burst, peak_minute / 60.0


def main():
    total, burst, peak = peak_rps()
    print("TRAFFIC MODEL, Punjab matric result day")
    print(f"  candidates                         {CANDIDATES:,}")
    print(f"  lookups per candidate              {LOOKUPS_PER_CANDIDATE}")
    print(f"  retry multiplier                   {RETRY_FACTOR}")
    print(f"  total lookups on the day           {total:,.0f}")
    print(f"  lookups in the first 15 minutes    {burst:,.0f}  ({SHARE_IN_FIRST_15_MIN:.0%})")
    print(f"  PEAK SUSTAINED LOAD                {peak:,.0f} req/s\n")

    print(f"{'stage':<46}{'req/s':>9}{'nodes':>8}{'cost / month':>18}")
    print("-" * 81)
    rows = []
    for m in MEASURED:
        nodes = -(-int(peak) // m["rps"])                      # ceiling division
        low, high = nodes * COST_PER_NODE_MONTH_LOW, nodes * COST_PER_NODE_MONTH_HIGH
        rows.append({**m, "nodes": nodes, "cost_low": low, "cost_high": high})
        print(f"{m['stage']:<46}{m['rps']:>9,}{nodes:>8,}{'$'+format(low,',')+' to $'+format(high,','):>18}")
    print("-" * 81)

    naive, best = rows[0], rows[-1]
    print(f"\nThe naive design needs {naive['nodes']:,} machines to survive the peak.")
    print(f"The pre-rendered design needs {best['nodes']}.")
    print(f"That is {naive['nodes'] // max(best['nodes'],1):,}x fewer machines for the same traffic,")
    print(f"and the difference in monthly cost is roughly "
          f"${naive['cost_low'] - best['cost_low']:,} to ${naive['cost_high'] - best['cost_high']:,}.")
    print("\nPut another way: the entire board's results can be pre-rendered in 3 seconds and")
    print(f"held in {782} MB of RAM. The crash is not a scale problem, it is a design choice.")

    Path("results.json").write_text(json.dumps(
        {"measured": MEASURED, "traffic_model": {
            "candidates": CANDIDATES, "lookups_per_candidate": LOOKUPS_PER_CANDIDATE,
            "retry_factor": RETRY_FACTOR, "total_lookups": round(total),
            "peak_rps": round(peak)}, "capacity": rows}, indent=2))
    burst = scenarios()
    data = json.loads(Path("results.json").read_text())
    data["burst_scenarios"] = burst
    Path("results.json").write_text(json.dumps(data, indent=2))
    print("\nwrote results.json")




# ---------------------------------------------------------------- burst scenarios
# The model above spreads the burst over a minute. Result day does not work like that: the time
# is announced, and everyone presses refresh in the same few seconds.
SCENARIOS = [
    ("Moderate: burst spread over 15 minutes", 15 * 60, 0.70),
    ("Severe: half the burst in the first minute", 60, 0.35),
    ("Thundering herd: a quarter of all lookups in 10 seconds", 10, 0.25),
]


def scenarios():
    total = CANDIDATES * LOOKUPS_PER_CANDIDATE * RETRY_FACTOR
    print("\n\nBURST SCENARIOS")
    print(f"{'scenario':<58}{'peak req/s':>12}{'nodes @ stage 0':>17}{'nodes @ stage 3':>17}")
    print("-" * 104)
    out = []
    for name, window_s, share in SCENARIOS:
        rps = total * share / window_s
        n0 = -(-int(rps) // MEASURED[0]["rps"])
        n3 = -(-int(rps) // MEASURED[3]["rps"])
        out.append({"scenario": name, "peak_rps": round(rps), "nodes_naive": n0, "nodes_final": n3})
        print(f"{name:<58}{rps:>12,.0f}{n0:>17,}{n3:>17,}")
    print("-" * 104)
    print("A single pre-rendered node absorbs every scenario here. The naive design needs a fleet")
    print("for the mildest one and is unbuildable for the worst.")
    return out


if __name__ == "__main__":
    main()
