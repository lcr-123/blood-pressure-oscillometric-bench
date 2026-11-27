# 发布前的四件事：逐条处置与剩余风险（2026-11-26）

## 0 一句话

发布链条上原本有四个阻塞点，今天四条全部处置完毕（仓库地址、体积、历史归档、凭据）。
**前三项处置都只改变"克隆者拿到什么"，不改变历史**——
遥测、`archive/historical/` 与来源未确认的遥测仍然留在全部 144 个本地提交里，
从 HEAD 移除不改变 `git clone` 能取到这些字节这一事实。

## 1 四条是什么，为什么必须处理

`reports/release_package_20261126.md` §9 最初列了五条，去掉可选的 Zenodo/DOI 后是四条：

| # | 事项 | 为什么是阻塞 |
| --- | --- | --- |
| 1 | 仓库地址 | `§8` 的 data-availability 引用块里写着 `linchuangrui/blood-pressure-oscillometric`，而 `git remote -v` 为空。论文里一句指向不存在仓库的数据可得性声明，比缺失更糟 |
| 2 | 托管与体积 | pack 457.72 MiB、提交树 2.52 GiB（3565 文件）。推到 GitHub 前必须决定哪些字节留在版本库 |
| 3 | `archive/historical/` | 第三方 Ansur 插件（8.7 MB exe）与 12 张论文页 PNG，`LICENSE.md` 已声明"未获授权再分发"，但文件仍在库里 |
| 4 | `cloud/` 凭据 | 未跟踪、未被 gitignore，内含明码 MQTT broker 地址与口令。一次 `git add -A` 就会公开 |

## 2 逐条处置

### 2.1 仓库地址：不写猜测地址

**决定：先占位 + 自曝，地址到手后再写入。** 当时 `git remote -v` 为空、只有 `master`
一个分支、141 个提交，`§8` 只能用 `⟨待填：仓库 URL⟩`，并写明为什么不用
`linchuangrui/...` 这个猜测地址（读者会去点它）。

**2026-11-26 18:24 更新**：地址已存在，`§8` 已写入
`https://github.com/lcr-123/blood-pressure-oscillometric-bench`。`CITATION.cff` 已补 `repository-code`；
`doi` 与 `license-url` 仍故意留空（没有 DOI、没有独立许可页），`preferred-citation`
仍标 `type: generic`，不虚构期刊。

**状态：已完成。**

### 2.2 体积：选策略 B，遥测移出版本库

三条路线，按下表统计口径逐字节复算（`git ls-tree -r -l 9c1cddf^` 一次遍历求和，不再逐文件
`git cat-file -s`；该提交是最后仍跟踪遥测的那个版本，3565 个文件 / 2579.95 MiB）：

| 策略 | 内容 | 跟踪树字节 |
| --- | --- | --- |
| A | 代码 + 文档 + 62 轮发布包（1050 文件） | 62.1 MiB |
| **B（选定）** | A + 全部 645 份导出 + 825 份元数据（289.7 + 8.2 MiB） | **359.9 MiB** |
| C | B + 全部 1030 份逐样本遥测（2210.2 MiB） | 2570.2 MiB |

（C 再加 `archive/historical/` 15 文件 / 9.8 MiB 就是 `9c1cddf^` 整棵树 2579.95 MiB。）

落地的实际跟踪树是 **2537 文件 / 362.4 MiB**（`git ls-tree -r -l master`）= 策略 B 的
359.9 MiB + 保留的 14 份 `*.capture.ndjson` / `*.verified.ndjson` / 桥接遥测 2.4 MiB。
上表是"造仓库前的规划复算值"，362.4 MiB 是"造完之后的实测值"，引用体积时用后者。

选 B 的依据是取证，不是估计：`tools/reference_bp.py:83-108` 的 `load()` 只读导出帧里的
`p`/`e`/`s` 三个数组，**没有任何估计器读逐样本遥测**。遥测占 `data/raw` 提交树的 88%
（2207.8 / 2516.5 MiB），是采集副产品。

