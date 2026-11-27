# 固件二进制归档

`blood pressure monitor/MDK-ARM/blood pressure monitor/` 下的 `.hex`/`.axf` 是**当前**
构建产物，会随每次代码改动而变。数据集元数据里的 `firmware_hex_sha256` 指向采集当时
烧录的那一份，所以那几份必须单独留存，否则以后无法复现。

## 已知二进制

| 文件 | sha256 | 字节 | 说明 |
|---|---|---|---|
| `PEAK_WINDOW_20261105_bb33a3a4.hex` | `bb33a3a40471ba24b9e677c566b83ec19c4cf38393b687684f73d1a618418a96` | 183426 | **2026-11-06/07 数据集全部 18 轮使用的固件**。`bp.capture/4` 的 `begin.firmware` 为 `PEAK_WINDOW_20261105` |
| 当前构建 | `61ca1da309439d9a4afa7f783aacbb56be56e4607cc09289a3729eb2e39f74ad` | 184146 | 同上，另加 `[Boot] reset_csr=` 复位来源诊断（见下） |

## 两份二进制的关系

当前构建与数据集固件**算法完全相同**，只多了一段启动期诊断：

- `Boot_CaptureResetCause()`：在 `HAL_Init()` 之前读 `RCC->CSR`，保存并清除复位来源标志
- `Boot_PrintResetCause()`：USART3 可用后打印 `[Boot] reset_csr=0x........ POR/PDR PIN IWDG ...`

这一段**不参与采集、不改变包络或压力换算**，所以 `BP_FIRMWARE_ID` 保持
`PEAK_WINDOW_20261105` 不变。代价是：**两份二进制的 `sw=` 字符串相同**，只能靠
`firmware_hex_sha256` 区分。任何新采集都必须记录该哈希。

## 为什么加这段诊断

2026-11-07 的 `standard120_080_target275_peakwindow_20261107-112327` 在放气结束 14 s
后发生一次未预期复位，采集只有 767 点。当时固件不读 `RCC_CSR`，只能靠串口时间戳反推：

- 最后一条 `[Pressure]` 到启动横幅仅 **0.184 s** → 排除 IWDG（4000 ms）超时
- 复位前 1 s 内 sensor 读数从 250 mV 塌到 129 mV（−48%），MPXV5050GP 为比率式输出，
  等价于 VS 掉到约 2.6 V → 指向电源塌陷而非软件

加上该诊断后，同类事件可直接读出 `POR/PDR`、`IWDG`、`PIN` 或 `SOFT`。

## 已验证

按 RESET 键后实测输出：

```
[Boot] reset_csr=0x04000000 PIN
```

`0x04000000` 仅 bit26 `PINRSTF` 置位，与按键复位一致；`PORRSTF` 未置位，说明清除
逻辑（`RMVF | 全部 RSTF`，RM0008 8.1.5）生效，下次读到的都是新事件。

## 烧录注意

Keil `Download` 在本工程执行的是 **Full Chip Erase**，会连校准记录一起擦掉。烧录后必须
按 `AGENTS.md` 要求写回并读回：

```
cal clear
cal write 82.326 -19.887
cal
```

期望读回 `[Cal] VALID slope=82.326mmHg/V intercept=-19.89mmHg`。
