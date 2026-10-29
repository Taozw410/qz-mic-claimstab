from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
RESULT_DIR = ROOT / "03_结果" / "07_ITS_UNITE分类"
DATA_DIR = ROOT / "01_数据" / "ASV_ITS"
RANKS = ["Kingdom", "Phylum", "Class", "Order", "Family", "Genus", "Species"]


def short_taxon(value: object, rank: str) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return f"Unclassified_{rank}"
    return re.sub(r"^[a-z]__", "", str(value))


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    run1 = pd.read_csv(RESULT_DIR / "taxonomy_unite_previous.csv")
    run2 = pd.read_csv(RESULT_DIR / "taxonomy_unite_run2.csv")
    if run1["ASV"].tolist() != run2["ASV"].tolist():
        raise ValueError("The two taxonomy runs do not contain identical ASV order")
    if run1["ASV"].duplicated().any() or run2["ASV"].duplicated().any():
        raise ValueError("Duplicate ASV IDs in taxonomy output")

    counts = pd.read_csv(DATA_DIR / "asv_table.csv")
    sample_sheet = pd.read_csv(ROOT / "01_数据" / "sample_sheet.csv")
    return run1, run2, counts, sample_sheet


def reconcile(run1: pd.DataFrame, run2: pd.DataFrame) -> pd.DataFrame:
    changed = run1[RANKS].fillna("") != run2[RANKS].fillna("")
    consensus = pd.DataFrame({"ASV": run1["ASV"]})
    for rank in RANKS:
        consensus[rank] = run1[rank].where(~changed[rank], np.nan)
    consensus["StableAcrossRuns"] = ~changed.any(axis=1)
    consensus["ChangedRanks"] = changed.apply(
        lambda row: ";".join(rank for rank in RANKS if row[rank]),
        axis=1,
    )
    return consensus


