# 跨天批次协议修订 4：编排器入库、日志名加块字母、失败归因工具（2026-11-25）

本文件修订 `reference_bp_batch_crosstday_v1.md`（含 amend1/amend2/amend3）。
**它不改任何冻结脚本**，也不改变已经跑完的 266 轮的任何字节。

它做三件事：

1. 把编排器从 `tmp/` 提升到 `tools/`——`tmp/` 被 `.gitignore` 忽略，266 轮数据的
   生产工具只能靠协议附录里的 sha256 指认，工作区一丢就不可复现（amend3 §7 已把
   这条列为结构性弱点，本次是它的落地）；
2. 修日志命名撞名：`<tag>_p<preset>_a<attempt>.out` 不含块字母，块B 会覆盖块A 的
   同名文件（整批 116 个 slot 的 `.out` 已被覆盖）；
3. 把「失败 slot 归因」做成入库工具，并更正此前「11 个失败 slot 已无法归因」的说法。

---

## 1 为什么编排器必须入库

`tmp/` 在 `.gitignore:2`，`git ls-files tmp` 返回 0 行。这意味着：

| 东西 | 现在唯一的身份锚点 | 丢了会怎样 |
|---|---|---|
| 编排器 `run_crosstday_20261116.py` | 协议附录 A 的 sha256 `e963e0fb…` + `tmp/verify_frozen_20261117.py` | 266 轮无法重跑，manifest 语义无法核对 |
| 采集脚本 `bp_standard255_195_target275_peakwindow_20261105.py` | 同上，`849d1db3…` | 同上 |
| 判定脚本 `crosstday_analyse_20261116.py` | 同上，`e2830823…` | 已发表的 T0–T4 读数无法复算 |
| 阀工作点 `daily_valve_point_20261116.py` | 同上，`5ae7679d…` | 每日卡片无法重算 |

amend3 已经示范了正确做法：**冻结副本留在 `tmp/` 不动（保住哈希），规则实现落进
`tools/`（入库、有哈希、有自检）**。本次对编排器做同样的事。

## 2 新编排器与冻结副本的差异

`tools/crosstday_orchestrator.py`（19152 B，
sha256 `4558e25500ece61903a5db1ba98256d6de2ae4cbb401184e6443b9a5f724d5a9`）是
`tmp/run_crosstday_20261116.py`（amend1 版，18212 B，
sha256 `e963e0fb5fd7960e6a289a139bc60790811abdbec5ff5aa3c021c2c98d55589e`）的
**逐字节副本**，只改三处：

| 位置 | 改前 | 改后 |
|---|---|---|
| 日志名 | `f'{tag}_p{preset}_a{attempt:03d}.out'` | `f'{tag}_p{preset}_a{attempt:03d}_{block}.out'` |
| `capture_round()` 签名 | `(preset, attempt, tag, extra, dry_run=False)` | `(preset, attempt, tag, extra, block, dry_run=False)` |
| 轮元数据 `orchestrator_path` | `'tmp/run_crosstday_20261116.py'` | `'tools/crosstday_orchestrator.py'` |

外加 docstring 里写明来源、两处行为差异、以及「冻结副本保留在 `tmp/` 以便已发表哈希
继续可验」。

**不变的东西（逐项确认）**：`PRESETS` 七档的 `(command, sbp, dbp, map note, cc)`、
`TARGET_MMHG = 275`、`MAX_ATTEMPTS_FACTOR = 3`、`SWITCH_WINDOW_S / SWITCH_ATTEMPTS /
SWITCH_RETRY_GAP_S = 12.0 / 3 / 2.0`（amend1 的切换策略）、`REWRAP_BEEP_EVERY_S =
20.0`、`wait_for_rewrap()` 的 marker 协议（存在即删、只认文件、没有 marker 就记块B
缺席）、manifest 的全部键与结构（`days[].blocks[].slots[]`、`captures_kept`、
`rewrap.waited_s`）、`--day` 防覆写、失败 slot 的记账方式。

## 3 日志命名撞名的实证

`tmp/log_collision_audit_20261125.py` 按 manifest 逐日统计。`lost` 指「留下的 `.out`
里找不到自己的 run_id」的 slot 数（失败 slot 没有 run_id，改判它是否仍含 `RESULT` 行）。

| 天 | slot | 日志名 | 被共用 | 丢自我 | 检查 |
|---|---|---|---|---|---|
| D1 | 17 | 17 | 0 | 0 | 17 |
| D2 | 29 | 15 | 14 | 14 | 29 |
| D3 | 28 | 14 | 14 | 14 | 28 |
| D4 | 32 | 18 | 14 | 12 | 32 |
| D5 | 31 | 17 | 14 | 13 | 31 |
| D6 | 29 | 15 | 14 | 13 | 29 |
| D7 | 30 | 16 | 14 | 13 | 30 |
| D8 | 37 | 23 | 14 | 11 | 37 |
| D9 | 30 | 16 | 14 | 13 | 30 |
| D10 | 30 | 16 | 14 | 13 | 30 |
| **合计** | **293** | **167** | **126** | **116** | **293** |

- D1 是 `half_day`（块B 因重缠确认超时缺席），0 撞名；
- D2–D10 每天 14 个名字被两块共用，正好是「7 档 × 2 轮」；
- `lost` 全部落在块A（块B 后写，挤掉块A）；
- D8 损失最少（11）是因为那天的块B 前四次尝试都在 `profile peak` 上失败、没写成文件。

