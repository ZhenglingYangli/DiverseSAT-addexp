#!/usr/bin/env python3
"""Local smoke tests for new-exps strict rerun code."""

from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import importlib.util
import subprocess

from pysat.formula import CNF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.dimacs import load_cnf

transformer_path = ROOT / "transform/transformers/cnf_to_wcnf.py"
spec = importlib.util.spec_from_file_location("new_exps_cnf_to_wcnf", transformer_path)
assert spec and spec.loader
transformer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transformer_module)
compile_wcnf = transformer_module.compile_wcnf


def tiny_cnf() -> CNF:
    cnf = CNF()
    cnf.nv = 2
    cnf.append([1, 2])
    return cnf


def test_strict_se_counts() -> None:
    cnf = tiny_cnf()
    _, _, _, sev1_count = compile_wcnf(cnf, 2, "OH", "SEv1")
    _, _, _, sev3_count = compile_wcnf(cnf, 2, "OH", "SEv3")
    assert sev1_count == 13, f"SEv1 strict clause count changed: {sev1_count}"
    assert sev3_count == 10, f"SEv3+distinct clause count changed: {sev3_count}"


def test_transformer_writes_file() -> None:
    cnf = tiny_cnf()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "tiny.wcnf"
        wcnf, *_ = compile_wcnf(cnf, 3, "UNA", "SEv1")
        wcnf.to_file(out)
        text = out.read_text()
        assert text.startswith("p wcnf"), text[:80]
        assert "0\n" in text


def test_dimacs_header_free_variables_are_preserved() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cnf_path = Path(tmp) / "free.cnf"
        cnf_path.write_text("p cnf 2 1\n1 0\n")
        cnf = load_cnf(cnf_path)
        assert cnf.nv == 2
        _, _, _, sev1_count = compile_wcnf(cnf, 2, "OH", "SEv1")
        assert sev1_count == 13


def test_cplex_module_syntax_if_available() -> None:
    try:
        import cplex  # noqa: F401
    except Exception:
        print("[skip] cplex Python module not available locally")
        return
    import importlib.util

    module_path = ROOT / "cplex/solvers/cplex_diversesat.py"
    spec = importlib.util.spec_from_file_location("new_exps_cplex_diversesat", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def test_cplex_tiny_all_encodings_if_available() -> None:
    try:
        import cplex  # noqa: F401
    except Exception:
        print("[skip] cplex package not available")
        return

    cplex_solver = ROOT / "cplex/solvers/cplex_diversesat.py"
    with tempfile.TemporaryDirectory() as tmp:
        cnf_path = Path(tmp) / "tiny.cnf"
        cnf_path.write_text("p cnf 2 1\n1 2 0\n")
        for encoding in ["QP", "OH", "UNA", "BIN"]:
            for se_mode in ["SEv1", "SEv3"]:
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(cplex_solver),
                        str(cnf_path),
                        "2",
                        encoding,
                        se_mode,
                        "--cutoff",
                        "10",
                    ],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=30,
                )
                assert proc.returncode == 0, proc.stdout
                assert "@@@ optimal" in proc.stdout, proc.stdout
                assert "OPT 2" in proc.stdout, proc.stdout


