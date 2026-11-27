# 失败 slot 的归因与日志命名撞名（2026-11-25）

跨天批次 D1–D10 共 293 个 slot：266 轮可用、27 轮失败。编排器把每个 attempt 的
stdout 写到 `tmp/omniprobe/<tag>_p<preset>_a<attempt>.out`，**名字里没有块字母**，
所以在任何完整的一天里块B 都会复用块A 的文件名。本文回答三个问题：撞名有多严重、
证据到底丢了没有、已经怎么修。

**本报告不含任何 MAP/SBP/DBP 估计值。**

---

## 0 一句话

撞名是真实的：293 个 slot 只要了 167 个日志名，126 个名字被要求了两次，116 个 slot
（全部是块A）留下的 `.out` 已经不是自己那一份。**但失败原因并没有丢**——采集脚本自己
写的 `<run_id>.metadata.json` 保留了 `error`，27/27 个失败 slot 全部可归因（19 超压、
4 次 `profile peak` 设不上、1 次导出帧不完整、1 次时间戳乱序、1 次命令未确认、1 次传输
中断）。修法是把编排器提升到 `tools/` 并给日志名加块字母，冻结副本不动。

---

## 1 现象

`tmp/run_crosstday_20261116.py:209`（逐步对照现在的 `tools/crosstday_orchestrator.py:222`）：

```python
log = ROOT / 'tmp' / 'omniprobe' / f'{tag}_p{preset}_a{attempt:03d}.out'
```

`tag` 只含批次、天号与启动时刻（`crosstday_d08_20261123-113754`），`preset` 与
`attempt` 在块A/块B 里取同一串值，所以同一天的块B 必然覆盖块A 的同名文件。
`capture_round()` 当时拿不到 `block`，因为它只收到 `(preset, attempt, tag, extra)`。

日志目录在 `tmp/`，而 `.gitignore:2` 是 `tmp/`——`git ls-files tmp` 返回 0 行，
所以这些日志**从来不进仓库**，覆盖发生在工作树里，没有 git 历史可回溯。

## 2 撞名有多严重

按 manifest 逐日统计。`names` 是当天出现过多少个不同的日志名，`shared` 是被两块
同时要求的名字数，`lost` 是「留下的 `.out` 里找不到自己的 run_id」的 slot 数
（失败的 slot 没有 run_id，改判它是否仍含 `RESULT` 行，见 §3.3 的说明）。

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

- D1 是 `half_day`（块B 因重缠确认超时而缺席），所以 0 撞名。
- D2–D10 每天都是 14 个名字被两块共用——正好是「7 档 × 2 轮」。
- `lost` 全部落在块A（`Counter` 只出现 `'A': 116`）：块B 的文件后写，块A 的文件被它
  挤掉。D8 损失最少（11），因为那天的块B 前四次尝试用自己的 `p1_a001..a004` 反复失败，
  反而没写成功、没覆盖到块A 的 `p2/p3/p5`；D3/D2 损失 14，因为块B 14 轮全部成功。

## 3 但失败原因没丢

### 3.1 证据在哪里

采集脚本 `tmp/bp_standard255_195_target275_peakwindow_20261105.py` 自己写
`data/raw/development_20261101/<run_id>.metadata.json`，里面就有 `error` 与
`outcome`。编排器随后调 `patch_metadata()` 往里加 `batch_tag` / `batch_day` /
`wrap_block`——但**失败轮走不到那一步**（`capture_round()` 在
`result['outcome'] != 'export_received'` 时直接 return，只有成功轮才
`patch_metadata(run_id, extra)`）。

后果是：失败轮的元数据**缺** `batch_day` 与 `wrap_block`，但**保留** `error`。
这足以归因，因为编排器的 manifest 一侧完整记录了 `(day, block, preset, attempt)`，
采集脚本一侧完整记录了 `(error, panel_preset, 文件名时刻)`。

### 3.2 归因结果（`tools/attribute_failed_slots.py`）

匹配规则：manifest 里的每个失败 slot（有 day/block/preset/attempt）→ 找
`outcome == 'failed'`、文件名时刻落在**该天窗口内**、且 `panel_preset` 相同的元数据文件；
按时刻升序取未被占用的第一个。批次窗口用 manifest 的 `started` / `finished`。

```
failed slots             27
failed metadata on disk 113
  inside a batch window  27
attributed               27 / 27
unattributed failed metadata inside windows: 0
```

