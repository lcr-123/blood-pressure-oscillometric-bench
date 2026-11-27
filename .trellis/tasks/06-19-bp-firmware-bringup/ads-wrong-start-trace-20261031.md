# 30 mmHg复测错误的代码追溯

## 结论

16:09复测中的 `stage=5 status=1 reg=0x01 err=0x200` 对应：
ADS请求开始单次转换时，HAL发送主机START请求，未等到SB置位，
超时检查时START请求位仍为1，HAL将错误码设置为WRONG_START。
此路径尚未执行发送设备地址和配置数据的代码，不是读到异常压力数值后
由压力阈值生成的错误，也不是等待ADS转换完成的25 ms超时。

本结论来自生产源代码和已保留的原始日志；本次未操作串口、执行器或烧录。
没有修改生产固件，未据此宣称故障已修复。

## 完整调用和错误传播链

路径均相对 `blood pressure monitor/`，行号为本次审查时的源文件行号。

1. `Core/Src/main.c:695-711`：手动充气或到压后保持期间，每25 ms调用
   `ADS1115_ReadSample`。保持不是一个无采样的等待阶段。
2. `Core/Src/ads1115.c:178`：ReadSample先调用StartSingleConversion。
3. `Core/Src/ads1115.c:125-140`：配置AIN0、单次转换、128 SPS，
   调用 `HAL_I2C_Master_Transmit` 写配置寄存器0x01的三字节事务。
   `Core/Inc/ads1115.h:37` 将本次传输Timeout设为10 ms。
4. `Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_i2c.c:1077-1113`：
   HAL记录事务入口Tick，先检查READY和BUSY，再清ErrorCode并调用
   `I2C_MasterRequestWrite`。其非OK返回在外层统一变成HAL_ERROR，
   因此日志status=1，而非HAL_TIMEOUT。
5. 同一HAL源文件 `6686-6709`：设置CR1.START，等待SR1.SB。
   等待函数返回失败且CR1.START仍为1时，`6707`执行
   `hi2c->ErrorCode = HAL_I2C_WRONG_START`。
   `6715`发送7位地址，位于上述失败返回之后，本次未走到这里。
6. 同一HAL源文件 `7323-7348`：等待函数在Tick差 **大于** Timeout且
   标志仍不满足时，将State改回READY、Mode改为NONE、置TIMEOUT并解锁。
   起算点是Master_Transmit入口，不是另给START独立的10 ms。
   随后6707的赋值用WRONG_START覆盖先前TIMEOUT，故err最终是0x200。
7. `Core/Src/ads1115.c:140` 调用 `ADS1115_Fail`，记录stage5、reg01、
   HAL错误/状态及外设/GPIO快照，标记离线并原样向上返回失败。
   `Core/Inc/ads1115.h:62-71` 的枚举定义stage5=CONVERSION_START；
   HAL头文件 `stm32f1xx_hal_i2c.h:172` 定义WRONG_START=0x200。
8. `Core/Src/main.c:702-711` 收到非HAL_OK，先取消控制并执行
   `ManualPump_EmergencyStop(BP_FAULT_SENSOR_READ)`，后打印
   `Pressure read failed during hold; emergency vent`及诊断。
   `Core/Src/bp_control.c:53-65` 实际停泵、关闭充气路径、打开放气阀，
   清理计算并锁存EMERGENCY。此后空闲恢复不会重新开始本轮采集。

Keil项目 `MDK-ARM/blood pressure monitor.uvprojx:435,555` 注册的
正是上述ADS和HAL源文件；并非另一个未使用的驱动副本。

## 寄存器证据解释

原始首错见
`data/raw/development_20261031/uart_guard_low30_20261031-160924.ndjson:267`。

| 首错字段 | 对应含义及限制 |
| --- | --- |
| status=1 | HAL_ERROR，来自Master_Transmit的返回值映射 |
| err=0x200 | HAL看到SB等待失败且START请求仍为1后设置的软件错误码 |
| state=0x20 | HAL等待超时分支主动改回READY；不能据此判定外设健康 |
| sr1=0x0010 | STOPF=1，SB=0；STOPF的设备头文件含义为从机模式STOP检测。当前主机事务失败时出现它是待查线索，不能仅凭位名确定原因 |
| sr2=0x0000 | 保存时MSL/BUSY/TRA均未置位；不等于先前时序无异常 |
| cr1=0x0101 | PE=1、START=1；START请求仍挂起，与错误赋值条件相符 |
| scl=1 / sda=1 | ADS失败函数中依次读取的引脚快照，两线当时为高，不是瞬态波形 |

第一次失败诊断的recoveries=0，后续查询为1。原始快照早于恢复，
成功恢复不会清掉最近错误记录。最终USER_STOP由宿主stop覆盖，
不能替代原始SENSOR_READ原因。

## 已收敛的范围与未决项

- 当前生产I2C配置实际为100 kHz、7位地址0x48传HAL左移为0x90；
  i2c.c文件头400 kHz是旧注释，不是运行配置。
- 检查Core中的调用点，当前RELAY_ONLY路径的ADS事务由主循环顺序调用；
  UART/EXTI/SysTick回调未调用ADS采样，未找到两个采样任务同时调用的证据。
  NVIC启用本身不能证明发生了I2C事件中断竞争。
- 本次源代码追溯确定的是外设START未完成的检测路径；尚不能区分
  总线电气瞬态、外设状态异常或其他时序因素，也不能判定特定器件损坏。
- 后续定位应围绕到压停泵/关充气阀附近的STOPF和START异常取证。
  更改压力阈值、把失败当成功、增大转换等待或盲目重试均不能作为修复证明。
  当前失败保护和vent→新鲜近零→seal收尾契约保持有效。

验证方式：静态逐层追溯、核对HAL/CMSIS定义、核对Keil源文件注册、
对照既有首错日志。本次未新增软件测试或物理复测；未获得新的电气波形。
