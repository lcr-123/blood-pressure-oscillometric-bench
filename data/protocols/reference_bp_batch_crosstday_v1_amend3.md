# 跨天批次协议修订 3：把 §4 规则 10 真正实现，并修 §7 的两处坏命令（2026-11-25）

本文件修订 `reference_bp_batch_crosstday_v1.md`，不修改任何冻结脚本。它做三件事：

1. 补上 v1 从未实现的 **§4 规则 10**（T1/T3 只用完整日），并把「完整日」与「前 5 天/后 5 天」
   两个谓词写死；
2. 记录这条规则在本批次上的后果——**T3 的 SBP 日项从"不复现"变成"复现"**，因此
   `data/reports/crosstday_verdict_20261125.md` 的 T3 定性必须更正；
3. 修 §7 复现链里两处实测跑不通的命令。

协议 §7 的铁律不变：**批次期间不得改任何脚本。** 本文件写于批次结束之后（280 轮于
2026-11-25 14:39:45 跑满、同日 16 时判定完成），因此不触发批次重置。**但它同样不改动
任何 `tmp/` 下的冻结脚本**：冻结判定器 `tmp/crosstday_analyse_20261116.py`
（`e2830823…cfa896cc8`）保持原样，规则 10 由一个**新的**、入库的判定器实现，两者并列。

## 1 为什么必须补这一条

v1 §4 规则 10 原文：

> 10. **块B 未完成的日子不排除块A**：该日按 `half_day=True` 记账，T2 用它之外的日子算，
>     T1/T3 只用完整日。

而冻结判定器 `tmp/crosstday_analyse_20261116.py` 的 `main()` 里：

```python
report['t1'] = t1(rows, 'v2')                      # 全部存活轮
report['model_sbp_mmhg'] = two_way(rows, 'sbp_mmhg', 'v2')   # 全部存活轮，T3 就是它
```

`rows` 是全部存活轮，**没有任何按日过滤**。于是规则 10 在 v1 里是一句没有被执行的话。

### 1.1 这不是措辞问题，它翻转了一条结论

同一份 265 轮数据，两种读法：

| 口径 | 轮数 | SBP 日项 | 判定 |
|---|---|---|---|
| 全部十天（冻结脚本的读法） | 265 | `F(9,243) = 1.869`，`p = 0.0572`，`sw 17.206`、`sb 0.000` | **不复现** |
| 完整九天（规则 10 的读法） | 251（去掉 D1） | `F(8,230) = 2.162`，`p = 0.0313`，`sw 15.863`、`sb 1.151` | **复现** |

MAP 两个口径都是 `p ≥ 0.05`（0.1001 / 0.4413），DBP 两个口径都 `p < 0.05`
（0.0174 / 0.0208）。**只有 SBP 会翻。**

### 1.2 翻转的机理（逐日残差，`tmp/t3_residual_20261125.py`）

| 天 | 轮数 | 残差 sd | 备注 |
|---|---|---|---|
| D1 | 14 | **32.41** | half_day（块B 缺席） |
| D2 | 27 | 37.12 | 含两个 +119…+156 的长尾轮 |
| D3 | 27 | 8.94 | |
| D4 | 27 | 9.19 | |
| D5 | 27 | 9.20 | |
| D6 | 27 | 10.39 | |
| D7 | 27 | 17.62 | 含 −100.75 的长尾轮 |
| D8 | 27 | 7.60 | |
| D9 | 27 | 7.99 | |
| D10 | 26 | 7.69 | 块B P1 只留 1 轮 |

块A 的 137 轮整体残差 sd 是 17.31，**扣掉 D1 那 14 轮后只有 14.91**，而 D1 自己那 14 轮是
32.41。`F = (SS_day/df_day) / sw²` 的分子几乎不动（SS_day 占比 5.8 % → 5.3 %），分母从
15.86² 抬到 17.21²，F 掉 14 %，p 从 0.0313 滑到 0.0572 跨过 0.05。

留给下一次设计的教训：**半天残差比整天散一倍，会把格内 sd 抬高约 9 %，足以把 p=0.031
推过 0.05。** 半天要么不进 T3，要么按下面的谓词记账，不能默认"多一天总比少一天好"。

### 1.3 结论对谓词宽严不敏感（`tmp/t3_predicate_20261125.py`）

| 候选谓词 | 保留天 | SBP `p` |
|---|---|---|
| manifest `half_day` 旗标 | 2–10 | 0.0313 |
| 两块都存在 | 2–10 | 0.0313 |
| 每档在两块各 ≥1 轮 | 2–10 | 0.0313 |
| 每格恰好 2 轮（最严） | 2–9 | 0.0369 |

四种都 `< 0.05`。**"复现"不是靠挑谓词挑出来的**，这一点必须写进任何引用本判定的文字。

## 2 写死的两个谓词

### 2.1 完整日（规则 10 的操作定义）

