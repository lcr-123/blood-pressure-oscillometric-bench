# 2026-11-01 Standard BP 非人体开发数据清单

主测压链路为 MPXV5050GP + ADS1115。BP Pump 2 Static Pressure / Pressure Source 多点标定已完成，系数 `82.326 mmHg/V`、`-19.887 mmHg`，证据见 `calibration_data/manual_static_2026-10-25.json`；本清单不要求重复静态标定。机器可读清单 `standard_bp_development_manifest_20261101.json` 含逐文件 SHA256、面板设置、脉搏容积、导出点数及失败轮。可用 `python tmp/build_20261101_development_manifest.py` 重建。

| 面板设置 | 完整导出 | 失败尝试 | 已记录脉搏容积 |
| --- | ---: | ---: | --- |
| 120/80，80 BPM | 4 | 0 | 前两轮未知；后两轮 0.68 cc |
| 150/100，80 BPM | 1 | 0 | 0.65 cc |
| 200/150，80 BPM | 1 | 1 | 0.60 cc |

6 轮完整文件均经严格解码，MCU 相邻 tick 为 25 ms，生产 C 同源回放的包络、特征和有效性按位一致。失败轮 12 秒未升压后安全停止，不能算完整波形。所有记录均为 **development**；缺本轮面板照片和 Standard BP 动态运行时的独立同步压力轨迹，原有静态标定点不能被误写成逐时刻动态参考。当前可以整理并开放原始开发波形、元数据和参考脚本，明确披露零点异常与包络质量筛查结果；不据此声明血压准确度。

本轮追加的 30 秒只读零点记录见 `data/raw/preflight/sealed_zero_readonly_20261101-140513.ndjson`，复算摘要 `data/reports/sealed_zero_readonly_20261101-140513.json`。601 条新鲜样本 raw=1312..1316，est 均为 0.0；这证明该窗口内原始读数稳定，不证明物理绝对零压。进一步解释见 `data/reports/zero_reference_plan_20261101.md`。

15:20 的 120/80、0.68 cc 新轮完整导出 2369 点，10 mmHg 包络候选通过；采后封阀 raw 曾较采前高约 55 计数，第二次 vent/新鲜近零/seal 后仍高约 11–16 计数。见 `data/reports/standard120_80_20261101-152030.md`。暂停进一步充气，先查清零点可比性。