**唯一读遥测的地方**是 `tools/preset_low_bp.py:69-86` 的 `device_verdict()`：它从
`data/raw/<run_id>.ndjson` 里正则抓固件自己打的
`[BP] SBP=(\d+) DBP=(\d+) Pulse=(\d+) bpm valid=1`。这一行**既不在导出帧里也不在元数据里**
（元数据的 85 个键只有面板值与 `[Pressure]` 回显），所以移出遥测前必须先把它抽出来：

```
python tools/extract_device_verdicts.py --out data/device_verdicts.json
→ 653 轮有结论：valid 278 / calculation_failed 375，94550 B
python tools/extract_device_verdicts.py --out data/device_verdicts.json --verify data/device_verdicts.json
→ verified: 653 recorded verdict(s) still match
```

`tools/preset_low_bp.py` 改成优先读这张表，表里没有才回落读遥测。实测
`python tools/preset_low_bp.py --from-raw --preset 5 --preset 6 --preset 7` 输出与改前一致
（P5 `calculation_failed 73 / valid 6` 加 6 行具体数值）。

**校验表跟着收窄。** `tools/build_checksums.py` 与 `tools/verify_checksums.py` 的
`PATTERNS` 都去掉 `*.ndjson`（保留 `*.export.ndjson`）。理由是校验表必须描述
**克隆真正收到的东西**，否则它会对一批 gitignored 文件报 `UNLISTED`，
再过一遍就变成"为了让检查通过而检查"。

| | 移出前 | 移出后 |
| --- | --- | --- |
| checksums 覆盖 | 2488 文件 / 2510.4 MB | **1707 文件 / 326.3 MB** |
| 构成 | — | metadata 770 / export 645 / reports 279 / 其余 13 |
| `verify_checksums.py` | `ok=2488` | **`ok=1707 mismatched=0 missing=0 duplicates=0 unlisted=0`** |

**发布包回归**：`tools/release_package.py` 仍产出 62 轮 / 147 文件 / 30.1 MB，
`tools/verify_release_package.py` 仍 `RELEASE PACKAGE OK`——因为包里从来没带过遥测。

### 2.3 `archive/historical/`：`git rm --cached` + `.gitignore`

15 个文件 / 10,272,145 B，从首个提交 `2430964`（2026-11-06「初始导入」）起就被跟踪：

```
archive/historical/legacy-tools/ansur_bppump2_plugin_1.0.3.1.exe   8,667,090 B
archive/historical/reference-pages/paper_p25/p31/p57/p58/p64/p65/p67/p68/p69/p72/p74/p75.png
                                                                    1,604,731 B
两个 README.md                                                          1,323 B
```

**先确认没有依赖**：`git grep` 只在 3 处提到这个目录——`LICENSE.md`、根 `README.md`
第 6 条、`reports/release_package_20261126.md`；**没有任何工具、报告或复现链读它**，
所以移除不影响任何可复现步骤。

处置：`git rm --cached`（工作区副本保留）+ `.gitignore` 加 `archive/` + `LICENSE.md`
改成描述"已从 HEAD 移除、工作区保留、历史里仍在"。

### 2.4 `cloud/`：gitignore + 可检测

**这是四条里唯一可能造成不可逆后果的**：23 文件 / 281,430 B，明码凭据分布在
`cloud/dashboard/bp_dashboard.html:112-115`（broker 地址、8084 端口、`bp-web` 账号、
预填的 `123456` 密码）、`cloud/esp8266/bp_gateway/bp_gateway.ino:30/35`、
`cloud/esp8266/_selftest/_selftest.ino:4`、`cloud/esp8266/WIRING.md:55`、
`cloud/tools/{probe_ports,sim_gateway}.py`、`cloud/README.md` 三处。

