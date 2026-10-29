from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
REPRO = ROOT / "03_结果" / "14_分析可重复性"
ALPHA_SENS_DIR = REPRO / "07_18样品alpha敏感性"
EXTERNAL_DIR = (
    ROOT
    / "07_可复用框架"
    / "claimstab"
    / "examples"
    / "globalpatterns"
    / "output"
)
OUT_DIR = REPRO / "06_论文表格"


def md_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append(
            "| "
            + " | ".join("" if pd.isna(row[column]) else str(row[column]) for column in columns)
            + " |"
        )
    return "\n".join(lines)


def fmt_p(value: float) -> str:
    if pd.isna(value):
        return "NA"
    if value < 0.001:
        return "<0.001"
    return f"{value:.3f}"


def fmt_r2(value: float) -> str:
    return f"{value:.3f}"


def build_table1() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Layer": "16S phylum reconstruction",
                "Original input": "97% OTU phylum table",
                "Current input": "DADA2 ASV table aggregated to phylum",
                "Samples": "18",
                "Features": "33 original; 28 current",
                "Question addressed": "Can phylum composition be reconstructed?",
                "Main limitation": "Original OTU count matrix unavailable",
            },
            {
                "Layer": "ITS phylum reconstruction",
                "Original input": "97% OTU phylum table",
                "Current input": "DADA2 ASV table with UNITE v10.0",
                "Samples": "18",
                "Features": "12 original; 14 current",
                "Question addressed": "Can fungal phylum composition be reconstructed?",
                "Main limitation": "Classification depth differs; one As sample is strongly affected",
            },
            {
                "Layer": "Alpha diversity",
                "Original input": "Original OTU alpha table",
                "Current input": "ASV alpha after rarefaction",
                "Samples": "15 primary; 18 sensitivity",
                "Features": "Observed, Shannon, Simpson",
                "Question addressed": "Are sample ranks and group-level inferences stable?",
                "Main limitation": "Original rarefaction depth and software settings unknown",
            },
            {
                "Layer": "Beta composition",
                "Original input": "Original phylum table",
                "Current input": "Current phylum and ASV levels",
                "Samples": "15 primary; 18 sensitivity",
                "Features": "Bray-Curtis and Aitchison",
                "Question addressed": "How do feature resolution and distance change inference?",
                "Main limitation": "Original OTU-level distances cannot be recomputed",
            },
            {
                "Layer": "Natural-reference distance",
                "Original input": "Original phylum table and published figure",
                "Current input": "Current phylum and ASV levels",
                "Samples": "15 primary",
                "Features": "Bray distance to Natural centroid",
                "Question addressed": "Is the AEFP ranking stable and statistically supported?",
                "Main limitation": "Only three plot-level records per treatment",
            },
            {
                "Layer": "Differential abundance",
                "Original input": "Published LEfSe claims",
                "Current input": "ALDEx2 and ANCOM-BC2",
                "Samples": "15 primary",
                "Features": "Phylum level",
                "Question addressed": "Are taxon calls stable across methods and taxonomies?",
                "Main limitation": "Original LEfSe inputs and complete outputs unavailable",
            },
            {
                "Layer": "Absolute abundance",
                "Original input": "No usable Cq or copy-number results",
                "Current input": "Relative amplicon composition",
                "Samples": "NA",
                "Features": "NA",
                "Question addressed": "Can biomass or absolute abundance be reproduced?",
                "Main limitation": "No matched quantitative calibration",
            },
            {
                "Layer": "Network analysis",
                "Original input": "Correlation matrix workbooks",
                "Current input": "Estimability audit",
                "Samples": "3 per treatment",
                "Features": "50 matrix nodes",
                "Question addressed": "Is an interaction network reproducible?",
                "Main limitation": "Sample/node ratio 0.06; node selection and edge settings unavailable",
            },
        ]
    )


