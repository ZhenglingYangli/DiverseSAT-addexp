#!/usr/bin/env python3
"""Diversity-aware greedy SAT baseline using PySAT RC2.

This is the journal strict CaDiCaL-greedy baseline: choose one SAT model, then
iteratively choose a distinct model maximizing distance to the models selected so far.
It is heuristic and does not prove optimality.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import time

from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
from pysat.solvers import Solver

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.dimacs import load_cnf  # noqa: E402


def diversity(models: list[list[int]]) -> int:
    total = 0
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            total += sum(a != b for a, b in zip(models[i], models[j]))
    return total


def normalize_model(model: list[int], n: int) -> list[int]:
    """Return a complete {-1, 1} assignment for variables 1..n."""
    assigned = {abs(lit): 1 if lit > 0 else -1 for lit in model if abs(lit) <= n}
    return [assigned.get(var, -1) for var in range(1, n + 1)]


def blocking_clause(model: list[int]) -> list[int]:
    """Forbid selecting this full assignment again."""
    return [-(var + 1) if value > 0 else var + 1 for var, value in enumerate(model)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path")
    parser.add_argument("k", type=int)
    parser.add_argument("--cutoff", type=int, default=7200)
    parser.add_argument("--solver-name", default="Cadical195")
    args = parser.parse_args()

    start = time.time()
    base_cnf = load_cnf(args.input_path)
    read_end = time.time()
    models: list[list[int]] = []

    with Solver(name=args.solver_name, bootstrap_with=base_cnf.clauses) as solver:
        if solver.solve():
            models.append(normalize_model(solver.get_model(), base_cnf.nv))

    one_counts = [0] * (base_cnf.nv + 1)
    zero_counts = [0] * (base_cnf.nv + 1)
    for var, val in enumerate(models[0] if models else [], 1):
        if val > 0:
            one_counts[var] += 1
        else:
            zero_counts[var] += 1

    while models and len(models) < args.k and time.time() - start < args.cutoff:
        wcnf = WCNF()
        for clause in base_cnf.clauses:
            wcnf.append(clause)
        for selected in models:
            wcnf.append(blocking_clause(selected))
        for var in range(1, base_cnf.nv + 1):
            if one_counts[var]:
                wcnf.append([-var], one_counts[var])
            if zero_counts[var]:
                wcnf.append([var], zero_counts[var])
        with RC2(wcnf) as rc2:
            model = rc2.compute()
        if model is None:
            break
        trimmed = normalize_model(model, base_cnf.nv)
        models.append(trimmed)
        for var, val in enumerate(trimmed, 1):
            if val > 0:
                one_counts[var] += 1
            else:
                zero_counts[var] += 1

    elapsed = time.time() - start
    opt = diversity(models) if len(models) == args.k else ""
    status = "completed" if len(models) == args.k else "incomplete"
    print(f"@@@ {status}")
    print(
        f">>> Benchmark {os.path.basename(args.input_path)} k {args.k} models {len(models)} "
        f"OPT {opt} TimeCost {elapsed} TimeSolve {elapsed - (read_end - start)} "
        f"TimeRead {read_end - start} TimeTrans 0"
    )


if __name__ == "__main__":
    main()

