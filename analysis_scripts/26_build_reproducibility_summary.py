from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
RESULT_ROOT = ROOT / "03_结果"
BASE_DIR = RESULT_ROOT / "14_分析可重复性" / "01_基础矩阵"
PIPELINE_DIR = RESULT_ROOT / "14_分析可重复性" / "02_多样性与参照"
DA_DIR = RESULT_ROOT / "14_分析可重复性" / "03_差异丰度"
ALPHA_SENS_DIR = RESULT_ROOT / "14_分析可重复性" / "07_18样品alpha敏感性"
ASV_DIR = RESULT_ROOT / "04_ASV综合分析"
STABILITY_DIR = RESULT_ROOT / "06_稳定性与参照区间"
NETWORK_DIR = RESULT_ROOT / "02_网络可估性"
OUT_DIR = RESULT_ROOT / "14_分析可重复性" / "04_结论汇总"


def fmt(value: float, digits: int = 3) -> str:
    if pd.isna(value):
        return "NA"
    if value == 0:
        return "0"
    if abs(value) < 0.001:
        return f"{value:.1e}"
    return f"{value:.{digits}f}"


def build_endpoint_matrix() -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    published = pd.read_csv(BASE_DIR / "original_published_permanova.csv")
    for _, row in published.iterrows():
        rows.append(
            {
                "Analysis": "Beta composition",
                "Domain": row["Domain"],
                "Pipeline": "original_published_summary",
                "SampleSet": "unclear",
                "Metric": "PERMANOVA",
                "Contrast": row["Characteristics"],
                "Statistic": row["F.Model"],
                "R2": row["R2"],
                "P": row["P.value"],
                "Classification": "published summary only",
            }
        )

    alpha = pd.read_csv(ALPHA_SENS_DIR / "alpha_omnibus_15_vs_18.csv")
    for _, row in alpha.iterrows():
        pipeline = (
            "original_otu"
            if row["Pipeline"] == "OriginalOTU"
            else "current_asv"
        )
        rows.append(
            {
                "Analysis": "Alpha diversity",
                "Domain": row["Domain"],
                "Pipeline": pipeline,
                "SampleSet": (
                    "primary"
                    if row["SampleSet"] == "primary15"
                    else "sensitivity18"
                ),
                "Metric": row["Metric"],
                "Contrast": "Omnibus",
                "Statistic": row["WelchF"],
                "R2": np.nan,
                "P": row["P"],
                "Classification": (
                    "supported" if row["P"] < 0.05 else "insufficient evidence"
                ),
            }
        )

    beta = pd.read_csv(PIPELINE_DIR / "beta_pipeline_sensitivity.csv")
    for _, row in beta.iterrows():
        rows.append(
            {
                "Analysis": "Beta composition",
                "Domain": row["Domain"],
                "Pipeline": row["Pipeline"],
                "SampleSet": row["SampleSet"],
                "Metric": row["Metric"],
                "Contrast": "Omnibus",
                "Statistic": row["F"],
                "R2": row["R2"],
                "P": row["P"],
                "Classification": (
                    "supported" if row["P"] < 0.05 else "insufficient evidence"
                ),
            }
        )

    for domain in ("16S", "ITS"):
        for sample_set, suffix in (("primary", "primary"), ("sensitivity18", "sensitivity")):
            asv_beta = pd.read_csv(ASV_DIR / f"beta_{domain}_{suffix}.csv")
            for _, row in asv_beta.iterrows():
                rows.append(
                    {
                        "Analysis": "Beta composition",
                        "Domain": domain,
                        "Pipeline": "current_asv_level",
                        "SampleSet": sample_set,
                        "Metric": row["Metric"],
                        "Contrast": "Omnibus",
                        "Statistic": row["F"],
                        "R2": row["R2"],
                        "P": row["P"],
                        "Classification": (
                            "supported"
                            if row["P"] < 0.05
                            else "insufficient evidence"
                        ),
                    }
                )

    reference = pd.read_csv(PIPELINE_DIR / "natural_reference_bootstrap.csv")
    exact = pd.read_csv(PIPELINE_DIR / "natural_reference_exact_permutation.csv")
    reference["Rank"] = reference.groupby(["Pipeline", "Domain"])[
        "ObservedMeanDistance"
    ].rank(method="min")
    for (pipeline, domain), group in reference.groupby(["Pipeline", "Domain"]):
        aefp = group.loc[group["Composition"].eq("AEFP")].iloc[0]
        range_p = exact.loc[
            exact["Pipeline"].eq(pipeline)
            & exact["Domain"].eq(domain)
            & exact["Test"].str.startswith("Any artificial-treatment"),
            "RawExactP",
        ].iloc[0]
        closest = group.sort_values("ObservedMeanDistance").iloc[0]["Composition"]
        rows.append(
            {
                "Analysis": "Natural reference",
                "Domain": domain,
                "Pipeline": pipeline,
                "SampleSet": "primary",
                "Metric": "Bray distance to Natural centroid",
                "Contrast": "AEFP",
                "Statistic": aefp["ObservedMeanDistance"],
                "R2": np.nan,
                "P": range_p,
                "Classification": (
                    f"AEFP rank={int(aefp['Rank'])}; closest={closest}; "
                    f"bootstrap closest={fmt(float(aefp['ProbabilityClosest']))}"
                ),
            }
        )

    asv_reference = pd.read_csv(STABILITY_DIR / "bootstrap_group_distance.csv")
    asv_exact = pd.read_csv(STABILITY_DIR / "exact_label_permutation.csv")
    asv_reference["Rank"] = asv_reference.groupby("Domain")[
        "ObservedMeanDistance"
    ].rank(method="min")
    for domain in ("16S", "ITS"):
        group = asv_reference.loc[asv_reference["Domain"].eq(domain)].copy()
        aefp = group.loc[group["Composition"].eq("AEFP")].iloc[0]
        range_p = asv_exact.loc[
            asv_exact["Domain"].eq(domain)
            & asv_exact["Test"].str.startswith("Any artificial-treatment"),
            "RawExactP",
        ].iloc[0]
        closest = group.sort_values("ObservedMeanDistance").iloc[0]["Composition"]
        rows.append(
            {
                "Analysis": "Natural reference",
                "Domain": domain,
                "Pipeline": "current_asv_level",
                "SampleSet": "primary",
                "Metric": "Bray distance to Natural centroid",
                "Contrast": "AEFP",
                "Statistic": aefp["ObservedMeanDistance"],
                "R2": np.nan,
                "P": range_p,
                "Classification": (
                    f"AEFP rank={int(aefp['Rank'])}; closest={closest}; "
                    f"bootstrap closest={fmt(float(aefp['ProbabilityClosest']))}"
                ),
            }
        )

    return pd.DataFrame(rows)


