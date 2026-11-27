# 统计口径清理：把 4 轮阀故障从"全库"里拿出来算（2026-11-11）

> 一句话：**此前所有"62 轮全库"的合并统计里混着 4 轮放气阀不节流的失败记录，
> 它们把 MAP 的合并 sd 从 4.73 抬到 12.78，是"三项全不通过 AAMI"这个结论的主因。
> 从本文起，默认口径是"守门通过的 58 轮"，并且逐参数、逐预设报告。**

## 1. 为什么要改

`data/README.md` 与 `data/reports/dataset_scope_statement.md` 一直写着
"62 轮全库，MAP +5.36 / sd 12.78、SBP +1.37 / 15.94、DBP +3.97 / 10.09，
三项全部不满足 AAMI 的 |mean| ≤ 5 且 sd ≤ 8"。

这个数字**在算术上是对的，在解释上是错的**：

| 问题 | 说明 |
|---|---|
| 混入了失败记录 | 62 轮里有 4 轮峰区放气速率 −13.35 … −32.87 mmHg/s（正常 1.56–2.63），是放气阀不节流，压力轨迹本身不成立 |
| 合并掩盖了预设差异 | 预设 1 与预设 4 的 MAP sd 都在 4 以内，预设 2 的旧 sd 22.01 由**单轮**造成 |
| "不通过"被当成整体结论 | 实际是"MAP 过、SBP 差 1.2、DBP 差 1.2"，且预设 1 三项全过 |

守门工具 `tools/validity_v2.py` 从 2026-11-07 起就存在，且**只看压力轨迹、
不看估算器输出**，但此前只是在采集时用来判"这一轮能不能进语料"，
没有在**统计时**再剔一遍——于是那 4 轮在早期批次里已经进来了。

## 2. 那 4 轮是什么

| run id | 峰区速率 | 拦截者 |
|---|---|---|
| `standard120_080_target275_peakwindow_20261107-154020` | −13.35 mmHg/s | v1 瞬态判据 |
| `standard150_100_target275_peakwindow_20261107-202606` | −15.49 | v1 **漏检**（整段包络被抬高，邻域中值涨到 19.93 mV） |
| `standard200_150_target275_peakwindow_20261107-212915` | −32.87 | v2 采集守门 |
| `standard255_195_target275_peakwindow_20261107-215245` | −16.81 | v2 采集守门 |

四轮合计 4/40 = **10%**，全部落在 200–245 mmHg 区间。这是硬件缺陷
（`dataset_limitations.md` 第 4 条），不是算法问题。

## 3. 改后的数字

冻结估算器 v2，已发布语料 62 轮 → **守门通过 58 轮**：

### 3a. 合并口径

| 口径 | MAP | SBP | DBP |
|---|---|---|---|
| 含 4 轮阀故障（旧） | +5.36 / **12.78**（n=49） | +1.37 / **15.94**（n=46） | +3.97 / **10.09**（n=49） |
| 剔除后（新） | +3.66 / **4.73**（n=48） | −0.56 / **9.20**（n=45） | +3.29 / **9.20**（n=48） |

> 上表的 MAP/DBP 用 `status != 'unresolved_map'`，SBP 用 `status == 'ok'`。
> 若三量一律用 `status == 'ok'`（n=45），MAP 是 **+3.87 / 4.68**。

**MAP 跨越了 AAMI 的 8 mmHg 门槛（12.78 → 4.73）。SBP 与 DBP 各自只降到 9.20，
仍超 1.20。** 所以既不能再说"三项全不过"，也不能说"三项全过"。

### 3b. 逐预设（正确读法）

| 参数 | 预设 1 (120/80) | 预设 2 (150/100) | 预设 3 (200/150) | 预设 4 (255/195) |
|---|---|---|---|---|
| MAP mean / sd | **+2.86 / 3.78 PASS** | +5.38 / 3.81 均值超 0.38 | +5.12 / 7.37 均值超 0.12 | **+1.84 / 3.74 PASS** |
| SBP mean / sd | **+3.87 / 7.36 PASS** | −1.10 / 10.67 sd 超 2.67 | **−2.84 / 7.38 PASS** | −4.94 / 9.74 sd 超 1.74 |
| DBP mean / sd | **+0.63 / 4.59 PASS** | +3.11 / 10.41 sd 超 2.41 | +4.72 / 13.27 sd 超 5.27 | +5.71 / 8.96 sd 超 0.96 |

**只有预设 1 三项同时通过。** 预设 2 与 3 的 SBP 反而通过了，失败的换成了 DBP；
预设 4 的 MAP 很准但 SBP 最差（已知的台架包络形状问题，见
`envelope_peak_instability_20261111.md`）。

## 4. 工具改动

`tools/preset_breakdown.py`：

1. `collect()` 每轮调用 `validity_v2.check(path)`，记录 `gate_usable` 与
   `peak_window_slope_mmhg_s`。守门只读压力轨迹，因此这一步**在评分之前**做，
   不存在"用估算结果反推该不该剔"的循环。
2. `print_breakdown()` 默认只统计守门通过的轮次，末尾逐条打印被剔除的 run id 与速率；
   新增 `--include-gate-failures` 复现旧口径。
3. 每张表新增 **mean** 与 **AAMI** 两列（`|mean| ≤ 5` 且 `sd ≤ 8`，逐参数判），
   `_summary()` 里存 `mean_error` / `aami_mean_ok` / `aami_sd_ok` / `aami_pass`。
