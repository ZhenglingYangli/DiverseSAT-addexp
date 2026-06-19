#!/usr/bin/env bash
set -euo pipefail
echo 'Do not submit all stages at once: MaxSAT solve jobs need transformed WCNF files.' >&2
echo 'Use: bash submit_transforms.sh; wait for completion; bash submit_solves.sh; bash submit_baselines.sh' >&2
exit 1