| 天 | 块 | 档 | 次 | 时刻 | 原因 |
|---|---|---|---|---|---|
| 1 | A | 2 | 1 | 19:13:28 | 超压 |
| 1 | A | 4 | 1 | 19:28:29 | 超压 |
| 1 | A | 7 | 1 | 19:50:24 | 超压 |
| 2 | B | 1 | 1 | 12:22:09 | 导出帧不完整 |
| 4 | A | 2 | 1 | 10:44:26 | 时间戳 stale/nonmonotonic |
| 4 | A | 2 | 2 | 10:45:13 | 命令未确认（`ACK profile` 超时） |
| 4 | B | 5 | 2 | 12:06:36 | 超压 |
| 4 | B | 6 | 1 | 12:10:22 | 超压 |
| 5 | A | 2 | 2 | 19:28:41 | 超压 |
| 5 | B | 5 | 2 | 20:34:28 | 超压 |
| 5 | B | 5 | 3 | 20:35:04 | 超压 |
| 6 | A | 1 | 2 | 11:19:59 | 传输中断（单字节乱码） |
| 7 | A | 4 | 2 | 12:50:44 | 超压 |
| 7 | B | 7 | 2 | 14:01:14 | 超压 |
| 8 | A | 2 | 2 | 11:48:04 | 超压 |
| 8 | A | 3 | 1 | 11:52:01 | 超压 |
| 8 | A | 5 | 2 | 12:09:51 | 超压 |
| 8 | B | 1 | 1 | 12:34:24 | `profile peak` 设不上（真零点在 −1..+1 外） |
| 8 | B | 1 | 2 | 12:36:29 | 同上 |
| 8 | B | 1 | 3 | 12:38:34 | 同上 |
| 8 | B | 1 | 4 | 12:40:39 | 同上 |
| 8 | B | 6 | 1 | 13:18:31 | 超压 |
| 8 | B | 7 | 2 | 13:28:33 | 超压 |
| 9 | A | 5 | 2 | 12:08:54 | 超压 |
| 9 | B | 7 | 2 | 13:13:29 | 超压 |
| 10 | A | 4 | 2 | 13:12:30 | 超压 |
| 10 | B | 6 | 2 | 14:28:58 | 超压 |

原因分布：

| 次数 | 原因 |
|---|---|
| 19 | 超压：280 mmHg 判定先于到压判定（`main.c:794` 在 `main.c:805` 之前） |
| 4 | `profile peak` 设不上：seal 态真零点在 −1..+1 之外 |
| 1 | 导出帧不完整（D2 的 `TimeoutError('incomplete capture export')`） |
| 1 | 时间戳 stale / 非单调（D4） |
| 1 | 命令未确认（D4 的 `TimeoutError('ACK profile')`） |
| 1 | 传输中断（D6 的单字节 U+FFFD） |

逐日：D1 3×超压；D2 1×导出；D4 2×超压 + 1×乱序 + 1×未确认；D5 3×超压；
D6 1×传输中断；D7 2×超压；D8 5×超压 + 4×profile；D9 2×超压；D10 2×超压。

### 3.3 一处必须说明的口径

- **D2 那轮没有 `error` 键**：它的失败发生在导出阶段，采集脚本把原因写进
  `export_error = "TimeoutError('incomplete capture export')"` 而不是 `error`。
  第一版归因工具因此把它报成 `no error key in the metadata`；`failure_text()`
  改为 `meta.get('error') or meta.get('export_error')` 之后恢复为「导出帧不完整」。
- **失败的 slot 没有 run_id**，所以 §2 表格里的「丢自我」对它们是靠「留下的文件里还有
  没有 `RESULT` 行」判断的，不是靠 run_id 比对。它们真正的识别符是 manifest 的
  `(day, block, preset, attempt)` 加上 №3.2 的时刻匹配。
- 113 份失败元数据里有 86 份**不在**任何批次窗口内（2026-11-12…11-15 的开发尝试），
  它们没有被误配，因为窗口过滤是硬条件。

## 4 更正一处此前的说法

D10 报告与三份日报里写过「27 个失败 slot 里 **11 个已无法归因**」。这句话现在**不成立**：
11 说的是「`.out` 被覆盖、且当天报告没手工记原因」的那部分，当时没注意到元数据里
`error` 还在。正确说法是：

> 27 个失败 slot 中，11 个的 `.out` 被同名文件覆盖、13 个的 `.out` 内容属于别的轮次，
> 但**全部 27 个都能从轮元数据的 `error` 字段归因**。

这个更正不降低撞名的严重性——它只是说明「采集脚本自己写元数据」这条设计救了证据一次。
如果哪天采集脚本也在失败路径上提前 return 而不写元数据，证据就真的没了。

## 5 修法

