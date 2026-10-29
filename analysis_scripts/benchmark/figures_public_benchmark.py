from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import ScaledTranslation
import numpy as np


SKILL_SCRIPTS = Path(
    r"C:\Users\hthome\.codex\skills\nature-figure\scripts"
)
sys.path.insert(0, str(SKILL_SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment


ROOT = Path(
    r"D:\CodexWork\QZ-mic\论文2-微生物\03_结果\15_多数据集框架验证"
)
SUMMARY = ROOT / "汇总"
OUTPUT = Path(
    r"D:\CodexWork\QZ-mic\论文2-微生物\04_图表\15_多数据集框架验证"
)
OUTPUT.mkdir(parents=True, exist_ok=True)

BLUE = "#0F4D92"
NEUTRAL = "#A8A8A8"
NEUTRAL_DARK = "#4D4D4D"
TEAL = "#42949E"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def add_panel_label(ax, label: str) -> None:
    offset = ScaledTranslation(-4 / 72, 3 / 72, ax.figure.dpi_scale_trans)
    ax.text(
        0,
        1,
        label,
        transform=ax.transAxes + offset,
        fontsize=8,
        fontweight="bold",
        ha="left",
        va="bottom",
    )


def style_axis(ax, title: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=7.5, fontweight="bold", pad=5)
    ax.set_ylabel(ylabel, fontsize=7)
    ax.tick_params(axis="both", labelsize=6.5, width=0.7, length=2.5)
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_linewidth(0.7)
    ax.spines["bottom"].set_linewidth(0.7)


def main() -> int:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.linewidth": 0.7,
            "legend.frameon": False,
        }
    )

    comparison = read_csv(
        SUMMARY / "main_comparison" / "framework_comparison.csv"
    )
    condition_rows = read_csv(SUMMARY / "condition_summary.csv")

    dataset_order = [
        "GlobalPatterns",
        "enterotype",
        "soilrep",
        "atlas1006",
    ]
    majority = Counter()
    claimstab = Counter()
    totals = Counter()
    for row in comparison:
        dataset = row["dataset"]
        totals[dataset] += 1
        if row["majority_call"] == "supported":
            majority[dataset] += 1
        if row["claimstab_supported"].lower() == "true":
            claimstab[dataset] += 1

    comparison_data = np.array(
        [
            [majority[dataset], claimstab[dataset], totals[dataset]]
            for dataset in dataset_order
        ]
    )

    signal_order = [
        "max_p_lt_0.01",
        "max_p_0.01_0.05",
        "max_p_0.05_0.10",
        "max_p_0.10_0.20",
        "max_p_ge_0.20",
    ]
    signal_labels = ["<0.01", "0.01–0.05", "0.05–0.10", "0.10–0.20", "≥0.20"]
    signal_lookup = {
        row["level"]: row
        for row in condition_rows
        if row["dimension"] == "signal_margin"
    }
    signal_data = np.array(
        [
            [
                float(signal_lookup[level]["majority_support_rate"]),
                float(signal_lookup[level]["claimstab_support_rate"]),
                int(signal_lookup[level]["n_claims"]),
            ]
            for level in signal_order
        ]
    )

    retention_order = [
        "retention_ge_0.70",
        "retention_0.40_0.70",
        "retention_lt_0.40",
    ]
    retention_labels = ["≥0.70", "0.40–0.70", "<0.40"]
    retention_lookup = {
        row["level"]: row
        for row in condition_rows
        if row["dimension"] == "effect_retention"
    }
    retention_data = np.array(
        [
            [
                float(retention_lookup[level]["majority_support_rate"]),
                float(retention_lookup[level]["claimstab_support_rate"]),
                int(retention_lookup[level]["n_claims"]),
            ]
            for level in retention_order
        ]
    )

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(7.2, 2.65),
        gridspec_kw={"width_ratios": [1.35, 1.0, 1.0]},
    )
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.27, top=0.88, wspace=0.32)

    ax = axes[0]
    x = np.arange(len(dataset_order))
    width = 0.34
    bars_majority = ax.bar(
        x - width / 2,
        comparison_data[:, 0],
        width,
        color=NEUTRAL,
        edgecolor=NEUTRAL_DARK,
        linewidth=0.6,
        label="Majority",
        zorder=3,
    )
    bars_claimstab = ax.bar(
        x + width / 2,
        comparison_data[:, 1],
        width,
        color=BLUE,
        edgecolor=NEUTRAL_DARK,
        linewidth=0.6,
        label="claimstab",
        zorder=3,
    )
    ax.set_xticks(
        x,
        [
            "Global\nPatterns\nn=7",
            "enterotype\nn=5",
            "soilrep\nn=10",
            "atlas1006\nn=10",
        ],
    )
    ax.set_ylim(0, 8.4)
    ax.set_yticks(range(0, 9, 2))
    style_axis(ax, "Supported claims", "Claims")
    for bars in (bars_majority, bars_claimstab):
        for bar in bars:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.16,
                f"{int(bar.get_height())}",
                ha="center",
                va="bottom",
                fontsize=6.2,
            )
    ax.legend(loc="upper right", fontsize=6.3, handlelength=1.2)
    add_panel_label(ax, "a")

    ax = axes[1]
    y = np.arange(len(signal_order))
    height = 0.34
    ax.barh(
        y + height / 2,
        signal_data[:, 0],
        height,
        color=NEUTRAL,
        edgecolor=NEUTRAL_DARK,
        linewidth=0.6,
        zorder=3,
    )
    ax.barh(
        y - height / 2,
        signal_data[:, 1],
        height,
        color=BLUE,
        edgecolor=NEUTRAL_DARK,
        linewidth=0.6,
        zorder=3,
    )
    ax.set_yticks(
        y,
        [
            f"{label}\nn={int(signal_data[index, 2])}"
            for index, label in enumerate(signal_labels)
        ],
    )
    ax.set_xlim(0, 1.14)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "0.25", "0.50", "0.75", "1"])
    ax.invert_yaxis()
    style_axis(ax, "Worst-endpoint P", "")
    ax.set_xlabel("Support rate", fontsize=7)
    ax.tick_params(axis="y", pad=10)
    add_panel_label(ax, "b")

    ax = axes[2]
    y = np.arange(len(retention_order))
    ax.barh(
        y + height / 2,
        retention_data[:, 0],
        height,
        color=NEUTRAL,
        edgecolor=NEUTRAL_DARK,
        linewidth=0.6,
        zorder=3,
    )
    ax.barh(
        y - height / 2,
        retention_data[:, 1],
        height,
        color=BLUE,
        edgecolor=NEUTRAL_DARK,
        linewidth=0.6,
        zorder=3,
    )
    ax.set_yticks(
        y,
        [
            f"{label}\nn={int(retention_data[index, 2])}"
            for index, label in enumerate(retention_labels)
        ],
    )
    ax.set_xlim(0, 1.14)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "0.25", "0.50", "0.75", "1"])
    ax.invert_yaxis()
    style_axis(ax, "Effect retention", "")
    ax.set_xlabel("Support rate", fontsize=7)
    ax.tick_params(axis="y", pad=10)
    add_panel_label(ax, "c")

    fig.canvas.draw()
    base = OUTPUT / "multidataset_claim_stability"
    require_matplotlib_panel_alignment(
        fig,
        axes=axes,
        panel_ids=["a", "b", "c"],
        row_groups=[["a", "b", "c"]],
        column_groups=[],
        json_out=str(base) + ".alignment-layout.json",
        overlay_svg=str(base) + ".alignment.svg",
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        require_panel_labels=True,
        strict=True,
        exemptions=[
            {
                "panels": ["a"],
                "checks": ["panel-width"],
                "reason": "Dataset panel intentionally has more width for readable names",
            }
        ],
    )
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(base.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
