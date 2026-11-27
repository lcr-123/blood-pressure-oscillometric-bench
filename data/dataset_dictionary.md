# 数据集字段字典 —— `bp.capture/4`

本文件逐字段说明导出格式。字段名、类型和取值范围以
`blood pressure monitor/Core/Src/bp_capture_export.c` 与严格解码器
`blood pressure monitor/tools/bp_capture.py` 为准；两者不一致时以固件为准。

## 传输层

一次导出是一个 NDJSON 文本，每行一条 JSON。记录顺序固定：

```
begin → point × n → valve → timing → pulse × m → step × k → features → end
```

`step` 记录只在 `bp.capture/2` 及以后出现，本数据集全部为 `bp.capture/4`，且
`valve.steps = 0`，因此**没有 step 行**。

严格解码器强制以下不变式，任一不满足即视为不完整导出而拒收：

- 恰好一个 `begin`、一个 `end`；`end` 之后不得再有记录
- `point.i` 从 0 连续递增，条数等于 `begin.n`
- `begin.dropped == 0`（溢出整轮作废，绝不写部分数据）
- `begin.interval_ms == 25`
- `point.t` 严格递增（按 32 位回绕比较）
- `end.hash` 等于对除 `end` 外所有原始行做 FNV-1a（basis 2166136261，prime 16777619）的结果

## `begin`

| 字段 | 类型 | 含义 |
|---|---|---|
| `schema` | string | 固定 `bp.capture/4` |
| `type` | string | 固定 `begin` |
| `firmware` | string | 固件标识，本数据集全部为 `PEAK_WINDOW_20261105` |
| `n` | uint | 点数，上限 4200（40 Hz ≈ 105 s） |
| `dropped` | uint | 采样溢出丢弃数，必须为 0 |
| `interval_ms` | uint | 名义采样间隔，固定 25（即 40 Hz） |
| `raw_kind` | uint | 电压来源：`1` = ADS1115 引脚电压，`2` = 反算的传感器节点电压 |
| `cal_valid` | uint | 采集时校准是否有效，必须为 1 |
| `slope` | float32 位模式 | 校准斜率。**历史导出全部是 `82.326`**；2026-11-26 重标定后固件写 `81.529` |
| `intercept` | float32 位模式 | 校准截距。**历史导出全部是 `-19.887`**；2026-11-26 重标定后固件写 `-20.03` |
| `calc` | uint | 计算状态：`0` 未算、`1` 计算中（禁止导出）、`2` 计算完成且有效、`3` 完成但结果无效、`4` 已取消 |

本数据集中 `calc` 为 `2` 或 `3`；`3` 表示固件自身判定的血压结果无效，但**包络已算完并可复算**。

## `point`

| 字段 | 类型 | 含义 |
|---|---|---|
| `i` | uint | 序号，从 0 连续 |
| `t` | uint | MCU 毫秒 tick（`HAL_GetTick()`），32 位会回绕 |
| `p` | float32 位模式 | 袖带压力，mmHg。**负值被固件钳到 0**（`ads1115.c:215-218`） |
| `v` | float32 位模式 | 算法输入电压，V；单位由 `begin.raw_kind` 决定 |
| `e` | float32 位模式 | 示波包络，V（包络检波后的搏动幅值） |
| `s` | float32 位模式 | 平滑包络，V（`e` 经滑动平滑） |

**位模式不是普通浮点。** 所有 `float32` 字段都是 IEEE-754 单精度的**整数位模式**，需要
按 `<f` 重解释，不能直接当数值读。这样做是为了让导出可以逐位回放比对。

时间基准：`t` 是设备开机后的毫秒计数，不同轮次之间不可比；单轮内的差值可靠。
名义 25 ms，但相邻点差值受主循环负载影响，实测全数据集均为 25 ms、无 >40 ms 缺口。

## `valve`

放气阀（PC1 高有效）PWM 相位诊断。

