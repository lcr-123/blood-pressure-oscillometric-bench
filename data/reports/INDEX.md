# data/reports 索引

本文件是 `data/reports/` 全部 **286** 个文件的逐份索引，2026-11-16 由四次只读清点合并而成。
每个文件一行：日期、一句话结论、状态、关键数字。状态只有四类——`现行`、`已取代`、`已撤回`、`数据图表`（原始 json/csv/png，本身不下结论，结论由其同名 `.md` 承载）。

> **引用纪律（先读这一条）**：本目录里同时存在互相推翻、互相重叠、以及"已作废但正文完整保留"的文件。任何一处引用都应先在本索引里确认状态，再看 §5 冲突与疑点里有没有针对它的条目。把文件名当结论直接引用，是本目录最容易犯的错。

## 0 从哪里开始读

| 文件 | 为什么先读它 |
|---|---|
| [dataset_scope_statement.md](dataset_scope_statement.md) | 数据集能证明什么、不能证明什么（62 轮冻结口径） |
| [dataset_limitations.md](dataset_limitations.md) | §1–§26 已知边界 + 引用时必须声明的最小集 21 条 |
| [covered_algorithm_20261113.md](covered_algorithm_20261113.md) | 一套常量通吃七档的三视图中位估计器 |
| [standard_conformance_20261114.md](standard_conformance_20261114.md) | 对 AAMI/ISO 与 BHS 判据的算术核算（232 轮） |
| [standard_conformance_20261115.json](standard_conformance_20261115.json) | 处置 P2 两轮后的重算（297 轮，七档 5/7） |
| [precision_levers_20261115.md](precision_levers_20261115.md) | 精度还能不能改：剩余失败格与已否证的预测变量 |
| [p4_steepness_target_20261113.md](p4_steepness_target_20261113.md) | 高压档出数率上限 84%，不是差一点就能修 |
| [measurement_precision_20261112.md](measurement_precision_20261112.md) | 一次采集有多准、k 次中位能降到多少 |
| [pressure_axis_accuracy_20261111.md](pressure_axis_accuracy_20261111.md) | 压力轴可声明到什么程度 |
| [volume_crosscheck_20261109.md](volume_crosscheck_20261109.md) | 回路容积 320 cc 的独立交叉验证 |
| [statistics_convention_20261111.md](statistics_convention_20261111.md) | 为什么剔除 4 轮阀故障、AAMI 怎么判 |
| [zero_drift_20261112.md](zero_drift_20261112.md) | 采集前零点是偏移不是残气，不影响血压量 |

## 1 规模与口径

- 文件总数 **286**（`data/reports/` 下除本索引外的全部普通文件）。
- 按状态：现行 **168**、已取代 **28**、已撤回 **7**、数据图表 **83**、其他 0。
- 按扩展名：`.md` 160、`.json` 95、`.png` 12、`.csv` 11、`.ndjson` 8
- 按日（文件名日期，27 天）：10-31 39；11-01 47；11-05 34；11-06 3；11-07 13；11-08 22；11-09 29；11-10 15；11-11 25；11-12 8；11-13 9；11-14 8；11-15 5；11-16 4；11-17 1；11-18 1；11-19 1；11-20 1；11-21 1；11-22 1；11-23 1；11-24 1；11-25 5；11-26 9

> 三处"日期"与内容无关的坑：`.json` 的 mtime 可能晚于同名 `.md`；`standard_display_protocol_20261109.md` 文件名 11-09 而 mtime 是 11-08；另有 3 份没有日期戳（`dataset_limitations.md`、`dataset_scope_statement.md`、`prospective_progress.md`），日期取自正文或 mtime。

## 2 逐份索引

按日期升序，同日按文件名。`状态` 一栏括注里的文件名是指"被谁取代/撤回"。

