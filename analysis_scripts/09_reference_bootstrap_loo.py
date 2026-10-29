from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


SEED = 20261023
N_BOOT = 20000
N_PERM = 999
ARTIFICIAL = ["As", "AFP", "AEFP", "BP"]
GROUP_ORDER = ["As", "AFP", "AEFP", "BP", "Natural"]


def read_sheet(path: Path) -> pd.DataFrame:
    sheet = pd.read_csv(path)
    sheet["Primary5"] = (
        sheet["Primary5"].astype(str).str.lower().isin(["true", "1", "yes"])
    )
    return sheet


def load_relative_counts(
    project_root: Path, domain: str, samples: list[str]
) -> np.ndarray:
    if domain == "16S":
        directory = project_root / "01_数据" / "ASV_16S"
    else:
        directory = project_root / "01_数据" / "ASV_ITS"

    table = pd.read_csv(directory / "asv_table.csv", index_col=0)
    missing = sorted(set(samples) - set(table.columns))
    if missing:
        raise ValueError(f"{domain}: missing samples in ASV table: {missing}")
    counts = table[samples].T.copy()

    if domain == "16S":
        taxonomy = pd.read_csv(directory / "taxonomy_silva.csv", index_col="ASV")
        taxonomy = taxonomy.loc[counts.columns]
        chloroplast = taxonomy["Order"].fillna("").str.contains(
            "Chloroplast", case=False, regex=False
        )
        mitochondria = taxonomy["Family"].fillna("").str.contains(
            "Mitochondria", case=False, regex=False
        )
        counts = counts.loc[:, ~(chloroplast | mitochondria).to_numpy()]

    relative = counts.to_numpy(dtype=float)
    totals = relative.sum(axis=1, keepdims=True)
    if np.any(totals <= 0):
        raise ValueError(f"{domain}: sample with zero reads after filtering")
    return relative / totals


def bray_curtis(matrix: np.ndarray) -> np.ndarray:
    n = matrix.shape[0]
    distance = np.zeros((n, n), dtype=float)
    row_sums = matrix.sum(axis=1)
    for left in range(n):
        for right in range(left + 1, n):
            value = np.abs(matrix[left] - matrix[right]).sum() / (
                row_sums[left] + row_sums[right]
            )
            distance[left, right] = distance[right, left] = value
    return distance


def reference_distances(
    relative: np.ndarray,
    metadata: pd.DataFrame,
    sample_indices: np.ndarray | None = None,
) -> pd.Series:
    if sample_indices is None:
        sample_indices = np.arange(len(metadata))
    selected_meta = metadata.iloc[sample_indices].reset_index(drop=True)
    selected = relative[sample_indices]
    natural = selected[selected_meta["Composition"].eq("Natural").to_numpy()]
    if len(natural) == 0:
        raise ValueError("Natural reference absent")
    centroid = natural.mean(axis=0)
    denominator = selected.sum(axis=1) + centroid.sum()
    values = np.abs(selected - centroid).sum(axis=1) / denominator
    return pd.Series(values, index=selected_meta["Sample"])


def bootstrap_reference(
    relative: np.ndarray, metadata: pd.DataFrame, rng: np.random.Generator
) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = metadata["Composition"].to_numpy()
    indices = {group: np.flatnonzero(labels == group) for group in GROUP_ORDER}
    distributions: dict[str, list[float]] = {
        group: [] for group in ARTIFICIAL
    }
    ranks: dict[str, list[int]] = {group: [] for group in ARTIFICIAL}

    for _ in range(N_BOOT):
        natural_indices = rng.choice(
            indices["Natural"], size=len(indices["Natural"]), replace=True
        )
        centroid = relative[natural_indices].mean(axis=0)
        means = {}
        for group in ARTIFICIAL:
            sampled = rng.choice(indices[group], size=len(indices[group]), replace=True)
            values = np.abs(relative[sampled] - centroid).sum(axis=1) / (
                relative[sampled].sum(axis=1) + centroid.sum()
            )
            mean_distance = float(values.mean())
            distributions[group].append(mean_distance)
            means[group] = mean_distance
        ordered = sorted(means, key=means.get)
        for rank, group in enumerate(ordered, start=1):
            ranks[group].append(rank)

    observed = reference_distances(relative, metadata)
    observed_means = {
        group: float(observed[metadata.loc[metadata["Composition"].eq(group), "Sample"]].mean())
        for group in ARTIFICIAL
    }
    group_rows = []
    for group in ARTIFICIAL:
        values = np.asarray(distributions[group])
        group_rows.append(
            {
                "Composition": group,
                "N": int(metadata["Composition"].eq(group).sum()),
                "ObservedMeanDistance": observed_means[group],
                "BootstrapMedian": float(np.median(values)),
                "CI2.5": float(np.quantile(values, 0.025)),
                "CI97.5": float(np.quantile(values, 0.975)),
                "ProbabilityClosest": float(np.mean(np.asarray(ranks[group]) == 1)),
                "ProbabilityRank1Or2": float(np.mean(np.asarray(ranks[group]) <= 2)),
            }
        )

    difference_rows = []
    aefp = np.asarray(distributions["AEFP"])
    for comparator in ["As", "AFP", "BP"]:
        difference = aefp - np.asarray(distributions[comparator])
        difference_rows.append(
            {
                "Contrast": f"AEFP minus {comparator}",
                "ObservedDifference": observed_means["AEFP"] - observed_means[comparator],
                "BootstrapMedian": float(np.median(difference)),
                "CI2.5": float(np.quantile(difference, 0.025)),
                "CI97.5": float(np.quantile(difference, 0.975)),
                "ProbabilityAEFPCloser": float(np.mean(difference < 0)),
            }
        )
    return pd.DataFrame(group_rows), pd.DataFrame(difference_rows)


