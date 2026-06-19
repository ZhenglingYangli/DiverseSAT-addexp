#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$SCRIPT_DIR"
sbatch baseline-CaDiCaL-k2.sh
sbatch baseline-CaDiCaL-Greedy-k2.sh
sbatch baseline-CaDiCaL-k3.sh
sbatch baseline-CaDiCaL-Greedy-k3.sh
sbatch baseline-CaDiCaL-k4.sh
sbatch baseline-CaDiCaL-Greedy-k4.sh
sbatch baseline-CaDiCaL-k5.sh
sbatch baseline-CaDiCaL-Greedy-k5.sh
sbatch baseline-CaDiCaL-k10.sh
sbatch baseline-CaDiCaL-Greedy-k10.sh
