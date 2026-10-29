# claimstab

`claimstab` converts cross-pipeline endpoint results into an auditable claim
stability matrix. It implements a four-component framework:

1. **Data reconstruction**: did alternative pipelines recover the same
   underlying data layer?
2. **Analysis dependence**: do direction, significance, or ranking change across
   pipelines, sample sets, or distance metrics?
3. **Inference stability**: is the scientific claim stable, conditional,
   unstable, or not verifiable?
4. **Evidence grade**: strong, moderate, descriptive, not supported, or not
   verifiable.

The package does not run a preferred statistical pipeline. It organises results
from different pipelines so that a claim can be evaluated without conflating
data reconstruction with downstream inference.

## Installation

Python 3.10 or newer is required. There are no third-party dependencies.

```bash
python -m pip install .
```

For development without installation, place `src/` on `PYTHONPATH` and run
`python -m claimstab build --help` or `python -m claimstab compare --help`.

A pre-built wheel and source archive are in `dist/`; SHA256 checksums are in
`dist/SHA256SUMS.txt`.

## Inputs

### `claims.csv`

One row per scientific claim.

| Column | Required | Values |
| --- | --- | --- |
| `claim_id` | yes | unique identifier |
| `claim_text` | yes | concise claim |
| `claim_type` | yes | `effect`, `difference`, `null`, `ranking`, `not_verifiable` |
| `reconstruction_id` | yes | links to the reconstruction audit |
| `manual_evidence_grade` | no | optional override |
| `manual_override_reason` | no | reason for manual grade change |
| `notes` | no | free text |

### `reconstruction.csv`

One row per data-layer or measurement-layer reconstruction check.

| Column | Required | Values |
| --- | --- | --- |
| `reconstruction_id` | yes | identifier used by `claims.csv` |
| `domain` | yes | e.g. 16S, ITS |
| `layer` | yes | e.g. phylum, alpha, ASV |
| `metric` | yes | e.g. mean_sample_bray |
| `value` | no | numeric value |
| `threshold` | no | descriptive threshold |
| `status` | yes | `stable`, `partial`, `unstable`, `not_available` |
| `source` | no | source path or identifier |
| `notes` | no | free text |

The analyst supplies `status`; this avoids a package silently choosing a
discipline-specific threshold. Multiple metric rows may share one
`reconstruction_id`.

### `endpoints.csv`

One row per result from one pipeline and one sample set.

| Column | Required | Values |
| --- | --- | --- |
| `claim_id` | yes | links to `claims.csv` |
| `domain` | yes | e.g. 16S, ITS |
| `outcome` | yes | e.g. beta_composition |
| `contrast` | yes | comparison or endpoint label |
| `pipeline` | yes | OTU, ASV-phylum, ASV, etc. |
| `sample_set` | yes | primary15, sensitivity18, etc. |
| `estimate` | no | effect size or statistic |
| `p_value` | no | numeric p value |
| `direction` | no | `positive`, `negative`, `none`, `not_applicable` |
| `rank` | no | integer rank for ranking claims |
| `testable` | yes | `true` or `false` |
| `source` | no | source path |
| `notes` | no | free text |

Rows are grouped by:

```text
claim_id × domain × outcome × contrast × sample_set
```

Each group compares the same endpoint across different pipelines.

The comparison denominator contains only interpretable specifications with a
valid estimate and P value. Planned but untestable specifications are retained
in the planned count and reported as missing; they never count as support. Any
missing planned specification caps an otherwise strong automatic grade at
moderate.

JSON Schema documents for all three CSV formats are in `schemas/`.

## Run

```bash
python -m claimstab build \
  --claims examples/minimal/claims.csv \
  --reconstruction examples/minimal/reconstruction.csv \
  --endpoints examples/minimal/endpoints.csv \
  --output-dir examples/minimal/output \
  --alpha 0.05
```

The `examples/qz_mic/` directory contains the complete grassland case study and
can be rebuilt with its project-specific `build_inputs.py` adapter.
The `examples/globalpatterns/` directory contains an independent public-data
case based on the phyloseq `GlobalPatterns` dataset.

To compare the four-component evidence grade with simpler multiverse/sensitivity
rules:

```bash
python -m claimstab compare \
  --claims examples/globalpatterns/claims.csv \
  --reconstruction examples/globalpatterns/reconstruction.csv \
  --endpoints examples/globalpatterns/endpoints.csv \
  --output-dir examples/globalpatterns/comparison
```

The comparison reports three rules:

- `majority`: more than half of interpretable specifications support the claim;
- `strict`: every interpretable specification supports the claim;
- `claimstab`: evidence grade is `strong` or `moderate`.

The `examples/public_multidataset/` directory contains the four-dataset public
benchmark and permuted-label negative controls.

## Outputs

- `endpoint_dependency.csv`: one row per endpoint comparison group;
- `claim_stability_matrix.csv`: one row per claim, including planned,
  interpretable, missing, and specification-coverage fields;
- `reconstruction_summary.csv`: reconstruction status and source records;
- `report.md`: human-readable summary and decision rules.

The `compare` command also emits:

- `framework_comparison.csv`: claim-level calls under all three rules;
- `framework_summary.csv`: counts by dataset, framework and call.

## Benchmark boundary

In the current public benchmark, the four-component rule removes five
majority-only overconfident calls. Its binary supported/not-supported decision
coincides with the strict all-specifications rule. Its added value is therefore
an auditable explanation of the conditions under which a claim is supported,
not superior binary accuracy over a strict multiverse rule.

## Evidence rules

Automatic grading is deliberately conservative.

- `strong`: stable reconstruction, low dependence on analytical choices, and stable
  direction/significance with complete specification coverage, or a stable
  null result for a null claim.
- `moderate`: stable inference with partial reconstruction or one moderate
  sensitivity; missing planned specifications also cap an otherwise strong
  result at moderate.
- `descriptive`: stable direction or ranking without full significance support.
- `not_supported`: mixed direction/ranking, or an effect claim with stable null
  results.
- `not_verifiable`: required data or testable results are unavailable.

`manual_evidence_grade` can override the automatic result, but the automatic
grade remains in the output for audit.

## Scope

`claimstab` does not calculate p values, choose statistical tests, or decide
whether a biological claim is true. It audits claims already evaluated across
explicit analysis choices.

## License

MIT License. See `LICENSE`.