def exact_label_permutation(
    relative: np.ndarray, metadata: pd.DataFrame
) -> pd.DataFrame:
    observed_distances = reference_distances(relative, metadata)
    artificial_rows = metadata.loc[
        metadata["Composition"].isin(ARTIFICIAL), ["Sample", "Composition"]
    ].reset_index(drop=True)
    values = observed_distances.loc[artificial_rows["Sample"]].to_numpy()
    n = len(values)
    positions = set(range(n))

    observed_means = {
        group: float(values[(artificial_rows["Composition"] == group).to_numpy()].mean())
        for group in ARTIFICIAL
    }
    observed_range = max(observed_means.values()) - min(observed_means.values())
    observed_pairwise = {
        comparator: abs(observed_means["AEFP"] - observed_means[comparator])
        for comparator in ["As", "AFP", "BP"]
    }

    total = 0
    range_exceed = 0
    pairwise_exceed = {group: 0 for group in ["As", "AFP", "BP"]}
    for as_indices in itertools.combinations(range(n), 3):
        remaining_after_as = positions - set(as_indices)
        for afp_indices in itertools.combinations(sorted(remaining_after_as), 3):
            remaining_after_afp = remaining_after_as - set(afp_indices)
            for aefp_indices in itertools.combinations(sorted(remaining_after_afp), 3):
                bp_indices = tuple(sorted(remaining_after_afp - set(aefp_indices)))
                means = {
                    "As": float(values[list(as_indices)].mean()),
                    "AFP": float(values[list(afp_indices)].mean()),
                    "AEFP": float(values[list(aefp_indices)].mean()),
                    "BP": float(values[list(bp_indices)].mean()),
                }
                total += 1
                if max(means.values()) - min(means.values()) >= observed_range - 1e-12:
                    range_exceed += 1
                for comparator in pairwise_exceed:
                    difference = abs(means["AEFP"] - means[comparator])
                    if difference >= observed_pairwise[comparator] - 1e-12:
                        pairwise_exceed[comparator] += 1

    pair_rows = []
    raw_ps = {}
    for comparator in ["As", "AFP", "BP"]:
        p_value = (pairwise_exceed[comparator] + 1) / (total + 1)
        raw_ps[comparator] = p_value
        pair_rows.append(
            {
                "Test": f"AEFP vs {comparator} (two-sided)",
                "ObservedAbsoluteDifference": observed_pairwise[comparator],
                "RawExactP": p_value,
            }
        )

    ranked = sorted(raw_ps, key=raw_ps.get)
    previous = 0.0
    for rank, group in enumerate(ranked):
        adjusted = min(1.0, (len(ranked) - rank) * raw_ps[group])
        adjusted = max(previous, adjusted)
        previous = adjusted
        for row in pair_rows:
            if row["Test"].startswith(f"AEFP vs {group} "):
                row["HolmAdjustedP"] = adjusted

    pair_rows.append(
        {
            "Test": "Any artificial-treatment difference (range)",
            "ObservedAbsoluteDifference": observed_range,
            "RawExactP": (range_exceed + 1) / (total + 1),
            "HolmAdjustedP": np.nan,
        }
    )
    result = pd.DataFrame(pair_rows)
    result.insert(0, "PermutationsEnumerated", total)
    result.insert(
        1,
        "ObservedGroupMeans",
        ";".join(f"{group}={observed_means[group]:.6f}" for group in ARTIFICIAL),
    )
    return result