| 字段 | 类型 | 含义 |
|---|---|---|
| `pulses` | uint | 本轮放气脉冲总数 |
| `period_min` / `period_max` | uint | 脉冲周期最小值/最大值，ms（标称 200） |
| `on_min` / `on_max` | uint | 阀开启时长最小值/最大值，ms |
| `threshold` | float32 位模式 | 压力阶跃判据，固定 `5.0` mmHg；不等于 5 即拒收 |
| `steps` | uint | 检测到的压力阶跃数，本数据集全为 0 |
| `phase` | uint[9] | 9 个 25 ms 相位箱内的脉冲计数 |
| `rise_*` / `fall_*` | mixed | 上升/下降沿检测结果，`*_found=0` 表示未检出 |
| `trace_n` | uint | 脉冲轨迹条数，上限 600 |

## `timing`

| 字段 | 类型 | 含义 |
|---|---|---|
| `n` | uint | 与 `valve.pulses` 一致 |
| `errors` | uint | 时序错误计数，必须为 0 |
| `complete` | uint | 是否为完整记录，必须为 1 |

## `pulse`

单次放气脉冲的开闭时刻。

| 字段 | 类型 | 含义 |
|---|---|---|
| `i` | uint | 序号 |
| `open` | uint | 阀开启的 MCU tick |
| `close` | uint | 阀关闭的 MCU tick |

注意：脉冲开启窗口**落在采样之后**（`main.c:2037` 先阻塞采样，`:2086` 才启动脉冲），
实测 `samples_in_on_window = 0`，所以放气脉冲不会污染压力轴。

## `features`

固件在采集内所选包的包络特征，**仅供对照，不是推荐结果**。

| 字段 | 类型 | 含义 |
|---|---|---|
| `map_i` | uint | 最大包络点序号 |
| `map_p` | float32 位模式 | 该点压力 |
| `sbp_found` | uint | 是否找到 SBP |
| `sbp_p` | float32 位模式 | 该点压力 |
| `dbp_found` | uint | 是否找到 DBP |
| `dbp_p` | float32 位模式 | 该点压力 |

**已知限制**：固件把 MAP 搜索窗写死在 80..100 mmHg（`bp_algorithm.c:534-541`），
SBP/DBP 上限写死 250/150（`:482`）。台架上四个预设的面板 MAP 分别是 93/116/166/215，
只有 Preset 1 落在窗内。因此 `features` 在 Preset 2/3/4 上**不可用**，`calc=3` 就是
这个原因。数据集使用者应改用 `tools/reference_bp.py` 做全量程复算。

## `end`

| 字段 | 类型 | 含义 |
|---|---|---|
| `n` | uint | 必须等于 `begin.n` 与点数 |
| `hash` | uint | 前面所有行（除 `end`）的 FNV-1a 校验和 |

## 派生 CSV

`tools/reference_bp.py` 与 `blood pressure monitor/tools/bp_capture.py --csv` 都可输出
解码后的 CSV：

| 列 | 含义 |
|---|---|
| `i` | 序号 |
| `mcu_tick_ms` | 原始 tick |
| `elapsed_ms` | 相对第一点的累计毫秒 |
| `pressure_mmhg` | `p` 解码，已钳 ≥0 |
| `algorithm_input_v` | `v` 解码 |
| `envelope_v` | `e` 解码 |
| `smooth_v` | `s` 解码 |
| `p_bits` `v_bits` `e_bits` `s_bits` | 原始位模式，用于逐位比对 |

## 逐轮索引（`data/manifest.csv` / `data/manifest.json`）

`bp.capture/4` 描述的是**一轮**的字节格式；库里有哪几轮、每轮属于哪一层、评过什么，
由 `tools/corpus_register.py` 生成的逐轮索引回答。索引共 **645 行**（= `data/raw/`
下 `*.export.ndjson` 的份数）**35 列**，工具落盘，**勿手改**。列的含义：

