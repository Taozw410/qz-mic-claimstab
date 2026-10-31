from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import procrustes
from scipy.stats import f_oneway, spearmanr, ttest_ind
from statsmodels.stats.multitest import multipletests

sys.path.append(
    r"C:\Users\<local-user>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages"
)


ROOT = Path("D:/CodexWork/QZ-mic")
RAW = ROOT / "数据" / "原始数据"
OUT = Path("C:/Users/<local-user>/AppData/Local/Temp/qz_mic_paper2/out/prelim")
OUT.mkdir(parents=True, exist_ok=True)

GROUP_MAP = {
    "1": ("T1", "As", "High", True),
    "20": ("T6", "AFP", "High", True),
    "7": ("T7", "AEFP", "High", True),
    "22": ("T22", "BP", "Reference", True),
    "24": ("T23", "Natural", "Reference", True),
    "23": ("Unassigned", "Unassigned", "Unknown", False),
}
GROUP_ORDER = ["As", "AFP", "AEFP", "BP", "Natural", "Unassigned"]
PRIMARY_ORDER = ["As", "AFP", "AEFP", "BP", "Natural"]
COLORS = {
    "As": "#0072B2",
    "AFP": "#009E73",
    "AEFP": "#D55E00",
    "BP": "#E69F00",
    "Natural": "#CC79A7",
    "Unassigned": "#7F7F7F",
}
RNG_SEED = 20261023


def read_table(path: Path, sheet: str | int = 0, header: int | None = 0) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name=sheet, header=header, engine="openpyxl")
    except Exception:
        return pd.read_excel(path, sheet_name=sheet, header=header, engine="xlrd")


def build_metadata(samples: list[str]) -> pd.DataFrame:
    rows = []
    for sample in samples:
        group, rep = sample.split("_")
        treatment, composition, density, primary = GROUP_MAP[group]
        rows.append(
            {
                "Sample": sample,
                "RawGroup": group,
                "Treatment": treatment,
                "Composition": composition,
                "Density": density,
                "Replicate": int(rep),
                "Primary5": primary,
            }
        )
    return pd.DataFrame(rows)


def bray_curtis(matrix: np.ndarray) -> np.ndarray:
    n = matrix.shape[0]
    out = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            denom = np.abs(matrix[i]).sum() + np.abs(matrix[j]).sum()
            value = np.abs(matrix[i] - matrix[j]).sum() / denom
            out[i, j] = out[j, i] = value
    return out


def gower_center(distance: np.ndarray) -> np.ndarray:
    n = distance.shape[0]
    centering = np.eye(n) - np.ones((n, n)) / n
    return -0.5 * centering @ (distance**2) @ centering


