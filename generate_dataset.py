#!/usr/bin/env python3
"""Generate a synthetic board-results dataset at real scale, for load testing.

Why synthetic: the benchmark needs realistic shape and volume, not real students. Bulk-collecting
result data would mean holding personal records of hundreds of thousands of minors, and it would
mean scraping the very servers this project is about. The schema below mirrors a Punjab board
result: roll number ranges, subject list, per-subject marks, totals and grade boundaries, so every
performance number measured against it transfers directly.

    python3 generate_dataset.py --count 400000 --out data/results.csv
"""
import argparse, csv, random, hashlib
from pathlib import Path

SUBJECTS_9 = ["English", "Urdu", "Islamiyat", "Mathematics", "Physics", "Chemistry", "Biology",
              "Pakistan Studies", "Computer Science"]
SUBJECTS_10 = SUBJECTS_9
GRADE_BANDS = [(0.80, "A+"), (0.70, "A"), (0.60, "B"), (0.50, "C"), (0.40, "D"), (0.33, "E")]

FIRST = ["Muhammad", "Ahmed", "Ali", "Hassan", "Usman", "Bilal", "Hamza", "Zain", "Ayesha", "Fatima",
         "Maryam", "Zainab", "Hira", "Sana", "Iqra", "Noor", "Saad", "Umar", "Talha", "Areeba"]
LAST = ["Khan", "Ahmed", "Malik", "Butt", "Raza", "Shah", "Iqbal", "Hussain", "Javed", "Nawaz",
        "Aslam", "Qureshi", "Chaudhry", "Farooq", "Siddiqui", "Abbas"]
SCHOOLS = [f"Govt High School Unit-{i}" for i in range(1, 60)] + \
          [f"Public Model School Campus-{i}" for i in range(1, 40)]


def grade(pct):
    for floor, letter in GRADE_BANDS:
        if pct >= floor:
            return letter
    return "F"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=400_000, help="candidates per class")
    ap.add_argument("--classes", default="9,10")
    ap.add_argument("--out", default="data/results.csv")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    classes = [int(c) for c in args.classes.split(",")]
    subjects = {9: SUBJECTS_9, 10: SUBJECTS_10}
    total_marks = {9: 100 * len(SUBJECTS_9), 10: 100 * len(SUBJECTS_10)}

    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["roll_no", "class", "name", "father_name", "school", "session",
                    *[s.lower().replace(" ", "_") for s in SUBJECTS_9],
                    "obtained", "total", "percentage", "grade", "status"])
        for cls in classes:
            base = 100_000 if cls == 9 else 600_000        # non-overlapping roll ranges, as the boards use
            for i in range(args.count):
                roll = base + i
                # a realistic marks curve: most candidates cluster mid-range, a long weak tail
                ability = min(max(rng.gauss(0.58, 0.16), 0.05), 0.99)
                marks = []
                for _ in subjects[cls]:
                    m = int(min(max(rng.gauss(ability * 100, 9), 0), 100))
                    marks.append(m)
                obtained = sum(marks)
                pct = obtained / total_marks[cls]
                failed = any(m < 33 for m in marks)
                w.writerow([roll, cls,
                            f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                            f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                            rng.choice(SCHOOLS), "Annual 2026",
                            *marks, obtained, total_marks[cls], f"{pct*100:.2f}",
                            "F" if failed else grade(pct),
                            "FAIL" if failed else "PASS"])
    size = out.stat().st_size / 1e6
    print(f"wrote {out}  {len(classes) * args.count:,} records  {size:.1f} MB")
    print("schema mirrors a Punjab board result; no real student data is used anywhere")


if __name__ == "__main__":
    main()
