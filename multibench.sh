#!/bin/bash
# Is 11.5k the server's ceiling or the load generator's? Run N independent generator
# processes and sum them. If the total rises, the single generator was the limit.
cd "$(dirname "$0")"
N=${1:-3}; PORT=${2:-8001}
for i in $(seq 1 $N); do
  timeout 60 .venv/bin/python bench.py --url "http://127.0.0.1:$PORT/result/{}" \
     --conns 32 --seconds 12 --label "gen$i" > mb_$i.txt 2>&1 &
done
wait
awk '/throughput/ {gsub(",","",$2); s+=$2} END {printf "combined throughput: %d req/s across '"$N"' generators\n", s}' mb_*.txt
grep -h "p99" mb_*.txt
rm -f mb_*.txt
