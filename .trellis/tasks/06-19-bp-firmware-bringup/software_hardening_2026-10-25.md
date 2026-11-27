# Standard BP 软件修复与非人体验证（2026-10-25）

## 最新软件交付：完整波形导出与生产 C 回放（尚未烧录）

`CAPTURE_EXPORT_20261025` 软件完成：逐主循环最多一行的 `bp.capture/1`
导出，包含完整内部采样、MCU tick、采集时校准/电压来源和完成计算的包络；
严格离线校验、CSV/NDJSON 输出与真实生产 C 回放。算法数值计算未改。
70/70 测试通过；Keil V6.22 为0错误/0警告，RAM63240/65536、余2296字节，
静态栈预算通过。本轮无下载、充气、接线供电或校准变化。
实板仍为此前 COOP 版本，新导出及运行时栈水位待验。
接线/操作/证据边界见 [验证说明](./capture_export_2026-10-25.md)。
下述19:40失败的完整内部波形未被记录，不能事后补造；直接拒绝条件已知，
选点根因仍待新数据。三轮有效 BP 重复性验收仍未通过。

## COOP 重复性首轮失败（19:40，第二轮未启动）

用户确认非人体External Cuff+真实袖带、120/80mmHg、80BPM、Running并回复
“就绪”，授权按先检查第一轮再启动第二轮的顺序复测。通过现有技能桥接运行
`python tmp/linkpad_lowpressure_check.py --standard`，未改固件、接线、供电、
校准82.326/-19.887、算法或安全门限；无需重新Keil编译/下载。本轮前只读5秒
100样本est均0.2；脚本独立status/pins/cal/fault与低压预检通过。

```text
[Inflate] target reached 151.4 mmHg; stopping pump
[Deflate] done; valve2 closed
[Capture] n=2177 capacity=2800 dropped=0 duration=54400ms interval=25ms
[BP] calculation failed
[DBGFAIL] n=2177 map=793(92.9) sbp=1(125.4) dbp=1(93.7)
[Calc] work=1581ms wall=2276ms max_step=31ms extract=1461ms smooth=89ms finish=31ms steps=568
```

停泵至放气开始1013ms。主机20Hz观测峰147.4mmHg与固件151.4采样时刻不同，
不作为独立仪表峰值。脚本STANDARD_COMPLETE=False、退出1，进入安全收尾。
本轮自然采集无溢出，但未产出有效BP，重复性验收失败，第二轮没有启动。
证据：`tmp/linkpad_standard_20261025-194047.ndjson`。

只读源码核对`bp_algorithm.c`的`calculate_result()`：SBP/DBP均找到；
DBP93.7>MAP92.9，满足现有合理性拒绝条件`dbp > map_pressure`，因此返回失败，
未输出补偿后的有效结果。这是直接拒绝条件。DBP搜索索引在MAP之后，袖带
压力却更高，说明所选两点的压力次序倒置；可能涉及压力起伏和包络特征选择，
但缺少本轮完整40Hz内部波形，不能确定噪声、气路、模拟器或算法哪项是根因，
不能仅凭20Hz遥测重建原始包络，也不能放宽顺序校验或套用补偿掩盖失败。

| 区间 | Pressure条数 | 最大主机相邻交付间隔 |
| --- | ---: | ---: |
| 全日志（预检、测量、计算和收尾） | 1456 | 84ms |
| 充气及hold | 62 | 60ms |
| 放气开始至done | 1089 | 51ms |
| done后至收尾stop | 60 | 84ms |

全日志无非正时间差或>200ms间隔。done时间戳1792928511452，前后Pressure
1792928511423/1792928511483，跨done60ms、done后31ms交付下一条。
最大84ms发生在1792928513676→1792928513760，跨失败结果/诊断输出。
max_step31<=50ms、交付84<=200ms，分别通过本轮时序目标；不能据此宣称
有效BP重复性通过，不能推断所有输入最坏界限。2秒新鲜度急停未放宽。
sampleRateHz=0仍表示未知，Capture的25ms配置及dropped0不等于外部40Hz
波形完整导出或独立测得的采样时序。

收尾stop→vent→新鲜低压→seal完成，首次实板使用修正后的
`pressure_after_ms`过滤，只有vent命令完成之后时间戳的样本参与收尾判定。
关阀前最后10条est为1.0×6、0.9×4，时间戳1792928516908…1792928517358，
均晚于固件VENT1792928514715；seal请求主机时间1792928517386.93。
最终pins为PC0/PC1 LOW、PC8 HIGH、pump OFF；cal VALID、ADS ONLINE、manual OFF，
ADS errors0/recoveries0、预期USER_STOP，target恢复50，日志末est0.7。
随后独立只读5秒100个样本est均3.7，不声称持续零点或独立压力表确认归零，
不自动再次vent或start。已提醒用户在BP Pump2面板单独Stop，面板是否按下尚未
由工具确认。接线及安全前提沿用本文件已有非人体流程，无新硬件建议。

与19:24比较：COOP自然完成采集两轮，分别n2057/2177、均dropped0，
max_step30/31ms、Pressure最大间隔80/84ms；有效BP只有19:24的118/68、84BPM，
19:40为失败，不能报告三轮有效结果范围或三轮重复性合格。19:33计算取消测试
不计入完整BP轮次，旧LINKPAD固件轮也不混入。当前任务继续in_progress。
下一步建议优先完整40Hz波形导出与离线回放，调查特征选点，再决定算法修改
和后续台架轮次；运行栈水位仍未测。此次只记录失败证据，不实现新功能。
以下早先章节的“未执行/待验证”均对应各自当时状态，以本节为最新状态。

## COOP 计算中stop（19:33，单个取消场景通过）

用户对“先计算中stop、再重复性”的下一步回复“OK，按你说的”。本轮先执行
计算中stop场景；不改固件、校准、接线、供电方案或算法。此前已让用户将
BP Pump2面板Stop，本场景只需真实压力采集和待计算任务，不依赖模拟脉搏；
面板实际状态未由串口独立读取，因此不把本轮计作120/80、80BPM重复性轮。
沿用非人体External Cuff+真实袖带，操作前5秒101样本均est0.9；独立预检
cal VALID/82.326/-19.89、ADS ONLINE/manual OFF、安全引脚及预期USER_STOP。

