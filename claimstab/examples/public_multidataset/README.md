# Four-dataset public microbiome benchmark

This example applies the four-component claim-stability framework to four
public microbiome datasets:

- `GlobalPatterns` from phyloseq (Caporaso et al. 2011);
- `enterotype` from phyloseq (Arumugam et al. 2011);
- `soilrep` from phyloseq (Zhou et al. 2011);
- `atlas1006` from microbiome (Lahti et al. 2014).

The benchmark tests framework portability. It is not an external replication of
the QZ grassland conclusion.

## Effective sample correction

The 56 sequencing records in `soilrep` represent 24 independent soil
microcosms with 2-3 technical replicates each. The benchmark aggregates
technical replicates by `Sample` before analysis.

`atlas1006` contains repeated measurements. Only `time == 0` is used, leaving
1006 independent participants.

## Comparison rules

- `majority`: more than half of interpretable specifications are significant;
- `strict`: every interpretable specification is significant;
- `claimstab`: reconstruction-aware evidence grade is `strong` or `moderate`.

The benchmark contains 32 observed-label claims and 400 nested
label-permutation claim evaluations.

## Key result

The majority rule supports 17/32 observed claims, while claimstab supports
12/32. The five majority-only claims contain endpoint threshold crossings and
are not supported by claimstab. The 400 label-permutation claim evaluations are
nested within 80 dataset-permutation combinations; all three compared rules
produced zero support decisions under the null.

The strict rule also supports 12/32 observed claims and, like claimstab, gives
no support decision under the label-permutation null. Therefore this benchmark
does not establish binary-accuracy superiority over the strict rule. Claimstab's
added value is the explicit reconstruction gate, specification coverage,
dependency diagnosis, stable-null distinction and auditable evidence grade.

The checked-in manuscript figure is
`multidataset_claim_stability.pdf`/`.png`; its source is
`figures_public_benchmark.py`, and `QA.md` records the alignment, glyph-size and
collision audits.

## Rebuild

```powershell
conda run -p D:\bioenv\envs\riz16s Rscript build_public_multiverse.R output
python summarize_public_benchmark.py `
  --benchmark-root output `
  --claimstab-root ..\.. `
  --output-dir output\summary
```

The checked-in `main/`, `permutation/` and `summary/` directories contain the
result used for the paper.
