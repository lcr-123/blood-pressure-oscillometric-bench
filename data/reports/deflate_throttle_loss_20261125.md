# 降压阀失节流：五例，不是三例（2026-11-25 追查）

本报告追查一件跨天批次 D10 里被冻结门抓到的事：**有一轮的压力剖面不是按设定的
1.8 mmHg/s 放出来的**。追下去发现这不是 D10 独有的故障，全库一共五例，而且固件
自己完全不知道发生过。

本报告不含任何 MAP/SBP/DBP 估计值，只谈压力剖面、阀门命令与固件机制。

---

## 0 一句话

全库 645 份导出里有 **5 轮**在 200–250 mmHg 段的降压斜率超过冻结门的 4.0 mmHg/s
（最陡 −33.40），形态完全一致：**闭环把开阀时间一路绕到 14–29 ms，阀在那段时间里
几乎不放气；气阻一放开，绕上去的占空比就在 3 s 内一次泄掉**。固件只在中止条件里
检查采样溢出与读失败，**"压力掉太快"没有任何运行时检查**，事后算导出斜率是唯一
发现手段；而冻结门恰好抓得住它，五轮全部被拒。附带发现：**已发布的 62 轮里有 4 轮
正是这五例中的四个**——"已发布"与"被门接受"是两层，不能混说。

---

## 1 触发点

跨天批次 D10（2026-11-25）块B 的 `P1 a2`（`standard120_080_target275_peakwindow_20261125-135554`）
在编排器逐轮跑门时被判 `REJECTED`：

```
REJECT peak_slope=-16.14 mmHg/s
  peak-window deflation ran at -16.14 mmHg/s against a limit of 4.0;
  healthy rounds measured 1.56..2.63, so the deflate valve was not throttling
  and the round does not represent the intended pressure profile
```

这一轮随后按协议 §4 规则 5 被排除，D10 的可用轮数记 27（仍是完整天）。
D10 的日报（`crosstday_d10_20261125.md` §3.3）当时写的是"全库另有 2 例同型"——
**这个数字是错的**，第 2 节更正。

---

## 2 语料里到底有几例

### 2.1 全库复核（不依赖元数据里有没有门键）

`data/raw/development_20261101/*.metadata.json` 里带 `gate_rejected` 键的只有 **5/770 份**，
其中 `true` 的只有 2 份——因为**门只在部分日期被跑过**，元数据里的门键不能当作
"这一轮没被拒"的证据。所以必须逐份重跑：

```powershell
# tmp\gate_corpus_20261125.py：对 645 份导出逐份 subprocess 跑 tools\validity_v2.py
python tmp\gate_corpus_20261125.py
```

结果 **645 份里 11 份 REJECT**，分三类：

| 类 | 数量 | 说明 |
|---|---|---|
| 2026-11-01 旧固件（无 `type=pulse`） | 6 | `standard120_80_*`×4、`standard150_100_20261101-123247` 等，门对它们没有意义 |
| 解码失败 | 1 | `standard080_050_…20261113-162512`（`decode_error`） |
| **阀失节流** | **5** | 见下表 |

五轮（`200–250 mmHg` 段 OLS 斜率，与门的算法同口径）：

| run_id | 段斜率 | 门的读数 | 同日采集序 |
|---|---|---|---|
| `standard200_150_…20261107-212915` | **−33.40** | −32.87 | 11-07 第 30 轮 |
| `standard255_195_…20261107-215245` | −16.96 | −16.81 | 11-07 第 37 轮 |
| `standard120_080_…20261125-135554` | −15.18 | −16.14 | 11-25 第 16 轮 |
| `standard150_100_…20261107-202606` | −14.32 | −15.49 | 11-07 第 18 轮 |
| `standard120_080_…20261107-154020` | −13.76 | −13.35 | 11-07 第 12 轮 |

