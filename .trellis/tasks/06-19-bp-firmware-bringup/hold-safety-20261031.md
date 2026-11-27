# 到压等待期故障保护修复与验证

状态：软件修复、主机回归及 Keil 编译通过；已下载并完成负载断电静态预检。
14:54 带负载复测因通信中断失败并人工收尾。恢复后15:06再次复测，等待期ADS故障
触发保护，未出现PWM启动，完成vent->连续新鲜近零->seal。保护取得本轮实物运行
证据，但底层ADS故障仍在，健康低压采集未通过。
固件标识：`HOLD_SAFETY_20261031`。

## 修复依据与行为

只读审计 `data/reports/ads_switching_audit_20261031.md` 证实：到压后的
1000 ms 等待期出现 ADS1115 读取失败，旧代码仍可能启动自动放气 PWM。
本次修复控制流程，不据此认定供电、电磁阀或 I2C 的物理故障原因。

- `ManualPump_TimeoutTask()` 在充气和到压等待期均按既有 25 ms 调度采样。
  这是协作主循环的调度间隔，不是包含 HAL/UART 延迟的严格墙钟时限。
- 等待期保留超压保护，但不再进入充气目标分支，避免反复延长等待计时。
- 读取失败时先使样本无效，取消等待、PWM、SysTick 脉冲与计算，再走既有
  紧急停止：泵停、充气阀关闭、放气阀打开，记录 SENSOR_READ，最后打印诊断。
  失败读取的尝试时间用于延后离线重试，避免同轮流输出马上恢复总线。
- 等待期串口流输出复用安全采样缓存；`stream stop` 不会停止安全检查。
- 等待期 `pressure` 查询遇到离线状态先取消并放气，不先重初始化；查询读取
  失败同样取消并放气。`seal` 已取消等待之后，空闲诊断失败仍只记录故障。
- 到压时先停泵、关闭充气阀，再输出到压日志。算法、校准和 PWM 参数保持原值。
  更新固件标识用于区分此次保护版本。

## 验证证据

主机测试提取并编译实际 `main.c` 函数、实际 `bp_control.c` 故障记录及紧急停止
函数，模拟 ADS、时钟、UART 和 HAL 边界；实际主循环等待转 PWM 分支也参与执行。
覆盖 HAL_ERROR/BUSY/TIMEOUT、串口流开/关、等待中及到期瞬间失败，并断言：
取消先于 GPIO、停泵/关充气阀先于开通气、放气先于日志或恢复、后续不启动 PWM。
另覆盖健康等待的采样频率、缓存复用、固定截止时间、单次查询故障、离线查询、
seal 后空闲失败不改 GPIO、超压、正常到压停止先于日志。

- 全套 `python -m unittest discover -s 'blood pressure monitor/test' -p 'test_*.py' -v`：
  **111/111 通过**，最终运行 35.253 s。
  日志：`blood pressure monitor/MDK-ARM/test_hold_safety_20261031.log`（UTF-8）。
- Keil ARMCLANG V6.22 Rebuild：**0 errors / 0 warnings**。
  Code=53320，RO=8120，RW=32，ZI=63440。
  日志：`blood pressure monitor/MDK-ARM/build_hold_safety_20261031.log`。
- `check_firmware_budget.py`：RAM 63472/65536，余 2064 字节；栈预留 4096，
  已知调用链峰值 1352，加 1024 保留后通过。本版本空闲及诊断路径运行时
  水位 used=1424/free=2672/saturated=0；动态采集和计算路径尚未验证。
- 全部 `Core/Src/*.c` 已登记在 uvprojx；新增 host 测试文件未加入 Keil。
  本次没有新增或移动生产 `.c/.s` 文件。
- HEX：`blood pressure monitor/MDK-ARM/blood pressure monitor/blood pressure monitor.hex`
  SHA256：`f402fd49740f8416ff28e5c3803802ae3efc505ec3ddd66b48f99f67426667b4`。
- main.c SHA256：`660874ea1c6d5bb80f83183f47471d147f2d4c674b1a302bb9f285510a68d531`。
  bp_algorithm.h SHA256：`d03512dcb9cd640045a980b5a3ab9844dbcef5e1069f6d547524ca04e3ddc8e4`。

## 接线、下载与非人体复测步骤

本次沿用 `血压仪完整接线方案.md` 的现有连接，不迁移引脚：ADS1115 AIN0
接传感器分压信号、I2C1 PB6/PB7；USART3 经 CH340；充气阀 PB8、放气阀 PC1、
泵 PC8。MPXV5050GP P1 接压力侧，P2 通大气；BP Pressure Port 经三通接传感器
和真实袖带。各电源、电平、继电器及封堵口按该方案及其官方资料依据执行。
禁止人体接入。

