# Preset 2 的两轮面板未确立数据：重采与标签处置（2026-11-15）

> 承接 `data/reports/precision_levers_20261115.md` §3.1。本文件只记录这一次处置，
> 因为它是**语料元数据发生了变化**，而不只是一次分析。

## 0. 一句话结论

`20261114-120952` 与 `-121253` 这两轮的**面板标签本身没有证据**（不是答案与标签不符），
所以它们从 Preset 2 的统计里退出；同时按正常流程重采了 2 轮 P2 补上。
处置后 Preset 2 的三项从 `+3.06/13.92`、`+1.32/13.44`、`+5.60/15.86`（全 FAIL）变成
`−0.29/4.39`、`−1.46/6.29`、`+1.37/3.95`（全 PASS），**七档全过 4/7 → 5/7**。

## 1. 为什么这两轮不能算作 Preset 2 的读数

三件事叠在一起：

1. 它们是 2026-11-14 那批补采里的**裸调用**——`python tmp/run_v4_batch.py 2 2 v5_p2b`。
   那个脚本**不发 `[SIM_STD*]`**（它只负责跑采集，不负责设定模拟器）。
2. 在它之前的编排脚本已经发过 `[SIM_STD200_150]`，把 Tester 切到 **Preset 3**。
3. 手册**没有读回当前预设的命令**，所以即使当时补发一次，也只能拿到一个 ACK，
   而 ACK 只说明命令被接受，不说明面板此刻显示什么。

形状证据指向同一个方向（`tmp/preset_shape_match_20261114.py`，归一化脉搏带剖面，
同档命中 262/268 = 97.8%）：这两轮到各档剖面均值的距离是 **Preset 3 = 0.108 / 0.114**，
而当日一个确证的 Preset 3 轮是 0.095、一个确证的 Preset 2 轮是 0.068。
它们最像 P3，不像 P2。

## 2. 这与 v5 协议 §4 第 7 条不冲突

§4 禁止的是"**因为答案与面板标签不符**就剔除"——那是拿结果反推数据。
这里的顺序相反：**标签先失去证据**，于是这一轮根本无法被当作 P2 的一个读数参与计算。
估计器的答案（`+48/+42/+62` 与 `+58/+51/+67` mmHg）不是理由，只是同一件事的另一个后果。

导出文件**全部保留**在 `data/raw/development_20261101/` 下，随时可读；
元数据里写明 `panel_state_established: false`、`exclusion_category:
panel_state_not_established`、`superseded_by`，并保留 `analysis` 与 `analysis_v5` 的原始结果。

## 3. 重采

| 项 | 值 |
|---|---|
| 命令 | `python tmp/run_topup_20261115.py --plan 2:2 --tag-prefix rec_p --tag-suffix a --port COM12` |
| 切档 | `[SIM_STD150_100] ACK (11.7 s)`（11.7 s 是这台 Tester 的实测回包延迟，不是超时） |
| 结果 | `2 captures kept from 2 attempt(s); 0 rejected by the v2 gate`（6.9 min） |
| 新轮次 | `standard150_100_target275_peakwindow_20261115-162713`、`-163039` |
| 固件 | `61ca1da309439d9a…` / 184146 B（与已发布语料同一代） |
| 峰窗斜率 | 两轮都是 −1.85 mmHg/s（健康范围内） |
| 工作点 | flow 0.1019 / 0.1047 mmHg per open-ms，脉宽中位慢档 → `slow` |
| 估计（v5） | MAP 116.39 / 114.76、SBP 151.37 / 152.60、DBP 95.85 / 97.28 |

两轮的 `map_note_gap` 是 +2.03 与 −0.96 mmHg，`pulse_pressure` 54.36 / 54.16 —— 
都不是擦边，两道门限都过得很松。

## 4. 处置后的分数

`python tools/covered_bp.py --score --exclude-panel-unknown`
（308 发布轮；`--exclude-panel-unknown` 是**新增的可选视角**，默认 `--score` 行为不变）：

| | 处置前（含 2 轮） | 处置后 |
|---|---|---|
| P2 MAP | +3.06/**13.92** FAIL | **−0.29/4.39 PASS** |
| P2 SBP | +1.32/**13.44** FAIL | **−1.46/6.29 PASS** |
| P2 DBP | **+5.60**/**15.86** FAIL | **+1.37/3.95 PASS** |
| 池化 MAP | −0.73/6.02 | −1.08/4.13 |
| 池化 SBP | +1.35/7.27 | +1.06/6.27 |
| 池化 DBP | +1.70/6.44 | +1.26/3.98 |
| 七档全过 | 4/7 `['1','3','4','6']` | **5/7 `['1','2','3','4','6']`** |

同一代固件、过 AAMI 判据的轮数 297（`tools/standard_conformance.py` 再剔掉 11 轮
异代固件后）：MAP −1.07/4.13 BHS A、SBP +0.99/6.24 BHS B、DBP +1.37/3.88 BHS A，
逐档只有 P5 与 P7 的 SBP 均值仍不过（+5.15/5.09、+5.05/6.46）。

## 5. 为什么默认口径不改

v5 前瞻批次的裁决（`data/reports/v5_validation_20261114.md`，`v5 FAILS: C1/C2/C4/C5`）
是在**含这两轮**的情况下公布并提交的。如果现在把默认打分改成自动排除它们，
那个已发表的结果会悄悄变化——这是数据论文最不能做的事。
所以改动落在两处彼此独立的地方：元数据标记（描述数据本身）+ 可选的
`--exclude-panel-unknown` 视角（新口径要显式请求）。

## 6. 能写 / 不能写

**能写**
- Preset 2 的三项 sd（13.4–15.9）不是算法极限：退掉两轮面板未确立的轮、补采两轮后
  三项全过（`−0.29/4.39`、`−1.46/6.29`、`+1.37/3.95`，n=32）。
- 七档全过 5/7；剩下的两格是 P5/P7 的 SBP 均值。

**不能写**
- 不能写"P2 是靠剔数据过掉的"——是靠**重采新数据** + 标签处置。
- 不能写"两轮是坏数据所以删了"——导出完好、保留、可读，只是标签无证据。
- 不能写"这修好了精度"——它只消掉一个采集缺陷，P5/P7 的 SBP 偏置一点没动。
- 不能写"面板被证明切到了 Preset 2"——只有 ACK 与形状证据，手册没有读回命令。

## 7. 复现

```
python tools/covered_bp.py --score --exclude-panel-unknown \
    --json tmp/omniprobe/covered_with_p2_recollect.json
python tools/standard_conformance.py --source tmp/omniprobe/covered_with_p2_recollect.json \
    --out data/reports/standard_conformance_20261115.json
python tools/corpus_register.py --out data/manifest.csv --json data/manifest.json
```

处置脚本（`tmp/`，gitignore）：`tmp/mark_panel_unknown_20261115.py`
（`--dry-run` 可用；它会先确认两轮替代数据存在，才允许退休这两轮）。
