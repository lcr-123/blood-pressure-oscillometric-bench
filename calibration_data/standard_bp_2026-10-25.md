# Standard BP 台架采集记录（2026-10-25）

状态（最终复查后）：已保存 3 轮完整充放气日志，其中固件计算有效 2 轮、计算失败 1 轮；另有 1 次 ADS1115 离线中止。当前 120/80 配置的三轮波形试采已收齐，但不作为正式数据集或三次有效结果的重复性验收通过。最终泄压期间曾再次离线，随后复查 ADS1115 已在线，30 s 的 600 条外部压力样本均为 est=0.0 mmHg，泵关闭、阀2关闭；恢复原因未知，未证明故障已解决。BP Pump 2 自身活塞的 Stop 状态不能由串口确认。

## 配置与出处

- 非人体台架，沿用前一会话用户确认已接好的动态测试气路。
- 预期配置：Standard BP 120/80 mmHg、80 BPM、External Cuff；本会话未获得面板照片或实时面板确认，因此这些标签仅为沿用配置，发布前必须核实。
- 桥联握手：`ek.telemetry/v1`，`writeEnabled.serial=true`。
- 开始前设备回读：`RELAY_ONLY / IDLE / cal=VALID / ads=ONLINE / stream=ON / manual=OFF`。
- 校准回读：`slope=82.326mmHg/V intercept=-19.89mmHg zero=0.242V sens=0.0911V/kPa`；完整写入系数出处为同目录 `manual_static_2026-10-25.json`。
- 开始前压力 0.0 mmHg，PC0 LOW、PC1 LOW、PC8 HIGH、泵关闭。
- 本会话仅发送现有串口命令，无固件修改、编译或烧录；未更改现有接线或电源。

## 第 1 轮

- 原始桥联日志：`../tmp/standard_bp_20261025_1640_run01.ndjson`（文件名中的 1640 为命名标签，准确时间以记录内时间戳为准）。
- 指令：`target 150`，收到设备目标回显后执行 `start`。
- 固件停泵回显：`[Inflate] target reached 151.8 mmHg; stopping pump`。
- 外部 20 Hz 压力流观察峰值为 149.5 mmHg，低于控制回显峰值；两者采样时刻不同，不应混为同一测量。
- START 到 done：59.942 s；受控放气阶段：56.633 s。
- 放气阶段外部流首末读数：135.3 → 14.7 mmHg；1133 条样本。
- 整个 100 s 记录窗：1962 条解析样本；START 到 done：1199 条。
- 结果：`[BP] SBP=105 DBP=83 Pulse=75 bpm valid=1`。
- 调试回显：`n=2048 map=814(89.1) sbp=1(115.0) dbp=1(88.1) fft=1(1.3Hz/75bpm/m=0.3/n=0.0/t=0.1) ff=75`；该调试行尾与下一条 Pressure 文本发生拼接，原日志保留不改。

质量限制：`valid=1` 仅为固件计算标记，不代表参考准确性。`BP_ALGO_MAX_SAMPLES=2048`，`BP_Algorithm_AddSample()` 满缓冲后直接返回，故内部算法样本存在截断风险；外部压力流记录覆盖至 done，但不是内部 40 Hz 波形导出。桥联 `sampleRateHz=0`，仅按宿主时间戳描述观察速率，不把批量到达间隔作为 MCU 采样时序。External 模拟结果不能证明临床准确性。

收尾：发送 `vent`，3 s 窗口末值降至 1.3 mmHg；下一 3 s 窗口稳定 0.9–1.0 mmHg 后发送 `seal`。下一轮日志启动前已恢复 est=0.0 mmHg，并由 `pins` 确认 PC0 LOW、PC1 LOW、PC8 HIGH、泵关闭。

## 第 2 轮：故障中止

