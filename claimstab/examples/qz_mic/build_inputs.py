from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
PAPER_ROOT = PACKAGE_ROOT.parents[1]
RESULT_ROOT = PAPER_ROOT / "03_结果"
EXAMPLES = Path(__file__).resolve().parent

CLAIMS = [
    ("B_16S_Bray", "16S Bray-Curtis composition differs by treatment", "difference", "R16_phylum", ""),
    ("B_16S_Aitchison", "16S Aitchison composition differs by treatment", "difference", "R16_phylum", ""),
    ("B_ITS_Bray", "ITS Bray-Curtis composition differs by treatment", "difference", "RITS_phylum", ""),
    ("B_ITS_Aitchison", "ITS Aitchison composition differs by treatment", "difference", "RITS_phylum", ""),
    ("A_16S_Observed_effect", "16S Observed richness differs by treatment", "difference", "R16_alpha", ""),
    ("A_16S_Shannon_null", "16S Shannon diversity has no treatment difference", "null", "R16_alpha", ""),
    ("A_16S_Simpson_null", "16S Simpson diversity has no treatment difference", "null", "R16_alpha", ""),
    ("A_ITS_Observed_null", "ITS Observed richness has no treatment difference", "null", "RITS_alpha", ""),
    ("A_ITS_Shannon_null", "ITS Shannon diversity has no treatment difference", "null", "RITS_alpha", ""),
    ("A_ITS_Simpson_null", "ITS Simpson diversity has no treatment difference", "null", "RITS_alpha", ""),
    ("R_16S_AEFP", "AEFP is the closest artificial treatment in 16S", "ranking", "R16_phylum", "descriptive"),
    ("R_ITS_AEFP", "AEFP is the closest artificial treatment in ITS", "ranking", "RITS_phylum", "descriptive"),
    ("D_LEfSe", "The original LEfSe taxa can be reproduced", "not_verifiable", "R_LEfSe", "not_verifiable"),
    ("D_abs_abundance", "Absolute microbial abundance changes", "not_verifiable", "R_qPCR", "not_verifiable"),
]

RECONSTRUCTION = [
    ("R16_phylum", "16S", "phylum", "mean_common_bray", "0.0273", "<=0.10", "stable", "sample_level_old_vs_current_concordance.csv", "max=0.0346; mean_spearman=0.971"),
    ("RITS_phylum", "ITS", "phylum", "mean_common_bray", "0.0517", "<=0.10", "partial", "sample_level_old_vs_current_concordance.csv", "max=0.3067; one classification-sensitive sample"),
    ("R16_alpha", "16S", "alpha", "sample_rank_spearman", "0.589-0.889", "not thresholded", "partial", "alpha_pipeline_concordance.csv", "Observed and Shannon ranks moderately concordant"),
    ("RITS_alpha", "ITS", "alpha", "sample_rank_spearman", "0.659-0.975", "not thresholded", "partial", "alpha_pipeline_concordance.csv", "Observed ranks less concordant than Shannon/Simpson"),
    ("R_LEfSe", "16S+ITS", "DA", "input_availability", "", "required files present", "not_available", "材料完整性/materials_inventory.csv", "OTU count matrix and full LEfSe output absent"),
    ("R_qPCR", "16S+ITS", "absolute abundance", "matched Cq availability", "", "required files present", "not_available", "QZ_mic_master_crosswalk.xlsx", "No matched Cq, standard curve or copy number"),
]


def claim_id_for_alpha(domain: str, metric: str) -> str:
    if domain == "16S" and metric == "Observed":
        return "A_16S_Observed_effect"
    return {
        ("16S", "Shannon"): "A_16S_Shannon_null",
        ("16S", "Simpson"): "A_16S_Simpson_null",
        ("ITS", "Observed"): "A_ITS_Observed_null",
        ("ITS", "Shannon"): "A_ITS_Shannon_null",
        ("ITS", "Simpson"): "A_ITS_Simpson_null",
    }[(domain, metric)]


def claim_id_for_beta(domain: str, metric: str) -> str:
    metric_id = "Aitchison" if metric == "Aitchison" else "Bray"
    return f"B_{domain}_{metric_id}"


