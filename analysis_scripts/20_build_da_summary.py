from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
RESULT_ROOT = ROOT / "03_结果"
OUTPUT_DIR = RESULT_ROOT / "12_两域差异丰度汇总"

DOMAINS = {
    "16S": RESULT_ROOT / "05_16S差异丰度",
    "ITS": RESULT_ROOT / "11_ITS差异丰度",
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    candidate_rows = []
    for domain, directory in DOMAINS.items():
        summary = pd.read_csv(directory / "consensus_summary.csv")
        summary.insert(0, "Domain", domain)
        summary_rows.append(summary)

        combined = pd.read_csv(directory / "ALDEx2_ANCOMBC2_consensus_all.csv")
        candidates = combined.loc[
            combined["ALDEx2Significant"].fillna(False)
            | combined["ANCOMBC2Significant"].fillna(False)
        ].copy()
        candidates.insert(0, "Domain", domain)
        candidate_rows.append(candidates)

    summary = pd.concat(summary_rows, ignore_index=True)
    summary.to_csv(OUTPUT_DIR / "da_summary.csv", index=False)
    candidates = pd.concat(candidate_rows, ignore_index=True)

    its_sensitivity_path = DOMAINS["ITS"] / "prevalence25" / (
        "ALDEx2_ANCOMBC2_consensus_all.csv"
    )
    if its_sensitivity_path.exists():
        sensitive = pd.read_csv(its_sensitivity_path)
        robust_keys = set(
            zip(
                sensitive.loc[
                    sensitive["ANCOMBC2Significant"].eq(True), "Genus"
                ],
                sensitive.loc[
                    sensitive["ANCOMBC2Significant"].eq(True), "Contrast"
                ],
            )
        )
        candidates["PersistentAt25PercentPrevalence"] = candidates.apply(
            lambda row: (
                (row["Genus"], row["Contrast"]) in robust_keys
                if row["Domain"] == "ITS" and row["ANCOMBC2Significant"]
                else pd.NA
            ),
            axis=1,
        )
    candidates.to_csv(
        OUTPUT_DIR / "single_tool_candidates.csv", index=False
    )

    readme = """# 两域属水平差异丰度汇总

## 判据

- 输入：15个主分析样品，每组3个小区层记录。
- 使用未抽平整数计数。
- 两域均采用10%流行率过滤。
- ALDEx2使用Welch t检验，命中要求`we.eBH < 0.05`且`|effect| > 1`。
- ANCOM-BC2使用BH校正、结构零和伪计数敏感性，命中要求
  `diff_robust == TRUE`。
- 只有两种工具同时命中的属才记为“双工具共识”。

## 结果

两域均没有得到双工具共识属。ANCOM-BC2给出少量单工具稳健候选，但这些属在
ALDEx2中均未通过Welch BH与效应量联合门禁，因此只能作为探索性候选。

ITS在流行率阈值提高到25%后，仍有5个ANCOM-BC2候选保留，但同样没有ALDEx2
支持；3个10%阈值候选不再稳健。这个结果说明候选清单对流行率阈值和软件选择
都比较敏感。

## 解释

- 不写“某属在人工处理中显著增加或减少”。
- 如需提及候选属，必须同时说明ANCOM-BC2单工具、q值、效应方向、流行率过滤，
  以及ALDEx2不同意。
- 每组n=3时ANCOM-BC2明确警告方差估计不稳定。
- 相对丰度变化不等于绝对丰度变化；当前没有qPCR锚定。

## 文件

- `da_summary.csv`：两域、四个对比的工具命中数和共识数。
- `single_tool_candidates.csv`：所有单工具候选及ANCOM-BC2统计量。
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(summary.to_string(index=False))
    print(f"\nSingle-tool candidate rows: {len(candidates)}")


if __name__ == "__main__":
    main()
