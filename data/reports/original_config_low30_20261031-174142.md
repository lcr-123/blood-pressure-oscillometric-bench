# 原配置30 mmHg低压复测：失败

用户明确要求保持原配置重测；未新增二极管、未声称泵支路物理隔离。非人体台架沿用既有条件，12V电压未独立测量。通过EK-OmniProbe TCP8765及GUI写权限执行一次，不直接打开COM。未改固件或校准。

## 实测结果

- 前检：IDLE、ADS ONLINE、cal VALID 82.326/-19.89、fault NONE、UART rx_errors0、ADS errors0/recoveries0，PB8 HIGH/PC1 LOW/PC8 HIGH。5秒基线100条新鲜近零。
- 命令target30、start；到压回显30.8 mmHg，紧接着保持阶段Pressure read failed，固件emergency vent。本轮失败；没有新的完整波形或有效BP结果，不自动重试。
- 保留的ADS首次失败诊断：stage5 / status2(HAL_BUSY) / reg01 / err0x20(TIMEOUT) / state0x20 / SR1=0 / SR2=0x2(BUSY) / CR1=0x0801 / GPIOB=0xFFFB / SCL1 / SDA1；首错当时errors1/recoveries0，收尾查询errors1/recoveries1。与此前部分WRONG_START0x200不同，不能混称同一错误码。
- UART rx_errors0，未观察Boot行。到压提示中出现stopping pEip异常字样，原样保留；不能仅凭UART硬件计数0排除文本/传输异常。
- stop覆盖末态Fault为USER_STOP；原始保持失读/紧急放气行及ADS保存诊断仍在，不能把USER_STOP当最初原因。

## 收尾

已收到stop和vent回显；vent后60条连续新鲜VALID估压<=0.3 mmHg，宿主时间跨度2950ms，再seal。密封后5秒100条样本均est0，最终PB8 HIGH/PC1 LOW/PC8 HIGH、pump OFF、manual OFF、ADS ONLINE。试验失败与收尾完成分别记录。未要求改变负载电源；target保留为本轮30 mmHg，未继续启动。

## 结论与限制

原配置的到压/停止附近故障再次复现，尚未修复。结合负载断电对照，继续支持检查负载切换、供电/接地与I2C外设状态，但单次结果不能锁定阀线圈反冲、泵故障或唯一软硬件根因。保护对照尚未执行。

本轮未改变接线，无Keil编译/下载；原配置接线沿用当前完整接线方案。复现项是到压后保持失读及ADS计数增加；健康预期应为保持/放气持续读取且计数不增加。

## 证据

- 原始记录：data/raw/development_20261031/original_config_low30_20261031-174142.ndjson
- 原始SHA256：87d869bf073e0e400eb902c1a2ca686b0dbff1606bb868ec761f7252b8eaa4bb
- runner：tmp/bp_original_config_retry_20261031.py
- runner SHA256：9b5f0c911414f59bbbef1a8c48c50cb0b54718d15f60d87b49bd70dd6704cbaf
- 复用HoldBridge/原低压流程及stable closeout；语法检查通过，离线失读/乱码/Boot guard三项通过。原始审核确认仅一次start、stop->vent->新鲜零->seal，hash匹配。