def write_rows(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    write_rows(
        EXAMPLES / "claims.csv",
        ["claim_id", "claim_text", "claim_type", "reconstruction_id", "manual_evidence_grade", "notes"],
        [
            {
                "claim_id": claim_id,
                "claim_text": text,
                "claim_type": claim_type,
                "reconstruction_id": reconstruction_id,
                "manual_evidence_grade": manual_grade,
                "notes": "",
            }
            for claim_id, text, claim_type, reconstruction_id, manual_grade in CLAIMS
        ],
    )
    write_rows(
        EXAMPLES / "reconstruction.csv",
        ["reconstruction_id", "domain", "layer", "metric", "value", "threshold", "status", "source", "notes"],
        [
            dict(
                zip(
                    ["reconstruction_id", "domain", "layer", "metric", "value", "threshold", "status", "source", "notes"],
                    row,
                )
            )
            for row in RECONSTRUCTION
        ],
    )

    endpoint_rows: list[dict[str, object]] = []
    endpoints = pd.read_csv(
        RESULT_ROOT / "14_分析可重复性" / "04_结论汇总" / "pipeline_endpoint_matrix.csv",
        encoding="utf-8-sig",
    )
    beta = endpoints.loc[
        endpoints["Analysis"].eq("Beta composition")
        & endpoints["Pipeline"].isin(
            ["original_phylum", "current_asv_phylum", "current_asv_level"]
        )
        & endpoints["Metric"].isin(["Bray-Curtis", "Aitchison"])
    ]
    for _, row in beta.iterrows():
        endpoint_rows.append(
            {
                "claim_id": claim_id_for_beta(row["Domain"], row["Metric"]),
                "domain": row["Domain"],
                "outcome": "beta_composition",
                "contrast": row["Metric"],
                "pipeline": row["Pipeline"],
                "sample_set": row["SampleSet"],
                "estimate": row["R2"],
                "p_value": row["P"],
                "direction": "not_applicable",
                "rank": "",
                "testable": "true",
                "source": "pipeline_endpoint_matrix.csv",
                "notes": "",
            }
        )

    alpha = pd.read_csv(
        RESULT_ROOT / "14_分析可重复性" / "07_18样品alpha敏感性" / "alpha_omnibus_15_vs_18.csv",
        encoding="utf-8-sig",
    )
    for _, row in alpha.iterrows():
        endpoint_rows.append(
            {
                "claim_id": claim_id_for_alpha(row["Domain"], row["Metric"]),
                "domain": row["Domain"],
                "outcome": "alpha_diversity",
                "contrast": row["Metric"],
                "pipeline": row["Pipeline"],
                "sample_set": row["SampleSet"],
                "estimate": row["WelchF"],
                "p_value": row["P"],
                "direction": "not_applicable",
                "rank": "",
                "testable": "true",
                "source": "alpha_omnibus_15_vs_18.csv",
                "notes": "",
            }
        )

    reference = pd.read_csv(
        RESULT_ROOT / "14_分析可重复性" / "02_多样性与参照" / "natural_reference_bootstrap.csv",
        encoding="utf-8-sig",
    )
    exact = pd.read_csv(
        RESULT_ROOT / "14_分析可重复性" / "02_多样性与参照" / "natural_reference_exact_permutation.csv",
        encoding="utf-8-sig",
    )
    for (domain, pipeline), group in reference.groupby(["Domain", "Pipeline"]):
        aefp = group.loc[group["Composition"].eq("AEFP")].iloc[0]
        ordered = group.sort_values("ObservedMeanDistance")["Composition"].tolist()
        rank = ordered.index("AEFP") + 1
        p_value = exact.loc[
            exact["Domain"].eq(domain)
            & exact["Pipeline"].eq(pipeline)
            & exact["Test"].str.startswith("Any artificial-treatment"),
            "RawExactP",
        ].iloc[0]
        endpoint_rows.append(
            {
                "claim_id": f"R_{domain}_AEFP",
                "domain": domain,
                "outcome": "natural_reference_rank",
                "contrast": "AEFP",
                "pipeline": pipeline,
                "sample_set": "primary",
                "estimate": aefp["ObservedMeanDistance"],
                "p_value": p_value,
                "direction": "not_applicable",
                "rank": rank,
                "testable": "true",
                "source": "natural_reference_*.csv",
                "notes": "",
            }
        )

    asv_reference = pd.read_csv(
        RESULT_ROOT / "06_稳定性与参照区间" / "bootstrap_group_distance.csv",
        encoding="utf-8-sig",
    )
    asv_exact = pd.read_csv(
        RESULT_ROOT / "06_稳定性与参照区间" / "exact_label_permutation.csv",
        encoding="utf-8-sig",
    )
    for domain, group in asv_reference.groupby("Domain"):
        aefp = group.loc[group["Composition"].eq("AEFP")].iloc[0]
        ordered = group.sort_values("ObservedMeanDistance")["Composition"].tolist()
        rank = ordered.index("AEFP") + 1
        p_value = asv_exact.loc[
            asv_exact["Domain"].eq(domain)
            & asv_exact["Test"].str.startswith("Any artificial-treatment"),
            "RawExactP",
        ].iloc[0]
        endpoint_rows.append(
            {
                "claim_id": f"R_{domain}_AEFP",
                "domain": domain,
                "outcome": "natural_reference_rank",
                "contrast": "AEFP",
                "pipeline": "current_asv_level",
                "sample_set": "primary",
                "estimate": aefp["ObservedMeanDistance"],
                "p_value": p_value,
                "direction": "not_applicable",
                "rank": rank,
                "testable": "true",
                "source": "06_稳定性与参照区间/*",
                "notes": "",
            }
        )

    for claim_id, domain, outcome in [
        ("D_LEfSe", "16S+ITS", "LEfSe reproducibility"),
        ("D_abs_abundance", "16S+ITS", "absolute abundance"),
    ]:
        endpoint_rows.append(
            {
                "claim_id": claim_id,
                "domain": domain,
                "outcome": outcome,
                "contrast": "not available",
                "pipeline": "not available",
                "sample_set": "not available",
                "estimate": "",
                "p_value": "",
                "direction": "not_applicable",
                "rank": "",
                "testable": "false",
                "source": "materials_inventory.csv",
                "notes": "Required inputs unavailable",
            }
        )

    write_rows(
        EXAMPLES / "endpoints.csv",
        [
            "claim_id",
            "domain",
            "outcome",
            "contrast",
            "pipeline",
            "sample_set",
            "estimate",
            "p_value",
            "direction",
            "rank",
            "testable",
            "source",
            "notes",
        ],
        endpoint_rows,
    )
    print(f"Wrote QZ example inputs to {EXAMPLES}")


if __name__ == "__main__":
    main()