（我这边算的段斜率与门的 `peak_slope` 差 0.2–1.0 mmHg/s，是因为门的窗口取
`PEAK_LOW_MMHG 200.0`–`PEAK_HIGH_MMHG 245.0` 且要求 `MIN_PEAK_WINDOW_POINTS 40`，
我用的是 200–250；两者判定方向一致，四舍五入不影响任何结论。）

**分布**：全库 637 份有 duty 数据的导出里，段斜率 `min −33.399 / p1 −3.363 /
median −1.917 / max −1.39`，**陡于 −4.0 的只有这 5 轮**。

### 2.2 更正 D10 日报的"3 例"

`crosstday_d10_20261125.md` 的 §0 第 2 条与 §3.3 的"全库同型先例"表只列了
`…212915`、`…215245` 与未拒的 `…213112`，据此写"18 天里出现 3 次"。
正确说法是**5 例**，而且**四例集中在 2026-11-07 的同一天**。D10 那一轮是第 5 例。

### 2.3 事件是单轮的，不传染

按采集时刻排 2026-11-07 当天 44 轮：

```
…153646 (−1.867) → …154020 (−13.757) → …154308 (−1.809)
…202234 (−1.823) → …202606 (−14.316) → …202825 (−1.730)
…212549 (−1.896) → …212915 (−33.399) → …213112 (−1.982) → …213433 (−2.040)
                 → …213751 (−3.061, duty_max 32) → …214926 (−2.182)
                 → …215245 (−16.964) → …215530 (−2.977, duty_max 15)
```

2026-11-25 一天 29 轮，唯一的陡轮是 `…135554`，前一轮 `…135229` 是 −1.770、
后一轮 `…135843` 是 −1.854。

→ **每一例的前后轮都正常**，事件只持续一轮，不跨越轮次传染。
但注意 `…213751`（−3.061、`duty_med` 25）与 `…215530`（−2.977、`duty_med` 16）
两轮紧跟在最陡的两例之后、**没超门但比全天中位陡 60 %**——见 §6.2，
它们是同一个机制的"余震"，不是独立现象。

---

## 3 固件是怎么节流的

全部在 `blood pressure monitor/Core/Src/main.c`。

### 3.1 常量

| 位置 | 名字 | 值 | 备注 |
|---|---|---|---|
| `main.c:155` | `DEFLATE_PWM_PERIOD_MS` | **200** | 5 Hz 阀基频，注释说明"在脉冲分析频带之上" |
| `main.c:170` | `DEFLATE_PWM_BASE_ON_MS` | **1** | 注释：真人手臂气阻小，2 ms 放气太快（0.65 s 放完），降到 1 ms |
| `main.c:171` | `DEFLATE_CONTROL_INTERVAL_MS` | **400** | 两个完整阀周期才调一次 |
| `main.c:183` | `DEFLATE_PWM_MAX_ON_MS` | **90** | 上限 |
| `main.c:172-177` | 目标速率 | peak 窗内 **1.8**、`≥200 mmHg` 高速档 3.0、否则 2.0 | `mmHg/s` |

`DeflateTargetSpeed()`（`main.c:272-284`）：只有 `s_inflate_target_mmhg >= 200` 时才可能
进高速档；peak profile 打开且当前压力在 200–245 之间 → **1.8 mmHg/s**。

### 3.2 闭环（`main.c:2142-2170`）

每 400 ms：

```
actual_speed = (s_deflate_last_pressure - g_last_pressure_mmhg) / dt
smooth       = 0.6 * actual_speed + 0.4 * s_deflate_speed_prev
err          = smooth - target_speed
err < -0.4  →  on_ms += 1      （下限 1）
err > +0.4  →  on_ms -= 1
上限 DEFLATE_PWM_MAX_ON_MS = 90
```

**每 400 ms 最多动 1 ms**。从 1 ms 爬到 18 ms 需要 **6.8 s**；而 200–245 mmHg 在
1.8 mmHg/s 下只有 25 s。**调控带宽（0.25 Hz、1 ms/步）与观测带宽同量级**，
这是后面所有现象的共同前提。

