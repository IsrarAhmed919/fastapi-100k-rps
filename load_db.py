#!/usr/bin/env python3
"""Load the synthetic results into Postgres with COPY, then index the lookup key.

COPY rather than INSERT: 800k rows one at a time through the driver takes minutes, COPY takes
seconds. That difference is itself one of the lessons of this project.
"""
import csv, os, sys, time
import psycopg2

DSN = os.environ.get("DSN", "postgresql://postgres:bench@localhost:5434/results")
SCHEMA = """
DROP TABLE IF EXISTS results;
CREATE TABLE results (
  roll_no int PRIMARY KEY, class smallint, name text, father_name text, school text,
  session text, english smallint, urdu smallint, islamiyat smallint, mathematics smallint,
  physics smallint, chemistry smallint, biology smallint, pakistan_studies smallint,
  computer_science smallint, obtained smallint, total smallint, percentage numeric(5,2),
  grade text, status text
);
"""

def main(path="data/results.csv"):
    t0 = time.time()
    conn = psycopg2.connect(DSN); conn.autocommit = True
    cur = conn.cursor()
    cur.execute(SCHEMA)
    with open(path) as fh:
        cur.copy_expert("COPY results FROM STDIN WITH CSV HEADER", fh)
    cur.execute("ANALYZE results;")
    cur.execute("SELECT count(*) FROM results;")
    n = cur.fetchone()[0]
    print(f"loaded {n:,} rows in {time.time()-t0:.1f}s")
    cur.execute("SELECT pg_size_pretty(pg_total_relation_size('results'));")
    print("table size:", cur.fetchone()[0])

if __name__ == "__main__":
    main(*sys.argv[1:])
