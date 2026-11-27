# 示波法袖带压力波形采集工程

本工程面向非人体台架采集：使用 BP Pump 2 产生可重复压力/脉搏参考，经 `MPXV5050GP + ADS1115 + STM32F103ZET6` 采集袖带压力波形，再由上位机保存为可复现分析的数据。

## 从这里开始

1. 读 [血压仪项目方向与进展.md](血压仪项目方向与进展.md)，了解当前目标和阶段。
2. 读 [血压仪完整接线方案.md](血压仪完整接线方案.md)，按非人体安全顺序接线。
3. 静态校准已完成；下一批动态波形先按 [采集记录 v1](data/capture_protocol_v1.md) 记录面板设置、气路、校准和零点。
4. 使用 `blood pressure monitor/tools/bp_capture.py` 严格校验和回放单轮波形，使用 `bp_capture_catalog.py` 审核历史导出清单。
5. 原始样本放在 [data/raw/](data/raw/)，历史审核见 [数据报告](data/reports/capture_catalog_20261031.md)；公开样本须另行通过质量审核。
   2026-11-01 的非人体开发批次见[数据清单](data/reports/standard_bp_development_manifest_20261101.md)与[离线包络弃判](data/reports/standard_bp_envelope_gate_20261101.md)；候选包络不等于准确血压。
   多档特征与建模缺口见[多档包络建模准备](data/reports/standard_bp_multisetting_study_20261101.md)。
6. 历史论文页面图片位于 `archive/historical/reference-pages/`，仅供追溯；该目录未获授权再分发。
7. 要把数据发给第三方，用发布包而不是整库：`python tools/release_package.py --out dist/bp_waveforms_20261126`。

## 当前基线

- 传感器：MPXV5050GP，P1 压力侧，P2 大气侧。
- ADC：ADS1115 AIN0，地址 `0x48`。
- 校准：`81.529 mmHg/V`、`-20.03 mmHg`（2026-11-26 重标定；17 点静态交叉验证落规格
  8/17 → 17/17，最坏总误差 5.715 → 2.840 mmHg）。此前所有导出与报告里的数字都建立在
  旧轴 `82.326 / -19.887` 上，引用时必须写明轴；两轴的换算与代价见
  [压力轴重标定](data/reports/pressure_axis_refit_20261126.md) 与
  [账本重算](data/reports/pressure_axis_rebook_20261126.md)。
- 串口：USART3/CH340，115200 8N1。
- 充气阀继电器：PB8 开漏低有效（替代 PC0）；放气阀 PC1 高有效，泵 PC8 低有效。
- 静态校准气路：BP Pump 2 Pressure Port -> 三通 -> 传感器和真实袖带；常开口与泵出气口封死。动态采集须按本轮完整气路另行记录。

## 许可与引用

- **代码 MIT**（`LICENSE`）、**数据 CC BY 4.0**（`data/LICENSE`）。两者的分界、不在授权
  范围内的内容、以及推荐的中英文署名文字见 `LICENSE.md`。
- 机器可读的引用记录见 `CITATION.cff`。引用时**必须同时带上 commit hash**：报告与冻结
  记录和代码在同一条 git 历史里，只给版本号指认不了"哪一版报告"。
- 许可只管"谁做的"；"这份数据能证明什么、不能证明什么"由
  [已知边界](data/reports/dataset_limitations.md) 的「引用时必须声明的最小集」管。两件事
  互不替代，`LICENSE.md` 里写了这句。
- **可以直接下载的小包**：62 轮已发布波形 + 最小文档集，147 个文件 / 30.1 MB，自带
  `checksums.sha256`，用 `python tools/verify_release_package.py <目录>` 独立校验。
  已发布为 GitHub Release **<https://github.com/lcr-123/blood-pressure-oscillometric-bench/releases/tag/v2026-11-26>**，
  附件 `bp_waveforms_20261126.zip`（约 5.6 MiB，`unzip` 后即上述 147 个文件），
  不必克隆 362 MiB 的仓库即可拿到这 62 轮。附件的 SHA-256 以 GitHub Release 页面
  显示的 asset digest 为准——**这个哈希刻意不写进仓库文件**，因为 zip 内含本 README，
  写进去就会自指、每次重打都变。
  包的身份证（62 个 `run_id`）在 `data/release/published_corpus_20261126.json`，
  做法与取舍见 [发布包与数据可用性](data/reports/release_package_20261126.md) 的 §7.1。

## 资料边界

当前有效配置只以入口文档、固件工程、校准目录和当前手册为准。历史排错日志和 `archive/historical/` 内容不再作为操作说明。用户指定的论文 `基于示波法的无创血压模拟系统的研制_胡海洋.pdf` 应保留；当前工作区未找到完整文件，待从原始来源补回。

## 固件

Keil 工程：`blood pressure monitor/MDK-ARM/blood pressure monitor.uvprojx`。修改固件后必须确认源码已加入工程，Rebuild 通过后使用 `UV4 -f` 下载；全片擦除后需重新写入并读回校准参数。