def clr_distance(relative: np.ndarray) -> np.ndarray:
    pseudo = relative + 0.5
    clr = np.log(pseudo / pseudo.sum(axis=1, keepdims=True))
    clr -= clr.mean(axis=1, keepdims=True)
    return np.sqrt(((clr[:, None, :] - clr[None, :, :]) ** 2).sum(axis=2))


def permanova(
    distance: np.ndarray,
    groups: np.ndarray,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    labels = np.asarray(groups)
    n = len(labels)
    unique = np.unique(labels)
    total_ss = float((distance[np.triu_indices(n, 1)] ** 2).sum() / n)

    def statistic(current_labels: np.ndarray) -> tuple[float, float, float]:
        within_ss = 0.0
        for group in unique:
            indices = np.flatnonzero(current_labels == group)
            if len(indices) > 1:
                block = distance[np.ix_(indices, indices)]
                within_ss += float((block[np.triu_indices(len(indices), 1)] ** 2).sum() / len(indices))
        between_ss = total_ss - within_ss
        df_between = len(unique) - 1
        df_within = n - len(unique)
        f_value = (between_ss / df_between) / (within_ss / df_within)
        r2 = between_ss / total_ss
        return f_value, r2, within_ss

    observed_f, observed_r2, observed_within = statistic(labels)
    exceed = 0
    for _ in range(N_PERM):
        permuted = rng.permutation(labels)
        permuted_f, _, _ = statistic(permuted)
        if permuted_f >= observed_f - 1e-12:
            exceed += 1
    p_value = (exceed + 1) / (N_PERM + 1)
    return observed_f, observed_r2, p_value


def welch_p(values: np.ndarray, groups: np.ndarray) -> float:
    unique = [group for group in GROUP_ORDER if np.any(groups == group)]
    arrays = [values[groups == group] for group in unique]
    if any(len(array) < 2 for array in arrays):
        return np.nan
    return float(stats.f_oneway(*arrays, equal_var=False).pvalue)


def leave_one_out(
    domain: str,
    relative: np.ndarray,
    metadata: pd.DataFrame,
    alpha: pd.DataFrame,
) -> pd.DataFrame:
    rng = np.random.default_rng(SEED + (1 if domain == "16S" else 2))
    rows = []
    for drop_position in range(len(metadata)):
        keep = np.setdiff1d(np.arange(len(metadata)), [drop_position])
        dropped_sample = metadata.iloc[drop_position]["Sample"]
        subset_meta = metadata.iloc[keep].reset_index(drop=True)
        subset_relative = relative[keep]

        distances = reference_distances(subset_relative, subset_meta)
        means = {}
        for group in ARTIFICIAL:
            group_samples = subset_meta.loc[
                subset_meta["Composition"].eq(group), "Sample"
            ]
            means[group] = float(distances.loc[group_samples].mean())
        ordered = sorted(means, key=means.get)
        aefp_rank = ordered.index("AEFP") + 1
        nearest = ordered[0]
        aefp_minus_nearest = (
            0.0 if nearest == "AEFP" else means["AEFP"] - means[nearest]
        )

        labels = subset_meta["Composition"].to_numpy()
        bray = bray_curtis(subset_relative)
        aitchison = clr_distance(subset_relative)
        _, bray_r2, bray_p = permanova(bray, labels, rng)
        _, aitchison_r2, aitchison_p = permanova(aitchison, labels, rng)

        alpha_subset = alpha.loc[
            alpha["Sample"].isin(subset_meta["Sample"])
        ].copy()
        alpha_groups = alpha_subset["Composition"].to_numpy()
        row = {
            "Domain": domain,
            "DroppedSample": dropped_sample,
            "DroppedGroup": metadata.iloc[drop_position]["Composition"],
            "DroppedReplicate": int(metadata.iloc[drop_position]["Replicate"]),
            "ClosestArtificial": nearest,
            "AEFPRankAmongArtificial": aefp_rank,
            "AEFPMinusNearestDistance": aefp_minus_nearest,
            "BrayR2": bray_r2,
            "BrayP": bray_p,
            "AitchisonR2": aitchison_r2,
            "AitchisonP": aitchison_p,
        }
        for metric in ["Observed", "Shannon", "Simpson"]:
            row[f"Alpha{metric}P"] = welch_p(
                alpha_subset[metric].to_numpy(), alpha_groups
            )
        for group in ARTIFICIAL:
            row[f"Distance_{group}"] = means[group]
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_loo(loo: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for domain, subset in loo.groupby("Domain", sort=False):
        closest_counts = subset["ClosestArtificial"].value_counts()
        rank_counts = subset["AEFPRankAmongArtificial"].value_counts()
        rows.append(
            {
                "Domain": domain,
                "LeaveOneOutRuns": len(subset),
                "AEFPClosestRuns": int(closest_counts.get("AEFP", 0)),
                "AEFPClosestProportion": float(closest_counts.get("AEFP", 0) / len(subset)),
                "AEFPRank1Runs": int(rank_counts.get(1, 0)),
                "AEFPRank2Runs": int(rank_counts.get(2, 0)),
                "AEFPRank3Runs": int(rank_counts.get(3, 0)),
                "AEFPRank4Runs": int(rank_counts.get(4, 0)),
                "BraySignificantRuns": int((subset["BrayP"] < 0.05).sum()),
                "AitchisonSignificantRuns": int((subset["AitchisonP"] < 0.05).sum()),
                "ObservedSignificantRuns": int((subset["AlphaObservedP"] < 0.05).sum()),
                "ShannonSignificantRuns": int((subset["AlphaShannonP"] < 0.05).sum()),
                "SimpsonSignificantRuns": int((subset["AlphaSimpsonP"] < 0.05).sum()),
                "BrayR2Min": float(subset["BrayR2"].min()),
                "BrayR2Max": float(subset["BrayR2"].max()),
                "BrayPmax": float(subset["BrayP"].max()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    output = project_root / "03_结果" / "06_稳定性与参照区间"
    output.mkdir(parents=True, exist_ok=True)

    sheet = read_sheet(project_root / "01_数据" / "sample_sheet.csv")
    primary = sheet.loc[sheet["Primary5"]].reset_index(drop=True)
    plot_counts = primary.groupby("Composition")["PlotRecordID"].nunique()
    expected_plot_counts = pd.Series({group: 3 for group in GROUP_ORDER})
    if not plot_counts.sort_index().equals(expected_plot_counts.sort_index()):
        raise ValueError(
            "Primary analysis must contain three unique plot records per group; "
            f"observed: {plot_counts.to_dict()}"
        )
    samples = primary["Sample"].tolist()

    all_group_rows = []
    all_difference_rows = []
    all_exact_rows = []
    all_loo = []
    for domain in ["16S", "ITS"]:
        relative = load_relative_counts(project_root, domain, samples)
        rng = np.random.default_rng(SEED + (100 if domain == "16S" else 200))
        group_rows, difference_rows = bootstrap_reference(relative, primary, rng)
        group_rows.insert(0, "Domain", domain)
        difference_rows.insert(0, "Domain", domain)
        exact = exact_label_permutation(relative, primary)
        exact.insert(0, "Domain", domain)

        alpha = pd.read_csv(
            project_root
            / "03_结果"
            / "04_ASV综合分析"
            / f"alpha_samples_{domain}_primary.csv"
        )
        loo = leave_one_out(domain, relative, primary, alpha)

        all_group_rows.append(group_rows)
        all_difference_rows.append(difference_rows)
        all_exact_rows.append(exact)
        all_loo.append(loo)

    bootstrap_groups = pd.concat(all_group_rows, ignore_index=True)
    bootstrap_differences = pd.concat(all_difference_rows, ignore_index=True)
    exact = pd.concat(all_exact_rows, ignore_index=True)
    loo = pd.concat(all_loo, ignore_index=True)
    loo_summary = summarize_loo(loo)

    bootstrap_groups.to_csv(output / "bootstrap_group_distance.csv", index=False)
    bootstrap_differences.to_csv(
        output / "bootstrap_pairwise_difference.csv", index=False
    )
    exact.to_csv(output / "exact_label_permutation.csv", index=False)
    loo.to_csv(output / "leave_one_out_influence.csv", index=False)
    loo_summary.to_csv(output / "leave_one_out_summary.csv", index=False)

    metadata = pd.DataFrame(
        [
            {"Parameter": "RandomSeed", "Value": SEED},
            {"Parameter": "BootstrapIterations", "Value": N_BOOT},
            {"Parameter": "LeaveOneOutPermutations", "Value": N_PERM},
            {
                "Parameter": "BootstrapUnit",
                "Value": "Stratified resampling of plot-level records within each treatment; Natural centroid resampled jointly",
            },
            {
                "Parameter": "ExactPermutationUnit",
                "Value": "Treatment labels exchanged among 12 artificial-treatment plot records",
            },
            {
                "Parameter": "PrimaryN",
                "Value": "15 plot records = 5 groups x 3 plot records",
            },
        ]
    )
    metadata.to_csv(output / "analysis_parameters.csv", index=False)

    print(bootstrap_groups.to_string(index=False))
    print()
    print(bootstrap_differences.to_string(index=False))
    print()
    print(exact.to_string(index=False))
    print()
    print(loo_summary.to_string(index=False))
    (output / "COMPLETE.txt").write_text(
        "Reference-distance bootstrap, exact label permutation, and leave-one-out sensitivity completed.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
