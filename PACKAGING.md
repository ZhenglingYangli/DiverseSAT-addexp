# Packaging `new-exps` for a Fresh Server

Only copy this directory:

```bash
tar czf new-exps.tar.gz new-exps
```

On the new server:

```bash
tar xzf new-exps.tar.gz
cd new-exps
python3 -m pip install -r requirements.txt
./server_preflight.sh
```

## Included

- all experiment Python code
- SLURM generator and generated staged submit scripts
- 289 benchmark CNF files in `benchmarks/`
- 289-instance manifest in `instances/289_instances.txt`
- baseline scripts using PySAT `Cadical195` and RC2
- local self tests
- sumup script
- `.gitignore` that keeps source/CNF/SLURM scripts but excludes generated WCNF,
  results, logs, caches, and local archives

## Not Included

These cannot be copied from the current workspace because they are not present
or require external installation/license setup:

- IBM CPLEX runtime, license, and Python bindings
- `cashwmaxsat-disjcom`
- `maxhs`
- `wmaxcdcl`
- SLURM itself

Place MaxSAT binaries under:

```text
solvers/MaxSAT/cashwmaxsat-disjcom
solvers/MaxSAT/maxhs
solvers/MaxSAT/wmaxcdcl
```

or set `CASH_BIN`, `MAXHS_BIN`, and `WMAXCDCL_BIN`.