扩展既有主机脚本 `tmp/linkpad_lowpressure_check.py --calc-stop`，仅执行一轮：
target150→seal→start，保留165mmHg主机上限、2秒压力新鲜度急停、75秒采集
期限和自然结束后独立30秒观察期限；接收新鲜done后等待至少300ms再请求stop。
必须有本轮非零Capture/dropped0，停止回复主机延时<=200ms，随后5秒至少60个
新压力，且本轮任意时刻出现BP/Calc都拒绝判为取消通过；禁止自动重试充气。
初始5项离线模拟检查覆盖正常、提前完成、迟发结果、停止回复缺失及压力中断，
均通过后执行；这些模拟检查本身不证明实板安全或执行器响应。

实板结果：目标触发150.4mmHg、hold约1秒、自然结束Capture2353/2800、
dropped0、duration58800ms、interval25ms。done主机时间戳1792928056009，
stop请求1792928056396.64（done后387.64ms），固件DebugCmd STOP/Safety STOP
在1792928056557到达（请求后160.36ms、done后548ms）。160.36ms包括客户端
启动、桥接和串口/调度开销，不是单独测得的MCU中断/执行耗时。
后续5秒104个新鲜Pressure，整份日志1545条Pressure、最大交付间隔60ms、
无>200ms间隔；整份日志无BP/Calc输出。脚本CALC_STOP_COMPLETE=True、退出0。
证据：`tmp/linkpad_calc_stop_20261025-193307.ndjson`。

结合生产代码自然done后Begin、后续循环Step及之前完整计算2160ms的证据，
本轮支持待计算任务被stop取消且观察期内无迟发结果；未直接读取运行phase/
step计数，不声称覆盖EXTRACT/SMOOTH/FINISH每个边界、测得最坏停止延时或
永远不会有迟发结果。Capture计数与主机交付节奏仍不等于完整40Hz波形导出。

急停已经开启阀2，观察5秒后再次stop→vent→低压确认→seal。最后10个关阀前
压力均0.7mmHg，最终日志est0.1；PC0/PC1 LOW、PC8 HIGH、pump OFF，
cal VALID、ADS ONLINE、manual OFF，errors=0/recoveries=0，target恢复50。
EMERGENCY/USER_STOP为预期主动急停锁存。随后只读5秒100个样本est0.8–0.9，
不把该软件读数当独立仪表零点证明。BP Pump2活塞仍由面板单独Stop控制。

日志复核发现主机收尾细节：10个低压样本中3个在最后一次vent之前、但均在
先前stop放气之后（阀已开>5秒），其余7个在vent之后。原脚本清空Python
列表不能清空套接字内排队数据，因此不声称本轮有10个严格post-vent样本。
已修正poll接受pressure_after_ms过滤，收尾只计vent命令完成后时间戳的新
压力；维持35秒等待、<=1目标/<=2低残压收尾规则，不能用旧样本提前关阀。
新增排队旧样本回归连同原5项共6项通过，py_compile通过。该修正仅在离线
验证，未再加压；不借机重复硬件操作。主机文件不加入Keil，无需重新下载。

下一阶段：用户面板恢复已确认的120/80mmHg、80BPM、External Cuff Running后，
再做两轮完整COOP重复性；运行栈水位和完整40Hz导出仍待实现/验证。当前任务
保持in_progress，无HEAD，不生成混杂初始提交、不归档长期任务。

## COOP 首轮完整 Standard BP（19:24，流程与板上时序通过；重复性待验）

用户确认模拟器120/80mmHg、80BPM、External Cuff+真实袖带就绪并授权本轮。
沿用原接线、已恢复的82.326/-19.887校准和板上CAPTURE_SAFE_COOP_20261025，
通过技能桥接运行 `python tmp/linkpad_lowpressure_check.py --standard`。
预检status/pins/cal/fault及新鲜低压门通过，target150、seal、start；本轮
不修改固件、不重新下载、不调整算法或安全阈值、不更换接线供电。

固件报告152.0mmHg到目标停泵，hold约1秒，再自然放气结束：

```text
[Deflate] done; valve2 closed
[Capture] n=2057 capacity=2800 dropped=0 duration=51400ms interval=25ms
[BP] SBP=118 DBP=68 Pulse=84 bpm valid=1
[DBG] n=2057 map=970(86.0) sbp=1(128.8) dbp=1(73.4) fft=1(1.4Hz/84bpm/m=0.3/n=0.1/t=0.2) ff=84 pk=84
[Calc] work=1500ms wall=2160ms max_step=30ms extract=1385ms smooth=85ms finish=30ms steps=538
```

脚本STANDARD_COMPLETE=True、退出0。主机20Hz Pressure观测峰147.7mmHg，
不同于固件目标触发读数152.0；不把任一读数当独立仪表峰值或硬件压力上限。
相对模拟器设定，本轮差值为-2/-12mmHg、+4BPM，只记录偏差，不判定测量
准确性、ISO达标或临床有效。证据：`tmp/linkpad_standard_20261025-192443.ndjson`。

逐条解析RX Pressure文本的主机时间戳，包含计算和结果输出：

| 区间 | Pressure条数 | 最大相邻交付间隔 |
| --- | ---: | ---: |
| 全日志（含预检及收尾） | 1414 | 80ms |
| 充气及hold | 65 | 60ms |
| 放气开始至done | 1029 | 51ms |
| done后至收尾stop（计算及输出） | 57 | 80ms |

全日志无>200ms间隔、无非正相邻时间差。done时间戳1792927544507，前后
Pressure为1792927544479/1792927544539，跨done间隔60ms，done后32ms
即有下一条Pressure。全日志最大80ms发生在1792927546626→1792927546706，
跨越BP/DBG/Calc输出。首轮板上max_step30<=50ms、Pressure最大80<=200ms，
满足本轮时序验收；此前1858ms计算后交付间隔本轮未复现。2秒新鲜度急停
门限保持不变，不据单轮推断所有输入下都满足目标。finish实测30ms，仍是
独立完整步骤而非5ms硬上限；运行时栈水位尚未测量。
sampleRateHz=0表示设备未提供真实采样率；主机时间戳只证明本轮交付节奏，
Capture计数/25ms配置不等于独立实测40Hz时序，20Hz日志也不是完整波形导出。

脚本在启动前的唯一改动：保留75秒采集期限，收到自然done后仅一次开启
独立30秒计算观察窗口，必须同时收到BP和Calc才结束观察；成功还要求自然
done、非零Capture/dropped0与BP valid1。始终保留2秒新鲜度失败停止、165mmHg
主机上限及故障检查。Python py_compile通过；脚本是host-only工具，不加入
Keil工程，本轮无生产源码变化，因此未重复编译或下载。

