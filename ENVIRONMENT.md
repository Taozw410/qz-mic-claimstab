# Software environment and run record

Date: 2026-10-29

## Primary software

| Component | Version |
| --- | --- |
| R | 4.5.3 |
| phyloseq | 1.54.2 |
| vegan | 2.7-6 |
| Python | 3.12.14 |
| pandas | 3.0.6 |
| NumPy | 2.5.3 |
| claimstab | 0.3.0 |

The QZ amplification analyses additionally used DADA2 1.38.0, ALDEx2 1.40.0,
and ANCOM-BC2 2.12.1 as reported in the manuscript.

## Fixed random seeds

- QZ reproducibility analyses: `20261023`.
- Public four-dataset benchmark: `20261027`.

## Inputs

- QZ archived FASTQ, OTU/phylum tables, alpha tables, and taxonomy files listed
  in the project data inventory.
- `GlobalPatterns`, `enterotype`, and `soilrep` from `phyloseq`.
- `atlas1006` from `microbiome`.

## Public benchmark run

```powershell
conda run -p D:\bioenv\envs\riz16s Rscript `
  脚本\build_public_multiverse.R output

python 脚本\summarize_public_benchmark.py `
  --benchmark-root output `
  --claimstab-root ..\..\07_可复用框架\claimstab `
  --output-dir output\summary
```

The run produces claims, reconstruction records, endpoints, claim-stability
matrices, framework comparisons, permutation summaries, condition summaries,
and the benchmark report.

## Scope

The run record supports computational reproduction of the published analysis
from the archived inputs. It does not replace independent field replication or
provide external evidence for the original ecological mechanism.