**先证明没泄漏**：`git log --all -- cloud/` 为空（从未提交），`git grep` 扫已跟踪树时
`emqxsl` / `123456@@` / `bp-web` / `bp-device-001` / `PRIVATE KEY` 全部 0 命中。

处置两层：

1. `.gitignore` 加 `cloud/`（注释写明为什么、指向两个含凭据的文件、要求先脱敏）。
2. 新建 `tools/scan_secrets.py`——把"靠人记得不要 `git add -A`"换成可执行的检查。
   11 条模式全部**要求凭据上下文**，不匹配裸数字：

   | 模式 | 为什么这样写 |
   | --- | --- |
   | 含 `PASSWORD`/`SECRET`/`TOKEN`/`KEY` 的标识符被赋成字符串 | 裸 `123456` 在 Cortex-M 头文件里命中 589 个文件，不能当判据 |
   | C 字符数组 `PASS[] = "…"` | 覆盖 `_selftest.ino:4`，第一版漏了这个名字 |
   | `<input>` 里 `type=password` 与 `value="…"` 同时出现 | 两个 lookahead，属性顺序无关（`bp_dashboard.html` 是 `value` 在 `type` 之前） |
   | `id`/`name` 含 `pass` 且带非空 `value` | 第二道网，覆盖预填密码框 |
   | PEM 私钥块、AWS/GitHub/Slack/bearer token、URL 内嵌口令 | 常见失手形态 |

   `SKIP_FILES` 只有一条豁免（`tools/scan_secrets_selftest.py`，它必须放合成凭据），
   且**每次运行都打印这条豁免**，不静默跳过。

   ```
   python tools/scan_secrets.py                 → clean: 1802 file(s) scanned
   python tools/scan_secrets.py --path cloud    → 7 hits, exit 1
   python tools/scan_secrets_selftest.py        → SELFTEST OK: 14 caught, 10 ignored
   ```

   自检里 10 条"必须放过"的样本都是真实假阳性陷阱：`matrix[0] = 123456`、
   `0x12345678`、`raw=123456 ads=...`、以及只在注释里提到扫描器自己的行。

## 3 顺带发现：15 个来源未确认的遥测

查孤儿文件（不在 `data/manifest.json`、不被任何文档引用）时发现 `data/raw` 根下有
15 个从首个提交就入库的文件：`human_run01`–`human_run10`、`human_run05_v2`、
`human_v2_run01`–`human_v2_run03`、`nonhuman_160_test`，共 20.1 MiB。

它们与 `data/reports/dataset_scope_statement.md` 的「非人体台架，无真人」直接冲突。
四项区分尝试全部失败：

| 尝试 | 结果 |
| --- | --- |
| 心率（FFT + 自相关） | 56–75 bpm 混杂，`nonhuman_160_test` 落在中间 |
| 搏动幅度变异系数 | 不可分 |
| 呼吸带调制深度（0.15–0.45 Hz） | 不可分 |
| 按周期折叠的搏动模板 R² | 全部 0.003–0.05，含 `nonhuman_160_test` 0.027 |

它们同一晚（2026-10-17 22:32–23:56）、同一固件、同一 160 mmHg 目标、同样约 118 s
的充气—保持—降压流程。唯一可比的模拟器对照组在次日（`bppump_std120_run01/02`），
而那两次的 pulse 估计本身就给出 75 与 84 两个不同值——**"pulse 值不稳定"也不能当真人证据**。

**因此无法排除其中含真人采集。** 处置：从 HEAD 移除 + `.gitignore`，并在
`dataset_scope_statement.md` 里写明「来源未确认，不属于本数据集，引用时不得引用或再分发」。
它们从未进 manifest、从未参与任何估计或判定、从未进 checksums，所以移除不影响 645 轮的
任何数字。

## 4 剩余风险：HEAD 移除 ≠ 历史清除

三项处置都只改 HEAD。三条证据说明**本地历史**里仍在：

