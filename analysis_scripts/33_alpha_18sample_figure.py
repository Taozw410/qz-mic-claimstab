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
INPUT = (
    ROOT
    / "03_结果"
    / "14_分析可重复性"
    / "07_18样品alpha敏感性"
    / "alpha_omnibus_15_vs_18.csv"
)
OUTPUT = (
    ROOT
    / "04_图表"
    / "14_分析可重复性"
    / "alpha_18sample_sensitivity.png"
)

COLORS = {"OriginalOTU": "#7F7F7F", "CurrentASV": "#0072B2"}
LABELS = {"OriginalOTU": "Original OTU", "CurrentASV": "Current ASV"}


def main() -> None:
    frame = pd.read_csv(INPUT)
    pairs = [
        (domain, metric)
        for domain in ("16S", "ITS")
        for metric in ("Observed", "Shannon", "Simpson")
    ]
    figure, axis = plt.subplots(figsize=(10, 4.8))
    x = np.arange(len(pairs))
    offsets = {
        ("OriginalOTU", "primary15"): -0.14,
        ("OriginalOTU", "sensitivity18"): -0.05,
        ("CurrentASV", "primary15"): 0.05,
        ("CurrentASV", "sensitivity18"): 0.14,
    }
    markers = {"primary15": "o", "sensitivity18": "D"}

    for pipeline in ("OriginalOTU", "CurrentASV"):
        for sample_set in ("primary15", "sensitivity18"):
            values = []
            for domain, metric in pairs:
                row = frame.loc[
                    frame["Domain"].eq(domain)
                    & frame["Pipeline"].eq(pipeline)
                    & frame["Metric"].eq(metric)
                    & frame["SampleSet"].eq(sample_set)
                ].iloc[0]
                values.append(min(-np.log10(float(row["P"])), 4.0))
            axis.scatter(
                x + offsets[(pipeline, sample_set)],
                values,
                s=38,
                marker=markers[sample_set],
                color=COLORS[pipeline],
                alpha=1.0 if sample_set == "sensitivity18" else 0.55,
                label=f"{LABELS[pipeline]}, {sample_set}",
            )
        p15 = []
        p18 = []
        for domain, metric in pairs:
            for sample_set, target in (("primary15", p15), ("sensitivity18", p18)):
                row = frame.loc[
                    frame["Domain"].eq(domain)
                    & frame["Pipeline"].eq(pipeline)
                    & frame["Metric"].eq(metric)
                    & frame["SampleSet"].eq(sample_set)
                ].iloc[0]
                target.append(min(-np.log10(float(row["P"])), 4.0))
        for position, value15, value18 in zip(x, p15, p18):
            axis.plot(
                [
                    position + offsets[(pipeline, "primary15")],
                    position + offsets[(pipeline, "sensitivity18")],
                ],
                [value15, value18],
                color=COLORS[pipeline],
                linewidth=0.7,
                alpha=0.45,
            )

    axis.axhline(-np.log10(0.05), color="#B2182B", linestyle="--", linewidth=0.9)
    axis.text(
        len(pairs) - 0.55,
        -np.log10(0.05) + 0.06,
        "P = 0.05",
        color="#B2182B",
        ha="right",
        fontsize=7,
    )
    axis.set_xticks(x, [f"{domain}\n{metric}" for domain, metric in pairs])
    axis.set_ylabel("−log10(P), capped at 4")
    axis.set_ylim(0, 4.2)
    axis.set_title(
        "Alpha-diversity group tests: 15 versus 18 samples",
        loc="left",
        fontweight="bold",
    )
    axis.legend(frameon=False, fontsize=7, ncol=4, loc="upper left")
    axis.grid(axis="y", color="#E6E6E6", linewidth=0.6)
    axis.set_axisbelow(True)
    for spine in ("top", "right"):
        axis.spines[spine].set_visible(False)
    figure.tight_layout()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        OUTPUT,
        dpi=300,
        bbox_inches="tight",
        metadata={"Software": None},
    )
    figure.savefig(
        OUTPUT.with_suffix(".pdf"),
        bbox_inches="tight",
        metadata={"Creator": None, "Producer": None},
    )
    plt.close(figure)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
