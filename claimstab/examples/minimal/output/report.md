# Claim stability report

## Framework

1. Data reconstruction
2. Analysis dependence
3. Inference stability
4. Evidence grade

Significance threshold: 0.05.

## Summary

- Claims: 3
- Reconstruction records: 3
- Evidence `descriptive`: 2
- Evidence `moderate`: 0
- Evidence `not_supported`: 0
- Evidence `not_verifiable`: 1
- Evidence `strong`: 0
- Analysis dependency `low`: 1
- Analysis dependency `moderate`: 1
- Analysis dependency `high`: 0
- Analysis dependency `not_evaluable`: 1

## Evidence rules

- Strong: stable reconstruction, low dependency, and stable
  direction/significance with complete specification coverage.
- Moderate: stable inference with partial reconstruction or one
  moderate sensitivity; any missing planned specification caps
  an otherwise strong claim at moderate.
- Descriptive: stable direction/ranking without full significance
  support.
- Not supported: mixed direction/ranking or an effect claim with
  stable null results.
- Not verifiable: required data are unavailable.

The generated grade is an audit aid. Analysts should set
`manual_evidence_grade` when domain reasoning requires an override;
the rationale should be recorded in `manual_override_reason`.
