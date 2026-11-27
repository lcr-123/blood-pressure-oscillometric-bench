# 完整波形导出与生产 C 回放：交付及非人体验证

日期：2026-10-25，实板下载状态更新于2026-10-26。当前源码及实板版本：
`CAPTURE_VALVE_20261025`。新版已下载并完成未加压安全启动/校准恢复验证；
`bp.capture/2` Standard BP 采集、严格解码及生产C回放已完成一轮。

## 阀脉冲直接关联增量（已下载，动态采集待验证）

新增约64B RAM 的 `BP_ValveDiagnostics_t`，由 `DeflatePulse_Start()` 在真实
`VALVE2_OPEN()` 后记录 MCU tick 与1..90ms on-time。相邻压力绝对变化>=5.0mmHg
时，按最近脉冲后的0..199ms八个25ms桶及>=200ms桶聚合，并保留最大正/负
跃变的 index、signed delta、phase 和 on-time。没有新增2800点数组，未改变
阀调度、压力采样、包络、FFT、阈值、补偿、校准或安全门槛。

协议升级为 `bp.capture/2`：begin -> n point -> 恰好一条 valve -> features ->
end；FNV1a 包含 valve 原始行。离线工具仍严格兼容旧 `/1`（其 valve 为缺失），
并拒绝 `/2` valve 缺失、重复、乱序、字段不一致或篡改。生产 C 回放仍只消费
原始 point，报告原样携带已验证的 valve 聚合。

软件验证：73/73测试通过；Keil V6.22构建0错误/0警告，日志
`tmp/valve_diag_build_20261025.log`；Code48432、RO6136、RW28、ZI63276。
RAM63304/65536，余2232B；预留栈4096B，静态已知峰1304B，另留1024B后通过。
工程未新增文件，`main.c`、`bp_algorithm.c`、`bp_capture_export.c` 均已在原
`.uvprojx` 登记。运行时栈水位仍未测。

2026-10-26 用户确认桥接并授予本轮硬件操作权限后，下载前只读基线为：
IDLE、manual OFF、ADS ONLINE、压力100点均0.0mmHg、PC0/PC1 LOW、PC8 HIGH、
pump OFF、校准82.326/-19.89 VALID。Keil `UV4 -f` 对预先锁定的 HEX
SHA256 `BEE4C399F96A0C758B4930C223CCF64C3E339A5756419ABE670476D7BA3146AB`
执行 Full Chip Erase、Programming、Verify OK；证据
`tmp/capture_valve_flash_20261026.log`。擦除后先验证 UNCAL、IDLE、安全引脚、
ADS ONLINE、Fault NONE，再仅写 `cal write 82.326 -19.887`；固件报告
written+verified，独立 `cal` 回读 VALID / 82.326 / -19.89。最终5秒100点均
0.0mmHg，ADS errors/recoveries均0。日志：`tmp/preflash_status_20261026.ndjson`、
`tmp/postflash_precal_status_20261026.ndjson`、
`tmp/postflash_cal_restore_20261026.ndjson`。本步骤未发送泵阀命令、未加压。

随后在同一镜像上完成两轮非人体低压动态门槛。主动急停轮以target50启动，
新鲜读数首次>=20时主机发送stop；观测峰值22.4mmHg，START至固件STOP回复
473ms，确认PC8 HIGH、PC0 LOW、PC1 HIGH。随后再次stop、vent，取得55个
命令后新鲜样本，末10个均0.0，再seal；最终PC0/PC1 LOW、PC8 HIGH、pump OFF。
日志：`tmp/linkpad_lowpressure_20261026-180136.ndjson`。

独立自然低压轮峰值50.7mmHg，hold后受控放气自然结束；Capture n377、
dropped0、duration9400ms、interval25ms。无BP Pump脉搏，故BP calculation
failed / map0是预期的无信号结果；Calc work257ms、wall370ms、max_step5ms。
收尾再次vent ->新鲜<=2 ->seal，安全引脚/ADS在线，USER_STOP为收尾锁存。
日志：`tmp/linkpad_low_natural_20261026-180223.ndjson`。