def test_sumup_parses_qp_encoding() -> None:
    import csv

    sumup_path = ROOT / "common/sumup_common.py"
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        result_dir = base / "results/CPLEX-QP-k2-SEv1"
        result_dir.mkdir(parents=True)
        (result_dir / "tiny.cnf.out").write_text(
            "@@@ MIP_optimal\n"
            ">>> Benchmark tiny.cnf k 2 encoding QP se SEv1 OPT 1 TimeCost 0.1 TimeSolve 0.05 TimeRead 0.01 TimeTrans 0.04\n"
        )
        out_dir = base / "sumup"
        subprocess.run(
            [sys.executable, str(sumup_path), "--results-dir", str(base / "results"), "--out-dir", str(out_dir)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        csv_path = out_dir / "CPLEX-QP-k2-SEv1.csv"
        assert csv_path.exists(), sorted(p.name for p in out_dir.iterdir())
        rows = list(csv.DictReader(csv_path.open()))
        assert rows[0]["is_OPT"] == "1"
        assert rows[0]["BEST"] == "1"


def test_sumup_status_semantics() -> None:
    import csv

    sumup_path = ROOT / "common/sumup_common.py"
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        bench_dir = base / "benchmarks"
        bench_dir.mkdir()
        (bench_dir / "tiny.cnf").write_text("p cnf 2 1\n1 2 0\n")
        cplex_dir = base / "results/CPLEX-QP-k2-SEv1"
        cplex_dir.mkdir(parents=True)
        (cplex_dir / "tiny.cnf.out").write_text(
            "@@@ optimal\n"
            ">>> Benchmark tiny.cnf k 2 encoding QP se SEv1 OPT 2 TimeCost 0.1 TimeSolve 0.05\n"
        )
        baseline_dir = base / "results/CaDiCaL-Greedy-k2"
        baseline_dir.mkdir(parents=True)
        (baseline_dir / "tiny.cnf.out").write_text(
            "@@@ completed\n"
            ">>> Benchmark tiny.cnf k 2 models 2 OPT 2 TimeCost 0.1 TimeSolve 0.05\n"
        )
        maxsat_dir = base / "results/MaxHS-OH-k2-SEv1"
        maxsat_dir.mkdir(parents=True)
        (maxsat_dir / "tiny.wcnf.out").write_text("s OPTIMUM FOUND\no 0\nc CPU time: 0.1\n")
        out_dir = base / "sumup"
        subprocess.run(
            [
                sys.executable,
                str(sumup_path),
                "--results-dir",
                str(base / "results"),
                "--out-dir",
                str(out_dir),
                "--bench-dir",
                str(bench_dir),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        cplex_rows = list(csv.DictReader((out_dir / "CPLEX-QP-k2-SEv1.csv").open()))
        baseline_rows = list(csv.DictReader((out_dir / "CaDiCaL-Greedy-k2.csv").open()))
        maxsat_rows = list(csv.DictReader((out_dir / "MaxHS-OH-k2-SEv1.csv").open()))
        assert cplex_rows[0]["is_OPT"] == "1"
        assert baseline_rows[0]["status"] == "completed"
        assert baseline_rows[0]["is_OPT"] == "0"
        assert maxsat_rows[0]["status"] == "OPTIMUM FOUND"
        assert maxsat_rows[0]["is_OPT"] == "1"


def test_sumup_converts_maxsat_cost_to_diversity() -> None:
    import csv

    sumup_path = ROOT / "common/sumup_common.py"
    raw_costs = {"OH": 0, "UNA": 0, "BIN": 10}
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        bench_dir = base / "benchmarks"
        bench_dir.mkdir()
        (bench_dir / "tiny.cnf").write_text("p cnf 2 1\n1 2 0\n")
        for encoding, raw_cost in raw_costs.items():
            result_dir = base / f"results/MaxHS-{encoding}-k2-SEv1"
            result_dir.mkdir(parents=True)
            (result_dir / "tiny.wcnf.out").write_text(f"s OPTIMUM FOUND\no {raw_cost}\nc CPU time: 0.1\n")
        out_dir = base / "sumup"
        subprocess.run(
            [
                sys.executable,
                str(sumup_path),
                "--results-dir",
                str(base / "results"),
                "--out-dir",
                str(out_dir),
                "--bench-dir",
                str(bench_dir),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for encoding in raw_costs:
            rows = list(csv.DictReader((out_dir / f"MaxHS-{encoding}-k2-SEv1.csv").open()))
            assert rows[0]["is_OPT"] == "1"
            assert rows[0]["BEST"] == "2", (encoding, rows[0])


def test_baselines_respect_distinctness_with_free_variables() -> None:
    baselines = [
        ROOT / "cadical/solvers/cadical_enumerate.py",
        ROOT / "cadical_greedy/solvers/cadical_greedy.py",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        cnf_path = Path(tmp) / "free.cnf"
        cnf_path.write_text("p cnf 2 1\n1 0\n")
        for baseline in baselines:
            completed = subprocess.run(
                [sys.executable, str(baseline), str(cnf_path), "2"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
            )
            assert completed.returncode == 0, completed.stdout
            assert "@@@ completed" in completed.stdout, completed.stdout
            assert "OPT 1" in completed.stdout, completed.stdout

            incomplete = subprocess.run(
                [sys.executable, str(baseline), str(cnf_path), "3"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
            )
            assert incomplete.returncode == 0, incomplete.stdout
            assert "@@@ incomplete" in incomplete.stdout, incomplete.stdout


def main() -> None:
    test_strict_se_counts()
    test_transformer_writes_file()
    test_dimacs_header_free_variables_are_preserved()
    test_cplex_module_syntax_if_available()
    test_cplex_tiny_all_encodings_if_available()
    test_sumup_parses_qp_encoding()
    test_sumup_status_semantics()
    test_sumup_converts_maxsat_cost_to_diversity()
    test_baselines_respect_distinctness_with_free_variables()
    print("[ok] new-exps local self tests passed")


if __name__ == "__main__":
    main()

