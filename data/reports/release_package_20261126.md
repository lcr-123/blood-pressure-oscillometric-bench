# 发布包与数据可用性声明（2026-11-26）

## 0 一句话

仓库里现在有一份**可独立下载、可独立校验**的发布物：62 轮已发布波形 + 解释它们所需的最小文档集，
共 **147 个文件 / 30.1 MB**，自带 `checksums.sha256` 与 `release.json`，用一个只读脚本就能验证，
不依赖克隆 2.4 GB 的开发数据。代码与数据分开授权（代码 MIT、数据 CC BY 4.0）。

## 1 为什么需要这一步

在此之前，这个工程能**复现**但**发不出去**，卡在三件事上：

1. **没有许可**。根目录没有 `LICENSE`，`data/README.md` 的「授权与引用」段只写了"按根目录 README 使用"，
   而根目录 README 那时没有任何法律条款。论文附带的数据集没有许可，第三方在法务上无法使用。
2. **没有可下载的东西**。62 轮已发布语料散在 `data/raw/development_20261101/` 的 645 份导出里，
   要拿这 62 轮得先克隆整个仓库（pack 457.72 MiB、工作树 2.4 GB）。`data/processed/` 是空的。
3. **没有 data-availability 说明**，也就没有"最小下载路径"这种可写进论文的句子。

## 2 许可

| 对象 | 许可 | 文件 |
| --- | --- | --- |
| 代码（`tools/**`、`blood pressure monitor/Core/**`、根目录 `*.py`、`docs/*.py`） | MIT | `LICENSE` |
| 数据（`data/raw/**`、`data/reports/**`、`data/protocols/**`、manifest、checksums） | CC BY 4.0 | `data/LICENSE` |
| 分界说明与不在范围内的内容 | —— | `LICENSE.md` |

`LICENSE.md` 明确了两件许可**不**管、但引用时仍是作者责任的事：一是按
`data/reports/dataset_limitations.md`「引用时必须声明的最小集」逐条声明采集条件；
二是声明这是非人体台架数据、真值是模拟器、**不构成临床验证**、不能说符合 ISO 81060-2。
许可只管"谁做的"，最小集管"这份数据能证明什么"——两件事互不替代，`LICENSE.md` 里写了这句。

不在授权范围内的：`blood pressure monitor/Drivers/**/LICENSE.txt`（ST 厂商文件，按各自条款）、
`archive/historical/**`（历史材料，未获授权再分发）、`tmp/**`、`软件下载/**`。

## 3 引用元数据

`CITATION.cff`（CFF 1.2.0）是机器可读的引用记录，`type: dataset`、`version: 2026-11-26`，
`license: MIT AND CC-BY-4.0`。里面写了一句在这个工程里非写不可的话：

> Cite the commit hash together with the version above, because the reports and
> the frozen records are versioned in the same history.

因为报告与冻结记录跟代码在**同一条** git 历史里，只给版本号不足以指认"哪一版报告"。
`preferred-citation` 标为 `generic`，说明这是仓库记录不是期刊论文——不虚构 DOI、不虚构期刊。

## 4 发布包里有什么

由 `tools/release_package.py` 生成，**轮次清单不手写**：它读 `data/manifest.json` 的
`published_corpus` 字段（该字段由 `tools/corpus_register.py` 从导出与冻结记录推导）。

```
dist/bp_waveforms_20261126/
├── README.md  LICENSE  LICENSE.md  CITATION.cff
├── checksums.sha256          ← 覆盖包内每一个文件，含 release.json
├── release.json              ← 轮数、文件数、字节数、层/门分布、轴口径
├── data/
│   ├── LICENSE  README.md  capture_protocol_v1.md  dataset_dictionary.md
│   ├── manifest.csv  manifest.json
│   ├── protocols/            ← 四份冻结记录（v1/v2/v3/v6）
│   ├── reports/              ← 8 份必读报告（见下）
│   └── raw/                  ← 62 × (.export.ndjson + .metadata.json)
```

实测量级：

| 内容 | 文件数 | 字节 |
| --- | --- | --- |
| 62 轮 `.export.ndjson` | 62 | 28,145,740 |
| 62 轮 `.metadata.json` | 62 | 715,519 |
| 文档 + 冻结记录 + manifest + release.json | 23 | 约 1.2 MB |
| **合计** | **147** | **30.1 MB** |

层分布 `frozen_baseline_v2 18 / prospective_v1 20 / prospective_v2 20 / supplementary 4`；
门分布 `USABLE 58 / REJECTED 4`——**这两个数字都在 `release.json` 里，且由校验脚本重算比对，
不是声明出来的**。

