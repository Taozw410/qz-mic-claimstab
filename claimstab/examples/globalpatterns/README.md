# GlobalPatterns external framework case

## Purpose

This example tests whether the four-component claim-stability framework can be
applied to a public dataset outside the QZ grassland experiment. It is a
portability test for the framework, not an external replication of the QZ
ecological conclusions.

## Data source

- Dataset: `GlobalPatterns`
- Source package: `phyloseq`
- Original study: Caporaso et al. (2011), DOI
  `10.1073/pnas.1000080107`
- Samples: 26
- OTUs: 19,216
- Sample types: 9, including three mock communities

The primary analysis retained all 26 samples. A sensitivity analysis excluded
the three mock communities, leaving 23 environmental samples.

## Feature levels

The same samples were represented at three levels:

- 19,216 OTUs;
- genus aggregation;
- phylum aggregation.

Unclassified entries were retained as `Unclassified`. Aggregation from OTUs to
genus and phylum preserved all sample totals exactly.

## Claims

1. Observed richness differs by sample type.
2. Shannon diversity differs by sample type.
3. Simpson diversity differs by sample type.
4. Bray-Curtis composition differs by sample type.
5. Aitchison composition differs by sample type.
6. Mock communities differ from environmental samples on Bray-Curtis.
7. Mock communities differ from environmental samples on Aitchison.

Alpha claims used Welch one-way tests after rarefaction to 58,688 reads.
Beta claims used PERMANOVA with 9,999 permutations.

## Result

- Five claims were graded `strong`: all three alpha metrics and both
  sample-type beta metrics stayed significant across OTU, genus and phylum
  levels and across the all-sample and environmental-sample sets.
- The mock-versus-environment claims were graded `not_supported` because the
  phylum-level tests were non-significant:
  - Bray-Curtis: P = 0.0913;
  - Aitchison: P = 0.1057.
  The lower feature levels were significant, so the claim depends on feature
  resolution.

This contrast shows that the framework can retain strong claims and reject
resolution-dependent omnibus claims on an independent public dataset.

## Rebuild

```bash
conda run -p D:\bioenv\envs\riz16s Rscript build_inputs.R .
```

Then:

```bash
python -m claimstab build \
  --claims claims.csv \
  --reconstruction reconstruction.csv \
  --endpoints endpoints.csv \
  --output-dir output \
  --alpha 0.05
```

## Files

- `claims.csv`
- `reconstruction.csv`
- `endpoints.csv`
- `output/claim_stability_matrix.csv`
- `output/endpoint_dependency.csv`
- `output/reconstruction_summary.csv`
- `output/report.md`
- `VALIDATION.md`
