from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path("D:/CodexWork/QZ-mic/数据/原始数据")
OUT = Path("C:/Users/hthome/AppData/Local/Temp/qz_mic_paper2/out/network_audit")
OUT.mkdir(parents=True, exist_ok=True)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize_matrix(path: Path) -> dict[str, object]:
    matrix = pd.read_excel(path, header=None, engine="openpyxl")
    values = matrix.iloc[1:, 1:].apply(pd.to_numeric, errors="coerce").to_numpy()
    row_index, column_index = np.triu_indices(values.shape[0], 1)
    upper = values[row_index, column_index]
    edges = np.abs(upper) > 0.8
    nodes_with_edges = np.zeros(values.shape[0], dtype=bool)
    nodes_with_edges[row_index[edges]] = True
    nodes_with_edges[column_index[edges]] = True
    return {
        "File": path.name,
        "MatrixSize": values.shape[0],
        "EdgeThresholdAbsRGreaterThan": 0.8,
        "Edges": int(edges.sum()),
        "PositiveEdges": int((upper > 0.8).sum()),
        "NegativeEdges": int((upper < -0.8).sum()),
        "NodesWithEdges": int(nodes_with_edges.sum()),
        "MatrixNodes": int(values.shape[0]),
        "SHA256": file_hash(path),
        "ContentSHA256": hashlib.sha256(
            matrix.to_csv(index=False, header=False).encode("utf-8")
        ).hexdigest(),
    }


def main() -> None:
    files = sorted(ROOT.glob("物种相关性矩阵*.xls"))
    rows = [summarize_matrix(path) for path in files]
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "network_matrix_audit.csv", index=False)

    duplicated = (
        summary.groupby("ContentSHA256")["File"]
        .agg(list)
        .reset_index()
    )
    duplicated = duplicated.loc[duplicated["File"].map(len) > 1]
    duplicated.to_csv(OUT / "network_duplicate_files.csv", index=False)

    estimability = pd.DataFrame(
        [
            {
                "Domain": "16S",
                "SamplesPerTreatment": 3,
                "NodesInFile": 50,
                "SampleNodeRatio": 3 / 50,
                "InferenceStatus": "not_estimable_as_interaction_network",
                "Reason": "Only three independent samples per treatment; dense feature correlation is unstable.",
            },
            {
                "Domain": "ITS",
                "SamplesPerTreatment": 3,
                "NodesInFile": 50,
                "SampleNodeRatio": 3 / 50,
                "InferenceStatus": "not_estimable_as_interaction_network",
                "Reason": "Only three independent samples per treatment; dense feature correlation is unstable.",
            },
        ]
    )
    estimability.to_csv(OUT / "network_estimability.csv", index=False)
    print(OUT)


if __name__ == "__main__":
    main()
