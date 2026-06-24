#!/usr/bin/env python3
"""Shared job runner for solver-oriented strict rerun directories."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTERNAL_SOLVERS = {"CPLEX", "CaDiCaL", "CaDiCaL-Greedy"}


def solver_command(solver: str, solver_bin: str, input_path: Path, args: argparse.Namespace) -> list[str]:
    if solver == "CPLEX":
        return [sys.executable, str(ROOT / "cplex/cplex_diversesat.py"), str(input_path), str(args.k), args.encoding, args.se_mode]
    if solver == "CaDiCaL":
        return [sys.executable, str(ROOT / "cadical/cadical_enumerate.py"), str(input_path), str(args.k)]
    if solver == "CaDiCaL-Greedy":
        return [sys.executable, str(ROOT / "cadical_greedy/cadical_greedy.py"), str(input_path), str(args.k)]
    solver_path = Path(solver_bin).expanduser()
    if solver_path.parent != Path(".") or solver_bin.startswith(("/", ".", "~")):
        solver_bin = str(solver_path.resolve())
    return [solver_bin, str(input_path.resolve())]


def selected_inputs(input_dir: Path, instance_list: str | None, suffix: str) -> list[Path]:
    if instance_list:
        names = [line.strip() for line in Path(instance_list).read_text().splitlines() if line.strip() and not line.startswith("#")]
        task_id = os.environ.get("SLURM_ARRAY_TASK_ID")
        if task_id:
            idx = int(task_id) - 1
            if idx < 0 or idx >= len(names):
                raise IndexError(f"SLURM_ARRAY_TASK_ID={task_id} outside 1..{len(names)}")
            names = [names[idx]]
        inputs = []
        for name in names:
            path = input_dir / name
            if not path.exists() and suffix == ".wcnf":
                path = input_dir / f"{Path(name).stem}.wcnf"
            if not path.exists():
                raise FileNotFoundError(path)
            inputs.append(path)
        return inputs
    return sorted(p for p in input_dir.rglob("*") if p.is_file() and (not suffix or p.name.endswith(suffix)))


def main(argv: list[str] | None = None) -> None:
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
    args = parser.parse_args(argv)

    input_dir = Path(args.input_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = selected_inputs(input_dir, args.instance_list, args.suffix)
    if not inputs:
        raise RuntimeError(f"no inputs found in {input_dir} with suffix {args.suffix!r}")

    for idx, path in enumerate(inputs, 1):
        out_path = out_dir / f"{path.name}.out"
        cmd = solver_command(args.solver, args.solver_bin, path, args)
        print(f"[{idx}/{len(inputs)}]", " ".join(cmd), flush=True)
        start = time.time()
        with out_path.open("w") as out:
            try:
                if args.solver in INTERNAL_SOLVERS:
                    subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT, text=True, timeout=args.timeout, check=False)
                else:
                    work_root = out_dir / "_work"
                    work_root.mkdir(parents=True, exist_ok=True)
                    with tempfile.TemporaryDirectory(prefix=f"{args.solver}-{path.stem}-", dir=work_root) as work_dir:
                        subprocess.run(
                            cmd,
                            stdout=out,
                            stderr=subprocess.STDOUT,
                            text=True,
                            timeout=args.timeout,
                            check=False,
                            cwd=work_dir,
                        )
                    try:
                        work_root.rmdir()
                    except OSError:
                        pass
            except subprocess.TimeoutExpired:
                out.write(f"@@@ timeout\n>>> Benchmark {path.name} TimeCost {time.time() - start}\n")


if __name__ == "__main__":
    main()