4. 新增合并行，直接把三项的 mean/sd/AAMI 判定打在一行里，不用再手工汇总。
5. JSON 载荷新增 `aami_limits` 与 `gate_filter` / `gate_excluded`。

验证：`--include-gate-failures` 能逐字复现旧数字（MAP +5.36/12.78 n=49、
SBP +1.37/15.94 n=46、DBP +3.85/9.92 n=49 —— 与旧 README 的 +3.97/10.09 差
0.12/0.17，因为旧表用的是总体标准差 9.82；样本口径一直是 9.92）。

## 5. 被这件事推翻的一个旧结论

`dataset_scope_statement.md` 第四节曾把"median 窗 2 → 3 s 使 pooled sd
12.65 → 4.62"列为候选改动的收益。现在看得很清楚：**它"抓住"的正是阀故障轮
`202606`（MAP +86.9），那轮本来就不该进统计**，所以这个收益是假的。

`reference_bp_v3_validation.md` 用 40 轮新数据独立否定了这项改动
（sd 6.084 → 6.237）。两件事的结论一致：**在含设备故障的语料上"改善"，
是在用算法兜硬件问题。**

## 6. 复现

```bash
# 新口径（默认剔除 4 轮阀故障，含 AAMI 判定）
python tools/preset_breakdown.py --published --map-policy not-unresolved \
    --glob "data/raw/**/standard*_peakwindow_*.export.ndjson"

# 三量一律 status == ok
python tools/preset_breakdown.py --published --map-policy ok \
    --glob "data/raw/**/standard*_peakwindow_*.export.ndjson"

# 旧口径（含 4 轮阀故障，复现已发表旧数字）
python tools/preset_breakdown.py --published --map-policy not-unresolved \
    --include-gate-failures --glob "data/raw/**/standard*_peakwindow_*.export.ndjson"

# 40 轮全新采集（v3 验收批次）同样跑一遍
python tools/preset_breakdown.py --tier v3_acceptance --map-policy not-unresolved \
    --glob "data/raw/**/standard*_peakwindow_*.export.ndjson"

# 分批次
python tools/preset_breakdown.py --tier frozen_baseline_v2
python tools/preset_breakdown.py --tier prospective_v1
python tools/preset_breakdown.py --tier prospective_v2
```

分批次（守门口径，`status == ok`）：

| 批次 | 采集 | 守门剔除 | 计分 | MAP | SBP | DBP |
|---|---|---|---|---|---|---|
| 冻结基线 | 18 | 0 | 16 | −2.2 … +10.8（sd 3.8） | −20.3 … +18.2（sd 10.0） | −12.3 … +23.2（sd 9.9） |
| 前瞻 v1 | 20 | 2 | 17 | −1.2 … +13.2（sd 4.1） | −14.1 … +11.5（sd 9.1） | −5.4 … +21.4（sd **7.6**） |
| 前瞻 v2 | 20 | 2 | 8 | −5.3 … +16.4（sd 7.3） | −5.8 … +5.6（sd **4.0**） | −12.8 … +25.1（sd 11.7） |
| v3 验收 | 40 | 0 | 37 | −18.4 … +13.3（sd 6.1） | −53.9 … +10.0（sd 10.8） | −14.7 … +23.3（sd 8.7） |

## 7. 现在可以写、不可以写

**可以写**

- "在 58 轮守门通过的非人体台架数据上，示波比例法参考实现给出
  MAP 误差 +3.66 / sd 4.73，满足 AAMI 的 |mean| ≤ 5 且 sd ≤ 8。"
- "预设 1（120/80）的 MAP、SBP、DBP 三项同时满足 AAMI。"
- "SBP 与 DBP 的合并 sd 均为 9.20，超出门槛 1.20 mmHg。"
- "4/40 轮因放气阀不节流被有效性守门剔除；不剔除时 MAP 的合并 sd 会从 4.73 升到 12.78。"

**不可以写**

- "本数据集三项全部不满足 AAMI"（旧错，主因是 4 轮阀故障）。
- "本数据集三项全部满足 AAMI"（SBP/DBP 仍差 1.2）。
- "达到 X mmHg 精度"（`dataset_limitations.md` 的原则不变）。
- 任何把 4 轮阀故障留在合并统计里的数字，而不注明是否剔除。

## 8. 这份口径还没回答的问题（2026-11-12 补）

本文件只定义了**哪些轮进统计**。它没有定义**一次测量是什么单位**——
而后者才是 SBP sd 9.20 的主因：同一轮数据的搏动分成两半各求一次 SBP，
两半之差 sd 达 32.26（逐搏法）/ 19.08（固件平滑包络法），
对单轮自身搏动重采样得到的轮内抽样 sd 中位 21.3，与轮间 sd 同量级。

因此：**在 §7 允许的每一条声明之后，还必须说明测量的重复单位。**
把同一面板设定下连续 k 次采集取中位当作"一次测量"，k=4 时
SBP sd 9.75 → 4.99、DBP 8.96 → 5.02、MAP → 3.40，三者 95% 上界均 < 8
（用互不重叠的整块重算，非重采样；理论值 1.2533·σ/√4 = 6.11，同向同量级）。

这一节的两个限制必须一起写：

1. k=4 **是同一批数据上的重聚合，不是前瞻验证** → 只能作为 v4 候选，须用新采集验收。
2. 样本量是硬约束：真 sd 9.2 时无论多少轮，95% 上界都过不了 8（n=200 仍 10.03），
   **只加轮次不改口径是无效劳动**。

详见 `data/reports/measurement_precision_20261112.md` 与
`data/reports/dataset_limitations.md` 第 15 条。
