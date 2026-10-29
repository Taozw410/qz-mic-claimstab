from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULT_DIR = ROOT / "03_结果" / "11_ITS差异丰度"
GROUPS = ["As", "AFP", "AEFP", "BP"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    input_dir = args.input_dir
    output_dir = args.output_dir or input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    aldex = pd.read_csv(input_dir / "ALDEx2_pairwise_vs_natural.csv")
    ancom = pd.read_csv(input_dir / "ANCOMBC2_pairwise.csv")
    if aldex["we.eBH"].isna().all():
        raise ValueError("ALDEx2 Welch expected BH values are missing")

    combined_rows = []
    summary_rows = []
    for group in GROUPS:
        contrast = f"{group} vs Natural"
        aldex_group = aldex.loc[aldex["Contrast"].eq(contrast)].copy()
        # The analysis uses ALDEx2 test='t', so the matching multiplicity field
        # is we.eBH (Welch expected BH), not wi.eBH.
        aldex_group["ALDEx2Significant"] = (
            (aldex_group["we.eBH"] < 0.05)
            & (aldex_group["effect"].abs() > 1)
        )
        ancom_columns = {
            "taxon": "Genus",
            f"lfc_Composition{group}": "ANCOMBC2LogFoldChange",
            f"q_Composition{group}": "ANCOMBC2Q",
            f"passed_ss_Composition{group}": "ANCOMBC2PassedSensitivity",
            f"diff_robust_Composition{group}": "ANCOMBC2Significant",
        }
        missing = sorted(set(ancom_columns) - set(ancom.columns))
        if missing:
            raise ValueError(f"Missing ANCOM-BC2 columns: {missing}")
        ancom_group = ancom[list(ancom_columns)].rename(columns=ancom_columns)
        merged = aldex_group.merge(ancom_group, on="Genus", how="outer")
        merged["Contrast"] = contrast
        merged["ConsensusSignificant"] = (
            merged["ALDEx2Significant"].fillna(False)
            & merged["ANCOMBC2Significant"].fillna(False)
        )
        combined_rows.append(merged)
        summary_rows.append(
            {
                "Contrast": contrast,
                "ALDEx2Hits": int(merged["ALDEx2Significant"].fillna(False).sum()),
                "ANCOMBC2RobustHits": int(
                    merged["ANCOMBC2Significant"].fillna(False).sum()
                ),
                "ConsensusHits": int(merged["ConsensusSignificant"].sum()),
            }
        )

    combined = pd.concat(combined_rows, ignore_index=True)
    combined.to_csv(output_dir / "ALDEx2_ANCOMBC2_consensus_all.csv", index=False)
    combined.loc[combined["ConsensusSignificant"]].to_csv(
        output_dir / "confident_genus_consensus.csv", index=False
    )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / "consensus_summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
