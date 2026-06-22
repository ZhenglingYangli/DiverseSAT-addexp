#!/usr/bin/env python3
"""DIMACS helpers shared by all clean rerun pipelines."""

from __future__ import annotations

from pathlib import Path

from pysat.formula import CNF


def declared_var_count(path: str | Path) -> int | None:
    """Return the variable count declared by the DIMACS ``p cnf`` header."""
    for line in Path(path).read_text(errors="replace").splitlines():
        parts = line.strip().split()
        if len(parts) >= 4 and parts[0] == "p" and parts[1] == "cnf":
            return int(parts[2])
    return None


def load_cnf(path: str | Path) -> CNF:
    """Load a CNF while preserving header-declared unconstrained variables."""
    cnf = CNF(from_file=str(path))
    declared = declared_var_count(path)
    if declared is not None and declared > cnf.nv:
        cnf.nv = declared
    return cnf
