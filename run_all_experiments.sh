#!/usr/bin/env bash
# Clean rerun entrypoint for strict-SE DiverseSAT experiments.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$ROOT"

step() {
  echo ""
  echo "================================================================"
  echo "== $1"
  echo "================================================================"
}

prepare() {
  step "prepare"
  python3 - <<'PY'
from pathlib import Path
required = [
    "common/config.py",
    "common/se_constraints.py",
    "transformers/cnf_to_wcnf.py",
    "cplex/cplex_diversesat.py",
    "baseline/cadical_enumerate.py",
    "baseline/cadical_greedy.py",
    "transform/run_transformer.py",
    "jobs/run_solver.py",
    "sumup/sumup_results.py",
    "generate_slurm.py",
    "instances/289_instances.txt",
]
missing = [p for p in required if not Path(p).exists()]
if missing:
    raise SystemExit("missing files:\\n" + "\\n".join(missing))
instances = [line.strip() for line in Path("instances/289_instances.txt").read_text().splitlines() if line.strip()]
missing_benchmarks = [name for name in instances if not Path("benchmarks", name).exists()]
if missing_benchmarks:
    raise SystemExit("missing benchmark CNFs:\\n" + "\\n".join(missing_benchmarks[:20]))
if len(instances) != 289:
    raise SystemExit(f"expected 289 instance names, got {len(instances)}")
print("[ok] support files exist")
print("[ok] benchmark CNFs exist: 289")
PY
  BENCH_DIR="${BENCH_DIR:-$ROOT/benchmarks}"
  [[ -d "$BENCH_DIR" ]] || echo "[warn] BENCH_DIR not found: $BENCH_DIR"
  command -v python3 >/dev/null || { echo "[fail] python3 missing"; exit 1; }
}

test_local() {
  step "local tests"
  python3 tests/self_test.py
}

generate() {
  step "generate slurm"
  python3 generate_slurm.py
}

submit() {
  step "submit slurm"
  (cd slurm && bash submit_all.sh)
}

sumup() {
  step "sumup"
  python3 sumup/sumup_results.py --results-dir results --out-dir sumup/results --bench-dir benchmarks
}

summary() {
  step "matrix summary"
  cat <<'EOF'
Matrix:
  Baseline: CaDiCaL, CaDiCaL-Greedy
  Exact solvers: CPLEX, CASH, MaxHS, WMaxCDCL
  Encodings: CPLEX uses QP, OH, UNA, BIN; MaxSAT uses OH, UNA, BIN
  SE modes: strict SEv1 (SE1--SE5), SEv3 + explicit pairwise distinctness
  k values: 2, 3, 4, 5, 10

Expected SLURM scripts:
  Transform: 2 SE modes * 5 k * 3 encodings = 30 array scripts
  CPLEX:    2 SE modes * 5 k * 4 encodings = 40 array scripts
  MaxSAT:   3 solvers * 2 SE modes * 5 k * 3 encodings = 90 array scripts
  Baseline: 2 solvers * 5 k = 10 array scripts
  Total:    170 array scripts, each with 289 tasks
EOF
}

case "${1:-all}" in
  prepare) prepare ;;
  test) test_local ;;
  generate) generate ;;
  submit) submit ;;
  sumup) sumup ;;
  summary) summary ;;
  all) prepare; test_local; generate; summary ;;
  *)
    echo "Usage: $0 {prepare|test|generate|submit|sumup|summary|all}" >&2
    exit 1
    ;;
esac