| 文件 | 日期 | 一句话结论 | 状态 | 关键数字 |
|---|---|---|---|---|
| [ads_bus_retest_20261031-153810.json](ads_bus_retest_20261031-153810.json) | 2026-10-31 | 该次 ADS 复测的机器记录：outcome=failed，错误码与波形摘要 | 数据图表 | outcome=failed、SR1=0x0010、sha bf4ec5c1… |
| [ads_bus_retest_20261031-153810.md](ads_bus_retest_20261031-153810.md) | 2026-10-31 | 30 mmHg 复测失败：保压期读取失败触发紧急放气，未进 PWM | 现行 | 30.9 mmHg、err 0x200、栈 1184/2912 |
| [ads_switching_audit_20261031.md](ads_switching_audit_20261031.md) | 2026-10-31 | 三份到压停泵记录同现 stage5 失败，确认固件未取消待启动 PWM | 现行 | 3 份记录、57–59 ms、0x200/0x20 |
| [branch_isolation_plan_20261031.md](branch_isolation_plan_20261031.md) | 2026-10-31 | 阀/继电器支路隔离方案＋器件核实，带载开闭实测已触发 ADS 错误 | 现行（待修复） | 线圈 89.7 Ω、1.61 W、errors 1→2 |
| [capture_catalog_20261031.json](capture_catalog_20261031.json) | 2026-10-31 | 102 份导出的严格解码目录，逐文件状态与重复标记 | 数据图表 | files 102、valid 83、unique 42 |
| [capture_catalog_20261031.md](capture_catalog_20261031.md) | 2026-10-31 | 同批目录审核：19 份失败全为无捕获结束标记，无一份可直接发布 | 现行 | 102/83/19、release_ready 0 |
| [external_static100_20261031-162647.md](external_static100_20261031-162647.md) | 2026-10-31 | 100 mmHg 外部静压对照未复现 ADS 失读，错误计数仍 1/1 | 现行 | 200 VALID、均值 98.6065、sha 55f2ba59… |
| [load_off_switch_20261031-170340.md](load_off_switch_20261031-170340.md) | 2026-10-31 | 断开负载 12 V 时 9 次输出切换全通过、ADS 零错误，但未判因 | 现行 | 9 次切换、errors 0/0、1484 条新鲜记录 |
| [original_config_low30_20261031-174142.md](original_config_low30_20261031-174142.md) | 2026-10-31 | 原配置 30 mmHg 复测再失败，错误码与上次不同（HAL_BUSY） | 现行 | 30.8 mmHg、SR2=0x2、err 0x20 |
| [pb8_standard_trial_20261031.json](pb8_standard_trial_20261031.json) | 2026-10-31 | PB8 开漏单次试验事件记录：到压成功但重复启动 8 次、复位原因未知 | 数据图表 | repeated_boot_count 8、150.5、66.525 s |
| [pb8_standard_trial_20261031.simulation.csv](pb8_standard_trial_20261031.simulation.csv) | 2026-10-31 | 该试验的理想斜坡示意曲线，自述「非气动模型」 | 数据图表 | 1330 行、2 mmHg/s |
| [prospective_preflight_20261031-132512-832862.json](prospective_preflight_20261031-132512-832862.json) | 2026-10-31 | 只读前瞻预检：设备状态正常，但零压/夹具/气路配置三项均 null | 数据图表 | 197 样本、ads 167、est 0 |
| [read_path_test_20261031.md](read_path_test_20261031.md) | 2026-10-31 | 读取路径隔离测试：静止零压400次全成功，根因未定 | 现行 | n=400；ADS错误0；RAM 63488/65536 |
| [readonly_retry_20261031-173923.md](readonly_retry_20261031-173923.md) | 2026-10-31 | 封阀零压只读复测通过，明示非带载验收 | 现行 | n=400；fresh=409；raw均值1311.82 |
| [reconnect_preflight_20261031-150248.md](reconnect_preflight_20261031-150248.md) | 2026-10-31 | 串口恢复后无负载预检通过，14:54失败记录仍有效 | 现行 | 10s/200样本；raw均值1299.04；栈1424/2672 |
| [restart_low30_20261031-142713.capture.ndjson](restart_low30_20261031-142713.capture.ndjson) | 2026-10-31 | 30mmHg放气PWM波形导出65点 | 数据图表 | 65点/1600ms；dropped=0 |
| [restart_low30_20261031-142713.csv](restart_low30_20261031-142713.csv) | 2026-10-31 | 上述波形逐点CSV，压力19.16→14.75 | 数据图表 | 65行；−2.76mmHg/s |
| [restart_low30_20261031-142713.decode.json](restart_low30_20261031-142713.decode.json) | 2026-10-31 | 波形完整性解码校验报告，校验通过 | 现行 | n=65；steps=0；丢点0 |
| [restart_low30_20261031-142713.summary.md](restart_low30_20261031-142713.summary.md) | 2026-10-31 | 30mmHg轮走完全流程，停泵等待期掉压明显 | 现行 | 到压30.2/峰值33.4；1s内降19.3 |
| [restart_low30_failure_20261031-145438.json](restart_low30_failure_20261031-145438.json) | 2026-10-31 | 结构化失败元数据，根因未定 | 现行 | 最后28.0mmHg；无有效导出 |
| [restart_low30_failure_20261031-145438.md](restart_low30_failure_20261031-145438.md) | 2026-10-31 | 该轮失败记录：stop/vent均无ACK，主机中止 | 现行 | 14条压力回显；root_cause undetermined |
| [restart_low30_failure_20261031-150649.md](restart_low30_failure_20261031-150649.md) | 2026-10-31 | 复测触发等待期保护，ADS I2C超时仍在 | 现行 | err0x20/stage5；到压31.2；约37mmHg/s |
| [sealed_hold30_20261031-143306.analysis.json](sealed_hold30_20261031-143306.analysis.json) | 2026-10-31 | 判定本轮保压对照无效（SENSOR_READ丢数） | 已撤回 | valid=false；82点降0.544mmHg/s；gap 1067ms |
| [sealed_hold30_20261031-143306.csv](sealed_hold30_20261031-143306.csv) | 2026-10-31 | 同轮串口逐点CSV，含充气与零压收尾段 | 数据图表 | 256行；est 0→19.6→0.9 |
| [sealed_hold30_20261031-143306.summary.md](sealed_hold30_20261031-143306.summary.md) | 2026-10-31 | 本轮无效：停泵附近I2C超时缺样本 | 已撤回 | errors1/recoveries1；到压30.7 |
| [sealed_hold30_20261031-184235.md](sealed_hold30_20261031-184235.md) | 2026-10-31 | 加二极管后复测无故障，但保压仍持续掉压 | 现行 | 22.3→17.6；0.950mmHg/s；440样本 |
| [uart_guard_low30_20261031-160924.md](uart_guard_low30_20261031-160924.md) | 2026-10-31 | UART 修好后带载保压仍失败，紧急放气 | 现行（该失败判据未被后续文件推翻） | 31.0 mmHg 触发 |
| [valve1_coil_disconnected_20261031-182417.md](valve1_coil_disconnected_20261031-182417.md) | 2026-10-31 | 断开阀线圈后单次开闭未复现失读 | 现行（隔离实验之一，未见反驳） | 379 样本, ADS 0/0 |
| [valve1_diode_20261031-181000.md](valve1_diode_20261031-181000.md) | 2026-10-31 | 带二极管单次开闭仍复现 ADS 失读 | 已取代（valve1_diode_20261031-183711.md 在阀端改接二极管后未复现） | HAL_BUSY, err 0x20 |
| [valve1_diode_20261031-181318.md](valve1_diode_20261031-181318.md) | 2026-10-31 | 再测再失读，ADS 错误计数翻倍 | 已取代（valve1_diode_20261031-183711.md 改接线后未复现） | ADS errors 1→2 |
| [valve1_diode_20261031-183711.md](valve1_diode_20261031-183711.md) | 2026-10-31 | 阀端二极管接线后单次开闭未复现失读 | 现行（当日最后一次同题实验，结论最新） | 378 样本, ADS 0/0 |
| [valve1_isolation_20261031-154115.json](valve1_isolation_20261031-154115.json) | 2026-10-31 | 只切一次 PB8 就通信中断，泵没起 | 数据图表（实验 json 载荷） | post_close 样本 0 |
| [valve1_isolation_20261031-154115.md](valve1_isolation_20261031-154115.md) | 2026-10-31 | 单次阀切换即通信中断，根因未定 | 现行（root_cause unresolved，无后续结案文件） | 中断, 泵未启动 |
| [valve1_live_20261031-174749.md](valve1_live_20261031-174749.md) | 2026-10-31 | 带载且无二极管时再次触发 ADS 失读 | 现行（作为二极管修复前的对照证据） | HAL_BUSY/TIMEOUT |
| [valve1_load_off_20261031-154839.md](valve1_load_off_20261031-154839.md) | 2026-10-31 | 负载断电后单次切换未复现断流 | 现行（隔离实验之一） | raw 1310..1313 |
| [valve_end_diode_low30_20261031-183921.capture.csv](valve_end_diode_low30_20261031-183921.capture.csv) | 2026-10-31 | 加二极管后 30 mmHg 复测逐点表 | 数据图表（csv 逐点数据） | 98 行 |
| [valve_end_diode_low30_20261031-183921.decode.json](valve_end_diode_low30_20261031-183921.decode.json) | 2026-10-31 | 该轮解码摘要 | 数据图表（解码摘要 json） | n=97, 2400 ms |
| [valve_end_diode_low30_20261031-183921.md](valve_end_diode_low30_20261031-183921.md) | 2026-10-31 | 加二极管后未复现 ADS 失读，但保压压降明显 | 现行（后续 valve_glitch_despike 未推翻该压降现象） | 30.6→20.1/1002 ms |
| [zero_observation_20261031-132735-752183.json](zero_observation_20261031-132735-752183.json) | 2026-10-31 | 被动零压观察 400 样本，ADS 恒 165 | 数据图表（观察 json 载荷） | mean raw 1319.26 |
| [high_target_capture_20261101.md](high_target_capture_20261101.md) | 2026-11-01 | Preset 3 高压采集的烧录与首跑到压过程记录 | 现行 | 3300 点/82.5 s、HEX be45baab… |
| [offline_bin_width_20261101.json](offline_bin_width_20261101.json) | 2026-11-01 | 46 轮逐轮 5 vs 10 mmHg 分箱敏感性原始表（含 SHA、上界、两口径） | 数据图表 | 历史 42 轮 8 vs 10、当日 4 轮 0 vs 4 |
| [offline_bin_width_20261101.md](offline_bin_width_20261101.md) | 2026-11-01 | 分箱宽度 5→10 的敏感性（42 轮 8→10、当日 0→4），冻结候选规则 | 现行 | 8→10、0→4、--bin-width 10、padding 40 |
| [offline_multiwindow_20261101.json](offline_multiwindow_20261101.json) | 2026-11-01 | 45 轮多窗口脉率诊断的逐轮原始结果 | 数据图表 | captures 45、128 点仅 5/45 |
| [offline_multiwindow_20261101.md](offline_multiwindow_20261101.md) | 2026-11-01 | 128 点重叠窗几乎无候选，256 点与长窗一致；心率多样性不足 | 现行 | 5/45、34/45、箱间隔 9.375 BPM |
| [preset1_zero_recovery_20261101.md](preset1_zero_recovery_20261101.md) | 2026-11-01 | P1 采后封阀零点 +53 counts 后回落到 +0.6，根因无法区分 | 现行 | +53.320→+0.615、1342.405 |
| [preset3_upper_envelope_20261101.json](preset3_upper_envelope_20261101.json) | 2026-11-01 | P3 高压段扩界到 210 mmHg 的原始分箱与冻结 170 口径对照 | 数据图表 | 57 beats、962 eligible、80 bpm |
| [preset3_upper_envelope_20261101.md](preset3_upper_envelope_20261101.md) | 2026-11-01 | P3 高压段起伏非稳定单峰，扩到 210 仍 incomplete，保留 development | 现行 | 47→57、0.0230–0.0347 V |
| [sealed_zero_readonly_20261101-140513.json](sealed_zero_readonly_20261101-140513.json) | 2026-11-01 | 封阀零压30s只读统计，静态读数稳定 | 现行 | 601样本；raw 1312–1316；est恒0.0 |
| [standard120_80_20261101-111311.csv](standard120_80_20261101-111311.csv) | 2026-11-01 | 2673 点原始采集表，11 列含 est/包络/平滑位 | 现行 | 2673 点；t 起 690886 |
| [standard120_80_20261101-111311.md](standard120_80_20261101-111311.md) | 2026-11-01 | 固件 114/81/75 valid=1，但缺独立参考不得升级 | 现行 | 2673 点；66800 ms；335 脉冲 |
| [standard120_80_20261101-111311.replay.json](standard120_80_20261101-111311.replay.json) | 2026-11-01 | CSV 回放包与固件结果全等 0 误差 | 现行 | n=2673；max err 0.0 |
| [standard120_80_20261101-111311.verified.ndjson](standard120_80_20261101-111311.verified.ndjson) | 2026-11-01 | begin/point/features/end 四段校验流 | 现行 | 2673 点；dropped 0 |
| [standard120_80_20261101-114844.csv](standard120_80_20261101-114844.csv) | 2026-11-01 | 2289 点原始采集表，同 11 列表头 | 现行 | 2289 点；57.2 s |
| [standard120_80_20261101-114844.md](standard120_80_20261101-114844.md) | 2026-11-01 | 固件 119/87/56 valid=1，离线拟合仅 2 搏支撑 | 现行 | R² 0.743；2 搏；节律 0.921 |
| [standard120_80_20261101-114844.replay.json](standard120_80_20261101-114844.replay.json) | 2026-11-01 | 2289 点回放，与采集逐点全等 | 现行 | n=2289；287 脉冲 |
| [standard120_80_20261101-114844.verified.ndjson](standard120_80_20261101-114844.verified.ndjson) | 2026-11-01 | 同轮校验后逐点波形，无结论文本 | 数据图表（ndjson 原始样本） | 2293 行 |
| [standard120_80_20261101-120429.csv](standard120_80_20261101-120429.csv) | 2026-11-01 | 第 3 轮逐点导出表 | 数据图表（csv 逐点数据） | 2274 行 |
| [standard120_80_20261101-120429.md](standard120_80_20261101-120429.md) | 2026-11-01 | 达 150.8 但峰箱仅 2 搏，被 weak_peak_support 拒 | 已取代（同日更晚 standard120_80_20261101-152030.md 用 10 mmHg 箱通过稳健性） | n=2273, 谐振峰高 97.5, R²0.85 |
| [standard120_80_20261101-120429.replay.json](standard120_80_20261101-120429.replay.json) | 2026-11-01 | 同源回放位全等，只证明解码一致 | 数据图表（replay 位比对输出） | n=2273, max err 0.0 |
| [standard120_80_20261101-120429.verified.ndjson](standard120_80_20261101-120429.verified.ndjson) | 2026-11-01 | 校验后逐点波形 | 数据图表（ndjson 原始样本） | 2277 行 |
| [standard120_80_20261101-152030.adaptive.json](standard120_80_20261101-152030.adaptive.json) | 2026-11-01 | 自适应估计算不出 BP，仅给包络峰 | 数据图表（算法 json 载荷） | 峰 95.0, clean_beats 56, bp_output_allowed=false |
| [standard120_80_20261101-152030.csv](standard120_80_20261101-152030.csv) | 2026-11-01 | Preset1 同容积轮逐点导出 | 数据图表（csv 逐点数据） | 2370 行 |
| [standard120_80_20261101-152030.md](standard120_80_20261101-152030.md) | 2026-11-01 | 10 mmHg 箱高度 98.11/面积 99.15 且稳健性通过 | 现行（同日 Preset1 最晚一轮，未见更晚同题文件推翻） | 2369 点, 达 151.1 |
| [standard120_80_20261101-152030.replay.json](standard120_80_20261101-152030.replay.json) | 2026-11-01 | 回放位全等，固件 119/81 | 数据图表（replay 位比对输出） | 119/81, 75 BPM |
| [standard120_80_20261101-152030.verified.ndjson](standard120_80_20261101-152030.verified.ndjson) | 2026-11-01 | 校验后逐点波形 | 数据图表（ndjson 原始样本） | 2373 行 |
| [standard150_100_20261101-123247.csv](standard150_100_20261101-123247.csv) | 2026-11-01 | Preset2 逐点导出表 | 数据图表（csv 逐点数据） | 2802 行 |
| [standard150_100_20261101-123247.md](standard150_100_20261101-123247.md) | 2026-11-01 | 66 个干净搏但峰箱 122.5 仅 2 搏，被拒 | 现行（未发现更晚同题文件推翻该轮判据） | 2801 点, 达 171.1 |
| [standard150_100_20261101-123247.replay.json](standard150_100_20261101-123247.replay.json) | 2026-11-01 | 回放位全等，固件 144/90 | 数据图表（replay 位比对输出） | 144/90, 75 BPM |
| [standard150_100_20261101-123247.verified.ndjson](standard150_100_20261101-123247.verified.ndjson) | 2026-11-01 | 校验后逐点波形 | 数据图表（ndjson 原始样本） | 2805 行 |
| [standard200_150_20261101-134453.csv](standard200_150_20261101-134453.csv) | 2026-11-01 | Preset3 逐点导出表 | 数据图表（csv 逐点数据） | 2290 行 |
| [standard200_150_20261101-134453.md](standard200_150_20261101-134453.md) | 2026-11-01 | MAP 窗选中 89 却与 160–170 段包络不符 | 已取代（standard255_195_target275_peakwindow_20261106_salvage.md 把该现象归因到 bp_algorithm.c:534-541 写死窗） | 2289 点, 峰 167.5 |
| [standard200_150_20261101-134453.replay.json](standard200_150_20261101-134453.replay.json) | 2026-11-01 | 回放位全等，固件 190/77 | 数据图表（replay 位比对输出） | 190/77, 75 BPM |
| [standard200_150_20261101-134453.verified.ndjson](standard200_150_20261101-134453.verified.ndjson) | 2026-11-01 | 校验后逐点波形 | 数据图表（ndjson 原始样本） | 2293 行 |
| [standard_bp_adaptive_20261101.json](standard_bp_adaptive_20261101.json) | 2026-11-01 | 7个固定预设+user_defined，SBP/DBP恒为null | 现行 | schema /2；7轮；包络峰95/95/100/95 |
| [standard_bp_adaptive_20261101.md](standard_bp_adaptive_20261101.md) | 2026-11-01 | 撤回首版经验比例SBP/DBP，只留诊断量 | 现行 | 5候选仅1轮有高压50%交叉；禁止引用 |
| [standard_bp_development_manifest_20261101.json](standard_bp_development_manifest_20261101.json) | 2026-11-01 | 七次尝试清单，逐轮附三份产物路径与 SHA256 | 现行 | 尝试 7；完整 6；采样 2673/2289 |
| [standard_bp_development_manifest_20261101.md](standard_bp_development_manifest_20261101.md) | 2026-11-01 | 三档 6 轮严格解码，失败轮 12 秒未升压即安全停止 | 现行 | 6 轮；tick 25 ms；回放误差 0 |
| [standard_bp_diagnostics_20261101.json](standard_bp_diagnostics_20261101.json) | 2026-11-01 | 7 轮自适应诊断，2 轮采集不完整其余已诊断 | 现行 | 7 轮；合格箱 9–14 |
| [standard_bp_diagnostics_20261101.md](standard_bp_diagnostics_20261101.md) | 2026-11-01 | 高压交叉点缺失主因判为压力覆盖不足 | 现行 | 保留 50–70 搏；200/150 仅 2 箱 |
| [standard_bp_envelope_gate_20261101.json](standard_bp_envelope_gate_20261101.json) | 2026-11-01 | 门控全轮 bp_output_allowed=false，无一输出血压 | 现行 | 7 轮；0 输出；upper 130/170 |
| [standard_bp_envelope_gate_20261101.md](standard_bp_envelope_gate_20261101.md) | 2026-11-01 | 5 轮仅诊断级 candidate、2 轮 abstain，不动固件 valid | 现行 | 启动 7 次；5 candidate |
| [standard_bp_multisetting_study_20261101.json](standard_bp_multisetting_study_20261101.json) | 2026-11-01 | 三档重复性研究，明确拒绝拟合跨档血压模型 | 现行 | 4/1/2 轮；峰 95.0–99.47 |
| [standard_bp_multisetting_study_20261101.md](standard_bp_multisetting_study_20261101.md) | 2026-11-01 | 逐档启动 4/1/2，重复性目标 ≥3 轮/档未达 | 现行 | 漏高 11–16 计数；新轮 2369 点 |
| [valve2_zero_20261101-112951.md](valve2_zero_20261101-112951.md) | 2026-11-01 | 开阀比封阀高约 50 计数，est=0 掩盖了它 | 现行（valve2_zero_repeat 复现，未推翻） | 约 50 计数 ≈0.7 mmHg |
| [valve2_zero_repeat_20261101-154528.md](valve2_zero_repeat_20261101-154528.md) | 2026-11-01 | 重复确认开阀高 69–71 计数，收尾未回基线 | 现行（同题最新一次） | 69.308/70.875 计数 |
| [zero_reference_plan_20261101.md](zero_reference_plan_20261101.md) | 2026-11-01 | 需独立压力参考；面板精度不足以分辨 0.7 mmHg | 现行（需求未被满足，也未被撤销） | ±0.5% 读数 ±1 mmHg |
| [standard255_195_20261105-103250_capacity4200_cross_version.json](standard255_195_20261105-103250_capacity4200_cross_version.json) | 2026-11-05 | 两个固件版本回放位全等，可跨版本比较 | 数据图表（跨版本比对 json 载荷） | n=2825, 221/82 |
| [standard255_195_20261105-103250_decode.json](standard255_195_20261105-103250_decode.json) | 2026-11-05 | 该轮解码摘要（标定有效） | 数据图表（解码摘要 json） | n=2825, 70600 ms |
| [standard255_195_20261105-103250_diagnostics.json](standard255_195_20261105-103250_diagnostics.json) | 2026-11-05 | 包络诊断：峰在 215，高压侧 50% 交叉不存在 | 数据图表（诊断 json 载荷） | accepted 69, high_50pct=none |
| [standard255_195_20261105-103250_replay.json](standard255_195_20261105-103250_replay.json) | 2026-11-05 | 回放位全等，固件 221/82 | 数据图表（replay 位比对输出） | 221/82, 84 BPM |
| [standard255_195_target275_20261105.md](standard255_195_target275_20261105.md) | 2026-11-05 | 放气中样本溢出触发紧急放气，无终点 BP | 已取代（standard255_195_target275_capacity4200_20261105-111540.md 用 4200 容量同题成功） | 82475 ms, dropped 1 |
| [standard255_195_target275_capacity4200_20261105-111540.adaptive.json](standard255_195_target275_capacity4200_20261105-111540.adaptive.json) | 2026-11-05 | 包络候选 215，仍不允许输出 BP | 数据图表（算法 json 载荷） | 峰 215, clean_beats 73 |
| [standard255_195_target275_capacity4200_20261105-111540.csv](standard255_195_target275_capacity4200_20261105-111540.csv) | 2026-11-05 | 该轮逐点导出表 | 数据图表（csv 逐点数据） | 3130 行 |
| [standard255_195_target275_capacity4200_20261105-111540.diagnostics.json](standard255_195_target275_capacity4200_20261105-111540.diagnostics.json) | 2026-11-05 | 达 264 但高压侧 50% 交叉缺失 | 数据图表（诊断 json 载荷） | accepted 73, 峰 215/215 |
| [standard255_195_target275_capacity4200_20261105-111540.envelope.png](standard255_195_target275_capacity4200_20261105-111540.envelope.png) | 2026-11-05 | 包络曲线图，内容未读（仅按文件名与同批 md 定位） | 数据图表（png 图） | 128262 B |
| [standard255_195_target275_capacity4200_20261105-111540.md](standard255_195_target275_capacity4200_20261105-111540.md) | 2026-11-05 | 达 275.1，包络峰与面板一致但缺高压交叉 | 现行（容量 4200 后该轮未被更晚同题文件推翻） | 3129 点, high 64.62%/66.68% |
| [standard255_195_target275_capacity4200_20261105-111540.replay.json](standard255_195_target275_capacity4200_20261105-111540.replay.json) | 2026-11-05 | 回放位全等，但旧固件算出 valid=0 | 数据图表（replay 位比对输出） | valid=0, sbp/dbp=0 |
| [standard255_195_target275_capacity4200_20261105-111540.verified.ndjson](standard255_195_target275_capacity4200_20261105-111540.verified.ndjson) | 2026-11-05 | 校验后逐点波形 | 数据图表（ndjson 原始样本） | 3133 行 |
| [standard_bp_envelope_stability_20261105.adaptive.json](standard_bp_envelope_stability_20261105.adaptive.json) | 2026-11-05 | 13 轮复算 5 candidate、8 abstain，固件未改 | 现行 | 13 轮；beats 67/53/50/56/70；bpm 79.7 |
| [standard_bp_envelope_stability_20261105.before.json](standard_bp_envelope_stability_20261105.before.json) | 2026-11-05 | 改判前基线快照，111540 当时仍算 candidate | 已取代（standard_bp_envelope_stability_20261105.adaptive.json） | 8 轮；111540 峰 215.0 |
| [standard_bp_envelope_stability_20261105.diagnostics.json](standard_bp_envelope_stability_20261105.diagnostics.json) | 2026-11-05 | 13 轮诊断，8 ready 5 采集不完整；source 路径含乱码 | 现行 | 13 轮；5 不完整 |
| [standard_bp_envelope_stability_20261105.json](standard_bp_envelope_stability_20261105.json) | 2026-11-05 | 146 测试通过仍判 not_ready_for_firmware | 现行 | 146 测试；跨度 17.5>15 |
| [standard_bp_envelope_stability_20261105.manifest.json](standard_bp_envelope_stability_20261105.manifest.json) | 2026-11-05 | 13 次尝试全量清单，8 完整 5 失败均留档 | 现行 | 13 次；8 完整；5 失败 |
| [standard_bp_envelope_stability_20261105.md](standard_bp_envelope_stability_20261105.md) | 2026-11-05 | 完整数据仅覆盖四档到 255/195，target275 弃判 | 现行 | 峰 212.5–230；跨度 17.5 |
| [standard_bp_envelope_stability_20261105.png](standard_bp_envelope_stability_20261105.png) | 2026-11-05 | 分箱起点敏感性图，仅被 12 号 md 第 41 行图注引用 | 数据图表 | 2040×765 |
| [standard_bp_peak_instability_20261105.json](standard_bp_peak_instability_20261105.json) | 2026-11-05 | 13 轮峰值不稳归因于逐搏起伏与顶箱并列交换 | 已取代（standard_bp_peak_instability_20261105_reviewed.json） | 8 诊断/5 不完整；跨度 17.5 |
| [standard_bp_peak_instability_20261105.md](standard_bp_peak_instability_20261105.md) | 2026-11-05 | 机制=少搏分箱+相邻箱平滑致顶箱跳最大值 | 已取代（standard_bp_peak_instability_20261105_reviewed.md） | 凹陷 搏24 188.61 mmHg；跨 17.5 |
| [standard_bp_peak_instability_20261105.png](standard_bp_peak_instability_20261105.png) | 2026-11-05 | 两轮高压采集对比图，与 reviewed 版逐字节相同 | 数据图表 | 1950×1200 |
| [standard_bp_peak_instability_20261105_reviewed.json](standard_bp_peak_instability_20261105_reviewed.json) | 2026-11-05 | 仅工具代码哈希更新的复算，其余与原版逐行一致 | 现行 | 1,637,372 B；8/5 |
| [standard_bp_peak_instability_20261105_reviewed.md](standard_bp_peak_instability_20261105_reviewed.md) | 2026-11-05 | 补 133011 状态并加「拒绝覆盖既有输出」说明 | 现行 | 3 处改动；153 测试 |
| [standard_bp_peak_instability_20261105_reviewed.png](standard_bp_peak_instability_20261105_reviewed.png) | 2026-11-05 | 与原版同哈希的高压对比图，四面板均可读 | 数据图表 | 1950×1200；同 SHA256 |
| [standard_bp_peak_instability_20261105_reviewed.validation.json](standard_bp_peak_instability_20261105_reviewed.validation.json) | 2026-11-05 | 复现一致性校验，三份产物哈希核对通过 | 现行 | reproduction_exact=true；153 测试 |
| [standard_bp_peakwindow_20261105.analysis.json](standard_bp_peakwindow_20261105.analysis.json) | 2026-11-05 | 固定 200–245 带内 28 搏，峰跨 10 判定通过 | 现行 | 3273 点；带内 21.0 s；跨 10.0 |
| [standard_bp_peakwindow_20261105.replay.json](standard_bp_peakwindow_20261105.replay.json) | 2026-11-05 | 该次峰窗采集的回放包，阀脉冲 410 次 | 现行 | n=3273；410 脉冲；25 ms |
| [standard_bp_peakwindow_comparison_20261105.json](standard_bp_peakwindow_comparison_20261105.json) | 2026-11-05 | 基线弃判、峰窗对照通过，明示不作准确度 | 现行 | 2 轮；窗口 200–245 |
| [standard_bp_peakwindow_comparison_20261105.md](standard_bp_peakwindow_comparison_20261105.md) | 2026-11-05 | 缩窗后带内搏 +40%、跨度 27.5→10 才通过 | 现行 | 20→28 搏；2.916→2.354 mmHg/s |
| [standard_bp_peakwindow_comparison_20261105.png](standard_bp_peakwindow_comparison_20261105.png) | 2026-11-05 | 两轮对比图，正文无 markdown 图注仅记已检 | 数据图表 | 1920×1280 |
| [standard_bp_peakwindow_comparison_20261105.validation.json](standard_bp_peakwindow_comparison_20261105.validation.json) | 2026-11-05 | 快照与回放全等、159 测试通过 | 现行 | 159 测试；max error 0.0 |
| [standard_bp_valvetiming_baseline_20261105.analysis.json](standard_bp_valvetiming_baseline_20261105.analysis.json) | 2026-11-05 | 基线带内仅 20 搏，峰跨 27.5 弃判 | 现行 | 3299 点；14.575 s；跨 27.5 |
| [standard_bp_valvetiming_baseline_20261105.replay.json](standard_bp_valvetiming_baseline_20261105.replay.json) | 2026-11-05 | 基线回放，固件自身判 valid=0 | 现行 | n=3299；413 脉冲；valid 0 |
| [standard255_195_target275_peakwindow_20261106_salvage.md](standard255_195_target275_peakwindow_20261106_salvage.md) | 2026-11-06 | 算出失败根因：MAP 搜索窗写死 80–100 mmHg | 现行（根因判断未被后续文件推翻，valve_glitch_despike 只更正窗口居中细节） | 3929 点, 峰区 −1.669 mmHg/s |
| [standard_bp_preset_matrix_20261106.md](standard_bp_preset_matrix_20261106.md) | 2026-11-06 | 12 轮导出全过但 9 轮 invalid、3 轮 valid 却 SBP 错 | 现行 | 12 轮；−8.7…+16.7 mmHg |
| [standard_bp_preset_matrix_20261106.png](standard_bp_preset_matrix_20261106.png) | 2026-11-06 | 四预设矩阵图，被 29 号 md 图注引用 | 数据图表 | 1690×676 |
| [cuff_soak_pulse_transfer_20261107.png](cuff_soak_pulse_transfer_20261107.png) | 2026-11-07 | 被 leak_and_pulse 引用的袖带泡水后脉搏传递曲线图 | 数据图表 | — |
| [export_inventory_audit_20261107.md](export_inventory_audit_20261107.md) | 2026-11-07 | 导出清单核对：实际 67 份而非 58，追回一轮但不并入冻结基线 | 现行 | 67 vs 58（漏 9）、追回 1 轮 |
| [leak_and_pulse_20261107.md](leak_and_pulse_20261107.md) | 2026-11-07 | 泄漏回到 7 mmHg/min 合格，但 200 mmHg 以上脉搏消失（后撤回） | 已撤回（preset_envelope_retraction_20261107.md） | −6.56 vs 面板 7.0、0.09–0.12 vs 0.21–0.75 |
| [preset_envelope_collapse_20261107.png](preset_envelope_collapse_20261107.png) | 2026-11-07 | 被 preset_envelope_retraction 引用的包络按面板 MAP 对齐塌缩三联图 | 数据图表 | — |
| [preset_envelope_retraction_20261107.md](preset_envelope_retraction_20261107.md) | 2026-11-07 | 撤回「泡水致高压无脉搏」：真因是 BP Pump 2 在面板 SBP 以上不注入脉搏 | 已撤回（本文推翻 pulse_loss_after_soak / leak_and_pulse 的归因） | 差 <0.4、四预设峰 105/125/175/215 |
| [pulse_loss_after_soak_20261107.md](pulse_loss_after_soak_20261107.md) | 2026-11-07 | 复绑后 200 以上仍无脉搏、阈值落在 160–165，误判为泡沫硬化 | 已撤回（preset_envelope_retraction_20261107.md） | 0.03–0.10 vs 0.4–1.0、边界 160–165 |
| [rebuilt_envelope_20261107.md](rebuilt_envelope_20261107.md) | 2026-11-07 | 逐搏峰峰包络能降SBP离散，但共振归因已勘误 | 已撤回（smoothing_window_correction_20261108.md） | 前瞻n=37 SBP sd9.2；开发DBP sd4.7；MAP离群+51.4 |
| [recovered_exports_20261107.json](recovered_exports_20261107.json) | 2026-11-07 | 从运行日志里恢复9份完整导出并被严格解码 | 现行 | 9份；23921点；跨4个固件镜像 |
| [reference_bp_20261107.json](reference_bp_20261107.json) | 2026-11-07 | 18轮冻结基线逐轮复算明细（旧0.50/0.60口径） | 已取代（ratio_method_final_20261108.json） | 18轮；2s中值滤波；2处主动拒判 |
| [reference_bp_20261107.md](reference_bp_20261107.md) | 2026-11-07 | 18轮复算总表，含1轮瞬态拒判与1轮SBP拒判 | 已取代（ratio_method_final_20261108.json） | MAP Δ−5.0…+159.0；SBP最差+18.2 |
| [reference_bp_all_current_firmware_20261107.json](reference_bp_all_current_firmware_20261107.json) | 2026-11-07 | 当前固件58轮全量复算明细 | 现行 | 58轮；PEAK_WINDOW_20261105 |
| [reference_bp_prospective_v1.json](reference_bp_prospective_v1.json) | 2026-11-07 | 前瞻第1批20轮复算明细 | 现行 | 20轮；含1轮gate_rejected(−32.87) |
| [reference_bp_prospective_v2.json](reference_bp_prospective_v2.json) | 2026-11-07 | 前瞻第2批20轮复算明细，冻结算子v2 | 现行 | 20轮；freeze=reference_bp_v2 |
| [ab_phase_a_20261108.md](ab_phase_a_20261108.md) | 2026-11-08 | A 段按活塞通大气反而不抖，p2p 小，疑似手接触而非电路 | 已取代（ab_result_20261108.md） | p2p 332 counts=4.71、sd 30 |
| [ab_result_20261108.md](ab_result_20261108.md) | 2026-11-08 | A/B 对比证明 4.7 mmHg 噪声来自手压活塞，非硬件故障 | 现行 | 4.71 vs 0.27 mmHg（17×）、sd 30 vs 5.0 |
| [analog_fault_20261108.md](analog_fault_20261108.md) | 2026-11-08 | 静态通大气 p2p 放大 72×，判为间歇接触不良并要求停线检查 | 已撤回（ab_result_20261108.md 推翻该归因） | p2p 720 counts=10.2 mmHg、最大步长 99 |
| [bp_pump_setup_for_volume_step_20261108.md](bp_pump_setup_for_volume_step_20261108.md) | 2026-11-08 | 容积阶跃实验的 BP Pump 2 操作方案与「接对判据」 | 已取代（dataset_loop_volume_result_20261109.md） | 死腔 20 cc、判据落差 80–130 mmHg |
| [four_presets_20261108.md](four_presets_20261108.md) | 2026-11-08 | 四预设 36 轮只有 P1 全达标，MAP 偏置全正且换峰定义无效 | 已取代（map_bias_20261109.md） | 25/36、+4.1/+4.4/+5.9/+6.4 |
| [how_far_off_and_can_it_be_trusted_20261108.md](how_far_off_and_can_it_be_trusted_20261108.md) | 2026-11-08 | 前瞻 36 轮偏差全表，并撤回其中一节的循环论证 | 现行 | MAP +5.9/10.2、SBP −2.3/8.5、±10 内 78/81/89% |
| [manual_audit_20261108.md](manual_audit_20261108.md) | 2026-11-08 | 手册查明面板 MAP 是算术注释，拿它当误差指标属评分方式错 | 现行 | 7 预设全中、DBP 差 16、SBP sd 8.54 |
| [plumbing_for_calibration_20261108.md](plumbing_for_calibration_20261108.md) | 2026-11-08 | 校准注射器接法：阀2 不可去、BP Pump 2 在回路，只能声明约 158 cc | 已取代（dataset_loop_volume_result_20261109.md） | 6.19–9.03 mmHg/min、158 cc |
| [pressure_step_first_result_20261108.md](pressure_step_first_result_20261108.md) | 2026-11-08 | 压力阶跃首跑通但 dV 不可信，三法算容积互相分裂 | 现行 | 等温 252/绝热 357/气体 158 cc、201.2→81.8 |
| [pressure_step_method_20261108.md](pressure_step_method_20261108.md) | 2026-11-08 | 方法纠正：压力把活塞往外推，故改用阶跃法只需稳 3 s | 现行 | 0.64 kgf、±5%、P2 预测 21.1–136.5 |
| [push_from_20ml_plan_20261108.md](push_from_20ml_plan_20261108.md) | 2026-11-08 | 用 20/10/0 mL 三刻度做三平台互校的容积测量方案 | 已取代（dataset_loop_volume_result_20261109.md） | 三平台、假定 158 cc |
| [push_lookback_fix_20261108.md](push_lookback_fix_20261108.md) | 2026-11-08 | 第三次协议错误（先记 P1 后等，漏气使答案错 30%）的修法 | 现行 | 漏气 −0.11…−0.15 vs 推入 +5…+15、错 30% |
| [push_step_plan_20261108.md](push_step_plan_20261108.md) | 2026-11-08 | 注射器已满28mL，方案改为分两次各推入10mL测容积 | 现行 | 28→18→8mL；120→170→226mmHg |
| [ratio_method_final_20261108.json](ratio_method_final_20261108.json) | 2026-11-08 | 逐搏峰峰包络比例法定稿：开发19轮+前瞻36轮 | 现行 | 前瞻SBP −2.27/sd8.54；DBP −2.06/5.73；离群+51.4 |
| [round_now_waiting_pull_20261108.md](round_now_waiting_pull_20261108.md) | 2026-11-08 | 等待用户拉20mL测容积，P1定为167.5 | 已取代（push_step_plan_20261108.md） | 201.2→170.5→167.5；斜率+6.0mmHg/min |
| [smoothing_window_correction_20261108.md](smoothing_window_correction_20261108.md) | 2026-11-08 | 撤回"改平滑窗"结论：实测缩窗更差 | 现行 | 32→8点 SBP −0.2→−23.4；命中10/16→2/16 |
| [syringe20_calibration_plan_20261108.md](syringe20_calibration_plan_20261108.md) | 2026-11-08 | 20 mL 够用但每侧需 2–3 轮；153cc 已作废 | 现行（横幅自带作废声明，与 volume_crosscheck 一致） | 320cc（278–320） |
| [syringe_mechanism_20261108.md](syringe_mechanism_20261108.md) | 2026-11-08 | 注射器作用是留一个空腔而非抽气，活塞须通气时动 | 现行（后续 syringe_volume_protocol 沿用该原理） | — |
| [syringe_per_round_handling_20261108.md](syringe_per_round_handling_20261108.md) | 2026-11-08 | 每轮活塞必须推回 home 并锁死，否则读数异常 | 现行（protocol 与 result 均沿用该步骤） | 12:56 未锁即异常 |
| [volume_loop_vs_cuff_20261108.md](volume_loop_vs_cuff_20261108.md) | 2026-11-08 | 153cc 是气路总容积，不是袖带气囊容积 | 现行（概念区分，后续沿用） | 袖带 ≈125 cc |
| [volume_without_water_20261108.md](volume_without_water_20261108.md) | 2026-11-08 | 气体定律加漏气比算得 153cc，依赖面板读数 | 已取代（volume_crosscheck_20261109.md 直接测得 320cc） | 153cc |
| [why_not_accurate_20261108.md](why_not_accurate_20261108.md) | 2026-11-08 | 自认用 50% 高度对面板 SBP 属循环论证 | 现行（自我更正，未见回退） | 121.5/254.6 mmHg |
| [amplitude_ratio_method_20261109.md](amplitude_ratio_method_20261109.md) | 2026-11-09 | 振幅比测容积须用平方公式，直接比幅度被 1.6–6.9× 包络变化淹没 | 已取代（dataset_loop_volume_result_20261109.md） | 包络变 61–591%、18 mL→−20.3% |
| [bp_pump2_panel_setup_20261109.md](bp_pump2_panel_setup_20261109.md) | 2026-11-09 | BP Pump 2 逐键设置规范（External + Preset 4 三数校验） | 现行 | 255/195/0.55 cc、停 Preset 3 差 49 mmHg |
| [cuff_listing_eval_20261109.md](cuff_listing_eval_20261109.md) | 2026-11-09 | 商品页只给几何无气囊容积，67 份导出同一支袖带，2 mm 孔径非瓶颈 | 已取代（dataset_loop_volume_result_20261109.md） | 44.5×14.5 cm、压头 ≤2.2 mmHg、67 份 |
| [dataset_loop_tee_back_20261109.png](dataset_loop_tee_back_20261109.png) | 2026-11-09 | 被 tee_back_decision 引用的回路三通容积账与必做动作图 | 数据图表 | — |
| [dataset_loop_volume_protocol_20261109.md](dataset_loop_volume_protocol_20261109.md) | 2026-11-09 | 释放法测数据集回路容积的操作协议与四档自检 | 已取代（dataset_loop_volume_result_20261109.md） | 自检 ≤0.3%、注射器 26 mL |
| [dataset_loop_volume_result_20261109.md](dataset_loop_volume_result_20261109.md) | 2026-11-09 | 释放法实测回路 320 cc、数据集工况 340 cc，否定 52 cc 小回路分支 | 现行 | V=320.3 cc（278–320）、208.4→121.6 |
| [dbp_identifiability_20261109.md](dbp_identifiability_20261109.md) | 2026-11-09 | DBP 在台架不可辨识：MAP 以下阈值不交叠区间中位仅 8 | 现行 | 中位 8 区间、平滑后 −17.0/25.4 |
| [gauge_command_side_effect_20261109.md](gauge_command_side_effect_20261109.md) | 2026-11-09 | [GAUGE] 会把 Tester 切出 Standard BP 到 GAUGE 屏，采集期禁发 | 已取代（gauge_side_effect_20261109.md） | 3 次观察、终点差 −0.25/−4.1 |
| [gauge_side_effect_20261109.md](gauge_side_effect_20261109.md) | 2026-11-09 | 同主题重写：副作用已定，副作用实验因面板早被切走而设计失败 | 现行 | 脉搏 0.027 vs 1.684、延迟 173→806 ms |
| [independent_reference_20261109.md](independent_reference_20261109.md) | 2026-11-09 | 独立压力参考成立：共节点 150 段差 −1.3…−2.6，泄漏斜率差 3.2% | 现行 | −1.3…−2.6、3.2%、参考 1.9 Hz |
| [map_bias_20261109.md](map_bias_20261109.md) | 2026-11-09 | MAP 正偏置结案：面板 MAP 非物理峰位，四种峰定义都消不掉 | 现行 | +4.1…+6.4、四种峰定义 +5.20…+5.87 |
| [next_steps_20261109.md](next_steps_20261109.md) | 2026-11-09 | 旧版三条下一步建议，文首自标已被 11-10 版取代 | 已取代（next_steps_20261110.md） | 3 条建议 |
| [preset4_three_rounds_20261109.md](preset4_three_rounds_20261109.md) | 2026-11-09 | 接回 BP Pump 2 后 P4 三轮：MAP 准而 SBP/DBP 偏差大 | 现行 | +0.91/+3.42/−0.94、DBP +15.38 |
| [preset4_two_rounds_20261109.md](preset4_two_rounds_20261109.md) | 2026-11-09 | P4 两轮过程记录：包络峰落在 156 而非 215，平台使穿越偏低 | 已取代（preset4_three_rounds_20261109.md） | 峰 156.2 vs 215、plateau 0.14/0.12 |
| [rs232_attempt_20261109.md](rs232_attempt_20261109.md) | 2026-11-09 | RS-232首次尝试失败：系统未枚举任何新设备 | 已取代（rs232_link_20261109.md） | 仅COM6；PnP事件0条；无新VID/PID |
| [rs232_link_20261109.md](rs232_link_20261109.md) | 2026-11-09 | RS-232打通：1mmHg/5Hz，采集期禁发GAUGE | 现行 | Ver2.01S/5788005；173ms；5.0–5.2Hz |
| [sbp_headroom_20261109.md](sbp_headroom_20261109.md) | 2026-11-09 | P4的SBP净空仅6mmHg，是压力上限硬墙 | 现行 | 净空6 vs 140/111/60；2.1s；r=0.319 |
| [session_summary_20261109.md](session_summary_20261109.md) | 2026-11-09 | 11-09当日总结：容积320cc、双传感器互证 | 现行 | 340cc工况；泄漏率差3.2%；70导出/62现行 |
| [single_pull_protocol_20261109.md](single_pull_protocol_20261109.md) | 2026-11-09 | 一次拉到底方案，G=26mL，精度2.1% | 现行 | 26mL；±4.28cc=2.1%；153cc已作废 |
| [standard255_195_20261109-172104.md](standard255_195_20261109-172104.md) | 2026-11-09 | 接回 BP Pump 2 后最好一轮，三项误差均小 | 现行（时间最晚的 Preset4 成品轮，此后无同题成品报告） | 3417 点, MAP +0.9 |
| [standard_display_protocol_20261109.md](standard_display_protocol_20261109.md) | 2026-11-09 | 自我纠正「15 秒内读数」，须 90 s 后读并计压缩热 | 现行 | 201.2→167.5；热降≈21 mmHg |
| [syringe_connection_20261109.png](syringe_connection_20261109.png) | 2026-11-09 | 注射器接法图，内容未读 | 数据图表（png 图） | 283917 B |
| [syringe_volume_protocol_20261109.md](syringe_volume_protocol_20261109.md) | 2026-11-09 | 给出可复现的注射器测气路容积协议 | 现行（后续 320cc 交叉验证沿用同式） | P1·(V+g1)=P2·(V+g2) |
| [tee_back_decision_20261109.md](tee_back_decision_20261109.md) | 2026-11-09 | BP Pump 2 必须接回三通，它就是脉搏源 | 现行（11-09 172104 起按此执行） | — |
| [valvefree_circuit_20261109.md](valvefree_circuit_20261109.md) | 2026-11-09 | 承认此前"阀必须留回路"的驳回用错了依据 | 现行（自我更正，未见再推翻） | — |
| [valvefree_full_procedure_20261109.md](valvefree_full_procedure_20261109.md) | 2026-11-09 | 阀外测容积全流程，约 15 分钟不用阀不用 MCU | 现行（protocol 汇总，后续 result 按此执行） | 约 15 min |
| [valvefree_result_20261109.md](valvefree_result_20261109.md) | 2026-11-09 | 六个压力读数推算约 153cc | 已取代（自身横幅声明 153cc 作废，volume_crosscheck_20261109.md 给出 320cc） | 153cc, G=26 mL |
| [volume_crosscheck_20261109.md](volume_crosscheck_20261109.md) | 2026-11-09 | 38 轮波形反算 320cc，数据集工况应为约 340cc | 现行（范围内最晚的容积定值文件） | 320cc→340cc, 6% |
| [volume_disagreement_20261109.md](volume_disagreement_20261109.md) | 2026-11-09 | 153cc 与 300–500 mL 冲突源于误读容器上限 | 现行（纠正的是统计口径，未被推翻） | 153 vs 300–500 mL |
| [calibration_logic_20261110.md](calibration_logic_20261110.md) | 2026-11-10 | 校准是两参数 affine，固定补值不成立，继承 BP Pump 2 规格 | 现行 | est=82.326·V−19.887、残差±0.6、最坏 ±5.7（2026-11-26 前口径，之后固件改为 81.529/−20.03、最坏 2.840） |
| [data_quality_assessment_20261110.md](data_quality_assessment_20261110.md) | 2026-11-10 | 70 份导出六项检验全通过；留一预设证明一比例常数不通吃四档 | 现行 | 70/70、回放 0.0、留一 0.56–0.57 vs 0.45–0.46 |
| [next_steps_20261110.md](next_steps_20261110.md) | 2026-11-10 | 更新版下一步，并撤回「第三方标准器」与「9.4 mmHg 线性度」 | 现行 | 260 处 −2.87、VS 5.149 vs 5.062、撤回 2 项 |
| [sensor_supply_alert_20261110.md](sensor_supply_alert_20261110.md) | 2026-11-10 | 供电告警解除：面包板线松，并自曝三处推理错 | 现行 | 122→221mV；试充18.6；raw+1435counts |
| [shutdown_rule_seal_20261110.md](shutdown_rule_seal_20261110.md) | 2026-11-10 | 收尾漏seal：两个常用脚本只vent不关阀2 | 现行 | 2脚本已修；阀2通电抬高约3.94mmHg |
| [slope_uncertainty_target_20261110.md](slope_uncertainty_target_20261110.md) | 2026-11-10 | 0.2pp不必追：瓶颈是零点漂移3.58 | 现行 | 0.2%≈0.4mmHg；漂移3.58；线性度9.4已撤回 |
| [static_crosscheck_20261110-175635.json](static_crosscheck_20261110-175635.json) | 2026-11-10 | 第一轮四点原始比对（100/150/200/240） | 数据图表（测量 json） | n=4, −3.11 |
| [static_crosscheck_20261110-183222.json](static_crosscheck_20261110-183222.json) | 2026-11-10 | 第二轮低起点，差值随压力增大 | 数据图表（测量 json） | n=4, −1.38 |
| [static_crosscheck_20261110-204535.json](static_crosscheck_20261110-204535.json) | 2026-11-10 | 升序三点重复，60 mmHg 处差 −0.9/−1.0 | 数据图表（测量 json） | n=4, −1.67 |
| [static_crosscheck_20261110-210053.json](static_crosscheck_20261110-210053.json) | 2026-11-10 | 反序首点完成即中断，未跑完 | 数据图表（中断的测量 json） | −1.9, spread 0.4 |
| [static_crosscheck_20261110-210657.json](static_crosscheck_20261110-210657.json) | 2026-11-10 | 反序完整四点，跨度 1.7 | 数据图表（测量 json） | n=4, mean −1.94 |
| [static_crosscheck_20261110.md](static_crosscheck_20261110.md) | 2026-11-10 | 四点 Tester 均低，拟合出约 −1.15% 比例误差 | 现行（后续 two_sweeps / order_test 复现该斜率） | 均值 −3.11, R²0.900 |
| [static_crosscheck_order_test_20261110.md](static_crosscheck_order_test_20261110.md) | 2026-11-10 | 升序/反序斜率一致，刻度差随压力不随时间 | 现行（声明为当日最有决定性测量，无更晚同题反驳） | −0.989%, R²0.855 |
| [static_crosscheck_two_sweeps_20261110.md](static_crosscheck_two_sweeps_20261110.md) | 2026-11-10 | 第二轮复现 −1% 比例误差，零点偏移未复现 | 已取代（static_crosscheck_order_test_20261110.md 用反序实验给出更强判据） | −0.968% / −0.995% |
| [supply_5v133_analysis_20261110.md](supply_5v133_analysis_20261110.md) | 2026-11-10 | VS 轨 15 分钟内漂 0.31%，只能解释部分 1% 差 | 现行（未发现撤销该判断的文件） | 5.133→5.149 V, 1.73% |
| [envelope_peak_instability_20261111.md](envelope_peak_instability_20261111.md) | 2026-11-11 | P4 峰位漂两机制：SBP 以上非脉搏振荡抢峰＋包络更平 | 现行 | 80% 峰宽 77.5 vs 32–42、r +0.736 |
| [panel_beep_20261111-220624.json](panel_beep_20261111-220624.json) | 2026-11-11 | 蜂鸣节拍采集失败：vent 命令 3 次报 WinError 10054，无读数 | 数据图表 | cue_ms 空、面板值 null |
| [panel_beep_20261111-220931.json](panel_beep_20261111-220931.json) | 2026-11-11 | 250 mmHg 保压 6 节拍 gauge 233→219 与 MCU 同步，面板值仍 null | 数据图表 | 6 节拍、gauge 233→219、MCU 235.25→221.3 |
| [panel_beep_offset_20261111.json](panel_beep_offset_20261111.json) | 2026-11-11 | 面板与 [GAUGE] 同源：6 节拍差中位 0.00，与 MCU 差 −3.23 | 现行 | 0.00/0.47、−3.23/0.21、4/6 精确相等 |
| [panel_vs_gauge_20261111-205721.json](panel_vs_gauge_20261111-205721.json) | 2026-11-11 | 首轮面板 vs gauge 对比：两档持压 gauge 中位 123/222，面板未记 | 数据图表 | 150/250、gauge 123/222、71 点 |
| [panel_vs_gauge_20261111-211143.json](panel_vs_gauge_20261111-211143.json) | 2026-11-11 | 第二轮短持压：泵停瞬间 gauge 只有 1 点、与 MCU 差 49/68 | 数据图表 | 34/127 vs MCU 83/195 |
| [panel_vs_gauge_20261111-212040.json](panel_vs_gauge_20261111-212040.json) | 2026-11-11 | 第三轮带 prompt 时间戳：gauge 与 MCU 同步下降，差约 −1.6 | 数据图表 | prompt 1794403265738.9、130→122 |
| [panel_vs_gauge_20261111-214313.json](panel_vs_gauge_20261111-214313.json) | 2026-11-11 | 第四轮读泵停瞬间：gauge 滞后明显（105 vs MCU 139.55） | 数据图表 | 105 vs 139.55、202 vs 240.25 |
| [panel_vs_gauge_20261111-215114.json](panel_vs_gauge_20261111-215114.json) | 2026-11-11 | 第五轮 20 s 后读：两档 gauge 与 MCU 差 ≤1 | 数据图表 | 126/126.95、229/230.8 |
| [panel_vs_gauge_20261111-215521.json](panel_vs_gauge_20261111-215521.json) | 2026-11-11 | 第六轮单点 150 泵停即读：gauge 138 vs MCU 139.85 | 数据图表 | 138 vs 139.85、持压中位 129.5 |
| [preset4_recovery_attempts_20261111.md](preset4_recovery_attempts_20261111.md) | 2026-11-11 | 纠正 P4 可用率口径：P4 MAP 全库最准，真短板只有 SBP | 现行 | +0.80/3.58、SBP 9/18、三种恢复全否 |
| [pressure_axis_accuracy_20261111.md](pressure_axis_accuracy_20261111.md) | 2026-11-11 | 压力轴可声明有界准确度 ±5.7（旧轴口径；11-26 重标定后 2.840、17/17），撤回「9.4 mmHg 线性度」 | 现行 | ±5.7、8/17 在规格内、−0.969 pp/100（旧轴；新轴 2.840、17/17） |
| [pressure_axis_bound_20261111.json](pressure_axis_bound_20261111.json) | 2026-11-11 | 17 点有界声明的原始表与中位/存储两口径拟合 | 数据图表 | 17 点、R² 0.789、worst 1.5051× |
| [reference_bp_v3_baseline_20261111.json](reference_bp_v3_baseline_20261111.json) | 2026-11-11 | 用v3候选回算18轮开发集，仅描述非验证 | 现行 | 18轮；中位窗3.0s；panel_map为null |
| [reference_bp_v3_validation.json](reference_bp_v3_validation.json) | 2026-11-11 | v3正式裁决：sd反升，放弃v3、v2保持冻结 | 现行 | sd 6.084→6.237；40轮；位移中位+1.35 |
| [reference_bp_v3_validation.md](reference_bp_v3_validation.md) | 2026-11-11 | v3放弃的正式说明，四条标准逐项对照 | 现行 | v2 6.084 vs v3 6.237；P4降0.61为分母效应 |
| [reference_bp_v3_validation_partial_3presets.json](reference_bp_v3_validation_partial_3presets.json) | 2026-11-11 | 30/40轮子集评分，NOTE明示非正式裁决 | 现行 | 30轮；池化sd 5.638→5.514 |
| [reference_bp_v3_validation_partial_3presets.md](reference_bp_v3_validation_partial_3presets.md) | 2026-11-11 | 三档30轮倾向放弃v3，坚持等P3补齐 | 现行 | sd −0.18…+0.64；P1恶化0.64 |
| [reference_bp_v3_validation_partial_p4.json](reference_bp_v3_validation_partial_p4.json) | 2026-11-11 | 首批10轮P4子集评分，非正式裁决 | 现行 | 10轮；sd 7.259→6.646 |
| [reference_bp_v3_validation_partial_p4.md](reference_bp_v3_validation_partial_p4.md) | 2026-11-11 | 首批10轮P4仅sd一条不过，另修4处工具缺陷 | 现行 | 降0.61；位移中位+2.31；4缺陷 |
| [static_crosscheck_20261111-195318.json](static_crosscheck_20261111-195318.json) | 2026-11-11 | 高压段 240/250/260 三点 | 数据图表（测量 json） | n=3, −2.16 |
| [static_crosscheck_20261111-195959.json](static_crosscheck_20261111-195959.json) | 2026-11-11 | 同三点重复，结果一致 | 数据图表（测量 json） | n=3, −2.14 |
| [static_crosscheck_20261111-201252.json](static_crosscheck_20261111-201252.json) | 2026-11-11 | 265/270 两点，差值 −3.3 | 数据图表（测量 json） | n=2, −3.36 |
| [static_crosscheck_20261111-222041.json](static_crosscheck_20261111-222041.json) | 2026-11-11 | 272/275 两点，高压处差达 −3.88 | 数据图表（测量 json） | n=2, −3.37 |
| [statistics_convention_20261111.md](statistics_convention_20261111.md) | 2026-11-11 | 剔除 4 轮阀故障后 MAP sd 腰斩，SBP/DBP 仍超 | 现行（该口径为后续 v4/v5 批次统计的基线约定） | MAP sd 12.78→4.73, n=48 |
| [measurement_precision_20261112.json](measurement_precision_20261112.json) | 2026-11-12 | k 次中位亚组与逐搏二分的原始统计表 | 数据图表 | n=78、sd 9.75→4.99、二分 34.14 |
| [measurement_precision_20261112.md](measurement_precision_20261112.md) | 2026-11-12 | 轮内不稳≥轮间：单次 SBP sd 9.75，k=4 可压到 4.99 | 现行 | 9.75/6.83/5.69/4.99、二分 34.14 |
| [static_crosscheck_20261112-115126.json](static_crosscheck_20261112-115126.json) | 2026-11-12 | 一个点都没采到，只留下零点漂移 | 数据图表（rows 为空的测量 json） | rows 空, zero_drift +2.0 mmHg |
| [v4_p1_groups_20261112.json](v4_p1_groups_20261112.json) | 2026-11-12 | Preset1 四判据全过，k=4 分组统计 | 数据图表（统计 json 载荷） | kgroup sd 3.599, 0.958 |
| [v4_p1_validation_20261112.md](v4_p1_validation_20261112.md) | 2026-11-12 | Preset1 预注册 v4 四条判据全过，仅限该预设 | 现行（v5 未推翻该预设的单点结论，只否定泛化） | SBP sd 10.53→3.60 |
| [v4_p4_groups_20261112.json](v4_p4_groups_20261112.json) | 2026-11-12 | Preset4 三条 C1 与 C4 全 FAIL | 数据图表（统计 json 载荷） | published 24/34=0.706 |
| [v4_p4_validation_20261112.md](v4_p4_validation_20261112.md) | 2026-11-12 | Preset4 判 FAIL，C4 决定性不达标且提前中止 | 现行（v5 批次进一步印证未达标） | 0.706 < 0.9 |
| [zero_drift_20261112.md](zero_drift_20261112.md) | 2026-11-12 | 封阀零点漂数 mmHg，脚本门限误挡 29 次采集 | 现行（同题最新，结论为门限该改） | −3.92 / +1.35 mmHg |
| [covered_algorithm_20261113.json](covered_algorithm_20261113.json) | 2026-11-13 | 三视图估计器在 222 导出上的逐轮结果与池化精度 | 数据图表 | exports 222、published 187、MAP −0.84/4.28 |
| [covered_algorithm_20261113.md](covered_algorithm_20261113.md) | 2026-11-13 | 三视图七档全过、静默清零，但属参数扫描后拟合，非前瞻验证 | 现行 | 0/7→7/7、MAP −0.84/4.28、187/222 |
| [low_preset_bands_20261113.png](low_preset_bands_20261113.png) | 2026-11-13 | 被 low_preset_sweep 引用的低三档 20 mmHg 分箱包络带图 | 数据图表 | — |
| [low_preset_peak_margin_20261113.png](low_preset_peak_margin_20261113.png) | 2026-11-13 | 被 low_preset_sweep 引用的 P5/P6/P7 峰余量对比图 | 数据图表 | — |
| [low_preset_sweep_20261113.md](low_preset_sweep_20261113.md) | 2026-11-13 | 低三档出数率高但 P5 被单轮 +149.6 毁掉，机理是阀脉宽量化振荡 | 现行 | P5 10/10、+149.6、真峰 5.64 mV |
| [p4_steepness_target_20261113.json](p4_steepness_target_20261113.json) | 2026-11-13 | P4 按 d90 扫描的逐档 yield 与偏置原始表 | 数据图表 | 63 轮、yield 0.746、−10.49→−23.60 |
| [p4_steepness_target_20261113.md](p4_steepness_target_20261113.md) | 2026-11-13 | 高压档出数率上限只有 84%，"把包络做陡"到不了 90%，且 SBP 偏置同步恶化 | 现行（诊断，不改常量） | 形状上限 53/63=84%；实测最高 76%；SBP 偏置 −5.7→−23.6；|SBP 误差|>15 从 6/42 到 34/44 |
| [preset_low_bp_20261113.json](preset_low_bp_20261113.json) | 2026-11-13 | 低三档各 11 轮的精度明细，P5 被单轮 +149.64 毁掉 | 数据图表 | +149.64、P7 sd 7.61、P6 −0.73/4.31 |
| [valve_glitch_despike_20261113.md](valve_glitch_despike_20261113.md) | 2026-11-13 | ADC 毛刺固定在开阀瞬间，剔除不改善精度，不值动硬件 | 现行（范围内最晚的毛刺专论） | 相位富集 43×, 156→158/184 |
| [covered_algorithm_20261114.json](covered_algorithm_20261114.json) | 2026-11-14 | 扩到 299 导出后的逐轮结果，池化 sd 反而变大 | 数据图表 | exports 299、published 243、MAP −0.74/6.55 |
| [deflate_loop_limit_cycle_20261114.md](deflate_loop_limit_cycle_20261114.md) | 2026-11-14 | 放气闭环极限环改窗只换抖动形态，纹波与精度无相关，已回退 | 现行 | 纹波 2.5–4.4→7.2–9.8、r ≤+0.229 |
| [preset3_vs_preset4_20261114.json](preset3_vs_preset4_20261114.json) | 2026-11-14 | 299 份按下阀毫秒流量分桶的 P3/P4 出数率原始表 | 数据图表 | 299 份、P3 0.606/0.75、P4 0.653/0.742 |
| [preset3_vs_preset4_20261114.md](preset3_vs_preset4_20261114.md) | 2026-11-14 | 「P3 比 P4 更难」不成立：剔快速放气日后 75% vs 74% | 现行 | 75/74、≥0.120 桶 38/25%、v2 88/63 |
| [standard_conformance_20261114.json](standard_conformance_20261114.json) | 2026-11-14 | 232 轮池化，7 档中 Preset2 三项全不过 | 已取代（standard_conformance_20261116.json） | 232 轮；MAP −0.71/6.64 |
| [standard_conformance_20261114.md](standard_conformance_20261114.md) | 2026-11-14 | 列四条理由不能称合规，冻结 v2 仍是参考 | 现行 | 232 轮；静默>20 mmHg 18 轮 |
| [v5_validation_20261114.json](v5_validation_20261114.json) | 2026-11-14 | 冻结 v5 三项 sd 全不过 AAMI | 数据图表（统计 json 载荷） | n=51, MAP sd 11.598 |
| [v5_validation_20261114.md](v5_validation_20261114.md) | 2026-11-14 | v5 前瞻 71 轮五条判据四失败，退回冻结 v2 | 现行（范围内最新算法版本结论） | C4 0.718, MAP sd 11.60 |
| [p2_panel_recollect_20261115.md](p2_panel_recollect_20261115.md) | 2026-11-15 | P2 两轮面板标签无证据→标 false 并重采，P2 三项转 PASS | 现行 | −0.29/4.39、−1.46/6.29、七档 4/7→5/7 |
| [precision_levers_20261115.md](precision_levers_20261115.md) | 2026-11-15 | 三条 SBP 偏置预测变量全部否证：均值改不动、sd 根本改不动 | 现行（速查表，判分口径以 standard_conformance 为准） | 308 轮；17 PASS / 3 FAIL(P2) / 2 未判定(P5/P7 SBP)；CI [+3.50,+6.80] 与 [+2.86,+7.24] |
| [sbp_levers_after_unresolved_20261115.md](sbp_levers_after_unresolved_20261115.md) | 2026-11-15 | 十条杠杆实测：只有加性偏移能动且不可迁移 | 现行 | PP斜率+0.657；反压缩0/7；偏置+2.00 vs −3.07 |
| [standard_conformance_20261115.json](standard_conformance_20261115.json) | 2026-11-15 | 补采后 297 轮，Preset2 转通过而 5/7 号 SBP 挂 | 已取代（standard_conformance_20261116.json） | 297 轮；通过 1,2,3,4,6 |
| [topup_batch_20261115.md](topup_batch_20261115.md) | 2026-11-15 | 补采 69 轮后全过 AAMI 的档数反而从 6/7 掉到 4/7 | 现行（范围内最晚文件，自称含"不能写"清单） | 4/7, SBP 均值 4.89→5.15 |
| [covered_algorithm_20261116.json](covered_algorithm_20261116.json) | 2026-11-16 | 371 导出（含 P2 重采）后的逐轮结果，池化三项全过 | 数据图表 | exports 371、published 308、MAP −1.08/4.13 |
| [crosstday_amend2_vent_offset_20261116.md](crosstday_amend2_vent_offset_20261116.md) | 2026-11-16 | vent 态读数不是零点：线圈偏移 +0.47…+7.1，旧门控卡在 est≤6.0 而非平稳性 | 现行（门控溯源，不改判定规则） | D1 14 轮 vent−seal +1.16…+1.99 中位 +1.68；失败轮重放旧条件 20 s 内 NEVER；seal 零点轮内漂 +0.44（t=7.78） |
| [crosstday_d01_20261116.md](crosstday_d01_20261116.md) | 2026-11-16 | 跨天批次 D1：块A 14 轮可用，块B 缺席记 half_day；3 次超压是 25 ms 采样相位、不是峰值过高 | 现行（批次记录，无估算值） | 14 轮 7 档；零点 −0.869…−0.219；峰值 273.8–280.0；3 次 Over-pressure；initial_rx_errors=86 |
| [standard_conformance_20261116.json](standard_conformance_20261116.json) | 2026-11-16 | 与 15 号仅 source 一行不同，全部数字相同 | 现行 | 297 轮；MAP −1.068/4.128 |
| [crosstday_d02_20261117.md](crosstday_d02_20261117.md) | 2026-11-17 | 跨天批次 D2：首个完整天 28 轮，块B 首档一次 ACK，1 次导出帧中断已补采 | 现行（批次记录，无估算值） | 28 轮 7 档 × 重缠前后；零点 pre mean +1.013 / post +1.346；漏率稳定段 −11.26；阀 flow 0.26805；固件拒判 22/29 |
| [crosstday_d03_20261118.md](crosstday_d03_20261118.md) | 2026-11-18 | 跨天批次 D3：第二个完整天 28 轮无失败；上午 +4.9 mmHg 台阶查实为传感器线松动 | 现行（批次记录，无估算值） | 28 轮；零点 pre mean −0.041 / post +0.348；峰窗斜率均值 −2.39（D2 为 −1.89）；漏率 −11.15；阀 flow 0.30063 |
| [crosstday_d04_20261119.md](crosstday_d04_20261119.md) | 2026-11-19 | 跨天批次 D4：第三个完整天 28 轮；4 次失败全补齐，含 2 次超压与 2 次桥接通路故障；COM12 假死靠改波特率唤醒 | 现行（批次记录，无估算值） | 28 轮；零点 pre mean +0.110 / post +0.482；峰窗斜率均值 −2.33；漏率稳定段 −11.36；阀 flow 0.31381；全批唯一无一轮峰值 ≥279 的一天 |
| [crosstday_d05_20261120.md](crosstday_d05_20261120.md) | 2026-11-20 | 跨天批次 D5：第四个完整天 28 轮；三次失败全是超压保护，超压与峰值无关，只看 25 ms 采样格点 | 现行（批次记录，无估算值） | 28 轮；零点 pre mean +0.920 / post +1.284；峰窗斜率均值 −2.50（三个离群点全在 P4）；漏率稳定段 −11.64；阀 flow 0.33333；线圈偏移 +0.37（本批最小） |
| [crosstday_d06_20261121.md](crosstday_d06_20261121.md) | 2026-11-21 | 跨天批次 D6：28 轮全 USABLE；开机 SENSOR_INIT 靠 0.6 s start/stop 清掉；1 轮死于单字节乱码 | 现行（批次记录，无估算值） | 28 轮；零点 pre mean +1.114 / post +1.545（本批最高）；峰窗斜率 −1.93（回到 D1/D2 档）；漏率稳定段 −11.13；阀 flow 0.32042（首次回落）；profile normal 复位失败 23/28 |
| [crosstday_d07_20261122.md](crosstday_d07_20261122.md) | 2026-11-22 | 跨天批次 D7：第五个完整天 28 轮；一次 raw=0 零电压坏样本（固件把全零读数当 VALID）；两次超压都在 target reached 后 18–20 ms；一处日志命名撞名 | 现行（批次记录，无估算值） | 28 轮；零点 pre mean +0.199 / post +0.613（本批最低）；峰窗斜率 −1.89（连续两天同一档）；漏率稳定段 −9.25（首次跌破 −11 平台）；阀 flow 0.17630（本批最大单日变动，−45%）；profile normal 复位失败 8/28 |
| [crosstday_d08_20261123.md](crosstday_d08_20261123.md) | 2026-11-23 | 跨天批次 D8：第六个完整天 28 轮 + 9 个失败 slot；5 次超压（单日最多）含 1 次无到压行；块B 重缠把零点顶到 +1.6 致 profile 连败 4 轮后自愈；采集前一次 MCU PIN 复位 | 现行（批次记录，无估算值） | 28 轮；零点 pre mean +1.135 / post +1.389（8 轮 post−pre 为负，本批最多）；峰窗斜率 −1.90（连续三天同一档）；漏率稳定段 −11.27（回到平台）；阀 flow 0.22057（两脉宽反向）；profile normal 复位失败 19/28；17/28 轮 pre 零点在固件 −1..+1 门外靠 already_peak 采成 |
| [crosstday_d09_20261124.md](crosstday_d09_20261124.md) | 2026-11-24 | 跨天批次 D9：第八个完整天 28 轮；开工前 ADS1115 间歇失联（HAL_I2C_WRONG_START 0x200，errors 4→20），早上 profile peak 五连败实为读数不可信；profile normal 复位 28/28 全失败 | 现行（批次记录，无估算值） | 28 轮；零点 pre mean +0.720 / post +1.046（post 最大 +1.244 本批最低，无一轮 >2.0）；峰窗斜率 −1.877（连续四天 −1.9 档）；漏率稳定段 −11.14（连续第二天在平台）；阀 flow 0.19974（两脉宽连续第二天反向）；coil offset +9.55 本批最大；14 次切换全一次 ACK、dropped 全天 0 |
| [crosstday_analysis_20261125.json](crosstday_analysis_20261125.json) | 2026-11-25 | 跨天批次 T0–T4 判定的机器可读输出（`crosstday_verdict_20261125.md` 的全部数字来源） | 现行（判定输出，含估算误差） | 265 轮 / 10 天 / 7 档；exclusions 1（`-135554` 峰窗降压 −16.14 mmHg/s）；顶层键 t0/t1/t2/t4 + 三个 model_*（T3 无独立键）；T2 63 个配对格；T4 frozen_v2 与 covered_bp 两套 |
| [crosstday_d10_20261125.md](crosstday_d10_20261125.md) | 2026-11-25 | 跨天批次 D10：第九个完整天 28 轮（27 可用）；第一次编排被 Windows 12:08:35 自动重启打断、写通道只能靠物理拔插恢复，整天作废重跑；重跑里 1 轮被冻结门判 REJECT（峰窗降压 −16.14 mmHg/s，降压阀丢了 3 秒节流） | 现行（批次记录，无估算值） | 28 轮（27 可用）；零点 pre mean +0.043 / post +0.339（post 最大 +1.046 是本批最低，余量 3.95）；峰窗斜率 −1.900（连续五天 −1.88…−1.93，是本批最稳的一段）；漏率稳定段 −17.63（首次离开 −11.1…−11.6 平台，但同一份轨迹里有 36 次 1.9 mmHg 锯齿）；阀 flow 0.18412（两脉宽连续三天反向）；coil offset +5.35；profile normal 复位失败 4/27、already_peak 只有 5/27；批次收尾 266/280 = 95.0% |
| [crosstday_verdict_20261125.md](crosstday_verdict_20261125.md) | 2026-11-25 | 跨天批次 T0–T4 判定：T0 一格都不能声明 5 mmHg 内（0/21 可声明、唯一 FAIL 是 P4/SBP）；T1 主检验 FAIL——加性 SBP 偏移不可迁移；T2 通过——袖带缠绕已排除到 1.81 mmHg 以下；T3 SBP 日项不复现（p=0.0572，完整日口径 p=0.0313 复现，两种口径并列）、DBP 复现；T4 冻结 v2 与 covered_bp 并列 | 现行（判定结论，含估算误差） | 266/280 = 95.0%（D1 half_day）；台架 1007 min；T0 claimable 0/21、20 undecided + 1 FAIL（P4/SBP −15.19 CI[−22.07,−8.31]）；T1 offset −1.325 / improvement −1.325 / late sd 12.47 FAIL；T2 Δwrap −1.083 CI[−5.283,+3.116] < 1.81；T3 SBP p 0.0572/0.0313、MAP 0.1001/0.4413、DBP 0.0174/0.0208，sb 0.000/0.000/1.469；T4 v2 259/265 静默 20 vs covered_bp 248/265 静默 2；剔 18 轮长尾后 T1 翻 PASS（描述性） |
| [deflate_throttle_loss_20261125.md](deflate_throttle_loss_20261125.md) | 2026-11-25 | 降压阀失节流的追查：全库其实是 5 例不是 3 例，机制是「阀端气阻先崩溃、闭环把开阀时间绕到 14-29 ms、气阻一放开绕上去的占空比一次泄掉」，固件零故障码，冻结门是唯一检测手段；并发现已发布 62 轮里有 4 轮正是其中四例 | 现行（工程报告，无估算值） | 645 份导出里 11 份 REJECT（6 旧固件 / 1 解码失败 / 5 阀失节流）；五轮段斜率 −13.76…−33.40 vs 健康 1.56…2.63、中位 −1.917、p1 −3.363；duty_med ≥ 8 的 10 轮含全部 5 例、627 轮 0 例，但 duty 必要不充分（余震轮 duty_med 14-25）；gain 比值不可用（82% 正常轮 ratio ≥ 3）；已发布 62 轮 USABLE 58 / REJECTED 4 |
| [failed_slot_attribution_20261125.md](failed_slot_attribution_20261125.md) | 2026-11-25 | 跨天批次 27 个失败 slot 的逐条归因，以及日志命名撞名的实证与修法 | 现行（工程报告，无估算值） | 293 slot / 167 日志名 / 126 名被共用 / 116 slot 的 .out 已非自己；113 份失败元数据里 27 份落在批次窗口，27/27 全部归因（19 超压、4 profile peak、1 导出不完整、1 时间戳乱序、1 命令未确认、1 传输中断）；更正「11 个已无法归因」为「全部可从 error 归因」 |
| [freeze_v6_20261126.md](freeze_v6_20261126.md) | 2026-11-26 | 冻结 v6：把压力轴钉进记录，并让基线可以被重算——前四份记录只钉代码哈希，换轴后仍报「完好」而基线数字已无法由当前硬件产生 | 现行（冻结声明，含已保留缺陷） | 四份记录全部通过（v6 新增 pressure_axis + covered_estimator + recompute_method 三块）；v2 基线 3.70/9.70/9.60 只在旧轴复现（新轴 3.819/9.770/9.416）；verify_freeze.py 对 v6 重跑基线比对字节，反向测试 8/8 抓到漂移；18 轮 pinned 轴 MAP +2.789/3.819、SBP −2.167/9.770、DBP −0.625/9.416，发布 16 |
| [pressure_axis_rebook_20261126.md](pressure_axis_rebook_20261126.md) | 2026-11-26 | 用新压力轴重算全部 645 份导出：跨天池从 6/7 掉到 5/7，掉的是 P4 的 SBP | 现行（账本重算，旧轴读数并列保留） | 跨天 235 轮 6/7→5/7（P4 SBP -2.91→-5.68、P2 SBP -3.97→-5.71）；T0 0/21→1/21（P1 MAP +0.602 CI[-3.56,+4.76]）；T1 两轴都 FAIL（offset 符号翻转 -0.73→+0.90）；T2 通过；T3 免疫（p 变化在第四位小数）；门多拒 1 份、跨天仍只有 135554；偏移常量改不改都不改 5/7 |
| [pressure_axis_refit_20261126.md](pressure_axis_refit_20261126.md) | 2026-11-26 | 压力轴两参数重标定：最坏总误差 5.715 → 2.840 mmHg、17/17 落规格内；改前 2/4、改后 8/8；代价是 AAMI 6/7 → 5/7（P4 SBP 靠旧轴偏移凑出来的） | 现行（标定变更，含诊断与代价） | 17 点静态基准 8/17 → 17/17 落 BP Pump 2 自身规格；差值斜坡 -0.9686 %/100 mmHg（R2 0.7888）被消掉；新值 81.529 / -20.03 隐含供电 5.1994 V vs 实测 5.133/5.149；改前三组 sweep 2/4（最坏 4.52）、改后 8/8（最坏 2.61）；T0 可声明 0/21 → 2/21（P1 MAP +0.39、P3 MAP +0.82）；T3 免疫（SBP p 0.04661 → 0.04643）；266 轮重映射冻结门 0 翻；轴只解释 0.8-1.8 % 方差，修的是偏不是抖 |
| [release_blockers_20261126.md](release_blockers_20261126.md) | 2026-11-26 | 发布前四件事的处置：凭据进 gitignore 且可检测、历史归档与来源未确认遥测移出版本库、体积选 B 策略；仓库地址仍在等 URL | 现行（发布处置记录） | 1031 文件 2.3 GB 移出 HEAD；checksums 2488→1707 文件；工作树 2570→362 MiB；pack 仍 457.72 MiB，历史未清 |
| [release_package_20261126.md](release_package_20261126.md) | 2026-11-26 | 发布包与数据可用性：62 轮/147 文件/30.1 MB 可独立下载并校验；已作为 Release `v2026-11-26` 的 zip 附件发布；代码 MIT、数据 CC BY 4.0 | 现行（发布物声明） | 62 轮、147 文件、30.1 MB；层 18/20/20/4、门 58+4；7 种破坏反向测试 8/8；dist/ 不入库；Release 附件 5.64 MiB，zip SHA-256 `45e6912fb9c873c27f4c8dad375bee7c7705a2c0869c65c91b833eaf4e62cd43` |
| [static_crosscheck_20261126-111028.json](static_crosscheck_20261126-111028.json) | 2026-11-26 | 改标定前的最后一次静态交叉验证（旧轴 82.326 / -19.887）：4 点 12 窗口 | 数据图表（旧轴，已被 pressure_axis_refit_20261126.md 引用） | mcu 44.00/102.10/167.30/225.40，差异 -1.00/-0.10/-2.30/-2.40，落规格 2/4，最坏总误差 4.52 mmHg；自拟合隐含斜率 81.4455；零点漂移 +3.7 mmHg |
| [static_crosscheck_20261126-112810.json](static_crosscheck_20261126-112810.json) | 2026-11-26 | 改标定后的静态交叉验证 A 组（新轴 81.529 / -20.03）：4 点 12 窗口 | 数据图表（新轴，已被 pressure_axis_refit_20261126.md 引用） | mcu 28.80/86.50/177.40/241.90，差异 +0.20/+0.50/-0.40/+0.10，落规格 4/4，最坏总误差 2.31 mmHg；同一批读数用旧轴解释则 2/4、最坏 4.81 |
| [static_crosscheck_20261126-114022.json](static_crosscheck_20261126-114022.json) | 2026-11-26 | 改标定后的静态交叉验证 B 组（新轴 81.529 / -20.03）：4 点 12 窗口，压力点与 A 组错开 | 数据图表（新轴，已被 pressure_axis_refit_20261126.md 引用） | mcu 50.40/113.50/140.60/221.50，差异 +0.10/-0.50/+0.40/+0.50，落规格 4/4，最坏总误差 2.61 mmHg；30 点合并后斜率收敛在 81.49-81.53 |
| [v6_baseline_20261126.json](v6_baseline_20261126.json) | 2026-11-26 | 冻结 v6 的基线重算输出：18 轮 frozen_baseline_v2 在新轴上的逐轮误差与两种 sd 口径 | 数据图表 | 6038 B sha256 96ec6a948afa36c2…；确定性（同输入两次运行字节相同）；pinned 轴 + capture 轴两套读数并列 |
| [dataset_limitations.md](dataset_limitations.md) | 无日期戳（mtime 2026-11-15） | 数据集局限总声明，26 条（含 v5 前瞻失败、P4 不可辨识、三视图非前瞻验证、压力轴已重标定） | 现行 | 26 条、压力轴旧轴 ±5.7 → 新轴 2.840、P4 出数 66.7% |
| [prospective_progress.md](prospective_progress.md) | 无日期戳（正文引用 20261107 脚本） | 前瞻 v1+v2 完成：v1 18/20，v2 的 P4 拒判 70% 是最大发现 | 现行 | 18/20、P4 拒判 7/10、阀故障 4/40 |
| [dataset_scope_statement.md](dataset_scope_statement.md) | 无日期戳（正文最新 2026-11-11） | 数据集核心声明：62 发布轮 MAP 过、SBP sd 超，仅 P1 三项全过 | 现行 | 62 轮、MAP +3.66/4.73、SBP sd 9.20 |

