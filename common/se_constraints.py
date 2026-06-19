#!/usr/bin/env python3
"""Strict symmetry/uniqueness constraints for clean reruns.

This file intentionally does NOT reproduce the historical exp1/exp2 non-strict
SEv1 chain.  The journal rerun uses explicit distinctness:

  SEv1:
    SE-1/2/3 lex-prefix chain
    SE-4 Y_{i,j} <=> V_{i,j} XOR V_{i+1,j}
    SE-5 OR_j Y_{i,j}

  SEv3:
    diagonal dominance V_{j,j} -> V_{i,j}
    explicit pairwise distinctness for every pair of models
"""

from __future__ import annotations

from collections.abc import Callable


ClauseAdder = Callable[[list[int]], None]
Var = Callable[[str], int]
VVar = Callable[[int, int], int]


def add_xor_equivalence(add_clause: ClauseAdder, y: int, a: int, b: int) -> None:
    """Add CNF clauses for y <=> (a XOR b)."""
    add_clause([-a, -b, -y])
    add_clause([-a, b, y])
    add_clause([a, -b, y])
    add_clause([a, b, -y])


def add_strict_sev1(add_clause: ClauseAdder, new_var: Var, v: VVar, k: int, n: int) -> int:
    """Add strict lexicographic SEv1 constraints and return hard-clause count."""
    before = 0
    for i in range(1, k):
        c = lambda j, i=i: new_var(f"C@{i}@{j}")
        y = lambda j, i=i: new_var(f"Y@{i}@{j}")

        # SE-3: the empty prefix is equal.
        add_clause([c(1)])
        before += 1

        for j in range(1, n + 1):
            # SE-1: C_{i,j} and V_{i,j}=1 imply V_{i+1,j}=1.
            add_clause([-c(j), -v(i, j), v(i + 1, j)])
            before += 1

            # SE-4: materialize Y_{i,j} as the XOR difference indicator.
            add_xor_equivalence(add_clause, y(j), v(i, j), v(i + 1, j))
            before += 4

        for j in range(1, n):
            # SE-2: if prefixes match and current bit does not differ, continue.
            add_clause([-c(j), y(j), c(j + 1)])
            before += 1

        # SE-5: adjacent models must be distinct.
        add_clause([y(j) for j in range(1, n + 1)])
        before += 1
    return before


def add_pairwise_distinct(add_clause: ClauseAdder, new_var: Var, v: VVar, k: int, n: int) -> int:
    """Force every pair of model copies to differ on at least one variable."""
    count = 0
    for i in range(1, k + 1):
        for ip in range(i + 1, k + 1):
            diff_vars = []
            for j in range(1, n + 1):
                d = new_var(f"D@{i}@{ip}@{j}")
                add_xor_equivalence(add_clause, d, v(i, j), v(ip, j))
                diff_vars.append(d)
                count += 4
            add_clause(diff_vars)
            count += 1
    return count


def add_sev3_with_distinct(add_clause: ClauseAdder, new_var: Var, v: VVar, k: int, n: int) -> int:
    """Add SEv3 diagonal dominance plus explicit pairwise distinctness."""
    count = 0
    for j in range(1, min(k, n + 1)):
        for i in range(j + 1, k + 1):
            add_clause([-v(j, j), v(i, j)])
            count += 1
    count += add_pairwise_distinct(add_clause, new_var, v, k, n)
    return count


def add_se_constraints(
    mode: str,
    add_clause: ClauseAdder,
    new_var: Var,
    v: VVar,
    k: int,
    n: int,
) -> int:
    if mode == "SEv1":
        return add_strict_sev1(add_clause, new_var, v, k, n)
    if mode == "SEv3":
        return add_sev3_with_distinct(add_clause, new_var, v, k, n)
    raise ValueError(f"unknown SE mode: {mode}")

