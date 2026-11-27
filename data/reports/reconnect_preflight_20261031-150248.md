# 串口恢复后的无负载预检

结果：无负载通信与状态检查通过；没有再次充气或改变泵阀输出。
操作者确认恢复期间也重启/断电重上电过STM32，因此不能把恢复归因于USB重连，
当前fault NONE与ADS errors/recoveries=0只描述重启后的运行状态。

- 桥接握手、status/pins/cal/fault/stack的ACK与MCU回显均收到。
- IDLE、ADS ONLINE、stream ON、manual OFF、校准VALID 82.326/-19.89。
- PB8 HIGH / PC1 LOW / PC8 HIGH，pump OFF。
- 连续10秒200条新鲜样本，est均为0.0，raw1297..1301，均值1299.035。
- 主机到达时间戳最大间隔51ms，不视为MCU真实采样周期。
- 原始值按现有比例重建未截断压力约-1.469..-1.413mmHg，均值-1.440；
  显示零受负值截断影响，不能当作独立零点精度通过，未调整校准。
- 栈used1424/free2672/reserved4096/saturated0，仅当前空闲及诊断路径。
- 固件版本仅在启动输出；本次连接未捕获新鲜版本行，保留14:49下载证据引用。
- 系统当前只列COM6且实时数据正常；缺少CH340/CH341名称本身不能证明此前适配器断开。

原始：`data/raw/preflight/reconnect_20261031-150248.ndjson`。
SHA256：`9d812591a1b4fb5ca63191d4370ac088f84351e9ffa74ed391bc106755526d45`。
同名metadata记录全部查询回显、门槛、重启确认和局限。

14:54失败记录仍有效：最后观测28.0mmHg，stop/vent无ACK，实际峰值与中断原因未知。
本次重启后的空闲检查不验证带负载切换安全性，不补填远程vent→近零→seal成功。
泵阀负载保持断电、BP Stop；后续需先定位或隔离中断条件，再制定独立受限复测。