| 列 | 来源 | 含义 |
|---|---|---|
| `run_id` | 文件名 | `standard<SBP>_<DBP>_target275_peakwindow_<YYYYMMDD>-<HHMMSS>` |
| `date` / `clock` | run_id 尾部 | 本地时间的日期与时刻 |
| `preset` | run_id 前缀 | 1..7；早期固件的 run_id 不带该前缀，记空 |
| `panel_sbp` / `panel_dbp` / `panel_map` | `tools/corpus_register.py` 的 `PANELS` | 该档的面板设定值（mmHg） |
| `tier` | `tools/dataset_tiers.py` | 协议层，见下节 |
| `published_corpus` | `tools/dataset_tiers.py` | 该轮能否进入已发布表（62 轮为 True） |
| `dataset_role` | metadata | 采集脚本收到的 `--dataset-role` |
| `outcome` | metadata | `export_received` / `failed` / `aborted` / … |
| `firmware_hex12` | metadata | 烧录固件 hex 的 sha256 前 12 位 |
| `batch_tag` | metadata | 编排器写入的批次名（如 `crosstday`） |
| `batch_day` / `wrap_block` | metadata | 跨天批次的第几天 / 块字母（`A` 或 `B`） |
| `gate` / `gate_slope_mmhg_s` | `tools/validity_v2.py` 现算 | 采集门控判定与峰窗降压斜率 |
| `v2_*` | metadata `analysis` | 冻结估算器 v2 的三个估计值与其误差 |
| `v5_*` | metadata `analysis_v5` | `tools/covered_bp.py` 的三个估计值与其误差 |
| `valve_flow_mmhg_per_open_ms` / `valve_working_point` | metadata | 当天阀工作点 |
| `analysis_state` | 推导 | `scored` 表示 metadata 里有 v2 结论，`not_run` 表示没有 |
| `export_sha256` | 现算 | 导出文件字节的 sha256 |

> **索引行数 ≠ 磁盘轮数 ≠ metadata 份数。** 645 份导出对应 645 行；`data/raw/` 下另有
> 180 份只有 metadata、没有导出的轮次（预检失败、只做预检、早期阀门实验、跨天批次里
> 被安全阀或 profile 门拒绝的失败轮等），它们**不在索引里**，作为排除与调试证据保留。

## 协议层

`tier` 列的取值由 `tools/dataset_tiers.py` 从**冻结记录、评分报告和 metadata 里的
`batch_tag`** 推导，不手抄。因此新采集的轮次不可能悄悄混进已经用于评分的层。

| 层 | 轮数 | 进已发布表 | 判定它的是什么 |
|---|---|---|---|
| `frozen_baseline_v2` | 18 | 18 | `protocols/reference_bp_freeze_v2.json` 的 `baseline_rounds` |
| `prospective_v1` | 20 | 20 | `reports/reference_bp_prospective_v1.json` |
| `prospective_v2` | 20 | 20 | `reports/reference_bp_prospective_v2.json` |
| `v3_acceptance` | 40 | 0 | `reports/reference_bp_v3_validation.json` |
| `crosstday` | 266 | 0 | metadata 的 `batch_tag == "crosstday"`，协议在 `protocols/reference_bp_batch_crosstday_v1.md` |
| `supplementary` | 273 | 4 | 当前固件、不属于任何协议；只有 v3 预注册前采的 4 轮进已发布表 |
| `legacy_firmware` | 8 | 0 | `begin.firmware != "PEAK_WINDOW_20261105"` |

**已发布语料 62 轮 = 18 + 20 + 20 + 4**，分界点是 `2026-11-11T09:49:47`（冻结 v3 的
`5066fc5`）。在此之后的轮次一律不进已发布表，包括 40 轮 `v3_acceptance`、269 轮
`supplementary` 与全部 266 轮 `crosstday`。

`crosstday` 是 10 天 × 7 档 × 每天 4 轮的预注册跨天批次，最终实得 **266/280**（D1 因
操作员确认超时缺块B，是 `half_day`）。它的判定不走冻结常量，而是协议 §3 的 T0–T4
规则加 `tools/validity_v2.py`，结果在 `reports/crosstday_verdict_20261125.md` 与
`reports/crosstday_analysis_20261125.json`。

## 读数边界

- **压力轴**：`p` 被钳到 ≥0，真实负压（如 vent 态被阀线圈抬升的 +4 mmHg 偏移，
  或封阀后的 −2 mmHg）在 `p` 中丢失。若要未钳位值，用 `v`（当 `raw_kind=2` 时是传感器
  电压）反算，但**必须用这一份导出自己的 `begin.slope` / `begin.intercept`**：
  `p_true = v × slope + intercept`。645 份历史导出的这两个字段都是 `82.326 / -19.887`，
  而 2026-11-26 重标定之后采的轮次会是 `81.529 / -20.03`；写死常量会在两代之间差
  1–3 mmHg。
- **时间轴**：`t` 是 tick，不是采样时钟校验过的时基；名义 25 ms。
- **包络**：`e`/`s` 由固件在设备上用单精度浮点算出，与 `bp_capture.py` 的离线 C 回放
  逐位一致（本数据集全部 `replay_exact = true`）。这证明回放实现正确，**不**证明算法正确。

