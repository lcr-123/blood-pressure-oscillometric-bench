# 跨天批次协议修订 2：收尾门控改看 seal 态零点（2026-11-16）

本文件修订 `reference_bp_batch_crosstday_v1.md` 的收尾判据，并在同一天覆盖
`reference_bp_batch_crosstday_v1_amend1.md` §4 末条「除编排脚本外其它脚本未改动」的陈述。

协议 §7 的铁律不变：**批次期间不得改任何脚本；若必须改，本批次在改动日终止，剩下的天数
归下一次预注册。** v1 与 amend1 在 2026-11-16 都没有产出完整天（见 §3），所以这次改动
同样把批次重置到改动日，代价为零。

判定规则 T0–T4、排除规则、每日仪表卡片五项、「不得做的五件事」、以及 amend1 的切换重试
全部不变。只改「一轮采完之后怎么确认气路是空的」这一条。

## 1 改了什么

| | v1 / amend1 原文 | 本修订 |
|---|---|---|
| vent 窗判据 | `all(est <= 6.0)` **且** `raw p2p <= 8`，20 s 内不满足即抛 `TimeoutError('vented reading did not reach its plateau')` | 只要求窗口**平稳**：`raw p2p <= 20`、`est span <= 0.5`、全 VALID，另加粗上限 `max(est) <= 10.0` |
| 空否的证明 | 由 vent 窗的 `est` 绝对值承担 | 由随后的 **seal 态真零点**（`sensor mV` 反算，未钳位）承担，门限仍是 ±5.0 mmHg，未变 |
| 记录 | `closeout_criterion`、`closeout_attempts` | 另加 `closeout_vented_ceiling_mmhg`、`closeout_settle_raw_p2p_max`、`closeout_settle_est_span_max`、`closeout_amendment` |

即：**vent 态读数不再被当作零点**。它带着阀2 线圈通电的偏移，而偏移量取决于线圈热态；
seal 态才是这份数据画图、算误差时用的零点，也是唯一能证明「气路空了」的状态。

## 2 为什么要改（2026-11-16 的实测证据）

### 2.1 失败轮与成功轮的 vent 窗几乎一样平

D1 第四轮（amend1 编排，`crosstday_d01_20261116-171336`）P1 第 1 个 slot 连试 4 次，
2 轮成功 2 轮失败，失败全部是同一个 `vented reading did not reach its plateau`。
把每轮最后一次 `[Deflate] VENT` 之后的 20.6 s 窗口取尾 40 样本：

| run_id 尾号 | 结局 | vent 窗 raw p2p | vent 窗 est 范围 | est span |
|---|---|---|---|---|
| `-171344` | failed | 11 | 6.50–6.70 | 0.20 |
| `-171608` | export_received | 5 | 0.80–0.90 | 0.10 |
| `-171935` | failed | 9 | 4.90–5.00 | 0.10 |
| `-172159` | failed | 7 | 7.10–7.20 | 0.10 |
| `-175439` | export_received | 4 | 0.40 | 0.00 |
| `-175950` | export_received | 5 | 0.40 | 0.00 |
| `-180309` | export_received | 4 | 0.30–0.40 | 0.10 |
| `-180636` | export_received | 6 | 0.40–0.50 | 0.10 |

八个窗口**全部是平的**（est span ≤ 0.20，raw p2p 4–11）。旧门限拒掉的两个窗口，唯一
超标的是 **est 的绝对水平**（6.50、7.10 > 6.0），不是平稳性。旧判据名义上在检测
「没排干净」，实际在检测「线圈此刻有多热」。

### 2.2 vent 态水平由线圈热态决定，不是残气量

