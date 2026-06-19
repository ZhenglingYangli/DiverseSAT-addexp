#!/usr/bin/env python3
"""Check whether a copied new-exps directory is ready on a fresh server."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def ok(message: str) -> None:
    print(f"[ok] {message}")


def warn(message: str) -> None:
    print(f"[warn] {message}")


def fail(message: str) -> None:
    print(f"[fail] {message}")


def check_python_module(name: str) -> bool:
    try:
        __import__(name)
    except Exception as exc:
        fail(f"python module missing: {name} ({exc})")
        return False
    ok(f"python module available: {name}")
    return True


def check_executable(label: str, env_name: str, default_rel: str) -> bool:
    path = Path(os.environ.get(env_name, ROOT / default_rel))
    if path.exists() and os.access(path, os.X_OK):
        ok(f"{label}: {path}")
        return True
    warn(f"{label} executable not found: set {env_name} or place it at {ROOT / default_rel}")
    return False


def main() -> int:
    success = True

    instance_list = ROOT / "instances/289_instances.txt"
    benchmarks = ROOT / "benchmarks"
    if not instance_list.exists():
        fail("missing instances/289_instances.txt")
        success = False
    else:
        names = [line.strip() for line in instance_list.read_text().splitlines() if line.strip()]
        missing = [name for name in names if not (benchmarks / name).exists()]
        if missing:
            fail(f"missing benchmark CNFs: {len(missing)}")
            for name in missing[:20]:
                print(f"  - {name}")
            success = False
        else:
            ok(f"all benchmark CNFs present: {len(names)}")

    success = check_python_module("pysat") and success
    check_python_module("psutil")
    if not check_python_module("cplex"):
        warn("CPLEX jobs will fail until IBM CPLEX Python bindings and license are configured")

    check_executable("CASH", "CASH_BIN", "solvers/MaxSAT/cashwmaxsat-disjcom")
    check_executable("MaxHS", "MAXHS_BIN", "solvers/MaxSAT/maxhs")
    check_executable("WMaxCDCL", "WMAXCDCL_BIN", "solvers/MaxSAT/wmaxcdcl")

    if shutil.which("sbatch"):
        ok("SLURM sbatch available")
    else:
        warn("sbatch not found; generate/test can run locally, but submission needs SLURM")

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())