## 3 时间线

覆盖 **2026-10-31 → 2026-11-26**（27 天），另有 3 份无日期戳文件。节奏可以切成九段，每段的产出性质不同：

| 段 | 日期 | 文件数 | 这一段在干什么 |
|---|---|---|---|
| 排障期 | 10-31 → 11-01 | 86 | ADS 总线故障、阀1 隔离、阀端二极管、UART 带载失败；首批 Standard BP 四轮采集与回放 |
| 方法与容积之争 | 11-05 → 11-08 | 72 | 高压 255/195 容量 3300 失败 / 4200 成功；峰区窗口；A/B 噪声归因；注射器测容积、回路容积 153→320 cc |
| 口径与参考 | 11-09 → 11-11 | 69 | 容积定案、振幅比、独立参考、MAP 偏置、DBP 可辨识性、[GAUGE] 副作用、面板≈串口、压力轴有界声明 |
| 精度天花板 | 11-12 → 11-14 | 25 | v4/v5 冻结与否决、三视图估计器、极限环、Preset3 vs 4、零点漂移、合规性核算 |
| 收尾、预注册与批次开跑 | 11-15 → 11-16 | 9 | P2 两轮重采与标签处置、precision_levers、sbp_levers、跨天批次预注册、11-16 两个重算产物、跨天批次 D1（块A 14 轮，块B 缺席）、amend2 门控溯源 |
| 批次进行中 | 11-17 | 1 | 跨天批次 D2：首个完整天 28 轮，amend1 切换重试首次实战、amend2 收尾门控首次实战 |
| 批次进行中 | 11-18 | 1 | 跨天批次 D3：第二个完整天 28 轮无失败；上午 +4.9 mmHg 台阶查实为传感器线松动 |
| 批次进行中 | 11-19 | 1 | 跨天批次 D4：第三个完整天 28 轮；4 次失败全补齐（2 次超压 + 2 次桥接通路）；COM12 假死靠改波特率唤醒 |
| 批次进行中 | 11-20 | 1 | 跨天批次 D5：第四个完整天 28 轮；三次失败全是超压保护，超压与峰值无关，只看 25 ms 采样格点；线圈偏移塌到 +0.37 |
| 批次进行中 | 11-21 | 1 | 跨天批次 D6：第五个完整天 28 轮；开机 SENSOR_INIT 靠 0.6 s start/stop 清掉；1 轮死于单字节乱码；profile normal 复位失败 23/28 |
| 批次进行中 | 11-22 | 1 | 跨天批次 D7：第六个完整天 28 轮；一次 raw=0 零电压坏样本被当 VALID；两次超压都在 target reached 后 18–20 ms；块B 覆盖块A 13 份日志；漏率与阀 flow 同日大降 |
| 批次进行中 | 11-23 | 1 | 跨天批次 D8：第七个完整天 28 轮 + 9 个失败 slot；5 次超压（单日最多）含 1 次无到压行；块B 重缠把零点顶到 +1.6 致 profile 连败 4 轮后自愈；采集前一次 MCU PIN 复位 |
| 批次进行中 | 11-24 | 1 | 跨天批次 D9：第八个完整天 28 轮 + 2 个失败 slot；开工前 ADS1115 间歇失联（`HAL_I2C_WRONG_START`，errors 爬 4→20），早上 profile peak 五连败实为读数不可信；profile normal 复位 28/28 全失败；COM12 第三次假死要连扫三次波特率 |
| 批次进行中 | 11-25 | 5 | 跨天批次 D10（最后一天）：第九个完整天 28 轮（27 可用）；第一次编排被 Windows 12:08:35 自动重启打断、写通道只能靠物理拔插恢复，整天作废重跑；重跑里 1 轮被冻结门判 `REJECT`（峰窗降压 −16.14 mmHg/s，降压阀丢了 3 秒节流）；批次收尾 266/280。同日下午批次跑满后解除「不看答案」纪律，跑 T0–T4 判定并落 `crosstday_verdict_20261125.md`。当晚按 amend3 把规则 10 落进入库判定器（`tools/crosstday_judge.py`），T3 的 SBP 日项由此定案为「复现」；随后按 amend4 把编排器提升到 `tools/` 并给日志名加块字母，同时写出 27 个失败 slot 的逐条归因；最后追查 D10 那轮被冻结门拒绝的原因，落 `deflate_throttle_loss_20261125.md`（全库其实 5 例、机制是闭环绕档后一次性泄放、已发布 62 轮里有 4 轮正是其中四例） |
| 标定变更 | 11-26 | 7 | 压力轴重标定：17 点静态基准的线性斜坡（−0.9686 %/100 mmHg）用一条 `cal write 81.529 -20.03` 消掉，最坏总误差 5.715 → 2.840 mmHg、落规格 8/17 → 17/17；当日三组独立扫描改前 2/4（最坏 4.52）、改后 8/8（最坏 2.61）；随后用新轴重算全部 645 份导出——跨天池 6/7 → 5/7（P4 SBP 翻不过）、T0 0/21 → 1/21、T3 免疫、门只多拒 1 份、266 轮不用重采门 0 翻；稍后又补上发布层——代码 MIT / 数据 CC BY 4.0、`CITATION.cff`、62 轮可独立下载并校验的小包（147 文件 / 30.1 MB）、`dist/` 不入库；当天最后处理发布前四件事——`cloud/` 凭据写进 gitignore 并有了 `tools/scan_secrets.py` 可检测、`archive/historical/` 与 15 份来源未确认遥测移出 HEAD、体积选 B（遥测 2.2 GB 不再跟踪，固件 `[BP]` 结论抽成 `data/device_verdicts.json`）、仓库地址仍等 URL；checksums 2488 → 1707 文件，跟踪树 2580 → 362 MiB，但 pack 仍 457.72 MiB。当晚发布落地：GitHub 连上后在 `lcr-123` 下建仓库 `blood-pressure-oscillometric-bench`，按「另建干净仓库、只推当前状态」的裁定把当前树做成 orphan 快照推上去（`git write-tree` 与本地 `master` 树逐字节相同，远端 `master` 只有 1 个提交，本地 144 个提交不发布），先 private 验证、验收通过后改为 public；克隆验收时抓到一处真缺陷——`.gitattributes` 只给数据扩展名标 `-text`，任何 `core.autocrlf=true` 的机器克隆后 `tools/*.py` 会被写成 CRLF，`tools/verify_freeze.py` 用工作树字节算指纹于是报「冻结记录被改」；补一条 `* -text`（`e70bc84`）后用 autocrlf=true 的新克隆复验，`4 freeze record(s) intact` 与 `ok=1707` 同时通过 |

