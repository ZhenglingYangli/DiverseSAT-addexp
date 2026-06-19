# Run Plan and Time Estimate

## Generated Workload

The package generates 170 SLURM array scripts. Each uses:

```text
#SBATCH --array=1-289
```

So the full matrix expands to:

| block | scripts | array tasks | task cutoff |
|---|---:|---:|---:|
| WCNF transforms | 30 | 8,670 | 3h walltime |
| CPLEX solve | 40 | 11,560 | 3h walltime, 7200s solver cutoff |
| MaxSAT solve | 90 | 26,010 | 3h walltime, 7200s solver cutoff |
| Baselines | 10 | 2,890 | 3h walltime, 7200s wrapper cutoff |
| Total | 170 | 49,130 |  |

## Suggested Submit Order

1. Run local checks on the server:

   ```bash
   cd new-exps
   python3 check_server_ready.py
   ./run_all_experiments.sh prepare
   ./run_all_experiments.sh test
   ./run_all_experiments.sh generate
   ```

2. Submit transform jobs first:

   ```bash
   cd slurm
   bash submit_transforms.sh
   ```

3. After transforms finish, submit exact solver jobs:

   ```bash
   bash submit_solves.sh
   ```

4. Baseline jobs can run independently:

   ```bash
   bash submit_baselines.sh
   ```

5. Aggregate:

   ```bash
   cd ..
   ./run_all_experiments.sh sumup
   ```

## Runtime Estimate

The strict SEv1/SEv3 encodings are larger than the old non-strict runs because
they add explicit distinctness. The worst case is still bounded by the 7200s
per-instance cutoff.

Rough estimates, assuming the cluster can run many array tasks concurrently:

| block | optimistic | conservative | comment |
|---|---:|---:|---|
| transforms | 1--6h | 12--24h | strict distinctness may make high-k transforms larger |
| baselines | <1h | 3--8h | PySAT RC2 greedy can be slow on some large instances |
| CPLEX | 1--2 days | 3--5 days | many hard high-k tasks may hit cutoff |
| MaxSAT | 1--3 days | 4--7 days | 26,010 tasks, scheduler throughput dominates |
| total wall-clock | 2--4 days | 1--2 weeks | depends mainly on queue limits and array concurrency |

If the cluster has strict array/concurrency limits, submit in waves by solver or
by `k` rather than using `submit_all.sh`.

## Important Risks

- The new strict SE formulations may be harder than the old non-strict runs.
- SEv3 now includes explicit pairwise distinctness; this is intentionally more
  faithful to Unique DiverseSAT but heavier than old exp4.
- CPLEX Python bindings and CPLEX license availability must be checked before
  submitting CPLEX array jobs.
- MaxSAT solver paths must be set via environment variables if the server is
  empty.
- `BENCH_DIR` must contain all files listed in `instances/289_instances.txt`.

## XOR

XOR/GaussMaxHS is not included in this main rerun. If the advisor wants XOR in
the strict matrix, add it later as a separate `XOR-strict` block with `SE-5`.
Do not reuse the old `exp3` as strict-SE evidence.

