# 串口与命令路径复查（2026-10-31）

用户要求“复查一下代码”。下列软件缺陷已修复并沿用直接烧录授权下载，固件标识 `UART_RX_GUARD_20261031`。本次泵阀12V断开，继电器5V与MCU保持供电，非人体、BP Stop、已卸压；未充气。带负载断流的具体原因仍未定位。

## 发现与修复

1. USART3缺少错误恢复回调，HAL遇到ORE后可能终止接收；带RXNE的错误还可能先调用接收完成回调。现在错误帧不进入解析器，也不提前重启接收；错误回调清标志、拒绝受损命令、重启READY接收器，主循环提供一次有界补启动。中断不做执行器、I2C或日志工作。`status`新增`[UART3] rx_errors=... rx_state=...`。
2. 中断和主循环共享命令缓冲，后续字节可能覆盖待解析参数。现在完整命令冻结，在保留PRIMASK的短临界区复制到本地缓冲；待处理时只允许完整`stop`/`vent`覆盖。非法字符、超长行及同步丢失后的尾段整行拒绝，直到下一个分隔符。
3. `i2cscan`的HAL地址未左移，且缺少活动测量/执行器门禁。现在使用`addr << 1`；采集、待计算或泵阀非密封空闲状态均在任何I2C调用前拒绝扫描。

生产修改：`Core/Src/main.c`、`Core/Inc/bp_algorithm.h`。主机回归执行真实HAL RX/错误路径、生产解析器和扫描函数。没有新增生产C/S文件；主机测试不登记为Keil固件源码。

## 软件验证

- `python -m unittest discover -s "blood pressure monitor/test" -p "test_*.py" -v`：113/113通过，27.036s。覆盖ORE有/无RXNE、PE/NE/FE、恢复、计数饱和、参数快照、忙时stop/vent、超长/损坏输入、PRIMASK还原及扫描地址/门禁。
- Keil ARMCLANG6.22 Rebuild：0 errors/0 warnings，Code53456、RO8264、RW32、ZI63448。日志`blood pressure monitor/MDK-ARM/rebuild_uart_rx_guard_20261031.log`。
- `tools/check_firmware_budget.py`通过：RAM63480/65536，余2056B；静态已知栈1392B，加1024B预留小于4096B。RAM接近2048B门限，新增缓冲须重新核算。
- 下载返回0、Verify OK、Application running，串口观察到新版本。HEX SHA256：`5e3a9c53796408ed1154fbb6362517bd0066f5932782f9c9598cc35d4b669e89`。

## 板上验证

全片擦除后恢复`cal write 82.326 -19.887`并读回VALID。下载前后各5秒100条新鲜VALID样本，est均0.0mmHg；下载后raw1293–1296。状态IDLE、manual OFF、ADS ONLINE、fault NONE，PB8 HIGH/PC1 LOW/PC8 HIGH、pump OFF、rx_errors0。空闲栈used1224/free2872/saturated0；不代表完整采集/导出峰值。

原始证据：`data/raw/preflight/uart_rx_guard_flash_20261031-160132.ndjson`及同名`.metadata.json`。原始SHA256：`84fac653bd192062ca1e0e5269e8852ab841dae444c3dad9e90958c3e6a885e5`。

## 接线、Keil及非人体验证步骤

沿用当前《血压仪完整接线方案》：MPXV5050GP、ADS1115 AIN0/I2C1 PB6-PB7/0x48/VDD3.3V；USART3 PB10-PB11、1152008N1；充气阀PB8开漏低有效，放气阀PC1高有效，泵PC8低有效。不新增接线和供电要求。需改线时先查官方资料、按既定断电/上电顺序操作。

Keil打开`blood pressure monitor/MDK-ARM/blood pressure monitor.uvprojx`，Rebuild并核对零错误/警告与内存预算，再Download确认Verify OK；全片擦除后恢复当前校准并读回。上述步骤本轮已执行。

本次非人体零压验证：保持12V断开，观察新版本、连续新鲜样本及`cal/status/pins/fault/stack`，预期为上述有效校准、空闲状态和安全引脚。故意注入UART错误及连续命令的验证在主机真实C路径完成，未在实板制造通信干扰。

后续带负载验收须独立记录，本次通过不能证明接回12V后的读取故障已消除。气路收尾仍固定为`vent`→连续新鲜近零样本→`seal`，不能凭桥接ACK推定机械动作或卸压完成。
