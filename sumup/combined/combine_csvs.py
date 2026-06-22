#!/usr/bin/env python3
"""Combine per-SE and baseline summary CSVs into one table."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    ("SEv1", ROOT / "sumup/SEv1/results"),
    ("SEv3", ROOT / "sumup/SEv3/results"),
    ("baseline", ROOT / "sumup/baseline/results"),
]
OUT_DIR = ROOT / "sumup/combined/results"
OUT_FILE = OUT_DIR / "all_results.csv"


def main() -> None:
    rows: list[dict[str, str]] = []
    fieldnames = ["source", "csv_file", "Benchmark", "is_OPT", "BEST", "tot_time", "solving_time", "status"]
    for source, directory in SOURCES:
        if not directory.exists():
            print(f"[skip] missing summary dir: {directory}")
            continue
        for csv_path in sorted(directory.glob("*.csv")):
            with csv_path.open(newline="") as handle:
                for row in csv.DictReader(handle):
                    rows.append({"source": source, "csv_file": csv_path.name, **row})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[ok] wrote {OUT_FILE} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
