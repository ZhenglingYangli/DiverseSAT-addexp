#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
for d in cplex cash maxhs wmaxcdcl; do (cd "$ROOT/$d/jobs" && bash submit_solves.sh); done
