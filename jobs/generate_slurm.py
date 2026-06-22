#!/usr/bin/env python3
"""Generate SE-oriented SLURM scripts for the strict rerun matrix."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codes/SEv1"))
DEFAULT_INSTANCE_LIST = "$ROOT/codes/289_instances.txt"

from common.config import (  # noqa: E402
    BASELINE_SOLVERS,
    CPLEX_ENCODINGS,
    CUTOFF_SECONDS,
    DEFAULT_BENCH_DIR,
    DEFAULT_MEM_GB,
    K_VALUES,
    MAXSAT_DEFAULT_BINS,
    MAXSAT_ENCODINGS,
    MAXSAT_SOLVERS,
    SE_MODES,
)

SOLVER_DIR = {
    "CPLEX": "cplex",
    "CASH": "cash",
    "MaxHS": "maxhs",
    "WMaxCDCL": "wmaxcdcl",
    "CaDiCaL": "cadical",
    "CaDiCaL-Greedy": "cadical_greedy",
}

GENERATED_JOB_DIRS = ("SEv1", "SEv3", "baseline", "sumup")


def slurm_header(job_name: str, se_mode: str, mem_gb: int = DEFAULT_MEM_GB, hours: int = 3, array: bool = True) -> str:
    array_line = "#SBATCH --array=1-289\n" if array else ""
    return f"""#!/usr/bin/env bash
#SBATCH --job-name={job_name}
#SBATCH --output=slurm-%x-%j.out
#SBATCH --error=slurm-%x-%j.err
#SBATCH --time={hours:02d}:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem={mem_gb}G
{array_line}
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd -P)"
if [[ -n "${{NEW_EXPS_ROOT:-}}" ]]; then
  ROOT="$(cd "$NEW_EXPS_ROOT" && pwd -P)"
else
  ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
fi
cd "$SCRIPT_DIR"
CODE_DIR="$ROOT/codes/{se_mode}"
export PYTHONPATH="$CODE_DIR${{PYTHONPATH:+:$PYTHONPATH}}"
BENCH_DIR="${{BENCH_DIR:-{DEFAULT_BENCH_DIR}}}"
INSTANCE_LIST="${{INSTANCE_LIST:-{DEFAULT_INSTANCE_LIST}}}"

"""


def baseline_header(job_name: str, mem_gb: int = 32) -> str:
    # Baselines are not SE-specific; use SEv1's shared code copy for the runner.
    return slurm_header(job_name, "SEv1", mem_gb=mem_gb)


def write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)


def transform_script(k: int, encoding: str, se_mode: str) -> str:
    out_dir = f"$ROOT/results/{se_mode}/transform/k_{k}-{encoding}-{se_mode}"
    return slurm_header(f"ne-t-{se_mode}-{k}-{encoding}", se_mode) + f"""python3 "$CODE_DIR/transform/run_transformer.py" \\
  --bench-dir "$BENCH_DIR" \\
  --instance-list "$INSTANCE_LIST" \\
  --out-dir "{out_dir}" \\
  --k {k} \\
  --encoding {encoding} \\
  --se-mode {se_mode}
"""


def cplex_script(k: int, encoding: str, se_mode: str) -> str:
    out_dir = f"$ROOT/results/{se_mode}/cplex/CPLEX-{encoding}-k{k}-{se_mode}"
    return slurm_header(f"ne-cplex-{se_mode}-{k}-{encoding}", se_mode) + f"""mkdir -p "{out_dir}"
python3 "$CODE_DIR/cplex/run_solver.py" \\
  --solver CPLEX \\
  --solver-bin python \\
  --input-dir "$BENCH_DIR" \\
  --instance-list "$INSTANCE_LIST" \\
  --out-dir "{out_dir}" \\
  --suffix .cnf \\
  --k {k} \\
  --encoding {encoding} \\
  --se-mode {se_mode} \\
  --timeout {CUTOFF_SECONDS}
"""


def maxsat_script(solver: str, k: int, encoding: str, se_mode: str) -> str:
    solver_dir = SOLVER_DIR[solver]
    env_name = f"{solver.upper()}_BIN" if solver != "WMaxCDCL" else "WMAXCDCL_BIN"
    default_bin = MAXSAT_DEFAULT_BINS[solver]
    return slurm_header(f"ne-{solver}-{se_mode}-{k}-{encoding}", se_mode, mem_gb=64) + f"""SOLVER_BIN="${{{env_name}:-{default_bin}}}"
