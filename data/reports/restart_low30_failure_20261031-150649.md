# 30 mmHg 复测：等待期保护触发，ADS 故障仍在

2026-10-31，非人体台架。目标30、主机上限40 mmHg、新鲜度门限2 s。
本轮没有修改固件、校准或PWM参数。健康低压采集失败，没有有效capture/export。

## 观察与安全收尾

时间为UTC+8宿主串口到达/发送时间，不是MCU采样tick或GPIO边沿。

| 时间 | 证据 |
| --- | --- |
| 15:06:49 | IDLE/ADS ONLINE/VALID，fault NONE，ADS errors0/recoveries0，安全引脚 |
| 15:06:54.561 | start发送，ACK成功 |
| 15:06:54.612 | START回显，PB8 LOW/PC1 LOW/PC8 LOW |
| 15:06:54.627–55.427 | 17条压力文本，est0.0 ->29.8 mmHg |
| 15:06:55.447 | 到压回显31.2 mmHg，holding；源字符串pump被接收为puep |
| 15:06:55.491 | Pressure read failed during hold; emergency vent |
| 15:06:55.496 | ADSdiag stage5/status2/err0x20/state0x20/SR1=0x10/SR2=2，errors1/recoveries0 |
| 15:06:55.528–55.631 | 主机追加stop、vent，ACK与MCU回显成功 |
| 15:06:56.503 | ADS retry init，Init OK config0xC383 |
| 15:06:56.610–57.060 | 十条新鲜VALID est：0.7/0.8/0.7/0.6/0.5/0.1/0.2/0.2/0.1/0.1 mmHg |
| 15:06:57.087–57.166 | seal发送并回显，最终PB8 HIGH/PC1 LOW/PC8 HIGH，pump OFF |

未出现PWM started或Boot回显。等待期故障取消及vent->新鲜近零->seal有本轮运行
证据，但没有独立机械阀位/电流测量。脚本shell退出0不是通过：metadata明确
outcome=failed、pneumatic_closeout_confirmed=true；不改写原始结果。

## 故障解释与边界

stage5=CONVERSION_START；status2=HAL_BUSY；err0x20=HAL_I2C_ERROR_TIMEOUT；
state0x20=READY；SR2位1=BUSY。与HAL Master_Transmit发START前等待总线释放超时
路径吻合，该处HAL内部等待上限25ms，不是驱动传入的10ms。SR1=0x10为STOPF；
缺少CR1、SDA/SCL引脚及边沿记录，不能仅凭快照确认外设勘误、电气或物理原因。

main.c源码打印stopping pump，实收stopping puep。字符损坏和I2C失败均在停泵/
关充气阀附近，尚不能唯一归因为供电、接地、负载抑制或其他原因。PB8宏使用
单引脚BSRR，未发现直接覆盖PB6/PB7。自动恢复不能补回缺失压力，也不是修复证明。

同步监测88个检查点，15:06:40.654–15:07:25.324：COM6始终存在，桥接PID49220
均未退出且Responding=true。不能由此证明UART无误码或排除检查点之间的短暂变化。

复测后只读查询：EMERGENCY/ADS ONLINE、fault USER_STOP、ADS errors1/recoveries1、
capture n0；stack used1424/free2672/reserved4096/saturated0。
BP_Control_RecordFault会以每个非NONE故障覆盖前值，因此主机追加stop可把最初的
SENSOR_READ改成USER_STOP；最终标签不抹去首错。
5秒100条新鲜压力raw1416..1421(mean1418.44)，est0.2..0.3(mean0.244)。
试前raw均值1317.71，差异不能由单传感器区分残余压力、零漂和供电影响。

## SF-01与快速充气假设

用户照片标签：VALVE / SF-01 / DC12.0V / www.fspump.cn；照片没有内部通径、流量、
线圈电流、内置抑制或工作制参数。厂家站点可访问，但本轮未找到精确SF-01规格，
不套用其0520A等其他型号数据。查阅入口：http://www.fspump.cn/valve23/ 。

17条宿主压力文本跨0.80s，端点平均升压约37.25mmHg/s，全窗口直线拟合约
30.19mmHg/s。START至到压回显约0.835s；起始袖带展开等可能不线性，这不是恒定
流量测量。31.2是同一传感器到压回显，比设定值高1.2；流文本最大29.8。
故障后实际峰值未知，不能声称“最大超调仅1.2mmHg”，没有独立同步压力验证。

同等泵、袖带、密封和接管条件下，内部有效通径增大可能减小气阻、加快充气。
外部接管嘴尺寸不等于内部节流孔；缺少同条件新旧阀对照，不能确认更换后加快。
充气快可能影响到压余量及压力瞬态，但本身不能解释I2C BUSY超时。
减慢充气即使改善现象，也不足以证明通信根因修复。

## 后续

健康低压验收保持未通过。先核实泵、继电器型号和负载端抑制器件，再安排零压、
泵保持OFF的充气阀单独切换对照。改线/下载需操作者新的负载断电、BP Stop、卸压
确认；本轮结束泵OFF、阀封闭，不等于负载已断电。不得用加大超时、盲目重试、
取消保护、改校准掩盖故障。本报告后没有再次充气或操作执行器。

## 原始完整性

- data/raw/development_20261031/restart_low30_20261031-150649.ndjson
  SHA256：9f670129820ea1ba7d51a6c197b3d4e9829807b6f96dc6c995021862db3cc4e2
- data/raw/development_20261031/transport_monitor_20261031-150638.ndjson
  SHA256：1b6406af664bebee82c25920c8d1f9e363f9bf24c4f31a6a05c4133060ba7071
- data/raw/preflight/post_low30_20261031-150726.ndjson
  SHA256：bb5655b9570caab06810040cfe97cdb6f4fcf8bbe6f6d49b48515aa9f0d6b47e

运行映像HOLD_SAFETY_20261031，身份沿用14:49下载/启动证据，本轮无新版本查询。
HEX SHA256：f402fd49740f8416ff28e5c3803802ae3efc505ec3ddd66b48f99f67426667b4。
已有原始NDJSON和metadata均未修改。
