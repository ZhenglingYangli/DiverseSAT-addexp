#!/usr/bin/env python3
"""CaDiCaL sequential enumeration baseline."""

from __future__ import annotations

import argparse
import os
import time

from pysat.formula import CNF
from pysat.solvers import Solver


def diversity(models: list[list[int]], n: int) -> int:
    counts = [0] * (n + 1)
    for model in models:
        for lit in model:
            if 0 < lit <= n:
                counts[lit] += 1
    return sum(counts[j] * (len(models) - counts[j]) for j in range(1, n + 1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path")
    parser.add_argument("k", type=int)
    parser.add_argument("--solver-name", default="Cadical195")
    args = parser.parse_args()

    start = time.time()
    cnf = CNF(from_file=args.input_path)
    read_end = time.time()
    models: list[list[int]] = []
    with Solver(name=args.solver_name, bootstrap_with=cnf.clauses) as solver:
        for model in solver.enum_models():
            models.append(model[: cnf.nv])
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

