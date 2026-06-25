#!/usr/bin/env python3
"""Shared configuration for the clean DiverseSAT rerun package."""

from __future__ import annotations

K_VALUES = [2, 3, 4, 5, 10]
ENCODINGS = ["OH", "UNA", "BIN"]
CPLEX_ENCODINGS = ["QP", "OH", "UNA", "BIN"]
MAXSAT_ENCODINGS = ["OH", "UNA", "BIN"]
SE_MODES = ["SEv1", "SEv3"]

BASELINE_SOLVERS = ["CaDiCaL", "CaDiCaL-Greedy"]
OPT_SOLVERS = ["CPLEX", "CASH", "MaxHS", "WMaxCDCL"]
MAXSAT_SOLVERS = ["CASH", "MaxHS", "WMaxCDCL"]

CUTOFF_SECONDS = 7200
TRANSFORM_CUTOFF_SECONDS = 7200
DEFAULT_MEM_GB = 120

# MaxSAT solvers default to sibling added_experiment's solver directory.
# Override with BENCH_DIR/CASH_BIN/MAXHS_BIN/WMAXCDCL_BIN if the paths differ.
DEFAULT_BENCH_DIR = "/users/scherif/ComputeSpace/DiverseSAT/benchmarks"
DEFAULT_INSTANCE_LIST = "codes/289_instances.txt"

MAXSAT_BIN_ENV = {
    "CASH": "CASH_BIN",
    "MaxHS": "MAXHS_BIN",
    "WMaxCDCL": "WMAXCDCL_BIN",
}

MAXSAT_DEFAULT_BINS = {
    "CASH": "$ROOT/../added_experiment/solvers/MaxSAT/CASHWMaxSAT_DisjCom_noscip",
    "MaxHS": "$ROOT/../added_experiment/solvers/MaxSAT/maxhs",
    "WMaxCDCL": "$ROOT/../added_experiment/solvers/MaxSAT/wmaxcdcl",
}

BASELINE_BIN_ENV = {
    "CaDiCaL": "CADICAL_BIN",
    "CaDiCaL-Greedy": "CADICAL_GREEDY_BIN",
}

