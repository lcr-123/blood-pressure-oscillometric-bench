# 停泵/阀切换附近 ADS1115 故障：只读审计

2026-10-31；非人体台架。本轮只读取源码、既有原始记录和 5 秒被动串口摘要，没有发送执行器命令、清故障、复位、写校准或下载固件。BP 保持 Stop。

## 结论

两份到压停泵记录具有相同的 `CONVERSION_START / HAL_BUSY / TIMEOUT / SR2.BUSY` 特征；另一次 STOP 附近为 `CONVERSION_START / HAL_ERROR / WRONG_START`。这些是通信失败证据，尚不能确定是负载切换、电源、布线、外设状态还是其他原因。不能据此判断电磁阀损坏。

另有可独立确认的控制流程问题：到压后的 1 秒等待期发生诊断读取失败时，读取失败分支未取消待启动 PWM。14:21 的记录实际出现了“读取失败 → PWM started → 下一次采样失败 → emergency vent”。这应先于下一轮充气处理。

## 三个故障窗口

| 原始记录（data/raw/development_20261031/） | 前一个切换回显 | 首个失败回显的宿主时间差 | 首份诊断 |
| --- | --- | --- | --- |
| restart_low50_20261031-141724.ndjson | STOP，PB8 HIGH / PC1 HIGH / PC8 HIGH | 58 ms | stage=5 status=1 err=0x200 state=0x20 SR1=0x10 SR2=0 |
| restart_low50_20261031-142117.ndjson | target reached 52.5；随后 holding | 57 ms | stage=5 status=2 err=0x20 state=0x20 SR1=0 SR2=2 |
| sealed_hold30_20261031-143306.ndjson | target reached 30.7；随后 holding | 59 ms | stage=5 status=2 err=0x20 state=0x20 SR1=0 SR2=2 |

时间来自串口接收时间，不是 MCU GPIO 边沿或传感器内部采样时刻；到压回显在源码中先于关闭阀1及停泵动作。三个首次失败行均带替换字符。不能从回显排序精确归因到某个触点或把 seal 的宿主发送时间当作 MCU 执行时间。

同目录另有到压但未记录 `sample failed` 的轮次（13:34、13:54、14:27），因此不是每次切换都出现同一故障，也不能把本表当成经过控制的故障率试验。未记录此类错误不等于完整数据质量通过。

## 状态码与调用路径

源码依据：

- `Core/Inc/ads1115.h`：stage=5 是 CONVERSION_START；驱动调用的 I2C 超时参数是 10 ms。
- `Core/Src/ads1115.c:105` 起：写 CONFIG 寄存器的三字节 `HAL_I2C_Master_Transmit` 失败后直接记录状态并返回，没有产生新有效样本。
- `Drivers/STM32F1xx_HAL_Driver/Inc/stm32f1xx_hal_def.h:38` 起：0=HAL_OK，1=HAL_ERROR，2=HAL_BUSY，3=HAL_TIMEOUT。因此 `status=2` 不能解释为 HAL_TIMEOUT 返回值。
- `.../Inc/stm32f1xx_hal_i2c.h`：error 0x20=HAL_I2C_ERROR_TIMEOUT；0x200=HAL_I2C_WRONG_START；state 0x20=READY；SR2 位1=BUSY，位0=MSL。
- `.../Src/stm32f1xx_hal_i2c.c:1074` 起：Master_Transmit 在发 START 之前等待 BUSY 清除，此处使用 HAL 自身的 **25 ms** 上限（不是传入的 10 ms）。等待失败后返回 HAL_BUSY；等待帮助函数把 error 置 TIMEOUT 并将 handle state 置 READY。

因此两份 `status=2 / error=0x20 / state=READY / SR2=2` 与“发送前等待总线释放超时”路径吻合；SR2.BUSY 是外设寄存器观察，不是对 SDA/SCL 引脚电压的实测。现有诊断缺少 CR1、SCL/SDA 引脚状态和独立边沿记录，不能进一步定位 BUSY 的物理原因。

