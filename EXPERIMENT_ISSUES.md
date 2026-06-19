# Experiment Issues Fixed by This Rerun

## 1. Historical SEv1 Was Non-Strict

The old `added_experiment` SEv1 implementations did not uniformly implement
the strict journal formulation.

Confirmed examples:

- `experiment-1/cplex/solvers/symmetry_elimination.py`
- `experiment-2-k=3,4/cplex/solvers/symmetry_elimination.py`
- `experiment-7-MaxSAT-SEv1-k34/transformers/SEv1_cnf_to_wcnf.py`
- `experiment-3-XOR/transformers/*SEv1XOR*`

They used the historical non-strict lex chain and omitted explicit `SE-5`
distinctness. The new package implements explicit `SE-4` and `SE-5`.

## 2. CPLEX `is_OPT` Parsing Bug

Old CPLEX `sumup.py` scripts misclassified some CPLEX statuses. The clean
package records the raw CPLEX status line:

```text
@@@ MIP_optimal
```

The new summary script treats `MIP_optimal` as proven optimal.

## 3. SEv3 Needs Explicit Uniqueness in the Main Matrix

The historical `SEv3` experiment was diagonal-dominance standalone and relied on
the diversity objective to discourage duplicates. For the journal main matrix,
the clean rerun adds pairwise distinctness to `SEv3` as hard constraints.

## 4. XOR/GaussMaxHS

The old XOR experiment is useful as a negative exploration, but it was also
non-strict with respect to `SE-5`. Therefore:

- It is not included in the clean main rerun matrix.
- It should not be used as a strict-SE main comparison unless rerun with
  explicit `SE-5`.
- If needed later, add a separate `XOR-strict` block rather than mixing it with
  the current main matrix.

