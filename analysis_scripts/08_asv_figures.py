from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path("C:/Users/<local-user>/AppData/Local/Temp/qz_mic_paper2/out/asv_analysis")
OUT = Path("C:/Users/<local-user>/AppData/Local/Temp/qz_mic_paper2/out/figures")
OUT.mkdir(parents=True, exist_ok=True)

ORDER = ["As", "AFP", "AEFP", "BP", "Natural"]
COLORS = {
    "As": "#0072B2",
    "AFP": "#009E73",
    "AEFP": "#D55E00",
    "BP": "#E69F00",
    "Natural": "#CC79A7",
}

fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
for column, domain in enumerate(["16S", "ITS"]):
    alpha = pd.read_csv(ROOT / f"alpha_samples_{domain}_primary.csv")
    for row, metric in enumerate(["Observed", "Shannon"]):
        axis = axes[row, column]
        for index, group in enumerate(ORDER):
            values = alpha.loc[alpha["Composition"] == group, metric]
            axis.scatter(
                [index] * len(values),
                values,
                color=COLORS[group],
                s=34,
                alpha=0.9,
            )
        axis.set_xticks(range(len(ORDER)), ORDER, rotation=30, ha="right")
        axis.set_ylabel(metric)
        axis.set_title(f"{domain} ASV {metric}")
fig.savefig(OUT / "alpha_asv_primary.png", dpi=300)
plt.close(fig)

fig, axis = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
for domain, marker in [("16S", "o"), ("ITS", "s")]:
    distances = pd.read_csv(ROOT / f"natural_reference_distance_{domain}_primary.csv")
    distances = distances.set_index("Composition").loc[ORDER]
    axis.errorbar(
        distances.index,
        distances["MeanDistanceToNatural"],
        yerr=distances["SE"],
        marker=marker,
        capsize=3,
        label=domain,
    )
axis.set_xlabel("Composition")
axis.set_ylabel("Bray-Curtis distance to natural centroid")
axis.set_title("ASV-level distance to natural reference")
axis.legend(frameon=False)
fig.savefig(OUT / "natural_reference_distance_asv.png", dpi=300)
plt.close(fig)