该capture的实板`bp.capture/2`完整导出为begin+377 point+恰好一条valve+
features+end，hash2688858164，固件字段`CAPTURE_VALVE_20261025`。valve聚合：
pulses48、period_min/max=200ms、on_min/max=1/4ms；低压无脉搏轮没有>=5mmHg
相邻跃变，因此steps0和九个phase桶全0符合预期。严格解码和真实生产C回放
通过：所有tick间隔25ms，包络/平滑最大误差0，位模式、特征、validity相等。
原始日志及报告：`tmp/capture_export_20261026-180333.ndjson`、同名前缀
`.csv`、`.verified.ndjson`、`.replay.json`。导出后5秒100点0.4..0.5mmHg，
最终只读预检压力0.2、PC0/PC1 LOW、PC8 HIGH、pump OFF。

## Standard BP `/2` 实板结果（2026-10-26 18:07—18:11）

用户确认非人体External Cuff+真实袖带、120/80mmHg、80BPM、Running后，仅执行
一轮。预检VALID/ONLINE、安全引脚及新鲜低压通过；target150，峰值152.1，
hold后自然放气。结果SBP113/DBP91/Pulse75/valid1；相对参考为-7/+11/-5，
valid1仅表示内部范围/顺序成立，不是准确性或临床通过。Capture n2225、
dropped0、duration55600ms、interval25ms；Calc work1605、wall2329、
max_step31ms。日志：`tmp/linkpad_standard_20261026-180709.ndjson`。

自然结束后执行stop、vent，等待命令后新鲜低压，再seal；最终PC0/PC1 LOW、
PC8 HIGH、pump OFF、ADS errors/recoveries0，target恢复50。第一次导出尝试因
主机额外严格的最近40点<=1mmHg门槛拒绝，尚未发出capture行；异常路径完成
stop/vent/seal。随后5秒压力稳定0.3..0.4，再次导出成功。失败前置日志：
`tmp/capture_export_20261026-180835.ndjson`。

完整`bp.capture/2`为begin+2225 point+一条valve+features+end，
hash423181647，firmware=`CAPTURE_VALVE_20261025`。279次真实脉冲，period
min/max=200ms、on-time min/max=1/4ms；>=5mmHg的steps和九个phase桶均0。
严格解码、全部25ms tick及生产C回放通过；113/91/75/valid1、包络位、特征位
完全一致，包络/平滑最大误差0。文件：
`tmp/capture_export_20261026-180916.ndjson`、同名前缀`.csv`、
`.verified.ndjson`、`.replay.json`。

离线只读差分显示最大下降-3.933mmHg（index504，MAP前19点/475ms），最大
上升+1.718mmHg；6个>=2mmHg和4个>=3mmHg变化全部位于
`elapsed_ms % 200 == 0`，但没有>=4或>=5mmHg变化。相较旧`/1`轮的
-14.3/+14.9mmHg冲击，大冲击未复现；本轮支持“较小阶跃仍与阀调度相位
关联”，不能证明阀导致MAP/DBP偏差，也不能证明阀无影响。未改算法或阈值。
最终只读预检压力0.0，封闭安全。运行时栈水位和三轮同镜像有效重复性仍待测。

后续Standard BP动态步骤仍需非人体：先断电泄压，检查短路/极性/共地；
保持现有已核实的 PB6/PB7 ADS1115、PB10/PB11 USART3、PC0/PC1 阀驱动和 PC8
泵继电器接线，不新增或猜测供电电压。上电先量关键电源与逻辑点，再确认
ADS ONLINE、校准82.326/-19.887 VALID、PC0/PC1 LOW、PC8 HIGH、pump OFF。
Keil Build0错0警告后才可 Download；全片擦除会清校准，下载后须在未加压状态
恢复并读回校准。先做低压非人体 stop/导出门槛，再由用户确认 BP Pump 2 的
External Cuff + 真实袖带、120/80mmHg、80BPM、Running 后做一轮 Standard BP。
自然结束后严格 `vent` -> 等命令后的新鲜 est 接近0且参考仪表确认 -> `seal`，
另在 BP Pump 2 面板 Stop。导出 `/2` 后验证 valve 聚合与压力跃变相位；未收到
完整 end/checksum、未过参考对比或只有软件 valid，均不能宣称直接因果或准确性。

## 本次交付及证据边界

