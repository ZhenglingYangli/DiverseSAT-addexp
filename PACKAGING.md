# Packaging `new-exps` for a Fresh Server

Only copy this directory:

```bash
tar czf new-exps.tar.gz new-exps
```

If using GitHub, clone with Git LFS enabled:

```bash
git lfs install
git clone git@github.com:ZhenglingYangli/DiverseSAT-addexp.git
cd DiverseSAT-addexp
git lfs pull
python3 -m pip install -r requirements.txt
./setup_solvers.sh all
./server_preflight.sh
```

If using an archive instead, make the archive after LFS files have been pulled
into the working tree. On the new server:

```bash
tar xzf new-exps.tar.gz
cd new-exps
python3 -m pip install -r requirements.txt
./server_preflight.sh
```

## Included

- all experiment Python code
- SLURM generator and generated staged submit scripts under solver-oriented
  `jobs/` directories
- 289 benchmark CNF files in `benchmarks/` (Git LFS when distributed through GitHub)
- 289-instance manifest in `instances/289_instances.txt`
- baseline scripts using PySAT `Cadical195` and RC2
- local self tests
- shared sumup parser plus thin per-solver sumup wrappers
- best-effort solver setup helper: `setup_solvers.sh`
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