- 原始桥联日志：`../tmp/standard_bp_20261025_run02.ndjson`。
- 沿用 target=150，不调整算法、校准或阀参数。
- `start` 后出现：`[Safety] Pressure read failed during inflate; emergency vent`。
- 随后持续出现：`[ADS1115] Init FAILED address=0x48, check power/I2C/pull-ups`。
- 另发 `stop`，ACK 成功；设备回显 `[Safety] STOP PC0=LOW PC1=HIGH PC8=HIGH`。
- `pins` 确认 PC0 LOW、PC1 HIGH、PC8 HIGH、泵关闭。
- `status`：`EMERGENCY / cal=VALID / ads=OFFLINE / manual=OFF`。
- `fault`：`code=3 name=SENSOR_INIT`。该回读是在 STOP 后取得，最先发生的故障以原始 inflate read failed 日志为准。
- 为停止错误刷屏发送 `stream stop`，设备回显确认；再执行一次 `pressure` 仍初始化失败。
- 未再充气，未执行第 3 轮，未在传感器离线时声称压力已归零或擅自 seal。

## 第 2 轮中止时提出的人工确认（历史状态，后续恢复见下文）

1. 保持非人体，先看 BP Pump 2 独立面板，确认实际压力归零；如其 rolling piston 仍 Running，在面板按 Stop。控制阀命令不会停止测试仪活塞。
2. 当前阀2处于应急开放状态，须在确认压力近零后及时 `seal`，不长期通电开放；恢复充气前必须确认 PC1 LOW。
3. 先断执行器电源，再在断电状态检查 ADS1115 接头、供电/地线、SCL/SDA 是否松脱或短路。不要带电拔插或照抄旧文档传感器/供电参数。
4. 如需改接线或重上电，先核对所用模块正确型号的数据手册及电平兼容性；先断电查通断/短路，再上电测关键电压，最后才运行。接反、错接电源或逻辑电平可能损坏模块。
5. 传感器恢复后读 `pressure`、`cal`、`pins`，确认零点、校准有效和泵停，再 `stream start`；核对面板预设和实际气路后补采相同配置至少两轮。

当时阻塞是 ADS1115/I2C 通道持续不可用；具体是松线、供电还是总线故障，尚无证据定位。不能据此断言为软件问题。

## 16:44 复查与安全收尾

用户对面板 Stop / 归零请求回复「OK」后，先按桥联技能观察 5 s：100 条样本均为 est=0.0 mmHg，raw=1354–1358，sensor=234 mV。随后发送 `seal`，桥联 ACK 成功，`pins` 回读 PC0 LOW、PC1 LOW、PC8 HIGH、pump OFF，确认阀2关闭。

此时 `status` 已恢复为 IDLE / cal VALID / ads ONLINE / stream ON / manual OFF；单次 `pressure` 成功，`cal` 仍为 82.326 / -19.89。期间未发送 start、未烧录、未更改校准。恢复的原因及是否发生用户断电/复位未知，不能把此次恢复当作故障根因已解决。采集仍为 1 轮完成 + 1 轮失败；再次充气前需确认 BP Pump 2 已重新处于对应 Standard BP 模拟页面与正确 Cuff 配置。

## 用户确认模拟器就绪后的补采

用户对 `Standard BP 120/80、80 BPM、External Cuff` 模拟运行状态回复「OK了」，作为本次补采的人工配置确认；未提供面板照片或远程仪器读回。采集前 5 s 桥联观察为 100 条 est=0.0 样本；cal/status/pins 均正常，目标回显确认为 150 mmHg 后才发送 start。全程不改固件、校准或算法参数。

| 尝试号 | 原始日志（相对项目根） | 停泵回显 mmHg | 放气时长 s | 放气流样本数 | 固件输出 |
| --- | --- | ---: | ---: | ---: | --- |
| 01 | tmp/standard_bp_20261025_1640_run01.ndjson | 151.8 | 56.633 | 1133 | 105/83，75 BPM，valid=1 |
| 02 | tmp/standard_bp_20261025_run02.ndjson | — | — | — | ADS1115 离线，中止 |
| 03 | tmp/standard_bp_20261025_run03.ndjson | 151.7 | 54.621 | 1093 | calculation failed |
| 04 | tmp/standard_bp_20261025_run04.ndjson | 151.6 | 53.021 | 1061 | 112/78，84 BPM，valid=1 |

尝试03：START→done 为 57.910 s，全记录窗 2363 条解析样本，活动阶段 1158 条；外部流峰值147.6，放气流首末133.5→17.6 mmHg。调试 `n=2048 map=363(113.3) sbp=1(118.7) dbp=1(113.8)`。失败样本原样保留，不从统计分母删除。收尾 vent 后有效读数稳定至1.0，seal；下一轮前 est=0.0，pins确认PC1 LOW、泵OFF。