新增 `bp_capture_export.[ch]`、只读采集接口及 `capture export` 命令，导出内部
标称 25ms 采样的全部记录、实际 MCU tick、压力、算法输入电压、完整计算包络、
特征点和采集时校准。导出逐主循环最多一行，不另复制 2800 点缓冲区。
采集中拒绝清除/写入校准，避免同一轮混用校准；导出不改变执行器 GPIO。
未修改算法数值计算、MAP 范围、窗口、SBP/DBP 阈值、补偿或安全门限。

新增离线工具 `blood pressure monitor/tools/bp_capture.py`，严格校验后生成
CSV/NDJSON，并编译真实 `bp_algorithm.c` 回放；没有设备连接或写命令能力。
`host_build.py` 复用 MSVC 环境发现，host runner 与固件编译入口分开。
Keil 工程已登记新增固件源文件及头文件；host 测试未加入固件。

已完成的软件验证：

- `python -m unittest discover -s 'blood pressure monitor/test' -v`：**70/70 通过**。
  包括原算法包络逐位回归、真实 C 导出/回放、失败/取消状态、2800 点边界、
  丢失/重复/篡改/截断、主循环调度及实际安全门槛检查。
- Keil ARMCLANG V6.22：**0 Error(s), 0 Warning(s)**。
  记录：`tmp/capture_export_build.log`；Code47680、RO5816、RW28、ZI63212 字节。
- `python 'blood pressure monitor/tools/check_firmware_budget.py'`：通过。
  RAM63240/65536 字节，余2296；预留栈4096，已知峰1192，额外余量1024。
  新增全局 RAM32 字节。**运行时栈水位尚未实测**。

软件交付当时**没有烧录、充气、操作阀门、改校准或改接线供电**；后续已按
下方步骤完成新版烧录和一次非人体50mmHg传输验收，证据见“实板验证结果”。

## 接线与上电检查

本功能无硬件变更，保持已核实的现有接线及供电。本说明不新增电压设定。
涉及模块型号/供电或逻辑电平有变化时，先查对应型号官方手册和实物丝印，
核实推荐/绝对最大电压、MCU 电平兼容、极性与上电顺序，再连接。

| MCU 引脚/外设 | 现有连接与检查 |
| --- | --- |
| PB6/PB7，I2C1 | ADS1115 SCL/SDA；沿用现有电平及上拉，地址0x48 |
| ADS1115 模拟输入 | 保持现有 MPXV5050GP 信号调理与输入连接，不改分压/PGA |
| PB10/PB11，USART3 | PB10(TX)→CH340 RX，PB11(RX)←CH340 TX；115200，沿用已核实电平 |
| PC0/PC1 | 阀1/阀2的现有驱动输入；禁止把线圈直接接 GPIO |
| PC8 | 现有低有效气泵继电器驱动输入；HIGH 为停泵 |
| 电源/地线 | MCU、ADS1115、传感器、串口及驱动按现有方案共地；保留已核实电源连接 |

操作顺序：先断电、泄压，不接人体；检查通断、短路、极性及共地；上电后先量
关键电源与逻辑节点电压，确认与已核实方案一致，再运行。接反电源、把驱动电源
接信号端或把不兼容电平接 MCU 均可能烧毁器件，发现不符立即停止。

气路沿用非人体 External Cuff + 真实袖带 + 三通至传感器 P1，P2 按现有方案通
大气；阀的断电常开旁路及泵出气口维持已验证封堵。BP Pump 2 的 Pressure Port
是测试接口。不得用内部小容积袖带替代，也不改为人体试验。

## Keil 编译与后续下载

打开 `blood pressure monitor/MDK-ARM/blood pressure monitor.uvprojx`，Build 并
确认0错误/0警告，再跑预算脚本。命令行 `UV4 -b` 仅构建，本次没有执行下载
`-f`。后续下载应在气路已泄压、无人体、泵停且接线检查通过后，通过 Keil
Download 执行。当前 UV4 下载配置会全片擦除，必须预期校准丢失并按下述安全
顺序恢复；不要使用存在兼容问题的 pyocd 下载路径。

下载后通过启动横幅或 `bp.capture/1` begin 的 `firmware` 字段确认
`CAPTURE_EXPORT_20261025`；当前 `status` 行本身不含 `sw`。读 `cal`，应保留
**82.326 / -19.887、VALID**（来源：
`calibration_data/manual_static_2026-10-25.json`）。若确实丢失且硬件配置未变，
先恢复 `cal write 82.326 -19.887`，再读回 VALID，确认前禁止加压。
`88.3/-19.96` 已过时，`26.5/-70.6` 属旧传感器，均不能照抄。