收尾按stop→vent→连续10个新鲜压力<=1→seal执行，关阀前最后12条为
1.0…0.9mmHg；不是精确归零验收。随后确认PC0/PC1 LOW、PC8 HIGH、pump OFF，
cal VALID、ADS ONLINE、manual OFF，errors=0/recoveries=0；EMERGENCY/USER_STOP
来自主动收尾stop，非测量自主故障。target恢复50，日志末est0.6。之后通过
技能客户端只读5秒摘要取得101个样本、est全为1.6，故不声称持续零压，不盲目
重复开阀。阀2已关，BP Pump2活塞需用户在面板单独Stop。

当前仅完成COOP版本一轮完整板上验收；先前LINKPAD版本完整轮不替代当前
版本重复性。计算中stop取消迟发结果、当前版本重复性、运行栈水位与完整
40Hz波形导出仍待完成；本轮不自动追加充气。接线和非人体验证前提沿用本文件
已有流程，无新增硬件电压/连接建议。

## COOP 低压急停重测（19:17，通过；完整计算时序待验）

用户先回复“已恢复”，按原计划执行target50、首个新压力>=20时stop。
19:16首次尝试未在主机脚本5秒内达到触发点，脚本进入stop/vent/seal收尾，
退出1。用户随后明确说明“刚才忘记插电了”并要求重来；不把首次尝试记作
急停验收通过，也不把主机脚本deadline误称固件超时。该日志287个样本，
est范围0–4.5，末次3.3；这不证明气泵实际通电，也不据此推断传感器故障。
失败尝试证据：`tmp/linkpad_lowpressure_20261025-191609.ndjson`。

重测前5秒100个新样本均est0.1，保持校准82.326/-19.887与target50。
status/pins/cal/fault门通过，桥接写权限已开启。脚本重新seal/start，收到
`[Inflate] START PC0=HIGH PC1=LOW PC8=LOW`后按压力触发stop；收到
`[Safety] STOP PC0=LOW PC1=HIGH PC8=HIGH`，未出现target reached。
脚本ACTIVE_STOP=True、观察峰值26.2mmHg、退出0。
26.2是20Hz串口观测峰值，不是独立压力表峰值或硬上限；主机时间戳不代表
MCU采样时刻。目标值/超压保护/2秒新鲜度门限均未改。

收尾stop、vent，连续10个新样本各为1.0mmHg后立即seal，确认PC0/PC1 LOW、
PC8 HIGH、pump OFF；最终est0。cal VALID、ADS ONLINE、manual OFF，
errors=0/recoveries=0，EMERGENCY/USER_STOP为主动急停预期锁存。
Capture n=0/dropped=0：本次尚未进入放气采集，不评价算法或完整捕获。
重测日志：`tmp/linkpad_lowpressure_20261025-191708.ndjson`，444个样本，
最大相邻主机交付时间戳间隔58ms。随后独立只读5秒100样本est均0，
不把未用独立表核对的钳位零读数当作精确零点验证。

本次未改固件、接线、供电方案或校准；沿用前述接线/上电流程，无新编译或
下载。下一步需用户在BP Pump2面板确认Standard BP120/80、80BPM、External
Cuff+真实袖带并启动Running；模拟器此前确认Stop，不能假装已在输出脉搏。
就绪后按已记录target150流程测自然放气结束、Calc耗时和压力交付间隔。
计算中stop、重复性、运行栈水位和完整40Hz导出仍待完成，不自动追加充气。

## COOP 接续：恢复全擦丢失的校准（19:10，未充气）

上轮已展示完整命令并询问恢复校准，用户本轮要求“继续当前任务”。
通过 `ek-omniprobe-ai` 先读取5秒摘要并查询 status/pins/cal/fault，确认
IDLE、UNCAL、ADS ONLINE、manual OFF、PC0/PC1 LOW、PC8 HIGH、pump OFF，
fault NONE、ADS errors=0/recoveries=0。写权限由桥接 hello 确认 serial=true。
UNCAL 下 est=0 不作为有效校准后的压力证据。

仅恢复既有 `cal write 82.326 -19.887`，桥接 ACK 成功，固件确认
`[Cal] written+verified slope=82.326 intercept=-19.89 -> VALID`；随后独立
`cal` 查询读回相同参数及 VALID，-19.89为串口显示精度。未使用旧88.3参数。
写后再次查询，保持 IDLE/ONLINE/manual OFF、安全引脚、fault NONE；
ADS错误/恢复均0，Capture n=0/dropped=0。5秒摘要100个新样本 est均0，
raw1358–1361、sensor234–235mV；sampleRateHz=0仍表示内部采样率未知。
未用独立仪表复核压力，不能将软件钳位后的0当作精确零点证明。

证据：`tmp/coop_resume_20261025-191026.ndjson`，45秒只读观察已自行结束。
日志包含恢复前后固件回复。未重新烧录、未发送 start/pump/deflate/vent/seal，
未改变接线、供电、目标或算法。本次恢复后未做复位持久性实验。

下一步：用户现场按原已验证接法恢复执行器供电，保持非人体、BP Pump2
面板Stop并独立确认无残压。按本文件末尾“接线与非人体验证”继续：先断电
核对短路/极性/共地，恢复原供电后量关键点，再做target50低压stop测试；
不新增供电电压建议、不变更模块接线。串口无法确认执行器物理电源状态，
因此在用户回复现场恢复完成前不发送充气命令。计算期板上时序、计算中stop、
两轮Standard BP复测、运行栈水位与完整40Hz导出均仍待完成。

## LINKPAD 首次完整 Standard BP（18:10，通过单轮流程，重复性待验）

用户授权“OK，你充气放气吧”。沿用已确认非人体台架、原接线和校准，
运行 `python 'tmp/linkpad_lowpressure_check.py' --standard`；未修改生产固件。
fresh低压、VALID/ONLINE及安全引脚门通过后，target150、seal、start。
固件报告150.9 mmHg到目标停泵，hold约1秒，再自然放气结束：

```text
[Deflate] done; valve2 closed
[Capture] n=2521 capacity=2800 dropped=0 duration=63000ms interval=25ms
[BP] SBP=117 DBP=74 Pulse=75 bpm valid=1
[DBG] n=2521 map=916(93.2) sbp=1(127.2) dbp=1(79.8) fft=1(1.3Hz/75bpm/m=0.3/n=0.1/t=0.2) ff=75 pk=75
```

脚本STANDARD_COMPLETE=True、退出0。相对配置参考120/80、80 BPM，
本轮读数差为-3/-6 mmHg、-5 BPM；仅记录差异，不判定准确性达标或临床有效。
日志：`tmp/linkpad_standard_20261025-181059.ndjson`。