### 4.1 为什么默认不带逐样本遥测

已发布 62 轮的 `*.ndjson`（每秒 40 点的原始遥测）合计 **194,091,209 B**，占这 62 轮全部体积的
**87%**。而冻结估计器消费的是 `.export.ndjson` 里已经解码好的压力、电压与包络——
`tools/reference_bp.py:83-108` 的 `load()` 只读 `p`/`e`/`s`，不读遥测。
所以默认只发导出帧，需要逐样本审计时用 `--with-telemetry` 重新打包。
这是个**取舍而不是遗漏**，`release.json` 的 `with_telemetry` 字段把它写死，校验脚本会检查该字段与
包内遥测文件数是否一致（见 §5 的 `telemetry flag lie` 用例）。

### 4.2 随包发的八份报告及理由

| 文件 | 为什么必须随包 |
| --- | --- |
| `dataset_scope_statement.md` | 数据能证明什么、不能证明什么 |
| `dataset_limitations.md` | 26 条已知边界 + 引用必须声明的最小集 |
| `statistics_convention_20261111.md` | sd 是样本标准差还是总体标准差 |
| `pressure_axis_refit_20261126.md` | 压力轴重标定的做法与代价 |
| `pressure_axis_rebook_20261126.md` | 换轴后账本怎么变（6/7 → 5/7） |
| `freeze_v6_20261126.md` | 分数所依据的冻结记录是什么 |
| `v5_validation_20261114.md` | 三视图估计器**前瞻验证失败**的原始报告 |
| `crosstday_verdict_20261125.md` | 266 轮跨天批次的 T0–T4 判定 |

第七行是最容易被省略、也最不该省略的一份：它记录的是**失败**。只发通过的报告会把
`covered_bp` 说成"7/7 全过的算法"，而实测是 C1/C2/C4/C5 四项不过。

## 5 怎么验证（不克隆仓库也能做）

```bash
python tools/verify_release_package.py dist/bp_waveforms_20261126
```

四道检查，任一不过即非零退出：

1. `checksums.sha256` 里每条路径都存在且摘要吻合；
2. 没有路径被列两次（重复行是生成器缺陷，不是通过）；
3. 包内每个文件都在清单里（未列出的文件同样是缺陷）；
4. `release.json` 与树**一致**——轮数、层分布、门分布、`with_telemetry` 全部从文件重算后比对。

正向结果：

```
ok=147 mismatched=0 exports=62 metadata=62 telemetry=0 files=147
axis raw_bits slope=1118086889 intercept=3248429203: 62 export(s)
RELEASE PACKAGE OK: digests, coverage and counts all agree
```

反向测试 `tmp/verify_release_negative_20261126.py`（七种破坏 + 一次原样复核，**8/8 通过**）：
篡改一字节 → `MISMATCH`；删一份导出 → `MISSING`；塞一个多余文件 → `UNLISTED`；
把 `published_rounds` 改成 61 → `round(s) but the tree holds`；改层分布 → `tier split sums to`；
把 `with_telemetry` 谎报为 true → `with_telemetry=True`；重复一行 checksum → `DUPLICATE`。

**第四道检查是这份设计里唯一"防自欺"的一道**：前三道只证明"文件没被动过"，
只有重算计数才证明"包里确实是那 62 轮、不是别的东西"。

## 6 轴口径写进了包里

每个导出帧首行 `begin` 自带 `slope` 与 `intercept`（IEEE-754 位模式）。实测这 62 份
**全部是 `slope=1118086889 / intercept=3248429203`**，即 f32 的 `82.326 / -19.887`——旧轴。
校验脚本把这一项打出来（`axis raw_bits ...: 62 export(s)`），`release.json` 的 `axis` 字段也写明：

> captures_in_this_package: `82.326 mmHg/V` 与 `-19.887 mmHg`（62 轮全部早于 2026-11-26 重标定）
> firmware_after_refit: `81.529 mmHg/V` 与 `-20.03 mmHg`
> note: 读每份导出的 `begin.slope` / `begin.intercept`，不要写死任一条轴

这样做的原因是：`dataset_dictionary.md` 原来教的是 `p_true = v × 82.326 − 19.887`，
写死常量会在两代之间差 1–3 mmHg。

## 7 与仓库的关系：`dist/` 不入库

`.gitignore` 新增 `dist/`。理由是这个目录是 `data/raw/` 里已有字节的**副本**，
30 MB 重复进 git 只增长 pack 而不增加信息。入库的是
`data/release/published_corpus_20261126.json`（14445 B）——**包的身份证**：
62 个 `run_id` 及其 `date / preset / tier / gate / export_bytes`、文件数、字节数、
层与门分布、轴口径、许可指向、以及重建与校验的两条命令。

