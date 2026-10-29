from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SECTION_DIR = ROOT / "05_稿件"
TABLE_DIR = ROOT / "03_结果" / "14_分析可重复性" / "06_论文表格"
CONDITION_TABLE = (
    ROOT
    / "03_结果"
    / "15_多数据集框架验证"
    / "汇总"
    / "condition_summary.csv"
)
MAJORITY_ONLY_TABLE = (
    ROOT
    / "03_结果"
    / "15_多数据集框架验证"
    / "汇总"
    / "framework_overconfident_claims.csv"
)
OUTPUT = SECTION_DIR / "10_MASTER_draft_en.md"

TITLE = (
    "# Endpoint-specific reproducibility of bacterial and fungal community "
    "conclusions in a high-altitude sown grassland"
)

SECTIONS = [
    "08_abstract_draft_en.md",
    "01_intro_draft_en.md",
    "02_methods_draft_en.md",
    "03_results_draft_en.md",
    "04_discussion_draft_en.md",
    "05_conclusion_draft_en.md",
]


def strip_h1(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).lstrip()
    return text


def demote_headings(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("## "):
            lines.append("#" + line)
        elif line.startswith("# "):
            lines.append("#" + line)
        else:
            lines.append(line)
    return "\n".join(lines)


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text))


def endpoint_condition_table(path: Path) -> str:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    labels = {
        "family": ("Endpoint family", {
            "alpha": "Alpha",
            "beta": "Beta",
        }),
        "metric": ("Metric", {
            "Observed": "Observed",
            "Shannon": "Shannon",
            "Simpson": "Simpson",
            "Bray": "Bray-Curtis",
            "Aitchison": "Aitchison",
        }),
        "sample_set_variation": ("Sample-set variation", {
            "multiple": "Multiple",
            "single": "Single",
        }),
        "pipeline_depth": ("Pipeline depth", {
            "three_or_more": "Three or more",
            "two": "Two",
        }),
        "signal_margin": ("Worst endpoint P", {
            "max_p_lt_0.01": "<0.01",
            "max_p_0.01_0.05": "0.01–0.05",
            "max_p_0.05_0.10": "0.05–0.10",
            "max_p_0.10_0.20": "0.10–0.20",
            "max_p_ge_0.20": "≥0.20",
        }),
        "effect_retention": ("Effect retention", {
            "retention_ge_0.70": "≥0.70",
            "retention_0.40_0.70": "0.40–0.70",
            "retention_lt_0.40": "<0.40",
        }),
        "sample_size": ("Median sample size", {
            "n_ge_100": "≥100",
            "n_lt_100": "<100",
        }),
    }
    lines = [
        "| Condition type | Level | Claims | claimstab supported | "
        "claimstab support rate | Majority support rate |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for dimension, (display_dimension, levels) in labels.items():
        selected = [
            row for row in rows if row["dimension"] == dimension
        ]
        selected = sorted(
            selected,
            key=lambda row: list(levels).index(row["level"]),
        )
        for row in selected:
            lines.append(
                "| "
                + " | ".join(
                    [
                        display_dimension,
                        levels.get(row["level"], row["level"]),
                        row["n_claims"],
                        row["claimstab_supported"],
                        f"{float(row['claimstab_support_rate']):.3f}",
                        f"{float(row['majority_support_rate']):.3f}",
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "Note: These are descriptive summaries of 32 predefined claims across",
            "four public datasets. They are candidate stability conditions, not",
            "universal ecological laws. Effect retention is the",
            "smallest-to-largest absolute endpoint effect ratio. Small condition",
            "bins should not be interpreted as precise rates.",
        ]
    )
    return "\n".join(lines)


def majority_only_table(path: Path) -> str:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    labels = {
        "GP_mock_beta_Bray": (
            "GlobalPatterns: mock vs environment, Bray-Curtis",
            "Phylum crossed the threshold; effect retention was 0.35.",
        ),
        "GP_mock_beta_Aitchison": (
            "GlobalPatterns: mock vs environment, Aitchison",
            "Phylum reached P = 0.100; effect retention was 0.41.",
        ),
        "EN_alpha_Simpson": (
            "enterotype: sequencing technology, Simpson",
            "One filtering and sample-set combination crossed the threshold; reconstruction was partial.",
        ),
        "ATLAS_BMI_alpha_Observed": (
            "atlas1006: BMI, observed richness",
            "Phylum and some subsets were non-significant; effect retention was 0.05.",
        ),
        "ATLAS_BMI_alpha_Shannon": (
            "atlas1006: BMI, Shannon diversity",
            "Phylum crossed the threshold; effect retention was 0.05.",
        ),
    }
    lines = [
        "| Dataset and claim | Significant/testable | Reconstruction | P range | "
        "Effect retention | Strict call | Added explanation |",
        "| --- | ---: | --- | --- | ---: | --- | --- |",
    ]
    row_by_id = {row["claim_id"]: row for row in rows}
    order = [
        "GP_mock_beta_Bray",
        "GP_mock_beta_Aitchison",
        "EN_alpha_Simpson",
        "ATLAS_BMI_alpha_Observed",
        "ATLAS_BMI_alpha_Shannon",
    ]
    ordered_rows = [row_by_id[key] for key in order if key in row_by_id]
    ordered_rows.extend(
        row for row in rows if row["claim_id"] not in order
    )
    for row in ordered_rows:
        label, explanation = labels.get(
            row["claim_id"], (row["claim_id"], "")
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    (
                        f"{round(float(row['significant_fraction']) * int(row['n_testable']))}"
                        f"/{row['n_testable']}"
                    ),
                    row["reconstruction_status"],
                    f"{float(row['p_min']):.3g}–{float(row['p_max']):.3g}",
                    f"{float(row['effect_retention']):.2f}",
                    row["strict_call"],
                    explanation,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Note: These are the five observed-label claims supported by the",
            "majority rule but not graded strong or moderate by claimstab. The",
            "strict rule returned `mixed` for every case, so it also did not",
            "support them. Claimstab adds the reconstruction status, the",
            "threshold-crossing endpoint and the amount of effect attenuation.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    body_parts = [TITLE]
    for filename in SECTIONS:
        text = demote_headings(
            (SECTION_DIR / filename).read_text(encoding="utf-8")
        )
        body_parts.append(text.strip())

    figure = """
## Figure 1

![Pipeline sensitivity](</D:/CodexWork/QZ-mic/论文2-微生物/04_图表/14_分析可重复性/pipeline_endpoint_sensitivity.png>)

**Figure 1.** Pipeline sensitivity of microbial community conclusions.
(A) PERMANOVA effects across feature resolution and distance. (B) Alpha-diversity
tests for the original OTU and current ASV pipelines. (C) Sample-level
reconstruction of phylum composition. (D, E) Natural-reference distances for
ITS and 16S with 20,000-iteration bootstrap intervals. (F) Phylum-level
differential-abundance hits. Asterisks indicate P < 0.05.
""".strip()
    body_parts.append(figure)

    operational = strip_h1(
        (
            TABLE_DIR / "Table1_framework_operational_definitions.md"
        ).read_text(encoding="utf-8")
    )
    body_parts.append(
        "## Table 1. Operational definitions of the four framework components."
        f"\n\n{operational.strip()}"
    )

    for caption, filename in [
        (
            "Table 2. Data layers and reproducibility analysis levels.",
            "Table1_data_and_analysis_levels.md",
        ),
        (
            "Table 3. Sensitivity of diversity, composition, "
            "reference-distance, and differential-abundance endpoints.",
            "Table2_endpoint_sensitivity.md",
        ),
        (
            "Table 4. Stability of the original study's main claims.",
            "Table3_claim_stability.md",
        ),
    ]:
        table = strip_h1((TABLE_DIR / filename).read_text(encoding="utf-8"))
        body_parts.append(f"## {caption}\n\n{table.strip()}")

    table_5 = majority_only_table(MAJORITY_ONLY_TABLE)
    body_parts.append(
        "## Table 5. Claims supported by the majority rule but not graded "
        f"strong or moderate by claimstab.\n\n{table_5.strip()}"
    )

    figure_2 = """
## Figure 2

![Claim-stability framework](</D:/CodexWork/QZ-mic/论文2-微生物/04_图表/14_分析可重复性/claimstab_framework.png>)

**Figure 2.** Four-component framework for endpoint-specific assessment of claim
stability. The workflow distinguishes data reconstruction, dependence on
analytical choices, inference stability, and evidence grading. Automatically
assigned grades serve as audit aids, and domain-specific manual adjudication is
explicitly documented.
""".strip()
    body_parts.append(figure_2)

    figure_s1 = """
## Figure S1

![Alpha 18-sample sensitivity](</D:/CodexWork/QZ-mic/论文2-微生物/04_图表/14_分析可重复性/alpha_18sample_sensitivity.png>)

**Figure S1.** Sensitivity of alpha-diversity group comparisons to sample
inclusion. Circles represent results from the 15-sample primary analysis and
diamonds represent results from the 18-sample sensitivity analysis. Samples with
the unmapped original group code 23 were included as a separate group only in
the sensitivity analysis. The dashed line marks P = 0.05.
""".strip()
    body_parts.append(figure_s1)

    table_s1 = strip_h1(
        (
            TABLE_DIR / "TableS1_alpha_18sample_sensitivity.md"
        ).read_text(encoding="utf-8")
    )
    body_parts.append(f"## Table S1. Alpha-diversity sensitivity\n\n{table_s1.strip()}")

    table_s2 = strip_h1(
        (
            TABLE_DIR / "TableS2_globalpatterns_claim_stability.md"
        ).read_text(encoding="utf-8")
    )
    body_parts.append(
        f"## Table S2. GlobalPatterns external case\n\n{table_s2.strip()}"
    )

    table_s3 = strip_h1(
        (
            TABLE_DIR / "TableS3_multidataset_benchmark.md"
        ).read_text(encoding="utf-8")
    )
    body_parts.append(
        f"## Table S3. Multi-dataset public benchmark\n\n{table_s3.strip()}"
    )

    table_s4 = endpoint_condition_table(CONDITION_TABLE)
    body_parts.append(
        f"## Table S4. Cross-dataset endpoint and stability conditions\n\n{table_s4.strip()}"
    )

    figure_3 = """
## Figure 3

![Multi-dataset claim-stability benchmark](</D:/CodexWork/QZ-mic/论文2-微生物/04_图表/15_多数据集框架验证/multidataset_claim_stability.png>)

**Figure 3.** Multi-dataset claim-stability benchmark.
(A) Supported claims by dataset under the majority and claimstab rules; labels
show the total number of claims in each dataset. (B) Support rate by the maximum
endpoint P value within a claim. (C) Support rate by effect retention, defined
as the smallest-to-largest absolute endpoint effect ratio. Support under
claimstab means strong or moderate evidence. Bars are descriptive summaries of
a predefined endpoint grid; no uncertainty interval is assigned to these rates.
Both observed-label and permuted-label PERMANOVA used 999 within-analysis
permutations.
""".strip()
    body_parts.append(figure_3)

    references = strip_h1(
        (SECTION_DIR / "06_references_verified.md").read_text(encoding="utf-8")
    )
    references = references.split("## Verification status", 1)[0].strip()
    body_parts.append(f"# References\n\n{references.strip()}")

    declarations = """
# Declarations

**Data availability.** The QZ sequencing files and derived tables used in this
reanalysis are retained in the project archive. The `GlobalPatterns`,
`enterotype`, `soilrep`, and `atlas1006` datasets are distributed with the
`phyloseq` and `microbiome` R packages; their source studies and DOIs are listed
in the references. A public repository identifier and permanent archive DOI for
the project data must be added before submission.

**Code availability.** `claimstab` 0.3.0, its schemas, tests, command-line
interfaces, examples, and the four-dataset benchmark are included in the
analysis archive. The archived workflow records versioned R and Python
environments, fixed random seeds, input configurations, and commands from input
tables to figures and claim-stability matrices. A public repository identifier,
license, and archival DOI must be added before submission.

**Ethics statement.** No new human participants or animals were involved. The
study reanalyses soil microbial sequencing data from an existing field
experiment and publicly available, de-identified human gut microbiome datasets.

**Author contributions, funding, competing interests, and AI-use disclosure.**
To be completed by the author team before submission.
""".strip()
    body_parts.append(declarations)

    manuscript = "\n\n".join(body_parts).strip() + "\n"
    OUTPUT.write_text(manuscript, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    print(f"Body word count: {word_count(manuscript)}")


if __name__ == "__main__":
    main()
