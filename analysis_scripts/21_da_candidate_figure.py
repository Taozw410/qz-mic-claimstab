from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
RESULT_ROOT = ROOT / "03_结果"
OUTPUT_DIR = ROOT / "04_图表" / "12_两域差异丰度汇总"

DOMAIN_DIRS = {
    "16S": RESULT_ROOT / "05_16S差异丰度",
    "ITS": RESULT_ROOT / "11_ITS差异丰度",
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = pd.read_csv(
        RESULT_ROOT / "12_两域差异丰度汇总" / "single_tool_candidates.csv"
    )
    candidates = candidates.loc[candidates["ANCOMBC2Significant"].eq(True)].copy()

    standard_error = []
    for row in candidates.itertuples():
        group = row.Contrast.split()[0]
        ancom = pd.read_csv(DOMAIN_DIRS[row.Domain] / "ANCOMBC2_pairwise.csv")
        matched = ancom.loc[ancom["taxon"].eq(row.Genus)]
        if len(matched) != 1:
            raise ValueError(f"Expected one ANCOM row for {row.Domain} {row.Genus}")
        standard_error.append(float(matched.iloc[0][f"se_Composition{group}"]))
    candidates["ANCOMBC2SE"] = standard_error

    candidates["Label"] = (
        candidates["Domain"]
        + " | "
        + candidates["Contrast"].str.replace(" vs Natural", "", regex=False)
        + " | "
        + candidates["Genus"]
    )
    candidates = candidates.sort_values(
        ["Domain", "Contrast", "ANCOMBC2LogFoldChange"]
    ).reset_index(drop=True)

    y = np.arange(len(candidates))
    colors = candidates["Domain"].map({"16S": "#0072B2", "ITS": "#D55E00"})
    figure, axis = plt.subplots(figsize=(9, 6.4), constrained_layout=True)
    axis.errorbar(
        candidates["ANCOMBC2LogFoldChange"],
        y,
        xerr=1.96 * candidates["ANCOMBC2SE"],
        fmt="none",
        ecolor="#555555",
        elinewidth=1,
        capsize=3,
        zorder=1,
    )
    axis.scatter(
        candidates["ANCOMBC2LogFoldChange"],
        y,
        c=colors,
        s=42,
        zorder=2,
    )
    axis.axvline(0, color="#777777", linewidth=0.8, linestyle="--")
    axis.set_yticks(y, candidates["Label"])
    axis.set_xlabel("ANCOM-BC2 log fold change vs Natural (95% CI)")
    axis.set_title("ANCOM-BC2-only genus candidates, not confirmed by ALDEx2")
    axis.grid(axis="x", color="#E5E5E5", linewidth=0.6)
    axis.set_axisbelow(True)
    for spine in ["top", "right"]:
        axis.spines[spine].set_visible(False)
    for position, row in enumerate(candidates.itertuples()):
        axis.text(
            1.01,
            position,
            f"q={row.ANCOMBC2Q:.3f}",
            transform=axis.get_yaxis_transform(),
            va="center",
            ha="left",
            fontsize=7,
            color="#333333",
        )
    figure.savefig(
        OUTPUT_DIR / "ancombc2_only_candidates.png",
        dpi=300,
        bbox_inches="tight",
        metadata={"Software": None},
    )
    plt.close(figure)


if __name__ == "__main__":
    main()
