#!/usr/bin/env python3
"""CaDiCaL sequential enumeration baseline."""

from __future__ import annotations

import argparse
from itertools import product
import os
from pathlib import Path
import sys
import time

from pysat.solvers import Solver

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.dimacs import load_cnf  # noqa: E402


def diversity(models: list[list[int]], n: int) -> int:
    counts = [0] * (n + 1)
    for model in models:
        for lit in model:
            if 0 < lit <= n:
                counts[lit] += 1
    return sum(counts[j] * (len(models) - counts[j]) for j in range(1, n + 1))


def expand_full_models(model: list[int], n: int):
    """Yield full assignments for header variables, including unconstrained ones."""
    assigned = {abs(lit): lit > 0 for lit in model if abs(lit) <= n}
    missing = [var for var in range(1, n + 1) if var not in assigned]
    for values in product([False, True], repeat=len(missing)):
        full = []
        free_values = dict(zip(missing, values))
        for var in range(1, n + 1):
            value = assigned.get(var, free_values.get(var, False))
            full.append(var if value else -var)
        yield full


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path")
    parser.add_argument("k", type=int)
    parser.add_argument("--solver-name", default="Cadical195")
    args = parser.parse_args()

    start = time.time()
    cnf = load_cnf(args.input_path)
    read_end = time.time()
    models: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    with Solver(name=args.solver_name, bootstrap_with=cnf.clauses) as solver:
        for model in solver.enum_models():
            for full in expand_full_models(model, cnf.nv):
                key = tuple(full)
                if key in seen:
                    continue
                seen.add(key)
                models.append(full)
                if len(models) == args.k:
                    break
            if len(models) == args.k:
                break

    dist = diversity(models, cnf.nv) if models else 0
    elapsed = time.time() - start
    status = "completed" if len(models) == args.k else "incomplete"
    print(f"@@@ {status}")
    print(
        f">>> Benchmark {os.path.basename(args.input_path)} k {args.k} nb_model {len(models)} "
        f"OPT {dist} TimeCost {elapsed} TimeSolve {elapsed - (read_end - start)} "
        f"TimeRead {read_end - start} TimeTrans 0"
    )


if __name__ == "__main__":
    main()