def build_claim_matrix() -> pd.DataFrame:
    sample_concordance = pd.read_csv(
        BASE_DIR / "sample_level_old_vs_current_concordance.csv"
    )
    phylum_correlations = pd.read_csv(
        BASE_DIR / "phylum_cross_sample_correlations.csv"
    )
    group_means = pd.read_csv(BASE_DIR / "group_phylum_mean_comparison.csv")
    alpha_tests = pd.read_csv(PIPELINE_DIR / "alpha_group_tests.csv")
    beta = pd.read_csv(PIPELINE_DIR / "beta_pipeline_sensitivity.csv")
    reference = pd.read_csv(PIPELINE_DIR / "natural_reference_bootstrap.csv")
    exact = pd.read_csv(
        PIPELINE_DIR / "natural_reference_exact_permutation.csv"
    )
    da = pd.read_csv(DA_DIR / "phylum_DA_summary.csv")
    network = pd.read_csv(NETWORK_DIR / "network_estimability.csv")

    sixteen_summary = sample_concordance.loc[
        sample_concordance["Domain"].eq("16S")
    ]
    its_summary = sample_concordance.loc[sample_concordance["Domain"].eq("ITS")]
    its_worst = its_summary.sort_values(
        "BrayOldVsCurrentAllUnion", ascending=False
    ).iloc[0]

    alpha_lookup = alpha_tests.set_index(["Domain", "Pipeline", "Metric"])["P"]
    beta_lookup = beta.set_index(
        ["Pipeline", "Domain", "SampleSet", "Metric"]
    )["P"]
    exact_lookup = exact.set_index(["Pipeline", "Domain", "Test"])["RawExactP"]
    da_consensus = int(da["ConsensusHits"].sum())
    da_aldex = int(da["ALDEx2Hits"].sum())
    da_ancom = int(da["ANCOMBC2Hits"].sum())

    def endpoint_p(pipeline: str, domain: str, sample_set: str, metric: str) -> float:
        return float(beta_lookup.loc[(pipeline, domain, sample_set, metric)])

    rows = [
        {
            "ClaimID": "C01",
            "OriginalClaim": "18个样品和六类测序组可对应到现场记录",
            "Testable": "yes",
            "PipelineResult": (
                "18/18 samples matched in both domains; raw group23 remains unassigned"
            ),
            "DirectionStable": "yes",
            "InferenceStable": "yes",
            "Verdict": "stable provenance",
            "EvidenceGrade": "strong within available records",
            "SourceFiles": "01_基础矩阵/sample_mapping_audit.csv",
        },
        {
            "ClaimID": "C02",
            "OriginalClaim": "原门水平组成可由原始FASTQ重新分析近似重建",
            "Testable": "yes",
            "PipelineResult": (
                f"16S mean common-taxa Bray={fmt(sixteen_summary['BrayOldVsCurrentCommon'].mean())}, "
                f"max={fmt(sixteen_summary['BrayOldVsCurrentCommon'].max())}, "
                f"mean Spearman={fmt(sixteen_summary['SpearmanAcrossPhyla'].mean())}"
            ),
            "DirectionStable": "yes",
            "InferenceStable": "yes",
            "Verdict": "strong phylum-level reconstruction",
            "EvidenceGrade": "strong",
            "SourceFiles": "01_基础矩阵/sample_level_old_vs_current_concordance.csv",
        },
        {
            "ClaimID": "C03",
            "OriginalClaim": "ITS门水平组成可由原分类结果和UNITE重分析稳定重建",
            "Testable": "yes",
            "PipelineResult": (
                f"mean common-taxa Bray={fmt(its_summary['BrayOldVsCurrentCommon'].mean())}, "
                f"max={fmt(its_summary['BrayOldVsCurrentCommon'].max())}; "
                f"largest all-taxa difference={its_worst['Sample']}"
            ),
            "DirectionStable": "partly",
            "InferenceStable": "partly",
            "Verdict": "mostly stable, but one sample and As Basidiomycota are classification-sensitive",
            "EvidenceGrade": "moderate",
            "SourceFiles": "01_基础矩阵/sample_level_old_vs_current_concordance.csv; group_phylum_mean_comparison.csv",
        },
        {
            "ClaimID": "C04",
            "OriginalClaim": "处理显著改变细菌和真菌群落组成",
            "Testable": "yes",
            "PipelineResult": (
                "ASV-level Bray P<0.001 for both domains; "
                f"16S phylum Bray primary P={fmt(endpoint_p('original_phylum','16S','primary','Bray-Curtis'))}/"
                f"{fmt(endpoint_p('current_asv_phylum','16S','primary','Bray-Curtis'))}; "
                f"ITS phylum Bray primary P={fmt(endpoint_p('original_phylum','ITS','primary','Bray-Curtis'))}/"
                f"{fmt(endpoint_p('current_asv_phylum','ITS','primary','Bray-Curtis'))}"
            ),
            "DirectionStable": "partly",
            "InferenceStable": "no",
            "Verdict": "composition effect is resolution- and distance-dependent",
            "EvidenceGrade": "strong at ASV level; weak at phylum Bray",
            "SourceFiles": "02_多样性与参照/beta_pipeline_sensitivity.csv; 04_ASV综合分析/beta_*.csv",
        },
        {
            "ClaimID": "C05",
            "OriginalClaim": "Shannon和Simpson总体无一致差异",
            "Testable": "yes",
            "PipelineResult": (
                "16S and ITS Shannon/Simpson are non-significant in the primary "
                "15-sample treatment set. In the 18-sample sensitivity set, 11/12 "
                "significance decisions are unchanged; only current-ASV ITS Simpson "
                "becomes P=0.044 after the Unassigned group is added"
            ),
            "DirectionStable": "yes",
            "InferenceStable": "yes in primary set; one unassigned-group exception",
            "Verdict": "stable null result for primary Shannon/Simpson comparisons",
            "EvidenceGrade": "strong in primary set; descriptive sensitivity",
            "SourceFiles": "02_多样性与参照/alpha_group_tests.csv; 07_18样品alpha敏感性/",
        },
        {
            "ClaimID": "C06",
            "OriginalClaim": "AEFP微生物多样性最高",
            "Testable": "yes",
            "PipelineResult": (
                "AEFP is numerically highest for ITS Shannon in both pipelines, "
                "but omnibus P remains >0.05; 16S Observed rank changes across pipelines"
            ),
            "DirectionStable": "partly",
            "InferenceStable": "no",
            "Verdict": "rank tendency only; no inferential support",
            "EvidenceGrade": "descriptive",
            "SourceFiles": "02_多样性与参照/alpha_group_means.csv; alpha_group_tests.csv",
        },
        {
            "ClaimID": "C07",
            "OriginalClaim": "AEFP群落最接近天然草地",
            "Testable": "yes",
            "PipelineResult": (
                "ITS AEFP is closest in original phylum, current phylum and current ASV; "
                "16S AEFP is not closest; exact range P for ITS="
                f"{fmt(exact_lookup.loc[('original_phylum','ITS','Any artificial-treatment difference (range)')])}/"
                f"{fmt(exact_lookup.loc[('current_asv_phylum','ITS','Any artificial-treatment difference (range)')])}"
            ),
            "DirectionStable": "yes for ITS; no for 16S",
            "InferenceStable": "no",
            "Verdict": "domain-specific descriptive tendency, not confirmed ranking",
            "EvidenceGrade": "descriptive",
            "SourceFiles": "02_多样性与参照/natural_reference_*.csv; 06_稳定性与参照区间/*",
        },
        {
            "ClaimID": "C08",
            "OriginalClaim": "As相对裸斑提高Actinobacteriota/Basidiomycota并降低Acidobacteriota",
            "Testable": "partly",
            "PipelineResult": (
                "16S Actinobacteriota and Acidobacteriota directions are consistent across old/current phylum; "
                "ITS As Basidiomycota changes from 13.06% to 25.05% after reclassification"
            ),
            "DirectionStable": "partly",
            "InferenceStable": "no",
            "Verdict": "bacterial directions descriptive-stable; fungal abundance is taxonomy-sensitive and no DA consensus",
            "EvidenceGrade": "descriptive",
            "SourceFiles": "01_基础矩阵/group_phylum_mean_comparison.csv; 03_差异丰度/phylum_DA_summary.csv",
        },
        {
            "ClaimID": "C09",
            "OriginalClaim": "AFP降低Mortierellomycota，AEFP改变Proteobacteria/Acidobacteriota",
            "Testable": "partly",
            "PipelineResult": (
                "Group means are broadly stable between old/current phylum tables, "
                "but no ALDEx2 hits and no dual-tool consensus in either domain"
            ),
            "DirectionStable": "yes descriptively",
            "InferenceStable": "no",
            "Verdict": "descriptive direction only; significance not reproducible",
            "EvidenceGrade": "descriptive",
            "SourceFiles": "01_基础矩阵/group_phylum_mean_comparison.csv; 03_差异丰度/phylum_DA_summary.csv",
        },
        {
            "ClaimID": "C10",
            "OriginalClaim": "LEfSe识别出稳定的差异类群",
            "Testable": "no",
            "PipelineResult": (
                f"LEfSe inputs/outputs unavailable; modern tools: ALDEx2 hits={da_aldex}, "
                f"ANCOM-BC2 hits={da_ancom}, consensus={da_consensus}"
            ),
            "DirectionStable": "cannot verify",
            "InferenceStable": "no",
            "Verdict": "original LEfSe result not computationally reproducible; modern phylum consensus is absent",
            "EvidenceGrade": "not verifiable / no consensus",
            "SourceFiles": "03_差异丰度/phylum_DA_summary.csv",
        },
        {
            "ClaimID": "C11",
            "OriginalClaim": "人工草地削弱微生物网络强相互作用且细菌受影响更大",
            "Testable": "no",
            "PipelineResult": (
                f"network inference={network['InferenceStatus'].iloc[0]}; "
                f"sample/node ratio={fmt(float(network['SampleNodeRatio'].iloc[0]))}"
            ),
            "DirectionStable": "cannot verify",
            "InferenceStable": "no",
            "Verdict": "not estimable and original network inputs are incomplete/duplicated",
            "EvidenceGrade": "not verifiable",
            "SourceFiles": "02_网络可估性/network_estimability.csv; network_matrix_audit.csv",
        },
        {
            "ClaimID": "C12",
            "OriginalClaim": "微生物丰度或微生物量发生变化",
            "Testable": "no",
            "PipelineResult": "No matched qPCR Cq, standard curve or copy number",
            "DirectionStable": "cannot verify",
            "InferenceStable": "no",
            "Verdict": "relative composition cannot establish absolute abundance",
            "EvidenceGrade": "not analyzable",
            "SourceFiles": "../../数据清单.csv; 00_ASV结果总表/key_results.csv",
        },
        {
            "ClaimID": "C13",
            "OriginalClaim": "pH、有效磷和总磷驱动特定微生物类群",
            "Testable": "no",
            "PipelineResult": "Soil measurements are treatment-level and confounded with site/history",
            "DirectionStable": "cannot verify",
            "InferenceStable": "no",
            "Verdict": "descriptive association only; causal mechanism not testable",
            "EvidenceGrade": "not analyzable causally",
            "SourceFiles": "10_土壤养分核查/; 13_与原文对比/README.md",
        },
        {
            "ClaimID": "C14",
            "OriginalClaim": "处理差异对未分配组23的纳入不敏感",
            "Testable": "yes",
            "PipelineResult": (
                "11/12 alpha significance decisions remain unchanged; current-ASV "
                "ITS Simpson changes from P=0.899 to 0.044 when Unassigned is added. "
                "ITS phylum Bray changes from 0.132 to 0.035 in the original phylum "
                "table and from 0.128 to 0.039 in the current phylum table"
            ),
            "DirectionStable": "yes",
            "InferenceStable": "no",
            "Verdict": (
                "the unassigned group changes a borderline alpha and phylum-level "
                "beta inference but not the high-resolution main contrast"
            ),
            "EvidenceGrade": "strong sensitivity evidence",
            "SourceFiles": "02_多样性与参照/beta_pipeline_sensitivity.csv; 07_18样品alpha敏感性/",
        },
    ]
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    endpoints = build_endpoint_matrix()
    endpoints.to_csv(
        OUT_DIR / "pipeline_endpoint_matrix.csv",
        index=False,
        encoding="utf-8-sig",
    )
    claims = build_claim_matrix()
    claims.to_csv(
        OUT_DIR / "claim_stability_matrix.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(f"Wrote {len(endpoints)} endpoint comparisons")
    print(f"Wrote {len(claims)} claim-stability judgements")


if __name__ == "__main__":
    main()