### 5.1 编排器入库并加块字母

`tools/crosstday_orchestrator.py`（19152 B，sha256 见 §6）是
`tmp/run_crosstday_20261116.py`（amend1 版，`e963e0fb…`）的逐字节副本，只改三处：

| 位置 | 改前 | 改后 |
|---|---|---|
| 日志名 | `f'{tag}_p{preset}_a{attempt:03d}.out'` | `f'{tag}_p{preset}_a{attempt:03d}_{block}.out'` |
| `capture_round()` 签名 | `(preset, attempt, tag, extra, dry_run=False)` | `(preset, attempt, tag, extra, block, dry_run=False)` |
| 轮元数据 | `'orchestrator_path': 'tmp/run_crosstday_20261116.py'` | `'orchestrator_path': 'tools/crosstday_orchestrator.py'` |

外加 docstring 里写明「这是从 `tmp/` 提升的副本、只改这两处行为、冻结副本保留」。
预估效果：同样的 293 个 slot 会产生 **293 个不同名字、0 撞名**（实测脚本按
`slot['log'][:-4] + '_' + block + '.out'` 重算）。

### 5.2 冻结副本不动

`tmp/run_crosstday_20261116.py` 保持 `e963e0fb…` 不变（`tmp/verify_frozen_20261117.py`
五个哈希仍全 OK）。理由与 amend3 相同：它是 266 轮数据的身份锚点，改了就无法复现。
新编排器的行为差异写进 `data/protocols/reference_bp_batch_crosstday_v1_amend4.md`。

### 5.3 归因工具入库

`tools/attribute_failed_slots.py`（8289 B）：无参数时读默认 manifest，`--json` 落一份
机器可读结果（`tmp/failed_slots_20261125.json`，14974 B）。退出码 0 表示
「全部失败 slot 都归因成功且没有多余元数据」，非 0 表示有缺口——可以直接进 CI。
内置六类原因分桶（`BUCKETS`），顺序从最长到最短，保证「device safety/offline event:
[Safety] Over-pressure…」被归到超压而不是通用前缀。

## 6 命名规则与哈希

新的日志名规则：

```
tmp/omniprobe/<batch_tag>_d<NN>_<YYYYMMDD-HHMMSS>_p<preset>_a<attempt:03d>_<A|B>.out
```

| 文件 | 字节 | sha256 |
|---|---|---|
| `tools/crosstday_orchestrator.py` | 19152 | `4558e25500ece61903a5db1ba98256d6de2ae4cbb401184e6443b9a5f724d5a9` |
| `tools/attribute_failed_slots.py` | 8289 | `dbe57fa767ff8136…` |
| `tmp/run_crosstday_20261116.py`（冻结，未动） | 18212 | `e963e0fb5fd7960e6a289a139bc60790811abdbec5ff5aa3c021c2c98d55589e` |

回滚：把 `tools/crosstday_orchestrator.py` 删除即可，冻结副本一直在 `tmp/`，
`--day` 参数与 manifest 结构完全一致，两者可以互换（唯一差别就是日志名与
`orchestrator_path`）。

## 7 还缺什么

1. **已发生的 116 份覆盖无法复原**。本次靠元数据救回归因，但轮次内部的 stdout
   （每条 `[Pressure]`、每次命令回显）确实没了；对这些轮只能依赖 ndjson 与元数据。
2. **失败轮的元数据缺 `batch_day` / `wrap_block`**。新编排器应当在失败路径上也
   `patch_metadata()`，或至少让采集脚本接受批次字段——本次没改，因为改采集脚本
   = 改冻结哈希。这是下一批的预注册项。
3. **113 份失败元数据里 86 份在批次窗口外**（开发期尝试）。它们与批次无关，但归因
   工具目前靠窗口过滤，未来若批次窗口重叠会误配。
4. **日志目录仍在 `tmp/`**。新编排器把**代码**入库了，日志本身仍然 gitignore。
   是否把失败轮的 `.out` 归档进 `data/`（例如 `data/raw/…/failed_logs/`）需要单独决定，
   因为那会改变 checksums 的规模。

## 附：复现命令

```powershell
# 归因（无参数即默认 manifest）
python tools\attribute_failed_slots.py
python tools\attribute_failed_slots.py --json tmp\failed_slots_20261125.json

# 撞名审计（逐日 slot / 名字 / 共用 / 丢自我）
python tmp\log_collision_audit_20261125.py

# 新编排器的干跑（不写 manifest，不出日志）
python tools\crosstday_orchestrator.py --day 11 --rounds 2 --port COM12 --dry-run
```
