from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent
DATA_DIR = PROJECT_ROOT / "数据" / "原始数据"
ASV_DIR = ROOT / "01_数据"
OUT_DIR = ROOT / "03_结果" / "14_分析可重复性" / "01_基础矩阵"

DOMAINS = {
    "16S": {
        "old_xls": DATA_DIR / "丰度表-16s.xls",
        "asv_table": ASV_DIR / "ASV_16S" / "asv_table.csv",
        "taxonomy": ASV_DIR / "ASV_16S" / "taxonomy_silva.csv",
    },
    "ITS": {
        "old_xls": DATA_DIR / "丰度表-its.xls",
        "asv_table": ASV_DIR / "ASV_ITS" / "asv_table.csv",
        "taxonomy": ASV_DIR / "ASV_ITS" / "taxonomy_unite.csv",
    },
}

ORIGINAL_ALPHA = {
    "16S": DATA_DIR / "多样性指数表-16S.xls",
    "ITS": DATA_DIR / "多样性指数表-its.xls",
}
ORIGINAL_PERMANOVA = {
    "16S": DATA_DIR / "PERMANOVA结果表16s.xls",
    "ITS": DATA_DIR / "PERMANOVA结果表its.xls",
}

PHYLUM_SYNONYMS = {
    "Actinobacteria": "Actinobacteriota",
    "Acidobacteria": "Acidobacteriota",
    "Bacteroidetes": "Bacteroidota",
    "Verrucomicrobia": "Verrucomicrobiota",
    "Gemmatimonadetes": "Gemmatimonadota",
    "Armatimonadetes": "Armatimonadota",
    "Planctomycetes": "Planctomycetota",
    "Nitrospirae": "Nitrospirota",
    "Spirochaetes": "Spirochaetota",
    "Deinococcus-Thermus": "Deinococcota",
    "Latescibacteria": "Latescibacterota",
    "Epsilonbacteraeota": "Campylobacterota",
    "Elusimicrobia": "Elusimicrobiota",
    "Fibrobacteres": "Fibrobacterota",
    "unclassified_k__norank_d__Bacteria": "Unclassified_Bacteria",
    "unclassified_k__Fungi": "Unclassified_Fungi",
    "unclassified_d__Eukaryota": "Unclassified_Eukaryota",
}

TREATMENT_ORDER = ["As", "AFP", "AEFP", "BP", "Natural", "Unassigned"]


