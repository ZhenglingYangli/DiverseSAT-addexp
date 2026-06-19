#!/usr/bin/env bash
# Full preflight check for collaborators on a fresh server.
#
# This script does NOT submit jobs. It verifies that the copied new-exps/
# directory is self-contained, that dependencies are visible, and that SLURM
# scripts can be generated safely.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$ROOT"

ERRORS=0
WARNINGS=0

section() {
  echo ""
  echo "================================================================"
  echo "== $1"
  echo "================================================================"
}

ok() {
  echo "[ok] $*"
}

warn() {
  echo "[warn] $*"
  WARNINGS=$((WARNINGS + 1))
}

fail() {
  echo "[fail] $*"
  ERRORS=$((ERRORS + 1))
}

check_file() {
  [[ -f "$1" ]] && ok "file exists: $1" || fail "missing file: $1"
}

check_dir() {
  [[ -d "$1" ]] && ok "directory exists: $1" || fail "missing directory: $1"
}

section "1. Basic Directory Layout"
echo "ROOT=$ROOT"
for path in \
  common/config.py \
  common/se_constraints.py \
  transformers/cnf_to_wcnf.py \
  cplex/cplex_diversesat.py \
  baseline/cadical_enumerate.py \
  baseline/cadical_greedy.py \
  transform/run_transformer.py \
  jobs/run_solver.py \
  sumup/sumup_results.py \
  check_server_ready.py \
  generate_slurm.py \
  run_all_experiments.sh \
  setup_solvers.sh \
  instances/289_instances.txt \
  requirements.txt
do
  check_file "$path"
done
check_dir benchmarks
check_dir solvers/MaxSAT

section "2. Benchmark Completeness"
python3 - <<'PY' || exit_code=$?
from pathlib import Path
instances = [line.strip() for line in Path("instances/289_instances.txt").read_text().splitlines() if line.strip()]
missing = [name for name in instances if not Path("benchmarks", name).exists()]
extra = [p.name for p in Path("benchmarks").glob("*.cnf") if p.name not in set(instances)]
lfs_pointers = []
invalid_headers = []
for name in instances:
    path = Path("benchmarks", name)
    if not path.exists():
        continue
    text = path.read_text(errors="replace")
    first_nonempty = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if first_nonempty == "version https://git-lfs.github.com/spec/v1":
        lfs_pointers.append(name)
    elif first_nonempty and not first_nonempty.startswith(("c", "p cnf")):
        invalid_headers.append(name)
print(f"instances={len(instances)}")
print(f"benchmark_cnfs={len(list(Path('benchmarks').glob('*.cnf')))}")
print(f"missing={len(missing)}")
print(f"extra={len(extra)}")
print(f"lfs_pointers={len(lfs_pointers)}")
print(f"invalid_headers={len(invalid_headers)}")
if missing:
    print("First missing entries:")
    for name in missing[:20]:
        print("  -", name)
    raise SystemExit(1)
if lfs_pointers:
    print("First Git LFS pointer files, not real CNF:")
    for name in lfs_pointers[:20]:
        print("  -", name)
    raise SystemExit(1)
if invalid_headers:
    print("First invalid CNF headers:")
    for name in invalid_headers[:20]:
        print("  -", name)
    raise SystemExit(1)
if len(instances) != 289:
    raise SystemExit(f"expected 289 instances, got {len(instances)}")
PY
if [[ "${exit_code:-0}" != 0 ]]; then
  fail "benchmark completeness check failed"
else
  ok "all 289 benchmark CNFs are present"
fi
unset exit_code

section "3. Python Dependencies"
command -v python3 >/dev/null && ok "python3: $(command -v python3)" || fail "python3 not found"
python3 --version || true
for module in pysat psutil; do
  if python3 -c "import ${module}" >/dev/null 2>&1; then
    ok "python module importable: ${module}"
  else
    fail "missing Python module: ${module}; run: python3 -m pip install -r requirements.txt"
  fi