python3 "$CODE_DIR/{solver_dir}/run_solver.py" \\
  --solver {solver} \\
  --solver-bin "$SOLVER_BIN" \\
  --input-dir "$ROOT/results/{se_mode}/transform/k_{k}-{encoding}-{se_mode}" \\
  --instance-list "$INSTANCE_LIST" \\
  --out-dir "$ROOT/results/{se_mode}/{solver_dir}/{solver}-{encoding}-k{k}-{se_mode}" \\
  --suffix .wcnf \\
  --timeout {CUTOFF_SECONDS}
"""


def baseline_script(solver: str, k: int) -> str:
    solver_dir = SOLVER_DIR[solver]
    return baseline_header(f"ne-{solver}-k{k}") + f"""python3 "$CODE_DIR/{solver_dir}/run_solver.py" \\
  --solver {solver} \\
  --solver-bin unused \\
  --input-dir "$BENCH_DIR" \\
  --instance-list "$INSTANCE_LIST" \\
  --out-dir "$ROOT/results/baseline/{solver_dir}/{solver}-k{k}" \\
  --suffix .cnf \\
  --k {k} \\
  --timeout {CUTOFF_SECONDS}
"""


def write_submit(path: Path, names: list[str]) -> None:
    write_script(
        path,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "SCRIPT_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd -P)\"\n"
        "cd \"$SCRIPT_DIR\"\n"
        + "".join(f"sbatch {name}\n" for name in names),
    )


def write_sumup_job() -> None:
    write_script(
        ROOT / "jobs" / "sumup" / "sumup_all.sh",
        """#!/usr/bin/env bash
#SBATCH --job-name=ne-sumup
#SBATCH --output=slurm-%x-%j.out
#SBATCH --error=slurm-%x-%j.err
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
cd "$ROOT"

python3 sumup/SEv1/sumup.py
python3 sumup/SEv3/sumup.py
python3 sumup/baseline/sumup.py
python3 sumup/combined/combine_csvs.py
""",
    )


def clean_generated_jobs() -> None:
    jobs_root = ROOT / "jobs"
    jobs_root.mkdir(exist_ok=True)
    for name in GENERATED_JOB_DIRS:
        shutil.rmtree(jobs_root / name, ignore_errors=True)


def main() -> None:
    clean_generated_jobs()
    total = 0
    transform_by_se: dict[str, list[str]] = {se: [] for se in SE_MODES}
    solve_by_se_solver: dict[tuple[str, str], list[str]] = {}
    baseline_by_solver: dict[str, list[str]] = {SOLVER_DIR[s]: [] for s in BASELINE_SOLVERS}

    for se_mode in SE_MODES:
        for solver_dir in ["cplex", "cash", "maxhs", "wmaxcdcl"]:
            solve_by_se_solver[(se_mode, solver_dir)] = []

        for k in K_VALUES:
            for encoding in MAXSAT_ENCODINGS:
                name = f"transform-{se_mode}-k{k}-{encoding}.sh"
                write_script(ROOT / "jobs" / se_mode / "transform" / name, transform_script(k, encoding, se_mode))
                transform_by_se[se_mode].append(name)
                total += 1
            for encoding in CPLEX_ENCODINGS:
                name = f"solve-CPLEX-{se_mode}-k{k}-{encoding}.sh"
                write_script(ROOT / "jobs" / se_mode / "cplex" / name, cplex_script(k, encoding, se_mode))
                solve_by_se_solver[(se_mode, "cplex")].append(name)
                total += 1
            for encoding in MAXSAT_ENCODINGS:
                for solver in MAXSAT_SOLVERS:
                    solver_dir = SOLVER_DIR[solver]
                    name = f"solve-{solver}-{se_mode}-k{k}-{encoding}.sh"
                    write_script(ROOT / "jobs" / se_mode / solver_dir / name, maxsat_script(solver, k, encoding, se_mode))
                    solve_by_se_solver[(se_mode, solver_dir)].append(name)
                    total += 1

    for k in K_VALUES:
        for solver in BASELINE_SOLVERS:
            solver_dir = SOLVER_DIR[solver]
            name = f"baseline-{solver}-k{k}.sh"
            write_script(ROOT / "jobs" / "baseline" / solver_dir / name, baseline_script(solver, k))
            baseline_by_solver[solver_dir].append(name)
            total += 1

    for se_mode, names in transform_by_se.items():
        write_submit(ROOT / "jobs" / se_mode / "transform" / "submit_transforms.sh", names)
    for (se_mode, solver_dir), names in solve_by_se_solver.items():
        write_submit(ROOT / "jobs" / se_mode / solver_dir / "submit_solves.sh", names)
    for solver_dir, names in baseline_by_solver.items():
        write_submit(ROOT / "jobs" / "baseline" / solver_dir / "submit_baselines.sh", names)

    write_sumup_job()
    print(f"Generated {total} SLURM array scripts in SE-oriented directories")


if __name__ == "__main__":
    main()
