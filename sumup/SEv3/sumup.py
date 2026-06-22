#!/usr/bin/env python3
"""Aggregate SEv3 solver logs into CSV files."""

from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "codes/SEv3"))
from common.config import DEFAULT_BENCH_DIR  # noqa: E402

COMMON = ROOT / "sumup/_common/sumup_common.py"
RESULT_ROOT = ROOT / "results/SEv3"
OUT_DIR = ROOT / "sumup/SEv3/results"
SOLVERS = ["cplex", "cash", "maxhs", "wmaxcdcl"]


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
            "--bench-dir",
            os.environ.get("BENCH_DIR", DEFAULT_BENCH_DIR),
        ], check=True)


if __name__ == "__main__":
    main()