def build_table2() -> pd.DataFrame:
    alpha = pd.read_csv(REPRO / "02_多样性与参照" / "alpha_group_tests.csv")
    beta = pd.read_csv(REPRO / "02_多样性与参照" / "beta_pipeline_sensitivity.csv")
    reference = pd.read_csv(REPRO / "02_多样性与参照" / "natural_reference_bootstrap.csv")
    exact = pd.read_csv(
        REPRO / "02_多样性与参照" / "natural_reference_exact_permutation.csv"
    )
    da = pd.read_csv(REPRO / "03_差异丰度" / "phylum_DA_summary.csv")

    rows = []
    for domain in ("16S", "ITS"):
        for metric in ("Observed", "Shannon", "Simpson"):
            old = alpha.loc[
                alpha["Domain"].eq(domain)
                & alpha["Metric"].eq(metric)
                & alpha["Pipeline"].eq("OriginalOTU")
            ].iloc[0]
            new = alpha.loc[
                alpha["Domain"].eq(domain)
                & alpha["Metric"].eq(metric)
                & alpha["Pipeline"].eq("CurrentASV")
            ].iloc[0]
            stable = (float(old["P"]) < 0.05) == (float(new["P"]) < 0.05)
            rows.append(
                {
                    "Domain": domain,
                    "Endpoint": f"Alpha {metric}, Welch P",
                    "Original phylum/OTU": fmt_p(float(old["P"])),
                    "Current ASV phylum": "NA",
                    "Current ASV level": fmt_p(float(new["P"])),
                    "Stability judgement": (
                        "stable null" if stable and float(new["P"]) >= 0.05
                        else "stable support" if stable
                        else "inference changes"
                    ),
                }
            )

    for domain in ("16S", "ITS"):
        for metric in ("Bray-Curtis", "Aitchison"):
            old = beta.loc[
                beta["Domain"].eq(domain)
                & beta["SampleSet"].eq("primary")
                & beta["Metric"].eq(metric)
                & beta["Pipeline"].eq("original_phylum")
            ].iloc[0]
            current_phylum = beta.loc[
                beta["Domain"].eq(domain)
                & beta["SampleSet"].eq("primary")
                & beta["Metric"].eq(metric)
                & beta["Pipeline"].eq("current_asv_phylum")
            ].iloc[0]
            asv = pd.read_csv(
                ROOT / "03_结果" / "04_ASV综合分析" / f"beta_{domain}_primary.csv"
            )
            asv = asv.loc[asv["Metric"].eq(metric)].iloc[0]
            values = [float(old["R2"]), float(current_phylum["R2"]), float(asv["R2"])]
            p_values = [float(old["P"]), float(current_phylum["P"]), float(asv["P"])]
            significant = [value < 0.05 for value in p_values]
            stability = (
                "stable support" if all(significant)
                else "stable null" if not any(significant)
                else "resolution- or distance-dependent"
            )
            rows.append(
                {
                    "Domain": domain,
                    "Endpoint": f"Beta {metric}, R2 (P)",
                    "Original phylum/OTU": (
                        f"{fmt_r2(values[0])} ({fmt_p(p_values[0])})"
                    ),
                    "Current ASV phylum": (
                        f"{fmt_r2(values[1])} ({fmt_p(p_values[1])})"
                    ),
                    "Current ASV level": (
                        f"{fmt_r2(values[2])} ({fmt_p(p_values[2])})"
                    ),
                    "Stability judgement": stability,
                }
            )

    for domain in ("16S", "ITS"):
        pipeline_rows = []
        for pipeline in ("original_phylum", "current_asv_phylum"):
            group = reference.loc[
                reference["Domain"].eq(domain)
                & reference["Pipeline"].eq(pipeline)
            ].sort_values("ObservedMeanDistance")
            aefp_rank = list(group["Composition"]).index("AEFP") + 1
            p_value = exact.loc[
                exact["Domain"].eq(domain)
                & exact["Pipeline"].eq(pipeline)
                & exact["Test"].str.startswith("Any artificial-treatment"),
                "RawExactP",
            ].iloc[0]
            pipeline_rows.append(f"AEFP rank {aefp_rank}; exact P {fmt_p(float(p_value))}")

        asv_reference = pd.read_csv(
            ROOT / "03_结果" / "06_稳定性与参照区间" / "bootstrap_group_distance.csv"
        )
        asv_exact = pd.read_csv(
            ROOT / "03_结果" / "06_稳定性与参照区间" / "exact_label_permutation.csv"
        )
        asv_group = asv_reference.loc[asv_reference["Domain"].eq(domain)].sort_values(
            "ObservedMeanDistance"
        )
        asv_rank = list(asv_group["Composition"]).index("AEFP") + 1
        asv_p = asv_exact.loc[
            asv_exact["Domain"].eq(domain)
            & asv_exact["Test"].str.startswith("Any artificial-treatment"),
            "RawExactP",
        ].iloc[0]
        rows.append(
            {
                "Domain": domain,
                "Endpoint": "AEFP natural-reference ranking",
                "Original phylum/OTU": pipeline_rows[0],
                "Current ASV phylum": pipeline_rows[1],
                "Current ASV level": (
                    f"AEFP rank {asv_rank}; exact P {fmt_p(float(asv_p))}"
                ),
                "Stability judgement": (
                    "direction stable; ranking unconfirmed"
                    if domain == "ITS"
                    else "AEFP advantage absent"
                ),
            }
        )

    for domain in ("16S", "ITS"):
        old = da.loc[
            da["Domain"].eq(domain) & da["Pipeline"].eq("original_phylum")
        ]
        current = da.loc[
            da["Domain"].eq(domain) & da["Pipeline"].eq("current_asv_phylum")
        ]
        rows.append(
            {
                "Domain": domain,
                "Endpoint": "Phylum DA hits (ALDEx2/ANCOM-BC2/consensus)",
                "Original phylum/OTU": (
                    f"{int(old['ALDEx2Hits'].sum())}/"
                    f"{int(old['ANCOMBC2Hits'].sum())}/"
                    f"{int(old['ConsensusHits'].sum())}"
                ),
                "Current ASV phylum": (
                    f"{int(current['ALDEx2Hits'].sum())}/"
                    f"{int(current['ANCOMBC2Hits'].sum())}/"
                    f"{int(current['ConsensusHits'].sum())}"
                ),
                "Current ASV level": "Genus: 0 dual-tool consensus",
                "Stability judgement": "no stable consensus; candidates change",
            }
        )

    return pd.DataFrame(rows)