def rank_counts(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for label, frame in frames.items():
        row = {"Run": label}
        for rank in RANKS:
            row[rank] = int(frame[rank].notna().sum())
        rows.append(row)
    return pd.DataFrame(rows)


def composition_tables(
    consensus: pd.DataFrame,
    counts: pd.DataFrame,
    sample_sheet: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    sample_columns = sample_sheet["Sample"].tolist()
    count_matrix = counts.set_index("ASV")[sample_columns]
    missing = sorted(set(count_matrix.index) - set(consensus["ASV"]))
    if missing:
        raise ValueError(f"ASVs missing taxonomy: {missing[:10]}")

    taxonomy = consensus.set_index("ASV").loc[count_matrix.index]
    metadata = sample_sheet.set_index("Sample")
    outputs = {}
    for rank in ["Phylum", "Genus"]:
        labels = taxonomy[rank].map(lambda value: short_taxon(value, rank))
        by_asv = count_matrix.copy()
        by_asv[rank] = labels.to_numpy()
        grouped = by_asv.groupby(rank).sum()
        sample_totals = count_matrix.sum(axis=0)
        relative = grouped.div(sample_totals, axis=1).T
        relative.index.name = "Sample"
        relative = relative.reset_index().merge(
            metadata[
                ["Treatment", "Composition", "Density", "Primary5"]
            ].reset_index(),
            on="Sample",
            how="left",
            validate="one_to_one",
        )
        relative.to_csv(
            RESULT_DIR / f"its_{rank.lower()}_relative_abundance_by_sample.csv",
            index=False,
        )

        primary = relative.loc[relative["Primary5"].astype(bool)].copy()
        taxon_columns = [
            column
            for column in primary.columns
            if column
            not in {
                "Sample",
                "Treatment",
                "Composition",
                "Density",
                "Primary5",
            }
        ]
        summary = (
            primary.melt(
                id_vars=["Treatment", "Composition", "Density"],
                value_vars=taxon_columns,
                var_name=rank,
                value_name="RelativeAbundance",
            )
            .groupby(["Treatment", "Composition", "Density", rank])[
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
        summary.to_csv(
            RESULT_DIR / f"its_group_{rank.lower()}_summary.csv",
            index=False,
        )
        top = (
            summary.sort_values(
                ["Treatment", "MeanRelativeAbundance"],
                ascending=[True, False],
            )
            .groupby("Treatment", as_index=False)
            .head(10)
            .copy()
        )
        top["RankWithinTreatment"] = top.groupby("Treatment").cumcount() + 1
        top.to_csv(
            RESULT_DIR / f"its_group_{rank.lower()}_top10.csv",
            index=False,
        )
        if rank == "Genus":
            classified_top = (
                summary.loc[summary[rank].ne("Unclassified_Genus")]
                .sort_values(
                    ["Treatment", "MeanRelativeAbundance"],
                    ascending=[True, False],
                )
                .groupby("Treatment", as_index=False)
                .head(10)
                .copy()
            )
            classified_top["RankWithinTreatment"] = (
                classified_top.groupby("Treatment").cumcount() + 1
            )
            classified_top.to_csv(
                RESULT_DIR / "its_group_genus_top10_classified.csv",
                index=False,
            )
            outputs[rank] = classified_top
        else:
            outputs[rank] = top

    richness = pd.DataFrame(
        {
            "Sample": count_matrix.columns,
            "ObservedGenera": [
                int(((count_matrix[column] > 0) & consensus.set_index("ASV")["Genus"].notna()).sum())
                for column in count_matrix.columns
            ],
        }
    ).merge(
        metadata[["Treatment", "Composition", "Density", "Primary5"]].reset_index(),
        on="Sample",
        how="left",
        validate="one_to_one",
    )
    richness.to_csv(RESULT_DIR / "its_observed_genera_by_sample.csv", index=False)
    return outputs


def main() -> None:
    run1, run2, counts, sample_sheet = load_inputs()
    sample_sheet["Primary5"] = (
        sample_sheet["Primary5"].astype(str).str.lower().isin(["true", "1", "yes"])
    )
    consensus = reconcile(run1, run2)
    consensus.to_csv(DATA_DIR / "taxonomy_unite.csv", index=False)
    consensus.to_csv(RESULT_DIR / "taxonomy_unite_consensus.csv", index=False)

    changed = ~consensus["StableAcrossRuns"]
    differences = pd.concat(
        [
            run1.loc[changed, ["ASV", *RANKS]].add_prefix("Run1_"),
            run2.loc[changed, RANKS].add_prefix("Run2_"),
            consensus.loc[changed, ["ChangedRanks"]],
        ],
        axis=1,
    )
    differences.to_csv(RESULT_DIR / "taxonomy_run_differences.csv", index=False)

    counts_table = rank_counts(
        {
            "Run1": run1,
            "Run2": run2,
            "Consensus": consensus,
        }
    )
    counts_table.to_csv(RESULT_DIR / "taxonomy_rank_counts.csv", index=False)
    top = composition_tables(consensus, counts, sample_sheet)

    audit = {
        "ASVs": len(consensus),
        "stable_ASVs": int(consensus["StableAcrossRuns"].sum()),
        "unstable_ASVs": int(changed.sum()),
        "unstable_fraction": float(changed.mean()),
        "changed_cells_by_rank": {
            rank: int((run1[rank].fillna("") != run2[rank].fillna("")).sum())
            for rank in RANKS
        },
        "consensus_assignment_counts": {
            rank: int(consensus[rank].notna().sum()) for rank in RANKS
        },
        "top_phylum_per_group": top["Phylum"][
            top["Phylum"]["RankWithinTreatment"].eq(1)
        ][["Treatment", "Phylum", "MeanRelativeAbundance"]].to_dict("records"),
        "top_classified_genus_per_group": top["Genus"][
            top["Genus"]["RankWithinTreatment"].eq(1)
        ][["Treatment", "Genus", "MeanRelativeAbundance"]].to_dict("records"),
    }
    (RESULT_DIR / "taxonomy_reanalysis_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
