#!/usr/bin/env bash
# One-command strict-SE rerun pipeline for the original experiment cluster.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$ROOT"

# Defaults are the original cluster resource paths. Override with environment
# variables if a collaborator's account uses different mount points.
export BENCH_DIR="${BENCH_DIR:-/users/scherif/ComputeSpace/DiverseSAT/benchmarks}"
export CASH_BIN="${CASH_BIN:-/users/scherif/ComputeSpace/DiverseSAT/solvers/MaxSAT/cashwmaxsat-disjcom}"
export MAXHS_BIN="${MAXHS_BIN:-/users/scherif/ComputeSpace/DiverseSAT/solvers/MaxSAT/maxhs}"
export WMAXCDCL_BIN="${WMAXCDCL_BIN:-/users/scherif/ComputeSpace/DiverseSAT/solvers/MaxSAT/wmaxcdcl}"
export INSTANCE_LIST="${INSTANCE_LIST:-$ROOT/codes/289_instances.txt}"

timestamp() {
  date +"%Y%m%d-%H%M%S"
}

log() {
  echo "[$(date '+%F %T')] $*"
}

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

join_by_colon() {
  local IFS=:
  echo "$*"
}

submit_array_group() {
  local label="$1"
  local dependency="$2"
  shift 2
  local scripts=("$@")
  local ids=()
  local id
  local dep_args=()

  if [[ "${#scripts[@]}" -eq 0 ]]; then
    die "no scripts found for $label"
  fi

  if [[ -n "$dependency" ]]; then
    dep_args=(--dependency="$dependency")
  fi

  log "Submitting $label (${#scripts[@]} array scripts)"
  for script in "${scripts[@]}"; do
    [[ -f "$script" ]] || die "missing script: $script"
    id="$(sbatch --parsable "${dep_args[@]}" "$script")"
    id="${id%%;*}"
    ids+=("$id")
    echo "$label $id $script" >> "$SUBMISSION_LOG"
  done
  join_by_colon "${ids[@]}"
}

check_file() {
  [[ -f "$1" ]] || die "missing file: $1"
}

check_executable() {
  [[ -x "$1" ]] || die "missing executable: $1"
}

check_python_module() {
  python3 - "$1" <<'PY'
import sys
module = sys.argv[1]
try:
    __import__(module)
except Exception as exc:
    raise SystemExit(f"missing Python module {module}: {exc}")
PY
}

check_benchmarks() {
  python3 - <<'PY'
import os
from pathlib import Path

bench_dir = Path(os.environ["BENCH_DIR"])
instance_list = Path(os.environ["INSTANCE_LIST"])
if not bench_dir.is_dir():
    raise SystemExit(f"BENCH_DIR does not exist: {bench_dir}")
if not instance_list.is_file():
    raise SystemExit(f"INSTANCE_LIST does not exist: {instance_list}")

names = [line.strip() for line in instance_list.read_text().splitlines() if line.strip()]
if len(names) != 289:
    raise SystemExit(f"expected 289 instances, got {len(names)}")
missing = [name for name in names if not (bench_dir / name).is_file()]
bad_headers = []
for name in names:
    path = bench_dir / name
    if path.is_file():
        with path.open("r", errors="ignore") as handle:
            first = handle.readline()
            if first.startswith("version https://git-lfs.github.com/spec/v1"):
                bad_headers.append(f"{name}: Git LFS pointer")
            elif not first.startswith(("c", "p cnf")):
                # DIMACS files may start with comments; the detailed parser will
                # validate later, so this is only a quick corruption check.
                pass
if missing:
    preview = "\n".join(f"  - {name}" for name in missing[:20])
    raise SystemExit(f"missing benchmark CNFs under {bench_dir}: {len(missing)}\n{preview}")
if bad_headers:
    preview = "\n".join(f"  - {name}" for name in bad_headers[:20])
    raise SystemExit(f"invalid benchmark files:\n{preview}")
print(f"[ok] benchmark CNFs visible: {len(names)}")
PY
}