通信只读复核：1572个Pressure文本；其中放气开始至done有1261个，
最大相邻主机时间戳间隔55ms，本轮经过此前约94 mmHg中断点且未复现积压。
但全日志最大间隔1858ms，发生于done后的计算/输出区间：
Pressure最后一条1792923131764，Capture在1769，BP在1792923133596，
下条Pressure在1792923133622。与同步Calculate阻塞相符，但尚未实测MCU
计算耗时，不能认定因果；距2秒新鲜度门限仅142ms，不放宽安全门限。
OmniProbe升级与固件修正同时发生，不能据此证明USB/驱动根因或单独修正效果。

自然完成后stop -> vent -> 连续10个新样本<=1 -> seal，确认PC0/PC1 LOW、
PC8 HIGH、pump OFF；ADS ONLINE、errors=0/recoveries=0、cal VALID。
EMERGENCY/USER_STOP为收尾stop产生的预期锁存，不是测量自主故障。
target已恢复50；日志末est0.2，随后只读5秒100样本为1.8–1.9，故不声称
持续归零，不盲目反复vent。阀2已关；BP Pump 2活塞需用户另在面板Stop。

结论：已完成首轮自然结束且内部计数无溢出的采集；三轮重复性仍缺两轮，
运行时栈水位和计算期遥测裕量仍待验证。外部20Hz日志不等于完整40Hz波形
导出，不能据Capture汇总宣称开放数据集采集/导出完成。本轮不再自动加压。

## LINKPAD 低压急停验证（18:08，通过，Standard BP 待启动模拟器）

用户明确回复执行器供电“恢复了”。通过技能客户端保持原桥接，fresh零压
检查及 status/pins/cal/fault 安全门通过，target50、seal、start。逐条新压力
达到20 mmHg即发送stop（未等50目标），固件确认Inflate START后在
1792922890771执行STOP，未出现target reached；串口观测峰值30.6 mmHg。
这次证明了充气期间主机stop可以使泵关/PC0关/PC1开，不把采样触发阈值
当成瞬时硬限或串口观测峰值当作独立参考仪表峰值。

随后stop、vent均有固件回复；等待10个连续新样本<=1后seal（脚本允许的
最终安全收尾上限<=2，非精确零点验收），末次est=0。pins确认PC0/PC1 LOW、
PC8 HIGH、pump OFF；cal VALID、ADS ONLINE、manual OFF。EMERGENCY及
USER_STOP是本次主动急停的预期锁存；ADS errors=0/recoveries=0。
Capture n=0是尚未进入deflate即急停，不作为完整波形。

日志：`tmp/linkpad_lowpressure_20261025-180803.ndjson`；584个压力文本，
主机时间跨度29149ms，压力范围0–30.6。只读解析不等同40Hz算法导出。
辅助验证脚本 `tmp/linkpad_lowpressure_check.py` 仅通过批准的技能客户端
连接桥接，未改生产固件、接线、电平或算法参数。未触及94 mmHg位宽边界，
没有完成Standard BP；下一步需用户面板确认Standard BP / External Cuff并
启动Running（不能在已确认Stop状态假装模拟脉搏正常）。

## LINKPAD 下载后验证（18:04–18:05，尚未加压）

用户对下载安全前提回复“OK，直接开测”。以非人体、模拟器 Stop、气路
泄压、执行器断电为前提，UV4 -f 于18:04:22完成 Full Chip Erase、Programming、
Verify OK、Application running，退出0。启动读回
`CAPTURE_SAFE_LINKPAD_20261025 capacity=2800 deflate=200ms_open1ms`。
Flash日志：`tmp/linkpad_flash_20261025-180412.log`；只读观测日志：
`tmp/linkpad_postflash_20261025-180412.ndjson`（120秒自行结束，不占COM）。

全片擦除后实读 UNCAL；发送既有 `cal write 82.326 -19.887`，桥接ACK成功，
固件确认 written+verified -> VALID，并再次 cal 读回相同参数（串口显示
intercept四舍五入为-19.89，不代表写入了另一个值）。status=IDLE、ADS ONLINE、
manual OFF；pins=PC0/PC1 LOW、PC8 HIGH、pump OFF；fault NONE，ADS错误/恢复均0。
随后30秒摘要收到600样本，est全部0；sampleRateHz=0仍是未知。

未发 start/pump/deflate/vent/seal，未操作模拟器。本轮完成下载及断执行器
供电下空闲验证，不能声称通过94 mmHg边界或完成Standard BP。下一步需要
用户恢复原执行器供电后才能进行低压stop/vent测试，不在断电状态盲发充气。

## 通信格式兼容修正（代码完成，未下载，台架待验证）

用户已将 OmniProbe 更新到 3.2.2。本次只读桥接 5 秒收到 100 个样本，est
均为 0；sampleRateHz=0 表示未知，不代表已验证 94 mmHg 附近的通信边界。

两次失败前均从 ads 四位数进入三位数，原文本含 CRLF 恰由 65 变为 64 字节：
`raw=8031 ads=1004mV sensor=1385mV est=94.2mmHg VALID` 对应 65 字节；
`raw=7992 ads=999mV sensor=1379mV est=93.6mmHg VALID` 对应 64 字节。
这支持串口/USB 满包刷新相关假设，但尚无 USB 抓包或同版本 A/B 实测，
不能宣布 CH340 驱动根因已证实。升级与格式变更并存也会干扰因果归因。

- 生产代码仅改 main.c 压力格式：实际整行长度为 64 的整数倍且缓冲可容纳时，
  在 CRLF 前插入一个 ASCII 空格。未改字段值、20Hz 流、算法、校准或安全阈值。
- 新版本标记 `CAPTURE_SAFE_LINKPAD_20261025`。main.c 已在 uvprojx；
  新增 test/host/pressure_format_regression.c 不参与 Keil 构建。
- 新增测试基线先失败，修正后通过；另检查分析器兼容尾空格 VALID/UNCAL。
- 最终完整回归 53/53 通过（含 14 个真实C执行/解析兼容测试）；
  本工程无独立 Web lint/type-check，使用主机 C 编译、Keil 和合同测试验证。
- Keil 0 errors / 0 warnings；RAM 63168/65536，余量 2368；栈预留 4096，
  已知调用峰值 1192，含未知调用/中断的实际高水位仍待实测。
- AXF SHA256：`B0D399D90651EA1E478B900FAE733F1E2BB1A2D4ED4E045E8FB3141402C07798`。
  构建日志 `tmp/linkpad_build.log`。本次未下载、未写校准、未启动泵阀。

### 接线与非人体验证步骤