```
$ git log --oneline -- data/raw/human_run01.ndjson
2430964 初始导入：STM32F103ZET6 示波法血压采集固件与非人体台架数据集

$ git log --oneline -- archive/historical/legacy-tools/ansur_bppump2_plugin_1.0.3.1.exe
2430964 初始导入：…

$ git count-objects -vH
size-pack: 457.72 MiB          ← 移除 1031 个文件、2.33 GB 提交树字节，pack 一个字节没变
```

真正清除需要重写全部 144 个提交：

```
$ git filter-repo --version
git: 'filter-repo' is not a git command. See 'git --help'.
```

本机没有 `git-filter-repo`（git 2.55.0.windows.5）。即使装上，重写历史会让全部已发表
报告的 commit hash 引用失效——包括 `data/release/published_corpus_20261126.json` 里
`built_from_commit d022013a…` 那类锚点，以及冻结记录里钉住的协议哈希。

**这条不是技术问题，是取舍**，2026-11-26 已经选定第三种：

| 选项 | 代价 | 裁定 |
| --- | --- | --- |
| 保留历史，公开时在数据可得性声明里注明 | 克隆者能取到 20.1 MiB 来源未确认遥测与 9.8 MiB 未授权归档 | 否 |
| 重写历史后再公开 | 全部报告里的 commit 引用失效，需重写引用表；`git filter-repo` 需先安装 | 否 |
| **另建一个干净仓库，只推当前状态** | 与"代码与数据在同一条历史"的设计相悖，报告里的本地哈希锚点在远端无法解析 | **选定** |

**处置结果**：远端 `master` 是一个 orphan 快照（`git write-tree` 与本地发布提交的树相同），
`git rev-list --count` = **1**。第一次推送得到 `a6750cc`；每次重建快照哈希都会变，
引用时以仓库页面上 `master` 的 HEAD 为准。本文刻意不写死当前远端 HEAD——写下它的那次编辑
本身就会改变树、从而改变哈希。本地 144 个提交不发布。

**这条链路怎么走通的（不是 `git push`）**：这条网络路径上 `git push`、`git fetch`、
`git push --dry-run` 全部在服务器接收阶段被断（`curl 55 Recv failure: Connection was reset`、
`curl 28 Connection timed out after 300053 milliseconds`、
`fatal: the remote end hung up unexpectedly`；第三次尝试已经传完 2614 个对象 / 75.24 MiB
才被断，说明卡点在服务器接收而不是缺对象——远端 `a6750cc` 的全部对象本地本来就有）。
最终改用 GitHub git-data API 四步：
`POST /git/blobs`（7 个改动文件，base64）→ `POST /git/trees`（自底向上 3 层）→
`POST /git/commits` → `PATCH /git/refs/heads/master`（`force: true`）。
每步都断言返回的 SHA 与本地相同：7 个 blob 与 3 层 tree 逐一相同；`PATCH` 后远端
`master` 从 `a6750cc` 变成 `a41aecd…`（此后每改一份文档、重建一次快照，这个哈希都会再变）。
再用 `GET /git/trees/8c7bfe27…?recursive=1` 与 `git -c core.quotepath=false ls-tree -r`
逐路径比对，2537 个 blob **only local 0 / only remote 0 / content differs 0**。

两个必须记住的坑：API 造的提交对象与本地 `git commit` 造的字节不同（**author 与 committer
共用同一个 epoch，且消息保留结尾换行**），所以本地提交对象要用
`git hash-object -t commit -w --stdin` 重写成与 API 逐字节相同的形态，两边哈希才一致，
否则远端会多出一个本地没有的提交；`git ls-tree` 默认 `core.quotepath=true` 会把中文
文件名转义成 `\347\244\272…`，与 API 的 UTF-8 路径对不上，比对时必须加
`-c core.quotepath=false`。仓库随后改为 public，匿名 `git ls-remote` 与
`git clone --depth 1` 现均可直接取到。