尝试04：START→done 为56.260 s，全记录窗2564条解析样本，活动阶段1125条；外部流峰值147.0，放气流首末134.8→17.7 mmHg。调试 `n=2048 map=699(83.8) sbp=1(122.6) dbp=1(83.5) fft=1(1.4Hz/84bpm/m=0.3/n=0.1/t=0.2) ff=84`。外部流与内部控制采样时刻不同，故其末读数可高于内部15 mmHg完成阈值。

质量结论：三轮完整波形中的计算有效率为2/3；把传感器中止也计入所有启动尝试，有效结果为2/4。不能只挑两次valid结果宣称重复性通过。三轮内部缓冲均到2048上限，须解决波形导出/采样完整性与故障稳定性后再做正式数据集。此次只是外部约20Hz诊断压力流，不是内部40Hz算法原始样本导出。

最终安全收尾：尝试04完成后发送vent，5s观察末值1.1 mmHg；之后ADS1115再次持续初始化失败，3s观察为0条样本。此后停止进一步充气并发送stream stop以停止刷屏。因传感器离线，未声称最终压力为0，未执行seal；已请用户在BP Pump 2面板Stop并确认独立压力为0，确认后立即关阀2。故障日志另存 `tmp/standard_bp_20261025_final_safety.ndjson`。掉线出现于放气收尾时，具体根因仍未定位，不能断定为电磁干扰或软件故障。

## 最终恢复复查与记录校验

承接上述异常，只读复查，不再发送 start、不再充气。先观察 5 s，100 条样本均为 est=0.0 mmHg；再记录 30 s 原始桥联日志 `tmp/standard_bp_20261025_closeout_confirm.ndjson`，其中 600 条样本均为 est=0.0 mmHg。设备回显：

```text
[Pins] PC0=LOW PC1=LOW PC8=HIGH pump=OFF
[Status] mode=RELAY_ONLY state=IDLE cal=VALID ads=ONLINE stream=ON manual=OFF remaining=0ms
[Cal] VALID slope=82.326mmHg/V intercept=-19.89mmHg zero=0.242V sens=0.0911V/kPa
```

因此最新实测为传感器恢复在线、压力估计归零、阀2已关闭，覆盖前述“待确认后关阀2”的历史状态。本次复查没有发送 seal，不能把现有关闭状态归因于助手的最后一次操作；是否发生人工操作或复位未知。BP Pump 2 的活塞是否停止仍需面板确认，vent/seal 不控制其活塞。

六份原始日志逐行 JSON 解析均为 0 错误。文件采用 PowerShell Tee-Object 生成的 UTF-16 编码，读取时须识别 BOM；以下 SHA256 针对原始文件字节，不应转码后照用。

| 日志 | JSON 记录数 | SHA256 |
| --- | ---: | --- |
| standard_bp_20261025_1640_run01.ndjson | 3376 | 05137D9872D24AEBE1EA22BC8F58437A0E378E330EEECD72F97B7B0221D86461 |
| standard_bp_20261025_run02.ndjson | 2364 | 43379D15AFBE31D10863822DBC31DB6F969F075EB14E90923430D87BC12688A1 |
| standard_bp_20261025_run03.ndjson | 4276 | 4D75D245935F31CF105421FE2256A07EA1F236C178988CFF0D3267D21EE9F71F |
| standard_bp_20261025_run04.ndjson | 4512 | 96004B9BCF81D66B1CE755FABFE15B1028569ED53A323581B4FE10C23441CEFA |
| standard_bp_20261025_final_safety.ndjson | 1343 | 30333F9B9A89D3A897528097FB41DE698DF1FF6E1D7BEE5C0C55312E473A2848 |
| standard_bp_20261025_closeout_confirm.ndjson | 1204 | C5147371F8491D7CEFA39366BC2B74908DEDD39EBBE6FE8D86407B75F7FAD55A |

本轮交付仅为该配置的诊断试采及故障留档，不是全部 Standard BP 预设矩阵。后续正式采集前应先处理间歇 ADS1115 离线和内部 2048 点截断，并实现可核验的内部波形导出；本轮未擅自修改固件。
