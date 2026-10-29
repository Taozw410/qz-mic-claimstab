from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "01_数据"
OUTPUT_DIR = ROOT / "03_结果" / "13_与原文对比"

TREATMENT_LABELS = {
    "T1": "As",
    "T6": "AFP",
    "T7": "AEFP",
    "T22": "BP",
    "T23": "Natural",
}
TREATMENT_ORDER = ["T1", "T6", "T7", "T22", "T23"]
KEY_PHYLA = [
    "Proteobacteria",
    "Actinobacteriota",
    "Acidobacteriota",
    "Chloroflexi",
]


def build_phylum_summary() -> pd.DataFrame:
    samples = pd.read_csv(DATA_DIR / "sample_sheet.csv")
    samples = samples.loc[samples["Primary5"].astype(bool)].copy()
    samples = samples.set_index("Sample")

    counts = pd.read_csv(DATA_DIR / "ASV_16S" / "asv_table.csv").set_index("ASV")
    taxonomy = pd.read_csv(DATA_DIR / "ASV_16S" / "taxonomy_silva.csv").set_index(
        "ASV"
    )

    sample_ids = samples.index.tolist()
    classified = counts[sample_ids].join(taxonomy[["Phylum"]], how="left")
    classified["Phylum"] = classified["Phylum"].fillna("Unclassified_Phylum")
    phylum_counts = classified.groupby("Phylum", dropna=False)[sample_ids].sum()
    relative = phylum_counts.div(phylum_counts.sum(axis=0), axis=1)

    sample_relative = relative.T
    sample_relative.index.name = "Sample"
    sample_relative.insert(
        0,
        "Treatment",
        samples.loc[sample_relative.index, "Treatment"].to_numpy(),
    )
    sample_relative.insert(
        1,
        "Composition",
        samples.loc[sample_relative.index, "Composition"].to_numpy(),
    )
    sample_relative.insert(
        2,
        "Density",
        samples.loc[sample_relative.index, "Density"].to_numpy(),
    )
    sample_relative.to_csv(
        OUTPUT_DIR / "16S_phylum_relative_abundance_by_sample.csv",
        index_label="Sample",
        encoding="utf-8-sig",
    )

    long = sample_relative.reset_index().melt(
        id_vars=["Sample", "Treatment", "Composition", "Density"],
        var_name="Phylum",
        value_name="RelativeAbundance",
    )
    summary = (
        long.groupby(["Treatment", "Composition", "Density", "Phylum"])[
            "RelativeAbundance"
        ]
        .agg(["mean", "std", "count"])
        .reset_index()
        .rename(
            columns={
                "mean": "MeanRelativeAbundance",
                "std": "SDRelativeAbundance",
                "count": "N",
            }
        )
    )
    summary["SortOrder"] = summary["Treatment"].map(
        {treatment: index for index, treatment in enumerate(TREATMENT_ORDER)}
    )
    summary = summary.sort_values(["SortOrder", "MeanRelativeAbundance"],
                                  ascending=[True, False])
    return summary.drop(columns="SortOrder")


def build_contrasts(summary: pd.DataFrame) -> pd.DataFrame:
    means = (
        summary.pivot(index="Phylum", columns="Treatment", values="MeanRelativeAbundance")
        .reindex(columns=TREATMENT_ORDER)
        * 100
    )
    rows = []
    contrasts = [
        ("BP_to_As", "T22", "T1"),
        ("BP_to_AFP", "T22", "T6"),
        ("BP_to_AEFP", "T22", "T7"),
        ("BP_to_Natural", "T22", "T23"),
    ]
    for phylum in KEY_PHYLA:
        for contrast, baseline, comparator in contrasts:
            rows.append(
                {
                    "Phylum": phylum,
                    "Contrast": contrast,
                    "Baseline": TREATMENT_LABELS[baseline],
                    "Comparator": TREATMENT_LABELS[comparator],
                    "BaselinePercent": means.loc[phylum, baseline],
                    "ComparatorPercent": means.loc[phylum, comparator],
                    "DifferencePercentagePoints": (
                        means.loc[phylum, comparator] - means.loc[phylum, baseline]
                    ),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = build_phylum_summary()
    summary.to_csv(
        OUTPUT_DIR / "16S_phylum_group_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    contrasts = build_contrasts(summary)
    contrasts.to_csv(
        OUTPUT_DIR / "16S_key_phylum_descriptive_contrasts.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(f"Wrote {len(summary)} phylum-treatment rows to {OUTPUT_DIR}")
    print(f"Wrote {len(contrasts)} descriptive contrasts to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