> 一天是**完整日**，当且仅当该日 manifest 的块A 与块B 对**每一个设计档位**都至少留下
> 1 轮存活轮次。

判据只读 manifest（即操作员实际记下的东西），**不读任何估计值**，所以答案出来之后无法
事后调整。要点：

- 块B 整块缺席（D1）→ 不完整；
- 块B 某一档整档没有留下轮次 → 不完整；
- **块B 某一档只留了 1 轮（本该 2 轮）→ 仍算完整**。D10 的块B P1 就是这种情况
  （`-135554` 被冻结门拒绝后只剩 1 轮），按此谓词保留，这也是上表里 251 而不是 245 的原因。

实现见 `tools/crosstday_judge.py` 的 `complete_days()`。

### 2.2 前 5 天 / 后 5 天（T1 的切分）

> 前/后两半按 **manifest 计划的天号**切分：前 `len(days)//2` 天为早段，其余为晚段；
> 早段/晚段里不完整的那些天在 T1 中被剔除，但**不改变另一半的成员**。

冻结脚本是 `days = sorted({r['day'] for r in rows})` 后
`first, second = set(days[:split]), set(days[split:])`，即**把存活天列表按索引切半**。
只要早段少一天，晚段的第一天就会被挪进早段。实测（`tmp/t1_split_20261125.py`）：剔除
D6–D10 中任一天时，冻结脚本给出 `first [1,2,3,4]` / `second [5,7,8,9,10]`，
`improvement` 从 −1.325 变 −1.433。本批次 12 次留一法全部 FAIL，所以结论没受影响，
但下一次会受影响。

本批次按计划天号切分后：`first [1..5]`、`second [6..10]`，剔除 D1 后早段是 `[2,3,4,5]`。
**T1 仍然 FAIL**（`offset_fitted −0.7286`、`late_mean_without −1.6414`、
`late_mean_with −2.3700`、`late_sd 12.4658`、`improvement −0.7286`），
所以 `dataset_limitations.md` §25 的"加性偏移不可迁移"与"`SBP_OFFSET_MMHG` 保持 0.0"
**都不变**。

## 3 新判定器（入库，与冻结判定器并列）

| 文件 | 作用 | sha256 |
|---|---|---|
| `tools/crosstday_judge.py` | 冻结判定器的逐行移植 + 规则 10 + 按计划天号切分 | `1e665213dd413d4edcdcc846bfcec1ac59f2f7d50cdf412c9f356f218981db7c` |
| `tools/crosstday_judge_selftest.py` | 合成数据自检：规则 10 是否真的生效、切分是否跟计划、T0/T2/T4 是否未被改动 | `607d725c48a50613b768cf7cc256818a1ea939b1db1686a9e76ba19b2f7e68fb` |
| `tmp/crosstday_analyse_20261116.py`（**不动**） | 冻结判定器，仍可用于复现已发表读数 | `e28308230497cf8c2717bddbb757cdbfb6ba87e88f90aa66333d311cfa896cc8` |

用法：

```powershell
# 协议口径（规则 10 生效，默认）
python tools\crosstday_judge.py --rule10 on  --json tmp\judge_on.json

# 冻结口径（必须与 data/reports/crosstday_analysis_20261125.json 逐字段一致）
python tools\crosstday_judge.py --rule10 off --json tmp\judge_off.json

# 两种口径并列
python tools\crosstday_judge.py --rule10 both --json tmp\judge_both.json

# 自检（不读任何原始文件，毫秒级）
python tools\crosstday_judge_selftest.py
```

**回归约束**：`--rule10 off` 必须与冻结脚本的 JSON 在 `t0` / `t1` / `t2` / `t4` 与三个
`model_*` 上逐字段一致（浮点 1e-9）。2026-11-25 实测通过（`tmp/judge_regress_20261125.py`：
7 组比对全 `OK`，265 轮、10 天、1 轮排除均一致）。任何一次改动后这条必须重跑。

`--rule10 on` 的实测输出：完整日 `[2..10]`、T1/T3 用 251 轮、
SBP `F(8,230)=2.162 p=0.0313 sw=15.863 sb=1.151 n=245`、
MAP `F(8,236)=0.994 p=0.4413 sw=7.740 sb=0.000 n=251`、
DBP `F(8,236)=2.316 p=0.0208 sw=8.772 sb=0.939 n=251`。

T0、T2、T4 **仍然用全部存活天**（规则 10 只收紧 T1/T3）。新判定器的三处对应行是
`report['t0_all_days'] = t0(rows, 'v2')`、`t2_all_days`、`t4_all_days`，自检第 4 组会检查
这三行没有被换成 `strict`。

## 4 本批次 T0–T4 的最终读法