十六个转折点值得单独记住：
- **11-26**：压力轴重标定（`pressure_axis_refit_20261126.md`）。这不是"再采一批"能解的问题：
    17 点静态交叉验证的差值是一条**斜坡**（`tester − mcu` 从 −1.0 单调走到 −3.42，
    斜率 −0.9686 %/100 mmHg、R² 0.7888、残差 max 0.772），所以两参数标定就够
    （加二次项 `F(1,14)=3.08` 不显著）。修法是 `p_new = (1+b)·p_old + a` 推出的
    `cal write 81.529 -20.03`（**截距也要乘 `(1+b)`**，漏了会再偏 0.2 mmHg）。
    **改前 2/4 落规格（最坏 4.52）、改后 8/8（最坏 2.61）**，30 点合并后斜率收敛在
    81.49–81.53。三条必须一起记住的代价与边界：①**AAMI 七档 6/7 → 5/7**，P4 SBP 由
    −2.91 变 −5.88 —— 旧轴在 P4 的 +2.97 系统偏移正好把误差推向 0，**原来那一档是尺子
    错了之后碰巧对的**（235 轮满分口径是 −5.682，重标定报告里那个 −5.88 是 27 轮近似，
    以重算报告为准）；②**T0 可声明 0/21 → 1/21**——只有 **P1 MAP +0.602**（半宽 4.159，
    和 4.761 ≤ 5.00）翻成可声明；重标定报告写的 2/21 是"把每档轴移加到冻结均值上、
    半宽不变"的近似算法，把 P3 MAP 也算进去了，实跑 T0 时 P3 MAP 得 **5.127**（差 0.127）
    仍不可声明，**正式数字是 1/21**；而 **T3 完全免疫**（SBP p 0.04661 → 0.04643），因为
    轴误差是压力档位的函数、被模型 preset 主效应吸收；③**轴只解释 0.8–1.8 % 的方差**，
    修的是"偏"不是"抖"，单次 95 % 区间仍是 SBP ±12.4。另发现一个固件缺陷：`bp_cal.c:137`
    `BP_Cal_Write()` **只 Program 不 Erase**，所以改标定必须先 `cal clear`，否则
    `cal write` 静默失败、旧记录原样保留。
    **同日下午补上另一半（`pressure_axis_rebook_20261126.md`）**：换尺子后仓库里所有已发表的
    血压数字都还是旧轴算的，所以把 645 份导出全量重算了一遍。方法只改一个入口——
    `reference_bp.load()` 是所有消费者（门、`estimate()`、`views_for()`、`judge.collect()`）
    取压力的唯一通道，patch 它即可，工具一行未改。结果：**跨天池成员两轴完全相同
    （235 轮、状态分布逐项相同）**，但数字从 MAP −0.50/4.03、SBP +0.50/6.31、DBP +2.26/3.73
    变成 **−1.86/4.06、−1.08/6.49、+1.05/3.60，七档 6/7 → 5/7**；均值整体移 1.2–1.6 mmHg、
    sd 几乎不动，与"轴只解释 0.8–1.8 % 方差"一致。T1 两轴都 FAIL 但 **offset 符号翻转
    （−0.73 → +0.90）**，结论不变；T4 静默 >20 轮从 20 涨到 26（多出来的是原来被旧轴负偏移
    压住的轮）——**不是变坏，是变真**。冻结门只多拒 1 份（`standard255_195_20261105-103250`，
    斜率 −3.977 → −4.055），跨天仍只有 `135554`，**266 轮一轮都不用重采**。
    `covered_bp` 的偏移常量（−5.31 / 0 / −1.16）仍按旧轴拟合，本报告算了三种做法
    （保持 / 机械平移 / 新轴重拟），**跨天池都是 5/7、失败档都是 P2+P4 的 SBP**，所以不改，
    留给 v6 处理"常量与硬件轴不匹配"这件事。