**代价已登记而不是抹掉**：`data/release/published_corpus_20261126.json` 的
`built_from_commit` 仍然是 `d022013a…`——这句话是真的，发布包确实从那个提交生成。
七个本地哈希在 §7 逐个登记，并说明它们在远端不可解析。把哈希改写成快照哈希才是假话。

## 5 处置后的数字（可核对）

| 项目 | 处置前 | 处置后 |
| --- | --- | --- |
| 被跟踪文件（提交树，`git ls-tree -r`） | 3565 | **2537** |
| 跟踪树字节 | 2579.95 MiB | **362.4 MiB** |
| pack | 457.72 MiB | 457.72 MiB（未 gc） |
| `data/raw` | 2592 文件 / 2516.5 MiB | **1576 文件 / 308.7 MiB** |
| checksums 覆盖 | 2488 文件 / 2510.4 MB | **1707 文件 / 326.3 MB** |
| 已发布语料 | 62 轮 / 147 文件 / 30.1 MB | 不变（包里从无遥测） |

提交树明细（处置后）：`data/raw` 1576 / 308.7 MiB、`blood pressure monitor` 401 / 19.8 MiB、
`data`（非 raw）318 / 17.1 MiB、`calibration_data` 12 / 8.3 MiB、`docs` 24 / 4.7 MiB、
根目录 15 / 2.0 MiB、`.trellis` 92 / 1.0 MiB、`tools` 53 / 0.5 MiB、`.agents` 46 / 0.2 MiB。

### 5.1 跟踪面里还剩 13 份"看起来该被排除"的文件（已裁定，不是遗漏）

克隆验收时用"不该出现的扩展名"扫了一遍远端快照，命中 13 份。逐份查过来源，结论是
**7 份必须留、1 份留、4 份不属发布面但无害**，没有一份需要移除。

| 文件 | 大小 | 是什么 | 裁定 |
| --- | --- | --- | --- |
| `data/reports/restart_low30_20261031-142713.capture.ndjson` | 7,694 B | `bp.capture/3` 捕获帧（`firmware DEFLATE_RATE_TEST_20261029`，n=65） | **保留** |
| `data/reports/standard120_80_20261101-{111311,114844,120429,152030}.verified.ndjson` | 279,145–377,875 B 各 | 同上，`READ_PATH_TEST_20261031` 等，n=2277–3133 | **保留** |
| `data/reports/standard150_100_20261101-123247.verified.ndjson` | 同上量级 | 同上 | **保留** |
| `data/reports/standard200_150_20261101-134453.verified.ndjson` | 同上量级 | 同上 | **保留** |
| `data/reports/standard255_195_target275_capacity4200_20261105-111540.verified.ndjson` | 同上量级 | 同上 | **保留** |
| `.trellis/tasks/06-19-bp-firmware-bringup/human-test-manifest.csv` | 362 B | 表头 20 列 + 5 行只有序号、其余全空 | **留**：无人体数据，`git grep` 零引用 |
| `blood pressure monitor/MDK-ARM/pb8_inflate_2s_20261031.ndjson` | 115,472 B | `ek.telemetry/v1` 桥接遥测 | 不属发布面但无害 |
| `blood pressure monitor/MDK-ARM/pb8_inflate_preflight_20261031.ndjson` | 102,705 B | 同上 | 不属发布面但无害 |
| `calibration_data/open_zero_1792907716303.ndjson` | 72,672 B | 同上 | 不属发布面但无害 |
| `calibration_data/zero_1792907611259.ndjson` | 58,222 B | 同上 | 不属发布面但无害 |

