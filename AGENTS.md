# AGENTS.md

本仓库是 STM32F103ZET6 示波法血压采集固件及非人体台架数据集工程，不是 Web 或全栈项目。

## 项目方向

当前目标是：开放袖带示波法压力波形数据集、参考脚本和第三方可复现验证，用于数据论文。入口资料是：

- [README.md](README.md)
- [血压仪项目方向与进展.md](血压仪项目方向与进展.md)
- [血压仪完整接线方案.md](血压仪完整接线方案.md)

当前硬件链路使用 `MPXV5050GP + ADS1115 + STM32F103ZET6`。旧型号、旧分压和旧校准值不属于当前配置，不能作为接线或烧录依据。

## Trellis 与固件规则

- 修改固件前读取 `.trellis/spec/firmware/core/index.md` 及当前任务下的 `prd.md`、`design.md`、`implement.md`。
- 每次新增或移动 `.c` / `.s` 文件，都同步检查 `blood pressure monitor/MDK-ARM/blood pressure monitor.uvprojx`。
- 修改完成后写出接线方法、非人体验证步骤、Keil 编译/下载步骤、串口观察项和预期现象。
- 固件必须保持 HAL/Keil 兼容；不要在采集主循环中加入无界阻塞或高频 printf。

## 当前硬件基线

- 传感器：MPXV5050GP；P1 接压力侧，P2 通大气。
- ADC：ADS1115 AIN0，I2C1 `PB6/PB7`，地址 `0x48`，VDD 3.3 V。
- 串口：USART3/CH340，115200 8N1。
- 充气阀：PB8 开漏、无内部上下拉、低电平吸合，初值 HIGH（释放）；旧 PC0 已停用。放气阀 PC1 高有效，泵 PC8 低有效。继电器先于 MCU 断电，MCU 先于继电器上电；接线详见当前方案。
- 校准：`cal clear` 后 `cal write 81.529 -20.03`（2026-11-26 重标定，读回
  `slope=81.529 intercept=-20.03`）。**必须先 `cal clear`**：`bp_cal.c:137` 的
  `BP_Cal_Write()` 只 Program 不 Erase，用不同值覆盖已有记录必定失败且旧记录静默保留。
  旧轴 `82.326 / -19.887` 只对 2026-11-26 之前采的导出成立。
- 传感器供电 VS 实测 **5.149 V**（2026-11-10，21:37 曾读 5.133，15 分钟内变 0.31%，
  该轨不稳），记录见 `calibration_data/supply_measurement_2026-11-10.json`。
  该传感器是比率式输出，VS 偏离 5.0 V 会整体改变刻度；重标定后的斜率隐含 VS≈5.111 V，
  与实测差 0.74%（旧轴隐含 5.062 V，差 1.73%），成因仍未定（供电漂移 vs 器件增益偏差）。
- 气路：BP Pump 2 Pressure Port 经三通接传感器和真实袖带；泵出气口、阀1/阀2断电常开口封死。

## 气路铁律

完整收尾顺序固定为：`vent` -> 等连续新鲜串口样本 `est≈0`（或目标值）-> `seal`。阀2不能长期通大气。BP Pump 2 External 模式在外部压力卸除后会自行停止；串口新鲜样本稳定在约 0 mmHg 可作为操作判据。

所有气泵、阀门、压力传感器和人体接触相关工作，先做非人体安全验证；当前项目默认禁止人体接入。

## 上电建议

给出任何硬件连接前，先查对应官方数据手册，确认供电范围、逻辑电平、引脚别名、极性和上电时序。先断电测通断/短路，再上电量关键点电压，最后运行；不确定时标记待查证，不凭经验给出电压。

## 当前脚本和资料

- `bp_static_calibration.py`：BP Pump 2 Source 静态点采集。
- `bp_serial_logger.py`、`bp_bridge_logger.py`：串口/桥联连续记录。
- `blood pressure monitor/tools/bp_capture.py`：波形校验和离线回放。
- `calibration_data/`：当前校准和零点检查结果。
- `data/raw/`：历史原始波形，须先审核再进入公开数据集。
- `tmp/pdfs/`：BP Pump 2 当前手册和相关工具资料。

## 语言

与用户沟通使用简体中文；代码标识符、命令、路径和必要的英文技术名词保持原文。
