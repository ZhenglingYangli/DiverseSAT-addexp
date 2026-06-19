#!/usr/bin/env python3
"""Run CNF->WCNF transformations over an instance list."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def read_instances(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench-dir", required=True)
    parser.add_argument("--instance-list", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--k", required=True)
    parser.add_argument("--encoding", required=True)
    parser.add_argument("--se-mode", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    transformer = root / "transform/transformers/cnf_to_wcnf.py"
    bench_dir = Path(args.bench_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    instances = read_instances(Path(args.instance_list))
    task_id = os.environ.get("SLURM_ARRAY_TASK_ID")
    if task_id:
        idx = int(task_id) - 1
        if idx < 0 or idx >= len(instances):
            raise IndexError(f"SLURM_ARRAY_TASK_ID={task_id} outside 1..{len(instances)}")
        instances = [instances[idx]]

    for name in instances:
        in_path = bench_dir / name
        if not in_path.exists():
            raise FileNotFoundError(f"missing benchmark: {in_path}")
        out_path = out_dir / f"{Path(name).stem}.wcnf"
        cmd = [
            sys.executable,
            str(transformer),
            str(in_path),
            str(out_path),
            str(args.k),
            args.encoding,
            args.se_mode,
        ]
        print("[transform]", " ".join(cmd), flush=True)
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()