### 3.3 脉冲执行（`main.c:2125-2132` / `345-363` / `384-395`）

```
if ((int32_t)(now - s_deflate_next_pulse_ms) >= 0) {
    DeflatePulse_Start(s_deflate_pwm_on_ms);
    s_deflate_next_pulse_ms = now + DEFLATE_PWM_PERIOD_MS;   /* 从实际开始时刻排 */
}
```

注释原话：**"Schedule from the actual start time. If the main loop was delayed,
do not emit catch-up pulses back-to-back."** —— 这是理论上的一条"少放气"通道
（主循环一旦延迟就永远补不回来），但不是本次五例的原因：五例的
`type=pulse` 里周期间隔严格 200 ms，没有漏拍。

`DeflatePulse_Start()`：`__disable_irq()` → `VALVE2_OPEN()` → 记 `on_ms` →
`BP_Algorithm_RecordValvePulse(HAL_GetTick(), on_ms)` → `__enable_irq()`。
**关闭在 SysTick 里**（`HAL_SYSTICK_Callback` 每 1 ms 递减，到 0 才 `VALVE2_CLOSE()`），
所以 ADS1115 的阻塞读拉不长脉冲。

### 3.4 软起动与结束

- 进入 PWM 时（`main.c:2018-2030`）`s_deflate_pwm_on_ms = DEFLATE_PWM_BASE_ON_MS`（1 ms）、
  `s_deflate_speed_prev = 0`、打 `[Deflate] PWM started after hold`。
  **每轮都从 1 ms 重新爬**，没有跨轮记忆。
- 结束在 `g_last_pressure_mmhg < 15.0f`（`main.c:2054`），打 `[Deflate] done; valve2 closed`。
  注释解释为什么用 15 而不是 5：BP Pump 2 External 在低压段会维持约 5–6 mmHg。

### 3.5 固件不知道压力掉太快

降压段只有两条中止路径（`main.c:2077-2123`）：

- `BP_Algorithm_AddSample()` 失败 → `BP_FAULT_SAMPLE_OVERFLOW` + `[Safety] Sample overflow during deflate; emergency vent`
- `ADS1115_ReadSample()` 失败 → `BP_FAULT_SENSOR_READ` + `[Safety] Pressure read failed during deflate; emergency vent`

**"压力比目标掉得快"不在其中。** 五例的降压段串口日志都只有
`[Deflate] PWM started after hold` 与 `[Deflate] done; valve2 closed` 两行，
**零故障码、零告警**。

---

## 4 取证通道：`type=pulse` 与 `type=step`

这一节是本报告的方法学部分——这两个导出事件以前没用过。

`blood pressure monitor/Core/Src/bp_capture_export.c`：

| 事件 | 位置 | 内容 |
|---|---|---|
| `type=pulse` | `:132-138` | `{"i":%u,"open":%lu,"close":%lu}`，单位 HAL tick ms |
| `type=step` | `:115` | `{"i":%u,"phase":%u,"on":%u}`，`phase` 单位 10 mmHg |
| `type=valve` | `:90` | 聚合：`pulses / period_min / period_max / on_min / on_max / threshold / steps / phase[9] / …` |

两个关键事实（`tmp/deflate_ticks_20261125.py` 实测）：

1. **`pulse.open` 与 `point.t` 是同一个 tick 域**。`point t` 首值 11329638、严格 25 ms；
   `pulse` 首 `(0, 11329614, 11329615)`、严格 200 ms。两者**从不相等**（0/354 命中），
   但到最近 `point` tick 的距离 **min 1 / median 1 / max 24 ms**——同一时钟、相位差 1 ms。
   所以**必须用 `bisect` 最近邻配对，不能要求相等**（第一版脚本就是在这里全丢了）。
