# Claim stability report

## Framework

1. Data reconstruction
2. Analysis dependence
3. Inference stability
4. Evidence grade

Significance threshold: 0.05.

## Summary

- Claims: 14
- Reconstruction records: 6
- Evidence `descriptive`: 2
- Evidence `moderate`: 5
- Evidence `not_supported`: 5
- Evidence `not_verifiable`: 2
- Evidence `strong`: 0
- Analysis dependency `low`: 6
- Analysis dependency `moderate`: 0
- Analysis dependency `high`: 6
- Analysis dependency `not_evaluable`: 2

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
