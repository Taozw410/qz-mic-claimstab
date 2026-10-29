from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ORDER = ["As", "AFP", "AEFP", "BP"]
COLORS = {
    "As": "#0072B2",
    "AFP": "#009E73",
    "AEFP": "#D55E00",
    "BP": "#E69F00",
}


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    result_dir = project_root / "03_结果" / "06_稳定性与参照区间"
    figure_dir = project_root / "04_图表" / "06_稳定性与参照区间"
    figure_dir.mkdir(parents=True, exist_ok=True)

    distances = pd.read_csv(result_dir / "bootstrap_group_distance.csv")
    exact = pd.read_csv(result_dir / "exact_label_permutation.csv")

    figure, axes = plt.subplots(1, 2, figsize=(8.2, 4.2), constrained_layout=True)
    for axis, domain in zip(axes, ["16S", "ITS"]):
        subset = (
            distances.loc[distances["Domain"].eq(domain)]
            .set_index("Composition")
            .loc[ORDER]
        )
        x = np.arange(len(ORDER))
        lower = subset["ObservedMeanDistance"] - subset["CI2.5"]
        upper = subset["CI97.5"] - subset["ObservedMeanDistance"]
        axis.errorbar(
            x,
            subset["ObservedMeanDistance"],
            yerr=np.vstack([lower, upper]),
            fmt="none",
            ecolor="#4A4A4A",
            elinewidth=1.1,
            capsize=3,
            zorder=1,
        )
        axis.scatter(
            x,
            subset["ObservedMeanDistance"],
            c=[COLORS[group] for group in ORDER],
            s=48,
            zorder=2,
        )
        for position, (group, row) in enumerate(subset.iterrows()):
            probability = row["ProbabilityClosest"]
            axis.annotate(
                f"{probability:.2f}",
                (position, row["CI97.5"]),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color="#333333",
            )

        range_p = exact.loc[
            exact["Domain"].eq(domain)
            & exact["Test"].str.startswith("Any artificial-treatment")
            , "RawExactP"
        ].iloc[0]
        axis.set_xticks(x, ORDER)
        axis.set_ylabel("Bray-Curtis distance to natural centroid")
        axis.set_title(f"{domain}: exact range P={range_p:.3f}", fontsize=10)
        axis.set_ylim(0.45, 0.86 if domain == "ITS" else 0.68)
        axis.grid(axis="y", color="#D9D9D9", linewidth=0.6)
        axis.set_axisbelow(True)
        for spine in ["top", "right"]:
            axis.spines[spine].set_visible(False)

    figure.suptitle(
        "Distance to natural reference with stratified bootstrap intervals",
        fontsize=11,
    )
    figure.text(
        0.5,
        -0.01,
        "Points: observed group means; bars: 95% percentile intervals; "
        "labels: bootstrap probability of ranking closest; n=3 per group.",
        ha="center",
        va="top",
        fontsize=7.5,
        wrap=True,
    )
    figure.savefig(
        figure_dir / "reference_distance_bootstrap.png",
        dpi=300,
        bbox_inches="tight",
        metadata={"Software": None},
    )
    plt.close(figure)
    (figure_dir / "README.md").write_text(
        "# 天然参照距离不确定性图\n\n"
        + "`reference_distance_bootstrap.png` 显示各人工处理到天然参照质心的观测平均"
        + "Bray-Curtis距离、2万次分层bootstrap的95%百分位区间，以及每次重采样中"
        + "该处理排名第一的概率。点的上方数字为“最接近天然参照”的bootstrap概率；"
        + "标题中的P值来自保留天然参照后、对12个人工处理小区记录进行369,600次精确"
        + "处理标签重组的总体组间差异检验。区间重叠和精确置换不显著表示当前3个"
        + "小区层记录不足以确认组间排序。\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
