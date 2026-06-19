#!/usr/bin/env python3
"""Aggregate clean rerun logs from new-exps/results into CSV files."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from math import floor, log2


DIR_RE = re.compile(r"^(?P<solver>.+?)-(?:(?P<enc>QP|OH|UNA|BIN)-)?k(?P<k>\d+)(?:-(?P<se>SEv1|SEv3))?$")


def strip_suffix(name: str) -> str:
    for suffix in (".wcnf.out", ".cnf.out", ".out", ".wcnf", ".cnf"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name


def original_var_count(bench_dir: Path, benchmark: str) -> int | None:
    cnf_path = bench_dir / f"{benchmark}.cnf"
    if not cnf_path.exists():
        return None
    for line in cnf_path.read_text(errors="replace").splitlines():
        if line.startswith("p cnf"):
            parts = line.split()
            if len(parts) >= 4:
                return int(parts[2])
    return None


def objective_offsets(encoding: str, k: int, n: int) -> tuple[int, int]:
    obj_sum = 0
    delta = 0
    if encoding == "OH":
        obj_sum = n * sum(r * (k - r) for r in range(1, k + 1))
    elif encoding == "UNA":
        for r in range(1, k + 1):
            weight = r * (k - r) - (r - 1) * (k - r + 1)
            obj_sum += n * abs(weight)
            if weight < 0:
                delta += n * (-weight)
    elif encoding == "BIN":
        log_k = floor(log2(k))
        for bit in range(0, log_k + 1):
            obj_sum += n * k * (2**bit)
            for bit2 in range(0, log_k + 1):
                weight = 2 ** (bit + bit2)
                obj_sum += n * weight
                delta += n * weight
    else:
        raise ValueError(f"cannot convert MaxSAT objective for encoding {encoding}")
    return obj_sum, delta


def parse_generic(path: Path) -> dict:
    text = path.read_text(errors="replace")
    record = {
        "Benchmark": strip_suffix(path.name),
        "is_OPT": 0,
        "BEST": "",
        "tot_time": "",
        "solving_time": "",
        "status": "",
    }
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("@@@"):
            record["status"] = line.split(maxsplit=1)[1] if len(line.split(maxsplit=1)) > 1 else ""
            if record["status"] in {"MIP_optimal", "optimal"}:
                record["is_OPT"] = 1
        elif line.startswith(">>>"):
            parts = line.split()
            for i, part in enumerate(parts[:-1]):
                if part == "OPT":
                    record["BEST"] = parts[i + 1]
                elif part == "TimeCost":
                    record["tot_time"] = parts[i + 1]
                elif part == "TimeSolve":
                    record["solving_time"] = parts[i + 1]
        elif line.startswith("s OPTIMUM FOUND"):
            record["status"] = "OPTIMUM FOUND"
            record["is_OPT"] = 1
        elif line.startswith("o "):
            fields = line.split()
            if len(fields) > 1:
                record["BEST"] = fields[1]
        elif line.startswith("c Found solution:"):
            nums = re.findall(r"[-+]?\d+", line)
            if nums:
                record["BEST"] = nums[-1]
        elif line.startswith("c CPU"):
            nums = re.findall(r"[-+]?\d+(?:\.\d+)?", line)
            if nums:
                record["tot_time"] = nums[-1]
                record["solving_time"] = nums[-1]
        elif line.startswith("CPUTIME="):
            record["solving_time"] = line.replace("CPUTIME=", "").split()[0]
            record["tot_time"] = record["solving_time"]
    return record


def convert_maxsat_best(record: dict, encoding: str | None, k: str, bench_dir: Path) -> None:
    if not encoding or not record["BEST"]:
        return
    n = original_var_count(bench_dir, record["Benchmark"])
    if n is None:
        return
    obj_sum, delta = objective_offsets(encoding, int(k), n)
    raw_cost = int(float(record["BEST"]))
    record["BEST"] = str(obj_sum - raw_cost - delta)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default="../results")
    parser.add_argument("--out-dir", default="./results")
    parser.add_argument("--bench-dir", default="../benchmarks")
    args = parser.parse_args(argv)

    results_dir = Path(args.results_dir)
    out_dir = Path(args.out_dir)
    bench_dir = Path(args.bench_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not results_dir.exists():
        raise FileNotFoundError(results_dir)

    for config_dir in sorted(p for p in results_dir.iterdir() if p.is_dir()):
        match = DIR_RE.match(config_dir.name)
        if not match:
            print(f"[skip] cannot parse result dir name: {config_dir.name}")
            continue
        solver = match.group("solver")
        enc = match.group("enc")
        k = match.group("k")
        se = match.group("se")
        csv_name = f"{solver}-{enc}-k{k}-{se}.csv" if enc else f"{solver}-k{k}.csv"
        rows = [parse_generic(p) for p in sorted(config_dir.glob("*.out"))]
        if solver in {"CASH", "MaxHS", "WMaxCDCL"}:
            for row in rows:
                convert_maxsat_best(row, enc, k, bench_dir)
        if not rows:
            print(f"[warn] empty result dir: {config_dir}")
            continue
        with (out_dir / csv_name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["Benchmark", "is_OPT", "BEST", "tot_time", "solving_time", "status"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"[ok] wrote {out_dir / csv_name} ({len(rows)} rows)")


if __name__ == "__main__":
    main()