加块字母后，同样 293 个 slot 会产生 **293 个不同名字、0 撞名**（按
`slot['log'][:-4] + '_' + block + '.out'` 重算验证）。

## 4 失败归因：证据没丢，但此前的说法要更正

### 4.1 改口径

D10 报告与 D7/D8/D9 日报里写过「27 个失败 slot 里 11 个已无法归因」。**这句不成立。**
11 说的是「`.out` 被覆盖、且当天报告没手工记原因」的那部分；当时没注意到采集脚本自己
写的轮元数据里 `error` 字段还在。

正确说法：

> 27 个失败 slot 中，11 个的 `.out` 被同名文件覆盖、13 个的 `.out` 内容属于别的轮次，
> 但**全部 27 个都能从轮元数据的 `error` 字段归因**。

### 4.2 为什么元数据救得了证据

采集脚本 `tmp/bp_standard255_195_target275_peakwindow_20261105.py` 自己写
`data/raw/development_20261101/<run_id>.metadata.json`，含 `error` 与 `outcome`。
编排器随后 `patch_metadata()` 追加 `batch_tag` / `batch_day` / `wrap_block`——但
**失败轮走不到那一步**（`capture_round()` 在 `outcome != 'export_received'` 时直接
return）。所以失败轮**缺**批次字段、**留**失败原因。

编排器一侧的 manifest 完整记录 `(day, block, preset, attempt)`，采集脚本一侧完整记录
`(error, panel_preset, 文件名时刻)`，两者按「天窗口 + 档位 + 时刻升序」即可配对。

### 4.3 工具与结果

`tools/attribute_failed_slots.py`（8289 B，sha256 `dbe57fa767ff8136…`）：

```
failed slots             27
failed metadata on disk 113
  inside a batch window  27
attributed               27 / 27
unattributed failed metadata inside windows: 0
```

原因分布：

| 次数 | 原因 |
|---|---|
| 19 | 超压：280 mmHg 判定先于到压判定（`main.c:794` 在 `main.c:805` 之前） |
| 4 | `profile peak` 设不上：seal 态真零点在 −1..+1 之外（D8 块B 开局连续四次） |
| 1 | 导出帧不完整（D2 的 `TimeoutError('incomplete capture export')`） |
| 1 | 时间戳 stale / 非单调（D4） |
| 1 | 命令未确认（D4 的 `TimeoutError('ACK profile')`） |
| 1 | 传输中断（D6 的单字节 U+FFFD） |

一处口径细节：D2 那轮的失败原因写在 `export_error` 而不是 `error`（因为失败发生在导出
阶段），工具用 `meta.get('error') or meta.get('export_error')` 兜住；只取 `error`
会把它误报为 `no error key in the metadata`。

退出码：0 = 全部归因且无多余元数据；非 0 = 有缺口。可直接进 CI。

## 5 日志名规则（新）

```
tmp/omniprobe/<batch_tag>_d<NN>_<YYYYMMDD-HHMMSS>_p<preset>_a<attempt:03d>_<A|B>.out
```

示例：`crosstday_d11_20261126-110000_p3_a002_B.out`

## 6 不改变的东西

- 冻结四件套（编排 18212 B `e963e0fb…`、采集 26314 B `849d1db3…`、判定 20581 B
  `e2830823…`、阀点 9629 B `5ae7679d…`）与 hex（184146 B `61ca1da3…`）**全部不动**，
  `tmp/verify_frozen_20261117.py` 必须继续报五个哈希 OK。
- 排除规则 1–11、T0–T4 的判定口径、§6 五条禁令、三份 freeze 全部不变。
- 已跑完的 266 轮的元数据不改：它们的 `orchestrator_path` 仍是
  `tmp/run_crosstday_20261116.py`，这是**历史事实**，不是错误。
- 日志目录仍在 `tmp/`（gitignore）。本修订只把**代码**入库，不搬日志。

## 7 下次预注册必须带上的三件事

1. **编排器一开始就放 `tools/`**，`tmp/` 只放一次性 scratch。判据：任何「产出数据集
   字节」的脚本都不许住在 gitignore 里。
2. **失败路径也要 `patch_metadata()`**：失败轮的元数据应当同样带 `batch_day` /
   `wrap_block`，这样归因不必依赖「天窗口 + 档位 + 时刻」的推断。本次没改，因为改采集
   脚本 = 改冻结哈希，只能下一批做。
3. **失败轮的 `.out` 归档进 `data/`**（例如 `data/raw/development_YYYYMMDD/failed_logs/`），
   否则日志永远活在 gitignore 里、覆盖一次就没了。需要同时决定它是否进 checksums。

## 8 关联文件

- `data/reports/failed_slot_attribution_20261125.md`（撞名审计 + 27 slot 逐条归因）
- `data/reports/crosstday_d10_20261125.md` §11 第 2 条（撞名债，本修订处置）
- `data/protocols/reference_bp_batch_crosstday_v1_amend3.md` §7（判定器入库的同一条教训）
- `data/protocols/reference_bp_batch_crosstday_v1.md`（附录 A 的五份哈希）
- `tools/crosstday_orchestrator.py`、`tools/attribute_failed_slots.py`