2. **`type=step` 只在 `on_ms` 变化时写一条**，不是每周期一条。所以
   `-135554` 的 `steps=13` 聚合只对应 **12 条** `type=step` 记录，全部 `phase=24`（240 mmHg），
   `on` 从 16 **单调降到** 10：

```
(376,24,16) (384,24,15) (392,24,15) (400,24,14) (408,24,14) (416,24,13)
(424,24,13) (432,24,12) (440,24,12) (448,24,11) (456,24,11) (464,24,10)
```

**这 12 条就是"闭环把 on_ms 从 16 ms 退回 10 ms"的现场记录**——它是 §5.3 那个
"泄放后回卷"阶段的直接证据，不需要再靠推测。

对照：健康轮 `-135229` 全程 `on 1..12 ms`、**`type=step` 计数 0**（闭环从未需要
发出超过几个 ms 的脉冲）。

---

## 5 五轮的解剖

### 5.1 时间线

`tmp/deflate_steep_20261125.py`（t=0 为该轮导出首样本；本轮一律从 `on=1 ms` 起步）：

| run | 最宽脉冲 | 首个爆发 | 爆发次数 | 最大单周期压降 |
|---|---|---|---|---|
| `…20261125-135554` | t=8.38 s / **18 ms** / p=249.1 | t=8.78 s / p=246.7 / 17 ms / **3.34** | 15（至 11.58 s） | 5.79 |
| `…20261107-212915` | t=10.38 s / **27 ms** / p=245.6 | t=10.18 s / p=253.0 / 26 ms / **7.41** | 7（至 11.38 s） | 9.19 |
| `…20261107-215245` | t=7.18 s / **18 ms** / p=254.8 | t=7.18 s / 同一点 / **9.03** | 12（至 10.38 s） | 9.03 |
| `…20261107-202606` | t=11.18 s / **29 ms** / p=249.6 | t=11.38 s / p=248.3 / 29 ms / 2.87 | 10（至 13.98 s） | 9.05 |
| `…20261107-154020` | t=5.98 s / **16 ms** / p=246.0 | t=5.78 s / p=257.0 / 15 ms / **11.01** | 9（至 7.98 s） | 11.01 |

共同点，五轮全中：

1. **最宽脉冲都落在 245–255 mmHg**（245.6 / 246.0 / 249.1 / 249.6 / 254.8）——
   恰好是进入峰窗（200–245）**之前**那一小段，压差最大的地方。
2. **爆发窗口都只有 2–3 s**，然后自行恢复。
3. 健康轮 `-135229` 的最宽脉冲是 **12 ms 但发生在 t=92 s / p=14.9**（已到低压段、
   闭环在追 20 mmHg/s 的尾段），**峰窗内最宽只有 7 ms**，所以 `duty_med` 天然小。

### 5.2 爆发的形状是锯齿，不是连续快泄

`tmp/deflate_shape_20261125.py`，`-135554` 逐 200 ms 周期：

```
t=9.000  −3.08
t=9.200  −3.42
t=9.400  −6.70   随后 +2.63
t=9.600  −6.75   随后 +2.66
t=9.800  −6.82   随后 +2.60
t=10.000 −6.28   随后 +2.36
```

**每 200 ms 掉 3–7 mmHg，紧跟着回弹 2.4–2.7 mmHg。** 净效应约 −4…−5 mmHg/周期，
但瞬时单步最大 **−6.82 mmHg / 25 ms ≈ 273 mmHg/s**。

对照健康轮 `-135229`：同样有锯齿，但每 200 ms 只掉 **0.4–0.8**、回弹 **+0.33**。

→ **失节流不是"阀一直开着"，而是"阀在该关的时候没关上，把整个 200 ms 周期的
绕上去的开度都放掉，然后压力回弹、下一周期重复"。**

### 5.3 gain 崩溃 → 闭环绕档 → 泄放

`gain` 定义为「一个 200 ms 周期的净压降 / 该周期的 commanded open ms」，单位 mmHg/ms。