def build_table3() -> pd.DataFrame:
    claims = pd.read_csv(REPRO / "04_结论汇总" / "claim_stability_matrix.csv")
    translations = {
        "C01": "Sample identity and treatment mapping",
        "C02": "16S phylum composition can be reconstructed",
        "C03": "ITS phylum composition can be reconstructed",
        "C04": "Treatments change bacterial and fungal composition",
        "C05": "Shannon/Simpson show no consistent treatment difference",
        "C06": "AEFP has the highest microbial diversity",
        "C07": "AEFP is closest to the natural community",
        "C08": "As increases Actinobacteriota/Basidiomycota and decreases Acidobacteriota",
        "C09": "AFP and AEFP alter selected phylum proportions",
        "C10": "LEfSe identifies stable differential taxa",
        "C11": "Artificial grassland weakens microbial network interactions",
        "C12": "Microbial abundance or biomass changes",
        "C13": "Soil pH and phosphorus drive specific taxa",
        "C14": "Treatment inference is insensitive to the unassigned group 23",
    }
    output = pd.DataFrame(
        {
            "ID": claims["ClaimID"],
            "Original claim": claims["ClaimID"].map(translations),
            "Direction stable": claims["DirectionStable"],
            "Inference stable": claims["InferenceStable"],
            "Current judgement": claims["Verdict"],
            "Evidence grade": claims["EvidenceGrade"],
        }
    )
    return output


def build_table_s1() -> pd.DataFrame:
    frame = pd.read_csv(ALPHA_SENS_DIR / "alpha_omnibus_15_vs_18.csv")
    primary = frame.loc[frame["SampleSet"].eq("primary15"), [
        "Domain", "Pipeline", "Metric", "P", "Eta2", "DF_num", "DF_den"
    ]].rename(columns={
        "P": "P_primary15",
        "Eta2": "Eta2_primary15",
        "DF_num": "DF_num_primary15",
        "DF_den": "DF_den_primary15",
    })
    sensitivity = frame.loc[frame["SampleSet"].eq("sensitivity18"), [
        "Domain", "Pipeline", "Metric", "P", "Eta2", "DF_num", "DF_den"
    ]].rename(columns={
        "P": "P_sensitivity18",
        "Eta2": "Eta2_sensitivity18",
        "DF_num": "DF_num_sensitivity18",
        "DF_den": "DF_den_sensitivity18",
    })
    output = primary.merge(
        sensitivity,
        on=["Domain", "Pipeline", "Metric"],
        how="inner",
        validate="one_to_one",
    )
    output["DeltaP_18_minus_15"] = (
        output["P_sensitivity18"] - output["P_primary15"]
    )
    output["Same_threshold_decision"] = (
        (output["P_primary15"] < 0.05) == (output["P_sensitivity18"] < 0.05)
    )
    return output


