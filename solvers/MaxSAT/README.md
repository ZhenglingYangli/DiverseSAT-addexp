# MaxSAT Solver Binaries

Place the solver binaries here when copying `new-exps/` to a fresh server:

```text
solvers/MaxSAT/cashwmaxsat-disjcom
solvers/MaxSAT/maxhs
solvers/MaxSAT/wmaxcdcl
```

Alternatively, keep the binaries elsewhere and set:

```bash
export CASH_BIN=/absolute/path/to/cashwmaxsat-disjcom
export MAXHS_BIN=/absolute/path/to/maxhs
export WMAXCDCL_BIN=/absolute/path/to/wmaxcdcl
```

The binaries are not included in this local package because they are not present
in the current workspace.

