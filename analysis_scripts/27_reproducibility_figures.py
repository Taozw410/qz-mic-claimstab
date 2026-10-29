from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42


ROOT = Path(__file__).resolve().parent.parent
RESULT = ROOT / "03_结果"
REPRO = RESULT / "14_分析可重复性"
FIGURE_DIR = ROOT / "04_图表" / "14_分析可重复性"

PIPELINE_LABELS = {
    "original_phylum": "Original\nphylum",
    "current_asv_phylum": "Current\nphylum",
    "current_asv_level": "Current\nASV",
}
PIPELINE_COLORS = {
    "original_phylum": "#7F7F7F",
    "current_asv_phylum": "#009E73",
    "current_asv_level": "#0072B2",
}
GROUP_COLORS = {
    "As": "#0072B2",
    "AFP": "#009E73",
    "AEFP": "#D55E00",
    "BP": "#E69F00",
}


def significance_mark(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def panel_beta(axis) -> None:
    frame = pd.read_csv(REPRO / "02_多样性与参照" / "beta_pipeline_sensitivity.csv")
    frame = frame.loc[
        frame["SampleSet"].eq("primary") & frame["Pipeline"].isin(
            ["original_phylum", "current_asv_phylum"]
        )
    ].copy()
    asv_rows = []
    for domain in ("16S", "ITS"):
        current = pd.read_csv(ROOT / "03_结果" / "04_ASV综合分析" / f"beta_{domain}_primary.csv")
        current["Pipeline"] = "current_asv_level"
        current["Domain"] = domain
        current["SampleSet"] = "primary"
        asv_rows.append(current)
    frame = pd.concat([frame, *asv_rows], ignore_index=True)

    comparisons = [
        ("16S", "Bray-Curtis", "16S Bray"),
        ("16S", "Aitchison", "16S AIT"),
        ("ITS", "Bray-Curtis", "ITS Bray"),
        ("ITS", "Aitchison", "ITS AIT"),
    ]
    x = np.arange(len(comparisons))
    width = 0.25
    pipelines = ["original_phylum", "current_asv_phylum", "current_asv_level"]
    for pipeline_index, pipeline in enumerate(pipelines):
        values = []
        errors = []
        for domain, metric, _ in comparisons:
            row = frame.loc[
                frame["Domain"].eq(domain)
                & frame["Metric"].eq(metric)
                & frame["Pipeline"].eq(pipeline)
            ].iloc[0]
            values.append(float(row["R2"]))
            errors.append(row["P"])
        positions = x + (pipeline_index - 1) * width
        axis.bar(
            positions,
            values,
            width=width,
            color=PIPELINE_COLORS[pipeline],
            label=PIPELINE_LABELS[pipeline].replace("\n", " "),
        )
        for position, value, p_value in zip(positions, values, errors):
            axis.text(
                position,
                value + 0.015,
                significance_mark(float(p_value)),
                ha="center",
                va="bottom",
                fontsize=7,
            )
    axis.set_xticks(x, [label for _, _, label in comparisons])
    axis.set_ylabel("PERMANOVA R²")
    axis.set_ylim(0, 0.65)
    axis.set_title("A  Community structure sensitivity", loc="left", fontweight="bold")
    axis.legend(frameon=False, fontsize=7, ncol=3, loc="upper left")
    axis.grid(axis="y", color="#E6E6E6", linewidth=0.6)
    axis.set_axisbelow(True)


def panel_alpha(axis) -> None:
    frame = pd.read_csv(REPRO / "02_多样性与参照" / "alpha_group_tests.csv")
    frame["DisplayPipeline"] = frame["Pipeline"].map(
        {"OriginalOTU": "original_phylum", "CurrentASV": "current_asv_level"}
    )
    metrics = ["Observed", "Shannon", "Simpson"]
    x = np.arange(len(metrics))
    width = 0.2
    for domain_index, domain in enumerate(("16S", "ITS")):
        for pipeline_index, pipeline in enumerate(("original_phylum", "current_asv_level")):
            values = []
            pvalues = []
            for metric in metrics:
                row = frame.loc[
                    frame["Domain"].eq(domain)
                    & frame["Metric"].eq(metric)
                    & frame["DisplayPipeline"].eq(pipeline)
                ].iloc[0]
                values.append(min(-np.log10(float(row["P"])), 3))
                pvalues.append(float(row["P"]))
            offset = (domain_index * 2 + pipeline_index - 1.5) * width
            positions = x + offset
            axis.bar(
                positions,
                values,
                width=width * 0.92,
                color=PIPELINE_COLORS[pipeline],
                alpha=1.0 if domain == "16S" else 0.58,
            )
            for position, value, p_value in zip(positions, values, pvalues):
                axis.text(
                    position,
                    value + 0.05,
                    significance_mark(p_value),
                    ha="center",
                    va="bottom",
                    fontsize=6.5,
                )
    axis.axhline(-np.log10(0.05), color="#B2182B", linestyle="--", linewidth=0.8)
    axis.set_xticks(x, metrics)
    axis.set_ylabel("−log10(P), capped at 3")
    axis.set_ylim(0, 3.35)
    axis.set_title("B  Alpha-diversity sensitivity", loc="left", fontweight="bold")
    axis.text(
        2.35,
        -np.log10(0.05) + 0.06,
        "P=0.05",
        color="#B2182B",
        fontsize=6.5,
        ha="right",
    )
    axis.text(0.02, 0.97, "left/dark=16S, right/light=ITS",
              transform=axis.transAxes, va="top", fontsize=6.5)
    axis.grid(axis="y", color="#E6E6E6", linewidth=0.6)
    axis.set_axisbelow(True)


def panel_concordance(axis) -> None:
    frame = pd.read_csv(
        REPRO / "01_基础矩阵" / "sample_level_old_vs_current_concordance.csv"
    )
    metrics = [
        ("BrayOldVsCurrentCommon", "Common phyla\nBray"),
        ("BrayOldVsCurrentAllUnion", "All phyla\nBray"),
    ]
    positions = []
    labels = []
    colors = []
    data = []
    current = 1
    for domain, domain_color in (("16S", "#0072B2"), ("ITS", "#D55E00")):
        for column, label in metrics:
            data.append(frame.loc[frame["Domain"].eq(domain), column].to_numpy())
            positions.append(current)
            labels.append(f"{domain}\n{label}")
            colors.append(domain_color)
            current += 1
    boxes = axis.boxplot(
        data,
        positions=positions,
        widths=0.65,
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "#222222", "linewidth": 1},
    )
    for patch, color in zip(boxes["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.35)
    rng = np.random.default_rng(20261023)
    for position, values, color in zip(positions, data, colors):
        jitter = rng.uniform(-0.1, 0.1, size=len(values))
        axis.scatter(
            position + jitter,
            values,
            s=16,
            color=color,
            alpha=0.8,
            linewidths=0,
        )
    axis.set_xticks(positions, labels, fontsize=7)
    axis.set_ylabel("Dissimilarity between pipelines")
    axis.set_ylim(0, 0.4)
    axis.set_title("C  Sample-level phylum reconstruction", loc="left", fontweight="bold")
    axis.grid(axis="y", color="#E6E6E6", linewidth=0.6)
    axis.set_axisbelow(True)


def reference_frame(domain: str) -> pd.DataFrame:
    frame = pd.read_csv(REPRO / "02_多样性与参照" / "natural_reference_bootstrap.csv")
    frame = frame.loc[
        frame["Domain"].eq(domain) & frame["Composition"].isin(list(GROUP_COLORS))
    ].copy()
    current = pd.read_csv(RESULT / "06_稳定性与参照区间" / "bootstrap_group_distance.csv")
    current = current.loc[
        current["Domain"].eq(domain) & current["Composition"].isin(list(GROUP_COLORS))
    ].copy()
    current["Pipeline"] = "current_asv_level"
    return pd.concat([frame, current], ignore_index=True)


def panel_reference(axis, domain: str, panel_letter: str) -> None:
    frame = reference_frame(domain)
    pipelines = ["original_phylum", "current_asv_phylum", "current_asv_level"]
    groups = list(GROUP_COLORS)
    x = np.arange(len(groups))
    width = 0.24
    for pipeline_index, pipeline in enumerate(pipelines):
        subset = frame.loc[frame["Pipeline"].eq(pipeline)].set_index("Composition").loc[groups]
        positions = x + (pipeline_index - 1) * width
        values = subset["ObservedMeanDistance"].to_numpy(dtype=float)
        lower = values - subset["CI2.5"].to_numpy(dtype=float)
        upper = subset["CI97.5"].to_numpy(dtype=float) - values
        axis.errorbar(
            positions,
            values,
            yerr=np.vstack([lower, upper]),
            fmt="o",
            markersize=5,
            capsize=2,
            linewidth=0.8,
            color=PIPELINE_COLORS[pipeline],
            label=PIPELINE_LABELS[pipeline].replace("\n", " "),
        )
    axis.set_xticks(x, groups)
    axis.set_ylabel("Bray distance to natural centroid")
    axis.set_title(
        f"{panel_letter}  {domain} natural-reference ranking",
        loc="left",
        fontweight="bold",
    )
    axis.legend(frameon=False, fontsize=6.5, ncol=3, loc="upper left")
    axis.grid(axis="y", color="#E6E6E6", linewidth=0.6)
    axis.set_axisbelow(True)


def panel_da(axis) -> None:
    frame = pd.read_csv(REPRO / "03_差异丰度" / "phylum_DA_summary.csv")
    frame["Label"] = frame["Pipeline"].map(PIPELINE_LABELS).str.replace("\n", " ") + "\n" + frame["Domain"]
    summary = (
        frame.groupby(["Pipeline", "Domain"], as_index=False)[
            ["ALDEx2Hits", "ANCOMBC2Hits", "ConsensusHits"]
        ]
        .sum()
    )
    labels = []
    aldex = []
    ancom = []
    consensus = []
    for _, row in summary.iterrows():
        labels.append(f"{PIPELINE_LABELS[row['Pipeline']].replace(chr(10), ' ')}\n{row['Domain']}")
        aldex.append(row["ALDEx2Hits"])
        ancom.append(row["ANCOMBC2Hits"])
        consensus.append(row["ConsensusHits"])
    x = np.arange(len(labels))
    axis.bar(x - 0.18, aldex, width=0.34, color="#0072B2", label="ALDEx2")
    axis.bar(x + 0.18, ancom, width=0.34, color="#D55E00", label="ANCOM-BC2")
    axis.scatter(x, consensus, marker="D", color="black", s=20, label="Consensus")
    axis.set_xticks(x, labels, fontsize=6.5)
    axis.set_ylabel("Total candidate hits across 4 contrasts")
    axis.set_title("F  Phylum-level differential abundance", loc="left", fontweight="bold")
    axis.legend(frameon=False, fontsize=7, ncol=3)
    axis.grid(axis="y", color="#E6E6E6", linewidth=0.6)
    axis.set_axisbelow(True)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(3, 2, figsize=(11.5, 10.2), constrained_layout=True)
    panel_beta(axes[0, 0])
    panel_alpha(axes[0, 1])
    panel_concordance(axes[1, 0])
    panel_reference(axes[1, 1], "ITS", "D")
    panel_reference(axes[2, 0], "16S", "E")
    panel_da(axes[2, 1])
    for axis in axes.ravel():
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)
    figure.suptitle(
        "Pipeline sensitivity of microbial community conclusions",
        fontsize=13,
        fontweight="bold",
    )
    figure.savefig(
        FIGURE_DIR / "pipeline_endpoint_sensitivity.png",
        dpi=300,
        bbox_inches="tight",
        metadata={"Software": None},
    )
    figure.savefig(
        FIGURE_DIR / "pipeline_endpoint_sensitivity.pdf",
        bbox_inches="tight",
        metadata={"Creator": None, "Producer": None},
    )
    plt.close(figure)
    print(f"Wrote figure to {FIGURE_DIR}")


if __name__ == "__main__":
    main()