def build_table_s2() -> pd.DataFrame:
    frame = pd.read_csv(
        EXTERNAL_DIR / "claim_stability_matrix.csv",
        encoding="utf-8-sig",
    )
    return frame[
        [
            "claim_id",
            "claim_text",
            "claim_type",
            "reconstruction_status",
            "analysis_dependency",
            "inference_stability",
            "evidence_grade",
            "rationale",
        ]
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tables = [
        (
            "Table1_data_and_analysis_levels",
            "Table 1. Data layers and reproducibility analysis levels.",
            build_table1(),
        ),
        (
            "Table2_endpoint_sensitivity",
            "Table 2. Sensitivity of diversity, composition, reference-distance, and differential-abundance endpoints to analysis choices.",
            build_table2(),
        ),
        (
            "Table3_claim_stability",
            "Table 3. Stability of the original study's main claims under reanalysis.",
            build_table3(),
        ),
        (
            "TableS1_alpha_18sample_sensitivity",
            "Table S1. Alpha-diversity group tests with 15 and 18 samples.",
            build_table_s1(),
        ),
        (
            "TableS2_globalpatterns_claim_stability",
            "Table S2. External application of claimstab to the public GlobalPatterns dataset.",
            build_table_s2(),
        ),
    ]
    for stem, caption, frame in tables:
        frame.to_csv(OUT_DIR / f"{stem}.csv", index=False, encoding="utf-8-sig")
        display = frame.copy()
        if stem == "TableS1_alpha_18sample_sensitivity":
            for column in ("P_primary15", "P_sensitivity18"):
                display[column] = display[column].map(fmt_p)
            for column in ("Eta2_primary15", "Eta2_sensitivity18"):
                display[column] = display[column].map(lambda x: f"{float(x):.3f}")
            display["DeltaP_18_minus_15"] = display[
                "DeltaP_18_minus_15"
            ].map(lambda x: f"{float(x):+.3f}")
            for column in (
                "DF_den_primary15",
                "DF_den_sensitivity18",
            ):
                display[column] = display[column].map(lambda x: f"{float(x):.2f}")
            display = display.rename(columns={
                "P_primary15": "Primary P (15)",
                "Eta2_primary15": "Primary η²",
                "P_sensitivity18": "Sensitivity P (18)",
                "Eta2_sensitivity18": "Sensitivity η²",
                "DeltaP_18_minus_15": "Delta P (18-15)",
                "Same_threshold_decision": "Same P<0.05 decision",
                "DF_num_primary15": "df1 primary",
                "DF_den_primary15": "df2 primary",
                "DF_num_sensitivity18": "df1 sensitivity",
                "DF_den_sensitivity18": "df2 sensitivity",
            })
        note = ""
        if stem == "Table2_endpoint_sensitivity":
            note = (
                "\n\nNote: Alpha rows show the 15-sample primary set. "
                "The 18-sample alpha sensitivity is reported in Table S1. "
                "All beta rows are labelled by sample set."
            )
        elif stem == "Table3_claim_stability":
            note = (
                "\n\nNote: The designation `cannot verify` indicates that "
                "required inputs, code, parameter settings, or independent "
                "measurements are unavailable. It should not be interpreted as "
                "evidence that the original claim is false."
            )
        elif stem == "TableS1_alpha_18sample_sensitivity":
            note = (
                "\n\nNote: Primary comparisons contain five groups with three "
                "samples each; sensitivity comparisons contain the same groups "
                "plus the three-record unmapped group code 23. df1 is the Welch "
                "numerator df and df2 is the Welch-Satterthwaite denominator df. "
                "Eta-squared is classical SS_between/SS_total and is descriptive. "
                "The final column compares only whether P crossed 0.05; it is not "
                "a full repeatability test or evidence that two groups are equivalent."
            )
        (OUT_DIR / f"{stem}.md").write_text(
            f"# {caption}\n\n{md_table(display)}{note}\n",
            encoding="utf-8",
        )
    print(f"Wrote {len(tables)} manuscript tables to {OUT_DIR}")


if __name__ == "__main__":
    main()
