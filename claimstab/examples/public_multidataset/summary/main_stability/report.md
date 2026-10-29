# Claim stability report

## Framework

1. Data reconstruction
2. Analysis dependence
3. Inference stability
4. Evidence grade

Significance threshold: 0.05.

## Summary

- Claims: 32
- Reconstruction records: 4
- Evidence `descriptive`: 0
- Evidence `moderate`: 4
- Evidence `not_supported`: 20
- Evidence `not_verifiable`: 0
- Evidence `strong`: 8
- Analysis dependency `low`: 23
- Analysis dependency `moderate`: 0
- Analysis dependency `high`: 9
- Analysis dependency `not_evaluable`: 0

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