`tmp/deflate_gain_series_20261125.py` 输出 `-135554` 在 200–258 mmHg 带的完整序列：

- **爆发前**：`on_ms` 从 12 单调爬到 18（t=6.18→8.58 s），而每周期压降仍只有
  −0.28…−0.97 → **gain 从 0.089 单调跌到 0.018–0.021**（5.2 倍下跌）。
  即：阀开 17 ms 只放出约 0.35 mmHg。
- **爆发期**：同样的 11–18 ms 命令宽度，压降跳到 2.5–5.8 mmHg →
  **gain 0.196→0.362**（涨 10–17 倍）。
- **泄放后**：gain 回到 0.05 附近，`on_ms` 每 400 ms 降 1 ms，用 **4.4–8.0 s**
  才退回 <8 ms（这就是 §4 那 12 条 `type=step` 记录的内容）。

**机理（这是本报告的核心判断）**：

> 阀端气阻先崩溃（开 16 ms 也几乎不放气）→ 闭环只看到"放得太慢"→ 每 400 ms 加 1 ms
> → 一路绕到 16、18 甚至 27 ms → 气阻一旦放开，**绕上去的占空比一次性泄掉** 3–9 mmHg
> → 压力回弹、gain 恢复 → 闭环再用 4.4–8.0 s 慢慢退回。

**不是"阀被关掉"，而是"阀在该放的时候不放，然后用积压的开度补放"。**
这也解释了为什么五轮的最宽脉冲都在进入峰窗之前那一段：那一段压差最大，
"该放多少"与"实际放了多少"的差最先被闭环看见。

### 5.4 gain 比值不能当判据

直觉上"gain 突然涨 6.8 倍"应该很异常。实测**不成立**：

`tmp/deflate_gain_corpus_20261125.py`（637 份，195–258 带，`ratio = max/median`）：

- **ratio ≥ 3.0 的有 524 份（82 %）**；
- ratio 榜首既有真被拒轮（`-212915` 27.3×），也有大量 `openmax=3` 的健康轮（17–19×）。

→ **gain 抖动是这台台架的常态**（每周期只掉 0.2–0.6 mmHg，分母小、量化误差大），
**比值永远分不开**。判据只能落在 commanded duty 的绝对高度上（§6）。

---

## 6 能不能用一条运行时规则替代门

值得问：既然机制清楚了，能不能在固件里加一条检查（比如"commanded duty 超过 X ms
就报故障"），把门从事后变成事前？

### 6.1 duty 是**必要**条件

全库 637 份、245–255 mmHg 带的 `duty_med`（`tmp/deflate_band245_20261125.py`）：

| 组 | 轮数 | `duty_med` 范围 |
|---|---|---|
| 五例陡轮 | 5 | **14 / 16 / 18 / 26 / 26** |
| 其余（正常） | 630 | 2 … 25（p90 = 6、p99 = 12） |

`duty_med ≥ 14` 的轮次里**包含全部五例**，没有一例例外。

### 6.2 但**不是**充分条件

同为 245–255 带、`duty_med ≥ 8` 的轮次一共 **27 轮，其中只有 5 轮爆发**。
最高的几个健康轮：

| run | `duty_med` | `duty_max` | 段斜率 |
|---|---|---|---|
| `…20261107-213751` | **25** | **32** | −3.06（未超门，但比中位陡 60 %） |
| `…20261107-215530` | 16 | 16 | −2.98（同上） |
| `…20261125-125122` | 14 | 20 | −1.98 |
| `…20261125-130555` | 14 | 14 | −1.91 |
| `…20261107-201902` | 13 | 14 | −1.78 |

→ **把阈值放在任何位置都会误报**：`duty_med ≥ 14` 命中 5 例，但也命中
`…213751`（25）、`…215530`（16）、`…125122`（14）、`…130555`（14）四轮健康轮。
D10 的样本看，`duty_med ≥ 8` 会命中 10 轮而只有 5 例是真事件。

