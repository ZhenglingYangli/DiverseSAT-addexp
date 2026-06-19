#!/usr/bin/env python3
"""Generate solver-oriented SLURM scripts for the strict rerun matrix."""

from __future__ import annotations

from pathlib import Path

from common.config import (
    BASELINE_SOLVERS,
    CPLEX_ENCODINGS,
    CUTOFF_SECONDS,
    DEFAULT_MEM_GB,
    K_VALUES,
    MAXSAT_ENCODINGS,
    MAXSAT_SOLVERS,
    SE_MODES,
)


ROOT = Path(__file__).resolve().parent
SOLVER_DIR = {
    "CPLEX": "cplex",
    "CASH": "cash",
    "MaxHS": "maxhs",
    "WMaxCDCL": "wmaxcdcl",
    "CaDiCaL": "cadical",
    "CaDiCaL-Greedy": "cadical_greedy",
}


def slurm_header(job_name: str, mem_gb: int = DEFAULT_MEM_GB, hours: int = 3, array: bool = True) -> str:
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
elif [[ -f "$SCRIPT_DIR/../../common/config.py" ]]; then
  ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
elif [[ -f "$SCRIPT_DIR/../common/config.py" ]]; then
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
else
  echo "[error] cannot locate new-exps root from SCRIPT_DIR=$SCRIPT_DIR" >&2
  echo "[hint] set NEW_EXPS_ROOT=/path/to/new-exps" >&2
  exit 2
fi
cd "$SCRIPT_DIR"
BENCH_DIR="${{BENCH_DIR:-$ROOT/benchmarks}}"
INSTANCE_LIST="${{INSTANCE_LIST:-$ROOT/instances/289_instances.txt}}"

"""


def write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)


def transform_script(k: int, encoding: str, se_mode: str) -> str:
    out_dir = f"$ROOT/transform/results/k_{k}-{encoding}-{se_mode}"
    return slurm_header(f"ne-t-{se_mode}-{k}-{encoding}") + f"""python3 "$ROOT/transform/run_transformer.py" \\
  --bench-dir "$BENCH_DIR" \\
  --instance-list "$INSTANCE_LIST" \\
  --out-dir "{out_dir}" \\
  --k {k} \\
  --encoding {encoding} \\
  --se-mode {se_mode}
"""


def cplex_script(k: int, encoding: str, se_mode: str) -> str:
    out_dir = f"$ROOT/cplex/results/CPLEX-{encoding}-k{k}-{se_mode}"
    return slurm_header(f"ne-cplex-{se_mode}-{k}-{encoding}") + f"""mkdir -p "{out_dir}"
python3 "$ROOT/cplex/jobs/run_solver.py" \\
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
    binary = "cashwmaxsat-disjcom" if solver == "CASH" else "maxhs" if solver == "MaxHS" else "wmaxcdcl"
    default_bin = f"$ROOT/solvers/MaxSAT/{binary}"
    return slurm_header(f"ne-{solver}-{se_mode}-{k}-{encoding}", mem_gb=64) + f"""SOLVER_BIN="${{{env_name}:-{default_bin}}}"
python3 "$ROOT/{solver_dir}/jobs/run_solver.py" \\
  --solver {solver} \\
  --solver-bin "$SOLVER_BIN" \\
  --input-dir "$ROOT/transform/results/k_{k}-{encoding}-{se_mode}" \\
  --instance-list "$INSTANCE_LIST" \\
  --out-dir "$ROOT/{solver_dir}/results/{solver}-{encoding}-k{k}-{se_mode}" \\
  --suffix .wcnf \\
  --timeout {CUTOFF_SECONDS}
"""


def baseline_script(solver: str, k: int) -> str:
    solver_dir = SOLVER_DIR[solver]
    return slurm_header(f"ne-{solver}-k{k}", mem_gb=32) + f"""python3 "$ROOT/{solver_dir}/jobs/run_solver.py" \\
  --solver {solver} \\
  --solver-bin unused \\
  --input-dir "$BENCH_DIR" \\
  --instance-list "$INSTANCE_LIST" \\
  --out-dir "$ROOT/{solver_dir}/results/{solver}-k{k}" \\
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


def main() -> None:
    transform_names: list[str] = []
    solve_names: dict[str, list[str]] = {d: [] for d in ["cplex", "cash", "maxhs", "wmaxcdcl"]}
    baseline_names: dict[str, list[str]] = {d: [] for d in ["cadical", "cadical_greedy"]}
    total = 0

    for se_mode in SE_MODES:
        for k in K_VALUES:
            for encoding in MAXSAT_ENCODINGS:
                name = f"transform-{se_mode}-k{k}-{encoding}.sh"
                write_script(ROOT / "transform/jobs" / name, transform_script(k, encoding, se_mode))
                transform_names.append(name)
                total += 1
            for encoding in CPLEX_ENCODINGS:
                name = f"solve-CPLEX-{se_mode}-k{k}-{encoding}.sh"
                write_script(ROOT / "cplex/jobs" / name, cplex_script(k, encoding, se_mode))
                solve_names["cplex"].append(name)
                total += 1
            for encoding in MAXSAT_ENCODINGS:
                for solver in MAXSAT_SOLVERS:
                    solver_dir = SOLVER_DIR[solver]
                    name = f"solve-{solver}-{se_mode}-k{k}-{encoding}.sh"
                    write_script(ROOT / solver_dir / "jobs" / name, maxsat_script(solver, k, encoding, se_mode))
                    solve_names[solver_dir].append(name)
                    total += 1

    for k in K_VALUES:
        for solver in BASELINE_SOLVERS:
            solver_dir = SOLVER_DIR[solver]
            name = f"baseline-{solver}-k{k}.sh"
            write_script(ROOT / solver_dir / "jobs" / name, baseline_script(solver, k))
            baseline_names[solver_dir].append(name)
            total += 1

    write_submit(ROOT / "transform/jobs/submit_transforms.sh", transform_names)
    for solver_dir, names in solve_names.items():
        write_submit(ROOT / solver_dir / "jobs/submit_solves.sh", names)
    for solver_dir, names in baseline_names.items():
        write_submit(ROOT / solver_dir / "jobs/submit_baselines.sh", names)

    write_script(
        ROOT / "submit_transforms.sh",
        "#!/usr/bin/env bash\nset -euo pipefail\ncd \"$(dirname \"${BASH_SOURCE[0]}\")/transform/jobs\"\nbash submit_transforms.sh\n",
    )
    write_script(
        ROOT / "submit_solves.sh",
        "#!/usr/bin/env bash\nset -euo pipefail\nROOT=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd -P)\"\nfor d in cplex cash maxhs wmaxcdcl; do (cd \"$ROOT/$d/jobs\" && bash submit_solves.sh); done\n",
    )
    write_script(
        ROOT / "submit_baselines.sh",
        "#!/usr/bin/env bash\nset -euo pipefail\nROOT=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd -P)\"\nfor d in cadical cadical_greedy; do (cd \"$ROOT/$d/jobs\" && bash submit_baselines.sh); done\n",
    )
    write_script(
        ROOT / "submit_all.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "echo 'Do not submit all stages at once: MaxSAT solve jobs need transformed WCNF files.' >&2\n"
        "echo 'Use: bash submit_transforms.sh; wait for completion; bash submit_solves.sh; bash submit_baselines.sh' >&2\n"
        "exit 1\n",
    )
    print(f"Generated {total} SLURM array scripts in solver-oriented directories")


if __name__ == "__main__":
    main()