1. 下载前由操作者确认 BP Stop、气路完全卸压、泵及阀负载电源断开。
   当前不能把历史断电确认当作本次确认。此后助手才执行下载。
2. Keil 打开 `blood pressure monitor/MDK-ARM/blood pressure monitor.uvprojx`，
   选原有目标 Rebuild，确认零错误/警告，再执行 Download。命令行 `UV4 -r`
   仅编译；本次于 2026-10-31 14:49 执行 `-f`，Verify OK，Application running。
3. 保持负载断电，以 115200 8N1 读取新鲜启动日志，核对固件标识，读取
   `cal`、`status`、`pins`、`fault`、`stack`。要求校准 VALID 82.326/-19.89，
   ADS ONLINE、泵 OFF、PB8 HIGH / PC1 LOW / PC8 HIGH。仅在校准丢失时按当前
   校准资料恢复并读回；本次全片擦除清掉记录后，已恢复原校准并读回 VALID。
4. 完成断电通断/短路检查，按现有方案先 MCU 后继电器上电；操作者确认非人体
   气路密封且无异常后，助手先采新鲜零压样本，再安排有上限的低压复测。
   BP 操作由用户完成，串口采集、分析与结束收尾由助手执行。
5. 正常现象：到压停泵，等待约 1 s 时仍有独立安全采样，随后才启动 PWM。
   故障现象：若出现等待期 ADS 失败，应输出
   `[Safety] Pressure read failed during hold; emergency vent`，故障 SENSOR_READ，
   PB8 HIGH / PC1 HIGH / PC8 HIGH，之后不得再出现该轮 `PWM started after hold`。
   查询失败可输出 `[Pressure] sample failed`；离线查询可输出 `Pressure offline during hold`。
   不通过热拔 ADS 或短接 I2C 制造实物故障，本次故障注入仅在 host 完成。
6. 实物异常立即结束该轮并保存原始首错与 ADSdiag，不把自动恢复当作修复成功。
   完整收尾固定 `vent` -> 连续新鲜 `est≈0` -> `seal`，核对最终 PC1 LOW，
   不让放气阀持续通电。先继电器后 MCU 断电。

## 2026-10-31 下载与负载断电预检记录

操作者以 `ok` 确认泵阀负载断电、BP Stop、气路卸压后，助手完成一次 Keil 下载。
返回码 0，日志记录 Full Chip Erase、Programming Done、Verify OK、Application running；
新鲜启动行显示 `sw=HOLD_SAFETY_20261031`，HEX SHA256 与上文一致。
随后发现校准 UNCAL，按既有校准资料发送 `cal write 82.326 -19.887`，
返回 written+verified，并以 `cal` 读回 VALID 82.326/-19.89；没有拟合新参数。

- 状态 IDLE、ADS ONLINE、stream ON、manual OFF，remaining=0。
- 引脚 PB8 HIGH / PC1 LOW / PC8 HIGH，pump OFF。这里只能验证负载断电时的
  MCU 引脚读回，接回负载后的执行器动作仍待检查。
- 故障 NONE，ADS errors=0/recoveries=0；捕获点数 0。
- 校准恢复后连续观察 10 s，保留 200 条新鲜记录：raw 1327..1331，均值 1329.34；
  est 全为 0.0。依当前 ADC 比例、分压与校准重建的未截断压力为
  -1.043..-0.987 mmHg，均值 -1.010 mmHg。显示零受负值截断影响，不能作为独立
  零点精度通过的证明，未据此调整校准。
- 空闲/诊断运行时栈 used=1424，free=2672，reserved=4096，saturated=0；
  本版本动态充放气、计算与导出路径的栈水位尚未测量。
- 本轮只发送状态查询与校准恢复，未发送 start、vent、seal 或 PWM 指令；
  保持负载断电，没有运行本版本带负载低压试验。

证据：

- `data/raw/preflight/hold_safety_flash_20261031-144929.ndjson`，
  SHA256 `1d704e8b1469df26f5c34bb2e307a4270abc231dea1986ce7a7c618420d0a089`；
  同名 `.metadata.json` 保存下载输出及预检回包。
- `blood pressure monitor/MDK-ARM/download_hold_safety_20261031-144929.log`。
- `data/raw/preflight/hold_safety_cal_restore_20261031-145124.ndjson`，
  SHA256 `4beed78ca46d533d822343e22eefa3d80b834ecf17985d5a4fcdbad34e43a5fb`；
  同名 `.metadata.json` 保存校准恢复、原始范围与状态回包。