而 `…213751` 与 `…215530` 恰好是**紧跟在最陡两例之后**的轮（§2.3）——
它们不是误报，是**同一个机制的余震**：阀还没完全恢复，闭环仍要求 16–25 ms，
但气阻已经半放开，所以斜率只是"略陡"而不是"失节流"。
**这恰好说明用"duty 高"做判据在物理上是对的、在统计上不可分**：
它测的是"闭环在补偿多少"，而事件是"补偿量一次性泄放"，两者只在爆发那一刻分开。

### 6.3 结论：门仍是唯一检测手段

- **duty 判据**：必要不充分，落在 14–25 的区间正好被余震占满，误报不可避免。
- **gain 比值判据**：82 % 的正常轮都能到 3 倍以上（§5.4），完全不可用。
- **斜rate 判据**：就是要算 OLS 斜率，即现在的门 `DEFLATE_RATE_MAX_MMHG_S 4.0`。

→ 如果要在**运行时**做，唯一可靠的形式是固件自己也按 25 ms 采样算一个滑动窗口斜率
（比如最近 40 个采样 = 1 s，`rate < -8.0` 即中止），而不是看 `on_ms`。这是一个
**固件改动**，需要重烧 hex、批次重新起算，所以本批次不做，写进"下次预注册"清单。

---

## 7 已发布语料里的四轮

这一节是本次追查的副作用，但重要性不亚于机制本身。

`tools/dataset_tiers.py:168-181`：

```python
def in_published_corpus(row):
    tier = row["tier"]
    if tier in PROTOCOL_TIERS:       # frozen_baseline_v2 / prospective_v1 / prospective_v2
        return True                  # ← 不看 gate
    if tier != "supplementary":
        return False
    stamp = captured_at(row["run_id"])
    return stamp is not None and stamp < datetime.fromisoformat(PUBLISHED_AT)
```

→ **"已发布 = 被列进冻结协议层"，与"被门接受"无关。**

实测（`tmp/published_gate_20261125.py`）：已发布 62 轮的 `gate` 列是
**`USABLE 58 / REJECTED 4`**，那 4 轮正是本报告五例里的四个：

| run | tier | 段斜率 | 来源 |
|---|---|---|---|
| `…20261107-154020` | `prospective_v1` | −13.35 | v2 冻结记录 `retrospective_check_of_the_gate` 列为 reject |
| `…20261107-202606` | `prospective_v1` | −15.49 | 同上 |
| `…20261107-212915` | `prospective_v2` | −32.87 | v2 评分报告标 `status: "gate_rejected"` |
| `…20261107-215245` | `prospective_v2` | −16.81 | 同上 |

已发布集的段斜率分布因这四轮被拉出长尾：`min −32.865 / median −1.904 / max −1.556`。

**三份冻结记录对它们的处理并不一致**：

- `reference_bp_freeze_v2.json` 的 `retrospective_check_of_the_gate` 明确列了
  前两轮为 reject，`false_positives_on_development: 0`、`healthy_prospective_rounds_retained: 18`——
  但**这两轮仍在 `prospective_v1` 层的 20 轮里被算作已发布**。
- `reference_bp_prospective_v2.json` 把后两轮标成 `status: "gate_rejected"`、
  `gate_usable: false`、`map_err/sbp_err/dbp_err` 全 `null`——**评分时确实剔除了**。
- `reference_bp_prospective_v1.json` **没有 gate 字段**：`…154020` 是
  `status: "unresolved_map"`（理由写的是包络瞬态，不是阀）、
  `…202606` 却是 **`status: "ok"`**，给出了 `map_mmhg 202.93 / sbp 238.24 / dbp 130.94`
  （面板 P2 是 150/100，**MAP 差 +86.9**）。v3 冻结记录的 `why` 正是拿这一轮当理由。