**为什么 7 份捕获帧不能删**：它们是 `data/reports/` 下 11 份报告正文唯一引用的波形来源
（`standard120_80_20261101-111311.md` 等）。删掉它们，那些报告的结论就没有可核对的证据了。
它们与 export 是同一个 `bp.capture/3` schema（`begin` 行同样带
`slope 1118086889 / intercept 3248429203` 的 f32 位模式），只是扩展名不带 `.export.`，
所以 `tools/build_checksums.py` 的 `PATTERNS`（`*.export.ndjson`）没有覆盖它们——
这是 `data/reports/` 里 287 个文件只有 279 个进 checksums 的全部原因，
差集正是这 7 份加 1 份 `.capture.ndjson`。

**为什么 4 份桥接遥测留着**：它们不在 `data/raw/` 下（`.gitignore` 的遥测规则只挡
`data/raw/`），体量合计 349 KB，不含人体数据（`pb8_inflate_*` 是 PB8 管脚驱动的空载预检，
`open_zero_*` / `zero_*` 是 ADS1115 零点采样），其中只有 `pb8_inflate_*` 被
`.trellis/tasks/06-19-bp-firmware-bringup/pb8-relay-20261031.md:41,45` 两处正文提到。
它们是"2026-10-31 固件期调试记录"，不属数据集发布面，但作为工程史保留不会伤害可复现性。

**这 13 份全部不在**：`data/checksums.sha256`（0 命中）、`data/manifest.json`（645 个 run_id
里没有 `pb8` / `open_zero` / `zero_179`）、`data/reports/INDEX.md`（0 行）。所以它们既不被
校验命令覆盖，也不被任何统计口径计入——留着只是让报告的证据可查。

## 6 还缺什么

1. ~~**仓库 URL**~~。**已完成**：`lcr-123/blood-pressure-oscillometric-bench`
   （先 private 验证，验收通过后已改 public）。`§8` 与 `CITATION.cff` 都已写入。
2. ~~**是否重写历史**~~。**已裁定**：不重写，另建 orphan 快照推送（§4）。
   遗留代价是七个本地哈希在远端无法解析，见 §7。
3. **`git gc` 未执行**。pack 仍 457.72 MiB；`git gc --prune=now` 能把不再可达的对象
   真正清掉一部分（但旧提交仍引用它们，所以收益有限）。
4. **`cloud/` 目录本身没脱敏**。它仍在工作区，将来要用得先从环境变量读凭据。
   `.gitignore` 只保证它进不了版本库，不保证它不被别的途径带走（打包、压缩、截图）。

## 7 本地哈希在远端不可解析（已登记的代价）

远端只有一个快照提交，所以下面七个哈希在 GitHub 上**查不到**。它们出现在仓库文本里
不是错误，每一处都指向一次真实的本地提交；把它们改写成快照哈希才会让内容变成假话
（例如 `built_from_commit` 会说成"发布包从快照生成"，而它实际是从 `d022013` 生成的）。

| 哈希 | 日期 | 提交标题 | 文本引用数 | 为什么保留 |
| --- | --- | --- | --- | --- |
| `d022013` | 2026-11-26 | Retire the claims the recalibration overturned | 3 | `data/release/published_corpus_20261126.json` 的 `built_from_commit`：62 轮发布包就是从这一次提交的树打出来的 |
| `c60ef1f` | 2026-11-26 | Refit the pressure axis with one calibration write | 3 | 冻结记录 v6 登记的压力轴与九常量来自这一次提交 |
| `2430964` | 2026-11-06 | 初始导入：STM32F103ZET6 示波法血压采集固件与非人体台架数据集 | 5 | 说明 `human_*.ndjson` 与 `archive/historical/` 从哪个提交开始就在历史里 |
| `0bf20b5` | 2026-11-25 | Implement the cross-day protocol's rule 10 instead of leaving it in prose | 2 | 跨天判定器落地的那一步 |
| `5066fc5` | 2026-11-11 | Say what the high-pressure preset can and cannot support | 9 | v3 冻结的锚点；`tools/dataset_tiers.py:50` 的 `PUBLISHED_SOURCE` 字符串里也写着它 |
| `7b0a04d` | 2026-11-13 | One set of constants for all seven presets: three-view median estimator | 3 | v5 判据与九个常量提交的时刻 |
| `d7db003` | 2026-11-14 | Prospectively test the seven-preset estimator: it fails four of five criteria | 5 | v5 批次关闭的时刻 |

