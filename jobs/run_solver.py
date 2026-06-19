#!/usr/bin/env python3
"""Run a solver over all files in an input directory."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def solver_command(solver: str, solver_bin: str, input_path: Path, args: argparse.Namespace) -> list[str]:
    root = Path(__file__).resolve().parents[1]
    if solver == "CPLEX":
        return [
            sys.executable,
            str(root / "cplex/cplex_diversesat.py"),
            str(input_path),
            str(args.k),
            args.encoding,
            args.se_mode,
        ]
    if solver == "CaDiCaL":
        return [
            sys.executable,
            str(root / "baseline/cadical_enumerate.py"),
            str(input_path),
            str(args.k),
        ]
    if solver == "CaDiCaL-Greedy":
        return [
            sys.executable,
            str(root / "baseline/cadical_greedy.py"),
            str(input_path),
            str(args.k),
        ]
    return [solver_bin, str(input_path)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver", required=True)
    parser.add_argument("--solver-bin", required=True)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--instance-list")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--suffix", default="")
    parser.add_argument("--k", default="")
    parser.add_argument("--encoding", default="")
    parser.add_argument("--se-mode", default="")
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.instance_list:
        names = [line.strip() for line in Path(args.instance_list).read_text().splitlines() if line.strip() and not line.startswith("#")]
        task_id = os.environ.get("SLURM_ARRAY_TASK_ID")
        if task_id:
            idx = int(task_id) - 1
            if idx < 0 or idx >= len(names):
                raise IndexError(f"SLURM_ARRAY_TASK_ID={task_id} outside 1..{len(names)}")
            names = [names[idx]]
        inputs = []
        for name in names:
            path = input_dir / name
            if not path.exists() and args.suffix == ".wcnf":
                path = input_dir / f"{Path(name).stem}.wcnf"
            if not path.exists():
                raise FileNotFoundError(path)
            inputs.append(path)
    else:
        inputs = sorted(p for p in input_dir.rglob("*") if p.is_file() and (not args.suffix or p.name.endswith(args.suffix)))
    if not inputs:
        raise RuntimeError(f"no inputs found in {input_dir} with suffix {args.suffix!r}")

    for idx, path in enumerate(inputs, 1):
        out_path = out_dir / f"{path.name}.out"
        cmd = solver_command(args.solver, args.solver_bin, path, args)
        print(f"[{idx}/{len(inputs)}]", " ".join(cmd), flush=True)
        start = time.time()
        with out_path.open("w") as out:
            try:
                subprocess.run(
                    cmd,
                    stdout=out,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=args.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                out.write(f"@@@ timeout\n>>> Benchmark {path.name} TimeCost {time.time() - start}\n")


if __name__ == "__main__":
    main()