`I2C_MasterRequestWrite` 在等待 SB 失败且 CR1.START 仍置位时记录 WRONG_START，外层发送函数返回 HAL_ERROR，与 14:17 的 `status=1 / error=0x200` 相符。保留首份诊断：后续“未初始化”失败会覆盖原始 stage，不能把 stage=1 当作最初原因。

PB8 阀宏通过 `HAL_GPIO_WritePin` 的 BSRR 单独写 PIN_8；未发现该宏整端口覆盖 PB6/PB7 的情况。这仅排除了这条直接代码路径，不排除电气耦合。

## 1 秒等待期的保护缺口

`main.c:700` 起到压后 disarm 泵、关闭阀1、停泵，并设置 `s_deflate_hold_until_ms`。等待期间 `PressureStream_Task` 不满足 manual/PWM 活动样本复用条件，会调用 `Debug_PrintPressureSample` 发起新 ADS 读取。

读取失败分支（约 417–429 行）取消计算、标记 ADS offline 和样本无效、记录 SENSOR_READ，但未调用 `DeflateControl_Cancel` 或紧急放气；计时到达分支（约 1645–1663 行）仍会使能 PWM。

14:21 实际串口顺序（宿主 RX）：

1. 14:21:22.328：sample failed；.337：首份 stage5 诊断及 stream read failed。
2. 14:21:23.276：PWM started after hold。
3. 14:21:23.301：Pressure read failed during deflate; emergency vent。
4. 14:21:23.312：stage1 诊断，errors=2；.319：retry init / Init OK。

这证明当前保护会在后续放气采样时触发，但等待期错误没有立即取消控制流程。14:33 的主机 seal 取消了计时，因此该轮没有 PWM started；它仍因关键数据缺口及 SENSOR_READ 锁存而无效。

## 恢复与数据缺口

驱动在失败时只标记 recovery pending；后续 Init 才 DeInit / 外设复位 / Init。诊断 stream 每隔至少 1000 ms 重试一次。因此约 1 秒压力缺口包含固件离线重试等待，不能说 I2C 调用本身阻塞了约 1 秒。14:33 最大压力宿主样本间隔为 1067 ms；自动恢复不能补回此段压力。

本轮被动 snapshot 持续 5 秒，101 个样本：raw=1383–1386，sensor=239 mV（串口整数显示），est=0.0 mmHg；sampleRateHz=0。该摘要只支持当前短窗口正在接收压力记录，不能证明切换瞬态已修复、故障锁存已清除或独立零点校准通过。没有额外保存本次 snapshot 的原始记录。

## 下一步的具体范围（尚未实施）

1. 给“到压等待”明确的故障取消路径：ADS 读取失败后立即取消待启动 PWM、停泵并执行既有紧急放气；空闲诊断和人工已 seal 的保压状态需保留各自执行器所有权，避免扩大成所有 stream 错误都切阀。
2. 在首个 ADS 错误处先保存有限的寄存器/引脚诊断及控制阶段，再进行任何恢复；不增加高频 printf，不做无界重试，不用自动恢复隐藏失败。
3. 用生产 C 的故障注入验证“等待期读取失败不再启动 PWM”，再做 Keil 编译及 RAM/栈检查。当前静态 SRAM 余量有限，新增字段需重新核算。
4. 软件保护通过并下载后，先做非人体零压基线和有界切换诊断；记录每次实际 GPIO 状态、原始电压及首份 ADS 诊断，再决定是否重复 30 mmHg 保压。涉及接线或抑制元件时先查对应官方资料。

本轮没有实施以上修改；物理根因仍待验证。暂不从失败轮次调整 PWM 或血压算法。

## 原始记录完整性

- 14:17 SHA256：`749e6f5c6d4ca3e31ee60829a3560c6c2e05c1dea3cb47d68c4390946fd72539`
- 14:21 SHA256：`161b0d1623753791c0f57a50b4e33d5ca14311e027ee7042b82dcb6bbba654fb`
- 14:33 SHA256：`c63004e949dae0ad28b7645c83ad9953f21a659d245beddc7f7ca5580ae2d014`

原始 NDJSON 和 metadata 均未修改。14:33 完整有效性结论见 [原报告](sealed_hold30_20261031-143306.summary.md)。
