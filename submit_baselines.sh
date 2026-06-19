#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
for d in cadical cadical_greedy; do (cd "$ROOT/$d/jobs" && bash submit_baselines.sh); done