→ **同一个物理故障，三份记录给了三种处置**。这不影响已发布语料的轮数（62），
但**任何引用 62 轮统计的人必须知道其中 4 轮的压力剖面不合格**；
`dataset_limitations.md` 与 `dataset_scope_statement.md` 已有相关条目，
本报告把它们与"阀失节流"这个统一原因对上。

---

## 8 处置

| 对象 | 处置 | 理由 |
|---|---|---|
| D10 `…135554` | `gate_usable: false`，判定按 §4 规则 5 排除，**不重采** | 协议没有"门拒绝就补采"条款；这一轮的存在本身就是有效信息 |
| D10 可用轮数 | 27（仍算完整天） | 两块都在、每档都有存活轮 |
| 本报告 §2.2 | 更正 D10 日报的"3 例" | 应为 5 例 |
| 前四轮 | **不动** | 它们已在冻结协议里，改就是改已发表语料 |

---

## 9 下次预注册该写进去的四件事

1. **门必须写进采集期，不能只事后算**。跨天批次做到了（编排器每轮跑
   `tools/validity_v2.py`、`gate_usable` 进 manifest）；更早的 v1/v2 批次没做到，
   于是四轮带病进了已发布层。下次预注册把"每轮必跑门 + 门结果进元数据
   `gate_rejected` / `gate_slope_mmhg_s`"写成硬要求，且**元数据里必须有键，
   不能靠"没键就是没跑过"来推断**（本报告 §2.1 就是被这个坑绊过）。
2. **"已发布"与"门接受"是两个字段**，文档里必须分开写。建议 manifest 增一列
   `gate` 已在（35 列里有），但 README 的"62 轮"说明里应注明"其中 4 轮被门拒绝"。
3. **固件加一条运行时斜率检查**（§6.3）：滑动窗口 1 s 的 OLS，`rate < -8.0 mmHg/s`
   即中止并记 `BP_FAULT_*`。残留的 `on_ms` 已能作为第二证据。需要重烧 hex，
   所以要随下一次固件改动一起做，不能塞进正在跑的批次。
4. **失败轮也要落证据**：本报告能成立，靠的是 `type=pulse`/`type=step` 在
   **成功导出**里；如果这一轮最后失败（比如超压中止），那 354 条脉冲记录就不会有。
   建议把 `type=pulse` 也写进 `.ndjson` 的侧通道（与 amend4 §7 的"失败轮 .out 归档"
   同一条思路）。

---

## 10 还缺什么

1. **气阻崩溃的物理原因没查**。可能方向：阀线圈温度（11-07 那天四例集中在
   15:40–21:52，机房温度未记）、阀芯异物、`VALVE2_OPEN()` 的驱动电流不足
   （`PB8` 是开漏 + 外部继电器？需看原理图）、或气路里凝水。**五例里有四例在
   同一天**，这条比"随机偶发"更值得追。
2. **`-213751` / `-215530` 两轮"余震"没有独立证据**。它们只是斜率偏陡 + duty 高，
   没有爆发记录；要确认是同一机制，需要更细的（<200 ms）压力分辨率。
3. **`DEFLATE_CONTROL_INTERVAL_MS 400` 是否该降到 200**：现在每两个阀周期才调一次，
   等于闭环采样率只有 2.5 Hz。降到 200 会让爬升快一倍（1→18 ms 只需 3.4 s），
   但也可能引入振荡。这是固件改动，需单独台架验证。
4. **`type=step` 的 `phase` 语义只有 9 个槽**（`phase[9]` 聚合），11-07 那两例
   出现了 `phase=[34,22,0,…]` 与 `[18,9,0,…]`——`34`/`32` 超过 30 个槽位，
   说明这个聚合数组在 <320 mmHg 之外会溢出。不影响本报告（用的是 `type=pulse`
   的原始 open/close），但导出侧值得修。

---

## 11 复现