## 非人体验证顺序及预期现象

1. 先不充气：检查 `status`、`pins`、`cal`、`fault` 和新鲜压力流。独立参考仪表
   确认已泄压；验证停泵/stop 路径，随后 `vent` → 等新鲜 est 接近0且参考确认
   → **立即 `seal`**。封闭闲置应为 PC0 LOW、PC1 LOW、PC8 HIGH，ADS ONLINE。
   `stop` 打开放气，不能把 stop 后状态当作已 seal。
2. 尚无采集时 `capture export` 应拒绝，且不动作泵阀。导出要求 stream 开启、
   当前校准 VALID、ADS ready、压力样本≤250ms且[-5,+5]mmHg、执行器安全、
   无采集/计算活动；这些软件判据不能替代独立参考仪表确认。
3. 新一轮 Standard BP 采集属于后续单独授权步骤。保持 External+真实袖带，
   面板单位确认 mmHg/kPa 换算、参考设置及 Running；保留既有高压保持流程。
   本软件交付不自动开始该步骤，也不调整算法来掩盖失败。
4. 自然测量完成后等待 `[Calc]` 及 BP 成功/失败输出，不在计算中途 stop，
   否则只保留取消状态。自然 done 只关阀2，袖带仍可能有残压；必须再
   `vent` → 观察**命令之后的新鲜** est 接近0、独立参考确认 → `seal`。
   检查安全 pins、VALID/ONLINE、stream start，并保存全部原始 RX 文本。
5. 发送一次 `capture export`。预期 begin → n 条 point → features → end。
   导出期间不发送 status/pins/cal 等其他命令，也关闭上位机自动命令轮询；
   它们会取消导出。安全需要时始终可以 stop：它应取消传输并正常停泵泄压，
   随后仍须确认低压再 seal。未收到并验证 end 的传输不能作为完整数据。
6. 单独低压测试导出途中 stop、陈旧读数/stream off 拒绝和重新导出完整性；
   保留命令请求/响应与压力日志来量实际延迟，验证期间不加压。每条命令逐一
   等响应，现有 ISR 单 pending 槽并未变成 stop 优先队列，不能密集连发。
7. 最终 `vent` → 新鲜低压及参考确认 → `seal`，确认安全 pins。BP Pump 2 的
   rolling piston 需在其面板按 Stop；我们的 vent/seal 不会停止它。

原2秒主机数据新鲜度中止门槛保持不变。导出约数千行，实际耗时待测；持续检查
新鲜压力、无意外泵阀动作、串口丢行/截断、stop 响应和运行时栈水位。

## 协议及离线回放

完整合同见 `.trellis/spec/firmware/core/capture-export.md`。`bp.capture/1` 中
浮点数采用十进制 uint32 的 float32 位模式，避免小数打印损精度。point 的
`t` 是 MCU tick，`p` 为 mmHg，`v/e/s` 为 V；relay 的 `raw_kind=2` 表示
重建 sensor V，full control 的1表示 ADS pin V，不可混称。
calc2/3分别为完成有效/无效 BP，均有完整包络；calc0/4 为未算/取消，e/s=null。
FNV1a 覆盖 begin+point+features 原始 JSON 字节，不含换行与 end。

在项目根目录运行，输出名必须尚不存在：

```powershell
python 'blood pressure monitor/tools/bp_capture.py' capture.ndjson --csv capture.csv --ndjson verified.ndjson --report replay.json
```

输入可为直接串口日志或 OmniProbe 原始 text/RX NDJSON 包装，不能只用20Hz
samples 投影。默认需安装 MSVC C 工具；只检查/转存可加 `--decode-only`。
工具拒绝丢行、乱序、重复、溢出、非有限数、截断与 checksum 不符等情况。
CSV 保留 bits 与 MCU elapsed；报告列出每点包络误差、特征点比较、有效性、
源码 SHA256 及实际 tick 间隔范围。不承诺 ARM 与 MSVC 浮点逐位一致。

## 实板验证结果（2026-10-25 20:47—21:05）

