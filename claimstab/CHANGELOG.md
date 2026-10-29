# Changelog

## 0.3.0 - 2026-10-29

- Added planned, interpretable, and missing specification counts.
- Added explicit specification coverage and a strong-to-moderate cap when any
  planned specification is missing.
- Added optional `manual_override_reason` while retaining the automatic grade.
- Matched observed-label and null-control PERMANOVA internal permutations at
  999 in the public benchmark.
- Clarified that the 400 label-permutation claim evaluations are nested within
  80 dataset-permutation combinations.

## 0.2.0 - 2026-10-27

- Added `claimstab compare` for auditable comparison with majority and strict
  multiverse/sensitivity rules.
- Added a four-dataset public microbiome benchmark covering GlobalPatterns,
  enterotype, soilrep and Atlas1006.
- Added label-permutation false-support controls and endpoint-condition
  summaries.
- Corrected the soil benchmark to aggregate technical replicates to 24
  independent communities before inference.
- Clarified that claimstab's observed advantage is specification
  discrimination and auditability; the benchmark does not establish binary
  superiority over a strict all-specifications rule.

## 0.1.0 - 2026-10-26

- Added four-stage claim-stability framework.
- Added CSV schemas for claims, reconstruction audits and endpoint results.
- Added endpoint-dependence and claim-stability matrix generation.
- Added automatic evidence grading with explicit manual override.
- Added minimal example, QZ grassland example, tests and framework diagram.
- Added the independent public `GlobalPatterns` case study.
