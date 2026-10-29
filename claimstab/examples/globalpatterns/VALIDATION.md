## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: validate
- Origin Date: 2026-10-26
- Verification Status: VERIFIED
- Version Label: globalpatterns_validation_v1

## Validation Report

- **Source**: `GlobalPatterns` from phyloseq
- **Original study**: Caporaso et al. (2011), DOI `10.1073/pnas.1000080107`
- **Overall Confidence**: CAUTION

The caution level reflects unbalanced sample-type group sizes and the use of a
single public dataset, not an execution or reproducibility failure.

### Statistical Findings

| Claim | Result across feature levels | Evidence grade |
| --- | --- | --- |
| Observed richness differs by sample type | Significant for OTU, genus and phylum in both sample sets | strong |
| Shannon differs by sample type | Significant for all levels and sample sets | strong |
| Simpson differs by sample type | Significant for all levels and sample sets | strong |
| Bray composition differs by sample type | R²=0.69–0.80; all P<0.001 | strong |
| Aitchison composition differs by sample type | R²=0.69–0.80; all P<0.001 | strong |
| Mock vs environment, Bray | Significant at OTU/genus; phylum P=0.0913 | not supported |
| Mock vs environment, Aitchison | Significant at OTU/genus; phylum P=0.1057 | not supported |

### Warnings

| Type | Detail | Affected |
| --- | --- | --- |
| Unbalanced groups | Sample-type counts range from 2 to 4 in the full set | Alpha tests |
| Small controls | Only three mock communities | Mock contrast |
| Resolution dependence | Phylum-level aggregation removed group separation in the mock contrast | Mock claims |
| Multiplicity | Several claims are part of a predefined sensitivity matrix | Evidence grading |

### Reproducibility

- **Method**: independent rerun of the deterministic R input builder.
- **Verdict**: REPRODUCIBLE.
- `claims.csv`, `reconstruction.csv` and `endpoints.csv` matched SHA256 exactly
  across two runs.
- The generic `claimstab` build produced identical output when run from the
  installed wheel and from the source tree.

### Fallacy Scan

- **Coverage**: 11/11.
- No causal, diagnostic base-rate, attrition, collider or reverse-causality
  claim is made.
- Look-elsewhere and forking-path risks are controlled by treating the set as a
  pre-specified stability matrix and reporting all claims.
