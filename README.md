# DiverseSAT Strict-SE Rerun

This is the clean rerun package for the journal experiments. The repository is
code-only: it does not include benchmark CNFs, solver binaries, or Git LFS
objects.

## One Command

On the original SLURM cluster:

```bash
cd new-exps
python3 -m pip install -r requirements.txt
bash run_cluster_pipeline.sh
```

`run_cluster_pipeline.sh` checks the real cluster environment, runs local tests,
generates SLURM jobs, submits the full experiment matrix, and automatically
submits the final sumup job after the solver jobs finish.

Default external paths are built into the script. MaxSAT solvers are read from
the sibling `added_experiment` directory used by the old runs:

```text
BENCH_DIR=/users/scherif/ComputeSpace/DiverseSAT/benchmarks
CASH_BIN=../added_experiment/solvers/MaxSAT/cashwmaxsat-disjcom
MAXHS_BIN=../added_experiment/solvers/MaxSAT/maxhs
WMAXCDCL_BIN=../added_experiment/solvers/MaxSAT/wmaxcdcl
INSTANCE_LIST=new-exps/codes/289_instances.txt
```

If a path differs, export it before running the script, for example:

```bash
export BENCH_DIR=/path/to/benchmarks
export CASH_BIN=/path/to/cashwmaxsat-disjcom
export MAXHS_BIN=/path/to/maxhs
export WMAXCDCL_BIN=/path/to/wmaxcdcl
bash run_cluster_pipeline.sh
```

## Experiment Matrix

- SE modes: strict `SEv1` with explicit `SE-4/SE-5`, and strict `SEv3` with explicit pairwise distinctness.
- Cutoff: `7200s`.
- k values: `2, 3, 4, 5, 10`.
- Exact solvers: `CPLEX` with `QP/OH/UNA/BIN`; `CASH`, `MaxHS`, `WMaxCDCL` with `OH/UNA/BIN`.
- Baselines: `CaDiCaL` and `CaDiCaL-Greedy`.
- Generated matrix: 170 SLURM array scripts, 49,130 array tasks.

## Layout

- `codes/`: source code and the 289-instance manifest.
- `jobs/generate_slurm.py`: creates all runtime job scripts under `jobs/`.
- `jobs/`: generated at runtime by the pipeline.
- `results/`: raw solver logs and transformed WCNF files.
- `sumup/`: per-SE and combined CSV summaries.

CASH may be a proxy script rather than a plain binary. The runner executes each
external MaxSAT solver call in an isolated temporary work directory under the
corresponding result folder, then cleans it up, so proxy-generated files such as
`output_*`, `*.var`, `*.wat`, and `maxsat.wcnf` do not collide across array
tasks.

Expected final output:

```text
sumup/SEv1/results/
sumup/SEv3/results/
sumup/baseline/results/
sumup/combined/results/all_results.csv
```

## Runtime Estimate

The wall time depends mainly on SLURM array concurrency after the jobs leave the
queue. Approximate total time:

- 500 concurrent tasks: 9-13 days.
- 1,000 concurrent tasks: 5-8 days.
- 2,000 concurrent tasks: 3-5 days.
- 5,000+ concurrent tasks: 1.5-3 days.