1. 保持现有已验证接线，不新增供电或电平配置：USART3 PB10 -> CH340 RX，
   PB11 <- CH340 TX，原共地保留；I2C1 PB6/PB7 -> ADS1115 SCL/SDA，AIN0
   仍接 MPXV5050GP 原分压链。PC0/PC1/PC8 为阀1/阀2/低有效泵继电器。
   本修改不要求改线或改变任何电源电压；重新接线需先查对应模块官方手册，
   断电检查短路/极性，再上电测关键点，禁止把未知 CH340 电平直接接 MCU。
2. 下载前重新请用户确认：无人接触袖带、BP Pump 2 面板 Stop、气路已泄压、
   执行器供电断开。旧轮次的确认不能代替当前物理确认。
3. Keil 打开原 uvprojx，Build（UV4 -b）零错误警告后 Download（UV4 -f），
   不使用 pyocd。检查启动及 status 标记、ADS ONLINE、泵关两阀关。
   若全片擦除清掉校准，先恢复 `cal write 82.326 -19.887` 并读回 VALID，
   不得使用历史传感器或旧校准值。
4. 执行器仍断电时观察至少 30 秒零压遥测；本步只检查启动与空闲传输。
   用户恢复原执行器供电后，先非人体低压 stop/vent 验证，再测 Standard BP。
5. 保持 External Cuff + 原真实袖带/气路及既定 150 mmHg 目标，模拟器由用户
   在面板设置并启动。保持 2 秒遥测新鲜度限制；重点记录 ads=1000 ->999
   附近的整行长度和宿主交付间隔。期望无长积压、自然 deflate done、完整
   Capture dropped=0 与 BP 结果；任一缺失不算成功一轮，需重新安全排查。
6. 每轮严格 vent -> 确认 est=0（或明确声明的低残压目标）-> seal，再核对
   PC0/PC1 LOW、PC8 HIGH；BP Pump 2 活塞需用户面板 Stop，不受 vent 控制。
   三轮完整采集与质量检查仍待完成，不作临床有效性声明。

## Bug Analysis: 遥测积压与64字节文本边界（根因待台架鉴别）

### 1. Root Cause Category

B 跨层契约、E 隐含假设、D 测试缺口：MCU 文本长度、USB/驱动读取、上位机
时间戳和 AI 桥接不是同一时钟/边界。已证实的是文本位宽边界，非驱动因果。

### 2. Why Fixes Failed

栈预算/溢出修复解决了真实独立缺陷，但不能据此假定遥测积压同时修好；
连续两轮 ADS 错误为零且宿主批量交付，需从单驱动层排查转向完整数据链。
空闲零压流不经过临界位宽，不能替代动态验证；升级上位机也不是修复证据。

### 3. Prevention Mechanisms

| 优先级 | 机制 | 动作 | 状态 |
| --- | --- | --- | --- |
| P0 | 运行安全 | 不放宽2秒新鲜度门限；异常停泵泄压后关阀收尾 | 保留 |
| P0 | 回归 | 真实生产C格式与解析器尾空格测试 | 已加入 |
| P1 | 端到端 | 相同上位机版本验证位宽边界及自然完成 | 待台架 |

### 4. Systematic Expansion

其余串口文本也可能受包/读取聚合影响，但暂无证据，不扩大修改所有日志。
长期导出应携带 MCU tick/seq，区分采样缺口和交付延迟；本轮不新增协议。

### 5. Knowledge Capture

已更新 capture-reliability.md 七节跨层合同及 implement.md。
无 src/templates/markdown/spec 镜像可同步。工作树无 HEAD，文件均属现有
未跟踪工作，保持不全仓提交；活动任务不归档、不标记完成。

## Standard BP 第2次尝试（17:44，同类中断复现，未完成）

用户明确要求继续下一轮。开始前 5 秒 100 个新样本 est 均为 0，查询确认
ADS ONLINE / cal VALID / 泵关两阀关，仅有前次主机 stop 的 USER_STOP 锁存。
保持非人体台架、原接线及校准，target 50 -> 150，seal 后 start；未改算法、
放气速度或安全门限。

- 固件约 2.06 秒到达 150.9 mmHg 自动停泵，hold 约 1 秒后进入放气。
- 再次触发主机 2 秒新压力超时，主动 stop。独立日志最大主机时间戳间隔
  2089ms：1792921520031（94.2 mmHg）->1792921522120（93.6 mmHg）；
  后一时间戳聚集 41 个样本，与第1次的 2129ms / 42 样本批量到达相似。
  两次中断前压力都约 94 mmHg，但尚不足以确定固件、串口或上位机具体根因。
- Capture n=973 / capacity=2800 / dropped=0 / duration=24300ms；ADS
  errors=0 / recoveries=0，无自主传感器故障记录，USER_STOP 来自主机中止。
- stop/vent 有固件执行回复，连续 10 个新样本 <=2 后 seal（当时 est=1.6）；
  最后 est=1.1 mmHg，pins=PC0 LOW / PC1 LOW / PC8 HIGH / pump OFF。
  已恢复 target 50。这是低残压收尾，不声称面板或传感器精确归零。
- 无自然 deflate done、无 BP 结果，第二次尝试仍不算完成一轮。
  不放宽安全门限，不继续反复加压；下一步先定位通信批量延迟。

原始日志：`tmp/safe_standard_20261025-1744_run02.ndjson`；独立只读观测器
PID=28344，计划 210 秒自动结束，不占用或绕过 EK-OmniProbe 的串口连接。
本轮未改固件、未重新烧录、未执行模拟器控制命令。

## Standard BP 第1次尝试（17:28，主机安全中止，未完成）

用户表示可以开始后，在新鲜压力为零、ADS ONLINE、cal VALID、泵关两阀关的
非人体台架上，将目标从 50 改为 150 mmHg，发送 start。未改校准、算法阈值、
放气速度或接线；未发送 BP Pump 2 原始控制命令。

- 固件约 2.36 秒达到 150.5 mmHg 停泵，hold 约 1 秒后开始放气。
- 放气过程中主机超过 2 秒未收到新压力样本，触发主机 stale pressure telemetry
  安全限制，主动 stop/vent。不是已证实的 ADS 掉线或固件自主保护。
- 独立原始日志：最后一批前 timestamp=1792920564516，下一批为
  1792920566645，间隔 2129ms；随后多个连续压力样本具有相同主机时间戳，
  支持串口/上位机/桥接批量延迟的可能，尚未定位具体环节。
- stop/vent 执行回复已确认；连续 10 个样本 <=2 mmHg 后 seal。
  pins 确认 PC0/PC1 LOW、PC8 HIGH、pump OFF；恢复 target 50。
