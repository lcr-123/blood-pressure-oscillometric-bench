# 历史固件波形导出审核

本报告由 `bp_capture_catalog.py` 对原始目录只读生成。详细逐文件结果和 SHA-256 见同名 JSON。
严格解码包含固件记录计数、顺序和 FNV 校验；相同 MCU 记录只算一轮。
本次未运行生产 C 回放，也未核对 BP 面板设置或独立参考压力。

## 结果

- 扫描文件：102；严格解码通过：83；失败：19。
- 独立记录序列：42；重复文件：41。
- 可直接发布的正式样本：0。历史文件属于方法开发集，不能充当独立验证集。
- `calc_state` 是固件算法状态，不代表传输质量、面板真值或临床准确性。
- 压力是本机传感器估计值，时间间隔来自 MCU tick；不能代替独立参考仪表。
- 42 轮中的固件算法状态：有效 24、无效 11、未计算 7；采集时长不足 20 秒 7 轮。

## 独立记录概览

| 文件 | 点数 | 时长 s | 压力范围 mmHg | 间隔最大 ms | >25ms 间隔 | calc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| capture_export_20261025-210212.ndjson | 321 | 8.000 | 14.6..31.4 | 25 | 0 | 3 |
| capture_export_20261025-211153.ndjson | 2089 | 52.200 | 14.9..132.3 | 25 | 0 | 2 |
| capture_export_20261026-180333.ndjson | 377 | 9.400 | 14.3..36.1 | 25 | 0 | 3 |
| capture_export_20261026-180916.ndjson | 2225 | 55.600 | 14.8..134.4 | 25 | 0 | 2 |
| capture_export_20261027-214442.ndjson | 2129 | 53.200 | 14.7..133.8 | 25 | 0 | 2 |
| capture_export_20261027-220211.ndjson | 1921 | 48.000 | 14.7..135.3 | 25 | 0 | 2 |
| capture_export_20261027-220714.ndjson | 1737 | 43.400 | 14.6..134.7 | 25 | 0 | 2 |
| capture_export_20261028-113752.ndjson | 2305 | 57.600 | 13.3..135.6 | 25 | 0 | 2 |
| capture_export_20261028-114718.ndjson | 2233 | 55.800 | 14.9..135.7 | 25 | 0 | 3 |
| capture_export_20261028-115410.ndjson | 2377 | 59.400 | 14.9..135.4 | 25 | 0 | 3 |
| capture_export_20261028-115823.ndjson | 2241 | 56.000 | 14.5..135.4 | 25 | 0 | 2 |
| capture_export_20261028-120531.ndjson | 2289 | 57.200 | 14.9..134.0 | 25 | 0 | 3 |
| capture_export_20261028-120941.ndjson | 2217 | 55.400 | 14.7..136.2 | 25 | 0 | 3 |
| capture_export_20261028-121553.ndjson | 2379 | 59.450 | 15.0..136.6 | 25 | 0 | 2 |
| capture_export_20261028-123230.ndjson | 2242 | 56.025 | 14.9..135.4 | 25 | 0 | 2 |
| capture_export_20261028-163539.ndjson | 2161 | 54.000 | 14.8..135.5 | 25 | 0 | 2 |
| capture_export_20261028-170426.ndjson | 3153 | 78.800 | 15.0..174.2 | 25 | 0 | 2 |
| capture_export_20261028-172032.ndjson | 2097 | 52.400 | 15.0..134.6 | 25 | 0 | 3 |
| capture_export_20261028-173648.ndjson | 2177 | 54.400 | 14.7..134.5 | 25 | 0 | 2 |
| capture_export_20261028-175901.ndjson | 1921 | 48.000 | 14.3..136.3 | 25 | 0 | 2 |
| capture_export_20261028-180524.ndjson | 2009 | 50.200 | 14.9..135.0 | 25 | 0 | 2 |
| capture_export_20261028-181030.ndjson | 2057 | 51.400 | 14.8..136.2 | 25 | 0 | 2 |
| capture_export_20261028-194221.ndjson | 2409 | 60.200 | 14.7..137.8 | 25 | 0 | 2 |
| capture_export_20261028-203223.ndjson | 2882 | 72.025 | 41.5..139.5 | 25 | 0 | 0 |
| capture_export_20261028-205246.ndjson | 643 | 16.050 | 109.3..135.2 | 25 | 0 | 0 |
| capture_export_20261028-210148.ndjson | 546 | 13.625 | 109.9..137.9 | 25 | 0 | 0 |
| capture_export_20261028-211130.ndjson | 920 | 22.975 | 43.3..101.1 | 25 | 0 | 0 |
| capture_export_20261028-212208.ndjson | 2185 | 54.600 | 14.7..137.0 | 25 | 0 | 3 |
| capture_export_20261028-222538.ndjson | 739 | 18.450 | 124.1..164.8 | 25 | 0 | 0 |
| capture_export_20261028-223729.ndjson | 2569 | 64.200 | 14.6..165.6 | 25 | 0 | 3 |
| capture_export_20261028-232501.ndjson | 2921 | 73.000 | 14.6..165.9 | 25 | 0 | 3 |
| capture_export_20261029-104132.ndjson | 2753 | 68.800 | 14.8..166.2 | 25 | 0 | 2 |
| capture_export_20261029-112521.ndjson | 2761 | 69.000 | 14.6..165.6 | 25 | 0 | 2 |
| capture_export_20261029-112950.ndjson | 2889 | 72.200 | 13.3..166.1 | 25 | 0 | 2 |
| capture_export_20261029-113351.ndjson | 2673 | 66.800 | 14.7..165.7 | 25 | 0 | 2 |
| capture_export_20261029-115718.ndjson | 2249 | 56.200 | 14.8..135.6 | 25 | 0 | 2 |
| capture_export_20261029-120105.ndjson | 2193 | 54.800 | 14.8..135.5 | 25 | 0 | 3 |
| capture_export_20261029-120520.ndjson | 2345 | 58.600 | 14.8..137.2 | 25 | 0 | 2 |
| capture_export_20261029-123637.ndjson | 2201 | 55.000 | 14.8..136.3 | 25 | 0 | 2 |
| capture_export_20261029-175604.ndjson | 160 | 3.974 | 57.5..58.1 | 25 | 0 | 0 |
| capture_export_20261029-211027.ndjson | 2009 | 50.200 | 15.0..135.6 | 25 | 0 | 2 |
| capture_export_20261030-final.ndjson | 400 | 9.975 | 54.0..55.6 | 25 | 0 | 0 |

## 解码失败

| 文件 | 原因 |
| --- | --- |
| capture_export_20261025-211025.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261025-211047.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261026-180835.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261027-214231.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261027-215951.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261027-220537.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261028-111017.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261028-113643.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261028-114638.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261028-115720.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261028-120843.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261028-121428.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261028-123123.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261028-163445.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261028-203147.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261028-232144.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261029-103539.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261029-112422.ndjson | no complete capture end; never accept cancelled/truncated export |
| capture_export_20261030-194237.ndjson | no complete capture end; never accept cancelled/truncated export |

## 下一批采集门槛

1. 采集前记录 BP 模式、面板 SBP/DBP/BPM/各脉搏组容积、完整气路、固件 HEX 哈希和校准读回。
2. 记录采集前后零点、参考压力证据、原始日志 SHA-256 和环境/故障事件。
3. 严格解码通过后，再按预先冻结的质量规则审核；算法开发集与独立验证集分开。
4. 本目录尚未补齐上述标签，不能从文件名或固件算法输出反推面板真值。
