# 2026-11-01 Standard BP Preset 3 高压采集准备

## 条件与容量

操作者确认 BP Pump 2 为 Standard BP / Preset 3 / External Cuff、200/150 mmHg、80 BPM、0.60 cc；气路未变且仅接非人体袖带。此为操作者确认，尚无面板照片或同步独立压力证据。当前现场只读快照 5 秒 est=0.0、raw=1294..1298；尚未下载新固件或进行本档充气。

固件缓冲 3300 点、间隔 25 ms，最多约 82.5 秒。上一轮 target170 的导出从约 161 mmHg 到低于 15 mmHg 用 2801 点/70 秒。若本档 target220 仍以约 2 mmHg/s 放气，预计超出缓冲。直接增大缓冲会突破当前 2048 B RAM 余量下限。

## 已准备的软件

- Relay-only 主循环在目标低于 200 mmHg 时保留 2.0 mmHg/s；目标达到 200 mmHg 时使用 3.0 mmHg/s。放气诊断维持 2.0 mmHg/s。活动采集期间 target 命令被拒绝，避免速度策略半途变化。原有超压、ADS 失读、缓存溢出、stop/vent 紧急放气路径不变。3.0 是待台架验证的控制目标，不保证实测斜率或完整导出。
- 固件标识 HIGH_PRESSURE_CAPTURE_20261101，可通过只读 version 命令查询。宿主脚本 tmp/bp_standard200_150_capture_20261101.py 在任何 target/start 之前核对该标识、IDLE/安全引脚/校准/ADS/UART/零点；设置 target220、主机截止 235 mmHg、失读截止 2 秒、活动期限 78 秒。异常尝试 stop，再执行 vent → 连续新鲜近零 → seal；记录原始日志、元数据和哈希。旧固件无该标识，脚本会在充气前退出。
- 生产 C 速度选择测试覆盖 170/199.9/200/220 mmHg 与放气诊断分支；活动期 target 拒绝及版本查询门槛有测试。完整宿主测试 123 项通过。Keil UV4 Rebuild 0 错误、0 警告；Program Size Code=54364、RO=8680、RW=32、ZI=63456。预算检查 RAM 使用 63488/65536，余量 2048 B，静态已知栈峰值 1392 B 加 1024 B 预留低于 4096 B。HEX SHA256 be45baab8c3ad598595d57fdce2ddb1481f1911341abf4180cb95b884048ac77。未新增或移动 C/S 源文件。

## 非人体下载与验证门槛

1. 保持当前气路只接非人体袖带。BP Pump 2 停止、已卸压；先断泵阀继电器负载电源，MCU/ADS/UART 可维持供电。以新鲜串口样本核对 est 近零、IDLE、PB8 HIGH/PC1 LOW/PC8 HIGH、泵 OFF、ADS ONLINE、UART 错误计数及 fault。断电核对连接/短路、再按当前接线方案和官方手册核对供电；不依据旧分压或旧传感器配置。
2. 在 Keil 打开 blood pressure monitor/MDK-ARM/blood pressure monitor.uvprojx，Rebuild 应为 0 错误、0 警告。确认源文件注册和 RAM/栈预算后，按既有 SWD 流程下载并 Verify。MCU 先于继电器负载上电；下载后先查询 version/status/pins/cal/fault。若全片擦除使校准 UNCAL，仅在未改变 MPXV5050GP/ADS1115 硬件时写 cal write 82.326 -19.887，读回 VALID 82.326/-19.89。先做非人体零压与安全引脚检查，才恢复负载电源。
3. 单轮开发性采集前重新执行 vent → 连续新鲜近零 → seal，并确认封阀后 raw 稳定。运行宿主脚本时需本轮面板和非人体确认。观察 target220 到压自动停泵、放气实际斜率、活动总时间、采样数小于 3300、dropped=0、无 Safety/ADS/UART 故障；任一条件失效则停止并卸压，不把不完整采集当数据集样本。
4. 成功收尾后严格解码 bp.capture/3、验证 25 ms MCU tick、生产 C 离线回放，并按冻结的 10 mmHg 候选与 5 mmHg 基线同时报告包络。只保留为 development，直到面板照片和同步独立压力证据齐备。不得将固件 valid=1 等同于血压准确性。

