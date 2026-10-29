# Figure 3 QA

Date: 2026-10-27

## Figure contract

**Results question:** Does the four-component claim-stability decision agree with
majority support across independent microbiome datasets, and where does that
support concentrate?

**Figure claim:** `claimstab` is more conservative than a majority rule at
endpoint threshold crossings, but its binary support boundary is not superior
to a strict all-specifications rule.

**Archetype:** quantitative grid.

| Panel | Evidence role | Decisive comparison |
| --- | --- | --- |
| a | Primary dataset-level comparison | Majority versus claimstab-supported claim counts |
| b | Boundary condition | Support rate across maximum endpoint P categories |
| c | Effect-dependence check | Support rate across effect-retention categories |

## Source data

- `../../03_结果/15_多数据集框架验证/汇总/main_comparison/framework_comparison.csv`
- `../../03_结果/15_多数据集框架验证/汇总/condition_summary.csv`

No observations were dropped for plotting. Panel sample counts are the
predefined claims in the public benchmark.

## Statistical definition

- n: number of claims in a dataset or condition bin;
- center: descriptive support proportion or count;
- uncertainty: no interval is assigned to these predefined-grid proportions;
- majority-supported: more than half of testable specifications significant;
- claimstab-supported: evidence grade strong or moderate;
- statistical tests are documented in the benchmark README, not re-run in the
  plotting script.

## Export and audit

- Final physical width: 182.9 mm;
- Formats: SVG, PDF, PNG, 600-dpi TIFF;
- Editable text: PDF TrueType and SVG text enabled;
- PDF glyph floor: PASS, minimum 6.2 pt;
- Multi-panel alignment: PASS, one documented width exemption for the wider
  dataset panel;
- Rendered collision audit: PASS, 0 FAIL and 0 WARN;
- Panel labels: lowercase bold a–c, fixed point offsets;
- Source preflight: 0 FAIL; one non-blocking WARN for preserving the canonical
  software name `claimstab` in lowercase.

## Files

- `multidataset_claim_stability.svg`
- `multidataset_claim_stability.pdf`
- `multidataset_claim_stability.png`
- `multidataset_claim_stability.tiff`
- `multidataset_claim_stability.alignment-layout.json`
- `multidataset_claim_stability.alignment.svg`
- `multidataset_claim_stability.collision-audit.json`
- `multidataset_claim_stability.collision-audit.pdf`
