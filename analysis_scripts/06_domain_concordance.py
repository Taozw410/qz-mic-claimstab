from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import procrustes
from scipy.stats import spearmanr


ROOT = Path("C:/Users/hthome/AppData/Local/Temp/qz_mic_paper2")
OUT = ROOT / "out" / "domain_concordance"
OUT.mkdir(parents=True, exist_ok=True)
RNG_SEED = 20261023


def bray_curtis(matrix: np.ndarray) -> np.ndarray:
    n = matrix.shape[0]
    result = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            value = np.abs(matrix[i] - matrix[j]).sum() / (
                np.abs(matrix[i]).sum() + np.abs(matrix[j]).sum()
            )
            result[i, j] = result[j, i] = value
    return result


def pcoa(distance: np.ndarray) -> np.ndarray:
    n = distance.shape[0]
    centering = np.eye(n) - np.ones((n, n)) / n
    gower = -0.5 * centering @ (distance**2) @ centering
    eigenvalues, eigenvectors = np.linalg.eigh(gower)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    positive = eigenvalues > max(0, eigenvalues.max() * 1e-10)
    return eigenvectors[:, positive] * np.sqrt(eigenvalues[positive])


def mantel(x: np.ndarray, y: np.ndarray, permutations: int = 9999):
    upper = np.triu_indices(x.shape[0], 1)

    def statistic(a, b):
        return float(spearmanr(a[upper], b[upper]).statistic)

    observed = statistic(x, y)
    rng = np.random.default_rng(RNG_SEED)
    exceed = 0
    for _ in range(permutations):
        order = rng.permutation(y.shape[0])
        exceed += statistic(x, y[np.ix_(order, order)]) >= observed
    return observed, (exceed + 1) / (permutations + 1)


def procrustes_test(x: np.ndarray, y: np.ndarray, permutations: int = 9999):
    axes = min(4, x.shape[1], y.shape[1])
    x = x[:, :axes]
    y = y[:, :axes]

    def statistic(a, b):
        _, _, disparity = procrustes(a, b)
        return 1 - disparity

    observed = statistic(x, y)
    rng = np.random.default_rng(RNG_SEED)
    exceed = 0
    for _ in range(permutations):
        exceed += statistic(x, y[rng.permutation(y.shape[0])]) >= observed
    return observed, (exceed + 1) / (permutations + 1)


def within_group_distances(distance: np.ndarray, groups: list[str]) -> np.ndarray:
    values = []
    for group in sorted(set(groups)):
        indices = [index for index, value in enumerate(groups) if value == group]
        for left, right in itertools.combinations(indices, 2):
            values.append(distance[left, right])
    return np.asarray(values)


def within_group_test(
    x: np.ndarray, y: np.ndarray, groups: list[str], permutations: int = 9999
):
    x_values = within_group_distances(x, groups)
    y_values = within_group_distances(y, groups)
    observed = float(spearmanr(x_values, y_values).statistic)
    rng = np.random.default_rng(RNG_SEED)
    exceed = 0
    for _ in range(permutations):
        permuted = y.copy()
        for group in sorted(set(groups)):
            indices = np.asarray([index for index, value in enumerate(groups) if value == group])
            shuffled = indices.copy()
            rng.shuffle(shuffled)
            permuted[np.ix_(indices, indices)] = y[np.ix_(shuffled, shuffled)]
        exceed += float(spearmanr(x_values, within_group_distances(permuted, groups)).statistic) >= observed
    return observed, (exceed + 1) / (permutations + 1)


def load_domain(domain: str, samples: list[str]) -> np.ndarray:
    directory = ROOT / "out" / "asv" / ("338F_806R" if domain == "16S" else "ITS1F_ITS2R")
    table = pd.read_csv(directory / "asv_table.csv", index_col=0)
    counts = table[samples].T
    if domain == "16S":
        taxonomy = pd.read_csv(directory / "taxonomy_silva.csv", index_col="ASV")
        taxonomy = taxonomy.loc[counts.columns]
        chloroplast = taxonomy["Order"].fillna("").str.contains("Chloroplast", case=False)
        mitochondria = taxonomy["Family"].fillna("").str.contains("Mitochondria", case=False)
        counts = counts.loc[:, ~(chloroplast | mitochondria).to_numpy()]
    relative = counts.to_numpy(dtype=float)
    relative = relative / relative.sum(axis=1, keepdims=True)
    return relative


def main() -> None:
    metadata = pd.read_csv(ROOT / "out" / "prelim" / "sample_sheet.csv")
    metadata["Primary5"] = (
        metadata["Primary5"].astype(str).str.lower().isin(["true", "1", "yes"])
    )
    metadata = metadata.loc[metadata["Primary5"]].reset_index(drop=True)
    samples = metadata["Sample"].tolist()
    groups = metadata["Composition"].tolist()

    matrix_16 = load_domain("16S", samples)
    matrix_its = load_domain("ITS", samples)
    distance_16 = bray_curtis(matrix_16)
    distance_its = bray_curtis(matrix_its)

    mantel_r, mantel_p = mantel(distance_16, distance_its)
    procrustes_r, procrustes_p = procrustes_test(pcoa(distance_16), pcoa(distance_its))
    within_r, within_p = within_group_test(distance_16, distance_its, groups)

    result = pd.DataFrame(
        [
            {
                "Test": "All primary samples",
                "N": len(samples),
                "MantelSpearman": mantel_r,
                "MantelP": mantel_p,
                "ProcrustesCorrelation": procrustes_r,
                "ProcrustesP": procrustes_p,
            },
            {
                "Test": "Within treatment groups",
                "N": len(samples),
                "MantelSpearman": within_r,
                "MantelP": within_p,
                "ProcrustesCorrelation": np.nan,
                "ProcrustesP": np.nan,
            },
        ]
    )
    result.to_csv(OUT / "domain_concordance_global_and_within.csv", index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