- **11-08**：容积从 153 cc 改为 320 cc 的分水岭；同日也发生了一次归因反转（`analog_fault_20261108.md` 判接触不良 → `ab_result_20261108.md` 归因为手压活塞）。
- **11-11T09:49:47**（commit `5066fc5`）：冻结 v3 的分界点。此后采集的轮次必须先用于验收测试，在统计上被隔离——这就是"62 轮已发布语料"与"308 轮三视图语料"两个口径的来源。
- **11-15**：`standard_conformance` 从 232 轮换到 297 轮（剔掉 11 轮的固件不符 + 处置 P2 两轮面板未确立），P2 从三项全 FAIL 变成三项全 pass。同一天 `precision_levers` 把 P5/P7 的 SBP 判为"未判定"而不是 FAIL。
- **11-16**：跨天批次 D1 开跑（`crosstday_d01_20261116.md`）。同日两次协议修订——`protocols/reference_bp_batch_crosstday_v1_amend1.md`（面板切换重试）与 `..._amend2.md`（收尾门控改以 seal 态零点为准）。按协议铁律，v1 与 amend1 在改动日终止且产出为零，**D1 起算日 = 2026-11-16**。amend2 的证据在 `crosstday_amend2_vent_offset_20261116.md`：vent 态读数带着阀2 线圈偏移（+0.47…+7.1 mmHg，随热态变化），旧门控的 `est ≤ 6.0` 实际上在测线圈温度。
- **11-17**：跨天批次 D2 是**第一个完整天**（`crosstday_d02_20261117.md`，28 轮，块A + 重缠后块B 各 14 轮，`half_day` 不置位）。两份协议修订首次实战：amend1 的切换重试让块B 首档一次 ACK（D1 连续三次死在此处），amend2 的收尾门控全天 28 轮通过。同日记录两个跨天级的台架变化——封阀零点比 D1 整体高约 +1.5 mmHg、稳定段漏率约为历史同口径的 2 倍（阀 flow 也从 0.247 升到 0.268），成因未定，协议不据此改门控。
- **11-18**：跨天批次 D3 是**第二个完整天**（crosstday_d03_20261118.md，28 轮，零失败零重试）。同日上午的 +4.9 mmHg 零点台阶被查实为**传感器线松动**（不是温度、不是固件）：一次 MCU 复位把它压到 −0.29，两个压力循环又推回 +1.76，重插线缆后落到 −0.95；seal 后静置 170 s 读数不衰减（raw p2p 2–3）是判据。代价是第一次 D3 启动撞上 profile peak 的 +0.9 mmHg 门控而作废。同日首次出现系统性过程量差异：峰窗斜率均值 −2.39（D1 −1.86、D2 −1.89），块A 与块B 各自均值相同，成因未查。
- **11-19**：跨天批次 D4 是**第三个完整天**（`crosstday_d04_20261119.md`，28 轮，共 32 次尝试、4 次失败全部重试补齐）。这一天出现了三种「设备不回应」的不同表现：开工时 COM12 整端口假死（`[BP_VERSION]` 连 5 轮 15 s 空回、DTR/RTS 四组合与裸 `\r` 全 0 字节，**改一次波特率就恢复**）、`stale/nonmonotonic pressure timestamp`（ndjson 里一对时间戳倒退 950 ms）、`TimeoutError('ACK profile')`；另有 2 次固件超压保护，与 D1 三次完全同型（`target reached` 后 18/21 ms 触发，串口 50 ms 打印看不到那个越线点）。**全库 583 份 metadata 里 `Over-pressure` 只命中 6 轮，其中 5 轮在本批次 11-16 与 11-19**，而 D4 恰是全批峰值最低的一天（无一轮 ≥279），反证「超压与峰值高低无关」。同日峰窗斜率 −2.331（块A −2.306 / 块B −2.356），与 D3 的 −2.390 构成一个新档位；块B 零点却比块A 高 0.31 mmHg 且内部单调上移，是四天里第一次。
- **11-20**：跨天批次 D5 是**第四个完整天**（`crosstday_d05_20261120.md`，28 轮）。三次失败全部是固件超压保护（`[Safety] Over-pressure; emergency vent`），而且三次都发生在 `target reached` 之后 **17–21 ms**——正好一个 25 ms 控制周期，因为 `main.c:794` 的超压判定在同一 tick 里排在 `main.c:805` 的到达目标判定之前。串口 `[Pressure]` 按 50 ms 打印，是 2 倍抽取，所以那个越线的样本从来不进 trace。**全库 527 次充气里 9 次超压，只出现在充气斜率中位 ≥82 mmHg/s 的日子；9 次里有 5 次串口峰值连 277 都不到**，而唯一显示 `280.0` 的那一轮（11-16 `-194325`）反而没超压——判定只看"某一个 25 ms 样本是否 ≥280"，与整轮峰值无关。同日线圈偏移塌到 **+0.37 mmHg**（D1 以来最小，两个阀态都读负值，此前从未出现）；阀 flow 升到 0.33333 仍未收敛；峰窗斜率 −2.500 是五天最陡，**三个离群点（−3.34/−3.34/−3.40）全在 P4**。另有一条工程教训：第一遍跑被 agent 会话重启连子进程杀掉，改用 `DETACHED_PROCESS` 分离进程后才跑完，日志见 `tmp/start_d5_detached_20261120.py`。
- **11-21**：跨天批次 D6 是**第五个完整天**（`crosstday_d06_20261121.md`，28 轮，块A 多花 1 个失败 slot、块B 零失败）。这一天补上了此前三个未解现象中的两个半。①开机锁存了新的故障码 **`[Fault] code=3 name=SENSOR_INIT`**（`main.c:1947-1953`，ADS1115 探测失败过 11 次又自行恢复），而采集脚本的白名单只认 `name=SENSOR_READ`（`bp_standard255_195_target275_peakwindow_20261105.py:260-264`），会直接抛 `initial sensor fault` 中止整天；用 `start` → 0.6 s → `stop` 借 `ManualPump_Start` 内部的 `BP_Control_Reset()`（`main.c:699`）清掉，代价是那 0.6 s 真的进气约 +6.9 mmHg。②块A 第 2 次尝试死于**一个 U+FFFD 乱码字节**（`bp_sealed_hold30_20261031.py:15-20` 的守卫把任何 `\ufffd` 当不可判定证据），该轮只覆盖 30.9 s；全库 623 轮里同型只 2 例（11-13 `-165250` 与今天），MCU 侧 `rx_errors` 全天 0，说明坏字节产生在 UART 之后、UTF-8 解码之前。③**28 轮里 23 轮的 `profile normal` 复位被拒**（`[Profile] rejected: require inactive sealed fresh calibrated zero`），成功 6 轮的收尾零点 +0.069…+0.721 与失败 23 轮的 +0.923…+2.529 **完全不重叠**，分界正是同一个 `-1..+1` 固件门；复位失败会让下一轮读到 `peak` 而跳过换气，块B 后半段零点因此整体下一个台阶（前 8 轮 +1.147 → 后 6 轮 +0.250），但 `-122940`/`-123631` 两个反例说明不是逐轮一一对应。峰窗斜率回到 **−1.93**（D3–D5 连续三天在 −2.3…−2.5），是本批第三次整体换档；阀 flow **首次回落** 0.33333 → 0.32042。零点 pre/post 均值 +1.114/+1.545 是本批最高。
- **11-22**：跨天批次 D7 是**第六个完整天**（`crosstday_d07_20261122.md`，28 轮，块A/块B 各多花 1 个失败 slot）。这一天第一次抓到**「零电压读数被当成有效值」**：仪表卡片阶段第一次漏率采集死在一个 `[Pressure] raw=0 ads=0mV sensor=0mV est=0.0mmHg VALID` 样本上，全库 1180 份 ndjson 里唯一一例。机理是 `ads1115.c:154-158` 把 I2C 读回的 `0x0000` 直接赋给 `*raw_value` 并返回 `HAL_OK`，`ADS1115_ReadSample`（`:203-207`）只查 status 不查数值，负压又被 `:215-218` 钳成 0，而 `main.c:461` 无条件按**校准记录是否有效**打 `VALID`——那个 `VALID` 描述的是校准，不是这一帧。②两次超压（块A `-125044` 峰值仅 274.1、块B `-140114` 峰值 278.3）都发生在 `target reached` 之后 **20 / 18 ms**，第三次复现「超压只看 25 ms 采样格点、与峰值高低无关」。③发现**编排器日志命名撞名**：`run_crosstday_20261116.py:209` 的 `{tag}_p{preset}_a{attempt:03d}.out` 不含块字母，D2–D7 每天 14 个名字被两块共用、12–14 个 slot 的日志装的是另一轮内容；但失败证据在 ndjson 里完整保留（`-125044`/`-140114` 各有 `Over-pressure`×1、`Safety`×2），所以**只损害可读性、不损害数据完整性**，改名留到批次结束后做。④零点回到本批最低（pre +0.199 / post +0.613，距 ±5.0 门余量 3.39），`profile normal` 复位失败从 23/28 改善到 **8/28**，因为今晨 profile 读回是 `normal`，D6 担心的「跨天保持 peak」没有发生。峰窗斜率 −1.885，**连续两天停在 −1.9 档（本批首次）**。漏率稳定段 **−9.25**，连续四天 −11.1…−11.6 的平台第一次松动；阀 flow **0.17630**，从 0.32042 基本减半（两个脉宽同向），是本批最大单日变动。
- **11-23**：跨天批次 D8 是**第七个完整天**（`crosstday_d08_20261123.md`，28 轮 + **9 个失败 slot**，是本批失败 slot 最多的一天）。这一天有四处新东西。①**五次超压，本批单日最多**（此前 D4 2 次、D5 3 次、D7 2 次）：四次在 `target reached` 之后 **17–21 ms**、串口峰值只有 274.1–279.9，第五次 `-132833` **连 `target reached` 行都没有**——从 −14 ms 的 274.70 一步跨到 ≥280，整个 275–280 窗口被跳过。把 `coast`（到压后 250 ms 内最高读数 − 到压值）全库分桶后拿到一个干净的分界：**617 轮有到压行的轮次里，coast ≤ 0（到压那一帧就是整轮最高读数）的 493 轮出了全部 13 次超压，coast > 0 的 124 轮一次都没有**；而到压值本身（超压组 275.9…279.9）与 604 个正常轮（p50 276.4 / p95 278.8）完全重叠，顶部加压速率（96.8 vs 90.3 mmHg/s 中位）也分不开。②**重缠袖带这个动作本身会把零点顶出 `profile` 门**：块B 开局 `preset 1` 连丢四轮（`-123424`/`-123629`/`-123834`/`-124039`，`RuntimeError('profile peak could not be set: …sealed true zero above +0.9 mmHg; profile set needs -1..+1')`，四轮都从未充气、`closeout_confirmed=False`），从 `-124039` 末 400 样本反算真零点 **+1.66**，确实在门外；第五次 `-124244` 无干预自愈。③**17/28 轮的 pre 零点在固件 `-1..+1` 门外，其中 16 轮靠 `profile_already_peak=True` 才采成**——七天对照 D2 15/15、D5 13/13、D6 18/18、D8 17/16，说明「profile 停在 peak」在这几天其实是继续采集的**必要条件**，不是纯缺陷。④**采集前一次 MCU 复位**：第一次漏率采集在 `[Inflate] START` 后 15.387 s（压力仅 0.8 mmHg）被打断，串口抓到完整开机横幅，末尾 `[Boot] reset_csr=0x04000000 PIN`。按 `main.c:1877-1900` 的 `Boot_CaptureResetCause()` 解码：**纯 PIN 意味着 NRST 被拉低而 VDD 未掉**，不是电源塌陷（会同时置 PORRSTF）、不是 IWDG（4000 ms + `debug-freeze=ON`）、不是软复位；扫 1991 份 ndjson 全库只有 **4 例、全部 `0x04000000`**（11-09、11-10、11-21、今天），`data/raw` 下 0 例。头号嫌疑是 pyserial 打开 COM6 时默认驱动 DTR/RTS，而 `direct_serial_bridge_20261107.py:95` 没有显式置 `dtr/rts=False`。过程量方面：峰窗斜率 **−1.896**，连续三天停在 −1.9 档；零点 pre +1.135 / post +1.389（**8 轮 post−pre 为负，本批最多**，块B 均值比块A 高 0.55）；漏率稳定段 **−11.27** 回到 11-18…11-21 的平台（11-22 的 −9.25 未复现，判为单日波动）；阀 flow **0.22057** 回升，但 3 ms 0.28333 / 4 ms 0.15781 **两个脉宽方向相反**（D7 是同向减半）。另外 COM12 今天第二次整端口假死，`wake_tester` 八个 DTR/RTS 组合全 0 字节，最后仍靠**改一次波特率**（`serial_baud_20261119.py`，9600 回 20 字节）唤醒。
- **11-24**：跨天批次 D9 是**第八个完整天**（`crosstday_d09_20261124.md`，28 轮 + 2 个失败 slot，是本批目前最干净的一天：14 次切换全部一次 ACK、`dropped` 全天 0、`rx_errors` 全天 `(0,0)`）。但**开工前一小时是本批最难的一段**。①**ADS1115 间歇失联**：`[ADSdiag] err=0x00000200` 连续爆发，`errors` 从开机就带的 4 次爬到 **20** 次，raw p2p 从正常 2–8 counts 涨到 **3359**，同一小时内真零点在 −3.67…+6.91 mmHg 之间摆。错误码按 `stm32f1xx_hal_i2c.c:3577` 解出是 **`HAL_I2C_WRONG_START`（START 条件请求了但 SB 没置起）**，不是此前一直以为的 AF/NACK——从机没有拒绝地址，是主机侧连 START 都没发出去。坏读数一路无阻：`ads1115.c:154-158` 的 `*raw_value = (int16_t)conversion;` 不判 `conversion==0`，`:215-218` 把负压钳成 0，`main.c:461` 按**校准记录是否有效**打 `VALID`。`ADS1115_I2C_Recover()` 的注释自己写着「No GPIO clock pulsing; this cannot repair a slave physically holding the bus low」，而 `errors`/`recoveries` 是 `ads1115.c:15` 的静态结构、只能靠 MCU 重启归零——11:32:12 那次归零（fault `code=4`→`0`、`errors 20`→`0`、基线 sensor 306→226 mV）因此**只能是 MCU 重启**，但 11:26:43–11:31:03 之间没有客户端持有 socket，`[Boot] reset_csr` 横幅没人读到；全库重扫 2077 份 ndjson 仍是那 4 条 `0x04000000`。②**早上 `profile peak` 五连败的根因不是门**：`sealed but true 1.52/1.44/1.44/1.68/1.76 still high`，同脚本同阈值在 ADS 归零后**第一次就通过**（`sealed last sample true -0.46`）——被测量骗了，不是 `-1..+1` 门过不去。③**`profile normal` 复位 28/28 全部失败**（本批最差，D6 23/28、D7 8/28、D8 19/28），`already_peak` 27/28；把 D8 的成功组 [+0.282,+0.713] 与 D9 的失败下限 +0.809 并起来看，复位门的实际门槛落在 **(0.713, 0.809]**，约 0.75 而不是固件写的 1.0——因为固件判"最后一帧"而卡片记"窗口中位"，两者差 0.2–0.3。④**COM12 第三次整端口假死**，`wake_tester` 八组合全 0 字节、**第一次波特率扫描四档也全 0**（本批首次），第二次只回乱码（19200→409 B、38400→171 B），**第三次**才在 9600 召回 20 字节 → 判据改为「扫描必须连跑 2–3 次」。另外 `COM12` 今天不在 `Win32_SerialPort` 列表里，但注册表 `\Device\VCP0 = COM12`、`Get-PnpDevice` 为 Status=OK/Present=True/CM_PROB_NONE，**WMI 空不代表端口不在**。⑤**`coil offset` 同小时内从 +6.09 变到 +9.55（本批最大）**：11:05 四态读 seal +3.66 / vent +9.75，11:14 的 185 s seal watch 读 −0.38、11:08 的 120 s vent watch 读 +9.17 且**不衰减**——两对都是稳定值却差一倍多，比 amend2 当年那批更干净地证明「vent 读数既不是零点、也不与 seal 误差成比例」。过程量：峰窗斜率 **−1.877**，连续四天停在 −1.9 档；零点 pre +0.720 / post +1.046，**post 最大只有 +1.244 是八天最低、无一轮 >2.0**（D8 有 6 轮），且块B（+0.984）比块A（+1.108）**低**，与 D4/D5/D7/D8 方向相反；漏率稳定段 **−11.14**，连续第二天在 −11.1…−11.3 平台，坐实 11-22 的 −9.25 是单日事件；阀 flow **0.19974**，两个脉宽**连续第二天反向**（3 ms 0.28333→0.16667 降、4 ms 0.15781→0.23281 升）。


- **11-25**：跨天批次 D10 是**第九个完整天**，也是批次最后一天（`crosstday_d10_20261125.md`，28 轮但只有 **27 轮可用**）。这一天有两个"第一次"。①**Windows 在 12:08:35 自动重启**（`Win32_OperatingSystem.LastBootUpTime` 实证），把第一次编排（tag `crosstday_d10_20261125-110924`）连同块B 一起杀掉；重启后出现一个古怪状态：**主机→MCU 的读通道完全正常，写通道全死**——桥回 `Failed to write to serial port: 信号灯超时时间已到 (os error 121)`，直连 pyserial 抛 `Write timeout`。软件层能试的全试了：换三种行尾、换命令、重启 OmniProbe（35 s 后重新起来仍写不动）、停工作台后直连、`dtr/rts` 三组合、`Disable-PnpDevice`（`常规故障`）、`pnputil /restart-device`（`Access is denied.`）——**本会话不是管理员，任何 PnP 级复位都做不了**。最后靠**操作员物理拔插 MCU 的 USB 线**恢复（端口号仍是 COM6，1922 B 回包）。因为块A 的一半在拔插前、块B 在拔插后，混采会污染 T2 的重缠对照，**整天作废重跑**：48 个原始文件（15 export / 16 metadata / 17 ndjson，63,312,618 B）+ 作废日志移入 `tmp/omniprobe/quarantine_20261125/`（先例 `quarantine_20261116` 47 项、`_20261118` 9 项、`_20261120` 22 项，一律保留证据不删），卡片测量（零点/漏率/阀点，全部在 10:50–11:08 完成）不重测。②重跑里 **`B/P1 a2`（`-135554`）被冻结门 `tools/validity_v2.py` 判 `REJECT`，峰窗降压 −16.14 mmHg/s**（门槛 4.0）——**本批 266 份 export 里唯一一次越线**（中位 −1.98、次差 −3.37）。查下去不是数据坏：**降压阀在 t≈9.0–12.2 s 失了 3.2 秒节流**，从 243.4 掉到 194.9（−15 mmHg/s，单步最大 −6.82 mmHg/25 ms 约 273 mmHg/s），随后自己回到 −1.8 mmHg/s；该轮降压段只有 `[Deflate] PWM started after hold` 与 `[Deflate] done; valve2 closed` 两条非压力行，**固件全程没报任何故障码**，只有事后算斜率才看得见。全库另有 2 例同型（2026-11-07 的 `-32.87` 与 `-16.81`，爆发段 3–7 s），说明这是**低频但可复现的执行器故障，而冻结门抓得住它**；协议没有"门拒绝就补采"的条款，这一轮按 §4 规则 5 排除、不重采。过程量方面：峰窗斜率 **−1.900**（连续五天停在 −1.88…−1.93，是本批最稳的一段）；零点 pre +0.043 / post +0.339，**post 最大只有 +1.046 是十天最低、无一轮 >2.0**，余量 3.95；块B（pre −0.161 / post +0.155）比块A 低，是十一天里第二次。漏率稳定段 **−17.63**，**首次离开 −11.1…−11.6 平台**——但同一份轨迹里有**规律锯齿**（36 次 >1.5 mmHg 上行、最大 1.90、20 s 后平均间隔 1.27 s；前三天 28 / 0 / 13 次），形态是每 ~0.75 s 一个台阶再线性回落，**所以"稳定段斜率"其实被台阶数决定，−17.63 与 −11.1…−11.6 可能是同一条阶梯的两种取法**。阀 flow **0.18412**（3 ms 0.12917 降 / 4 ms 0.23906 升，**两脉宽连续第三天反向**）。`coil offset` +5.35 居中；ADS1115 与昨天相反，**全天干净**（8 窗 ×5 s 与 6 窗 ×4 s 全部 `bad=0`）；COM12 第一次就 ACK，无需波特率扫描。`profile` 连续第四天 `normal`，11:07:02 一次设上 `peak`。批次到此收尾：**266 轮 / 280 = 95.0%**（D1 14 + 九天 ×28 = 266，已达可达上限），27 个失败 slot 的成因是超压 19、`profile peak` 设不上 4、单字节乱码 1、`stale/nonmonotonic` 1、`TimeoutError` 2、`incomplete export` 1。
- **11-25**（判定，同日另一件事）：批次跑满 280 轮之后解除"不看答案"纪律，按预注册协议跑 T0–T4。
  - **T0**：21 个 档×量 格里 **0 格可声明"在 5 mmHg 内"**（20 格 undecided、1 格 FAIL）。唯一 FAIL 是
    **Preset 4 的 SBP（−15.19，日聚类 CI [−22.07, −8.31]，n=32）**——与 §2a 的物理限制（净空仅 6 mmHg、
    刚性平台）一致，但这是**第一次在预注册的完整交叉设计上把它判成 FAIL**。半宽中位 4.61、最小 4.14：
    按协议"CI 整体落 ±5.0"的规矩，21 格里只有 3 格的均值够靠近 0，而它们的半宽就把预算吃光了。
  - **T1（主检验）FAIL**：前五天拟合 `d = −1.3254`，加到后五天把 late mean 从 −1.6414 推到 **−2.9668**
    （离 0 更远），`improvement = −1.3254`（要求 ≥ +0.5），`late_sd 12.47`（要求 ≤ 8.0）。
    → **加性 SBP 偏移在这 10 天上没有迁移性**；开发集 `+2.00` 与留出层 `−3.07` 符号相反
    **不是那两批的偶然，而是台架常态**。`SBP_OFFSET_MMHG` 保持 0.0。
  - **T2 通过**：`Δ_wrap = −1.083`（95% CI −5.283…+3.116），小于本设计 1.81 的检出限 →
    "缺少可指名的机理解释"继续成立，且现在能写"袖带缠绕已排除到这个量级以下"。MAP −0.996 / DBP −0.036 同向；
    cell 级有 −77.18/+63.78 的极端值（每格只有 2 轮），所以这是**批次层面**的陈述。
  - **T3 按规则 10 定案，SBP 与 DBP 复现**：协议 §4 规则 10 规定 T1/T3 只用完整日，
    按该口径（D2–D10，**251 轮**）**SBP `p = 0.0313` 复现、DBP `p = 0.0208` 复现、MAP `p = 0.4413` 不复现**；
    实测 `sw/sb` 是 **15.863/1.151、7.740/0.000、8.772/0.939**，与协议 §1.1 的 `5.40/2.32` 并列时
    `sw` 差 3 倍、`sb` 掉到 ≈0（ICC 0.005/0.000/0.011）。
    **冻结脚本从未实现规则 10**（它含 D1 的 `half_day`，265 轮给出 SBP `0.0572` / MAP `0.1001` / DBP `0.0174`，
    `sw/sb` 17.206/0.000、11.293/0.000、12.237/1.469），那个读数作为同一判定的另一半并列保留，
    引用时不得只取一方。翻转机理：D1 那 14 轮残差 sd **32.41**（其余块A 123 轮只有 14.91）把 `sw` 抬高 9%，
    F 掉 14%；**留一法 12 次只有剔 D1 能翻**，**四种完整日谓词全部 < 0.05**。
    因此 `precision_levers_20261115.md` §3.2 的"跨天采样"建议**确认、不撤回**，但"摊天数就能达标"仍不能写。
    规则 10 的实现放在入库的 `tools/crosstday_judge.py`（不改冻结脚本，否则已发表的 0.0572 不可复现），
    操作定义与回归约束见 `protocols/reference_bp_batch_crosstday_v1_amend3.md`。
  - **T4 并列**：冻结 v2 发布 **259/265 = 0.977**、静默 >20 **20 轮**、可声明 **0/21**；
    `covered_bp` 发布 **248/265 = 0.936**、静默 **2 轮**、可声明 **15/21**。
    但两者半宽差一倍的主因**不是 n**，而是 `se_half = 1.96·se_clustered` 的日聚类 SE：
    v2 的 18 轮长尾集中在 D1–D4（14/18），日均值整天往外跳，聚类 SE 被放大；`covered_bp` 把它们拒判掉了。
    → "靠多拒判赢"正是协议 §3 T4 明令要防的比较，两估算器的 claimable 数**不可直接比**。
  - **规则 10 定案 + 三项描述性敏感性**（改判定的只有规则 10）：①完整日口径是**判定**不是敏感性；②实测方差分量代入协议公式后，
    SBP 要半宽 2.55 需 **38 天**、MAP **9 天**、DBP **12 天**（协议 §1.2 是按 `sb=2.32` 算的，
    本批实测 `sb≈0`，方向一致但量级差很多）；③**剔掉 18 轮 |SBP|>20 的长尾（6.8%）后 T1 翻成 PASS、
    T3 三项全部 p<0.05、剩余 241 轮 mean −0.36/sd 8.24**——所以本批的 FAIL 主要是 7% 灾难性缺失驱动的，
    不是整条分布平移；④逐格"还需多少天"（P2/P4/P5 的 MAP、P2/P3/P4 的 DBP 都在 2–3 天内可判定）。
  - **库内改动（三处，都是协议要求的产物）**：`dataset_limitations.md` 新增 §25（加性偏移不可迁移 +
    §25a 与 §23「日间方差占 8.4–26.6%」的口径差别 + §25b 长尾解读 + **§25c T3 的两种口径**）；
    `precision_levers_20261115.md` §3.2 的判定标注**确认「跨天采样」建议**；
    `protocols/reference_bp_batch_crosstday_v1_amend3.md` 写死规则 10 的两个谓词并修 §7 两处跑不通的命令。
  - 复现：`python tools\crosstday_judge.py --rule10 both`（`--rule10 off` 必须逐字段复现
    `python tmp\crosstday_analyse_20261116.py --json data\reports\crosstday_analysis_20261125.json`）；
    自检 `python tools\crosstday_judge_selftest.py`；三项敏感性见报告 §7.2–§7.4。

