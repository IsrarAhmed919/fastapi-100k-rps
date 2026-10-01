#!/usr/bin/env python3
"""Two charts for the write-up: throughput per stage, and latency per stage."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = json.load(open("results.json"))
m = d["measured"]
labels = ["0. sync,\nconn per request", "1. async +\npool", "2. Redis +\norjson", "3. nginx +\npre-rendered"]
rps = [x["rps"] for x in m]
p99 = [x["p99_ms"] for x in m]
peak = d["burst_scenarios"][2]["peak_rps"]

fig, ax = plt.subplots(1, 2, figsize=(13, 5))
colors = ["#c0392b", "#d98324", "#2f6fb2", "#2e8b57"]

b = ax[0].bar(labels, rps, color=colors)
ax[0].set_yscale("log")
ax[0].set_ylabel("requests per second (log scale)")
ax[0].set_title("Throughput, same laptop, same data, same query")
for rect, v in zip(b, rps):
    ax[0].text(rect.get_x() + rect.get_width()/2, v*1.15, f"{v:,}", ha="center", fontweight="bold")
ax[0].axhline(peak, ls="--", c="#555", lw=1.2)
ax[0].text(0.02, peak*1.2, f"result-day peak, thundering herd: {peak:,} req/s",
           transform=ax[0].get_yaxis_transform(), fontsize=9, color="#555")
ax[0].set_ylim(300, 400_000)

b2 = ax[1].bar(labels, p99, color=colors)
ax[1].set_ylabel("p99 latency (ms)")
ax[1].set_title("Tail latency: what the slowest 1% of students experience")
for rect, v in zip(b2, p99):
    ax[1].text(rect.get_x() + rect.get_width()/2, v + 3, f"{v} ms", ha="center", fontweight="bold")

for a in ax:
    a.grid(axis="y", alpha=.25)
    a.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig("results_chart.png", dpi=150)
print("wrote results_chart.png")