- Keil `UV4 -f` 完成全片擦除、Programming、Verify OK，HEX SHA256 为
  `BF093D230A0008F61CC48FC8CFC73B8C1BE49116107A955952DB9CA64D8E6918`；日志
  `tmp/capture_export_flash_20261025.log`。擦除后先确认 PC0/PC1 LOW、PC8 HIGH、
  pump OFF、ADS ONLINE，再仅恢复并读回 `cal write 82.326 -19.887`。
- 空捕获导出被拒绝。非人体50mmHg自然采集峰值50.1，n321、dropped0、MCU跨度
  8000ms；无脉搏导致预期的 calc3 / BP invalid，计算 work218ms、wall314ms、
  max_step5ms。收尾严格执行 stop -> vent ->10条命令后新鲜低压 -> seal。
  原始日志：`tmp/linkpad_low_natural_20261025-210043.ndjson`。
- 完整导出 begin+321 point+features+end，hash211184480，begin到end 5596ms；期间
  107条压力记录，最大宿主到达间隔54ms。MCU所有相邻tick均25ms。生产C回放
  包络/平滑最大误差0，位模式、特征和validity一致。日志及报告：
  `tmp/capture_export_20261025-210420.ndjson`、同名前缀`.replay.json`。
- stream off/陈旧门槛正确拒绝且恢复后收到新鲜流。导出27条记录时发送stop，
  无end，宿主观测安全响应23.2ms；随后 vent ->新鲜低压 ->seal，重新完整导出
  得到相同hash。日志：`tmp/capture_stream-reject_20261025-210350.ndjson`、
  `tmp/capture_abort_20261025-210404.ndjson`。
- 最终只读检查：VALID/ONLINE，PC0/PC1 LOW、PC8 HIGH、pump OFF，92条新鲜压力
  末值0.0。`USER_STOP` 是本次中止/收尾的预期锁存状态。上述宿主时间包含桥接
  和串口开销；sampleRateHz=0不代表上位机已知真实采样率。
- 经用户确认 External Cuff+真实袖带、Standard120/80mmHg、80BPM、Running 后，
  新版完成一轮自然测量：峰值150.3，n2089、dropped0、跨度52200ms；固件输出
  93/90mmHg、56BPM、valid1，计算work1513/wall2183/max_step31ms。结果相对参考
  明显偏差，valid1只表示内部范围/顺序校验通过，不是准确性通过。日志：
  `tmp/linkpad_standard_20261025-210904.ndjson`。
- 完整波形导出hash3282054663，begin到end37163ms；期间697条压力记录，最大宿主
  间隔60ms。生产C回放包络/特征/validity逐位一致。第一次重导前置低压门槛未
  满足；第二次在point约1250时实时压力瞬态到8.3mmHg，正确按>5门槛中止且无
  end，执行vent/seal后第三次完整成功。完整日志/CSV/报告同前缀：
  `tmp/capture_export_20261025-211153.*`；门槛中止日志：`...-211047.ndjson`。
- 选点证据：MAP=index606/P97.0，平滑包络53.67mV；SBP原始=index225/P103.2，
  DBP原始=index625/P95.3，固定补偿后成为93/90。相邻压力绝对变化>=4mmHg共
  42次，其中20次正好位于200ms周期边界；最大单点跌落/回弹为-14.3/+14.9。
  这与阀2的200ms脉冲调度强相位关联，但当前导出不含GPIO/on_ms，不能当作
  直接因果证明。不得据此直接调阈值，应先增加/取得阀状态关联证据。
- 脉率证据：算法只用最前256点。该窗56.2BPM峰0.3031，仅比84.4BPM峰0.3022
  高约0.3%，最大bin规则选择56；后续7个256点窗的主峰大多为75或84.4BPM。
  因而错误脉率来自取窗/近并列选峰，不是导出或回放不一致。

本轮完成的是低压传输/回放/中止验收，不是 Standard BP、临床准确性或运行时
栈水位验收。BP Pump 2 rolling piston 是否已在面板 Stop 仍由操作者独立确认。

## 未完成项与下一步判据

19:40 原日志 `tmp/linkpad_standard_20261025-194047.ndjson` 没有内部完整波形，
无法事后回放。已知直接拒绝条件为 DBP93.7 > MAP92.9，根因尚未确定。
下一轮应先取得可校验完整性的新波形，再看 MAP 后压力逆序、包络及特征点，
不得用合成数据冒充实测或通过调阈值把失败变成通过。