- **11-25**（阀失节流，同日第三件事）：D10 那轮被冻结门拒绝的 `-135554` 追下去发现**全库共 5 例**（不是 D10 日报说的 3 例）：`…20261107-212915` −33.40 / `…20261107-215245` −16.96 / `…20261125-135554` −15.18 / `…20261107-202606` −14.32 / `…20261107-154020` −13.76，健康轮中位 −1.917。机制不是"阀被关掉"而是**阀端气阻先崩溃、闭环每 400 ms 加 1 ms 把开阀时间绕到 14–29 ms、气阻一放开绕上去的占空比就一次性泄掉 3–9 mmHg**（`main.c:2142-2170` 闭环、`main.c:2125-2132` 脉冲、`main.c:384-395` SysTick 关阀）；固件零故障码，门是唯一检测手段。**duty 是必要条件但不充分**（`duty_med ≥ 8` 的 10 轮含全部 5 例、627 轮 0 例，但余震轮 `…213751` 25 ms / `…215530` 16 ms 会误报），`gain` 比值不可用（82 % 正常轮 ratio ≥ 3）。**已发布 62 轮里 4 轮正是其中四例**（`USABLE 58 / REJECTED 4`），三份冻结记录给了三种处置。


## 4 同主题簇

跨四份清点表合并后的主题簇（同一件事的散落文件）。要查一件事时先在这里定位簇，再回 §2 看逐个状态。

| 主题 | 成员（要点，非全量） | 现在的落点 |
|---|---|---|
| ADS 总线故障与阀端隔离 | `ads_bus_retest_20261031-153810.md/.json`、`ads_switching_audit_20261031.md`、`branch_isolation_plan_20261031.md`、`valve1_isolation_20261031-154115.md/.json`、`valve1_diode_20261031-181000/181318/183711.md`、`valve_end_diode_low30_20261031-183921.*` | 阀端二极管接好后失读未复现，但 `valve1_isolation` 的通信中断根因仍 unresolved（§5-B2） |
| 回路容积 | `pressure_step_first_result_20261108.*`、`volume_without_water_20261108.md`、`volume_disagreement_20261109.md`、`valvefree_result_20261109.md`、`dataset_loop_volume_result_20261109.md`、`volume_crosscheck_20261109.md` | **320 cc（测量工况）/ ≈340 cc（数据集工况）**；153/158/176/252/357 cc 全部作废但仍留在正文（§5-A3） |
| 零点的两种现象 | `zero_observation_20261031-132735-752183.json`、`valve2_zero_20261101-112951.md`、`valve2_zero_repeat_20261101-154528.md`、`zero_drift_20261112.md`、`zero_reference_plan_20261101.md` | 开阀/封阀电气偏移 ≈+2.6…+3.9 mmHg 与 封阀态随时间的缓漂 是两件事，不可相加（§5-C7） |
| 压力轴与独立参考 | `static_crosscheck_20261110*.md/.json`、`static_crosscheck_2026111{1,2}-*.json`、`pressure_axis_accuracy_20261111.md`、`pressure_axis_bound_20261111.json`、`independent_reference_20261109.md`、`panel_vs_gauge_20261111-*.json`、`panel_beep_20261111-220624/220931.json`、**`pressure_axis_refit_20261126.md`（换尺子本身）**、**`pressure_axis_rebook_20261126.md`（换尺子后的账本重算）**、`static_crosscheck_20261126-111028/112810/114022.json` | **旧轴**最坏 ±5.7、典型 ±2–3 mmHg（`pressure_axis_accuracy_20261111.md`，2026-11-11 口径）；**新轴**最坏 2.840、落规格 17/17（11-26 重标定），但引用任何覆盖率数字时必须带轴的口径——跨天池 6/7 是旧轴、5/7 是新轴；"面板≈串口"只有 6 个节拍支撑（§5-C3） |
| 高压档（Preset 4） | `preset4_two/three_rounds_20261109.md`、`preset4_recovery_20261111.md`、`p4_steepness_target_20261113.md/.json`、`sbp_headroom_20261109.md`、`dbp_identifiability_20261109.md` | 出数率上限 84%、SBP 净空 6 mmHg、DBP 不可辨识；"做陡包络"这条路已否证 |
| 估计器版本链 | `reference_bp_20261107.*`、`ratio_method_final_20261108.json`、`rebuilt_envelope_20261107.md`、`smoothing_window_correction_20261108.md`、`covered_algorithm_20261113/14/16.*`、`v4_*`、`v5_validation_20261114.*`、`preset3_vs_preset4_20261114.*` | **冻结 v2 是参考算法**；v3/v4/v5 全部否决；三视图估计器是候选不是替代（§5-A1） |
| 合规性核算 | `standard_conformance_20261114.md/.json`、`standard_conformance_20261115.json`、`standard_conformance_20261116.json`、`statistics_convention_20261111.md`、`standard_bp_preset_matrix_20261106.md` | 15/16 号是同一结果的两次归档；判分口径以这两份为准（§5-A1、§5-B3） |
| 发布与交付 | `release_package_20261126.md`、`release_blockers_20261126.md`（四条阻塞的处置、「HEAD 移除 ≠ 历史清除」、13 份跟踪面例外文件的裁定）、`../release/published_corpus_20261126.json`、`../../tools/release_package.py`、`../../tools/verify_release_package.py`、`../../tools/scan_secrets.py`、`../../LICENSE`、`../../LICENSE.md`、`../../data/LICENSE`、`../../CITATION.cff` | 62 轮 / 147 文件 / 30.1 MB 可独立下载并校验；代码 MIT、数据 CC BY 4.0。**已发布到 <https://github.com/lcr-123/blood-pressure-oscillometric-bench>**（2026-11-26 建，先 private 验证后改 public；远端 `master` 是单提交 orphan 快照，本地 144 个提交不发布，七个本地哈希在远端不可解析但已逐个登记、且无一处被校验命令读取）。**最小下载路径是 Release `v2026-11-26` 的 zip 附件**（5.64 MiB，不必克隆 362.4 MiB）。克隆后跑 `tools/verify_checksums.py` 与 `tools/verify_freeze.py` 均为绿 |
| 面板操作规范 | `bp_pump2_panel_setup_20261109.md`、`gauge_command_side_effect_20261109.md`、`gauge_side_effect_20261109.md`、`p2_panel_recollect_20261115.md` | `[GAUGE]` 会切走 Standard BP 屏、采集期间禁用；`[SIM_STD*]` 只承诺 ACK 不证明面板动了 |
| 数据清洗与清点 | `capture_catalog_20261031.*`、`export_inventory_audit_20261107.md`、`data_quality_assessment_20261110.md`、`dataset_limitations.md`、`dataset_scope_statement.md` | "总导出数"有三口径（102/67/70）；"发布语料"有两口径（62/308）（§5-A1、§5-C6） |
| 前瞻与协议 | `prospective_progress.md`、`prospective_preflight_20261031-132512-832862.json`、`topup_batch_20261115.md`、`how_far_off_and_can_it_be_trusted_20261108.md` | 协议规程在 `data/protocols/`，本目录只放结果 |
| 跨天批次 | `crosstday_d01_20261116.md`、`crosstday_d02_20261117.md`、`crosstday_d03_20261118.md`、`crosstday_d04_20261119.md`、`crosstday_d05_20261120.md`、`crosstday_d06_20261121.md`、`crosstday_d07_20261122.md`、`crosstday_d08_20261123.md`、`crosstday_d09_20261124.md`、`crosstday_d10_20261125.md`、**`crosstday_verdict_20261125.md`（T0–T4 判定，不是当日报告）**、`crosstday_amend2_vent_offset_20261116.md`、`precision_levers_20261115.md`、`sbp_levers_after_unresolved_20261115.md`、`standard_conformance_20261115.json`、**`failed_slot_attribution_20261125.md`（撞名审计 + 27 slot 归因，工程报告）**、**`deflate_throttle_loss_20261125.md`（降压阀失节流 5 例 + 已发布语料的 4 轮，工程报告）**、**`pressure_axis_refit_20261126.md`（压力轴两参数重标定，标定变更 + 代价表）** | 预注册在 `data/protocols/reference_bp_batch_crosstday_v1.md`（+ amend1/amend2/amend3/amend4）；D1 为 **half_day**（块B 缺席），D2–D10 是**完整天**（各 28 轮；D10 有 27 轮可用，因为 1 轮被冻结门拒绝）；**十天齐全后 T0–T4 已判定并落在 `crosstday_verdict_20261125.md`**（T0 0/21 可声明、T1 FAIL、T2 通过、**T3 按规则 10 报 SBP 0.0313 / DBP 0.0208 复现、MAP 0.4413 不复现**（冻结口径 0.0572 / 0.1001 / 0.0174 并列）、T4 两估算器并列）；结论同时回写到 `dataset_limitations.md` §25（含 §25c）与 `precision_levers_20261115.md` §3.2；规则 10 由入库的 `tools/crosstday_judge.py` 实现，谓词与回归约束见 `protocols/reference_bp_batch_crosstday_v1_amend3.md` |

## 5 冲突与疑点

按"会不会误导引用"排序，不按发现顺序。每条都写明**影响**与**该怎么读**。

### A 同一指标有多个不兼容的数（最容易被上级误引）

1. **达标档数有 4/7、5/7、6/7、7/7、1/4、0/7 六种说法同时在库里。**
   `covered_algorithm_20261113.md` 写 7/7（三视图估计器、187 轮）；`dataset_limitations.md` 第 17 条写 6 档；
   `standard_conformance_20261114.md` 给 232 轮的 6/7；`topup_batch_20261115.md` 把 6/7 改判 4/7；
   `precision_levers_20261115.md` 与 `standard_conformance_20261115.json` 给 5/7（297 轮）；
   `statistics_convention_20261111.md` 按 4 预设只承认预设 1；`v5_validation_20261114.md` 是 0/7。
   **原因不是"后来推翻前面"**：档位定义、估算器版本（v2 / 三视图 / v5）、样本批次（62 / 187 / 232 / 297 / 308）三者同时变了。
   **影响**：任何一句"七档里 N 档通过"必须同时写估算器、轮数、判据，否则无法核。
   **该怎么读**：要报合规就用 `standard_conformance_20261115.json`（297 轮、七档 5/7、P5/P7 的 SBP 未判定）；
   要报"能不能用一套常量通吃七档"就用 `covered_algorithm_20261113.md`（7/7，但那是另一套估计器且不含 P5/P7 边界声明）。

2. **`standard_conformance_20261115.json` 与 `_20261116.json` 是同一结果的两次归档。**
   408 行里除 `source` 一行外完全相同（`tmp/omniprobe/covered_with_p2_recollect.json` → `data/reports/covered_algorithm_20261116.json`）。
   **怎么读**：引用数字用 16 号（指向 `data/` 下的稳定副本），但要写明"这是 15 号结论的重新归档，不是新实验"。

3. **回路容积的现行值是 320 cc，但 153/158/176/252/357 cc 全部以完整正文留在库里。**
   153 cc 在 `valvefree_result_20261109.md` 与 `volume_without_water_20261108.md` 各有作废横幅，但正文照旧；
   `single_pull_protocol_20261109.md` 内部勘误成 320 cc，同一份文件的表格仍用 176 cc/190 mmHg 举例；
   `dataset_loop_volume_result_20261109.md` 给 320 cc，`session_summary_20261109.md` 另给 ≈340 cc（数据集工况）；
   `pressure_step_first_result_20261108.md` 的等温 252 / 绝热 357 / 气体定律 158 三法分裂，作者自判"dV 不可信"。
   **影响**：单抓一份文件引用容积，有一半概率引用到作废值。**现行**：320 cc（测量工况）≈340 cc（数据集工况）。

4. **"发布语料"有两个互不相同的定义，两份文件都在自称发布语料。**
   `dataset_scope_statement.md` 用 62 轮（冻结 v2 守门、`5066fc5` 之前）；`dataset_limitations.md` 用 308 轮（三视图估计器发布）。
   另 `sbp_levers_after_unresolved_20261115.md` 实测"62 轮里只有 3 轮跑在当前镜像上"，与 `dataset_limitations.md` §20
   "一个语料=一代固件"直接冲突。
   **怎么读**：写"本数据集 n=…"之前必须先指明走哪条准则。`data/README.md` 的 62 轮表与三视图的 297/308 轮是**两套并列口径**，不是新旧替换。

5. **`covered_algorithm` 三个 JSON 的池化 sd 不单调。** 11-13（187 轮）MAP/SBP/DBP = −0.84/4.28、0.23/5.77、1.40/4.31；
   11-14 扩到 299 轮反而变成 −0.74/6.55、0.64/7.23、1.63/7.08（变差）；11-16 到 371 份又回到 −1.08/4.13、1.06/6.27、1.26/3.98。
   三份的轮次、固件代次、排除口径都不同（11-16 含 P2 重采）。**不可直接并列引用**。

### B 撤回与取代链

1. **撤回链没有终点标记。** `analog_fault_20261108.md`（判间歇接触不良、停止气路实验）被 `ab_result_20261108.md` 归因为手压活塞，
   但 `ab_result` 未声明前者作废；`pulse_loss_after_soak_20261107.md` 被 `preset_envelope_retraction_20261107.md` 全文推翻，
   原件正文也无作废声明；`rebuilt_envelope_20261107.md` 的归因被 `smoothing_window_correction_20261108.md` 撤回，原件仍独立留存。
   **影响**：按文件名检索会读到被推翻的结论。**怎么读**：看 §2 的状态栏，不要看文件名。

2. **阀1 失读到底修没修好，三份同日文件结论相反。** `valve1_diode_20261031-181000.md`（仍复现）、`-181318.md`（再复现）、
   `-183711.md`（阀端二极管接好后未复现），相隔不到 4 小时，差别只在二极管装在哪一侧；而 181000 的标题也写着"带二极管"。
   `valve1_isolation_20261031-154115.json` 记的通信中断**根因至今 unresolved**。
   **影响**：11-13 的 `valve_glitch_despike_20261113.md` 说"毛刺不值得动硬件"是**单点毛刺**，不能拿来收口**通信中断**这条未结故障。

3. **`standard_bp_peak_instability_20261105{,.json,.md,.png}` 与 `…_reviewed{…}` 双份并存、无取代标记。**
   png 逐字节相同（同 SHA256）；json 只差 `code_sha`；md 只差 3 处文字。原版未标废弃。**属可清理的重复，不是两个结果。**

4. **`standard_bp_envelope_stability_20261105.before.json` 把 `…111540` 轮记为 `envelope_candidate`、峰 215.0，
   而 `.adaptive.json` 与 `.json/.md` 改判 `bin_origin_peak_unstable` 并弃判。** before 文件内无 superseded 字段。
   **影响**：单引 before 会得出相反结论。

5. **v3 的"部分裁决"三份 JSON 的 `verdict` 字段都写 "v3 FAILS"。** `reference_bp_v3_validation_partial_p4.json`、
   `_partial_3presets.json` 仅靠 `NOTE` 标注非正式，而 `invalid_for_acceptance_test` 均为 `false`。
   **影响**：脚本批量汇总会把半裁决当正式裁决。

6. **`reference_bp_20261107.json`（DBP 比例 0.60、2 s 中值）与 `ratio_method_final_20261108.json`（DBP 0.45、逐搏峰峰）
   是两代估算器，文件名族相近。** 混用会得到不同的 SBP/DBP。

7. **同一份文件一半被撤回、一半仍在用。** `leak_and_pulse_20261107.md` 的"200 mmHg 以上无脉搏"已被全文推翻，
   但其泄漏数字（−6.56 vs 面板 7.0）仍被后续引用。引用前必须逐节分清哪半还有效。

8. **自我引用式取代。** `sensor_supply_alert_20261110.md` 正文写"原告警文件是 `sensor_supply_alert_20261110.md`，本文取代它"——
   取代对象与自身同名，无法确认原件是否还存在或已改名。

9. **半撤回文件。** `slope_uncertainty_target_20261110.md` 的"线性度 ±2.5%=9.4 mmHg 排第一"与"必须有第三方标准器"
   均已撤回（改为 ≤0.8 mmHg、继承 BP Pump 2 规格），但撤回依据 `pressure_axis_accuracy_20261111.md` 不在同一清点分区，
   就地核对不到。

10. **同日互斥方案无作废声明。** `round_now_waiting_pull_20261108.md`（拉 20 mL，P1=167.5）与
    `push_step_plan_20261108.md`（注射器满 28 mL、只能推入）同日并存，后者明确否定前者，两份都不指向对方，
    也都没有执行完成记录。

### C 数据文件本身的问题

1. **`standard255_195_target275_capacity4200_20261105-111540.replay.json` 的 `valid=0`、`sbp=dbp=pulse=0`**，
   而同轮 `.md`/`.diagnostics.json` 在讨论"包络峰 215 与面板一致、只缺高压交叉"。回放全零是旧固件计算失败，
   **不是采集失败，也不能当该轮血压结果**。这是本目录最容易造成误解的一份 json。

2. **`static_crosscheck_20261112-115126.json` 是一份空采集**（rows 为空、34 秒结束），却是该日期唯一的静态核验记录；
   `static_crosscheck_20261110-210053.json` 中途 `RuntimeError` 退出（target 180 报达到 210 mmHg）。
   **影响**：按"每日期至少一轮核验"统计覆盖率会虚高。

3. **"面板值当参考"的证据只有 6 个节拍。** `panel_vs_gauge_*` 六份的 `operator_panel_value` **全为 null**；
   唯一有面板实测的是 `panel_beep_offset_20261111.json` 的 6 个节拍。**结论只由 6 个点支撑，引用要写出这个 n。**

4. **`sealed_hold30_20261031-143306` 三份互相拉扯。** `.summary.md` 与 `.analysis.json` 判本轮 `valid=false`，
   而原始 metadata 记 `outcome=sealed_hold_completed`；`.csv` 是整轮串口流水（est 0→19.6→0.9），
   而 summary 只讨论其中 82 点保压段（19.6→17.4）。**直接对 CSV 求斜率会得到不同数。**

5. **"86% 毛刺落在开阀后第一个采样点"的分母是 184 份导出版本，不是故障率。** `valve_glitch_despike_20261113.md`
   同时说"28 份被拒里只有 2 份是毛刺"。省掉前半句会得出相反结论。

6. **"总导出数"有三个互不相等的口径**：`capture_catalog_20261031.*` 说 102、`export_inventory_audit_20261107.md` 说 67、
   `data_quality_assessment_20261110.md` 说 70。三者扫描目录/时间窗不同，但标题都像"全部导出清点"。

7. **两种"零点问题"被同名。** `zero_drift_20261112.md` 是封阀态随时间的缓漂（上午负、下午正，量级 ~1–5 mmHg）；
   `valve2_zero_*.md` 是开阀 vs 封阀的电气偏移（开阀高 ≈+2.6…+3.9 mmHg）。两者不可相加，也不可互相解释。

8. **`standard_bp_envelope_stability_20261105.diagnostics.json` 的 source 是乱码路径**
   （`C:\Users\31800\Desktop\琛€鍘嬩华\…`，GBK/UTF-8 误码），按此路径无法定位原始文件。

9. **`standard_display_protocol_20261109.md` 文件名标 11-09 而 mtime 是 11-08**；`standard_bp_peakwindow_comparison_20261105.png`
   在同名 md 内没有 markdown 图片引用，只有 validation.json 的 `plot_visually_checked: true`，正文无法确认图画的是什么。

10. **`pb8_standard_trial_20261031.simulation.csv` 首列自述"ideal curve is illustrative; not a pneumatic model"**，
    不能当气动仿真结果引用。本索引覆盖的 12 张 png 均为二进制，只按引用它的正文归类，**未做视觉核对**。

### D 未解释的异常（截至本索引建立仍无收口文件）