```powershell
# 1. 全库跑门，找出所有 REJECT（645 份，约 20 分钟）
python tmp\gate_corpus_20261125.py

# 2. 全库 commanded duty 与 200-250 段斜率（637 份）
python tmp\deflate_duty_corpus_20261125.py

# 3. 245-255 带的分桶（本报告 §6.1 的表）
python tmp\deflate_band245_20261125.py
python tmp\deflate_bandstats_20261125.py

# 4. 五轮的时间线、锯齿、gain 序列
python tmp\deflate_steep_20261125.py
python tmp\deflate_shape_20261125.py
python tmp\deflate_gain_series_20261125.py

# 5. gain 比值不可用的证据（82% 正常轮 ratio >= 3）
python tmp\deflate_gain_corpus_20261125.py

# 6. 已发布 62 轮里的门状态
python tmp\published_gate_20261125.py
```

冻结门本体：`tools/validity_v2.py`（sha256 `0857b93a172b027c4ff9c9835b29078cb9c92b848c6b759441d1d1b70bddf880`），
常量来自 `data/protocols/reference_bp_freeze_v2.json` / `…_v3.json` 的
`validity_gate.constants`：`PEAK_LOW_MMHG 200.0`、`PEAK_HIGH_MMHG 245.0`、
**`DEFLATE_RATE_MAX_MMHG_S 4.0`**、`MIN_PEAK_WINDOW_POINTS 40`。

---

## 附：本报告用到的临时脚本

| 脚本 | 作用 |
|---|---|
| `deflate_shape_20261125.py` | 逐 400 ms 块速率 + 逐样本 dp，看清"锯齿"形状 |
| `deflate_valve_cmd_20261125.py` | 读 `type=valve` / `type=step` / `type=pulse` 的分布 |
| `deflate_ticks_20261125.py` | 证明 `pulse.open` 与 `point.t` 同一 tick 域 |
| `deflate_duty_20261125.py` → `deflate_duty2_20261125.py` | 按压力带统计 commanded open ms（第一版 band 上下界写反，全 0） |
| `deflate_transfer_20261125.py` | open ms → 每周期净压降的传递曲线 |
| `deflate_timeline_20261125.py` | 逐脉冲时间线（t=0 为首导出样本） |
| `deflate_gain_20261125.py` / `_series` / `_corpus` | gain 的中位/峰值/比值，以及全库比值分布 |
| `deflate_duty_corpus_20261125.py` | 全库 637 份的 `duty_max`/`duty_med` 与段斜率 |
| `deflate_band245_20261125.py` / `deflate_bandstats_20261125.py` | 245–255 带的分桶与健康/陡轮对照 |
| `deflate_medcontig_20261125.py` / `deflate_contig_20261125.py` | duty 分桶的列联表 |
| `deflate_preburst_20261125.py` | 爆发前 3 s 的 gain 中位 |
| `deflate_windup_20261125.py` | 11-07 / 11-25 逐轮顺序 + 按压力带的 gain 中位 |
| `deflate_steep_20261125.py` | 五轮的时间线汇总表（§5.1） |
| `deflate_profile_meta_20261125.py` | 确认五轮的 deflation profile 都是 peak / 1.8 mmHg/s |
| `deflate_gatekeys_20261125.py` | 确认 `-135554` 的元数据里没有门键 |
| `gate_corpus_20261125.py` | 645 份逐份跑 `tools\validity_v2.py` |
| `gate_rejects_detail2_20261125.py` | 把 11 份 REJECT 关联回 manifest（第一版用 `file` 键查不到，manifest 是 `run_id`） |
| `published_gate_20261125.py` | 已发布 62 轮的 gate 列 |
| `v2_score_report_20261125.py` / `unresolved_20261125.py` / `v1_report_20261125.py` | 三份冻结记录对同样四轮的不同处置 |
| `pub_gate_rej_20261125.py` / `pub_tier_counts_20261125.py` / `pub_state_20261125.py` / `analysis_state_20261125.py` | 已发布层的构成与 `analysis_state` |
