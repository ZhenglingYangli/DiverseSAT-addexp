# Clean Rerun Experiments for DiverseSAT Journal Version

This directory is a fresh rerun package. It does not continue the historical
`exp1`--`exp7` naming. The goal is to rerun the journal matrix with one
consistent semantics:

- `SEv1`: strict lexicographic SE with explicit `SE-4` and `SE-5`.
- `SEv3`: diagonal dominance plus explicit pairwise distinctness.
- cutoff: `7200s`.
- benchmark list: `instances/289_instances.txt`.

## Experiment Matrix

| block | solver | encodings | k |
|---|---|---|---|
| Baseline | CaDiCaL | original CNF | 2, 3, 4, 5, 10 |
| Baseline | CaDiCaL-Greedy | original CNF | 2, 3, 4, 5, 10 |
| Exact | CPLEX | QP, OH, UNA, BIN | 2, 3, 4, 5, 10 |
| Exact | CASH | OH, UNA, BIN | 2, 3, 4, 5, 10 |
| Exact | MaxHS | OH, UNA, BIN | 2, 3, 4, 5, 10 |
| Exact | WMaxCDCL | OH, UNA, BIN | 2, 3, 4, 5, 10 |

The exact blocks are run for both `SEv1` and `SEv3`.

## Why This Exists

The old `added_experiment` SEv1 scripts used a historical non-strict lex chain:
`SE-1/2/3`, without explicit `SE-4` and without `SE-5` distinctness. That is not
the same as the strict journal formulation. This package fixes that at the
encoding level instead of only re-summarizing old logs.

## Quick Start

```bash
git lfs install
git clone git@github.com:ZhenglingYangli/DiverseSAT-addexp.git
cd DiverseSAT-addexp
git lfs pull

# local smoke tests and self-contained data check
./server_preflight.sh

# generate all SLURM scripts
./run_all_experiments.sh generate

# on the cluster: submit in stages
cd slurm
bash submit_transforms.sh
# wait until transform arrays finish
bash submit_solves.sh
bash submit_baselines.sh

# after jobs finish
cd ..
./run_all_experiments.sh sumup
```

## Outputs

- transformed WCNF: `benchmarks/k_<K>-<ENC>-<SE>/`
- raw logs: `results/<solver>-<encoding>-k<K>-<SE>/`
- summary CSV: `sumup/results/`
- SLURM scripts: `slurm/`

## Notes

The 289 CNF benchmark files are stored under `benchmarks/` and tracked with
Git LFS because the largest instance exceeds GitHub's regular file-size limit.
On a fresh server, install Git LFS before cloning or run `git lfs pull` after
cloning. Once LFS files are present, the server only needs this repository plus
solver installations/licenses.

XOR/GaussMaxHS is not part of this clean main rerun matrix. The previous XOR
experiment can remain a historical negative exploration. If XOR is needed as a
strict-formulation comparison, it should be added later with the same explicit
`SE-5` distinctness rule.