这份 JSON 的作用：第三方下载到包之后，可以核对自己手上的 62 个 `run_id` 与该提交点名的是否同一批。
它由 `tmp/release_manifest_20261126.py` 从 `release.json` 与 `data/manifest.json` 交叉断言生成
（`assert set(exports) == {r['run_id'] for r in published}`），不是手抄。

### 7.1 GitHub Release：真正的最小下载路径

§1 第 2 条说的"没有可下载的东西"到 2026-11-27 才算彻底解决。此前虽然有 `dist/` 里的包，
但它 `gitignore` 了、没上传，外部读者仍需克隆 362.4 MiB 才能自己跑一遍
`tools/release_package.py`——这跟"能下载"不是一回事。

现在包已作为 **GitHub Release** 发布：

| 项 | 值 |
| --- | --- |
| Tag | `v2026-11-26`（指向远端 `master` 的快照提交） |
| 页面 | <https://github.com/lcr-123/blood-pressure-oscillometric-bench/releases/tag/v2026-11-26> |
| 附件 | `bp_waveforms_20261126.zip`，5,911,202 B（5.64 MiB） |
| zip SHA-256 | `45e6912fb9c873c27f4c8dad375bee7c7705a2c0869c65c91b833eaf4e62cd43` |
| 解压内容 | `bp_waveforms_20261126/`，148 个文件 = 147 个清单内文件 + `checksums.sha256` 本身 |

三点设计取舍：

1. **zip 是确定性打包**（固定 `date_time=(2026,11,26,0,0,0)`、固定成员顺序、`compresslevel=9`），
   同样的输入重复打包会得到同一个 SHA-256。**哈希只写在本报告里**（本报告不在包内，
   所以写它不会改变 zip）；根 `README.md` 与 `data/README.md` 在包内，因此那两份文件
   刻意只指向 Release 页面上的 asset digest——把哈希写进 zip 自己的内容里会变成自指，
   每改一处文档哈希就再变一次。
   "确定性"这四个字还包含一个容易被漏掉的量：**`ZipInfo.create_system` 必须固定**。本包沿用
   `zipfile` 的默认值 `0`；若改成 `3`（Unix，通常是为了带上 `external_attr` 权限位），
   148 个成员头各差一个字节，同一个目录会算出另一个同样合法的 SHA-256
   （实测 `4790258c77daf1ba1e882b365a70d3d60ccbf88c1b53920e2f13b04635ce0b33`）。
   也就是说：**"我重打了一遍、哈希不一样"未必是包坏了，先对齐打包参数。**
2. **zip 只有 5.64 MiB / 30.1 MB = 18.7%**，因为 `.export.ndjson` 是高度可压缩的文本帧。
   不要因为"5.64 MiB"就以为包变小了——`release.json` 里的 30,126,567 B 才是解压后的量。
3. **附件是包而不是整库快照**。整库有 362.4 MiB，而 62 轮公开发布语料只占 30.1 MB；
   把整库塞进 Release 只会让"最小下载路径"重新变胖。

验收不是"上传成功"，而是**匿名下载后校验**：不带头、不走代理直连下载
`.../releases/download/v2026-11-26/bp_waveforms_20261126.zip` → HTTP 200、字节数与
SHA-256 与上表一致；解压后 `python tools/verify_release_package.py bp_waveforms_20261126`
→ `ok=147 mismatched=0 exports=62 metadata=62 telemetry=0 files=147` 与
`RELEASE PACKAGE OK`。GitHub 自己也算了一遍，`assets[0].digest` 与本地 SHA-256 相同。

还多做了一道**"包里的字节是不是仓库里的字节"**：`tmp/check_package_vs_tree_20261127.py`
把包里 148 个文件逐个与 `HEAD` 的 blob 对哈希（`data/raw/` 下的文件名要回到
`data/raw/development_20261101/` 去查，因为打包时把该子目录拍平了），结果
**146 个与 `HEAD` blob 逐字节相同、2 个是打包器生成（`checksums.sha256`、`release.json`）、
缺失 0、内容不符 0**。没有这一道，"能下载"只证明下载到了某个包，不证明这个包就是仓库
校验过的那份语料。

**tag 与附件必须一起动**：文档一改、快照重建，`master` 的哈希就变，`v2026-11-26` 若不跟着
`PATCH /git/refs/tags/v2026-11-26 {"sha": …, "force": true}` 就会指向一个旧树，而附件却是新树打出来的。
本次顺序固定为：改文档 → `build_checksums.py` → 三条校验 → `release_package.py` 重打 →
重打 zip → `republish_20261127.py`（API 造提交并 force 移 `master`）→ 移 tag → 再匿名下载复验。