## 2026-10-31 14:54 带负载低压复测失败

带负载预检为 IDLE、ADS ONLINE、校准 VALID、fault NONE、ADS errors/recoveries=0，
安全引脚读回正常；5 秒零压基线 raw1326..1329，est=0。目标30、主机上限40 mmHg。
14:54:43.450 发送 start，桥接 ACK 成功，收到充气 GPIO 回显；活动期收到14条压力。
最后一条14:54:44.122为raw3370、est28.0 mmHg，随后超过2秒无新鲜压力而中止。
14:54:46.172的stop与14:54:47.675的vent均无桥接ACK。

没有到压、hold、PWM、Safety、ADS故障或重启回显，不能把最后28.0视为实际峰值，
也不能据此定位停泵切换、ADS或MCU死机。未取得有效capture/export，低压项不通过。
操作者随后明确回复“三项均已完成”，确认泵阀负载断电、BP Stop、手动卸压；
远程vent→新鲜近零→seal未完成，最终GPIO未读回，原始metadata不回填成功。

断电后5秒snapshot仍为0样本；14:59的无动作status诊断收到hello，但ACK超时、无样本。
Windows仅枚举“USB 串行设备(COM6)”，PNP ID为
`USB\VID_FAED&PID_4870&MI_02\6&19B9AC61&1&0002`，未找到名称含CH340/CH341的设备；
这只是当前枚举证据，不能反推中断的物理根因。界面检查工具因native pipe不可用，
两次均未取得OmniProbe界面状态，没有操作重连、复位或再次充气。

- 原始：`data/raw/development_20261031/restart_low30_20261031-145438.ndjson`。
  SHA256 `5c8156536067867c6165ce0ee0cb35f84a4695bfb8a89699eb33d9a7a668370e`。
- 只读审计：`data/reports/restart_low30_failure_20261031-145438.md`及同名JSON。
- 断电诊断：`data/raw/development_20261031/load_off_diagnostic_20261031-145904.ndjson`。
  SHA256 `e3bb3239a28d60cb4bb21b6d9e5dd2145f4e864b1259a31bbe893c4565309319`。

## 边界与后续

15:02恢复连接后的无负载预检通过：status/pins/cal/fault/stack的ACK与MCU回显均正常，
IDLE/ONLINE、校准VALID、安全引脚、fault NONE、ADS errors0/recoveries0；10秒200条新鲜
样本est0、raw1297..1301(mean1299.035)，未截断换算均值-1.440mmHg，不作零点精度结论。
栈used1424/free2672/saturated0；本次没有新鲜版本回显，没有复位、校准或泵阀命令。
操作者明确确认恢复期间也重启/断电重上电过STM32，故当前计数不能追溯上次故障，
不能把恢复仅归因USB重连。系统仅列COM6时实时数据正常，不能以缺少CH340名称证明断连。
详见`data/reports/reconnect_preflight_20261031-150248.md`；原始SHA256
`9d812591a1b4fb5ca63191d4370ac088f84351e9ffa74ed391bc106755526d45`。

I2C BUSY/TIMEOUT、WRONG_START 的物理触发原因仍未证实；保护测试通过不等于
压力数据有效或硬件故障消失。大任务保留进行中，实物低压验证和数据集采集仍待完成。
上述为15:02时的状态。后续操作者明确授权重新复测并确认准备完毕，负载接回后
完成下节15:06试验；不得把之前的负载断电确认用于当前改线/下载。
不因通信中断调整PWM、算法或校准。
仓库尚无提交且全量资料未跟踪，本轮未创建首次全仓提交或归档任务。

## 2026-10-31 15:06 复现与保护运行证据

目标30/主机上限40mmHg，到压回显31.2后出现等待期SENSOR_READ紧急放气；
首份ADSdiag stage5/status2/err0x20/state0x20/SR1=0x10/SR2=2，errors1/recoveries0。
无PWM启动或Boot回显；主机stop/vent成功，十条新鲜VALID<=1mmHg后seal，
最终PB8 HIGH/PC1 LOW/PC8 HIGH、pump OFF。健康采集失败，无有效导出。
同窗口88个监测点均COM6存在、桥接响应；pump文本实收puep，物理触发原因未证实。
后查询fault USER_STOP由追加stop覆盖，ADS1/1，stack1424/2672/saturated0。
用户照片SF-01/DC12.0V；估压0->29.8约0.80s，平均37.25mmHg/s，实际峰值未知。
通径/流量假设待同条件对照，不能直接解释I2C BUSY。不更改校准/PWM、未再次充气。
完整原始哈希、时间线与后续范围见data/reports/restart_low30_failure_20261031-150649.md。
