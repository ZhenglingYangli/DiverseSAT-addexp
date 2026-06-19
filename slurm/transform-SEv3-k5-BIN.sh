#!/usr/bin/env bash
#SBATCH --job-name=ne-t-SEv3-5-BIN
#SBATCH --output=slurm-%x-%j.out
#SBATCH --error=slurm-%x-%j.err
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=120G
#SBATCH --array=1-289


set -euo pipefail
SUBMIT_DIR="${SLURM_SUBMIT_DIR:-$(pwd -P)}"
if [[ -n "${NEW_EXPS_ROOT:-}" ]]; then
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
BENCH_DIR="${BENCH_DIR:-$ROOT/benchmarks}"
INSTANCE_LIST="${INSTANCE_LIST:-$ROOT/instances/289_instances.txt}"

python3 "$ROOT/transform/run_transformer.py" \
  --bench-dir "$BENCH_DIR" \
  --instance-list "$INSTANCE_LIST" \
  --out-dir "$ROOT/benchmarks/k_5-BIN-SEv3" \
  --k 5 \
  --encoding BIN \
  --se-mode SEv3
