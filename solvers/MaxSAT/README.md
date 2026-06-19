# MaxSAT Solver Binaries

The clean rerun uses three MaxSAT solvers: `MaxHS`, `WMaxCDCL`, and `CASH`.

## Bundled (ship with this package, tracked by Git LFS)

```text
solvers/MaxSAT/maxhs                  # MaxHS, static x86-64 ELF
solvers/MaxSAT/wmaxcdcl               # WMaxCDCL, static x86-64 ELF
solvers/MaxSAT/cashwmaxsat-disjcom    # CASH / CASHWMaxSAT, static x86-64 ELF
```

All three binaries are statically linked, so they run on a fresh x86-64 Linux
server without extra shared libraries (important when the server can only pull
this repo and has no general internet access). Verify after `git lfs pull`:

```bash
./solvers/MaxSAT/maxhs --help
./solvers/MaxSAT/wmaxcdcl --help
./solvers/MaxSAT/cashwmaxsat-disjcom --help
```

## Overriding any binary

Each solver path can be overridden by an env var (see `common/config.py`):

```bash
export MAXHS_BIN=/abs/path/maxhs
export WMAXCDCL_BIN=/abs/path/wmaxcdcl
export CASH_BIN=/abs/path/cashwmaxsat-disjcom
```

If a binary is missing, `./setup_solvers.sh` can build WMaxCDCL from source and
clone/build MaxHS (the latter needs IBM CPLEX C/C++ paths). Run
`./server_preflight.sh` to confirm all three resolve before submitting jobs.
