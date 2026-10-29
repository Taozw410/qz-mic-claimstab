# Four-component claim-stability framework

## Purpose

The framework separates four questions that are often collapsed into a single
statement that a study was “reproduced” or “not reproduced”.

## Component 1: Data reconstruction

Question: can the alternative analysis recover the same data layer?

Examples:

- sample identifiers and read totals;
- phylum-level composition from OTU and ASV pipelines;
- taxonomic ranks before and after a database update;
- alpha-diversity sample rankings across representation choices.

Input: `reconstruction.csv`.

Output status:

- `stable`;
- `partial`;
- `unstable`;
- `not_available`.

This status is supplied by the analyst. A package should not choose a
discipline-specific threshold silently.

## Component 2: Dependence on analytical choices

Question: which downstream conclusions change when defensible analysis
decisions are varied?

The package compares direction, p-value decision and rank within each group:

```text
claim × domain × outcome × contrast × sample set
```

Claim types are `effect` for directional effects, `difference` for omnibus
tests, `null` for explicitly null claims, `ranking` for ordered comparisons, and
`not_verifiable` for claims without usable inputs.

Output per group:

- `direction_stability`;
- `significance_stability`;
- `rank_stability`;
- `dependency_level`;
- minimum and maximum estimates and p values;
- pipelines compared.

## Component 3: Inference stability

Question: is the scientific claim stable after combining reconstruction and
endpoint-level dependence?

Output categories:

- `stable`;
- `conditional`;
- `unstable`;
- `not_verifiable`.

The status is derived from all endpoint groups belonging to a claim.

## Component 4: Evidence grading

The framework produces an automatic audit grade:

| Grade | Rule |
| --- | --- |
| `strong` | reconstruction stable, dependency low, direction/significance stable, and no planned specification missing |
| `moderate` | stable inference with partial reconstruction, one moderate sensitivity, or any missing planned specification |
| `descriptive` | stable direction or ranking without full significance support |
| `not_supported` | mixed direction/ranking or stable null result for an effect claim |
| `not_verifiable` | required data or testable results unavailable |

An analyst can provide `manual_evidence_grade` when domain reasoning requires an
override. The automatic grade remains visible for audit, and
`manual_override_reason` records why the grade changed. A manual change without
a reason remains flagged for review.

The rule denominators contain interpretable specifications. Planned but
uninterpretable specifications remain in the audit record and are reported as
missing. An otherwise strong automatic grade is capped at moderate whenever a
planned specification is missing.

## Comparison with multiverse and sensitivity rules

`claimstab compare` separates three decision rules:

| Rule | Supported when |
| --- | --- |
| majority | more than half of interpretable specifications support the claim |
| strict | every interpretable specification supports the claim |
| claimstab | reconstruction-aware evidence grade is `strong` or `moderate` |

The majority rule is useful for summarising a specification curve but can hide
threshold crossings. For example, four of six significant specifications do not
establish an endpoint-wide result. The strict rule is conservative and, in the
current benchmark, gives the same binary supported/not-supported calls as
`claimstab`. The distinctive value of `claimstab` is therefore the visible
reconstruction gate, specification coverage, dependency diagnosis, stable-null
distinction and source traceability, not a demonstrated accuracy advantage over
the strict rule.

## Recommended reporting

For each claim, report:

1. the scientific statement;
2. the reconstruction layer and its status;
3. the pipelines, sample sets and endpoints compared;
4. direction and significance stability;
5. rank stability for ranking claims;
6. the final evidence grade and any manual override;
7. source files for every endpoint.

Do not report zero support decisions under a label-permutation null as a zero
false-positive rate. Multiple claim evaluations can share labels and distance
matrices. Negative controls evaluate overconfidence only; independent positive
validation remains necessary.

## What the framework cannot do

- It cannot choose the biologically correct statistical model.
- It cannot replace independent replication.
- It cannot turn non-significance into evidence of no effect.
- It cannot recover missing analysis inputs.
- It cannot validate a claim that was never testable with the available data.
