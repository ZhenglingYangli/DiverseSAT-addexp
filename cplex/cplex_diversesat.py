#!/usr/bin/env python3
"""Unified CPLEX solver for clean strict-SE DiverseSAT reruns."""

from __future__ import annotations

import argparse
import os
import sys
import time
from math import floor, log2
from pathlib import Path

import cplex
from pysat.formula import CNF

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.config import CUTOFF_SECONDS  # noqa: E402
from common.se_constraints import add_se_constraints  # noqa: E402


class CplexBuilder:
    def __init__(self, prob: cplex.Cplex) -> None:
        self.prob = prob
        self.ids: dict[str, int] = {}
        self.names: dict[int, str] = {}
        self.next_id = 1

    def var(
        self,
        name: str,
        obj: float = 0.0,
        var_type: str | None = None,
        lb: float = 0.0,
        ub: float = 1.0,
    ) -> int:
        name = name.replace("@", "_")
        if name not in self.ids:
            idx = self.next_id
            self.next_id += 1
            self.ids[name] = idx
            self.names[idx] = name
            cplex_type = var_type or self.prob.variables.type.binary
            self.prob.variables.add(names=[name], types=[cplex_type], obj=[obj], lb=[lb], ub=[ub])
        elif obj:
            self.prob.objective.set_linear(self.ids[name] - 1, obj)
        return self.ids[name]

    def name(self, lit: int) -> str:
        return self.names[abs(lit)]

    def add_clause(self, lits: list[int]) -> None:
        normalized: list[int] = []
        seen: set[int] = set()
        for lit in lits:
            if -lit in seen:
                return
            if lit not in seen:
                seen.add(lit)
                normalized.append(lit)
        lits = normalized
        if not lits:
            raise ValueError("empty clause cannot be added to CPLEX model")

        vars_in_clause = []
        coeffs = []
        neg_count = 0
        for lit in lits:
            vars_in_clause.append(self.name(lit))
            if lit > 0:
                coeffs.append(1)
            else:
                coeffs.append(-1)
                neg_count += 1
        self.prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair(vars_in_clause, coeffs)],
            senses=["G"],
            rhs=[1 - neg_count],
        )


def create_cplex_instance(cutoff: int) -> cplex.Cplex:
    prob = cplex.Cplex()
    prob.objective.set_sense(prob.objective.sense.maximize)
    prob.parameters.threads.set(1)
    prob.parameters.clocktype.set(1)
    prob.parameters.timelimit.set(cutoff)
    prob.parameters.mip.tolerances.integrality.set(0)
    prob.parameters.mip.tolerances.mipgap.set(0)
    prob.parameters.mip.tolerances.absmipgap.set(0)
    prob.set_log_stream(None)
    prob.set_error_stream(None)
    prob.set_warning_stream(None)
    return prob


def add_cnf_constraints(builder: CplexBuilder, cnf: CNF, k: int, v) -> None:
    for i in range(1, k + 1):
        for clause in cnf.clauses:
            builder.add_clause([v(i, lit) if lit > 0 else -v(i, -lit) for lit in clause])


def add_oh(builder: CplexBuilder, n: int, k: int, v, u) -> None:
    prob = builder.prob
    for j in range(1, n + 1):
        for r in range(0, k + 1):
            builder.var(f"U@{j}@{r}", obj=r * (k - r))
        prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                [builder.name(v(i, j)) for i in range(1, k + 1)] + [builder.name(u(j, r)) for r in range(0, k + 1)],
                [1] * k + [-r for r in range(0, k + 1)],
            )],
            senses=["E"],
            rhs=[0],
        )
        prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair([builder.name(u(j, r)) for r in range(0, k + 1)], [1] * (k + 1))],
            senses=["E"],
            rhs=[1],
        )


def add_qp(builder: CplexBuilder, n: int, k: int, v) -> None:
    prob = builder.prob
    integer = prob.variables.type.integer
    for j in range(1, n + 1):
        o = builder.var(f"O@{j}", obj=k, var_type=integer, lb=0, ub=k)
        prob.objective.set_quadratic_coefficients(o - 1, o - 1, -2.0)
        prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                [builder.name(v(i, j)) for i in range(1, k + 1)] + [builder.name(o)],
                [1] * k + [-1],
            )],
            senses=["E"],
            rhs=[0],
        )


