# 非人体袖带波形采集记录 v1

本协议用于下一批**前瞻性** BP Pump 2 External Cuff 台架数据。历史调试导出保留在开发集，不能自动改标为独立验证集。固件 `bp.capture/3` 记录波形、MCU tick、校准和阀诊断，**不包含** BP 面板真值、完整气路或独立参考压力；这些须与原始导出同轮记录。

## 每轮记录模板

采集前创建一个与原始日志关联的记录；未知项写 `null` 并写原因，不根据文件名或算法结果补猜。

```yaml
run_id: null                         # 唯一编号，关联原始日志及面板照片
dataset_role: prospective_validation # 或 development；采集前确定
nonhuman_fixture_confirmed: null
bp_model: "BP Pump 2"
bp_mode: null                        # 面板实际模式，如 External Standard BP / User Defined
panel_sbp_mmhg: null
panel_dbp_mmhg: null
panel_bpm: null
panel_pulse_volume_profile_cc: null  # 各脉搏组分别记录；面板若不显示，说明原因
panel_evidence_path: null            # 本轮面板照片或设置记录
pneumatic_configuration: null        # BP口、袖带、P1、阀/泵和封堵逐项列明
cuff_volume_cc: null                 # 未实测则说明标称值来源
inflation_target_mmhg: null          # 本轮 MCU 设置和 BP 面板参考范围分别说明
acquisition_commands: null           # 含 start/hold/deflate/capture export 的实际命令与时间
deflation_start_est_mmhg: null       # 本机估计值，不当作独立真值
firmware_hex_sha256: null
calibration_readback: null           # slope/intercept/valid
leak_test_mmhg_per_min: null          # 写起始压力、时长、气路和结果
pre_capture_zero: null               # 串口新鲜 raw/sensor/est 范围与时间
post_capture_zero: null
capture_source_path: null
capture_source_sha256: null
verified_mcu_capture_sha256: null
reference_pressure_evidence: null    # BP面板/独立参考；不得把估计值当真值
reference_device_model: null         # 独立压力参考的厂家、型号及版本
reference_datasheet_path: null       # 官方量程、精度、分辨率和接口依据
reference_calibration_record: null   # 校准日期/证书；未知则记录原因
reference_pressure_node: null        # 参考测压端与袖带、MPXV5050GP P1 的实际节点
reference_raw_path: null             # 独立、连续、带时间戳的原始记录
reference_raw_sha256: null
reference_sample_timing: null        # 实测采样间隔、时钟来源和丢样信息
reference_sync_method: null          # 与 MCU tick/串口记录的对时事件及误差
reference_added_volume_or_tubing: null # 新增容积/软管/接头，改变气路需记录
serial_error_or_fault_events: null
operator_notes: null
exclusion_reason: null
missing_value_reasons: {}            # 逐字段说明为何无法取得
```

## 采集与审核顺序

1. 非人体固定，按现行接线方案核对电源、共地和压力链路；保持可随时停止气泵和泄压。先记录 BP 面板设置、校准读回、固件 HEX 哈希、气路和零压原始信号；零点或 ADS 异常时暂停正式采集。
2. 按本轮面板设置采集，原始串口或 EK 桥日志直接写入 `data/raw/` 新文件，保留全部原文。记录异常和停止原因，不覆盖失败轮次。
3. 完成后 `vent`，确认连续新鲜估计压力约 0，再立即 `seal`；BP 外部压力卸除后若已自动停稳，无需每轮再按面板 Stop。记录采集后零点与面板状态。
4. 用 `bp_capture.py` 严格解码并保存经过验证的 MCU 记录。独立 C 回放另行运行、另行记录；传输校验通过不代表波形质量通过。
5. 检查 tick 间隔、压力覆盖、波形瞬态、零点漂移、气路漏气、面板标签和参考证据。排除理由在分析前冻结；`calc=2`、算法 SBP/DBP 或单个 MAP 均不能替代这些检查。完整原始导出不得裁掉低压尾段；离线包络分析应预先声明压力/样本窗口及排除规则，并报告低压侧覆盖和窗口外尾段。尾段弱包络或约 1 mmHg 以下封阀后回升，单独不阻断开发性采集；失读、超压、明显残压或安全收尾失败则停止充气。正式验证仍需完整面板标签、气路和独立参考证据。

首先做同一设置的小批重复试验，确认采集完整性和零点稳定，再扩展压力、心率、脉搏容积条件。开发/验证划分须在算法调参前确定；本数据集只支持非人体台架重复性分析，不得宣称临床准确性。

若加入独立压力参考，必须先依据其官方手册核对测压口、量程、供电、接口和额定值，并在断电卸压时接至与袖带及 MPXV5050GP P1 相同的压力节点。新增支路会改变气路容积和可能的压力响应，须重新记录气密性与零点，不能把旧轮次直接视为同条件。同步参考需保存独立原始轨迹、真实时间基与对时误差；BP Pump 2 Standard BP 面板预设和 MCU 同一传感器估压均不能代替它。若只发布原始开发波形，应明确标注参考缺失，不把该缺失解释为传输失败。
