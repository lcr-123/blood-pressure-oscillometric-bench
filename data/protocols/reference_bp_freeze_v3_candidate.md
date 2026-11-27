# 冻结候选 v3：MAP 定位的滚动中位窗 2 s → 3 s

状态：**已于 2026-11-11 冻结**（记录见 `data/protocols/reference_bp_freeze_v3.json`，
实现见 `tools/reference_bp_v3.py`）。本文保留为**事前登记原文**，其中四条验收标准
一字未改，`tools/verify_freeze.py` 会同时校验 v1/v2/v3 三份记录。

冻结方式必须说明：**没有改 `tools/reference_bp.py`**。那份文件的 sha256 被 v1、v2
两份记录钉住，改了就等于宣布既往前瞻评分作废。v3 是一个薄包装模块，`import`
v2 的 `estimate` 并只覆盖 `map_smoothing_s` 的默认值，两个版本因此在结构上不可能
出现除此之外的任何差异。

日期：2026-11-11

## 一、候选改动（只有一处）

`tools/reference_bp.py` 的 `DEFAULT_MAP_SMOOTHING_S` 从 `2.0` 改为 `3.0`。

其余 10 个常量、算法结构、拒判规则全部不动：

| 常量 | 现值（v2） | 候选（v3） |
|---|---|---|
| `DEFAULT_SBP_RATIO` | 0.50 | 不变 |
| `DEFAULT_DBP_RATIO` | 0.60 | 不变 |
| `DEFAULT_SKIP_START_S` | 2.0 | 不变 |
| **`DEFAULT_MAP_SMOOTHING_S`** | **2.0** | **3.0** |
| `RATIO_SWEEP` | 0.40…0.70 | 不变 |
| `PLATEAU_FRACTION` | 0.90 | 不变 |
| `PLATEAU_REFUSE_RATIO` | 0.25 | 不变 |
| `MIN_ENVELOPE_V` | 1e-4 | 不变 |
| `TRANSIENT_FACTOR` | 2.0 | 不变 |
| `SBP_SUSTAINED_SAMPLES` | 3 | 不变 |
| `DBP_SUSTAINED_SAMPLES` | 3 | 不变 |

## 二、为什么是这个改动

唯一理由不是"数字更好看"，而是**它拦住了一次已知的灾难性失败**。

`standard150_100_..._20261107-202606`（预设 2）峰区放气速率 −15.49 mmHg/s
（健康轮 1.56–1.91），是放气阀不节流；58 秒的放气压缩成 2 秒，整段包络被抬高，
v1 的瞬态判据（邻域中值 19.93 mV、比值 1.90 < 2.0）因此漏检。
在 v2 的 2 s 中位窗下它被判 `ok`，MAP 给 **202.9 mmHg**（面板 116，**+86.9**）。
把窗加宽到 3 s 后，该轮被 `unresolved_map` 正确拒绝。

## 三、代价（已在 62 轮上量过，全部公开）

| 指标 | 2.0 s（v2） | 3.0 s（候选） |
|---|---|---|
| MAP 发布 | 49/62 | 48/62 |
| MAP 中位 \|误差\| | 3.43 | **4.23**（变差） |
| MAP sd | 12.65 | **4.62**（变好） |
| MAP 最差 \|误差\| | **86.9** | **16.3** |
| \|误差\| > 10 的轮数 | 5 | **7**（变差） |
| SBP 发布 | 46/62 | **43/62**（变差） |

> 勘误（同日）：本节初版写"SBP 发布 46 → 50"，是抄错了上一版临时脚本的输出。
> 用 `reference_bp.estimate(..., map_smoothing_s=3.0)` 重跑全库确认为 **43/62**。
> 加宽中位窗会把窄峰削平，被平台判据拒绝的轮次因此**更多**，不是更少。

在 47 个两种设置都发布的轮次上：位移中位 **+1.14 mmHg**，
按预设 P1 +2.57 / P2 +1.00 / P3 +1.11 / P4 +0.98，
**17 轮变差 >3 mmHg、只有 2 轮变好**。

**这是一个明确的两面改动：sd 大幅改善、最差情况大幅改善，但中位误差与轮次数变差。**
任何一种"全面更好"的表述都是错的。

## 四、事前登记的验收标准

冻结 v3 之后必须**新采**一批轮次（不得复用现有 62 轮任何一轮），
每预设 10 轮、共 40 轮，采集时两个版本都对同一批数据打分，
按下面四条判定。**任一条不满足则弃用候选，保留 v2。**

1. **MAP 发布数不低于 v2 的 90%**（即 ≥ 36/40，若 v2 在该批发布 N 轮则 ≥ 0.9N）。
2. **MAP sd 严格低于 v2**，且差值大于 1.0 mmHg（避免落在噪声里）。
3. **MAP 中位 \|误差\| 不高于 v2 + 1.0 mmHg。**
4. **|误差| > 20 mmHg 的轮次数不高于 v2。**

判分脚本必须**只调用 `tools/reference_bp.py` 的公开接口**，
并把两次运行的完整 JSON 一并入库（`data/reports/reference_bp_v3_validation.json`）。

## 五、明确禁止的做法

- 不得用现有 62 轮的成绩宣称 v3 更好（那是选参集，不是验证集）。
- 不得在看到新批次结果后调整上面四条标准里的任何一个数字。
- 不得因为 v3 在这一批上更好就顺手调 `DEFAULT_SKIP_START_S`（8 s 那版已量过：
  pooled sd 反而从 12.65 升到 13.81，且放出了 +86.9 那轮）。
- 不得把 v3 与"包络去尖"组合后只报告较好的一半（去尖版新放出的 5 轮里
  `20261107-212915` 错 **+60.3**，已放弃）。

## 六、如果候选失败，数据集照样成立

v2 的数字（MAP 按预设 sd 3.65 / 22.01 / 6.95 / 3.58）本身就是诚实的负结果：
它记录下来的是"这台架在高压档的 0.5 倍穿越点不存在"这一物理事实，
不是算法缺陷。v3 是否成立不改变数据集的可用性。

## 七、复现（两个版本并列打分）

```powershell
# v2（现冻结）
python tools\reference_bp.py data\raw\development_20261101\standard150_100_target275_peakwindow_20261107-202606.export.ndjson

# v3（现冻结，包装模块，只改一个默认值）
python tools\reference_bp_v3.py data\raw\development_20261101\standard150_100_target275_peakwindow_20261107-202606.export.ndjson

# 按预设分档对照（本文三节的表）
python tools\preset_breakdown.py

# 四条验收标准（只接受冻结后新采的轮次，否则判 INVALID）
python tools\v3_acceptance.py --batch data\raw\prospective_v3 --panel-map <run_id到面板MAP的JSON> --json data\reports\reference_bp_v3_validation.json
```

`tools/v3_acceptance.py` 默认拒绝在现有 62 轮上运行；传 `--include-existing` 只为
复现选参语料，那次运行会被标为 **INVALID**，不能拿去当验收结果。
判分脚本里踩过两个坑，都写在 `tools/v3_acceptance.py` 的注释里：①汇总时读
`<key>_mmhg` 而行的键是 `<key>_v2`/`<key>_v3`，会把健康批次报成"0 轮发布"；
②把非空 `map_mmhg` 当"已发布"，而 `reference_bp.estimate` 在
`unresolved_map` 时仍然填了这个字段。
