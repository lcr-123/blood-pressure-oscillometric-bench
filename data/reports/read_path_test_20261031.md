# 读取路径隔离测试：2026-10-31

已实现、编译、下载并完成一轮非人体板上静止验证。根因仍未完全定位。

## 结果

| 对照 | 结果 | 能说明的范围 |
| --- | --- | --- |
| 真实生产 C 主机模拟升压至100 mmHg、停泵保持、事务故障注入 | 通过 | 测试输入下的配置、数据拼接、换算、目标停泵、保持及错误处理正常 |
| 新固件板上密封零压，泵阀静止，25 ms读取、持续10秒 | 400次成功，ADS错误0/恢复0，UART错误0 | 相同读取频率本身未复现故障 |
| 此前外部BP Source约100 mmHg静压 | 未增加ADS错误 | 外部静压下能持续采样；该次为旧镜像，不是严格同镜像实验 |
| 此前内部泵目标100 mmHg | 回显101.6后保持期失读，急停放气 | 故障与内部泵阀切换条件相关；不单独证明泵损坏 |

现有证据缩小了普通读取、换算和频率错误的嫌疑，但不能排除真实外设时序下的软件驱动问题。
主机假的HAL不模拟STM32全部寄存器/电气行为。仍需区分负载切换的供电/地线/干扰、
I2C线路与STM32外设/驱动时序；不能把静止PASS记为问题已修复。

## 已写测试

- `blood pressure monitor/test/host/read_path_regression.c`：编译实际`ads1115.c`，
  提取实际主循环充气/保持及新诊断函数体；校验地址0x90、配置字0xC383、8 ms就绪、
  有符号原始码、大端拼接、量程/分压及校准；模拟0→100、目标停止和保持读取。
  在五个事务位置分别注入HAL_ERROR/BUSY/TIMEOUT，共15种组合，断言失败不改输出样本、
  不在ReadSample内恢复、活动保持先取消及停泵/关充气阀/放气再打印。
  另测转换超时、时钟回绕、慢循环、首错、引脚/压力/校准/新鲜度门限及显式取消。
- `blood pressure monitor/Core/Src/main.c`：新增串口`readtest`，10秒、25 ms间隔，
  泵阀静止、无GPIO写入、无掩盖失败的重试；>=380次成功才打印PASS_READ_ONLY。
  首次ADS失败打印FAIL_ADS及诊断；引脚变化/压力越界/采样不足分别失败。
  `stop`/`vent`/`seal`取消测试，不输出成功。活动测试阻止其他采集、校准、扫描、导出。
- `tmp/bp_read_path_board_20261031.py`：经EK TCP8765预检、下载、只在UNCAL恢复
  既定校准、运行诊断、记录元数据和完整串口；复用已有卸压/新鲜零压/密封收尾。

## 构建与软件验证

- 全套114项通过，29.535秒：`blood pressure monitor/MDK-ARM/test_read_path_20261031.log`。
- 完整Rebuild零错误零警告：`rebuild_read_path_20261031.log`；随后补充help提示，
  `build_read_path_help_20261031.log`仍零错误零警告。help文字不改测试逻辑。
- `check_firmware_budget.py`：RAM63488/65536，余2048；预留栈4096，已知调用峰值1392+额外1024通过。
- 未新增/移动生产C/S文件；主机测试源码不进入Keil固件工程。
- 新镜像标识`READ_PATH_TEST_20261031`，HEX SHA256：
  `5862023c617a7614fece0d7c27d4542bf6d62b9175385d446559b5cd8151b181`。

## 下载及板上实测

沿用用户“烧录直接烧，不用老是问我”的明确授权。下载前保存旧故障，核对连续新鲜VALID零压、
ADS ONLINE、泵OFF及PB8 HIGH/PC1 LOW/PC8 HIGH；完成vent→约3秒连续新鲜零压→seal，
并观察约5秒不回压。未获得负载电源断开证据，不记为断电试验。

Keil现有uvprojx通过UV4 -f于16:52:09完成Full Chip Erase/Programming/Verify OK/Application running，
exit0。从实时启动行核对新固件。全擦导致UNCAL，写入`cal write 82.326 -19.887`，
写入验证并再次读回VALID/82.326/-19.89。校准、分压、目标及ADS设置未调参。

串口实测：

```text
[ReadTest] START 10000ms interval=25ms sealed-zero NONHUMAN
[ReadTest] PASS_READ_ONLY n=400 elapsed=10000ms last_raw=1296
[Fault] code=0 name=NONE age=0ms
[ADSdiag] ... errors=0 recoveries=0
[Status] mode=RELAY_ONLY state=IDLE cal=VALID ads=ONLINE stream=ON manual=OFF remaining=0ms
[UART3] rx_errors=0 rx_state=0x22
[Stack] used=1224 free=2872 reserved=4096 saturated=0 ...
```

诊断期间另有201条约50 ms串口显示样本，raw1295..1298、sensor223..224mV，估压均0。
400为MCU转换成功计数，201为主机接收的显示记录数；串口到达时间不能替代MCU采样时钟。
估压在零点有截断，不代表未截断压力完全不变。测试没有完整波形导出或独立压力真值。
栈水位仅覆盖本次诊断路径。

结束再次vent→60条连续新鲜近零→seal；随后约5秒99条新鲜VALID样本均0，
raw1292..1296，最终PB8 HIGH/PC1 LOW/PC8 HIGH、pump OFF。未启动气泵或新充气轮次。

## 接线与复现

无接线变更。按当前《血压仪完整接线方案》保持MPXV5050GP经现有分压接ADS1115 AIN0，
VDD3.3V、ADDR=GND/0x48、PB6=SCL/PB7=SDA，共地；USART3/CH3401152008N1。
PB8低有效充气阀、PC1高有效放气阀、PC8低有效泵。非人体，P2通大气。
实际改线前先查对应官方手册、断电查通断；继电器先断电，MCU先上电。

Keil打开`blood pressure monitor/MDK-ARM/blood pressure monitor.uvprojx`，Rebuild要求0错误0警告，
再下载并Verify OK，核对boot身份、cal/pins/fault。全擦仅恢复上述既定校准。
新鲜VALID压力0..1、ADS在线、无活动采集/计算且安全密封引脚满足时发送`readtest`。
预期10秒后PASS_READ_ONLY且n>=380、无新增ADS错误/恢复；任何FAIL/REJECTED均不通过。
完整收尾固定vent→连续新鲜近零→seal→观察无回压。ADS离线不能凭旧样本密封，应独立卸压。

下一步需做有明确接线和供电状态记录的负载隔离对照；不能再用重复充气代替根因定位。
本报告仅完成测试实现与静止对照，总任务仍in_progress。

## 证据

- 原始串口：`data/raw/preflight/read_path_board_20261031-165145.ndjson`。
- 元数据：同名`.metadata.json`。
- 原始SHA256：`a847866fdc77325d407615360b58ce8969446e0af32d55c1c61f63607d74c4d7`。
- 下载日志：`blood pressure monitor/MDK-ARM/download_read_path_20261031-165145.log`。
- 旧内部100试验：`data/raw/development_20261031/internal_target100_20261031-163559.metadata.json`。
- 旧外部静压：`data/reports/external_static100_20261031-162647.md`。