新版下载、低压导出/停止响应及一轮完整 Standard BP 波形/回放/选点分析已完成；
运行时栈水位和阀状态直接关联尚未实测。新版只有这一轮固件valid但参考偏差大的
自然 BP，三轮同镜像有效重复性未完成。模拟器结果不代表临床准确性，也不代表
ISO 81060-2 合规。长期 bring-up 任务继续 in_progress。

## `/2` 阀关联与第三轮结果（2026-10-27）

本轮保持非人体、External Cuff+真实袖带、BP Pump 2 设为120/80mmHg、80BPM。
固件 `CAPTURE_VALVE_20261025` 在150.3mmHg停泵并保持后完成自然放气，输出
103/82mmHg、84BPM、valid1；Capture n2129、dropped0、跨度53200ms、间隔25ms。
计算耗时work1545ms、wall2224ms、max_step31ms。`valid1`仅表示固件内部有效性
检查通过，不表示模拟器准确性或临床准确性通过。

保留波形成功导出为`bp.capture/2`：begin1+point2129+valve1+features1+end1，
hash27142329；所有相邻MCU tick均25ms。阀聚合记录267次脉冲，周期200..200ms，
on-time 1..5ms；以5.0mmHg为门槛共4个相邻跃变，phase桶为
`[3,1,0,0,0,0,0,0,0]`。最大上升+5.367668mmHg位于index409/phase42ms，
最大下降-7.810104mmHg位于index408/phase17ms，两者记录on-time均5ms。

生产C同源回放复现103/82mmHg、84BPM；MAP为index700/88.38955mmHg，原始
SBP/DBP特征为113.538109/87.66534mmHg。包络及平滑包络最大误差均为0，
包络位模式、特征位模式和validity全部一致。原始与派生产物为
`tmp/capture_export_20261027-214442.ndjson`、同名前缀`.csv`、
`.verified.ndjson`和`.replay.json`；测量日志为
`tmp/linkpad_standard_20261027-214101.ndjson`。

导出后复核VALID/ONLINE、ADS errors/recoveries均0、PC0/PC1 LOW、PC8 HIGH、
pump OFF；5秒快照100点est均0.0mmHg。安全收尾已按`vent` ->新鲜低压->`seal`
完成；串口连续新鲜样本回到约0mmHg后按新约定判为外部BP已自动停稳。

同镜像三轮valid结果为113/91@75、99/81@75、103/82@84。描述性统计：SBP
均值105.0、样本SD7.21、极差14mmHg；DBP均值84.67、样本SD5.51、极差10mmHg；
脉率均值78.0、样本SD5.20、极差9BPM。仅第一轮与本轮保留完整且已验证的`/2`
波形；第二轮波形因随后MCU复位丢失，因此不能声称已完成三轮完整波形重复性。
运行时栈水位仍未测，长期任务继续in_progress。

## 连续三轮完整波形批次（2026-10-27 21:41—22:08）

在同一固件、校准、External Cuff、120/80mmHg、80BPM设置下连续取得三轮完整
`bp.capture/2`波形，结果依次为103/82@84、118/88@75、114/90@75。三轮分别为
2129/1921/1737点，跨度53200/48000/43400ms，均dropped0且相邻MCU tick严格25ms；
生产C回放均与板端结果、包络、平滑包络、特征位模式和validity完全一致。

第二轮hash2299046525，阀脉冲241次、周期200..200ms、on-time1..5ms、>=5mmHg
跃变0次；第三轮hash332354659，阀脉冲218次、周期200..200ms、on-time1..4ms、
>=5mmHg跃变0次。与第一轮4次>=5mmHg跃变对照，说明大跃变并非每轮稳定出现，
当前证据不足以断言阀因果或据此调参。

本批均值/样本SD/极差：SBP 111.67/7.77/15mmHg，DBP 86.67/4.16/8mmHg，
脉率78.0/5.20/9BPM。三轮完整波形采集门槛已完成，但不代表模拟器准确性、
临床准确性或ISO81060-2合规；运行时栈水位仍待测。

操作约定更新：External Standard BP在外部压力释放后会自动停。后续以导出预检
至少40条连续新鲜串口压力稳定于`[-2,+1]mmHg`作为已停稳/可导出判据，不再每轮
要求面板Stop；只有压力不回零、持续波动或下一轮不能开始时才检查面板状态。
固件侧仍严格执行`vent` ->新鲜低压->`seal`。
