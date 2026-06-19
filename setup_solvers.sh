#!/usr/bin/env bash
# Best-effort helper for preparing external MaxSAT solvers.
#
# This script is intentionally conservative:
# - WMaxCDCL has a public MaxSAT Evaluation source zip and can usually be built.
# - MaxHS is public but needs IBM CPLEX C/C++ libraries; build only when paths are set.
# - CASH/CASHWMaxSAT has no stable public one-command source URL here; provide or set it.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
BIN_DIR="$ROOT/solvers/MaxSAT"
SRC_DIR="$ROOT/solvers/src"

WMAXCDCL_URL="${WMAXCDCL_URL:-https://maxsat-evaluations.github.io/2023/mse23-solver-src/exact/WMaxCDCL.zip}"
MAXHS_REPO="${MAXHS_REPO:-https://github.com/fbacchus/MaxHS.git}"

mkdir -p "$BIN_DIR" "$SRC_DIR"

have() {
  command -v "$1" >/dev/null 2>&1
}

need_tools() {
  local missing=()
  for tool in git make unzip; do
    have "$tool" || missing+=("$tool")
  done
  if ! have curl && ! have wget; then
    missing+=("curl-or-wget")
  fi
  if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "[fail] missing required build/download tools: ${missing[*]}" >&2
    echo "       install them with your system package manager, then rerun this script." >&2
    exit 1
  fi
}

download() {
  local url="$1"
  local out="$2"
  if have curl; then
    curl -L "$url" -o "$out"
  else
    wget -O "$out" "$url"
  fi
}

mark_executable() {
  local path="$1"
  [[ -f "$path" ]] || return 1
  chmod +x "$path"
}

install_wmaxcdcl() {
  echo ""
  echo "================================================================"
  echo "== WMaxCDCL"
  echo "================================================================"
  if [[ -x "$BIN_DIR/wmaxcdcl" ]]; then
    echo "[ok] already installed: $BIN_DIR/wmaxcdcl"
    return
  fi

  local work="$SRC_DIR/WMaxCDCL"
  rm -rf "$work"
  mkdir -p "$work"
  download "$WMAXCDCL_URL" "$work/WMaxCDCL.zip"
  unzip -q "$work/WMaxCDCL.zip" -d "$work"

  local build_dir
  build_dir="$(find "$work" -type d -path '*/code/simp' | head -n 1 || true)"
  if [[ -z "$build_dir" ]]; then
    echo "[fail] could not find WMaxCDCL code/simp directory after unpacking" >&2
    return 1
  fi

  make -C "$build_dir"
  local binary
  binary="$(find "$build_dir" -maxdepth 2 -type f -perm -111 -name 'wmaxcdcl*' | head -n 1 || true)"
  if [[ -z "$binary" ]]; then
    echo "[fail] WMaxCDCL build finished but no executable named wmaxcdcl* was found" >&2
    return 1
  fi
  cp "$binary" "$BIN_DIR/wmaxcdcl"
  mark_executable "$BIN_DIR/wmaxcdcl"
  echo "[ok] installed: $BIN_DIR/wmaxcdcl"
}

install_maxhs() {
  echo ""
  echo "================================================================"
  echo "== MaxHS"
  echo "================================================================"
  if [[ -x "$BIN_DIR/maxhs" ]]; then
    echo "[ok] already installed: $BIN_DIR/maxhs"
    return
  fi

  local work="$SRC_DIR/MaxHS"
  if [[ ! -d "$work/.git" ]]; then
    rm -rf "$work"
    git clone "$MAXHS_REPO" "$work"
  fi

  if [[ -z "${LINUX_CPLEXLIBDIR:-}" || -z "${LINUX_CPLEXINCDIR:-}" ]]; then
    echo "[warn] MaxHS source downloaded, but build needs CPLEX C/C++ paths." >&2
    echo "       Set both variables and rerun:" >&2
    echo "       export LINUX_CPLEXLIBDIR=/path/to/cplex/lib/x86-64_linux/static_pic" >&2
    echo "       export LINUX_CPLEXINCDIR=/path/to/cplex/include" >&2
    echo "       ./setup_solvers.sh maxhs" >&2
    return 0
  fi

  make -C "$work" r \
    LINUX_CPLEXLIBDIR="$LINUX_CPLEXLIBDIR" \
    LINUX_CPLEXINCDIR="$LINUX_CPLEXINCDIR"

  local binary="$work/build/release/bin/maxhs"
  if [[ ! -x "$binary" ]]; then
    echo "[fail] MaxHS build finished but expected binary not found: $binary" >&2
    return 1
  fi
  cp "$binary" "$BIN_DIR/maxhs"
  mark_executable "$BIN_DIR/maxhs"
  echo "[ok] installed: $BIN_DIR/maxhs"
}

install_cash() {
  echo ""
  echo "================================================================"
  echo "== CASH / CASHWMaxSAT"
  echo "================================================================"
  if [[ -x "$BIN_DIR/cashwmaxsat-disjcom" ]]; then
    echo "[ok] already installed: $BIN_DIR/cashwmaxsat-disjcom"
    return
  fi
  if [[ -n "${CASH_BIN:-}" && -x "$CASH_BIN" ]]; then
    cp "$CASH_BIN" "$BIN_DIR/cashwmaxsat-disjcom"
    mark_executable "$BIN_DIR/cashwmaxsat-disjcom"
    echo "[ok] copied from CASH_BIN: $BIN_DIR/cashwmaxsat-disjcom"
    return
  fi

  echo "[warn] no stable public one-command CASH download is configured." >&2
  echo "       Put the solver binary at:" >&2
  echo "       $BIN_DIR/cashwmaxsat-disjcom" >&2
  echo "       or set CASH_BIN=/absolute/path/to/cashwmaxsat-disjcom and rerun:" >&2
  echo "       ./setup_solvers.sh cash" >&2
}

check_installed() {
  echo ""
  echo "================================================================"
  echo "== Installed Solver Check"
  echo "================================================================"
  for pair in \
    "CASH:$BIN_DIR/cashwmaxsat-disjcom" \
    "MaxHS:$BIN_DIR/maxhs" \
    "WMaxCDCL:$BIN_DIR/wmaxcdcl"
  do
    local label="${pair%%:*}"
    local path="${pair#*:}"
    if [[ -x "$path" ]]; then
      echo "[ok] $label: $path"
    else
      echo "[warn] $label missing: $path"
    fi
  done
}

main() {
  need_tools
  case "${1:-all}" in
    all)
      install_wmaxcdcl
      install_maxhs
      install_cash
      check_installed
      ;;
    wmaxcdcl) install_wmaxcdcl; check_installed ;;
    maxhs) install_maxhs; check_installed ;;
    cash) install_cash; check_installed ;;
    check) check_installed ;;
    *)
      echo "Usage: $0 {all|wmaxcdcl|maxhs|cash|check}" >&2
      exit 2
      ;;
  esac
}

main "$@"
