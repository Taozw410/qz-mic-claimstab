from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
RESULT_DIR = ROOT / "03_结果" / "07_ITS_UNITE分类"
FIGURE_DIR = ROOT / "04_图表" / "07_ITS_UNITE分类"

TREATMENT_LABELS = {
    "T1": "As",
    "T6": "AFP",
    "T7": "AEFP",
    "T22": "BP",
    "T23": "Natural",
}
GROUP_ORDER = ["T1", "T6", "T7", "T22", "T23"]


def matrix_for_stacked_plot(
    summary: pd.DataFrame, rank: str, exclude_unclassified: bool
) -> tuple[pd.DataFrame, list[str]]:
    data = summary.copy()
    if exclude_unclassified:
        data = data.loc[~data[rank].str.startswith("Unclassified")]
    overall = (
        data.groupby(rank)["MeanRelativeAbundance"]
        .mean()
        .sort_values(ascending=False)
    )
    top_taxa = overall.head(8).index.tolist()
    matrix = (
        data.loc[data[rank].isin(top_taxa)]
        .pivot(index="Treatment", columns=rank, values="MeanRelativeAbundance")
        .reindex(GROUP_ORDER)
        .fillna(0)
        .reindex(columns=top_taxa)
    )
    other = 1 - matrix.sum(axis=1)
    matrix["Other"] = other.clip(lower=0)
    return matrix, top_taxa


def plot_stacked(
    axis,
    matrix: pd.DataFrame,
    title: str,
    ylabel: str,
) -> None:
    x = np.arange(len(matrix.index))
    bottom = np.zeros(len(matrix.index))
    palette = plt.get_cmap("tab20").colors
    for index, column in enumerate(matrix.columns):
        values = matrix[column].to_numpy()
        color = "#D9D9D9" if column == "Other" else palette[index % len(palette)]
        axis.bar(x, values, bottom=bottom, color=color, width=0.72, label=column)
        bottom += values
    axis.set_xticks(
        x,
        [TREATMENT_LABELS[group] for group in matrix.index],
    )
    axis.set_ylim(0, 1)
    axis.set_ylabel(ylabel)
    axis.set_title(title, fontsize=10)
    axis.grid(axis="y", color="#E5E5E5", linewidth=0.6)
    axis.set_axisbelow(True)
    for spine in ["top", "right"]:
        axis.spines[spine].set_visible(False)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    phylum = pd.read_csv(RESULT_DIR / "its_group_phylum_summary.csv")
    genus = pd.read_csv(RESULT_DIR / "its_group_genus_summary.csv")
    phylum_matrix, _ = matrix_for_stacked_plot(phylum, "Phylum", False)
    genus_matrix, _ = matrix_for_stacked_plot(genus, "Genus", True)

    figure, axes = plt.subplots(1, 2, figsize=(11, 9), constrained_layout=False)
    figure.subplots_adjust(
        left=0.08,
        right=0.98,
        top=0.90,
        bottom=0.22,
        wspace=0.26,
    )
    plot_stacked(
        axes[0],
        phylum_matrix,
        "Phylum composition",
        "Mean relative abundance",
    )
    plot_stacked(
        axes[1],
        genus_matrix,
        "Classified genus composition",
        "Mean relative abundance",
    )
    handles = []
    labels = []
    for axis in axes:
        current_handles, current_labels = axis.get_legend_handles_labels()
        for handle, label in zip(current_handles, current_labels):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    figure.legend(
        handles,
        labels,
        loc="lower center",
        ncol=4,
        frameon=False,
        fontsize=7,
        bbox_to_anchor=(0.5, 0.015),
    )
    figure.suptitle(
        "ITS fungal composition from two-run UNITE consensus taxonomy",
        fontsize=11,
    )
    figure.savefig(
        FIGURE_DIR / "its_taxonomy_composition.png",
        dpi=300,
        bbox_inches="tight",
        metadata={"Software": None},
    )
    plt.close(figure)


if __name__ == "__main__":
    main()