## 幅值轴的绝对换算

`envelope_v` 与 `smooth_v` 的单位是伏特，代表袖带内的压力摆动。要把它们换算成
mmHg 的**绝对幅度**，需要一个量：回路容积。

2026-11-09 直接测得的容积（**注意两种工况不同**）：

| 工况 | 回路构成 | 容积 |
|---|---|---|
| 测量工况 | MCU + 袖带 + 三通 + 阀 + 传感器 + 注射器接头，**BP Pump 2 已摘除** | **320 cc**（区间 278–320） |
| **数据集工况** | 上述 + **BP Pump 2 主气室 20 cc** | **≈ 340 cc** |
| 拆分 | 袖带气囊 ≈ 295–315，管路+三通+阀死腔+传感器口 ≈ 25 | |

BP Pump 2 的主气室是 20 cc，且**直接连在前面板压力端口上**（手册 Figure 3-1 说明
`:1317-1322`）；External Cuff 模式下 290 cc 罐体关闭，但 20 cc 主气室始终在回路里。
62 轮已发布语料的每一轮都是 BP Pump 2 通过三通接入、由它注入脉搏，所以**数据集的气路容积是
340 cc，不是 320 cc**。

> 佐证：阀外回路独立测得 362 cc，减去 20 cc 主气室后剩 342 cc；与本次 320 cc
> 加上主气室后的 340 cc 相差 2 cc（0.6%）。两条互不相干的路线收敛到同一个数。

换算用**绝压**，不是表压：

```
dP = P_abs · dV / V          P_abs = 760 + P_gauge   (mmHg)
每搏取绝热：dP = 1.4 · P_abs · dV / V
```

四个预设的中心值（**数据集工况 V = 340 cc**）：

| 预设 | P_gauge | P_abs | dV | dP 等温 | **dP 绝热** |
|---|---|---|---|---|---|
| 1 | 93 | 853 | 0.68 | 1.71 | **2.39** |
| 2 | 116 | 876 | 0.65 | 1.67 | **2.34** |
| 3 | 166 | 926 | 0.60 | 1.63 | **2.29** |
| 4 | 215 | 975 | 0.55 | 1.58 | **2.21** |

> 勘误一：本节早期写的是 `dP_mmhg = dV_cc × 101.3 / V_cc`，那是**错的** —— 101.3 是
> kPa/atm，混了单位，而且漏掉了表压项。
> 勘误二：早期按 V = 320 cc 换算，忽略了 BP Pump 2 主气室。数据集实际是 340 cc，
> 两者相差 6%。

**每搏用绝热、缓慢阶跃用等温。** 一搏只有 0.75 s，气体来不及与囊壁换热；
26 mL 的释放跨约 5 s 并观察了 210 s，接近等温。用 38 轮真实波形复核（见
`data/reports/volume_crosscheck_20261109.md`）：固定 V = 320 cc，绝热模型反解出
面板实际每搏推 0.61–0.77 cc，与标称 0.55–0.68 相差 10–28%；等温模型反解出
0.85–1.07 cc，相差 54–78%。**所以每搏幅度该用绝热系数 1.4。**

三个必须同时说明的边界：

1. **只在绷紧段有效**。100 mmHg 以下囊壁皱褶与泡沫的形变会吸收容积位移：
   0 表压下推入 26 cc 只产生 7.0 mmHg（气体定律要求 61.8），只完成 11.3%；
   抽 3 cc 只掉 0.66 mmHg（要求 7.46），完成 8.8%。低压段的 `envelope_v`
   不能按上表换算。
2. **320 cc 是有效容积**，对小幅度（每搏 0.5–1 cc）响应可信，对大幅阶跃
   （26 cc）可能因壁面再变形而偏小。
3. **面板的 `panel_pulse_volume_profile_cc` 是设定值，不是实测值**。若面板实际
   推入的容积与设定不符，由本表反算出的 dP 会同比偏离，而由 dP 反推的 dV 也会。
   两者不可同时当真。

测量方法、失败路径与误差来源见 `data/reports/dataset_loop_volume_result_20261109.md`，
分析工具 `tools/release_volume_analysis.py`。