- Capture n=909 / capacity=2800 / dropped=0 / duration=22700ms；
  ADS errors=0 / recoveries=0，fault=USER_STOP。样本数量和跨度与名义 40Hz
  相容，但不能替代内部逐样本 tick 证据，不能证明 MCU 完全无采样缺口。
- 本次没有自然 deflate done、没有 BP 结果，不算完成一轮；三轮验收仍未完成。

原始日志：`tmp/safe_standard_20261025-172857_run01.ndjson`。

接续检查发现封闭气路后存在约 3.5–5.3 mmHg 低残压；来源未确定，不改零点校准。
再次执行 vent，观察达到 <=2 后 seal；随后实时 est=0，pins 再次确认泵关两阀关。
独立 30 秒非加压观察记录 `tmp/safe_link_idle_20261025-1734.ndjson`：600 个样本，
est=0–0.1 mmHg，主机样本时间戳最大相邻差 51ms，未复现长空档。
sampleRateHz=0，以上仅为主机交付情况，不等同 MCU 采样周期或零点精度验收。
本次收尾命令的执行证据在工具回传中，不声称包含在后续 30 秒日志内。

当前不放宽 2 秒安全门限继续加压。后续先核对 BP Pump 2 面板 Stop/实际压力及
Standard BP / External Cuff 设置；模拟器活塞不受本设备 vent/seal 控制。

## 低压在线验证（2026-10-25 17:24，Standard BP 待执行）

用户回复 OK 后按原执行器供电已恢复继续。开始前再次观察 5 秒、100 个样本，
est 均为 0；status/pins/cal/fault 符合已校准、在线、无故障、泵关两阀关。
通过 AI 写权限发送 `target 50`、`seal`、`start`，未改校准或算法参数。

- 固件约 1.0 秒后报告 `target reached 50.4 mmHg; stopping pump`。
  串口 Pressure 流观测峰值为 49.1 mmHg（不等同内部峰值）。
- hold 约 1 秒后自动放气，结束时阀2关闭；Capture n=314、capacity=2800、
  dropped=0、duration=7825ms。低压且 BP Pump 2 Stop 条件下 calculation failed，
  不作为成人 BP 准确性验收。
- 主机脚本原计划在当前读数 >=45 时手动 stop，但批量消费遥测后检查当前值，
  错过峰值并走到 15 秒主机截止。故本轮证明自动目标停泵及 stop 命令可响应，
  **不声称已验证充气过程中手动 stop**，也不将脚本 deadline 误报为固件超时。
- 随后 stop/pins 确认 PC0 LOW、PC1 HIGH、PC8 HIGH、pump OFF；vent 后读数缓慢
  趋近 1.1 mmHg，未达到脚本最初要求的 <=1 mmHg，因此脚本以失败退出，
  保留泄压状态。未因该脚本结果自动提高充气目标或进入 Standard BP。
- 收尾重新独立读取 5 秒 101 个新样本，est 全为 1.1 mmHg。为避免阀2持续通电，
  明确使用低残压收尾目标 <=2 mmHg 执行 seal；这**不是零点检查合格**。
  pins 确认 PC0 LOW、PC1 LOW、PC8 HIGH、pump OFF。
- 最后 ADS ONLINE、errors=0、recoveries=0；fault=USER_STOP 为本次手动 stop
  产生的预期锁存，不是传感器故障；状态 EMERGENCY 未自动清除。

原始低压日志：`tmp/safe_lowpressure_20261025-172416.ndjson`（90 秒）。
末次 seal/pins/fault 发生在该观测器结束之后，证据为本次命令工具回传，
不谎称它们包含在该 NDJSON 文件中。

待现场核对 BP Pump 2 实测压力/单位及 Standard BP 120/80、80 BPM、External
配置与运行状态；未进行三轮 Standard BP、2048 点以上完整放气验证或运行栈水位验证。
接续时须重新读取新鲜压力、状态及引脚；未核对零点前不继续加压。

## 后续在线验证（2026-10-25 17:21，已烧录；充气测试待执行）

用户明确确认：仅连接非人体台架、独立确认无残压、BP Pump 2 已 Stop、
执行器电源已断开，并授权直接测试。此次未启动气泵或放气 PWM。

- 烧录前在线读取：IDLE、ADS ONLINE、cal VALID、fault NONE；
  PC0 LOW / PC1 LOW / PC8 HIGH / pump OFF，5 秒 100 个样本 est 均为 0。
- 再次通过 51 项主机测试及 RAM/栈预算门禁。
- 使用现有 Keil 工程执行 UV4 -f：Full Chip Erase Done、Programming Done、
  Verify OK、Application running，完成时间 17:21:22。
- AXF SHA256：`4560DB4A64ED861C2A226F6E903A0809349C53B14AE1295D1EC2E16ED94A389F`。
- 启动实测版本：`sw=CAPTURE_SAFE_20261025 capacity=2800`；ADS Init OK。
- 全片擦除后启动为 UNCAL；恢复原记录 `cal write 82.326 -19.887`，
  收到 written+verified，随后 `cal` 回读 VALID / 82.326 / -19.89。
  这是恢复原校准，不是重新标定或改变拟合参数。
- 烧录后 status/pins/fault 实测正常；ADSdiag errors=0 / recoveries=0；
  Capture n=0 / capacity=2800 / dropped=0，说明还没有实际放气采样。
- 8 秒观测收到 163 个样本（包含命令查询期间），est 均为 0；
  sampleRateHz=0，不将串口到达节奏当作内部采样周期。

证据：`tmp/safe_flash_20261025-172111.keil.log`、
`tmp/safe_flash_20261025-172111.ndjson`、
`tmp/safe_postflash_20261025-172150.ndjson`。

下一步须用户在现场按原接法恢复执行器供电、核对关键电压，BP Pump 2
保持 Stop；之后先做 50 mmHg 低压 stop 验证，再配置 Standard BP 三轮复测。
断电状态下不发送 start 假装完成压力验证；本次未完成动态掉线、截断或栈水位验证。

## 软件修复阶段结果（烧录前记录）

只改软件，未烧录、未发送气泵/阀门命令，未改接线、供电、Flash 校准、
放气速度或算法阈值。硬件正常是待验证前提，不是已经排除硬件故障。

- 去掉 Calculate 中约 8 KiB 局部数组；95 分位信号门控改为等价计数。
- 容量 2048 -> 2800 点（40 Hz 名义 70 秒），栈 1 -> 4 KiB。
  超限不再静默丢弃后继续出 BP：记录 dropped，SAMPLE_OVERFLOW 停泵泄压。
