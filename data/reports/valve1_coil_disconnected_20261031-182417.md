# 2026-10-31 18:24 阀线圈断开、继电器单次开闭：未复现

用户确认完全断电后断开充气阀一根供电线并绝缘，随后按先MCU、后继电器及负载电源的要求回复ok。上述物理状态来自操作者反馈，未独立测量断线、供电电压或继电器触点/机械动作；二极管位置和实际抑制效果仍未独立验证。

## 方法与结果

- 使用EK TCP8765桥接，serial write permission true；初态IDLE/NONE、ADS ONLINE、cal VALID 82.326/-19.89、manualOFF、UART0、ADS errors0/recoveries0、安全引脚。
- 切换前5秒100条新鲜VALID估压0，raw1312..1317。
- 一次holdopen -> 宿名义250ms观察 -> close；回显PB8 LOW->HIGH、PC8始终HIGH；没有start/open，没有启动泵、改变目标、校准、固件或重启设备的命令。实际GPIO脉宽未测量。
- 切换后5秒100条新鲜VALID估压0，raw1309..1314；没有乱码、失读或重启文本。ADS errors/recoveries仍0/0。
- 收尾vent ->60条连续新鲜VALID零压跨2949ms ->seal；封闭后5秒100条零压，最终IDLE/NONE/ONLINE/manualOFF、UART0、ADS0/0、PB8 HIGH/PC1 LOW/PC8 HIGH、pumpOFF。
- 共379条有效新鲜显示样本；sampleRateHz=0，不能以宿主串口到达间隔宣称真实采样周期。

## 结论及限制

本轮只通过“操作者报告阀线圈断开条件下的一次继电器开闭”对照，未验证带载修复。与18:10、18:13带线圈时关阀触发失读相比，进一步支持充气阀线圈带载切换路径相关性；仍不能区分线圈反冲、触点拉弧、供电/地线耦合与受电气扰动触发的I2C状态问题，也不能据此断言阀损坏或纯软件无缺陷。

用户补充照片中的左侧实际接NO而非COM；应保留此更正，不将此前口述COM作为错误接线证据。面包板导通、二极管器件及线圈端实际抑制效果仍需独立验证。

保持充气阀断线端绝缘；测试结束时未要求或执行新的断电，不能声称12V已断开。下一步涉及移动线或器件时，仍需完全断电卸压。

## 证据及检查

- Raw: `data/raw/development_20261031/valve1_coil_disconnected_20261031-182417.ndjson`
- Metadata: 同名 `.metadata.json`。
- Raw SHA256: `effd14f928dc5df1e8e96fab5b54ca52195df724185d8dd3ff286feb67646597`
- Runner: `tmp/bp_valve1_diode_20261031.py --coil-disconnected`
- Runner SHA256: `e9367272ff4562c57dd5bcd50d7d6cdad84d3e7d44e6ff110f7e8725b2f8096d`
- 仅为现有runner增加隔离配置和准确元数据，复用HoldBridge及stable closeout；语法与既有guard三项回归通过。
- 原始审计确认一次开闭、无start/open、所有诊断计数0、无失败/乱码/Boot、收尾顺序/新鲜零样本及hash匹配。
- 无生产固件变化，无Keil编译/下载。任务保持in_progress。