preflight() {
  section "1. Preflight"
  check_file "README.md"
  check_file "codes/289_instances.txt"
  check_file "codes/SEv1/common/config.py"
  check_file "codes/SEv1/common/se_constraints.py"
  check_file "codes/SEv1/transform/cnf_to_wcnf.py"
  check_file "codes/SEv1/cplex/cplex_diversesat.py"
  check_file "codes/SEv3/common/config.py"
  check_file "codes/SEv3/common/se_constraints.py"
  check_file "codes/SEv3/transform/cnf_to_wcnf.py"
  check_file "codes/SEv3/cplex/cplex_diversesat.py"
  check_file "jobs/generate_slurm.py"
  check_file "codes/check_server_ready.py"
  check_file "sumup/SEv1/sumup.py"
  check_file "sumup/SEv3/sumup.py"
  check_file "sumup/baseline/sumup.py"
  check_file "sumup/combined/combine_csvs.py"

  command -v python3 >/dev/null 2>&1 || die "python3 not found"
  command -v sbatch >/dev/null 2>&1 || die "sbatch not found; run on the SLURM cluster login node"
  check_python_module pysat
  check_python_module psutil
  check_python_module cplex
  check_executable "$CASH_BIN"
  check_executable "$MAXHS_BIN"
  check_executable "$WMAXCDCL_BIN"
  check_benchmarks
}

run_local_tests() {
  section "2. Local Tests"
  python3 tests/self_test.py
  python3 codes/check_server_ready.py
}

generate_jobs() {
  section "3. Generate SLURM Scripts"
  python3 jobs/generate_slurm.py
  python3 - <<'PY'
from pathlib import Path
job_scripts = [
    p for p in Path("jobs").rglob("*.sh")
    if p.name.startswith(("transform-", "solve-", "baseline-"))
]
if len(job_scripts) != 170:
    raise SystemExit(f"expected 170 generated array scripts, got {len(job_scripts)}")
print("[ok] generated 170 SLURM array scripts")
PY
}

section() {
  echo ""
  echo "================================================================"
  echo "== $1"
  echo "================================================================"
}

PIPELINE_ID="$(timestamp)"
SUBMISSION_LOG="$ROOT/pipeline-submissions-$PIPELINE_ID.tsv"
: > "$SUBMISSION_LOG"
log "Submission log: $SUBMISSION_LOG"

preflight
run_local_tests
generate_jobs

section "4. Submit Transform Arrays"
mapfile -t transform_scripts < <(
  printf '%s\n' \
    "$ROOT"/jobs/SEv1/transform/transform-*.sh \
    "$ROOT"/jobs/SEv3/transform/transform-*.sh | sort
)
transform_ids="$(submit_array_group "transform" "" "${transform_scripts[@]}")"
log "Transform dependency ids: $transform_ids"

section "5. Submit Exact Solver Arrays After Transform Success"
mapfile -t solve_scripts < <(
  printf '%s\n' \
    "$ROOT"/jobs/SEv1/cplex/solve-*.sh \
    "$ROOT"/jobs/SEv1/cash/solve-*.sh \
    "$ROOT"/jobs/SEv1/maxhs/solve-*.sh \
    "$ROOT"/jobs/SEv1/wmaxcdcl/solve-*.sh \
    "$ROOT"/jobs/SEv3/cplex/solve-*.sh \
    "$ROOT"/jobs/SEv3/cash/solve-*.sh \
    "$ROOT"/jobs/SEv3/maxhs/solve-*.sh \
    "$ROOT"/jobs/SEv3/wmaxcdcl/solve-*.sh | sort
)
solve_ids="$(submit_array_group "solve" "afterok:$transform_ids" "${solve_scripts[@]}")"
log "Solve dependency ids: $solve_ids"

section "6. Submit Baseline Arrays"
mapfile -t baseline_scripts < <(
  printf '%s\n' \
    "$ROOT"/jobs/baseline/cadical/baseline-*.sh \
    "$ROOT"/jobs/baseline/cadical_greedy/baseline-*.sh | sort
)
baseline_ids="$(submit_array_group "baseline" "" "${baseline_scripts[@]}")"
log "Baseline dependency ids: $baseline_ids"

section "7. Submit Sumup Job"
sumup_dependency="afterany:$solve_ids:$baseline_ids"
sumup_id="$(sbatch --parsable --dependency="$sumup_dependency" "$ROOT/jobs/sumup/sumup_all.sh")"
sumup_id="${sumup_id%%;*}"
echo "sumup $sumup_id $ROOT/jobs/sumup/sumup_all.sh" >> "$SUBMISSION_LOG"
log "Sumup job id: $sumup_id"

section "8. Done"
cat <<EOF
Submitted strict-SE rerun pipeline.

Submission log:
  $SUBMISSION_LOG

Dependency chain:
  transforms -> exact solvers -> sumup
  baselines --------------^

Monitor:
  squeue -u "$USER"
  squeue -j "$sumup_id"

When the sumup job finishes, check:
  sumup/SEv1/results/
  sumup/SEv3/results/
  sumup/baseline/results/
  sumup/combined/results/all_results.csv
EOF