1. `pb8_standard_trial_20261031.json` 的 `repeated_boot_count = 8`、`reset_cause = unknown`。
2. `pulse_loss_after_soak_20261107.md` 记的 112327 轮"运行中 MCU 重启（226→112 用 0.5 s，无 `[Safety]` 打印）"。
3. `restart_low30_failure_20261031-145438.json` 记 `root_cause=undetermined`、无 ACK、无有效导出，
   但同日 15:06 又继续充气复测——与该文件自带的 `next_gate`（先恢复通信再动执行器）自相矛盾。
4. `standard120_80_20261101-120429.md` 固件输出 56 BPM vs 真值 84 BPM（归因：FFT 只取前 256 点），
   同日同容积的 `-152030.md` 输出 75 BPM，差 19 BPM 未解释——**属未结的固件缺陷线索**。
5. `recovered_exports_20261107.json` 的 9 份恢复导出与 `standard_bp_adaptive_20261101.json` 的 7 个 run
   存在同 run_id 重叠，两处各自计数，去重规则不明。
6. **导出帧发一半停住**（`crosstday_d02_20261117.md` §6）：`-20261117-122209` 轮的 `capture export`
   在 147 行（2.6 s）后停止，此后 `[Pressure]` 流继续 147.3 s，帧始终无 `"type":"end"`。
   到达速率与成功轮相同（~56 行/s），不是「慢」而是「断」。全库 523 份元数据里只此一例
   （另一份 `export_error` 是主机侧 `TypeError`，性质不同）。属固件串口发送侧，本批次不据此改脚本。
7. **封阀零点两天差 +1.5 mmHg 且漏率翻倍**（`crosstday_d02_20261117.md` §2/§4）：D1 十四轮 pre 全负
   （−0.869…−0.219），D2 二十八轮 pre 全正（−0.267…+2.367，均值 +1.013）；同压力下 D2 稳定段
   漏率（−11.26 / 重测 −9.90）约为 D1（−5.76）与 11-07（−5.50）的 2 倍，阀 flow 同步从 0.247 升到 0.268。
   协议 §2.3 无泄漏判据，不阻塞，但两者是否同源未查。
8. **峰窗斜率在 D3 整体变陡**（`crosstday_d03_20261118.md` §6）：D1 均值 −1.860（n=14）、D2 −1.894（n=28）、D3 **−2.390**（n=28，范围 −2.63…−2.19）。D3 的块A 与块B 均值都是 −2.39，不是某一段的偏差；D3 的最大值 −2.19 已比 D2 的均值更陡，整个分布平移约 0.5 mmHg/s。候选解释（传感器线重插、阀 flow 变快、微小新漏、室温下降）都无法验证，因为同一天放弃了温度记录且批次期间不得调参。
9. **`initial_rx_errors` 在夜间累积到 533**（`crosstday_d03_20261118.md` §7）：D1 首轮 86、D2 全天 0、D3 开机前已是 533 且 28 轮的 `initial`/`final` 全部相等（全天零新增）。即错误是在无人操作的夜间累积的，白天不增。需要一次通宵观测才能定位。
10. **`profile peak` 的 +0.9 mmHg 门控只在特定组合下咬人**（`crosstday_d03_20261118.md` §1.3）：零点越过 +0.9 且 `profile_already_peak` 为假时，重设 profile 会连试 4 次各等 25 s 后终止整天。11-16 与 11-18 各撞一次（11-18 那次是零点 +1.4…+1.8，起因是线缆松动）。它不是 bug，但「平时不出现、出现就整天作废」。
11. **COM12 会整端口假死，改一次波特率就醒**（`crosstday_d04_20261119.md` §1.2）：11-19 开工时 `[BP_VERSION]`/`[CUFF_EXT]`/`[SIM_STD120_80]` 连 5 轮全部 15 s 空回，设备在（`Get-PnpDevice` 两条 `Status=OK`）、控制线 `cts=True dsr=True`、DTR/RTS 四种组合与裸 `\r`、`\x05` 全部 0 字节；跑一遍波特率扫描（`tmp/serial_baud_20261119.py`）到 9600 时立刻回 `\x062780201 Ver 2.01S\r\n`，之后再查第 1 轮就全 ACK。属 Tester 侧接收状态假死，与 amend1 处理的「单条命令丢应答」是同一族但层次不同——整端口假死时重试单条命令没用，得打断链路。
12. **块B 零点比块A 高 0.31 mmHg 且块B 内部单调上移**（`crosstday_d04_20261119.md` §4）：D4 块A pre 均值 −0.046、块B **+0.265**；块B 逐档 +0.27/−0.89 → −0.29/−0.41 → +0.45/+0.53 → +0.55 → +0.59 → +0.53 → +0.62，P2 到 P3 之间跳约 +0.9 后稳定。D1/D2/D3 记的都是「重缠后零点短时下移」，只有 D4 是上移并保持。同日还首次出现 2 轮 `post − pre` 负值（`111744` −0.427、`113727` −0.310），D1–D3 共 70 轮全正。
13. **桥接流的时间戳乱序会让整轮报废**（`crosstday_d04_20261119.md` §1.3）：`tmp/bp_development_trial_20261031.py:73` 的守卫 `if not 0 <= age <= 1000 or stamp <= self.last_stamp: raise RuntimeError('stale/nonmonotonic pressure timestamp')` 用**严格比较**；D4 的 `-104426` 轮 795 个样本里恰好有一对倒退 950 ms（`1795056299388 -> 1795056298438`），整轮报废。同源的还有 `TimeoutError('ACK profile')`。若该现象在块B 首档连续发生会吃掉整天，是否容忍小幅乱序需 amend，本批次不动。
14. **超压事件集中在 11-16 与 11-19，且与峰值高低无关**（`crosstday_d04_20261119.md` §1.4）：全库 583 份 metadata 里 ndjson 文本命中 `Over-pressure` 的只有 **6 轮**——11-12 一次、11-16 三次（D1）、11-19 两次（D4）。D4 是全批峰值最低的一天（28 轮最高 278.6，**无一轮 ≥279**）却仍触发两次；D1 峰值最高的两轮（280.0、279.8）反而成功。机理是超压判定（`bp_control.h:29` = 280）在同一 tick 里排在「到达目标」判定之前（`main.c:794` vs `:805`），而串口 `[Pressure]` 打印间隔 50 ms 比采样 25 ms 宽一倍，越线的那一点看不到。
15. **超压的真因是 25 ms 控制时钟上的单点尖峰，不是峰值过高、也不是充气过快**（`crosstday_d05_20261120.md` §2）：D5 三次超压都发生在 `target reached` 之后 **17–21 ms**（一个控制周期），其中 `-203504` 连 `target reached` 都没有、从 ≤275 直跳 ≥280。按串口 trace 反推，触发所需的相邻 25 ms 跳变速率（143–195 mmHg/s）除 `-192841` 外**全部高于该轮的宏观充气斜率**（77.6–104.8 mmHg/s），说明是泵脉动打在某一个采样格点上。充气斜率与超压只是相关：≥95 mmHg/s 的 49 轮超压 4 次（8.2%），<95 的 478 轮 5 次（1.0%），两组分布重叠（`ok` 轮的 p99 也有 100.3），**没有可分阈值**。要证因果需要一条独立的高频压力通道。
16. **超压之后固件会拒绝设 profile**（`crosstday_d05_20261120.md` §2.6）：失败轮 trace 尾部出现 `[Profile] rejected: require inactive sealed fresh calibrated zero`（`-203428`/`-203504` 各 3 次），发生在 `target 50` 恢复之后，含义是固件拒绝在「刚放过气、零点还不新鲜」时设 profile。只影响恢复速度，不影响记账，但会让编排的重试多花约一轮时间。
17. **线圈偏移幅度可以在两天内从 +1.76 塌到 +0.37，且两态都读负**（`crosstday_d05_20261120.md` §1.2）：D4 coil offset +1.76（vent +1.76 / seal −0.01）、D5 **+0.37**（vent **−0.42** / seal −0.79）。vent 态读负是本批第一次出现——此前 vent 一直是正值。同一天传感器线没有碰过（`zero_arc` 四条读数一致）。这进一步支持 amend2 的判断（vent 态水平不能当门控），但也说明「线圈偏移」这个量本身不稳定，不能当常数校准。
18. **agent 会话重启会连后台采集的子进程一起杀掉**（`crosstday_d05_20261120.md` §6）：D5 第一遍跑在块A 第 8 轮被 kill，该轮无 metadata、无 export，OmniProbe 也一起消失。改用 `subprocess.Popen(..., creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP, stdin=DEVNULL)` （`tmp/start_d5_detached_20261120.py`）后第二遍跑正常。**后续每天都必须用分离进程启动**，否则会话一重启就白跑一次块A。
19. **开机锁存 `SENSOR_INIT`（`code=3`）会让整天第 1 轮就中止**（`crosstday_d06_20261121.md` §2）：固件在 `main.c:1947-1953` 探测 ADS1115 失败时记这个码，`bp_control.c:44-51` 的记录函数**只写不清**，只有 `BP_Control_Reset()`（`bp_control.c:68-79`）能清，而它的调用点只有 `start`（`main.c:699`）、`deflate test` 与 `loaded pulse`（后两者仅当已在 `EMERGENCY`）。采集脚本的容忍白名单只含 `name=SENSOR_READ`，所以 `SENSOR_INIT` 必挂。11-21 开机时 `errors=11 recoveries=11` 说明 ADS1115 失败过 11 次又自恢复，但故障记录停在第一次。清法 `start` → 0.6 s → `stop`，代价是真的进气约 +6.9 mmHg。
20. **单字节乱码 `U+FFFD` 会作废一整轮**（`crosstday_d06_20261121.md` §3）：守卫 `bp_sealed_hold30_20261031.py:15-20` 把 `\ufffd` 与 `sample failed`/`read failed`/`retry init`/`[Boot]` 一视同仁，任何一行含 U+FFFD 就抛 `hold sensor/transport discontinuity`。全库 623 轮里只 2 例（11-13 `standard100_065_target275_peakwindow_20261113-165250` 与 11-21 `-111959`），形态完全一致：一个 U+FFFD 落在 `[Pressure]` 行首、`closeout_confirmed=True`、无 export。两例的 MCU `rx_errors` 都是 0，说明坏字节出现在 MCU UART 之后（FTDI 帧错误 / 桥接读取边界 / UTF-8 跨 chunk 切断多字节字符，三选一未区分）。
21. **`profile normal` 复位在 23/28 轮被拒，且与收尾零点完全可分**（`crosstday_d06_20261121.md` §4）：成功复位的 6 轮收尾零点 +0.069…+0.721，失败 23 轮 +0.923…+2.529，两段不重叠，分界就是这个 `-1..+1` 固件门。复位失败使 profile 停在 `peak`，下一轮 `profile_already_peak` 分支跳过 vent/seal 换气，块B 前 8 轮 pre 均值 +1.147、后 6 轮 +0.250 与之一致；但 `-122940`（pre −0.132，前轮 post +1.666）与 `-123631`（pre −0.222，前轮 post +1.378）是反例，故只能算同向相关。**后果**：次日开工时 profile 很可能仍是 `peak`，「每轮现场设 peak」这个隐含前提不再成立，报告须逐日注明。
22. **`raw=0` 的零电压样本会被固件当成 `VALID` 正常值**（`crosstday_d07_20261122.md` §2）：`ads1115.c:154-158` 把转换寄存器读回的 `0x0000` 直接赋给 `*raw_value` 并返回 `HAL_OK`，`ADS1115_ReadSample`（`:203-207`）只看 status；0 V 代入 `82.326×0−19.887` 得 −19.887 mmHg，被 `:215-218` 钳成 0；`main.c:461` 打的 `VALID` 语义是**校准记录有效**，不是这一帧有效。受影响的守卫 `direct_serial_bridge_20261107.py:161-162`（`bp_development_trial_20261031.py:84` 同）在 `active` 期间见 `raw<1000` 即抛 `invalid calibration or extreme raw signal`。全库 1180 份 ndjson 只 1 例（11-22 `daily_leak_20261122` 12:19:27.666），前后帧相隔 43 ms 都正常，且这一帧**没有** `sample failed` 行，说明它走 `HAL_OK` 分支、**未被任何故障计数器记到**。修法（把全零读回视为失败）需改固件 = 批次终止，留到批次结束后。
23. **每轮日志名不含块字母，块B 会覆盖块A**（`crosstday_d07_20261122.md` §3）：`run_crosstday_20261116.py:209` 的 `f'{tag}_p{preset}_a{attempt:03d}.out'` 让块A/块B 共用同一批文件名。D1（半天）0 处撞名；D2–D7 每天 14 个名字共用、12–14 个 slot 的日志内容已被换掉；D7 是 30 slot / 16 name / 14 collide / 13 wrong。**原始证据不受影响**——日志在 `tmp/`（`.gitignore:2`）不入库，raw 按 run_id 命名从不撞名，失败原因在 ndjson 文本行里完整保留。修法是给文件名加块字母，改冻结脚本只能批次后做。
24. **漏率与阀 flow 在同一天大幅同向下降**（`crosstday_d07_20261122.md` §1.2）：漏率稳定段 −11.13 → **−9.25**（−17 %，四个分窗同向变缓），阀 flow 0.32042 → **0.17630**（−45 %，3 ms 与 4 ms 两个脉宽同向下降）。这是本批次第一次出现「两个独立气路测量同日同向大动」，但两者物理上未必同因，D8 若继续同向才谈得上气路整体变化。

25. **超压的可分判据是「到压那一帧是否就是整轮最高读数」，不是到压值也不是加压速率**（`crosstday_d08_20261123.md` §2）：全库 710 份 metadata 里 617 轮有 `target reached` 行、其中 13 轮超压。把 `coast` 定义成「到压后 250 ms 内最高 `est` − 到压值」后分桶：`coast < 0` 的 190 轮出 7 次超压（3.7 %）、`coast = 0` 的 303 轮出 6 次（2.0 %），而 `coast > 0` 的 124 轮**一次都没有**。到压值本身（超压组 275.9…279.9）与 604 个正常轮（p50 276.4 / p95 278.8 / max 279.9）完全重叠，按到压值分桶还**非单调**（277–278 桶 4.7 % 高于 278–279 桶 1.4 %）；顶部加压速率超压组中位 96.8、正常组 90.3 mmHg/s，同样分不开。机理是 `main.c:794` 的 280 判定在同一 tick 里排在 `main.c:805` 的到压判定之前，所以「把压力推过 280 的那一帧恰好也是判定到压的那一帧」时必然走超压分支。另有 3 轮超压**连 `target reached` 行都没有**（`150803` 11-12、`203504` 11-20、`132833` 11-23）——一步跨过整个 275–280 窗口。

26. **重缠袖带这个动作本身会把零点顶出 `profile` 门，且能连丢四轮**（`crosstday_d08_20261123.md` §3）：块B 开局 `preset 1` 连续四次死于 `RuntimeError('profile peak could not be set: …sealed true zero above +0.9 mmHg; profile set needs -1..+1')`，四轮都**从未充气**（峰值 est 4.8–4.9）、`closeout_confirmed=False`、`fresh_samples` 只有 2481–2482。从 `-124039` 末 400 样本反算 raw 中位 1516 → 真零点 **+1.66 mmHg**，确实在门外；第五次 `-124244` 无干预自愈（`profile normal` ×3 + 若干 `vent` 之后 `profile peak` 被接受）。D6（长 vent 才过门）、D7（第一次就过）同型，但 D8 是第一次因为它连丢四轮。

27. **「profile 停在 peak」在这几天其实是继续采集的必要条件**（`crosstday_d08_20261123.md` §4）：D8 有 **17/28 轮**的 `pre_capture_zero_true_mmhg > +1.0`（超出固件 `-1..+1` 的 profile 门，但在采集脚本 ±5.0 的预检门内），其中 **16 轮**靠 `profile_already_peak=True` 直接采集成功，只有 `-124244` 需要重试。七天对照 `pre>1.0 轮数 / 其中 already_peak`：D1 0/0、D2 15/15、D3 0/0、D4 0/0、D5 13/13、D6 18/18、D7 1/1、D8 17/16。链式统计 `(上一轮复位失败, 本轮 already_peak)`：`(True,True) 14 / (True,False) 4 / (False,True) 4 / (False,False) 5`，说明复位失败是强相关而不是充分条件。因此 D6 §21 那条「复位失败是缺陷」应改读为「**复位失败把 profile 留在 peak，反而让零点偏高的轮次仍能开跑**」。

28. **MCU 的 `reset_csr=0x04000000` 是纯 PIN 复位，NRST 被拉低而 VDD 未掉**（`crosstday_d08_20261123.md` §5）：采集前第一次漏率采集在 `[Inflate] START` 后 15.387 s 被打断（当时压力仅 0.8 mmHg），串口抓到完整开机横幅并以 `[Boot] reset_csr=0x04000000 PIN` 结束。固件 `main.c:1877-1900` 的 `Boot_CaptureResetCause()` 在 `HAL_Init()` 之前读 `RCC->CSR`，按位可区分 POR/PDR、PIN、IWDG、WWDG、SOFT、LPWR。扫描 1991 份 ndjson 全库只有 **4 例、全部 `0x04000000`**（11-09 `dataset_step240b`、11-10 `sag_test`、11-21 `d6_state3`、11-23 `daily_leak`），`data/raw` 下 0 例——正式采集从未记录到复位。排除电源塌陷（会同时置 PORRSTF）、看门狗（4000 ms 且 `debug-freeze=ON`）、软复位之后，头号嫌疑是 pyserial 打开 COM6 时默认驱动 DTR/RTS，而 `direct_serial_bridge_20261107.py:95` 的 `serial.Serial(port, BAUD, timeout=0.05)` 没有显式置 `dtr=False, rts=False`。

29. **导出帧的 `p` 就是从峰值稍后开始的实时降压序列，`p = slope·v + intercept` 精确成立**（`crosstday_d08_20261123.md` §11）：`begin.slope` / `begin.intercept` 是 IEEE-754 f32（`82.325996` / `−19.886999`，与 `[Cal]` 一致），28 份 export 全部满足 `max|p − (slope·v + intercept)| = 0.000021`；`t` 严格 25 ms 递增、`t0` 是上电后毫秒 tick；`p[0]` 比元数据 `active_pressure.est.max` 低 9.33–13.88（中位 10.40），把串口 `est` 与 export `p` 按时间对齐后 37 个抽样点误差**中位 0.03 / 最大 0.05 mmHg**——所以 `p` 是降压段而非加压段，**判断加压速率仍然只能用串口 50 ms 流**。`e`（≤0.0315）与 `s`（≤0.0177）的确切定义仍未查。

30. **COM12 整端口假死第二次复现，仍只有改波特率能唤醒**（`crosstday_d08_20261123.md` §6）：`panel_check_20261119.py 3` 五轮全部 15 s 空回，`wake_tester_20261120.py` 的八个组合（close-open 9600、`dtr/rts` 1/1、0/0、1/0、0/1、baud 4800、57600、retry 9600）**全 0 字节**；随后 `serial_baud_20261119.py` 扫到 `baud 9600 -> 20 bytes b'\x062780201 Ver 2.01S\r\n'`（19200 回 459 字节乱码、38400/115200 全 0），扫完立刻重跑 `panel_check` 第 1 轮全 ACK。D4 与 D8 两次实战，`wake_tester` 从未奏效。

31. **8,416 个样本的差额：`fresh_samples` 与 `[Capture] n` 是两个口径**（`crosstday_d08_20261123.md` §9）：D8 28 轮的 `[Capture]` 样本合计 **102,366**，与 28 份 export 的 `begin.n` 合计完全一致；而元数据 `fresh_samples` 合计 **110,782**，差 8,416。原因是 `fresh_samples` 覆盖整轮（含降压段），`[Capture]` 只记峰值之后写入环形缓冲的那一段（82.8–99.2 s、mean 91.4）。**引用样本数时必须注明用哪个口径。**

32. **ADS1115 的 `0x00000200` 是 `HAL_I2C_WRONG_START`，不是 AF/NACK**（`crosstday_d09_20261124.md` §2）：此前 D4 起的多次记录把 `err=0x00000200` 读成"AF 应答失败"，实际按 `stm32f1xx_hal_i2c.c:3577` 是 `if (READ_BIT(hi2c->Instance->CR1, I2C_CR1_START) == I2C_CR1_START) { hi2c->ErrorCode = HAL_I2C_WRONG_START; } return HAL_TIMEOUT;`——**START 条件请求了但 SB 没置起**，从机根本没参与。D9 的 `errors` 轨迹 4→5→10→11→18→20、`raw p2p` 2–8→3359、爆发段 11:24:47–11:25:01 连续 7 次失败 + retry init，是这个码第一次被完整取证。`0x00000020` 是 `HAL_I2C_ERROR_TIMEOUT`。两者都指向总线被拉低/上拉不足/接触电阻，而不是器件 NACK——**此前所有把 `0x200` 当 AF 的判读都要按此更正**。

33. **`ADS1115_I2C_Recover()` 自己修不了被拉低的总线**（同上 §2.4）：`ads1115.c:43-55` 只做 `HAL_I2C_DeInit` → `__HAL_RCC_I2C1_FORCE_RESET()` → `RELEASE_RESET` → `HAL_I2C_Init`，注释明写「No GPIO clock pulsing; this cannot repair a slave physically holding the bus low」。而 `errors`/`recoveries` 是 `ads1115.c:15` 的 `static ADS1115_Diagnostics_t s_diag = {0};`、`:36`/`:47` 两处只增不减，锁存 fault 也只有 `bp_control.c:68-79` 的 `BP_Control_Reset()` 能清。**所以「计数器归零 + fault 清空」这三件同时发生，等价于「MCU 重启过」**；D9 11:32:12 就是靠这个指纹认定的，尽管没有抓到 `[Boot] reset_csr` 横幅。

34. **`profile normal` 复位门的实际阈值约 0.75，不是固件写的 ±1.0**（同上 §4.3）：D8 复位成功组收尾零点 +0.282…+0.713（均值 +0.481，n=9）、失败组 +1.060…+2.469；D9 的失败下限 **+0.809** 落进这个空档，把边界夹到 **(0.713, 0.809]**。原因是 `main.c:286-294` 判 `s_last_pressure_sample.pressure_mmhg`（最后一帧），而卡片记的 `closeout_true_zero_mmhg` 是收尾窗口 100 样本的**中位**，两者差 0.2–0.3。这条仍未直接读到最后一帧，属推断。

35. **「profile 停在 peak」在两天的意义完全相反**（同上 §4 与 D8 §4）：D8 有 **17/28** 轮 pre 零点在固件 `-1..+1` 门外、其中 16 轮靠 `already_peak` 才采成（`pre>1.0 轮数/其中 already_peak`：D2 15/15、D5 13/13、D6 18/18、D8 17/16）；D9 则是 **28 轮 pre 全在门内**（最大 +0.960），却因为复位 28/28 全败而全程停在 peak。→ 协议层面应写清「`already_peak` 是允许的采集路径」，而不是留成脚本分支的副作用。

36. **`coil offset` 不是当天常数**（同上 §1.3）：D9 同一小时内 11:05 四态给 +6.09、11:08/11:14 的稳定对给 **+9.55**（vent +9.17 保持 120 s 不衰减、seal −0.38 保持 185 s 不动）。两对读数各自稳定却差 1.5 倍，**比 amend2（11-16 +6.0…+7.1）更干净地证明 vent 读数既不是零点、也不与 seal 误差成比例**。为什么同小时会变，没有分离实验。

37. **COM12 假死的判据要放宽到「波特率扫描连跑 2–3 次」**（同上 §5）：D9 是第三次实战，`wake_tester_20261120.py` 的八个组合（close-open 9600、`dtr/rts` 1/1、0/0、1/0、0/1、baud 4800、57600、retry 9600）**全 0 字节**；`serial_baud_20261119.py` **第一次四档也全 0**（本批首次），第二次只回乱码（19200→409 B、38400→171 B），**第三次**才在 9600 拿到 `b'\x062780201 Ver 2.01S\r\n'`。另外 `COM12` 那天不在 `Win32_SerialPort` 列表，但注册表 `HKLM:\HARDWARE\DEVICEMAP\SERIALCOMM` 有 `\Device\VCP0 = COM12`、`Get-PnpDevice` 为 Status=OK/Present=True/CM_PROB_NONE——**WMI 列表为空不代表端口不在**。