def pcoa(distance: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gower = gower_center(distance)
    eigenvalues, eigenvectors = np.linalg.eigh(gower)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    positive = eigenvalues > max(0, eigenvalues.max() * 1e-10)
    eigenvalues = eigenvalues[positive]
    eigenvectors = eigenvectors[:, positive]
    coords = eigenvectors * np.sqrt(eigenvalues)
    explained = eigenvalues / max(eigenvalues.sum(), 1e-12)
    return coords, explained


def permanova(
    distance: np.ndarray, labels: np.ndarray, permutations: int = 9999
) -> tuple[float, float, float]:
    def statistic(current_labels: np.ndarray) -> tuple[float, float]:
        groups = np.unique(current_labels)
        n = current_labels.size
        g = groups.size
        design = np.column_stack([(current_labels == group).astype(float) for group in groups])
        hat = design @ np.linalg.pinv(design.T @ design) @ design.T
        identity = np.eye(n)
        centered = gower_center(distance)
        total_ss = np.trace(centered)
        residual = (identity - hat) @ centered @ (identity - hat)
        within_ss = np.trace(residual)
        between_ss = total_ss - within_ss
        pseudo_f = (between_ss / (g - 1)) / (within_ss / (n - g))
        return float(pseudo_f), float(between_ss / total_ss)

    observed_f, observed_r2 = statistic(labels)
    rng = np.random.default_rng(RNG_SEED)
    exceed = 0
    for _ in range(permutations):
        permuted = rng.permutation(labels)
        candidate_f, _ = statistic(permuted)
        exceed += candidate_f >= observed_f
    return observed_f, observed_r2, float((exceed + 1) / (permutations + 1))


def dispersion_test(
    coordinates: np.ndarray, labels: np.ndarray, permutations: int = 9999
) -> tuple[float, float]:
    def distance_to_centroid(current: np.ndarray, current_labels: np.ndarray) -> np.ndarray:
        distances = np.zeros(current.shape[0])
        for group in np.unique(current_labels):
            mask = current_labels == group
            centroid = current[mask].mean(axis=0)
            distances[mask] = np.linalg.norm(current[mask] - centroid, axis=1)
        return distances

    def statistic(current_labels: np.ndarray) -> float:
        distances = distance_to_centroid(coordinates, current_labels)
        groups = np.unique(current_labels)
        grand = distances.mean()
        ss_between = sum(
            (current_labels == group).sum() * (distances[current_labels == group].mean() - grand) ** 2
            for group in groups
        )
        ss_within = sum(
            ((distances[current_labels == group] - distances[current_labels == group].mean()) ** 2).sum()
            for group in groups
        )
        return float((ss_between / (groups.size - 1)) / (ss_within / (distances.size - groups.size)))

    observed = statistic(labels)
    rng = np.random.default_rng(RNG_SEED)
    exceed = 0
    for _ in range(permutations):
        exceed += statistic(rng.permutation(labels)) >= observed
    return observed, float((exceed + 1) / (permutations + 1))


def permutation_mantel(x: np.ndarray, y: np.ndarray, permutations: int = 9999) -> tuple[float, float]:
    upper = np.triu_indices(x.shape[0], 1)

    def statistic(a: np.ndarray, b: np.ndarray) -> float:
        return float(spearmanr(a[upper], b[upper]).statistic)

    observed = statistic(x, y)
    rng = np.random.default_rng(RNG_SEED)
    exceed = 0
    for _ in range(permutations):
        permutation = rng.permutation(y.shape[0])
        exceed += statistic(x, y[np.ix_(permutation, permutation)]) >= observed
    return observed, float((exceed + 1) / (permutations + 1))


def permutation_procrustes(
    x: np.ndarray, y: np.ndarray, permutations: int = 9999
) -> tuple[float, float]:
    axes = min(4, x.shape[1], y.shape[1])
    x = x[:, :axes]
    y = y[:, :axes]

    def statistic(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
        _, _, disparity = procrustes(a, b)
        return float(disparity), float(1 - disparity)

    observed_disparity, observed_stat = statistic(x, y)
    rng = np.random.default_rng(RNG_SEED)
    exceed = 0
    for _ in range(permutations):
        _, candidate_stat = statistic(x, y[rng.permutation(y.shape[0])])
        exceed += candidate_stat >= observed_stat
    return observed_disparity, float((exceed + 1) / (permutations + 1))


def pairwise_tests(data: pd.DataFrame, metric: str, order: list[str]) -> pd.DataFrame:
    rows = []
    for left, right in itertools.combinations(order, 2):
        a = data.loc[data["Composition"] == left, metric].astype(float).to_numpy()
        b = data.loc[data["Composition"] == right, metric].astype(float).to_numpy()
        test = ttest_ind(a, b, equal_var=False)
        pooled = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
        effect = (a.mean() - b.mean()) / pooled if pooled > 0 else np.nan
        rows.append(
            {
                "Metric": metric,
                "Group1": left,
                "Group2": right,
                "Mean1": a.mean(),
                "Mean2": b.mean(),
                "Difference": a.mean() - b.mean(),
                "HedgesGLike": effect,
                "P": test.pvalue,
            }
        )
    result = pd.DataFrame(rows)
    result["Q_BH"] = multipletests(result["P"], method="fdr_bh")[1]
    return result


def load_phylum(domain: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    path = RAW / ("丰度表-16s.xls" if domain == "16S" else "丰度表-its.xls")
    table = read_table(path, sheet="OTU表")
    sample_columns = [column for column in table.columns[3:21]]
    counts = table[sample_columns].apply(pd.to_numeric, errors="raise")
    counts.index = table["Phylum"].astype(str)
    counts = counts.groupby(level=0).sum()
    samples = pd.DataFrame(counts.T)
    proportions = samples.div(samples.sum(axis=1), axis=0)
    return samples, proportions


def load_alpha(domain: str) -> pd.DataFrame:
    path = RAW / ("多样性指数表-16S.xls" if domain == "16S" else "多样性指数表-its.xls")
    alpha = read_table(path)
    alpha.columns = ["Sample", "Sobs", "Shannon", "Simpson", "ACE", "Chao", "Coverage"]
    return alpha


def analysis_subset(metadata: pd.DataFrame, primary_only: bool) -> pd.DataFrame:
    if primary_only:
        return metadata.loc[metadata["Primary5"]].reset_index(drop=True)
    return metadata.reset_index(drop=True)


def run_analysis(primary_only: bool) -> dict[str, pd.DataFrame]:
    metadata_all = build_metadata(
        [f"{group}_{rep}" for group in ["1", "20", "7", "22", "24", "23"] for rep in [1, 2, 3]]
    )
    metadata = analysis_subset(metadata_all, primary_only)
    order = PRIMARY_ORDER if primary_only else GROUP_ORDER
    suffix = "primary" if primary_only else "sensitivity"
    domain_results: dict[str, dict[str, object]] = {}
    alpha_summaries = []
    alpha_tests = []
    alpha_pairwise = []
    permanova_rows = []
    dispersion_rows = []
    pairwise_permanova = []
    reference_rows = []

    for domain in ["16S", "ITS"]:
        counts, proportions = load_phylum(domain)
        counts = counts.loc[metadata["Sample"]]
        proportions = proportions.loc[metadata["Sample"]]
        group_labels = metadata.set_index("Sample").loc[proportions.index, "Composition"]
        distance = bray_curtis(proportions.to_numpy())
        coords, explained = pcoa(distance)
        labels = metadata["Composition"].to_numpy()

        class_test = f_oneway(
            *[
                counts.loc[(metadata["Composition"] == group).to_numpy()].sum(axis=1).to_numpy()
                for group in order
            ]
        )
        f_value = float(class_test.statistic)
        p_value = float(class_test.pvalue)
        total = counts.sum(axis=1).to_numpy()
        grand = total.mean()
        ss_between = sum(
            (metadata["Composition"] == group).sum()
            * (total[labels == group].mean() - grand) ** 2
            for group in order
        )
        ss_total = ((total - grand) ** 2).sum()
        alpha_tests.append(
            {
                "Domain": domain,
                "Metric": "ClassifiedReads",
                "GroupCount": len(order),
                "F": f_value,
                "P": p_value,
                "Eta2": ss_between / ss_total if ss_total > 0 else np.nan,
            }
        )

        alpha = load_alpha(domain)
        alpha = metadata.merge(alpha, on="Sample", how="left", validate="one_to_one")
        for group in order:
            subset = alpha.loc[alpha["Composition"] == group]
            for metric in ["Sobs", "Shannon", "Simpson", "Coverage"]:
                alpha_summaries.append(
                    {
                        "Domain": domain,
                        "Composition": group,
                        "Metric": metric,
                        "N": len(subset),
                        "Mean": subset[metric].mean(),
                        "SD": subset[metric].std(ddof=1),
                        "SE": subset[metric].std(ddof=1) / math.sqrt(len(subset)),
                    }
                )
        for metric in ["Sobs", "Shannon", "Simpson", "Coverage"]:
            groups = [
                alpha.loc[alpha["Composition"] == group, metric].astype(float).to_numpy()
                for group in order
            ]
            test = f_oneway(*groups)
            grand = alpha[metric].astype(float).mean()
            ss_between = sum(len(group) * (group.mean() - grand) ** 2 for group in groups)
            ss_total = ((alpha[metric].astype(float) - grand) ** 2).sum()
            alpha_tests.append(
                {
                    "Domain": domain,
                    "Metric": metric,
                    "GroupCount": len(order),
                    "F": test.statistic,
                    "P": test.pvalue,
                    "Eta2": ss_between / ss_total if ss_total > 0 else np.nan,
                }
            )
            pairwise = pairwise_tests(alpha, metric, order)
            pairwise.insert(0, "Domain", domain)
            alpha_pairwise.append(pairwise)

        adonis_f, adonis_r2, adonis_p = permanova(distance, labels)
        dispersion_f, dispersion_p = dispersion_test(coords, labels)
        permanova_rows.append(
            {
                "Domain": domain,
                "Metric": "Bray-Curtis",
                "F": adonis_f,
                "R2": adonis_r2,
                "P": adonis_p,
                "DispersionF": dispersion_f,
                "DispersionP": dispersion_p,
                "PCoA1": explained[0],
                "PCoA2": explained[1] if len(explained) > 1 else np.nan,
            }
        )

        for left, right in itertools.combinations(order, 2):
            mask = np.isin(labels, [left, right])
            selected_distance = distance[np.ix_(mask, mask)]
            pair_f, pair_r2, pair_p = permanova(
                selected_distance, labels[mask], permutations=999
            )
            pairwise_permanova.append(
                {
                    "Domain": domain,
                    "Group1": left,
                    "Group2": right,
                    "F": pair_f,
                    "R2": pair_r2,
                    "P": pair_p,
                }
            )

        # Aitchison sensitivity on phylum proportions with additive zero replacement.
        pseudo = proportions.to_numpy() * 1_000_000 + 0.5
        closure = pseudo / pseudo.sum(axis=1, keepdims=True)
        clr = np.log(closure) - np.log(closure).mean(axis=1, keepdims=True)
        aitchison_distance = np.linalg.norm(clr[:, None, :] - clr[None, :, :], axis=2)
        aitchison_f, aitchison_r2, aitchison_p = permanova(aitchison_distance, labels)
        permanova_rows.append(
            {
                "Domain": domain,
                "Metric": "Aitchison",
                "F": aitchison_f,
                "R2": aitchison_r2,
                "P": aitchison_p,
                "DispersionF": np.nan,
                "DispersionP": np.nan,
                "PCoA1": np.nan,
                "PCoA2": np.nan,
            }
        )

        natural = proportions.groupby(group_labels).mean().loc["Natural"].to_numpy()
        centroids = proportions.groupby(group_labels).mean().loc[order]
        centroid_distance = bray_curtis(centroids.to_numpy())
        natural_index = order.index("Natural")
        for index, group in enumerate(order):
            mask = labels == group
            sample_distances = np.array(
                [
                    np.abs(row - natural).sum() / (np.abs(row).sum() + np.abs(natural).sum())
                    for row in proportions.loc[mask].to_numpy()
                ]
            )
            reference_rows.append(
                {
                    "Domain": domain,
                    "Composition": group,
                    "N": mask.sum(),
                    "CentroidDistanceToNatural": centroid_distance[index, natural_index],
                    "SampleMeanDistanceToNatural": sample_distances.mean(),
                    "SampleSE": sample_distances.std(ddof=1) / math.sqrt(len(sample_distances))
                    if len(sample_distances) > 1
                    else np.nan,
                }
            )

        domain_results[domain] = {
            "coords": coords,
            "explained": explained,
            "distance": distance,
            "proportions": proportions,
            "metadata": metadata,
        }

    pd.DataFrame(alpha_summaries).to_csv(OUT / f"alpha_group_summary_{suffix}.csv", index=False)
    pd.DataFrame(alpha_tests).to_csv(OUT / f"alpha_omnibus_{suffix}.csv", index=False)
    pd.concat(alpha_pairwise, ignore_index=True).to_csv(
        OUT / f"alpha_pairwise_{suffix}.csv", index=False
    )
    pd.DataFrame(permanova_rows).to_csv(OUT / f"beta_omnibus_{suffix}.csv", index=False)
    pairwise_permanova_df = pd.DataFrame(pairwise_permanova)
    pairwise_permanova_df["Q_BH"] = multipletests(
        pairwise_permanova_df["P"], method="fdr_bh"
    )[1]
    pairwise_permanova_df.to_csv(OUT / f"beta_pairwise_{suffix}.csv", index=False)
    pd.DataFrame(reference_rows).to_csv(
        OUT / f"natural_reference_distances_{suffix}.csv", index=False
    )

    x_distance = domain_results["16S"]["distance"]
    y_distance = domain_results["ITS"]["distance"]
    mantel_r, mantel_p = permutation_mantel(x_distance, y_distance)
    procrustes_disparity, procrustes_p = permutation_procrustes(
        domain_results["16S"]["coords"], domain_results["ITS"]["coords"]
    )
    pd.DataFrame(
        [
            {
                "N": len(metadata),
                "MantelSpearman": mantel_r,
                "MantelP": mantel_p,
                "ProcrustesDisparity": procrustes_disparity,
                "ProcrustesP": procrustes_p,
            }
        ]
    ).to_csv(OUT / f"domain_concordance_{suffix}.csv", index=False)

    # Plot alpha
    alpha_16 = load_alpha("16S").merge(metadata, on="Sample")
    alpha_its = load_alpha("ITS").merge(metadata, on="Sample")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), constrained_layout=True)
    for axis, data, title in zip(axes, [alpha_16, alpha_its], ["16S", "ITS"]):
        for group in order:
            values = data.loc[data["Composition"] == group, "Shannon"]
            axis.scatter(
                np.full(len(values), order.index(group)),
                values,
                color=COLORS[group],
                s=35,
                label=group,
            )
        axis.set_xticks(range(len(order)), order, rotation=30, ha="right")
        axis.set_ylabel("Shannon index")
        axis.set_title(f"{title} alpha diversity")
    fig.savefig(OUT / f"alpha_shannon_{suffix}.png", dpi=300)
    plt.close(fig)

    # Plot beta PCoA
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), constrained_layout=True)
    for axis, domain in zip(axes, ["16S", "ITS"]):
        data = domain_results[domain]
        coords = data["coords"]
        explained = data["explained"]
        for group in order:
            mask = data["metadata"]["Composition"].to_numpy() == group
            axis.scatter(
                coords[mask, 0],
                coords[mask, 1],
                color=COLORS[group],
                s=40,
                label=group,
            )
        axis.set_xlabel(f"PCoA1 ({explained[0]:.1%})")
        axis.set_ylabel(f"PCoA2 ({explained[1]:.1%})")
        axis.set_title(f"{domain} Bray-Curtis")
    axes[1].legend(frameon=False, bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.savefig(OUT / f"beta_pcoa_{suffix}.png", dpi=300)
    plt.close(fig)

    reference = pd.DataFrame(reference_rows)
    fig, ax = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
    plot_data = reference.loc[reference["Composition"] != "Natural"]
    for domain, marker in [("16S", "o"), ("ITS", "s")]:
        subset = plot_data.loc[plot_data["Domain"] == domain]
        ax.errorbar(
            subset["Composition"],
            subset["SampleMeanDistanceToNatural"],
            yerr=subset["SampleSE"],
            marker=marker,
            capsize=3,
            label=domain,
        )
    ax.set_ylabel("Bray-Curtis distance to natural centroid")
    ax.set_xlabel("Composition")
    ax.legend(frameon=False)
    ax.set_title("Distance to natural reference")
    fig.savefig(OUT / f"natural_reference_distance_{suffix}.png", dpi=300)
    plt.close(fig)

    # Sample-level domain concordance plot
    reference_wide = reference.pivot(
        index="Composition", columns="Domain", values="SampleMeanDistanceToNatural"
    ).loc[[group for group in order if group != "Natural"]]
    fig, ax = plt.subplots(figsize=(4.5, 4.5), constrained_layout=True)
    for group in reference_wide.index:
        ax.scatter(
            reference_wide.loc[group, "16S"],
            reference_wide.loc[group, "ITS"],
            color=COLORS[group],
            s=55,
        )
        ax.text(
            reference_wide.loc[group, "16S"],
            reference_wide.loc[group, "ITS"],
            f" {group}",
            va="center",
        )
    ax.set_xlabel("16S distance to natural")
    ax.set_ylabel("ITS distance to natural")
    ax.set_title("Domain concordance")
    fig.savefig(OUT / f"domain_reference_concordance_{suffix}.png", dpi=300)
    plt.close(fig)

    return {
        "alpha_summary": pd.DataFrame(alpha_summaries),
        "alpha_omnibus": pd.DataFrame(alpha_tests),
        "beta": pd.DataFrame(permanova_rows),
        "domain_concordance": pd.read_csv(OUT / f"domain_concordance_{suffix}.csv"),
    }


def main() -> None:
    metadata = build_metadata(
        [f"{group}_{rep}" for group in ["1", "20", "7", "22", "24", "23"] for rep in [1, 2, 3]]
    )
    metadata.to_csv(OUT / "sample_sheet.csv", index=False)
    primary = run_analysis(primary_only=True)
    sensitivity = run_analysis(primary_only=False)

    summary_lines = [
        "# Paper 2 preliminary phylum-level results",
        "",
        "## Scope",
        "",
        "- Primary set: five paper groups, 15 samples.",
        "- Sensitivity set: six sequence groups, 18 samples; raw group 23 is retained as unassigned.",
        "- Features: phylum-level relative abundance and existing alpha-diversity output.",
        "- PERMANOVA and dispersion tests use 9,999 permutations; pairwise tests use 999.",
        "- Bray-Curtis is primary; Aitchison is a sensitivity analysis.",
        "",
        "## Alpha omnibus",
        "",
        "```text",
        primary["alpha_omnibus"].to_string(index=False),
        "```",
        "",
        "## Beta",
        "",
        "```text",
        primary["beta"].to_string(index=False),
        "```",
        "",
        "## Domain concordance",
        "",
        "```text",
        primary["domain_concordance"].to_string(index=False),
        "```",
        "",
    ]
    (OUT / "preliminary_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"WROTE {OUT}")


if __name__ == "__main__":
    main()
