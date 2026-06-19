#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common.sumup_common import main  # noqa: E402

if __name__ == "__main__":
    main(["--results-dir", str(ROOT / "maxhs/results"), "--out-dir", str(ROOT / "maxhs/sumup/results"), "--bench-dir", str(ROOT / "benchmarks")])
