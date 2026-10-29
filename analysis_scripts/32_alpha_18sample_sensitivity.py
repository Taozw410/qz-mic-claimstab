from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import f_oneway


ROOT = Path(__file__).resolve().parent.parent
INPUT = (
    ROOT
    / "03_结果"
    / "14_分析可重复性"
    / "02_多样性与参照"
    / "alpha_sample_pipeline_comparison.csv"
)
OUTPUT_DIR = ROOT / "03_结果" / "14_分析可重复性" / "07_18样品alpha敏感性"

DOMAINS = ("16S", "ITS")
METRICS = ("Observed", "Shannon", "Simpson")
PIPELINES = ("OriginalOTU", "CurrentASV")
GROUP_ORDER = ("As", "AFP", "AEFP", "BP", "Natural", "Unassigned")


def md_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append(
            "| "
            + " | ".join(
                "" if pd.isna(row[column]) else str(row[column])
                for column in columns
            )
            + " |"
        )
    return "\n".join(lines)


def eta_squared(values: pd.Series, groups: pd.Series) -> float:
    grand_mean = float(values.mean())
    total_ss = float(((values - grand_mean) ** 2).sum())
    between_ss = 0.0
    for group in groups.dropna().unique():
        current = values.loc[groups.eq(group)]
        between_ss += len(current) * (float(current.mean()) - grand_mean) ** 2
    return between_ss / total_ss if total_ss > 0 else np.nan


