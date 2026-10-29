# 多数据集框架验证复现状态（审稿修订）

日期：2026-10-29

## 本轮重跑

- 使用交付脚本从原始公共数据重新生成主分析与标签置换分析；
- 主分析：32 claims、176 planned/interpretable specifications；
- 标签置换：400 claim evaluations，嵌套于 80 个数据集—置换组合；
- 观测标签和阴性对照的 PERMANOVA 内部置换均为 999 次；
- 随机种子固定为 20261027。

## 统计修订

- 所有 32 个公共 claim 的 planned 与 interpretable specification 数均为 176，
  缺失规格为 0；
- majority、strict 和 claimstab 在标签置换零假设下均为 0/400 个支持判定；
- 该结果仅描述当前相关评估集合，不解释为 400 个独立试验中的零假阳性率；
- `soilrep` 技术重复已聚合为 24 个独立微宇宙；
- `atlas1006` 只使用 `time == 0` 的 1006 人。

## 输出一致性

- `main/claims.csv`、`main/endpoints.csv`、`main/reconstruction.csv` 已替换；
- `permutation/claims.csv`、`permutation/endpoints.csv` 已替换；
- `summary/permutation_support_summary.csv` 替代旧的
  `permutation_false_support.csv`；
- `framework_comparison.csv` 已包含 planned、testable、missing 和 coverage
  字段；
- `claim_stability_matrix.csv` 已包含 specification coverage、manual
  override 和 reason 字段。

## 结论

审稿意见涉及的置换分辨率、嵌套结构、缺失规格和证据分级操作化已经落实到
脚本、结果表和稿件。仍不能把 0/400 写成零错误率，也不能把 claimstab 写成
优于严格规则的二元分类器。
