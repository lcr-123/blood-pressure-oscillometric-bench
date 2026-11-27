# ADS 首错证据保留与总线诊断

状态：代码、111项主机测试和Keil编译通过；15:34下载并Verify OK，校准恢复及空闲采样通过。15:38用户要求复测，单轮30mmHg试验再次失败，已完成卸压密封。
读取故障的物理原因仍未定位，不能标记修复完成。

15:38首错为stage5/HAL_ERROR/WRONG_START0x200，SR1=0x0010、SR2=0、
CR1=0x0101、GPIOB.IDR=0xFFFB、SCL1/SDA1、errors1/recoveries1。
到压回显30.9后保持期紧急放气，没有进入PWM；主机完成vent->新鲜近零->seal。
高电平快照不确定物理原因。详见`data/reports/ads_bus_retest_20261031-153810.md`。

## 已改行为

- 失败时在既有SR1/SR2后只读保存CR1及GPIOB.IDR，后者保留PB6/SCL、PB7/SDA、PB8。
- 保留原ADSdiag格式，新增低频ADSbus行，从故障快照解码SCL/SDA。
- 已离线后被拒绝的调用不再以ARGUMENT覆盖真正的总线故障，也不增加错误计数。
  实际初始化/探测/事务再次失败仍更新证据；恢复成功保留故障快照。
- 读取失败仍先返回，活动调用者停泵、关充气阀、紧急放气，之后才允许离线恢复。
- 固件标识`ADS_BUS_DIAG_20261031`。压力数据丢失仍使本轮无效。

## 软件验证

- 生产C驱动/控制22项测试通过；包含样本不变、无就地恢复、离线调用及成功恢复后
  的首错/CR1/IDR保留。全套111项测试通过，27.911s。
- Keil ARMCLANG6.22 Rebuild：0 errors、0 warnings。
- RAM63480/65536，余2056；栈4096，已知调用链1352+保留1024通过。
  SRAM较前版增加8B；运行时栈水位仍需新镜像实测。
- 全部Core/Src生产源码已登记uvprojx，主机测试未进入固件工程。没有新增生产C/S文件。
- 日志：MDK-ARM/test_ads_bus_diag_20261031.log、build_ads_bus_diag_20261031.log。

## 接线与上电

不新增接线。保持MPXV5050GP及现有分压、ADS1115 AIN0/VDD3.3V/地址0x48，
PB6=SCL、PB7=SDA；USART3经CH3401152008N1；充气阀PB8开漏低有效、
放气阀PC1高有效、泵PC8低有效。实际连接按当前《血压仪完整接线方案》。
ST官方数据手册DocID14611Rev12已有本地副本；本次不增加任何电气器件或供电设定。
未取得适配本板的勘误触发证据，不将BUSY直接归为芯片勘误。

原计划下载前请求负载断电确认。用户随后明确指示“烧录直接烧，不用老是问我”，
据此直接执行，改由串口核对新鲜校准零压及泵阀安全状态，并完成vent->新鲜零压->seal。
本次未获得或推断负载电源隔离，不能记作负载断电试验。后续烧录沿用用户授权，
自行核对可观测状态，不重复索取同一授权。涉及实际改线仍遵守继电器先断电、
MCU后断电，MCU先上电、继电器后上电的时序。

## Keil下载及非人体验证顺序

1. 打开MDK-ARM/blood pressure monitor.uvprojx，Rebuild零错误零警告；
   校验下列HEX哈希，在用户已授权范围内核对可观测安全状态后Download，要求Verify OK。
2. 从新鲜Boot行确认sw=ADS_BUS_DIAG_20261031，查询pins/status/cal/fault/stack。
   安全引脚PB8 HIGH、PC1 LOW、PC8 HIGH、pump OFF；PB8需已供电的外部继电器上拉。
3. 若下载全擦后校准UNCAL，按当前校准记录恢复`cal write 82.326 -19.887`并读回
   VALID/82.326/-19.89。未通过校准、近零、ADS在线、无故障门限不开始压力试验。