## 8 data-availability 声明（可直接用于论文）

> 本数据集（波形、逐轮元数据、分析报告与参考实现）公开于
> **https://github.com/lcr-123/blood-pressure-oscillometric-bench**，以 **CC BY 4.0**
> 授权；采集与分析代码以 **MIT** 授权。已发布语料为 62 轮非人体台架采集，参考端为
> Fluke BP Pump 2 模拟器。**最小下载路径**是 Release `v2026-11-26` 的附件
> `bp_waveforms_20261126.zip`（147 个文件、30.1 MB，含全部 62 轮与最小文档集）；
> 发布包的构成、逐文件 SHA-256 与重建命令记录在
> `data/release/published_corpus_20261126.json`，可用 `tools/verify_release_package.py`
> 独立校验。数据**不构成临床验证**，不支持符合 ISO 81060-2 的声明；
> 引用所需的全部限定条件见 `data/reports/dataset_limitations.md`。

**这段在 2026-11-26 19:00 已经可以使用**，但要连同下面三点一起读。

1. **仓库已改为 public**。地址已存在、内容已推上去，现在对外部可见。
   改 public 是发布动作的最后一步，2026-11-26 已完成。
2. **远端只有一个提交**。本地开发历史 144 个提交**没有推上去**；远端 `master` 是一个
   orphan 快照（第一次推送得到 `a6750cc`，此后每改一份文档、重建一次快照，哈希都会变），
   树内容等于本地发布提交的树。所以引用时**用远端 `master` 的提交哈希**，不要用本地哈希。
   这份文档里刻意不写死当前远端 HEAD：写下它的那次编辑本身就会改变树、从而改变哈希。
   要去 GitHub 仓库页面的 `master` 上读。
3. **文档里出现的本地哈希在远端不存在**——`d022013`、`c60ef1f`、`5066fc5`、`7b0a04d`、
   `d7db003`、`0bf20b5`、`2430964` 都指向本地开发历史，这七个哈希已在
   `reports/release_blockers_20261126.md` §7 逐个登记（日期、提交标题、引用数、为什么保留）。

## 9 发布前的四件事：现状与处置

这四条在 2026-11-26 逐条处理过，处置记录在 `reports/release_blockers_20261126.md`。
四条均已完成，其中第一条的最后一步（改 public）在当天验收通过后落地。

| # | 事项 | 处置 | 状态 |
| --- | --- | --- | --- |
| 1 | 仓库地址 | 已建 `lcr-123/blood-pressure-oscillometric-bench`（先 private 验证，2026-11-26 已改 public），`§8` 已写入真实地址 | 已完成 |
| 2 | 托管与体积 | 选策略 B：645 份导出 + 825 份元数据留在版本库（跟踪树实测 362.4 MiB / 2537 文件），`data/raw` 下 1016 份逐样本遥测移出版本库 | 已完成 |
| 3 | `archive/historical/` | `git rm --cached` + `.gitignore`，工作区保留副本，`LICENSE.md` 表明不在授权范围 | 已完成 |
| 4 | `cloud/` 凭据 | `.gitignore` 挡住（从未提交，凭据未进历史）；新增 `tools/scan_secrets.py` 可检测 | 已完成 |

**第 2 条的取舍需要写清**：逐样本遥测合计 2208 MiB（`data/raw` 下 1016 份：1008 份 `*.ndjson`
加 8 份 `*.jsonl`），占 `data/raw` 的 88%，而
`tools/reference_bp.py:83-108` 的 `load()` 只读导出帧里的 `p`/`e`/`s`，
没有任何估计器读遥测。唯一读它的是 `tools/preset_low_bp.py`，读的是固件自己打的
`[BP] SBP=… DBP=… Pulse=… bpm valid=1`——这一行既不在导出帧里也不在元数据里，
所以移出遥测前先用 `tools/extract_device_verdicts.py` 把它抽成
`data/device_verdicts.json`（653 轮，`valid 278` / `calculation_failed 375`，94,550 B），
`--verify` 可逐轮比对确认无丢失。`components`：checksums 从 2,488 文件 / 2,510.4 MB
降到 **1,707 文件 / 326.3 MB**，且 `PATTERNS` 里移除 `*.ndjson` 后仍然
`unlisted=0`——因为版本库与校验表现在描述的是同一批文件。