def add_una(builder: CplexBuilder, n: int, k: int, v, u) -> None:
    prob = builder.prob
    for j in range(1, n + 1):
        for r in range(1, k + 1):
            builder.var(f"U@{j}@{r}", obj=r * (k - r) - (r - 1) * (k - r + 1))
        prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                [builder.name(v(i, j)) for i in range(1, k + 1)] + [builder.name(u(j, r)) for r in range(1, k + 1)],
                [1] * k + [-1] * k,
            )],
            senses=["E"],
            rhs=[0],
        )
        for r in range(2, k + 1):
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair([builder.name(u(j, r)), builder.name(u(j, r - 1))], [1, -1])],
                senses=["L"],
                rhs=[0],
            )


def add_bin(builder: CplexBuilder, n: int, k: int, v, u, z) -> None:
    prob = builder.prob
    log_k = floor(log2(k))
    for j in range(1, n + 1):
        for bit in range(0, log_k + 1):
            builder.var(f"U@{j}@{bit}", obj=k * (2**bit))
        prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                [builder.name(u(j, bit)) for bit in range(0, log_k + 1)] + [builder.name(v(i, j)) for i in range(1, k + 1)],
                [2**bit for bit in range(0, log_k + 1)] + [-1] * k,
            )],
            senses=["E"],
            rhs=[0],
        )
        for bit in range(0, log_k + 1):
            for bit2 in range(0, log_k + 1):
                zij = z(j, bit, bit2)
                builder.add_clause([-u(j, bit), -u(j, bit2), zij])
                builder.prob.objective.set_linear(builder.name(zij), -(2 ** (bit + bit2)))


def build_problem(cnf: CNF, k: int, encoding: str, se_mode: str, cutoff: int) -> cplex.Cplex:
    prob = create_cplex_instance(cutoff)
    builder = CplexBuilder(prob)
    n = cnf.nv
    v = lambda i, j: builder.var(f"V@{i}@{j}")
    u = lambda j, r: builder.var(f"U@{j}@{r}")
    z = lambda j, r, rp: builder.var(f"Z@{j}@{r}@{rp}")

    for i in range(1, k + 1):
        for j in range(1, n + 1):
            v(i, j)
    add_cnf_constraints(builder, cnf, k, v)

    if encoding == "QP":
        add_qp(builder, n, k, v)
    elif encoding == "OH":
        add_oh(builder, n, k, v, u)
    elif encoding == "UNA":
        add_una(builder, n, k, v, u)
    elif encoding == "BIN":
        add_bin(builder, n, k, v, u, z)
    else:
        raise ValueError(f"unknown encoding {encoding}")

    add_se_constraints(se_mode, builder.add_clause, lambda name: builder.var(name), v, k, n)
    return prob


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path")
    parser.add_argument("k", type=int)
    parser.add_argument("encoding", choices=["QP", "OH", "UNA", "BIN"])
    parser.add_argument("se_mode", choices=["SEv1", "SEv3"])
    parser.add_argument("--cutoff", type=int, default=CUTOFF_SECONDS)
    args = parser.parse_args()

    start = time.time()
    cnf = CNF(from_file=args.input_path)
    read_end = time.time()
    prob = build_problem(cnf, args.k, args.encoding, args.se_mode, args.cutoff)
    trans_end = time.time()
    prob.solve()
    end = time.time()

    status = prob.solution.status[prob.solution.get_status()]
    feasible = prob.solution.is_primal_feasible()
    opt = int(round(prob.solution.get_objective_value())) if feasible else ""
    print(f"@@@ {status}")
    print(
        f">>> Benchmark {os.path.basename(args.input_path)} k {args.k} encoding {args.encoding} se {args.se_mode} "
        f"OPT {opt} TimeCost {end - start} TimeSolve {end - trans_end} "
        f"TimeRead {read_end - start} TimeTrans {trans_end - read_end}"
    )


if __name__ == "__main__":
    main()

