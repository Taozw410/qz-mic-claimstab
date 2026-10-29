from __future__ import annotations

from pathlib import Path

import pandas as pd


def fmt(value: float, digits: int = 3) -> str:
    if pd.isna(value):
        return "NA"
    if value == 0:
        return "0"
    if abs(value) < 0.001:
        return f"{value:.1e}"
    return f"{value:.{digits}f}"


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    result_root = project_root / "03_结果"
    asv_dir = result_root / "04_ASV综合分析"
    stability_dir = result_root / "06_稳定性与参照区间"
    da_dir = result_root / "05_16S差异丰度"
    its_da_dir = result_root / "11_ITS差异丰度"
    output = result_root / "00_ASV结果总表"
    output.mkdir(parents=True, exist_ok=True)

    rows = []
    loo = pd.read_csv(stability_dir / "leave_one_out_summary.csv").set_index("Domain")

    for domain in ["16S", "ITS"]:
        alpha = pd.read_csv(asv_dir / f"alpha_omnibus_{domain}_primary.csv")
        alpha_sensitivity = pd.read_csv(
            asv_dir / f"alpha_omnibus_{domain}_sensitivity.csv"
        )
        for index, row in alpha.iterrows():
            metric = row["Metric"]
            sensitivity_p = float(
                alpha_sensitivity.loc[alpha_sensitivity["Metric"].eq(metric), "P"].iloc[0]
            )
            significant_loo = int(loo.loc[domain, f"{metric}SignificantRuns"])
            if domain == "16S" and metric == "Observed":
                evidence = "supported"
                note = f"LOO {significant_loo}/15; 18-sample sensitivity P={fmt(sensitivity_p)}"
            elif domain == "ITS" and metric == "Simpson" and sensitivity_p < 0.05:
                evidence = "insufficient"
                note = (
                    f"LOO {significant_loo}/15; 18-sample sensitivity P={fmt(sensitivity_p)} "
                    "depends on the unassigned group"
                )
            else:
                evidence = "insufficient"
                note = f"LOO {significant_loo}/15; 18-sample sensitivity P={fmt(sensitivity_p)}"
            rows.append(
                {
                    "Section": "Alpha diversity",
                    "Domain": domain,
                    "Outcome": metric,
                    "N_primary": 15,
                    "Estimate": float(row["WelchF"]),
                    "CI_low": None,
                    "CI_high": None,
                    "P": float(row["P"]),
                    "Sensitivity": note,
                    "Evidence": evidence,
                    "Source": f"03_结果/04_ASV综合分析/alpha_omnibus_{domain}_primary.csv",
                }
            )

        beta = pd.read_csv(asv_dir / f"beta_{domain}_primary.csv")
        beta_sensitivity = pd.read_csv(asv_dir / f"beta_{domain}_sensitivity.csv")
        for _, row in beta.iterrows():
            metric = row["Metric"]
            sens = beta_sensitivity.loc[beta_sensitivity["Metric"].eq(metric)].iloc[0]
            if metric == "Bray-Curtis":
                note = (
                    f"18-sample R2={fmt(float(sens['R2']))}, P={fmt(float(sens['P']))}; "
                    f"LOO significant {int(loo.loc[domain, 'BraySignificantRuns'])}/15"
                )
            else:
                note = (
                    f"18-sample R2={fmt(float(sens['R2']))}, P={fmt(float(sens['P']))}; "
                    f"LOO significant {int(loo.loc[domain, 'AitchisonSignificantRuns'])}/15"
                )
            rows.append(
                {
                    "Section": "Beta composition",
                    "Domain": domain,
                    "Outcome": metric,
                    "N_primary": 15,
                    "Estimate": float(row["R2"]),
                    "CI_low": None,
                    "CI_high": None,
                    "P": float(row["P"]),
                    "Sensitivity": note,
                    "Evidence": "supported",
                    "Source": f"03_结果/04_ASV综合分析/beta_{domain}_primary.csv",
                }
            )

    reference = pd.read_csv(stability_dir / "bootstrap_group_distance.csv")
    exact = pd.read_csv(stability_dir / "exact_label_permutation.csv")
    for domain in ["16S", "ITS"]:
        domain_reference = reference.loc[reference["Domain"].eq(domain)].set_index(
            "Composition"
        )
        range_p = float(
            exact.loc[
                exact["Domain"].eq(domain)
                & exact["Test"].str.startswith("Any artificial-treatment"),
                "RawExactP",
            ].iloc[0]
        )
        aefp = domain_reference.loc["AEFP"]
        rows.append(
            {
                "Section": "Natural reference",
                "Domain": domain,
                "Outcome": "AEFP distance to natural centroid",
                "N_primary": 15,
                "Estimate": float(aefp["ObservedMeanDistance"]),
                "CI_low": float(aefp["CI2.5"]),
                "CI_high": float(aefp["CI97.5"]),
                "P": range_p,
                "Sensitivity": (
                    f"bootstrap closest probability={fmt(float(aefp['ProbabilityClosest']))}; "
                    f"LOO closest {int(loo.loc[domain, 'AEFPClosestRuns'])}/15"
                ),
                "Evidence": (
                    "descriptive only"
                    if domain == "ITS"
                    else "no AEFP advantage"
                ),
                "Source": "03_结果/06_稳定性与参照区间/bootstrap_group_distance.csv",
            }
        )

    concordance = pd.read_csv(asv_dir / "domain_concordance_global_and_within.csv")
    for _, row in concordance.iterrows():
        rows.append(
            {
                "Section": "Domain concordance",
                "Domain": "16S vs ITS",
                "Outcome": row["Test"],
                "N_primary": 15,
                "Estimate": float(row["MantelSpearman"]),
                "CI_low": None,
                "CI_high": None,
                "P": float(row["MantelP"]),
                "Sensitivity": (
                    f"Procrustes r={fmt(float(row['ProcrustesCorrelation']))}, "
                    f"P={fmt(float(row['ProcrustesP']))}"
                    if pd.notna(row["ProcrustesCorrelation"])
                    else "within-treatment Mantel only"
                ),
                "Evidence": (
                    "supported"
                    if row["Test"] == "All primary samples"
                    else "insufficient"
                ),
                "Source": "03_结果/04_ASV综合分析/domain_concordance_global_and_within.csv",
            }
        )

    for domain, directory in [("16S", da_dir), ("ITS", its_da_dir)]:
        consensus = pd.read_csv(directory / "consensus_summary.csv")
        for _, row in consensus.iterrows():
            rows.append(
                {
                    "Section": "Differential abundance",
                    "Domain": domain,
                    "Outcome": row["Contrast"],
                    "N_primary": 15,
                    "Estimate": float(row["ConsensusHits"]),
                    "CI_low": None,
                    "CI_high": None,
                    "P": None,
                    "Sensitivity": (
                        f"ALDEx2={int(row['ALDEx2Hits'])}; "
                        f"ANCOM-BC2 robust={int(row['ANCOMBC2RobustHits'])}"
                    ),
                    "Evidence": (
                        "exploratory"
                        if row["ConsensusHits"] > 0
                        else "no consensus"
                    ),
                    "Source": (
                        f"03_结果/{directory.name}/consensus_summary.csv"
                    ),
                }
            )

    rows.extend(
        [
            {
                "Section": "Data availability",
                "Domain": "Both",
                "Outcome": "Absolute microbial abundance",
                "N_primary": 15,
                "Estimate": None,
                "CI_low": None,
                "CI_high": None,
                "P": None,
                "Sensitivity": (
                    "No matched Cq, standard curve, or copy-number records in the qPCR sheet"
                ),
                "Evidence": "not analyzable",
                "Source": "../outputs/QZ-mic-data-master/QZ_mic_master_crosswalk.xlsx",
            },
            {
                "Section": "Data availability",
                "Domain": "ITS",
                "Outcome": "Fungal taxonomic assignment",
                "N_primary": 15,
                "Estimate": 1265,
                "CI_low": None,
                "CI_high": None,
                "P": None,
                "Sensitivity": (
                    "UNITE v10.0 two-run consensus; 2,481/2,481 to Fungi; "
                    "1,265 genera and 687 species hypotheses"
                ),
                "Evidence": "available",
                "Source": "03_结果/07_ITS_UNITE分类/taxonomy_rank_counts.csv",
            },
            {
                "Section": "Estimability",
                "Domain": "16S + ITS",
                "Outcome": "Co-occurrence network as ecological interaction",
                "N_primary": 15,
                "Estimate": 0.06,
                "CI_low": None,
                "CI_high": None,
                "P": None,
                "Sensitivity": "3 plot records per treatment against 50 nodes",
                "Evidence": "not estimable",
                "Source": "03_结果/02_网络可估性/network_estimability.csv",
            },
        ]
    )

    table = pd.DataFrame(rows)
    table.to_csv(output / "key_results.csv", index=False)

    markdown = """# 论文2 ASV分析结果总表

本目录是论文2当前唯一的结果入口。`01_门水平初步`仅保留为历史敏感性记录，
不得再作为主结果引用。主分析使用5组15个小区层测序记录，每组3个记录；
样名与`01_数据/sample_sheet.csv`中的`PlotRecordID`一一对应。原始组23身份
未确认，只用于18样品敏感性分析。`T1-1/T1-2/T1-3`等已由用户确认是正式田间
随机排列号；田间“区组”的数值化归属仍未补齐，因此在拿到区组定义前不得增加
区组固定效应或做区组配对检验。

## 可以写入主结果的结论

1. 16S与ITS的ASV组成均存在处理间差异：Bray-Curtis PERMANOVA分别为
   R²=0.415、P=0.0002和R²=0.469、P=0.0002，组间离散度均不显著；
   Aitchison也得到同方向结果。逐一剔除任一主小区记录后，两个域、两种距离的
  PERMANOVA均保持P<0.05。
2. 16S的观测ASV数存在组间差异（Welch P=0.00176，逐一剔除15/15均P<0.05），
   但Shannon与Simpson没有一致差异。因此只能写“观测丰富度不同”，不能写
   “总体α多样性提高或降低”。
3. ITS的Observed、Shannon和Simpson在15个小区记录的主分析中均无差异证据。18样品
  敏感性中Simpson的P=0.0436来自未分配组，不能改变主结论。
4. 两个域的全局距离矩阵相关（Mantel rho=0.675，P=0.0002；
   Procrustes r=0.626，P=0.0001），但同一处理内部的样本级相关不成立
   （Mantel rho=0.421，P=0.432）。可写“两域共同区分处理与天然参照”，
   不能写“两域在每个处理内同步波动”。

## 只能作为描述或探索的内容

1. ITS中AEFP的平均天然参照距离最小（0.615），但2万次分层bootstrap的
   95%区间为0.530–0.738，“排名第一”的概率仅0.643；对12个人工处理小区记录
   进行369,600次精确标签置换，总体P=0.871，AEFP与As、AFP、BP的两两
   Holm校正P均为1.000。逐一剔除小区记录时14/15次仍排第一，但剔除AFP的
   `20_3`后降为第二。正确表述是“AEFP显示最接近天然参照的描述性倾向，
   当前3个重复不足以确认组间排序”，不能写成强证据或“趋同”。
2. 16S中AEFP没有天然参照优势：描述均值排第三，精确总体P=0.444。
3. 16S和ITS属水平差异丰度均没有双工具共识。16S的As vs Natural仅有
   `Allorhizobium-Neorhizobium-Pararhizobium-Rhizobium`由ANCOM-BC2单独支持
   （log fold change=-1.760，q=0.0203），ALDEx2 Welch `we.eBH=0.791`。
   ITS有8个ANCOM-BC2单工具候选，但ALDEx2均不支持；提高到25%流行率后只剩5个。
   ANCOM-BC2明确报告每组n=3时方差估计不稳定，所有候选只能作为探索性结果。

## 当前不能分析

- 无与当前测序样品匹配的qPCR Cq或拷贝数，不能计算绝对丰度或微生物量。
- ITS已完成UNITE v10.0两轮一致分类、门/属组成描述和属水平双工具差异丰度；
  仍不能从分类表推断功能。
- 每处理仅3个小区层记录，旧网络有50个节点，样本/节点比0.06；网络不进入
  主结论，不能推断关键类群或生态互作。
- 单时间点、无完整密度梯度，不能推断时间演替或“高密度导致”的因果关系。

## 论文体量判断

- 当前数据足以支撑1篇以16S+ITS群落结构为核心的观察性论文。主线应是两域
  β组成均响应处理、全局响应相关但处理内不同步，以及AEFP天然参照距离的
  描述性真菌倾向。
- 当前数据不足以从同一批15个小区记录再独立支撑1篇完整的微生物机制论文。
  真菌分类已补齐，但它仍使用同一批样品；绝对丰度、功能验证和网络互作缺少
  可分析数据或可估性。这些内容只能作为第一篇论文的深化或边界讨论，不能拆成
  第二篇主论文。

## 唯一数字来源

逐项数值、区间、P值、证据等级和源文件见`key_results.csv`。表中`Source`
路径相对于论文2根目录。主要底层文件：

- `03_结果/04_ASV综合分析/alpha_*.csv`
- `03_结果/04_ASV综合分析/beta_*.csv`
- `03_结果/04_ASV综合分析/domain_concordance_global_and_within.csv`
- `03_结果/05_16S差异丰度/consensus_summary.csv`
- `03_结果/11_ITS差异丰度/consensus_summary.csv`
- `03_结果/12_两域差异丰度汇总/da_summary.csv`
- `03_结果/06_稳定性与参照区间/bootstrap_group_distance.csv`
- `03_结果/06_稳定性与参照区间/bootstrap_pairwise_difference.csv`
- `03_结果/06_稳定性与参照区间/exact_label_permutation.csv`
- `03_结果/06_稳定性与参照区间/leave_one_out_influence.csv`
- `03_结果/06_稳定性与参照区间/leave_one_out_summary.csv`
"""
    (output / "README.md").write_text(markdown, encoding="utf-8")
    print(f"Wrote {len(table)} result rows to {output}")


if __name__ == "__main__":
    main()