**第 3 条与第 4 条都只改变"克隆者拿到什么"，不改变本地历史中的内容**：两者从首个提交
`2430964` 起就在本地历史里，`git rm --cached` 之后的克隆仍能 checkout 旧提交拿到这些字节。
真正删除需要重写 144 个提交，而本机没有 `git filter-repo`
（`git filter-repo --version` → `git: 'filter-repo' is not a git command`）。

**这一条已经用"另建干净仓库"绕开了**：远端 `master` 是一个从当前树构造的 orphan 快照，
只有 1 个提交，本地那 144 个提交（含 `human_*.ndjson` 与 `archive/historical/`）**没有推上去**。
代价是报告里的本地哈希在远端无法解析——在 §11 登记，而不是改写成快照哈希
（把 `built_from_commit` 改成快照哈希会让那句话变成假话：发布包确实是从 `d022013` 生成的）。

**第 5 条（原列表里的 3）仍是可选项**：Zenodo/DOI 只在论文需要 DOI 时才做，
`CITATION.cff` 现在故意没有 `doi` 字段，不是漏了。

## 10 复现

下面这些命令要在**匿名克隆**里跑（`git clone --depth 1` 之后进目录），不是开发工作树：

```bash
python tools/release_package.py --out dist/bp_waveforms_20261126          # 生成，30.1 MB
python tools/verify_release_package.py dist/bp_waveforms_20261126         # 四道检查
python tools/verify_checksums.py                                          # 1707 条逐条比对
python tools/verify_freeze.py                                             # 四条冻结记录
python tools/scan_secrets.py                                              # 已跟踪树不得含凭据
python tools/scan_secrets_selftest.py                                     # 14 抓到 / 10 放过
python tools/extract_device_verdicts.py --verify data/device_verdicts.json  # 653 轮，克隆里按 metadata 校验
python tools/dataset_tiers.py                                             # 645 轮七层 + 62 轮发布语料
```

需要遥测或未跟踪文件才有意义的三条（在克隆里分别 exit 2 / exit 2 / 无输出）：

```bash
python tools/release_package.py --out dist/full --with-telemetry          # 含遥测，约 223 MB
python tools/extract_device_verdicts.py --out data/device_verdicts.json   # 重建这张表
python tmp/verify_release_negative_20261126.py                            # 七种破坏（tmp/ 不跟踪）
python tmp/release_manifest_20261126.py                                   # 刷新 data/release/*.json
python tools/preset_low_bp.py --from-raw --preset 5                       # 无 manifest 时必须 --from-raw
python tools/scan_secrets.py --path cloud                                 # 只在有 cloud/ 的机器上
```

`extract_device_verdicts.py --verify` 在两种树上做两件不同的事：有遥测就逐轮重推再比对，
没有就退回"这轮还在、`panel_preset` 与记录一致"，最后一行必须打印做了哪一种。详见
`release_blockers_20261126.md` §8.1。

## 附 本次新增与修改的文件

字节数随修订变化，以 `git ls-tree -r -l HEAD | grep <path>` 为准；下表是
2026-11-27 修复"克隆里跑不通的三条命令"之后的值。

| 文件 | 字节 | 作用 |
| --- | --- | --- |
| `LICENSE` | 1069 | 代码 MIT |
| `LICENSE.md` | 2583 | 代码/数据分界、不在范围内的内容、怎么署名 |
| `data/LICENSE` | 2828 | 数据 CC BY 4.0（含推荐中英文署名文字） |
| `CITATION.cff` | 2922 | 机器可读引用记录 |
| `tools/release_package.py` | 6828 | 打包含计数自检 |
| `tools/verify_release_package.py` | 4735 | 四道检查 + 轴口径打印 |
| `data/release/published_corpus_20261126.json` | 14445 | 包的身份证（62 个 run_id） |
| `.gitignore` | 2209 | 新增 `dist/` |

2026-11-26 晚追加（发布前四件事）：

| 文件 | 字节 | 作用 |
| --- | --- | --- |
| `tools/scan_secrets.py` | 8112 | 11 条上下文敏感模式；`--staged` / `--path`；有命中即 exit 1，路径不存在 exit 2 |
| `tools/scan_secrets_selftest.py` | 3155 | 14 条必须抓到 + 10 条必须放过（含四个真实假阳性陷阱） |
| `tools/extract_device_verdicts.py` | 7876 | 把 653 轮固件的 `[BP]` 结论抽成一张 94 KB 的表 |
| `data/device_verdicts.json` | 94550 | 同上产出的表，遥测移出版本库后唯一的固件侧证据 |
| `tools/build_checksums.py` | 2354 | `PATTERNS` 去掉 `*.ndjson`；docstring 说明为什么 |
| `tools/verify_checksums.py` | 2347 | 同上，两份列表必须一致 |
