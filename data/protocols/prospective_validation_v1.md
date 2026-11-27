# 前瞻性验证采集规程 v1

本规程用于在参考实现冻结之后采集 `prospective_validation` 轮次。**采集前读完全文**，
采集一旦开始，下列任何一项都不得改动。

## 为什么需要这一组

当前 18 轮全部是 `development`：它们参与过参数选择（0.5/0.6 比例、2 s 起始跳过、
2 s 中值滤波、平台拒判阈值）。任何方法在这批数据上的表现都**不能作为泛化证据**。

`data/capture_protocol_v1.md:11` 要求 `dataset_role` 在采集前确定，事后不得改标。
本规程就是执行这一条。

## 冻结物

冻结记录：`data/protocols/reference_bp_freeze_v1.json`

| 冻结对象 | 值 |
|---|---|
| `tools/reference_bp.py` sha256 | `ddc9daf72a55ed5d32d9b8c832e61e76fc04011a8e462aa9be74a877a2ba8868` |
| 基线报告 sha256 | `a50a905b1476ccce14dabff1211f6e2af2b3f1add726f490e36ab8f7492743f2` |
| 基线轮次 | 18（其中 16 轮 `status = ok`） |

冻结常量：

```
DEFAULT_SBP_RATIO      = 0.50
DEFAULT_DBP_RATIO      = 0.60
DEFAULT_SKIP_START_S   = 2.0
DEFAULT_MAP_SMOOTHING_S= 2.0
PLATEAU_FRACTION       = 0.90
PLATEAU_REFUSE_RATIO   = 0.25
TRANSIENT_FACTOR       = 2.0
SBP_SUSTAINED_SAMPLES  = 3
DBP_SUSTAINED_SAMPLES  = 3
MIN_ENVELOPE_V         = 1e-4
```

**已确认重复运行输出逐字节一致**（同一命令跑两次，JSON sha256 相同）。

## 两条冻结记录

| 版本 | estimator | 采集守门 | 适用 |
|---|---|---|---|
| v1 | `ddc9daf7…` | 无 | 已采 20 轮（Preset 1、2） |
| **v2** | `ddc9daf7…`（不变） | `tools/validity_v2.py`，峰区速率 ≤ 4.0 mmHg/s | **Preset 3、4 及以后** |

v2 不修改估算器。v2 新增的是**采集有效性守门**，回答"这一轮的数据能不能用来打分"，
与"这份波形意味着多少血压"是两个问题。

判据只有一条：峰区（200–245 mmHg）压力对时间的 OLS 斜率，`|slope| > 4.0` 即判该轮不可用。

来源：开发集 18 轮的最大值是 2.63 mmHg/s，实测两次阀故障是 13.35 与 15.49，
空档 5 倍以上。阈值从开发集独立可得，不依赖已经看到的故障。

另一条候选判据（邻域中值 > 10 mV）被实测否决：健康开发轮可达 11.14 mV，
健康前瞻轮可达 10.32 mV，会大量误伤。

**评分前必须对两条记录都跑 `python tools/verify_freeze.py`。**

## 采集目标

每预设 10 轮，共 40 轮。理由：现在每预设只有 3 轮，标准差估计的相对不确定度约
50%；10 轮可降到 25% 以下。

每轮约 3 分钟硬件时间，面板操作由操作员完成。

## 排除规则（采集前已声明，不得事后追加）

一轮被**排除**，当且仅当：

1. 严格解码器拒收（无完整 `end`、校验和不符、`dropped != 0`、`interval != 25`）
2. 预检拒跑且**未充气**
3. 运行中出现 `[Fault]` 计数增长或 `[Safety]` 行
4. vent→seal 收尾未确认封阀零点

一轮被**标记但不排除**，当估算器自己拒判（`unresolved_map` / `unresolved_sbp`）。
**拒判率是一个要报告的结果，不是要回避的失败。**

**不得因为结果与面板不符而排除任何一轮。不得在采集开始后修改任何估算器参数。**

## 每轮操作

1. 面板设定为对应预设（Preset 1/2/3/4），确认 `Cuff: External`
2. 袖带按同一松紧绑在同一位点（与之前的干态一致）
3. 运行：

```bash
python tmp/run_matrix_20261106.py <preset> <rounds> 275 prospective_validation
```

4. 脚本自动：预检 → vent/seal 净气 → `profile peak` → `target 275` → `start`
   → 等 `target reached` → 等 `[BP]` → 封阀收尾 → `capture export` → 拆分导出
   → 分析 → 写元数据

## 采集后

```bash
# 冻结的估算器跑前瞻组
python tools/reference_bp.py --json data/reports/reference_bp_prospective_v1.json \
    data/raw/<prospective_dir>/*.export.ndjson
```

报告必须同时给出：

- 每轮 `status`（含拒判轮次与原因）
- 相对面板的 MAP/SBP/DBP 偏差范围与 sd
- 与基线（sd 3.7 / 9.7 / 9.6）的对比
- **拒判率**

## 禁止事项

- 不得把前瞻组并入基线统计来"改善"数字
- 不得在前瞻组上做任何参数选择后再报告基线
- 不得因为前瞻结果比基线差而重采（除非触发了上面的排除规则）

## 若前瞻结果明显差于基线

这是**有效发现**，如实报告。可能原因包括：

- 3 轮估计的 sd 本身就不可靠（基线 sd 可能低估）
- 存在开发集未覆盖的失效模式

两种情况都值得写进论文，都不需要重采。
