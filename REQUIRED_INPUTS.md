# Empty-Server Checklist

This rerun package assumes the new server is otherwise empty. Before submitting
jobs, prepare the following items.

## Data

Included in this directory:

- CNF benchmarks: `new-exps/benchmarks/*.cnf`
- Instance list: `new-exps/instances/289_instances.txt`

When this package is obtained from GitHub, the CNF benchmarks are tracked with
Git LFS. Install Git LFS before cloning, or run `git lfs pull` inside the
repository before running the preflight script. The preflight script rejects
Git LFS pointer files, so it will catch an incomplete clone.

The default benchmark location is `new-exps/benchmarks`. Override it only if you
want to use an external benchmark directory:

```bash
export BENCH_DIR=/absolute/path/to/benchmarks
```

Every line in `instances/289_instances.txt` must resolve to a file under the
selected `BENCH_DIR`.

## Python

Required Python packages:

```bash
python3 -m pip install python-sat psutil
```

For CPLEX jobs, IBM CPLEX Python bindings must be installed and importable:

```bash
python3 -c "import cplex; print(cplex.__version__)"
```

## Solver Binaries

Set these environment variables if the solver is not in the default location:

```bash
export CASH_BIN=/path/to/cashwmaxsat-disjcom
export MAXHS_BIN=/path/to/maxhs
export WMAXCDCL_BIN=/path/to/wmaxcdcl
```

The CaDiCaL and CaDiCaL-Greedy baselines use PySAT's `Cadical195` and RC2
interfaces, so they do not require an external CaDiCaL binary.

Default MaxSAT locations are inside this directory:

```text
solvers/MaxSAT/cashwmaxsat-disjcom
solvers/MaxSAT/maxhs
solvers/MaxSAT/wmaxcdcl
```

You can try the helper script:

```bash
./setup_solvers.sh all
```

It can usually download/build `WMaxCDCL` automatically. `MaxHS` requires IBM
CPLEX C/C++ library and include paths:

```bash
export LINUX_CPLEXLIBDIR=/path/to/cplex/lib/x86-64_linux/static_pic
export LINUX_CPLEXINCDIR=/path/to/cplex/include
./setup_solvers.sh maxhs
```

For `CASH`, provide a binary explicitly:

```bash
export CASH_BIN=/path/to/cashwmaxsat-disjcom
./setup_solvers.sh cash
```

## SLURM

The generated scripts assume:

- `sbatch` is available.
- one CPU per task.
- memory requests: 120 GB for transforms/CPLEX, 64 GB for MaxSAT, 32 GB for baseline.
- SLURM walltime: 3 hours per array task by default.
- individual solver timeout: 7200s.

## Pre-Submit Checks

Run:

```bash
cd new-exps
./run_all_experiments.sh prepare
python3 check_server_ready.py
./run_all_experiments.sh test
./run_all_experiments.sh generate
```

Then inspect:

```bash
ls slurm | wc -l
```

Expected: 174 shell files (`170` array job scripts plus `submit_transforms.sh`,
`submit_solves.sh`, `submit_baselines.sh`, and a guarded `submit_all.sh`). Each
job script uses `#SBATCH --array=1-289`, so the full matrix expands to 49,130
array tasks.

