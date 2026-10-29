# 分析脚本说明

运行环境：

```text
R: D:\bioenv\envs\riz16s\Lib\R\bin\Rscript.exe
Python: D:\bioenv\envs\riz16s\python.exe
```

运行前必须将 R 的 `bin\x64`、`bin` 和 conda `Library\bin` 加入 `PATH`。

脚本顺序：

1. `01_phylum_prelim.py`
   - 使用现有门水平表和α多样性表。
   - 生成论文五组主分析与六组敏感性结果。
2. `02_dada2_asv.R`
   - 完整串行 DADA2 流程参考脚本。
3. `02b_dada2_its.R`
   - ITS 单端 DADA2 实际运行脚本。
4. `02c_dada2_16s_chunk.R`
   - 16S 使用共同误差模型按样品分块去噪。
5. `02d_dada2_16s_combine.R`
   - 合并16S分块、统一去嵌合体并进行 SILVA 分类。
6. `03_asv_analysis.R`
   - ASV α/β多样性、参照距离和域间一致性。
7. `04_legacy_network_audit.py`
   - 旧网络矩阵完整性及可估性检查。
8. `05_16s_differential_abundance.R`
   - ALDEx2 与 ANCOM-BC2 属水平差异丰度。
9. `06_domain_concordance.py`
   - 全体与处理内细菌—真菌一致性。
10. `07_consensus_da.py`
    - 两种差异丰度工具的交集。
11. `08_asv_figures.py`
    - ASV α多样性、PCoA 和天然参照距离基础图。
12. `09_reference_bootstrap_loo.py`
    - 天然参照距离分层 bootstrap、精确处理标签置换、逐一剔除样品敏感性。
13. `10_reference_uncertainty_figure.py`
    - 生成带 bootstrap 区间的天然参照距离图。
14. `11_build_result_summary.py`
    - 汇总论文2当前可引用结果、证据等级和唯一来源。
15. `12_assign_its_unite.R`
    - 使用UNITE v10.0对ITS ASV进行DADA2分类。
16. `13_ingest_backfilled_metadata.py`
    - 读取回填后的唯一主表和燕麦生理指标，生成论文2小区映射及处理级植物数据核查。
17. `14_parse_block_layout.py`
    - 解析区块播种示意图及位置简称，核对69个位置与随机表。
18. `15_ingest_soil_nutrients.py`
    - 从`土壤养分结果.docx`提取长表，并核对土壤22/23/24与论文处理的身份。
19. `16_reconcile_its_taxonomy.py`
    - 比较两次UNITE分类，生成保守共识表、组水平门/属组成和差异审计。
20. `17_its_taxonomy_figures.py`
    - 绘制五个主分析处理的门和已分类属组成图。
21. `18_its_differential_abundance.R`
    - ITS属水平ALDEx2和ANCOM-BC2差异丰度，支持流行率阈值参数化。
22. `19_its_consensus_da.py`
    - 按Welch `we.eBH`和ANCOM-BC2 `diff_robust`生成两工具共识。
23. `20_build_da_summary.py`
    - 汇总16S与ITS差异丰度、单工具候选和ITS流行率敏感性。
24. `21_da_candidate_figure.py`
    - 绘制ANCOM-BC2单工具候选的效应量与95%区间。

在唯一主表更新后依次运行`13_ingest_backfilled_metadata.py`和
`14_parse_block_layout.py`，再运行`15_ingest_soil_nutrients.py`；前者重建
基础样品映射，第二个补充图中田块位置，最后一个生成土壤养分处理级数据。

UNITE参考库固定位置：

```text
D:\bioenv\envs\riz16s\share\unite\v10.0_2025-02-19\sh_general_release_dynamic_19.02.2025.fasta
```

ITS分类运行示例：

```text
Rscript 12_assign_its_unite.R \
  --input <ASCII路径下的asv_representative_sequences.fasta> \
  --reference D:/bioenv/envs/riz16s/share/unite/v10.0_2025-02-19/sh_general_release_dynamic_19.02.2025.fasta \
  --output-dir <ASCII输出目录> \
  --threads 8 \
  --min-boot 50
```

Windows R读取中文路径可能失败，因此输入和输出先使用ASCII临时目录，运行后再
由PowerShell复制到项目正式目录。

说明：脚本中的 `C:/Users/hthome/AppData/Local/Temp/qz_mic_paper2` 是本次分析的 ASCII 工作目录。正式重跑时应根据新环境修改输入和输出根路径，但不应改变随机种子、抽平深度或统计口径。

`09`–`11` 已改为直接读取论文2目录下的正式 ASV 与结果文件，不依赖 ASCII
临时目录。建议重跑顺序：

```text
03_asv_analysis.R
→ 05_16s_differential_abundance.R
→ 06_domain_concordance.py
→ 07_consensus_da.py
→ 09_reference_bootstrap_loo.py
→ 10_reference_uncertainty_figure.py
→ 11_build_result_summary.py
```

ITS分类复核顺序：

```text
12_assign_its_unite.R（独立运行两次）
→ 16_reconcile_its_taxonomy.py
→ 17_its_taxonomy_figures.py
```

ITS差异丰度顺序：

```text
18_its_differential_abundance.R
→ 19_its_consensus_da.py
→ 20_build_da_summary.py
→ 21_da_candidate_figure.py
```