本报告记录软件就绪状态，尚不证明 3.0 mmHg/s 在现行气路上可达，也不构成下载或高压采集已经执行的证据。

## 下载、首次失败与重试门槛

- 用户要求直接烧录。下载前只读预检显示 IDLE、校准 VALID、ADS ONLINE、UART 错误 0、安全引脚和 5 秒稳定零点。Keil UV4 日志为 Full Chip Erase Done、Programming Done、Verify OK、Application running。新固件 version 读回 HIGH_PRESSURE_CAPTURE_20261101；全片擦除后校准 UNCAL，按现行配置写 cal write 82.326 -19.887 并读回 VALID。烧录与校准恢复记录分别见 blood pressure monitor/MDK-ARM/high_pressure_flash_20261101.log 和 data/raw/preflight/high_cal_restored_20261101-132724.ndjson。
- 13:30 首次 target220/start 前没有取得负载侧 12 V 已恢复的确认。约 12 秒内显示压力一直为 0.0 mmHg，未达到目标，宿主触发超时，发送 stop，并完成 vent→新鲜近零→seal；target 恢复 50。该轮没有有效高压波形。随后操作者确认负载侧 12 V 已接通、MCU/ADS/UART 保持上电、气路未变且仅接非人体袖带；不能把这条事后确认倒填为首次启动前的供电证据。原始记录 data/raw/development_20261101/standard200_150_20261101-133011.ndjson，SHA256 b3c2634f038fbe1c627304d3d09bd2fc184e21e0fbfd600e6b3300b4830de4c7。
- 用户要求重试。重试前 vent→新鲜近零→seal 收尾通过，但封阀后 raw=1267..1329，未通过原始零点稳定门槛；随后 10 秒只读 raw=1184..1252，最后 5 秒只读 raw=950..995、est 均显示 0.0。最终 status=EMERGENCY / fault=USER_STOP 与前次主动 stop 一致，PB8 HIGH / PC1 LOW / PC8 HIGH、pump OFF，ADS ONLINE、errors/recoveries=0、UART rx_errors=0、校准 VALID。重试未发送 start。最终原始只读记录 data/raw/preflight/high_retry_final_readonly_20261101-133803.ndjson，SHA256 aea4574bbbbe9cc76c3eced270f3dad5d5fecf8053a86225d030dcd90d44b031。
- 显示 est=0 对负向估压有截断，不能替代 raw 零点稳定判据。单一压力通道和控制引脚读回无法区分实际负载供电、泵机械动作、气路泄漏、传感器供电或 ADC 输入变化。暂停高压启动，先排查原始零点持续下移和上一轮不升压的物理原因；不得用重复 start 代替定位。3.0 mmHg/s 的高压放气策略尚未经板上到压/放气验证。

## 操作者再次报告 OK 后的重试检查

操作者报告现场已处理好。只读预检显示新固件、VALID 校准、ADS ONLINE、UART 错误 0、安全引脚和 USER_STOP 锁存；10 秒 raw=1347..1357、est 全为 0.0。一个额外的写死 raw=1270..1310 门槛错误地拒绝了这段稳定样本，该门槛不能代表独立压力零点证据。随后再做 10 秒只读快照，raw=1302..1388，显示 est 仍全为 0.0，说明原始零点跨窗口未稳定。未发送 target 或 start，未进行本次重试充气。预检原始记录 data/raw/preflight/preset3_retry_preflight_20261101-133938.ndjson；应先核对非人体气路真实卸压、MPXV5050GP P2 通大气、传感器与 ADS 供电/地及连接，再用连续原始样本确认稳定，不能仅凭截断后的 est=0 重试高压。

后续零点恢复稳定后，13:44 的受控单轮重试已到压并完成全段导出；结果、收尾和算法质量限制见 standard200_150_20261101-134453.md。此前“重试未发送 start”仅描述 13:39 的被拦截尝试。