38. **`fresh_samples` 与 `[Capture] n` 的差额不是 D8 特有的**（同上 §9）：D8 差 8,416、D9 差 **7,706**（约为 `[Capture]` 的 7 %），同量级。D9 另外核对了 `[Capture]` 的 `duration=` 与 `(n−1)×25 ms` **44 条全部一致到 0 ms**（`n×25` 会多 25 ms），所以「每轮时长」应写 `(n−1)×25`。**引用样本数必须注明口径。**

39. **Windows 自动重启会留下"读通写不通"的 USB-CDC 半死状态**（D10 §2）：2026-11-25 12:08:35 重启后，`[Pressure]` 流照常、`serial.write` 一律 `os error 121`（信号灯超时）。软件层六种手段全无效，只有**物理拔插**能恢复；本会话非管理员，`Disable-PnpDevice` 报 `常规故障`、`pnputil /restart-device` 报 `Access is denied.`。另外**不设 `write_timeout` 的 `serial.Serial` 会让写无限阻塞**并把端口占住（`tmp/d10_modem_reset_20261125.py` 就这么挂住过），试写必须带 `write_timeout=3.0`。

40. **降压阀会偶发丢失数秒节流，而固件不报错**（D10 §3.3）：`-135554` 在 200–250 mmHg 段 3.2 s 内掉了 48.5 mmHg（−15 mmHg/s），随后自恢复 −1.8 mmHg/s；该轮降压段只有两条非压力行，**没有任何故障码**。全库 266 份批次 export 里只有这 1 轮越过 4.0 mmHg/s 的门槛，另有 2 例同型在 2026-11-07（−32.87、−16.81）。→ **冻结门是唯一能发现它的机制**；要找根因必须在 `main.c` 的 PWM 节流环路里加打印（占空比、每步目标、实际压差），批次期间不能改。

41. **漏率的"稳定段斜率"可能被锯齿决定**（D10 §1.2）：同一份 hold 轨迹里 40–60 s 段有 36 次 >1.5 mmHg 的向上台阶（最大 1.90、间隔 1.27 s），而前三天分别是 28 / 0 / 13 次。D10 算出 **−17.63** 首次离开 −11.1…−11.6 平台，但若把台阶数当作变量，−17.63 与平台值**可能是同一条阶梯的两种取法**。→ 引用漏率时必须同时报 `sawtooth` 计数，不能只报一个斜率。

42. **失败归因正在依赖人工记录**（D10 §10.2）：27 个失败 slot 里只有 **16 个**的原因还能从现存 `.out` 读出来（12 超压 + 4 `profile peak`），另外 11 个的日志已被块B 同名文件覆盖，只剩 `(no RESULT line)`。这 11 个是靠当天报告补回来的（D2 1、D4 2、D5 1、D6 1、D7 1、D8 3、D9 1、D10 1）。→ 日志撞名（`tmp/run_crosstday_20261116.py:209` 不含块字母）**不只是可读性问题**，它让复核失败成因必须依赖人工台账。

43. **加性 SBP 偏移不可迁移，是三份语料的共同结论而不是两次偶然**（判定 §3）：本批用前五天定
`d = −1.3254`、后五天验，`improvement = −1.3254`（要求 ≥ +0.5）、`late_sd 12.47`（要求 ≤ 8.0）。
符号翻转与 `dataset_limitations.md` 里"开发集 `+2.00`、留出层 `−3.07`"一致。→ 任何"把 `SBP_OFFSET_MMHG`
调成某个常数就能过线"的说法都被这次真留出检验否掉；常量保持 0.0（已写入 §25）。

44. **协议文本与冻结脚本的一处不一致会翻转 SBP 的日项结论 —— 2026-11-25 已修**（判定 §5.4、amend3）：
`tmp/crosstday_analyse_20261116.py` 没有实现协议 §4 规则 10 的"T1/T3 只用完整日"，把 D1 的 `half_day`
也算进去 → SBP 日项 `p = 0.0572`；只喂 D2–D10（251 轮）则 `p = 0.0313`，一侧"不复现"、一侧"复现"。
**修法不是改冻结脚本**（哈希是已发表读数的唯一锚点，改了 0.0572 就不可复现），而是把规则 10 落进入库的
`tools/crosstday_judge.py`：完整日谓词只读 manifest（该日两块对每个设计档都至少留 1 轮；某档只少 1 轮仍算完整）、
前后半按**计划天号**切（不按存活列表索引），`--rule10 off` 必须逐字段复现冻结 JSON 的 `t0/t1/t2/t4` 与三个 `model_*`。
→ 本批 SBP 日项按规则 10 记为**复现**，冻结读数并列保留；下一批预注册必须一开始就带上这条规则。

45. **日聚类 SE 才是半宽的主导项，不是 n**（判定 §6.3）：两个估算器在 P1 上的 sd 只差 9%
（6.90 vs 6.31），但 `half_width` 是 6.40 vs 3.33。原因是 v2 的 18 轮 |SBP|>20 长尾**成团落在 D1–D4
（14/18）**，日均值整天往外跳，把 `se_clustered` 放大；`covered_bp` 把这些轮拒判掉，长尾不再成团。
→ 比较两个估算器的"可声明格数"时，**必须同时看 n、sd 与日聚类 SE**，否则会把"多拒判"读成"更准"。

46. **本批的 FAIL 是 7% 长尾驱动的，不是分布整体平移**（判定 §7.3，描述性不改判定）：剔掉 18 轮
|SBP|>20 后，T1 从 FAIL 翻 PASS（offset +0.3513、late sd 7.7564）、T3 三项全部 p<0.05，
剩余 241 轮 mean **−0.36** / sd **8.24**（比 v5 在 71 轮前瞻上的 248 轮 +1.08/9.62 还略好）。
18 轮里 **P4 占 6、块B 占 11**；极端值是 `D2/P5/B +156.51`、`D1/P6/A +119.99`、`D2/P6/B +119.50`、
`D7/P4/B −100.75`。→ 正确的读法是"少数灾难性 SBP 缺失压倒了整批"，不能读成"这个月台架变差了"。

47. **判定器放在 `tmp/` 是结构性弱点**（amend3 §7）：`tmp/` 被 `.gitignore` 忽略（`git ls-files tmp` = 0），
冻结脚本的唯一身份锚点是协议附录的 sha256 + `tmp/verify_frozen_20261117.py`，一旦工作区丢失就无法复现
已发表读数。→ 从本批起，**凡是参与判定的代码都放 `tools/`**（`tools/crosstday_judge.py`、
`tools/crosstday_judge_selftest.py`），`tmp/` 只留一次性取证脚本。

48. **协议里的复现命令必须实测过才写进去**（amend3 §5）：v1 协议 §7 的两条命令一条 glob 匹配 0 个文件
（`standard*_peakwindow_crosstday-*`，真实名是 `standard*_target275_peakwindow_2026112*`）、
另一条跑 `--tag crosstday` 直接 `error: unrecognized arguments`（脚本只有 `--manifest`/`--json`）。
两条都是"写的时候没跑过"。→ 协议里每条命令发布前都要在真实工作区跑一次，并把输出粘回去。

49. **「失败轮无法归因」是错的判断，先查元数据**（2026-11-25）：D7–D10 四份日报都写过
    「27 个失败 slot 里 11 个已无法归因」，理由是 `.out` 被块B 同名文件覆盖。实测
    `tools/attribute_failed_slots.py` 能归因 **27/27**——采集脚本自己写的
    `<run_id>.metadata.json` 里有 `error`，失败轮只是缺 `batch_day`/`wrap_block`
    （跳过 `patch_metadata`），原因一直在。教训：说「证据丢了」之前先把所有落盘产物
    列一遍，尤其要想到「生产者自己写的那份」与「编排器打补丁的那份」是两个文件。
    一处坑：D2 那轮的原因在 `export_error` 而不是 `error`（导出阶段失败），
    只读 `error` 会误报成「没有 error 键」。
50. **日志名必须带块字母，否则同一天的两个块互相覆盖**（2026-11-25）：冻结编排器
    `tmp/run_crosstday_20261116.py:209` 写成 `f'{tag}_p{preset}_a{attempt:03d}.out'`，
    `tag` 只含批次/天号/启动时刻，于是块B 复用块A 的文件名。整批 293 个 slot 只要了
    **167 个名字**、126 个被要求两次、**116 个 slot（全是块A）的 `.out` 已非自己**。
    D1 因为是 `half_day` 而幸免，D2–D10 每天都是 14 个名字被共用（7 档 × 2 轮）。
    修法：`tools/crosstday_orchestrator.py`（amend4）加块字母，同样 293 个 slot
    产生 293 个不同名字、0 撞名；日志目录仍在 `tmp/`（gitignore），所以**覆盖是永久
    的**，无法从 git 历史回溯。
- **51 判据必须落在"命令量的绝对高度"，不能落在"增益的相对变化"。** 阀失节流五例的
    `gain = 每周期净压降 / commanded open ms` 会从 0.089 塌到 0.018–0.021、爆发期又涨到
    0.196–0.362；但**全库 637 份里 82 % 的正常轮 `max/median` 也能到 3 倍以上**，比值完全
    分不开。能分开的是 `duty_med`：`≥ 8` 的 10 轮含全部 5 例、`< 8` 的 627 轮 0 例。
    即便如此它也**只是必要条件**——`…213751`（duty_med 25）与 `…215530`（16）是紧接着最陡
    两例之后的"余震"轮，斜率只陡 60 % 没超门，说明"闭环在补偿多少"与"补偿量是否一次性
    泄放"是两件事。写判据时先想清楚它测的是哪一件。
- **52 "已发布"与"被门接受"是两个字段。** `tools/dataset_tiers.py:168-181` 的
    `in_published_corpus()` 对 `PROTOCOL_TIERS` 直接返回 True，**不看 `gate` 列**；所以
    62 轮已发布语料里有 4 轮被冻结门判 REJECTED（`USABLE 58 / REJECTED 4`），而且三份
    冻结记录给了三种处置（v2 retrospective 列入 reject 但仍算已发布、v2 评分报告标
    `gate_rejected` 且误差全 null、v1 报告里 `…202606` 竟 `status: "ok"` 给出 MAP 202.93
    vs 面板 150）。引用 62 轮统计时必须知道这 4 轮的压力剖面不合格；反过来也不能说
    "已发布语料全部通过门"。
- **53 「近似算一遍」和「真跑一遍」会给出不同的结论，先例是 T0 的 2/21 vs 1/21**（11-26）。
    重标定报告用"把每档的轴移加到冻结 T0 均值上、半宽保持不变"估了一次，得到 2 格可声明；
    真按新轴跑完 21 格后只有 **P1 MAP** 一格翻过去，P3 MAP 得 5.127（差 0.127）仍不可声明。
    原因很直接：**换轴同时改均值和半宽**（半宽来自日聚类 SE，而日均值本身变了），把半宽
    当常数就系统性高估可声明格数。凡"换尺子"的敏感性都必须真跑，不能只平移均值。
- **54 换尺子会暴露原来被偏差掩盖的错误，看起来像变坏，其实是变真**（11-26）。
    修掉旧轴在 200 mmHg 以上 2–3 mmHg 的系统偏低之后：跨天池 AAMI 从 6/7 掉到 5/7（P4 的
    SBP −2.91 → −5.68）、`frozen_v2` 静默 >20 从 20 轮涨到 26 轮、全库池也从 6/7 掉到 5/7。
    这三处都是"原来的成绩里有一部分是尺子错了碰巧抵消"。**任何在旧轴上算出来的覆盖率，
    引用时必须带轴的口径**，否则就是在拿一个错的零点当基准。

- **55 换口径时，最先过期的是"交付文档"，而它恰好最常被外人引用。** 压力轴在 11-26 换了
    一对数字后，报告与 README 都跟着改了，但 `docs/make_doc.py` 生成的 docx 里仍写着
    `82.326 / -19.887` 和手算示例 116.4 mmHg、`data/reports/dataset_limitations.md` 仍写着
    「标定未改动」和「最坏 ±5.7 超 ISO ±3」、`data/dataset_dictionary.md` 的"反算未钳位
    压力"一节还把常量写死在正文里。清这批话的顺序应该是：**先扫"声明式句子"（可声明、
    最坏、未改动、符合），再扫数字**——因为数字会出现在很多正当的历史语境里，而声明式
    句子一旦过期就是错的。另外，扫 `5.7` 必须用 `(?<![\d.])5\.7(?![\d])`：仓库里
    `5.71`、`5.70`、`5.75`、`5.7 mV` 大量存在且都是正确数字。

- **56 「能复现」不等于「能发出去」。** 到 2026-11-26，这个仓库能复现任何一条结论
    （四份冻结记录 + 四道校验 + 反向测试），但仍然发不出去：没有 `LICENSE`、没有
    `CITATION.cff`、没有只含已发布子集的下载物（62 轮散在 2.4 GB 的 645 份导出里，
    `data/processed/` 一直是空的）、没有 data-availability 说明。这四样一样都不属于
    "研究内容"，缺任何一样第三方都用不了。**"验证"做扎实之后要立刻回头看"交付"，
    两者是两条独立的线。**
- **58 `git add -A` 之前没被检查的目录，等于已经泄漏过一次。** `cloud/` 里有明码 MQTT
    口令，从 2026-11-06 起就躺在工作区里、既没跟踪也没被 gitignore——这种"靠人记得"的
    状态只要有一次 `git add -A` 就变成永久：git 历史一旦推上去就撤不回。
    处置不是"记得别 add"，而是**两层**：`.gitignore` 挡住，加一个能跑的检查
    （`tools/scan_secrets.py`，11 条模式全部要求凭据上下文，`SKIP_FILES` 只有一条豁免且
    每次都打印）。**裸数字不能当判据**——`git grep 123456` 命中 589 个文件，全是
    Cortex-M 头文件里的魔数和 NDJSON 字节。
- **59 把大文件移出 HEAD 不等于缩小仓库。** 移除 1031 个文件、2.33 GB 提交树字节之后
    `git count-objects -vH` 的 `size-pack` 一个字节没变（仍 457.72 MiB）：这些字节仍在
    144 个提交里，`git clone` 照样能取到。要真清除必须重写全部历史，而本机没有
    `git-filter-repo`；更麻烦的是重写会让报告里所有 commit hash 锚点失效
    （`published_corpus_20261126.json` 的 `built_from_commit` 就是一类）。所以这是个
    取舍问题而不是技术问题，**必须在"公开"这个动作之前定，不能之后**。
- **60 关掉一个数据源之前，先找出唯一读它的那一行。** 逐样本遥测 2.2 GB 被 gitignore
    之前，取证发现 `tools/reference_bp.py:83-108` 的 `load()` 只读导出帧的 `p`/`e`/`s`，
    唯一例外是 `tools/preset_low_bp.py:69-86` 从遥测里正则抓固件自己打的 `[BP] SBP=…`
    那一行——而这一行既不在导出帧里也不在元数据里。于是先写
    `tools/extract_device_verdicts.py` 把它抽成 94 KB 的表（653 轮，`--verify` 在带遥测的
    树上逐轮重推、在克隆里退回按 metadata 校验），再移出遥测。**"没有估计器读它"这个判断
    要靠读代码确认，不能靠印象。**

- **57 发布包的校验必须包含"重算计数"，只校验摘要不够。** `checksums.sha256` 只能证明
    "这些文件没被动过"，证明不了"这些文件是那 62 轮"。所以
    `tools/verify_release_package.py` 第四道检查从树里重算轮数、层分布、门分布、
    遥测开关，再与 `release.json` 比对；反向测试专门构造了「把 published_rounds 改成
    61」「把层分布改一个数」「把 with_telemetry 谎报为 true」三个用例。另外
    `release.json` 必须写在 `checksums.sha256` **之前**并被它覆盖，否则它自己就是一个
    未受检的声明——这正是第一次跑正向验证时被抓到的缺陷（`UNLISTED release.json`）。

- **61 检出字节不是"内容"的一部分，但它会被当成内容来校验。**（11-26）发布快照克隆到
    另一台机器后 `tools/verify_freeze.py` 直接报 6 处 FAIL：`frozen 0857b93a172b027c !=
    current ce0916ae9ec40ab0` 等。原因是旧 `.gitattributes` 只给数据类扩展名标 `-text`，
    `*.py` / `*.md` 仍由 `core.autocrlf` 决定——本地 `.git/config` 里恰好是 `false`，
    克隆机继承的是系统级 `true`，于是 `tools/*.py` 被写成 CRLF，而指纹算的是**工作树字节**。
    修法是一条 `* -text`（`e70bc84`）：索引里是什么字节，检出就是什么字节。教训有两层：
    ①任何"对文件内容算哈希"的校验都必须同时钉住行尾，否则校验的是宿主机的设置；
    ②回归测试必须在**干净克隆 + 默认配置**下跑，本地工作树永远是最后一处会暴露问题的地方。
- **62 只推一次快照，会让仓库正文里的提交哈希变成不可解析的字符串。**（11-26）为了不让
    2.3 GB 历史进入远端，按"另建干净仓库、只推当前状态"处理，远端只有一个 orphan 提交。
    代价立刻出现：七个被正文引用的本地哈希（`d022013`、`c60ef1f`、`2430964`、`0bf20b5`、
    `5066fc5`、`7b0a04d`、`d7db003`）在 GitHub 上查不到。**最诚实的处置是登记而不是改写**：
    把它们替换成快照哈希会让 `published_corpus_20261126.json` 的 `built_from_commit` 变成假话
    （发布包实际是从 `d022013` 的树打出来的）。登记前先确认"有没有代码读这些哈希"——
    实测 `tools/v3_acceptance.py:57`、`tools/v5_acceptance.py:58,69` 用的是**时间戳**，
    `tools/verify_release_package.py` 不比对 `built_from_commit`，所以登记后所有校验命令仍全绿。
- **63 这条网络路径上 `git push` 走不通，不代表东西推不上去。**（11-26）快照提交做好后
    `git push` 连试三次全在**服务器接收阶段**被断：`curl 55 Recv failure: Connection was reset`、
    `curl 28 Connection timed out after 300053 milliseconds`、第三次已经
    `Writing objects: 100% (2614/2614), 75.24 MiB` 传完才 `fatal: the remote end hung up
    unexpectedly`。关键判据是**先证明不是本地缺对象**：远端 `a6750cc` 的每个 blob 都能
    `git cat-file -e` 通过、两侧对象数都是 2614、实测只有 11 个对象不同（7 个 blob + 3 层树
    + 1 个提交）。同一链路上 `git fetch` 与 `git push --dry-run` 也各自卡满 300 s 超时——
    **当 push、fetch、dry-run 三条同时失败，问题在链路而不在凭证或对象库**，此时重试只是耗
    时间。改走 GitHub git-data API 四步即通：`POST /git/blobs` → `POST /git/trees`（自底向上）
    → `POST /git/commits` → `PATCH /git/refs/heads/master`（`force: true`）。两个坑值得记：
    ①**API 造的提交对象与本地 `git commit` 字节不同**（author 与 committer 共用同一个 epoch，
    消息保留结尾换行），不想让远端多出一个本地没有的提交，就得用
    `git hash-object -t commit -w --stdin` 把本地提交重写成同样的字节；
    ②`git ls-tree` 默认 `core.quotepath=true` 会把中文文件名转义成 `\347\244\272…`，与 API 的
    UTF-8 路径对不上，**比对时必须 `-c core.quotepath=false`**，否则会误报"3 个文件只在本地"。
    验收方式不是"push 成功"，而是**双端逐路径比对**（2537 个 blob，only local 0 / only remote 0
    / content differs 0）+ **匿名 `git clone --depth 1`**——克隆下来的副本里
    `verify_checksums.py` 1707 条全绿、`verify_freeze.py` 四条冻结记录完好，
    这才算"第三方拿得到、且拿到的就是校验过的那份"。
- **64 有包不等于能下载，发布包要有一个不属于仓库树的出口。**（11-27）`dist/bp_waveforms_20261126`
    从 11-26 起就能生成、能校验，但它被 `.gitignore` 挡住，外部读者想知道"那 62 轮长什么样"
    仍需克隆 362.4 MiB 再自己跑一遍打包脚本——**这不是可下载物**。补的办法是 GitHub Release：
    tag `v2026-11-26` 指向远端 `master` 快照，附件 `bp_waveforms_20261126.zip`
    5,911,202 B（5.64 MiB，zip SHA-256 `45e6912f…2cd43`）。三点值得记：
    ①**zip 必须确定性打包**（固定 `date_time`、固定成员顺序、`compresslevel=9`），否则每次
    重打哈希都变，"把 SHA-256 写进文档"这条验收就失效；**还有 `ZipInfo.create_system` 这类
    隐藏量**——默认 `0`，改成 `3`（Unix，常为带权限位而设）会让 148 个成员头各差一字节，
    同一目录算出另一个合法 SHA-256（实测 `4790258c…ce0b33`）。重打包哈希不符时，
    先对齐参数再怀疑包坏；
    ②**压缩率会骗人**：`.export.ndjson` 是文本帧，30.1 MB 压到 5.64 MiB（18.7%），
    别把附件大小当成数据集体积，`release.json` 的 30,126,567 B 才是解压后的量；
    ③**附件发小包不发整库**——整库 362.4 MiB 里公开发布语料只占 30.1 MB，把整库塞进 Release
    会把刚建立的"最小下载路径"重新变胖。验收标准同样是"匿名下载后校验"而不是"上传成功"：
    不带头直连 `.../releases/download/v2026-11-26/bp_waveforms_20261126.zip` → HTTP 200、
    字节数与 SHA-256 一致、解压后 `verify_release_package.py` 复现 `ok=147 … RELEASE PACKAGE OK`；
    GitHub 侧的 `assets[0].digest` 与本地哈希相同，等于第三方又独立算了一遍。
- **65 自称可复现的命令，必须在匿名克隆里跑一遍才算数。**（11-27）仓库公开、Release 上线、
    文档里每条命令在工作树里都绿之后，才做第一次第三方视角验收：`git clone --depth 1`
    到干净目录，逐条照文档跑。九条绿、三条红，而且是**同一种形状的红：
    什么都没做，但退出码是 0**。
    ①`extract_device_verdicts.py --verify` 报 653 行 `VANISHED …` exit 1——它只从遥测
    重新推导，而克隆里遥测 0 份；②`scan_secrets.py --path cloud` 在**不存在的目录**上打印
    `clean: 1 file(s) scanned` exit 0——`read_text` 的 `OSError` 被吞掉了，等于谎报"这里没凭据"；
    ③`preset_low_bp.py` 裸跑时默认清单 `v4_p{5,6,7}a_manifest.json` 从未被跟踪，三条 SKIP
    之后 exit 0——看起来像跑通了。
    修法都是让"做不了"显式失败或显式降级：`--verify` 无遥测时退回 metadata 校验并
    在末行声明做了哪一种；`--path` 不存在 exit 2；无清单 exit 2 并给出 `--from-raw`。
    **教训：开发工作树是"超集"，它能跑通不代表克隆能跑通；工作树里有多余的遥测、
    未跟踪的 `cloud/`、`tmp/` 下的清单，正好掩盖了三种"静默成功"。**所以验收顺序必须是
    先克隆、后宣布，而不是先宣布、再等第三方来报。

### E 本索引自身的边界

- 四份清点由四次只读清点完成（scope 0/1a/1b/2），另有两份文件（`p4_steepness_target_20261113.md`、
  `precision_levers_20261115.md`）由人工补入。合计 **262** 个文件，与 `data/checksums.sha256` 的 reports 段一致。
- `.csv` / `.ndjson` 只统计了行数与形态，**未逐行审读**；其"一句话结论"写的是数据形态，不是结论。
- 12 张 png 未做视觉核对。
- 本索引**不判断气路与硬件的安全性**，也不替代 `dataset_limitations.md` 的最小声明集。
