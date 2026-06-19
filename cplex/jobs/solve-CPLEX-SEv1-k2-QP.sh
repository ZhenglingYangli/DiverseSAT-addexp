#!/usr/bin/env bash
#SBATCH --job-name=ne-cplex-SEv1-2-QP
#SBATCH --output=slurm-%x-%j.out
#SBATCH --error=slurm-%x-%j.err
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=120G
#SBATCH --array=1-289

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ -n "${NEW_EXPS_ROOT:-}" ]]; then
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
BENCH_DIR="${BENCH_DIR:-$ROOT/benchmarks}"
INSTANCE_LIST="${INSTANCE_LIST:-$ROOT/instances/289_instances.txt}"

mkdir -p "$ROOT/cplex/results/CPLEX-QP-k2-SEv1"
python3 "$ROOT/cplex/jobs/run_solver.py" \
  --solver CPLEX \
  --solver-bin python \
  --input-dir "$BENCH_DIR" \
  --instance-list "$INSTANCE_LIST" \
  --out-dir "$ROOT/cplex/results/CPLEX-QP-k2-SEv1" \
  --suffix .cnf \
  --k 2 \
  --encoding QP \
  --se-mode SEv1 \
  --timeout 7200