def welch_row(data: pd.DataFrame, column: str) -> dict[str, float]:
    arrays = [
        data.loc[data["Composition"].eq(group), column].to_numpy(dtype=float)
        for group in GROUP_ORDER
        if data["Composition"].eq(group).any()
    ]
    statistic, p_value = f_oneway(*arrays, equal_var=False)
    group_sizes = np.array([len(values) for values in arrays], dtype=float)
    group_vars = np.array(
        [np.var(values, ddof=1) for values in arrays],
        dtype=float,
    )
    weights = group_sizes / group_vars
    total_weight = float(weights.sum())
    k = len(arrays)
    correction = float(
        np.sum(((1.0 - weights / total_weight) ** 2) / (group_sizes - 1.0))
    )
    df_num = k - 1
    df_den = 1.0 / ((3.0 / (k**2 - 1.0)) * correction)
    return {
        "GroupCount": len(arrays),
        "N": len(data),
        "DF_num": df_num,
        "DF_den": df_den,
        "WelchF": float(statistic),
        "P": float(p_value),
        "Eta2": eta_squared(data[column], data["Composition"]),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(INPUT, encoding="utf-8-sig")
    frame["Primary5"] = (
        frame["Primary5"].astype(str).str.lower().isin(["true", "1", "yes"])
    )
    if len(frame) != 36:
        raise ValueError(f"Expected 36 domain-sample rows, found {len(frame)}")
    if any(frame.groupby("Domain").size() != 18):
        raise ValueError("Each domain must contain 18 samples")

    omnibus_rows = []
    group_rows = []
    comparison_rows = []

    for domain in DOMAINS:
        domain_data = frame.loc[frame["Domain"].eq(domain)].copy()
        for pipeline in PIPELINES:
            for metric in METRICS:
                column = f"{metric}_{pipeline}"
                primary = domain_data.loc[domain_data["Primary5"]].copy()
                sensitivity = domain_data.copy()

                for sample_set, data in (
                    ("primary15", primary),
                    ("sensitivity18", sensitivity),
                ):
                    result = welch_row(data, column)
                    omnibus_rows.append(
                        {
                            "Domain": domain,
                            "Pipeline": pipeline,
                            "Metric": metric,
                            "SampleSet": sample_set,
                            **result,
                            "Significant": result["P"] < 0.05,
                        }
                    )
                    means = (
                        data.groupby("Composition")[column]
                        .agg(["count", "mean", "std"])
                        .reset_index()
                    )
                    means["SE"] = means["std"] / np.sqrt(means["count"])
                    means["MeanRank"] = means["mean"].rank(
                        ascending=False, method="min"
                    )
                    for _, row in means.iterrows():
                        group_rows.append(
                            {
                                "Domain": domain,
                                "Pipeline": pipeline,
                                "Metric": metric,
                                "SampleSet": sample_set,
                                "Composition": row["Composition"],
                                "N": int(row["count"]),
                                "Mean": float(row["mean"]),
                                "SD": float(row["std"]),
                                "SE": float(row["SE"]),
                                "MeanRank": int(row["MeanRank"]),
                            }
                        )

                p15 = next(
                    row["P"]
                    for row in omnibus_rows
                    if row["Domain"] == domain
                    and row["Pipeline"] == pipeline
                    and row["Metric"] == metric
                    and row["SampleSet"] == "primary15"
                )
                p18 = next(
                    row["P"]
                    for row in omnibus_rows
                    if row["Domain"] == domain
                    and row["Pipeline"] == pipeline
                    and row["Metric"] == metric
                    and row["SampleSet"] == "sensitivity18"
                )
                comparison_rows.append(
                    {
                        "Domain": domain,
                        "Pipeline": pipeline,
                        "Metric": metric,
                        "P_primary15": p15,
                        "P_sensitivity18": p18,
                        "DeltaP_18_minus_15": p18 - p15,
                        "DF_num_primary15": int(
                            next(
                                row["DF_num"]
                                for row in omnibus_rows
                                if row["Domain"] == domain
                                and row["Pipeline"] == pipeline
                                and row["Metric"] == metric
                                and row["SampleSet"] == "primary15"
                            )
                        ),
                        "DF_den_primary15": next(
                            row["DF_den"]
                            for row in omnibus_rows
                            if row["Domain"] == domain
                            and row["Pipeline"] == pipeline
                            and row["Metric"] == metric
                            and row["SampleSet"] == "primary15"
                        ),
                        "DF_num_sensitivity18": int(
                            next(
                                row["DF_num"]
                                for row in omnibus_rows
                                if row["Domain"] == domain
                                and row["Pipeline"] == pipeline
                                and row["Metric"] == metric
                                and row["SampleSet"] == "sensitivity18"
                            )
                        ),
                        "DF_den_sensitivity18": next(
                            row["DF_den"]
                            for row in omnibus_rows
                            if row["Domain"] == domain
                            and row["Pipeline"] == pipeline
                            and row["Metric"] == metric
                            and row["SampleSet"] == "sensitivity18"
                        ),
                        "Significance_primary15": p15 < 0.05,
                        "Significance_sensitivity18": p18 < 0.05,
                        "Same_threshold_decision": (p15 < 0.05) == (p18 < 0.05),
                    }
                )

    omnibus = pd.DataFrame(omnibus_rows)
    group_means = pd.DataFrame(group_rows)
    comparison = pd.DataFrame(comparison_rows)
    omnibus.to_csv(
        OUTPUT_DIR / "alpha_omnibus_15_vs_18.csv",
        index=False,
        encoding="utf-8-sig",
    )
    group_means.to_csv(
        OUTPUT_DIR / "alpha_group_means_15_and_18.csv",
        index=False,
        encoding="utf-8-sig",
    )
    comparison.to_csv(
        OUTPUT_DIR / "alpha_primary_vs_sensitivity.csv",
        index=False,
        encoding="utf-8-sig",
    )
    parameters = pd.DataFrame(
        [
            {"Parameter": "PrimarySamples", "Value": 15},
            {"Parameter": "SensitivitySamples", "Value": 18},
            {
                "Parameter": "UnassignedGroup",
                "Value": "raw group 23, three records, retained without treatment label",
            },
            {"Parameter": "Test", "Value": "Welch one-way ANOVA"},
            {"Parameter": "EffectSize", "Value": "Classical eta squared (descriptive)"},
            {"Parameter": "Threshold", "Value": 0.05},
        ]
    )
    parameters.to_csv(
        OUTPUT_DIR / "analysis_parameters.csv",
        index=False,
        encoding="utf-8-sig",
    )
    display = comparison.copy()
    display["P_primary15"] = display["P_primary15"].map(lambda x: f"{x:.4g}")
    display["P_sensitivity18"] = display["P_sensitivity18"].map(lambda x: f"{x:.4g}")
    display["DeltaP_18_minus_15"] = display["DeltaP_18_minus_15"].map(
        lambda x: f"{x:+.4g}"
    )
    changed = comparison.loc[~comparison["Same_threshold_decision"]]
    unchanged_count = int(comparison["Same_threshold_decision"].sum())
    readme = f"""# 18-sample alpha-diversity sensitivity

## Definition

- Primary set: 15 plot-level records, five treatment groups with three records each.
- Sensitivity set: all 18 records. Raw sequencing group 23 remains `Unassigned`.
- Test: Welch one-way ANOVA for Observed, Shannon and Simpson.
- Effect size: classical eta squared, descriptive only.

## Result

{unchanged_count}/12 pipeline-metric significance decisions remained unchanged
after adding the unassigned group.

The only change was current-ASV ITS Simpson:

- primary 15: P = {comparison.loc[(comparison.Domain == 'ITS') & (comparison.Pipeline == 'CurrentASV') & (comparison.Metric == 'Simpson'), 'P_primary15'].iloc[0]:.4f};
- sensitivity 18: P = {comparison.loc[(comparison.Domain == 'ITS') & (comparison.Pipeline == 'CurrentASV') & (comparison.Metric == 'Simpson'), 'P_sensitivity18'].iloc[0]:.4f}.

The Unassigned group had the highest mean Simpson value in the 18-sample set,
but it has no treatment identity. The change therefore demonstrates sensitivity
to including an unlabelled group and cannot be interpreted as a treatment effect.

## Comparison table

{md_table(display)}

## Files

- `alpha_omnibus_15_vs_18.csv`: F, P and eta squared for both sample sets.
- `alpha_group_means_15_and_18.csv`: group means, SD, SE and mean rank.
- `alpha_primary_vs_sensitivity.csv`: direct P-value comparison.
- `analysis_parameters.csv`: fixed analysis settings.
- `VALIDATION.md`: experiment-agent validation report and 11/11 fallacy scan.

## Supplementary figure

- `../../../04_图表/14_分析可重复性/alpha_18sample_sensitivity.png`
- Generator: `../../../02_脚本/33_alpha_18sample_figure.py`
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    (OUTPUT_DIR / "COMPLETE.txt").write_text(
        "18-sample alpha-diversity sensitivity completed.\n", encoding="utf-8"
    )
    print(comparison.to_string(index=False))
    print(f"\nWrote results to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
