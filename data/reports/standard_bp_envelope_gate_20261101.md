# 2026-11-01 非人体开发波形的离线包络弃判

输入为 `standard_bp_development_manifest_20261101.json` 所列的 7 次启动。`bp_envelope_gate.py` 先核对已验证波形的 SHA256 并严格解码，再调用现有 `bp_oscillogram_study.analyze()`；以 10 mmHg 分箱候选为主，同时保存 5 mmHg 基线结果。它不计算或输出 SBP/DBP，所有轮次的 `bp_output_allowed=false`、`bp_estimate_mmhg=null`。完整逐轮原因和输入哈希见同名 JSON，可运行 `python 'blood pressure monitor/tools/bp_envelope_gate.py'` 复算。

| 面板档位 | 完整波形 | 10 mmHg 包络判定 | 解释 |
| --- | --- | --- | --- |
| 120/80（四轮） | 是 | 四轮 `analyzable_candidate` | 前三轮参与过 10 mmHg 规则选择；新轮采后零点变化，均只作开发性候选 |
| 150/100（一轮） | 是 | `analyzable_candidate` | 同属规则选择数据 |
| 200/150（首次） | 否 | `abstain` | 12 秒内未升压，没有完整导出 |
| 200/150（重试） | 是 | `abstain` | 170 mmHg 上界原为 150/100 设定；本轮高度和面积包络均不完整，稳健性也未通过 |

`analyzable_candidate` 仅表示在已声明的开发性筛查下，高度与面积包络都为 `diagnostic_only` 且稳健性为 `pass`。它不验证面板 SBP/DBP，也不授权固件报告血压。200/150 的 170 mmHg 结果仅为既有边界下的失败诊断；不能看过波形后扩大上界，再把这轮改判通过。

压力链的 Static Pressure 多点标定已经完成，当前系数 `82.326/-19.887`。本轮 190/77 的主要疑点是固件固定 80..100 mmHg MAP 搜索及固定补偿，而不是约 1 mmHg 量级的静态点残差。此离线门槛不修改固件 `valid` 字段；在其经过独立数据验证并完成安全审核前，设备上的 `valid=1` 仍须按开发输出解释。