done
if python3 -c "import cplex" >/dev/null 2>&1; then
  ok "CPLEX Python binding importable"
else
  warn "CPLEX Python binding not importable; CPLEX jobs will fail until IBM CPLEX is installed/licensed"
fi

section "4. Solver Binaries"
check_solver() {
  local label="$1"
  local env_name="$2"
  local default_path="$3"
  local resolved="${!env_name:-$default_path}"
  if [[ -x "$resolved" ]]; then
    ok "$label executable: $resolved"
  else
    warn "$label executable not found/executable: $resolved (set $env_name or place binary there)"
  fi
}
check_solver "CASH" "CASH_BIN" "$ROOT/solvers/MaxSAT/cashwmaxsat-disjcom"
check_solver "MaxHS" "MAXHS_BIN" "$ROOT/solvers/MaxSAT/maxhs"
check_solver "WMaxCDCL" "WMAXCDCL_BIN" "$ROOT/solvers/MaxSAT/wmaxcdcl"

section "5. SLURM Availability"
if command -v sbatch >/dev/null; then
  ok "sbatch: $(command -v sbatch)"
else
  warn "sbatch not found; this server cannot submit SLURM jobs yet"
fi

section "6. Local Code Tests"
if ./run_all_experiments.sh prepare; then
  ok "prepare passed"
else
  fail "prepare failed"
fi
if ./run_all_experiments.sh test; then
  ok "self-test passed"
else
  fail "self-test failed"
fi

section "7. Generate SLURM Scripts"
if ./run_all_experiments.sh generate; then
  ok "SLURM generation passed"
else
  fail "SLURM generation failed"
fi

section "8. Generated Script Sanity"
sh_count=$(find slurm -maxdepth 1 -name '*.sh' | wc -l)
job_count=$(find slurm -maxdepth 1 \( -name 'transform-*.sh' -o -name 'solve-*.sh' -o -name 'baseline-*.sh' \) | wc -l)
echo "shell_files=$sh_count"
echo "job_scripts=$job_count"
[[ "$sh_count" -eq 174 ]] || fail "expected 174 shell files, got $sh_count"
[[ "$job_count" -eq 170 ]] || fail "expected 170 array job scripts, got $job_count"

for required_script in \
  slurm/solve-CPLEX-SEv1-k2-QP.sh \
  slurm/solve-CPLEX-SEv3-k10-QP.sh \
  slurm/submit_transforms.sh \
  slurm/submit_solves.sh \
  slurm/submit_baselines.sh \
  slurm/submit_all.sh
do
  check_file "$required_script"
done

if grep -R "/users/scherif/ComputeSpace/DiverseSAT/benchmarks" slurm >/dev/null 2>&1; then
  fail "generated SLURM scripts still contain old external benchmark path"
else
  ok "generated SLURM scripts use local benchmark defaults"
fi

if grep -R "\$ROOT/benchmarks" slurm/transform-SEv1-k2-OH.sh >/dev/null 2>&1; then
  ok "transform scripts default to local benchmarks"
else
  fail "transform scripts do not default to local benchmarks"
fi

section "9. Shell Syntax"
while IFS= read -r script; do
  bash -n "$script" || fail "shell syntax failed: $script"
done < <(find . -name '*.sh' -type f | sort)
ok "shell syntax checked"

section "10. Final Result"
if [[ "$ERRORS" -eq 0 ]]; then
  echo "[READY] fatal checks passed with $WARNINGS warning(s)."
  echo "Next steps:"
  echo "  1. Install/configure warned solver dependencies if needed."
  echo "  2. Submit transforms first:  cd slurm && bash submit_transforms.sh"
  echo "  3. After transforms finish: bash submit_solves.sh"
  echo "  4. Baselines can run anytime: bash submit_baselines.sh"
  exit 0
fi

echo "[NOT READY] $ERRORS error(s), $WARNINGS warning(s). Fix errors before submitting."
exit 1

