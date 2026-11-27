# 采集前零点从 −3.92 漂到 +1.35 mmHg：是什么、影响多大、要不要改门限

日期：2026-11-12。触发原因：Preset 1 的 v4 批次在采到 26/44 后，连续 29 次报
`RuntimeError('unloaded zero baseline failed')`，被迫中断。

## 0 一句话

封阀后的零点今天上午是 **−3.92 mmHg**、下午变成 **+1.35 mmHg**，同一个封阀窗口在 120 s 内
只掉 **0.09 mmHg**；这不是残气（残气会按漏气率掉），是**传感器链路的零点漂移**。而这个漂移
对 MAP/SBP/DBP 的误差**几乎没有影响**（sd 变化 ≤0.07 mmHg），却刚好越过采集脚本写死的
`est > 1.2` 门限把采集挡住了。**门限该改，压力轴声明该补一句不确定度。**

## 1 实测：现在是偏移，不是残气

`tmp/zero_hold_20261112.py 120`（封阀一次，盯 120 s，每 10 s 一块）：

| 时刻 | raw 中位 | raw 峰峰 | sensor mV | est | 由 sensor 反算的真压 |
|---|---|---|---|---|---|
| sealed+10 s | 1500 | 10 | 259 | 1.40 | +1.44 |
| sealed+60 s | 1498 | 10 | 258 | 1.40 | +1.35 |
| sealed+120 s | 1497 | 10 | 258 | 1.40 | +1.35 |

封阀零点 120 s 掉 **0.09 mmHg = −0.04 mmHg/min**。

对照：这个回路在 150–240 mmHg 下的实测漏气率是 **6–12 mmHg/min**（`data/reports/leak_*`）。
如果线里真封着 +1.4 mmHg 的气，体积流量按压力正比缩小，在 1.4 mmHg 下约 **0.05–0.11 mmHg/min**
—— 和实测的 0.04 是同一量级。**所以这个 120 s 实验分不开残气和偏移。**

能分开的是通大气那一路：`vent` 态让阀通向大气，**真实表压必然是 0**，所以 vent 态的读数就是
全部偏移量。同时测四态（`tmp/zero_sanity_20261112.py 6`）：

| 状态 | raw 中位 | sensor mV | est | 真压 |
|---|---|---|---|---|
| vent_1 | 1677 | 289.0 | 3.9 | **+3.91**（大气，真值 0 → 全部是偏移） |
| seal_1 | 1499 | 259.0 | 1.4 | +1.44 |
| vent_2 | 1673 | 289.0 | 3.9 | **+3.91** |
| seal_2 | 1496 | 258.0 | 1.4 | +1.35 |

两条结论：
- **ADC 分压链完全自洽**：`sensor_mv_from_raw`（raw×0.125×1.3799）与固件上报的
  `sensor_mv` 逐态一致（289.3/289、258.6/259、288.6/288、258.0/258）→ 不是换算或 I2C 的问题。
- **偏移是真的**：大气对应 0，读数却是 +3.91；其中封阀后降到 +1.35，说明 vent 时放气阀的
  线圈把读数抬高了 **+2.56 mmHg**（`coil offset (vent−sealed) +2.56`）。

## 2 今天的漂移轨迹（61 份 Preset 1 元数据，按采集顺序）

`pre_capture_zero_true_mmhg`（封阀态、由 sensor mV 反算）：

```
-1.775 → -0.52 → -0.272 → -0.367 → -0.94 → -0.974 → -0.951 → -0.951
→ -0.883 → -0.818 → -0.849 → -0.734 → -0.711 → -0.646 → -0.62 → -0.593
→ -0.457 → -0.553 → -0.458 → -0.704 → -0.289 → -0.173
→ +0.36 → +0.418 → +0.428 → +0.459 → -0.872（一次充放气后回落）→ +0.494
→ 之后 25 份 None（预检没过基线采样）
```

上午 10:34 的独立测量是 **−3.92**（sensor 194 mV），比上面任何一轮都低。也就是说
从上午到下午，零点单方向走了 **5.3 mmHg**。`raw` 峰峰全程只有 4–10 counts（0.06–0.14 mmHg），
链路很稳，**不是接触不良那种跳变**，是缓变（自热或长期漂移）。

历史对照：`static_crosscheck_*` 里每次充气后的 `zero_end` 都是正的（+1.6、+2.67、+3.74、
+3.99、+4.23），`zero_start` 都在 −0.8 附近 → **每次充放气都会把零点推正**，之后慢慢回落。
今天下午的 +1.35 最可能是连续 26 轮充放气累积的热漂移。

## 3 这个偏移影响 MAP/SBP/DBP 吗？几乎不影响

`tmp/zero_bias_20261112.py --preset 1 --date 20261112`：对今天 27 份有零点的导出，做两次
`reference_bp.estimate` —— 一次按原样，一次把整条 `pressure` 减去该轮记录到的零点：

| 量 | n | 原样的 sd | 扣零点后的 sd | 位移中位 | 位移 sd | 位移范围 |
|---|---|---|---|---|---|---|
| MAP | 26 | 3.74 | **3.81** | +0.64 | 0.51 | −0.46 … +1.78 |
| SBP | 26 | 7.80 | **7.74** | +0.63 | 0.51 | −0.46 … +1.78 |
| DBP | 26 | 3.91 | **3.84** | +0.64 | 0.51 | −0.46 … +1.78 |

**扣掉零点后 sd 变化 ≤0.07 mmHg**（MAP 3.74→3.81、SBP 7.80→7.74、DBP 3.91→3.84），
而位移只有 +0.64 mmHg。零点在这一批里跨了 2.23 mmHg（−1.77 … +0.46），
**换来的误差变化不到 0.1 mmHg** —— 因为估算器看的是包络峰在压力轴上的**位置**，
整条压力轴平移 1 mmHg 对峰位置几乎不动。

