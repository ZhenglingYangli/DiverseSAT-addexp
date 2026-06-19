#!/usr/bin/env python3
"""Generate SLURM scripts for the clean rerun matrix."""

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
SUBMIT_DIR="${{SLURM_SUBMIT_DIR:-$(pwd -P)}}"
if [[ -n "${{NEW_EXPS_ROOT:-}}" ]]; then
  ROOT="$(cd "$NEW_EXPS_ROOT" && pwd -P)"
elif [[ -f "$SUBMIT_DIR/../common/config.py" ]]; then
  ROOT="$(cd "$SUBMIT_DIR/.." && pwd -P)"
elif [[ -f "$SUBMIT_DIR/common/config.py" ]]; then
  ROOT="$(cd "$SUBMIT_DIR" && pwd -P)"
else
  echo "[error] cannot locate new-exps root from SLURM_SUBMIT_DIR=$SUBMIT_DIR" >&2
  echo "[hint] submit from new-exps/slurm, from new-exps, or set NEW_EXPS_ROOT=/path/to/new-exps" >&2
  exit 2
fi
cd "$ROOT/slurm"
BENCH_DIR="${{BENCH_DIR:-$ROOT/benchmarks}}"
INSTANCE_LIST="${{INSTANCE_LIST:-$ROOT/instances/289_instances.txt}}"

"""


def write_script(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(0o755)


def transform_script(k: int, encoding: str, se_mode: str) -> str:
    out_dir = f"$ROOT/benchmarks/k_{k}-{encoding}-{se_mode}"
    return slurm_header(f"ne-t-{se_mode}-{k}-{encoding}") + f"""python3 "$ROOT/transform/run_transformer.py" \\
  --bench-dir "$BENCH_DIR" \\
  --instance-list "$INSTANCE_LIST" \\
  --out-dir "{out_dir}" \\
  --k {k} \\
  --encoding {encoding} \\
  --se-mode {se_mode}
"""


def cplex_script(k: int, encoding: str, se_mode: str) -> str:
    out_dir = f"$ROOT/results/CPLEX-{encoding}-k{k}-{se_mode}"
    return slurm_header(f"ne-cplex-{se_mode}-{k}-{encoding}") + f"""mkdir -p "{out_dir}"
python3 "$ROOT/jobs/run_solver.py" \\
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
    env_name = f"{solver.upper()}_BIN" if solver != "WMaxCDCL" else "WMAXCDCL_BIN"
    default_bin = f"$ROOT/solvers/MaxSAT/{'cashwmaxsat-disjcom' if solver == 'CASH' else 'maxhs' if solver == 'MaxHS' else 'wmaxcdcl'}"
    return slurm_header(f"ne-{solver}-{se_mode}-{k}-{encoding}", mem_gb=64) + f"""SOLVER_BIN="${{{env_name}:-{default_bin}}}"
python3 "$ROOT/jobs/run_solver.py" \\
  --solver {solver} \\
  --solver-bin "$SOLVER_BIN" \\
  --input-dir "$ROOT/benchmarks/k_{k}-{encoding}-{se_mode}" \\
  --instance-list "$INSTANCE_LIST" \\
  --out-dir "$ROOT/results/{solver}-{encoding}-k{k}-{se_mode}" \\
  --suffix .wcnf \\
  --timeout {CUTOFF_SECONDS}
"""


def baseline_script(solver: str, k: int) -> str:
    solver_arg = solver
    return slurm_header(f"ne-{solver}-k{k}", mem_gb=32) + f"""python3 "$ROOT/jobs/run_solver.py" \\
  --solver {solver_arg} \\
  --solver-bin unused \\
  --input-dir "$BENCH_DIR" \\
  --instance-list "$INSTANCE_LIST" \\
  --out-dir "$ROOT/results/{solver}-k{k}" \\
  --suffix .cnf \\
  --k {k} \\
  --timeout {CUTOFF_SECONDS}
"""


def main() -> None:
    scripts_dir = ROOT / "slurm"
    scripts_dir.mkdir(exist_ok=True)
    scripts: list[str] = []
    transform_scripts: list[str] = []
    solve_scripts: list[str] = []
    baseline_scripts: list[str] = []

    for se_mode in SE_MODES:
        for k in K_VALUES:
            for encoding in MAXSAT_ENCODINGS:
                path = scripts_dir / f"transform-{se_mode}-k{k}-{encoding}.sh"
                write_script(path, transform_script(k, encoding, se_mode))
                scripts.append(path.name)
                transform_scripts.append(path.name)

            for encoding in CPLEX_ENCODINGS:
                path = scripts_dir / f"solve-CPLEX-{se_mode}-k{k}-{encoding}.sh"
                write_script(path, cplex_script(k, encoding, se_mode))
                scripts.append(path.name)
                solve_scripts.append(path.name)

            for encoding in MAXSAT_ENCODINGS:
                for solver in MAXSAT_SOLVERS:
                    path = scripts_dir / f"solve-{solver}-{se_mode}-k{k}-{encoding}.sh"
                    write_script(path, maxsat_script(solver, k, encoding, se_mode))
                    scripts.append(path.name)
                    solve_scripts.append(path.name)

    for k in K_VALUES:
        for solver in BASELINE_SOLVERS:
            path = scripts_dir / f"baseline-{solver}-k{k}.sh"
            write_script(path, baseline_script(solver, k))
            scripts.append(path.name)
            baseline_scripts.append(path.name)

    for filename, names in [
        ("submit_transforms.sh", transform_scripts),
        ("submit_solves.sh", solve_scripts),
        ("submit_baselines.sh", baseline_scripts),
    ]:
        submit = scripts_dir / filename
        submit.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "SCRIPT_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd -P)\"\n"
            "cd \"$SCRIPT_DIR\"\n"
            + "".join(f"sbatch {name}\n" for name in names)
        )
        submit.chmod(0o755)

    submit_all = scripts_dir / "submit_all.sh"
    submit_all.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "echo 'Do not submit all stages at once: MaxSAT solve jobs need transformed WCNF files.' >&2\n"
        "echo 'Use: bash submit_transforms.sh; wait for completion; bash submit_solves.sh; bash submit_baselines.sh' >&2\n"
        "exit 1\n"
    )
    submit_all.chmod(0o755)
    print(f"Generated {len(scripts)} SLURM scripts under {scripts_dir}")


if __name__ == "__main__":
    main()