- Reset 清理全部诊断；Calculate 失败清除结果有效位；记录实际首末采样跨度。
- ADS 保留 HAL 状态、失败阶段/寄存器、错误码、SR1/SR2、恢复次数。
  读失败先返回，让上层先泄压；后续离线 Init 才完整重建 HAL/I2C1。
  失败不写出部分 sample；离线 stream 重试间隔 >=1 秒。
- `[Capture]` 报告完整性；修正成功诊断行的缓冲长度，避免 CRLF 被截断。

验证记录：

- `python -m unittest discover -s 'blood pressure monitor/test' -v`：51/51 通过。
- 其中 12 项 MSVC 主机测试运行真实 ADS/算法/控制 C，使用模拟 HAL，
  不访问串口。覆盖满容量、跨 tick 回绕、复位、超时、HAL_BUSY、恢复失败、
  保留诊断、读失败输出不变、充/放气故障与两类采样溢出泄压。
- Keil ARMCLANG 6.22 全量构建：0 Error(s), 0 Warning(s)。
  Code=45736, RO=5004, RW=28, ZI=63140；SRAM 共 63168/65536，余 2368。
  4096 字节栈已包含在 ZI 中；callgraph 已知最大 1112 字节，仍有
  Unknown(Cycles, Untraceable Function Pointers)，未实测栈水位。
- `python 'blood pressure monitor/tools/check_firmware_budget.py'` 通过；
  RAM 余量至少 2048，已知栈峰值 +1024 预留 <=4096。
- main.c / ads1115.c / bp_algorithm.c / bp_control.c / startup 已在 uvprojx；
  无新增固件编译单元。test/host 是主机替身，绝不可加入 Keil 包含路径/源组。

## 接线与上电前置（保持原接法，不新增电压建议）

本轮不重新接线、不调整电源。涉及 I2C1 PB6=SCL、PB7=SDA -> 现有 ADS1115；
现有 MPXV5050GP 经已校准分压进入 AIN0，ADDR 接法保持 0x48。
USART3 PB10=TX -> 现有 CH340 RX，PB11=RX <- CH340 TX，115200/8N1。
PC0 阀1、PC1 阀2、PC8 气泵低有效继电器控制；此处是信号映射，
不是允许 MCU 直接连接泵/线圈。

电源与地：沿用已确认的模块供电、驱动级、共地和电平转换，不交叉混接
电源输出。具体额定/绝对最大电压、电平兼容性须以完全一致型号的官方手册
和实测为准；本轮未重新查证这些参数，不据此更改任何供电。
接反极性、短接电源或把不兼容逻辑接入 MCU 可损坏模块/MCU。

上电顺序：先彻底断电，用通断/电阻/二极管档排除短路并核对极性与共地；
随后仅给控制/传感器部分上电，执行器电源断开，量关键供电与 I2C 空闲电平，
与已确认记录/官方手册对照；全部符合后再做无人体运行验证。
任何改线均在断电且气路已独立确认泄压后进行；不要带电拔插 I2C 造故障。

## 编译、下载与无执行器检查

1. BP Pump 2 面板 Stop，气路独立确认无残压，无人体连接。执行器供电保持断开。
2. Keil 打开 `blood pressure monitor/MDK-ARM/blood pressure monitor.uvprojx`，
   Rebuild 全工程，确认 0 错误/0 警告；运行上述预算脚本与测试。
3. 确认安全后用 Keil Download（或 UV4 -f）下载；不要使用已知不兼容的
   pyocd 流程。本轮没有替用户执行这一步。
4. 串口检查启动版本 `sw=CAPTURE_SAFE_20261025 capacity=2800`，
   ADS Init OK；`pins` 预期 PC0 LOW、PC1 LOW、PC8 HIGH、pump OFF。
   以逻辑仪/万用表验证控制输出，不只看串口文字。
5. `cal` 应回读 82.326 / -19.89（显示精度）且 VALID；来源为
   `calibration_data/manual_static_2026-10-25.json`。仅在下载清掉记录且确认
   传感器/分压未改变时重写 `cal write 82.326 -19.887`，再读回。
   不要使用旧 88.3 / 84.054 / MPXV7007 参数。
6. `pressure` 应有实时 raw/ads/sensor/est；近零与独立参考一致后，
   `vent` -> 确认压力近零 -> `seal` -> `pins` 确认 PC1 LOW。
   若 ADS 离线，不能据旧值宣称已归零，须独立仪表确认泄压。

## 非人体低压与 Standard BP 复测（下一步，尚未执行）

1. 控制/传感器检查通过后断电，恢复原执行器供电与原气路，先测电压再运行。
   只用现有 External Cuff + 真实袖带/非人体容积台架，严禁连接手臂。
   常开口封堵、管路与量程沿用已验证配置，BP Pump 2 单位需核对
   （Standard #1 面板 16.0/10.7 kPa 即 120/80 mmHg）。
2. 先 `target 50` 做低压流程及 `stop`：应先停泵、PC0 LOW、PC1 HIGH 泄压，
   主循环不再产生放气 PWM。压力与独立表一致，无意外复位；然后
   `vent` -> 实测近零 -> `seal`。低压不要求算法给出有效成人 BP。
3. 低压通过后恢复上轮相同 Standard BP 配置（120/80、80 BPM、External），
   `target 150`，保存串口原始日志并开 `stream start`，执行一次 `start`。
   预期到目标停泵、hold 1 秒、开始放气，结束时 `[Deflate] done; valve2 closed`。
   `[Capture]` 应 dropped=0、n 不再固定截在 2048，时长覆盖完整放气段。
   若 n=2800 且 dropped>0，该轮明确失败并泄压，不通过加速放气掩盖。
4. 采集后检查 `[BP]` 或 `[BP] calculation failed`，独立记录参考设置、
   波形与诊断；不能把“有结果”当作准确性合格。至少连续三轮无掉线/复位/
   截断，并检查近零及重复性，才评估是否恢复正式采集。
5. 如再出现掉线，保存最早 `[ADSdiag]` 与 `[Fault]`：
   stage 2 探测、3 指针写、4 接收、5 启动转换、6 等待转换超时、7 恢复。
   后续 Init OK 不应清除之前快照，也不得自动重新启动泵。
   故障注入优先用已提供主机模拟，不能带压/带电拔线。
6. 每轮收尾：`vent` -> 参考/实时传感器确认近零 -> `seal`；
   BP Pump 2 活塞另在面板 Stop。测量结束时关阀不等于残压为零。

## 剩余边界