**所以：零点偏移是设备健康指标，不是精度项。** 门限把它当精度项挡住，是错误的。

## 4 但它给压力轴声明带来一个新的不确定度

`static_crosscheck_*` 的 19 个点（`settle ≥ 8 s`）用三种零点处理重新拟合斜率：

| 零点处理 | 斜率 | 截距 | 残差最大 | 平均差值 | 差值范围 |
|---|---|---|---|---|---|
| 不修正 | **−1.042 pp/100** | −0.24 | 1.01 | −2.24 | −3.88 … −0.80 |
| 减去 (zero_start + zero_end)/2 | **−0.988 pp/100** | +0.53 | 2.09 | −1.36 | −4.05 … +0.18 |
| 减去 zero_end | **−0.768 pp/100** | +1.82 | 3.40 | +0.36 | −3.51 … +2.39 |

已发布的声明是 **−0.97 ± 0.13 pp/100**，与"减中点零点"的 −0.988 几乎一致，
但"减 end 零点"给出 −0.768。**真值落在 −0.77 … −1.04 之间**。

为什么零点处理能改斜率：一次扫描里高点是**后测**的（先 60 再 260），而零点在这段时间里
从 −0.8 漂到 +4，于是高压点被多扣了更多零点 → 漂移伪装成负斜率。

**要补的声明**：压力轴的刻度差 −0.97 ± 0.13 pp/100 未做零点漂移修正；若按扫描首尾零点
的中点修正为 −0.99，按尾零点修正为 −0.77。最好也补一句：本设备连续充放气会累积正零点漂移，
单次会话内可达 +4 mmHg。

## 5 采集门限已按此改掉（2026-11-12 当天生效）

改之前的判据（`tmp/bp_standard255_195_target275_peakwindow_20261105.py` 预检）：

```python
if len(base) < 80 or any(p['valid'] != 'VALID' or p['est'] > 1.2 or p['raw'] < 1000
                         for p in base) or max(...) - min(...) > 20:
    raise RuntimeError('unloaded zero baseline failed')
```

三个问题：
1. **只查正方向**。固件 `ads1115.c:215-218` 把负压钳到 0，所以早上的 −3.92 读成 0.00 一路放行，
   下午的 +1.35 读成 1.35 被拒 —— 同一个漂移，两个方向待遇不同。
2. **用 `est`（被钳过的值）判断**，丢掉了真实零点信息。
3. **1.2 mmHg 比漂移本身还小**（今天跨了 5.3），门限在噪声里。

改成的判据：

- 新增 `true_zero_mmhg(sample) = sample['sensor']/1000 × 82.326 − 19.887`（不带钳位）；
- 新增 `PRE_CAPTURE_ZERO_GATE_MMHG = 5.0` 与 `zero_gate(base, ceiling)`，返回 `(ok, reason)`；
  保留 `len ≥ 80`、全 VALID、`raw ≥ 1000`、`raw 峰峰 ≤ 20`，最后要求
  `|mean(true_zero)| ≤ 5.0`；
- 收尾 `closeout_sealed_zero(..., sealed_ceiling=PRE_CAPTURE_ZERO_GATE_MMHG)` 同样改用
  `abs(mean(true_zero))` 而不是被钳的 `est`；
- 元数据写入 `pre_capture_zero_gate_mmhg`、`pre_capture_zero_gate`、
  `closeout_zero_gate_mmhg`、`closeout_true_zero_mmhg`，任何一轮都能事后按自己的零点重算。

**同批修掉的一个真 bug**：profile 分支原先用 `current[0]` 判断当前是否已是 `mode=peak`，
而 `profile` 的回显里 `[Pressure]` 行可能排在第一 → 明明已是 peak 却连试 4 次重置，
每次都卡在 `sealed zero above +0.9` 超时。改为对返回的每一行做
`any('mode=peak' in line ...)`，`profile normal` 的恢复分支同样处理。

验证：修复后 `standard120_080_target275_peakwindow_20261112-140853` 之前的失败轮是
`profile peak could not be set`（门限已放行，是 profile 分支在挡），修掉 profile 后
`...-141400` 一次成功：`n=3609`、`dropped=0`、`closeout_confirmed true`、
`target_restored 50`、`gate USABLE peak_slope −1.78 mmHg/s`、
v2 打分 `MAP 99.38 / SBP 119.92 / DBP 75.5`（面板 120/80/93）。
此后连续三轮（`141948`/`142312`/`142638`）全部 `export_received` + `USABLE`，
`pre_capture_zero_true_mmhg` 依次 1.188 / 1.253 / 0.934，`pre_capture_zero_gate_mmhg` 均为 5.0。

**这属于采集有效性判据，不是估算器常量**，三份冻结记录（v1/v2/v3 的 11 个常量与 sha256）
都不受影响，`tools/verify_freeze.py` 仍报三份完好。协议侧修订记录写在
`data/protocols/reference_bp_freeze_v4_candidate.md` §6。

## 6 复现

```powershell
python tmp\zero_sanity_20261112.py 6          # 四态：vent/seal 交替，看偏移与线圈偏移
python tmp\zero_hold_20261112.py 120          # 封阀 120 s，看零点是否在掉
python tmp\zero_bias_20261112.py --preset 1 --date 20261112 `
    --json tmp\omniprobe\zero_bias_20261112.json   # 零点对 MAP/SBP/DBP 的影响
```

前两个把 JSON 落在 `tmp/omniprobe/zero_sanity_20261112.json` 与
`tmp/omniprobe/zero_hold_20261112.json`；第三个落 `tmp/omniprobe/zero_bias_20261112.json`。
