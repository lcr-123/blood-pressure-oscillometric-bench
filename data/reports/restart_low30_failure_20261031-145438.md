# 30 mmHg 低压复测失败记录

结论：本轮失败，没有有效波形导出，未验证到压等待期保护的实物效果。

## 证据与时序

- 原始记录：`data/raw/development_20261031/restart_low30_20261031-145438.ndjson`。
- SHA256：`5c8156536067867c6165ce0ee0cb35f84a4695bfb8a89699eb33d9a7a668370e`（本次审计重新计算一致）。
- 目标 30 mmHg，主机压力上限 40 mmHg；上限依赖收到新鲜数据，不能视为独立硬件限压。
- 充气前状态 IDLE、ADS ONLINE、校准 VALID；5 秒基线 est=0，raw1326..1329。
- `start` 发送于 2026-10-31T14:54:43.450175+08:00，桥接 ACK 成功，收到充气 GPIO 回显。
- 充气期间保留 14 条压力回显；最后一条 2026-10-31T14:54:44.122+08:00，raw3370，est28.0 mmHg。
- 随后超过 2 秒无新鲜压力，主机中止；`stop`（14:54:46.172）与 `vent`（14:54:47.675）均未收到桥接 ACK。
- 没有到压、hold、PWM、Safety、ADS 故障或重启回显。28.0 只是最后收到的值，实际峰值未知。

## 收尾与通信检查

操作者随后明确回复“三项均已完成”，确认泵阀负载断电、BP Stop、手动卸压。
这是人工物理状态确认；远程 `vent -> 连续新鲜近零 -> seal` 未完成，最终 GPIO 未读回。
原始试验 metadata 的 `pneumatic_closeout_confirmed=false` 保留，不回写为成功。

断电后 5 秒只读 snapshot 为 0 样本。窗口工具两次报告 native pipe 不可用，界面状态未知。
Windows 当前仅枚举 USB 串行设备(COM6)，PNP ID为
`USB\VID_FAED&PID_4870&MI_02\6&19B9AC61&1&0002`；未找到名称含CH340/CH341的设备。
设备枚举只表示当前状态，不证明断连原因或断连时刻。
仅发送一次无动作的 `status` 诊断：TimeoutError('ACK status')。
诊断记录：`data/raw/development_20261031/load_off_diagnostic_20261031-145904.ndjson`，SHA256 `e3bb3239a28d60cb4bb21b6d9e5dd2145f4e864b1259a31bbe893c4565309319`。
桥接 hello、桥接 ACK、MCU 回显属于不同层；不能把 ACK 缺失直接归因 ADS 或 MCU 死机。

## 下一步门槛

保持负载断电，先恢复通信，再核对新鲜固件标识、status/pins/fault/stack 和零压样本。
原因未明前不再次充气，不调整 PWM、算法或校准。本轮不是公开数据集有效样本。
