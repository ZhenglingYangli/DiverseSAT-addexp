#!/usr/bin/env python3
"""Aggregate baseline solver logs into CSV files."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "sumup/_common/sumup_common.py"
RESULT_ROOT = ROOT / "results/baseline"
OUT_DIR = ROOT / "sumup/baseline/results"
SOLVERS = ["cadical", "cadical_greedy"]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for solver in SOLVERS:
        results_dir = RESULT_ROOT / solver
        if not results_dir.exists():
            print(f"[skip] missing results dir: {results_dir}")
            continue
        subprocess.run([
            sys.executable,
            str(COMMON),
            "--results-dir",
            str(results_dir),
            "--out-dir",
            str(OUT_DIR),
        ], check=True)


if __name__ == "__main__":
    main()
