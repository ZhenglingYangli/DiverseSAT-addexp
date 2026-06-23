#!/usr/bin/env python3
"""Check whether new-exps can see the original cluster resources."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codes/SEv1"))

from common.config import DEFAULT_BENCH_DIR, MAXSAT_DEFAULT_BINS  # noqa: E402


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


def resolve_default_path(path: str) -> Path:
    return Path(path.replace("$ROOT", str(ROOT)))


def check_executable(label: str, env_name: str, default_path: str) -> bool:
    path = Path(os.environ[env_name]) if env_name in os.environ else resolve_default_path(default_path)
    if path.exists() and os.access(path, os.X_OK):
        ok(f"{label}: {path}")
        return True
    warn(f"{label} executable not found: set {env_name} or check default path {path}")
    return False


def main() -> int:
    success = True

    instance_list = ROOT / "codes/289_instances.txt"
    benchmarks = Path(os.environ.get("BENCH_DIR", DEFAULT_BENCH_DIR))
    if not instance_list.exists():
        fail("missing codes/289_instances.txt")
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

    check_executable("CASH", "CASH_BIN", MAXSAT_DEFAULT_BINS["CASH"])
    check_executable("MaxHS", "MAXHS_BIN", MAXSAT_DEFAULT_BINS["MaxHS"])
    check_executable("WMaxCDCL", "WMAXCDCL_BIN", MAXSAT_DEFAULT_BINS["WMaxCDCL"])

    if shutil.which("sbatch"):
        ok("SLURM sbatch available")
    else:
        warn("sbatch not found; generate/test can run locally, but submission needs SLURM")

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