4. 先记录负载断电静态新鲜串口；确认正常再分离电气负载做有界对照，具体操作须
   根据当时供电/接线状态和负载规格确定。不能在未知阀工作制下长期通电。
5. 出错保留首份ADSdiag/ADSbus及切换上下文。SCL/SDA为0表示当时数字低电平；
   两者为1仍不能排除先前瞬态。实际0/1不是对电压或器件损坏的单独结论。
6. 根因处理后才重复30mmHg有界非人体试验；要求连续新鲜压力、ADS错误/恢复均0，
   串口无损坏、控制流程正常。故障恢复后数据继续不等于本轮通过。
7. 每次固定收尾vent->连续新鲜est接近0->seal，验证安全引脚，放气阀不长期通大气。
   压力传感器仍离线时依靠独立卸压，不能凭旧样本seal。

## 构建身份SHA256

- HEX：549ae75f62bec60108dbddd3053280fd92a38e49abd3b4fdd5032024d244e63b
- ads1115.c：e58863774d936db453fb971cd360e95c8b8fb975227952596abd51b750c0f223
- ads1115.h：73047bfe27592a871cec38109491d82b9819ae985a33bd68d66652004a059f51
- main.c：c6285983d18ce1c94a5526a0c9d0acdf65d66bfaf1703c29bfec66eb4d417e10
- bp_algorithm.h：599d2f6e64ba82a099e4a6850ef75cdfc4676ea78c5686de9c39125e0558ed1a

## 用户电压反馈

用户反馈“都3.2左右，现在”，未指明测点及单位。若指PB6/PB7对地约3.2V，
支持当时空闲高电平；万用表静态读数不能排除停泵切换的短暂干扰。未将此视为
负载已断电、已修改接线或可以下载的状态确认。

## 15:34实际下载与空闲验证

- 用户明确授权直接烧录，未重复要求物理状态回复。下载前旧固件state=EMERGENCY、
  ads=ONLINE、manual=OFF、泵OFF、sealed；新鲜样本为VALID近零。先保存旧故障：
  SENSOR_READ，stage5/status1/err0x200/sr1=0x0110/sr2=0，errors4/recoveries4。
  随后vent->十条连续新鲜VALID<=1mmHg样本->seal，核对安全引脚。
- Keil下载exit0、Verify OK、Application running，15:34:35；新鲜启动版本
  ADS_BUS_DIAG_20261031，HEX哈希与本文一致。未修改物理接线。
- 全片擦除使校准UNCAL，恢复既定`cal write 82.326 -19.887`，写入校验和读回均VALID。
- 恢复后9.949秒宿主时间窗口200条新鲜样本，raw1302..1305/均值1303.655，sensor225mV，
  est0。IDLE、ADS ONLINE、fault NONE、errors0/recoveries0，PB8 HIGH/PC1 LOW/PC8 HIGH/泵OFF。
  栈used1184/free2912/reserved4096/saturated0，为空闲路径实测，不代表完整压力流程峰值。
- ADSbus全零且stage0表示尚无故障快照，不能解释为SCL/SDA当前低电平。
  这次没有充气或新固件负载切换验收，读取问题的根因仍未解决。

记录：
- `data/raw/preflight/direct_flash_before_20261031-153350.ndjson`（旧故障查询）
- `data/raw/preflight/direct_flash_closeout_20261031-153416.ndjson`
- `data/raw/preflight/ads_bus_diag_flash_20261031-153418.ndjson`及同名metadata.json，
  SHA256 c5c2152400fed4d1cfd1697536da34ca4b61a7d90e54a0bf52540194ed9dc7d2。
- `data/raw/preflight/ads_bus_diag_cal_20261031-153505.ndjson`及同名metadata.json，
  SHA256 a2aa1745f3fee6057c0e04d2d981222ad4ba0dca2b5663f57d3422c7082bab6d。
- `blood pressure monitor/MDK-ARM/download_ads_bus_diag_20261031-153418.log`。
