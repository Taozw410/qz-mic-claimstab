from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent / "03_结果" / "05_16S差异丰度"
OUT = ROOT
OUT.mkdir(parents=True, exist_ok=True)

aldex = pd.read_csv(ROOT / "ALDEx2_pairwise_vs_natural.csv")
ancom = pd.read_csv(ROOT / "ANCOMBC2_pairwise.csv")

groups = ["As", "AFP", "AEFP", "BP"]
rows = []
summary = []
for group in groups:
    aldex_group = aldex.loc[aldex["Contrast"] == f"{group} vs Natural"].copy()
    aldex_group["ALDEx2Significant"] = (
        (aldex_group["we.eBH"] < 0.05) & (aldex_group["effect"].abs() > 1)
    )
    ancom_group = ancom[["taxon", f"lfc_Composition{group}", f"q_Composition{group}",
                         f"passed_ss_Composition{group}", f"diff_robust_Composition{group}"]].copy()
    ancom_group = ancom_group.rename(
        columns={
            "taxon": "Genus",
            f"lfc_Composition{group}": "ANCOMBC2LogFoldChange",
            f"q_Composition{group}": "ANCOMBC2Q",
            f"passed_ss_Composition{group}": "ANCOMBC2PassedSensitivity",
            f"diff_robust_Composition{group}": "ANCOMBC2Significant",
        }
    )
    merged = aldex_group.merge(ancom_group, on="Genus", how="outer")
    merged["Contrast"] = f"{group} vs Natural"
    merged["ConsensusSignificant"] = (
        merged["ALDEx2Significant"].fillna(False)
        & merged["ANCOMBC2Significant"].fillna(False)
    )
    rows.append(merged)
    summary.append(
        {
            "Contrast": f"{group} vs Natural",
            "ALDEx2Hits": int(merged["ALDEx2Significant"].fillna(False).sum()),
            "ANCOMBC2RobustHits": int(merged["ANCOMBC2Significant"].fillna(False).sum()),
            "ConsensusHits": int(merged["ConsensusSignificant"].sum()),
        }
    )

combined = pd.concat(rows, ignore_index=True)
combined.to_csv(OUT / "ALDEx2_ANCOMBC2_consensus_all.csv", index=False)
combined.loc[combined["ConsensusSignificant"]].to_csv(
    OUT / "confident_genus_consensus.csv", index=False
)
pd.DataFrame(summary).to_csv(OUT / "consensus_summary.csv", index=False)
print(pd.DataFrame(summary).to_string(index=False))
