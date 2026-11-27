# 2026-11-01 离线包络分箱敏感性与下一批预设协议

## 本次只读比较

输入为 `capture_catalog_20261031.json` 中严格解码有效且未重复的 42 轮历史开发采集，以及 2026-11-01 四轮已验证的 Standard BP 开发采集。逐文件路径、SHA256、压力搜索上界和两个分箱结果保存在 `offline_bin_width_20261101.json`。历史轮次多缺面板标签；所有 46 轮都参与过方法开发，不是独立验证集。

使用 `bp_oscillogram_study.py` 原有的严格解码、原始电压脉搏提取、40 点压力阶跃隔离、峰值覆盖、拟合、留一压力箱稳定性筛查；只改变压力分箱宽度 5 或 10 mmHg。工具新增 `--bin-width {5,10}`，默认 5，以保留旧报告行为。历史轮次以首点压力是否达到 150 mmHg 选择搜索上界 130/170 mmHg；这只是回顾性分组规则，不是面板标签。今天三轮 120/80 使用上界 130，150/100 使用上界 170。

| 输入组 | 轮数 | 5 mmHg 高度/面积同时通过 | 10 mmHg 高度/面积同时通过 |
| --- | ---: | ---: | ---: |
| 历史去重开发采集 | 42 | 8 | 10 |
| 今天已知面板条件的规则选择采集 | 4 | 0 | 4 |

单独计数：历史组 5 mmHg 高度 11、面积 8，10 mmHg 高度 11、面积 10；今天四轮 5 mmHg 高度 1、面积 0，10 mmHg 高度 4、面积 4。10 mmHg 时今天三轮 120/80 的高度拟合峰分别为 95.00、99.47、98.57 mmHg；150/100 为 123.79 mmHg。这些均为同一传感器链的诊断候选峰，不能当作 BP Pump 2 的真实 MAP 或准确度证据。今天四轮用于选宽度，因此 0→4 的变化不能算外部验证；历史组的改善也只有 8→10，不能断言普遍有效。

## 下一批采集前冻结的候选规则

1. 原始记录完整保存，以 `bp_capture.decode` 严格检查数量、顺序、校验和及 MCU tick；不从桥接 `sampleRateHz=0` 推断采样频率。记录面板模式、预设、SBP/DBP、BPM、脉搏容积、面板照片、气路与采前后零点。缺证据的轮次保留为 development。
2. 离线节律及干净脉搏提取保持现行实现，不用面板 BPM 来选频。研究诊断固定 `step_padding_samples=40`；Standard 120/80 用 `upper_pressure=130`，Standard 150/100 用 `upper_pressure=170`。压力箱从 50 mmHg 起，以左闭右开规则划分。
3. **待检验候选**为 `--bin-width 10`，同时输出 `--bin-width 5` 作为已知基线敏感性结果。其余门槛沿用现行脚本：峰值箱至少 3 个干净脉搏、已占箱最大间隔不超过 15 mmHg、留一箱拟合峰最大移动不超过 7.5 mmHg，以及现行高低压尾、R² 与峰位一致性规则。高度和面积均为 `diagnostic_only` 且 `robustness.screen=pass` 才标注“包络可分析候选”；否则报告拒绝原因并保留原始波形。不得只挑对当前轮次有利的宽度。
4. 候选峰只供第三方研究，不从拟合峰直接产生 SBP/DBP 或临床结论。以后若要把动态压力写成参考真值，需另有同步独立压力证据；BP Pump 2 的 Standard BP 界面不显示实时压力，先前 Pressure Source 静态校准不能冒充这轮动态参考。下一批独立采集的结果无论通过与否均按上述规则报告，并与本次规则选择批次分开。

复现全部汇总：`python 'blood pressure monitor/tools/bp_bin_width_audit.py' data/reports/standard120_80_20261101-111311.verified.ndjson data/reports/standard120_80_20261101-114844.verified.ndjson data/reports/standard120_80_20261101-120429.verified.ndjson data/reports/standard150_100_20261101-123247.verified.ndjson`。该工具从固定目录的去重历史目录读取另 42 轮，输出本报告所用 JSON。复现单轮：`python 'blood pressure monitor/tools/bp_oscillogram_study.py' <verified.ndjson> --upper-pressure 130 --bin-width 10`；150/100 将上界改为 `170`。同一输入再以 `--bin-width 5` 运行基线比较。全程无需串口写入、充气、固件或校准变更。