| 判定 | 冻结脚本读数 | 规则 10 读数 | 最终定性 |
|---|---|---|---|
| T0 可声明格 | 0/21（20 undecided + 1 FAIL） | 同（不丢天） | **0/21**；唯一 FAIL 是 P4/SBP |
| T1 偏移迁移 | FAIL | FAIL（分量不同） | **FAIL**；`SBP_OFFSET_MMHG` 保持 0.0 |
| T2 袖带缠绕 | 排除到 1.81 mmHg 以下（实测 −1.08，CI −5.28…+3.12） | 同（D1 本无块B） | **通过** |
| T3 SBP 日项 | `p = 0.0572` 不复现 | **`p = 0.0313` 复现** | **复现**（按 §4 规则 10） |
| T3 MAP 日项 | `p = 0.1001` 不复现 | `p = 0.4413` 不复现 | **不复现** |
| T3 DBP 日项 | `p = 0.0174` 复现 | `p = 0.0208` 复现 | **复现** |
| T4 两估算器 | v2 259/265 静默 20；covered_bp 248/265 静默 2 | 同 | **两者并列**，不合并 |

按 v1 §3 T3 的原文，SBP `p < 0.05` 意味着"**复现**"，此时**不撤回**
`data/reports/precision_levers_20261115.md` §3 的"跨天采样"建议；但该建议仍受 §5-D 第 44 条
约束：**"摊天数"只降批次均值 SE、不动单次测量 sd**，所以"跨天摊平就能达标"这句话依然
不能写。两句都要写，缺一即误。

## 5 §7 复现链的两处坏命令（实测跑不通，本修订一并修）

| 位置 | 原文 | 问题 | 改成 |
|---|---|---|---|
| §7 第 3 步 | `--glob "data/raw/development_20261101/standard*_peakwindow_crosstday-*.export.ndjson"` | 盘上**匹配 0 个文件**；真实 run_id 是 `standard060_030_target275_peakwindow_20261125-131619` 这种 | `--glob "data/raw/development_20261101/standard*_target275_peakwindow_2026111*.export.ndjson"`（或按 `batch_tag` 过滤，见下） |
| §7 第 4 步 | `python tmp\crosstday_analyse_20261116.py --tag crosstday` | 该脚本没有 `--tag` 参数，报 `error: unrecognized arguments: --tag crosstday` | `python tmp\crosstday_analyse_20261116.py --json data\reports\crosstday_analysis_<stamp>.json` |

按 `batch_tag` 取轮的可靠做法（批次跨 2026-11-16…25 十天，日期 glob 容易漏）：

```powershell
python -c "import json,pathlib; m=json.loads(pathlib.Path('data/manifest.json').read_text(encoding='utf-8')); rows=[r for r in m['rounds'] if r.get('batch_tag')=='crosstday']; print(len(rows)); pathlib.Path('tmp/crosstday_ids.txt').write_text('\n'.join(r['run_id'] for r in rows), encoding='utf-8')"
```

## 6 不改变的东西

- 排除规则 1–11 全部不变，本批次仍排除 1 轮
  （`standard120_080_target275_peakwindow_20261125-135554`，阀失节流，`peak_slope −16.14`）。
- T0 的门限（`|mean| + 半宽 ≤ 5.0`、`sd ≤ 8.0`）、T2 的 `1.81`、T4 的 `static >20` 口径全部不变。
- §6 五条禁令不变：不得重选估算器常量、不得给 P5/P7 SBP 下过/不过结论、不得用前 5 天常数
  报全库指标、不得因 T2 就把台架判成不可复现、不得写成"设备算法"或"符合 ISO 81060-2"。
- 三份 freeze（v1/v2/v3）不变，`python tools\verify_freeze.py` 必须继续报全部完好。

## 7 下次预注册必须带上的三件事

1. **规则 10 从一开始就在判定器里**，并且**判定器放在 `tools/`**（入库、有哈希、有自检），
   不再放在 `tmp/`——`tmp/` 被 `.gitignore` 忽略，冻结脚本的唯一身份锚点只能靠协议附录里的
   哈希，这是个结构性弱点。
2. **完整日与切分两个谓词写进协议正文**，而不是只在代码里。
3. **判定器入库时附回归测试**：`--rule10 off` 必须复现上一版读数，`--rule10 on` 必须能被
   合成数据证明规则生效。本次 `tools/crosstday_judge_selftest.py` 就是模板。

## 8 关联文件

- `data/reports/crosstday_verdict_20261125.md` §5（T3 定性已按本修订更正）
- `data/reports/dataset_limitations.md` §25（T1 不可迁移；§25a 口径差别；§25b 长尾）
- `data/reports/precision_levers_20261115.md` §3.2（判定标注已按本修订更正为"确认"）
- `data/reports/crosstday_analysis_20261125.json`（冻结脚本的原始输出，保留不动）
- `data/protocols/reference_bp_batch_crosstday_v1.md` §3 T3 / §4 规则 10 / §7 复现链
