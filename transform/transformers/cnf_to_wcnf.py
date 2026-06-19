#!/usr/bin/env python3
"""Compile CNF to WCNF for strict SE reruns.

Usage:
  python3 cnf_to_wcnf.py input.cnf output.wcnf K ENCODING SE_MODE

ENCODING in {OH, UNA, BIN}; SE_MODE in {SEv1, SEv3}.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from math import floor, log2
from pathlib import Path

from pysat.formula import CNF, IDPool, WCNF
from pysat.pb import EncType, PBEnc
import pysat.card as card

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.dimacs import load_cnf  # noqa: E402
from common.se_constraints import add_se_constraints  # noqa: E402


PB_ENCODING = EncType.best


def compile_wcnf(cnf: CNF, k: int, encoding: str, se_mode: str) -> tuple[WCNF, int, int, int]:
    encoding = encoding.upper()
    if encoding not in {"OH", "UNA", "BIN"}:
        raise ValueError(f"unsupported encoding {encoding!r}")
    if se_mode not in {"SEv1", "SEv3"}:
        raise ValueError(f"unsupported SE mode {se_mode!r}")

    vpool = IDPool(start_from=1)
    v = lambda i, j: vpool.id(f"V@{i}@{j}")
    u = lambda j, i: vpool.id(f"U@{j}@{i}")
    z = lambda j, i, ip: vpool.id(f"Z@{j}@{i}@{ip}")
    new_var = lambda name: vpool.id(name)

    wcnf = WCNF()
    n = cnf.nv
    obj_sum = 0
    delta = 0

    # K copies of the SAT instance.
    for i in range(1, k + 1):
        for clause in cnf.clauses:
            wcnf.append([v(i, lit) if lit > 0 else -v(i, -lit) for lit in clause])

    if encoding == "OH":
        for j in range(1, n + 1):
            wcnf.extend(
                card.CardEnc.equals(
                    lits=[u(j, i) for i in range(0, k + 1)],
                    bound=1,
                    encoding=card.EncType.cardnetwrk,
                    vpool=vpool,
                )
            )
            wcnf.extend(
                PBEnc.equals(
                    lits=[u(j, i) for i in range(1, k + 1)] + [-v(i, j) for i in range(1, k + 1)],
                    weights=[i for i in range(1, k + 1)] + [1] * k,
                    bound=k,
                    vpool=vpool,
                    encoding=PB_ENCODING,
                )
            )
            for i in range(1, k + 1):
                weight = i * (k - i)
                if weight:
                    wcnf.append([u(j, i)], weight)
                    obj_sum += weight

    elif encoding == "UNA":
        for i in range(2, k + 1):
            for j in range(1, n + 1):
                wcnf.append([-u(j, i), u(j, i - 1)])
        for j in range(1, n + 1):
            wcnf.extend(
                card.CardEnc.equals(
                    lits=[u(j, i) for i in range(1, k + 1)] + [-v(i, j) for i in range(1, k + 1)],
                    bound=k,
                    encoding=card.EncType.cardnetwrk,
                    vpool=vpool,
                )
            )
            for i in range(1, k + 1):
                weight = i * (k - i) - (i - 1) * (k - i + 1)
                if weight > 0:
                    wcnf.append([u(j, i)], weight)
                    obj_sum += weight
                elif weight < 0:
                    wcnf.append([-u(j, i)], -weight)
                    obj_sum -= weight
                    delta -= weight

    elif encoding == "BIN":
        log_k = floor(log2(k))
        for j in range(1, n + 1):
            wcnf.extend(
                PBEnc.equals(
                    lits=[u(j, i) for i in range(0, log_k + 1)] + [-v(i, j) for i in range(1, k + 1)],
                    weights=[2**i for i in range(0, log_k + 1)] + [1] * k,
                    bound=k,
                    vpool=vpool,
                    encoding=PB_ENCODING,
                )
            )
            for i in range(0, log_k + 1):
                wcnf.append([u(j, i)], weight=k * (2**i))
                obj_sum += k * (2**i)
                for ip in range(0, log_k + 1):
                    wcnf.append([-u(j, i), -u(j, ip), z(j, i, ip)])
                    wcnf.append([-z(j, i, ip)], weight=2 ** (i + ip))
                    obj_sum += 2 ** (i + ip)
                    delta += 2 ** (i + ip)

    se_count = add_se_constraints(se_mode, wcnf.append, new_var, v, k, n)
    return wcnf, obj_sum, delta, se_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path")
    parser.add_argument("output_path")
    parser.add_argument("k", type=int)
    parser.add_argument("encoding", choices=["OH", "UNA", "BIN"])
    parser.add_argument("se_mode", choices=["SEv1", "SEv3"])
    args = parser.parse_args()

    start = time.time()
    cnf = load_cnf(args.input_path)
    read_end = time.time()
    wcnf, obj_sum, delta, se_count = compile_wcnf(cnf, args.k, args.encoding, args.se_mode)
    transform_end = time.time()

    os.makedirs(os.path.dirname(args.output_path) or ".", exist_ok=True)
    wcnf.to_file(args.output_path)
    print_end = time.time()

    print(
        f"Benchmark {os.path.basename(args.input_path)} k {args.k} encoding {args.encoding} se {args.se_mode} "
        f"obj_sum {obj_sum} delta {delta} se_hard {se_count} "
        f"whole_trans_time {print_end - start} read_time {read_end - start} "
        f"transform_time {transform_end - read_end} print_time {print_end - transform_end}"
    )


if __name__ == "__main__":
    main()