**只有一处是可执行判断，且不依赖哈希**：`tools/v3_acceptance.py:57` 与
`tools/v5_acceptance.py:58,69` 用的是时间戳（`2026-11-11T09:49:47`、`2026-11-13T21:09:53`、
`2026-11-14T15:21:46`），哈希只出现在注释里。`tools/verify_release_package.py` 不比对
`built_from_commit`。所以这七个悬空引用**不影响任何校验命令的通过与否**——
`python tools/verify_checksums.py` 与 `python tools/verify_release_package.py` 都不读它们。

**如果要让它们在远端可解析**，只有两条路：把 144 个提交全推上去（违背"只推当前状态"的选择），
或在文档里给每个哈希补一句"本地开发历史，远端不可解析"——本表做的就是后者。

## 8 复现

在**匿名克隆**里逐条跑（`git clone --depth 1` 之后 `cd` 进去，不要用开发工作树）：
工作树里能跑通不代表克隆里能跑通，`data/raw` 下的逐样本遥测不在版本库里。

```bash
python tools/scan_secrets.py                      # 已跟踪树：clean 1805 文件
python tools/scan_secrets_selftest.py             # 14 caught / 10 ignored
python tools/extract_device_verdicts.py --verify data/device_verdicts.json  # 653 verdicts still match
python tools/verify_checksums.py                  # ok=1707 ... unlisted=0
python tools/release_package.py --out dist/probe --force
python tools/verify_release_package.py dist/probe  # RELEASE PACKAGE OK
git log --all -- cloud/                            # 空：从未提交
```

三条只在特定树上成立的命令，各自的正确用法：

```bash
python tools/scan_secrets.py --path cloud          # 只在有 cloud/ 的机器上有意义；目录不存在时 exit 2
python tools/preset_low_bp.py --from-raw --preset 5  # 无 manifest 时必须用 --from-raw；裸跑 exit 2
python tools/extract_device_verdicts.py --out data/device_verdicts.json  # 只有带遥测的工作树才能重建这张表
```

`--verify` 的语义随树而变，这是刻意的：**有遥测就逐轮重新推导再比对，没有遥测就退回
"这轮还在、`panel_preset` 与记录一致"**，最后一行必须说明到底做了哪一种。在克隆里
输出 `(0 re-derived from telemetry, 653 checked against tracked metadata only ...)`，
在开发工作树里输出 `(653 re-derived from telemetry, 0 checked against ... )`。

### 8.1 为什么这一节在公开之后还改过

2026-11-27 对公开仓库做了一次匿名 `git clone --depth 1`，把上面每条命令在克隆里跑了一遍，
发现三条在工作树里绿、在克隆里红：

| 命令 | 克隆里的表现 | 原因与修法 |
| --- | --- | --- |
| `extract_device_verdicts.py --verify` | 653 行 `VANISHED …`，exit 1 | `collect()` 只 glob 遥测；克隆里遥测 0 份。改成按轮判断，无遥测时按 metadata 校验 |
| `scan_secrets.py --path cloud` | `clean: 1 file(s) scanned`，exit 0 | 路径不存在时 `read_text` 抛错被 `scan_file()` 吞掉；改成先 `exists()`，否则 exit 2 |
| `preset_low_bp.py`（无参） | 三条 `SKIP …not found` 后 exit 0 | 默认清单 `data/protocols/v4_batches/v4_p{5,6,7}a_manifest.json` 从未被跟踪；改成无清单时报错 exit 2 |

三条的共同形状是**"什么都没做，但退出码是 0"**。这类缺陷在开发工作树里永远看不出来，
只有从公开仓库克隆才能暴露——也只有在公开之后才会被第三方撞上。