| 探针 | 做法 | 结果 |
|---|---|---|
| `tmp/vent_state_now_20261116.py vent_state_a 60` | 静置 `stop`+`vent` 观测 60 s | `raw_med 1372`、p2p 2–4、`est 0.00` 全程 12/12 窗通过 |
| `tmp/vent_seal_alternate_20261116.py vent_seal_alt_a 8` | 静置时交替 vent 6 s / seal 6 s × 8 | `raw` 差 +38…+40（≈+0.47 mmHg），两态 `est` 都 0.00 |
| `tmp/post_deflate_vent_20261116.py post_deflate_vent_a 275 180` | 充到 275 → 固件 PWM 放气 → vent 180 s | t=5 s `est 2.50` gate=NO；**t≥15 s 起 `est 2.30`、p2p 1–5，稳定到 180 s** |
| `tmp/panel_vent_offset_20261116.py panel_vent_offset_a 275` | 面板不动 vs 面板在 Standard BP #1 各跑一次 275 充放 | `Δraw_med = +5`、`Δest = +0.10 mmHg`（**否证**「面板 SIM 态加载气路」） |
| `tmp/coil_cool_20261116.py coil_cool_a 60` | 充 60 放气后交替 vent/seal × 5 | vent 态 `est` 2.40→2.10、`raw_med` 1566→1550，冷却只降一点，**稳定在一个 >0 的平台上** |
| `tmp/post_capture_alternate_20261116.py post_capture_alt_c` | 真实采集后交替 vent 6 s / seal 6 s × 6 | vent `raw_med 1546–1552`、seal `raw_med 1383–1390`，`Δraw = +161…+165`（≈+2.0 mmHg）；逐样本序列两态各自平稳、切换瞬间跳变 |

逐样本序列是关键证据：两态的读数各自是一条直线，切换发生在单个 25 ms 采样间隔内。
若是真有气体残留，`raw` 会在 vent 打开后连续下降；实际是**一步跳变**，符合「线圈通电
改变了传感器读数」而非「气体进出」。

### 2.3 偏移量随时间与热态在 +0.4…+7.4 mmHg 之间变化

- 静置 vent：`est = 0.00`（`raw 1372`）
- 275 充放结束后 15 s：`est = 2.30–2.40`（`raw ~1565`）
- 同一天某些轮次：`est = 6.50 / 7.10`（同上平稳）
- 同一个 seal 态：`est = 0.00–0.80`，真零点在同一批轮里是 −0.87 … +0.36 mmHg

所以把 vent 态 `est` 卡在 6.0，等价于把「线圈有没有热到某个程度」当成「气排干净没有」。
这既不是它要测的东西，也会随机作废掉 seal 零点明明干净的轮次。

## 3 记账

- v1（`reference_bp_batch_crosstday_v1.md`）：2026-11-16 改动，无完整天，产出为零。
- amend1（`..._v1_amend1.md`）：同日改动，块A 跑通 14 轮但块B 首档切换反复丢应答，
  仍然无完整天，产出为零。三组块A 共 28 轮已移入 `tmp/omniprobe/quarantine_20261116/`。
- 本修订（amend2）：同日改动，重置到本日。
- 今天 `data/raw/development_20261101/` 下的 20261116 诊断轮（含 `-171344`…`-180636`
  共 8 轮，其中 6 轮 `export_received`）**全部不进入本批次 280 轮**，移入
  `tmp/omniprobe/quarantine_20261116/`，报告里只能作为「门控缺陷的证据」引用。
  `daily_card_20261116.json` 保留：它是当日仪表状态，不随某次采集失败而失效。

## 4 本修订之后

- D1 用 amend1 编排脚本 + amend2 采集脚本从头跑：7 档 × 2 轮 × 块A/块B = 28 轮。
- 脚本哈希（2026-11-16 18:55 记录）：

| 脚本 | sha256 |
|---|---|
| `tmp/run_crosstday_20261116.py`（amend1） | `e963e0fb5fd7960e6a289a139bc60790811abdbec5ff5aa3c021c2c98d55589e` |
| `tmp/bp_standard255_195_target275_peakwindow_20261105.py`（amend2） | `849d1db38a4ddd4bb94f7114cb802b74dcf2948fbef7c6c57c00b7e406b48d47` |
| `tmp/crosstday_analyse_20261116.py` | `e28308230497cf8c2717bddbb757cdbfb6ba87e88f90aa66333d311cfa896cc8` |
| `tmp/daily_valve_point_20261116.py` | `5ae7679df6967288881d3d69df250b61ca101d7f979b4f72a3c7075eddac2027` |

- `tmp/crosstday_analyse_20261116.py` 的 T0–T4 不读收尾门控字段，因此本修订不改变判定
  逻辑，只改变「哪些轮次能走到 export 阶段」。
- 本修订之后若再改任何脚本，批次从改动日终止，规则同 v1。