2800 点不是无限采集；完整 40 Hz 原始波形导出尚未实现，20 Hz Pressure
日志不能等同内部波形。现有固定 MAP 窗口及 SBP/DBP 经验补偿未改，仍可能
造成计算失败/参考偏差；需独立数据评估，模拟器验证不等于临床验证。
台架验证和运行时栈水位未完成，不将 ADS 离线根因认定为已解决。
长期 bring-up 任务保持 in_progress；仓库无 HEAD、大量已有文件未跟踪，
未创建混杂初始提交，未归档长期任务。

## Bug Analysis: stack budget / silent truncation / lost ADS evidence

### 1. Root Cause Category

D（测试覆盖缺口）+ E（隐含假设）+ B（跨层契约）：编译通过不代表 1 KiB
栈容纳得下 8 KiB 局部数组；AddSample void 无法通知调用者已丢低压尾段；
HAL 错误统一折叠与立即 PE 切换丢失了诊断和安全顺序。

### 2. Why Fixes Failed

不臆测此前每次失败的因果。只调阈值/延长采集无法消除栈预算和静默满缓冲；
PE 开关不等于完整重建 HAL 句柄，且不能证明已修复物理总线问题。

### 3. Prevention Mechanisms

P0 已完成：去大栈数组、RAM/栈门禁、AddSample 返回值+全调用点安全处理。
P1 已完成：真实 C 主机故障测试、持久失败快照、先泄压后恢复、捕获统计。
P1 待完成：目标板非人体三轮复测与栈水位/采样时间质量测量。

### 4. Systematic Expansion

检查了 main 与两个 bp_control 采样入口，保留终态 continue/break，避免 PWM
覆盖泄压。后续扩容必须统一评估全部数组、FFT、启动栈和链接区域；正式数据
导出需独立设计，不将诊断流冒充原始数据集。

### 5. Knowledge Capture

已更新 core/capture-reliability、safety-rules、quality-guidelines 与 index。
本仓不存在 src/templates/markdown/spec 模板副本，无需创建伪模板目录。
无 HEAD 且含大量用户未跟踪文件，不为流程创建混杂初始提交；本记录保留审计。
## Cooperative calculation increment — 软件完成，台架未验证

版本 `CAPTURE_SAFE_COOP_20261025`。本轮仅修改、主机测试、Keil编译；
未下载、未充放气，未改变接线、校准、采样间隔、算法阈值/补偿、放气速度
或宿主2秒新鲜度门限。不得将本次构建称为1.86秒空档已实测消除。

实现：Begin/Step/Cancel；提取与平滑每批最多8点，每点后检查5ms让出目标；
最后特征/FFT单独测时，尚无5ms硬上限。两个采集调用方均协作执行；停止、
重置、执行器覆盖、校准变更、诊断ADS故障作废待计算结果，避免迟发BP。
新增 `[Calc] work/wall/max_step/extract/smooth/finish/steps`，算法不打印/喂狗。

验证：59/59测试通过（含冻结旧循环的逐位包络/平滑等价、多长度成功/失败
结果与特征诊断等价、计时回绕、批次限制、各阶段取消/重启、主循环真实C
输出一次/取消不输出、控制路径取消、安全静态合同）。Keil日志
`tmp/coop_build.log`：0错误/0警告，Code45928 RO5108 RW28 ZI63180。
RAM63208/65536，余2328；栈4096，已知峰1192，额外1024保留通过；
未测运行时栈水位。生产文件已在uvprojx；无新增固件源文件，主机测试不入工程。

### 接线与非人体验证（下一轮，未执行）

1. 不改现有已确认接线：I2C1 PB6/SCL、PB7/SDA至ADS1115；现有传感器
   输出经已确认前端至AIN0；USART3 PB10/TX、PB11/RX至既有CH340交叉连接；
   PC0/PC1阀驱动、PC8低有效泵继电器维持原接法，不将线圈直接接MCU。
   供电、逻辑兼容、极性/共地沿用已核实方案；本次不提出新电压或改接建议。
2. 不接人体，BP Pump2面板Stop、气路已泄压、执行器电源断开。先断电检查
   通断/短路/极性，再仅上控制和传感器电源测现有关键电源点与地线；确认后
   才恢复执行器。若要变更模块或供电，先按对应官方手册重新核实；接反可能
   损坏器件。现有External Cuff+真实袖带保持，不换Internal Adult。
3. 用户确认上述条件后，在Keil打开MDK-ARM的uvprojx，Rebuild确认0错误/
   0警告，再Download（本轮未执行；勿用pyocd）。启动须见COOP版本、泵OFF
   安全引脚与ADS在线。`cal`读回当前82.326/-19.887；只有全擦导致丢失才重写
   `cal write 82.326 -19.887`再读回，禁用历史88.3/-19.96。
4. 先target50的非人体低压stop验证，再做自然结束与计算中stop测试（分开轮次）。
   预期两批之间继续收到新Pressure、stop后无迟发BP，故障不自启动泵；计算
   成功/失败只输出一次。记录Calc各字段与全程宿主Pressure间隔，尤其done到
   下一条Pressure；目标单步<=50ms、交付间隔<=200ms，均尚未达成实测。
   finish或结果串口输出超标须继续拆分/评估，不放宽2秒安全停止门限。
5. 通过后再补两轮Standard BP重复性；捕获n/dropped/时间、BP/参考设置、
   ADS错误/恢复和最大交付间隔。每轮vent→连续新样本确认目标（零点需<=1且
   参考表确认）→立即seal，不把低残压当零点；读数失效时以独立仪表确认。
   模拟器活塞须另在面板Stop。20Hz诊断流不能替代内部40Hz原始波形导出。

### Bug Analysis: post-capture主循环阻塞

1. Root Cause Category：E隐含假设+D测试覆盖缺口。原同步全量包络计算阻塞
   命令/新ADS遥测；假设计算足够快未获板测支持。日志1858ms位置吻合，
   但USB/驱动贡献及MCU实际时长仍未知，不分配虚构因果概率。
2. Why Fixes Failed：记录长度规避只针对64字节交付边界，不能解释/消除全部
   计算期空档；没有证据将先前改动一概判为无效。本轮初测两处失败是测试
   输入未跨20mmHg、mock tick差期望写错，纠正测试而未改生产阈值。
3. Prevention：P0协作批次/全调用方取消已做；P1位等价/真实main测试/耗时诊断
   已做；P1板上最终FFT步骤、串口日志、急停响应及栈水位待测。
4. Systematic Expansion：同步兼容入口保留但禁止采集调用；不在算法喂狗；
   如finish或输出仍长，依据阶段计时扩展，不能假设所有Step都<=5ms。
5. Knowledge Capture：已写capture-reliability七部分合同；本仓无模板副本。
   无HEAD且用户文件大量未跟踪，不创建混杂初始提交；长期bringup不归档。