def clean_taxon(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    for prefix in ("p__", "B__", "F__"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    return PHYLUM_SYNONYMS.get(text, text)


def load_sample_sheet() -> pd.DataFrame:
    samples = pd.read_csv(ASV_DIR / "sample_sheet.csv", encoding="utf-8-sig")
    samples["Primary5"] = (
        samples["Primary5"].astype(str).str.lower().isin(["true", "1", "yes"])
    )
    return samples


def write_original_derived() -> None:
    alpha_frames = []
    permanova_frames = []
    for domain, path in ORIGINAL_ALPHA.items():
        alpha = pd.read_excel(path, sheet_name="多样性指数表")
        alpha = alpha.rename(columns={"Sample\\Estimators": "Sample"})
        alpha.insert(0, "Domain", domain)
        alpha_frames.append(alpha)
    alpha = pd.concat(alpha_frames, ignore_index=True)
    alpha.to_csv(OUT_DIR / "original_alpha.csv", index=False, encoding="utf-8-sig")

    for domain, path in ORIGINAL_PERMANOVA.items():
        result = pd.read_excel(path, sheet_name="PERMANOVA结果表")
        result.insert(0, "Domain", domain)
        result.insert(1, "SourceFile", path.name)
        permanova_frames.append(result)
    pd.concat(permanova_frames, ignore_index=True).to_csv(
        OUT_DIR / "original_published_permanova.csv",
        index=False,
        encoding="utf-8-sig",
    )


def load_original_phylum(domain: str, sample_ids: list[str]) -> pd.DataFrame:
    raw = pd.read_excel(DOMAINS[domain]["old_xls"], sheet_name="OTU表")
    missing = sorted(set(sample_ids) - set(raw.columns))
    if missing:
        raise ValueError(f"{domain}: samples missing from old phylum table: {missing}")
    counts = raw[["Phylum", *sample_ids]].copy()
    counts["Phylum"] = counts["Phylum"].map(clean_taxon)
    counts = counts.groupby("Phylum", as_index=True)[sample_ids].sum()
    counts = counts.apply(pd.to_numeric, errors="coerce").fillna(0)
    return counts.T


def load_current_phylum(
    domain: str, sample_ids: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    asv = pd.read_csv(DOMAINS[domain]["asv_table"], encoding="utf-8-sig").set_index(
        "ASV"
    )
    taxonomy = pd.read_csv(
        DOMAINS[domain]["taxonomy"], encoding="utf-8-sig"
    ).set_index("ASV")

    missing = sorted(set(sample_ids) - set(asv.columns))
    if missing:
        raise ValueError(f"{domain}: samples missing from ASV table: {missing}")

    counts = asv[sample_ids].copy()
    if domain == "16S":
        chloroplast = (
            taxonomy["Order"].fillna("").str.contains("Chloroplast", case=False)
        )
        mitochondria = (
            taxonomy["Family"].fillna("").str.contains("Mitochondria", case=False)
        )
        keep = ~(chloroplast | mitochondria)
        counts = counts.loc[keep]
        taxonomy = taxonomy.loc[keep]

    phylum = taxonomy["Phylum"].map(clean_taxon)
    phylum = phylum.replace("", "Unclassified_Phylum").fillna("Unclassified_Phylum")
    phylum_counts = counts.groupby(phylum).sum()
    phylum_counts.index.name = "Phylum"
    return phylum_counts.T, taxonomy


def relative_rows(counts: pd.DataFrame) -> pd.DataFrame:
    totals = counts.sum(axis=1)
    if (totals <= 0).any():
        raise ValueError("Every sample must have a positive count total")
    return counts.div(totals, axis=0)


def bray_rows(first: pd.DataFrame, second: pd.DataFrame) -> pd.Series:
    union_columns = sorted(set(first.columns) | set(second.columns))
    first = first.reindex(columns=union_columns, fill_value=0)
    second = second.reindex(columns=union_columns, fill_value=0)
    numerator = (first - second).abs().sum(axis=1)
    denominator = (first + second).sum(axis=1)
    return numerator / denominator.replace(0, np.nan)


def spearman_series(first: pd.Series, second: pd.Series) -> float:
    paired = pd.concat([first, second], axis=1).dropna()
    if len(paired) < 3:
        return np.nan
    ranked = paired.rank(method="average")
    return float(ranked.iloc[:, 0].corr(ranked.iloc[:, 1]))


def build_domain(
    domain: str, samples: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sample_ids = samples["Sample"].tolist()
    old_counts = load_original_phylum(domain, sample_ids)
    current_counts, taxonomy = load_current_phylum(domain, sample_ids)
    old_rel = relative_rows(old_counts)
    current_rel = relative_rows(current_counts)

    common = sorted(set(old_rel.columns) & set(current_rel.columns))
    if len(common) < 3:
        raise ValueError(f"{domain}: too few common phyla ({len(common)})")

    old_common_raw = old_rel[common]
    current_common_raw = current_rel[common]
    old_common = old_common_raw.div(
        old_common_raw.sum(axis=1), axis=0
    )
    current_common = current_common_raw.div(
        current_common_raw.sum(axis=1), axis=0
    )
    union_columns = sorted(set(old_rel.columns) | set(current_rel.columns))
    old_union = old_rel.reindex(columns=union_columns, fill_value=0)
    current_union = current_rel.reindex(columns=union_columns, fill_value=0)
    sample_concordance = pd.DataFrame(
        {
            "Domain": domain,
            "Sample": sample_ids,
            "OldTotalCounts": old_counts.sum(axis=1).reindex(sample_ids).to_numpy(),
            "CurrentTotalCounts": current_counts.sum(axis=1)
            .reindex(sample_ids)
            .to_numpy(),
            "CommonPhyla": len(common),
            "OldCommonReadFraction": old_common_raw.sum(axis=1).to_numpy(),
            "CurrentCommonReadFraction": current_common_raw.sum(axis=1).to_numpy(),
            "OldUnclassifiedFraction": old_rel[
                [column for column in old_rel.columns if "Unclassified" in column]
            ]
            .sum(axis=1)
            .to_numpy(),
            "CurrentUnclassifiedFraction": current_rel[
                [
                    column
                    for column in current_rel.columns
                    if "Unclassified" in column
                ]
            ]
            .sum(axis=1)
            .to_numpy(),
            "BrayOldVsCurrentCommon": bray_rows(
                old_common, current_common
            ).to_numpy(),
            "BrayOldVsCurrentAllUnion": bray_rows(
                old_union, current_union
            ).to_numpy(),
        }
    )
    sample_concordance["SpearmanAcrossPhyla"] = [
        spearman_series(old_common.loc[sample], current_common.loc[sample])
        for sample in sample_ids
    ]

    sample_metadata = samples.set_index("Sample")
    for column in ("RawGroup", "Treatment", "Composition", "Primary5"):
        sample_concordance[column] = sample_concordance["Sample"].map(
            sample_metadata[column]
        )

    phylum_correlations = []
    for phylum in common:
        old_values = old_common[phylum]
        current_values = current_common[phylum]
        phylum_correlations.append(
            {
                "Domain": domain,
                "Phylum": phylum,
                "SpearmanAcrossSamples": spearman_series(old_values, current_values),
                "PearsonAcrossSamples": old_values.corr(current_values),
                "OldMeanRelative": old_values.mean(),
                "CurrentMeanRelative": current_values.mean(),
                "OldDetectionSamples": int((old_values > 0).sum()),
                "CurrentDetectionSamples": int((current_values > 0).sum()),
            }
        )
    phylum_correlations = pd.DataFrame(phylum_correlations)

    group_means = []
    for composition in TREATMENT_ORDER:
        group_samples = sample_metadata.index[
            sample_metadata["Composition"].eq(composition)
        ].tolist()
        if not group_samples:
            continue
        for phylum in common:
            old_mean = old_common.loc[group_samples, phylum].mean()
            current_mean = current_common.loc[group_samples, phylum].mean()
            group_means.append(
                {
                    "Domain": domain,
                    "Composition": composition,
                    "Phylum": phylum,
                    "OldMeanRelative": old_mean,
                    "CurrentMeanRelative": current_mean,
                    "DifferenceCurrentMinusOld": current_mean - old_mean,
                    "OldMeanRelativeRaw": old_common_raw.loc[
                        group_samples, phylum
                    ].mean(),
                    "CurrentMeanRelativeRaw": current_common_raw.loc[
                        group_samples, phylum
                    ].mean(),
                }
            )
    group_means = pd.DataFrame(group_means)

    crosswalk_rows = []
    for phylum in sorted(set(old_rel.columns) | set(current_rel.columns)):
        crosswalk_rows.append(
            {
                "Domain": domain,
                "CanonicalPhylum": phylum,
                "InOriginal": phylum in old_rel.columns,
                "InCurrent": phylum in current_rel.columns,
                "Common": phylum in common,
            }
        )
    crosswalk = pd.DataFrame(crosswalk_rows)

    old_counts.index.name = "Sample"
    current_counts.index.name = "Sample"
    old_counts.to_csv(
        OUT_DIR / f"original_phylum_counts_{domain}.csv", encoding="utf-8-sig"
    )
    current_counts.to_csv(
        OUT_DIR / f"current_asv_phylum_counts_{domain}.csv", encoding="utf-8-sig"
    )
    return sample_concordance, phylum_correlations, group_means, crosswalk, taxonomy


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_original_derived()
    samples = load_sample_sheet()
    sample_audit = samples[
        [
            "Sample",
            "RawGroup",
            "Treatment",
            "Composition",
            "Primary5",
            "PlotRecordID",
            "FieldPlotID",
        ]
    ].copy()
    sample_audit.to_csv(
        OUT_DIR / "sample_mapping_audit.csv", index=False, encoding="utf-8-sig"
    )

    sample_concordances = []
    phylum_correlations = []
    group_means = []
    crosswalks = []
    taxonomy_audits = []
    for domain in DOMAINS:
        audit, correlations, means, crosswalk, taxonomy = build_domain(
            domain, samples
        )
        sample_concordances.append(audit)
        phylum_correlations.append(correlations)
        group_means.append(means)
        crosswalks.append(crosswalk)
        taxonomy_audits.append(
            {
                "Domain": domain,
                "CurrentASVs": len(taxonomy),
                "CurrentPhylumAssigned": int(taxonomy["Phylum"].notna().sum()),
                "CurrentPhylumMissing": int(taxonomy["Phylum"].isna().sum()),
                "CurrentGenera": int(
                    taxonomy["Genus"].dropna().astype(str).str.len().gt(0).sum()
                ),
            }
        )

    pd.concat(sample_concordances, ignore_index=True).to_csv(
        OUT_DIR / "sample_level_old_vs_current_concordance.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.concat(phylum_correlations, ignore_index=True).to_csv(
        OUT_DIR / "phylum_cross_sample_correlations.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.concat(group_means, ignore_index=True).to_csv(
        OUT_DIR / "group_phylum_mean_comparison.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.concat(crosswalks, ignore_index=True).to_csv(
        OUT_DIR / "phylum_crosswalk.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(taxonomy_audits).to_csv(
        OUT_DIR / "taxonomy_audit.csv", index=False, encoding="utf-8-sig"
    )
    print(f"Wrote reproducibility base matrices to {OUT_DIR}")


if __name__ == "__main__":
    main()
