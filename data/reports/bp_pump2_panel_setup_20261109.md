# BP Pump 2 面板设置：逐键步骤与检查点

日期 2026-11-09。对象是 Fluke Biomedical **BP Pump 2**（固件 `2780201 Ver 2.01S`，
序列号 `5788005`）。目标工况：**Standard BP / External Cuff / Preset 4**，
配合 MCU 采集。

> 依据：`tmp/pdfs/opmanual_text.txt` 第 3 章（`:1588-2035`）、表 3-2（`:1920-1955`）、
> 表 1-2 面板部件（`:563-607`）、FAQ（`:2912-2922`）。
> 凡是手册没写的，下面都标成「未查到」或「实测」，不凭经验补。

---

## 零、接线先确认（设置前的物理前提）

| 项目 | 要求 |
|---|---|
| 用哪个口 | **前面板 `Pressure Port`**（面板部件 I），不是背面的 `LEAK` / `PRESSURE RELIEF` |
| 接到哪 | 三通 A（与袖带、MCU 传感器 P1、阀2 上游同一节点） |
| 管子 | 4–6 mm 内径硅胶管，尽量短，两路内径一致 |
| MCU 侧阀2 | 必须能 `seal`（PC1=LOW） |
| 非人体 | 袖带缠硬芯，不接人 |

手册 `:604-607`：`Pressure Port` "Connects to the Non-Invasive Blood Pressure Monitor
for all pressure simulations and tests" —— 内部直连 20 cc 主气室与它自己的压力传感器。
接错到 `LEAK` 口，`[GAUGE]` 会读不到回路压力。

---

## 一、开机

1. 接好电源，按前面板电源键
2. 等自检结束，出现主菜单：

```
Fluke Biomedical BP Bump 2
   SETUP    PRESSURE    AUTO      PERFORM
             TESTS     SEQUENCE   SIMULATION
```

3. **先别急着进模拟**。如果上一轮留下过压力，先走一遍泄压：
   `PRESSURE TESTS` → `STATIC PRESSURE` → `GAUGE` → 按 `VENT`（约 5 秒），
   屏幕 `Measured` 应回到 0。按 `HOME` 回主菜单。

---

## 二、进入 Standard BP（两种路径，任选）

- **路径 A（快捷）**：直接按数字键 **`4`**
- **路径 B（软键）**：`PERFORM SIMULATION` → `STANDARD BP`

手册 `:1895`："Access these simulations by pressing the 4 STANDARD BP number key."

进入后屏幕应显示（手册 `:1906-1915` 的原文布局）：

```
        Standard BP
        Preset # 1
        Cuff: External
  OPTIONS        CUFF
        ready ....
  120/
         80 (93)
  80 BPM
         0.68 cc
```

### 检查点 1 —— Cuff 必须是 External

看第二行 `Cuff:` 后面是 `External` 还是 `Internal Adult`。

- 若是 `Internal Adult`，按 **`CUFF` 软键**切换（手册 `:1956`：
  "Press the CUFF soft key to select Internal Adult or External cuff"）
- 循环切换，直到显示 `External`
- **不要停在 Internal Adult**：那个模式会把空的内部模拟袖带当负荷，
  我们的真实袖带就变成并联，容积和包络全部错

### 检查点 2 —— 确认 `Preset # 4`

按 **`OPTIONS` 软键**循环预设（手册 `:1918`），直到第一行显示 `Preset # 4`。
七个预设按表 3-2 循环（`:1920-1955`）：

| Preset | 血压 (MAP) | 心率 | 脉搏容积 |
|---|---|---|---|
| 1 | 120/80 (93) | 80 BPM | 0.68 cc |
| 2 | 150/100 (116) | 80 BPM | 0.65 cc |
| 3 | 200/150 (166) | 80 BPM | 0.60 cc |
| **4** | **255/195 (215)** | **80 BPM** | **0.55 cc** |
| 5 | 60/30 (40) | 80 BPM | 0.75 cc |
| 6 | 80/50 (60) | 80 BPM | 0.71 cc |
| 7 | 100/65 (76) | 80 BPM | 0.69 cc |

### 检查点 3 —— 三个数字必须同时对

停在 `Preset # 4` 后，屏幕上**三个数字必须和下面完全一致**：

| 屏幕项 | 必须是 | 常见的错误 |
|---|---|---|
| 血压 | `255/ 195 (215)` | 停在 Preset 3 的 `200/ 150 (166)` |
| 心率 | `80 BPM` | 无（七个预设都是 80） |
| 脉搏容积 | `0.55 cc` | 停在 Preset 1 的 `0.68 cc` |

**这三个数字是我们采集脚本的硬校验**：`--panel-preset 4` 会校验
`(SBP, DBP, MAP, dV) == (255, 195, 215, 0.55)`，只要面板实际不是这个，
元数据就是错的。所以**读一遍，不是扫一眼**。

> 关于 `(215)`：它不是物理目标，是 `floor((255+2×195)/3)` 的算术注释。
> 详见 `data/reports/map_bias_20261109.md`。评测 MAP 误差时不要直接拿它当真值。

---

## 三、要不要按 `START`？—— 不用

**BP Pump 2 在 External Cuff 模式下不需要按 START。** 它进入 `ready ....`
后就在等外部压力：一旦检测到袖带被充起来，就开始按预设注入脉搏。

我们这边的分工：

| 谁 | 做什么 |
|---|---|
| **MCU** | 充气到目标（275 mmHg）、按 profile 放气、封阀 |
| **BP Pump 2** | 只注入脉搏，不充气、不放气 |

证据（本项目实测，非手册）：
- 59 轮采集里从未按过 Tester 的 START，脉搏都正常出现
- `vent` 之后外部压力消失，Tester 自行停止注入（面板回到 `ready ....`）

> 手册 `:1957` 写的是 "Press Start on the NIBP unit" —— 那是让**被检血压计**
> 开始测量，不是让 Tester 开始。Tester 没有需要按的 START。

### 怎么确认它真的在打脉搏

两个办法，任选：

1. **看面板 LED**：手册 `:585-589` 的 Pulse Indicator —— "blinks in synchronization
   with beeper, indicating that the pump is generating a simulated blood pressure
   pulse"。**80 BPM 就是每 0.75 秒闪一次**，同时有蜂鸣声
2. **看 MCU 串口**：`[Pressure]` 的 `est` 在 ±2 mmHg 范围内以 0.75 s 周期摆动
   （Preset 4 在 215 mmHg 附近约 ±1.2 mmHg）

两个都没有 → 检查 `Cuff` 是不是 Internal、或回路是不是没充起来。

---

## 四、跑一轮时的完整时序

```
① Tester：设好 Preset 4 / External，停在 ready ....      ← 你现在这一步
② 我：跑采集脚本，MCU 会自己 vent → seal → target 275 → start
③ MCU 充到 275 mmHg，封阀，开始 1.8 mmHg/s 峰区放气
④ Tester 检测到压力 → LED 开始闪 → 注入 80 BPM 脉搏
⑤ MCU 采 40 Hz，导出 bp.capture/4
⑥ MCU vent → 压力归零 → Tester 自动停下，回 ready ....
⑦ MCU seal，收尾
```

**②–⑦ 之间你不需要碰面板。** 唯一要注意：**别在中途按 HOME 或 CUFF**，
那会打断注入。

---

## 五、跑完之后

1. 确认 MCU 已 `vent`，压力回到 0
2. 面板应自动回到 `ready ....`（LED 停止闪、蜂鸣停止）
3. 按 **`HOME`** 回主菜单（手册 `:1959`）
4. 若还要跑下一轮，重新进 `4 STANDARD BP`，`OPTIONS` 到 Preset 4，
   `CUFF` 确认 External —— **Preset 与 Cuff 不保证跨轮保持**

---

## 六、另两条常用路径（设置方法不同，别混）

### A. 泄漏测试（Tester 自己加压并测漏）

```
PRESSURE TESTS → PRESSURE LEAK TEST → SETUP
  Setpoint: 250（可 0–400，用 ▲▼ 或软键改，ENT 确认）
  ENT → 进入 Leak Test 屏
  CUFF → 选 External
  VENT（先泄压，约 5 秒）
  <START>   ← 这个才是真需要按的 START（它自己要打压）
  60 秒后屏幕显示 Leak Rate: _._  mmHg/min
```

手册 `:1662-1682`、`:2464`。两个必须记住的点：

- **`CUFF` 必须选 External**，否则它测的是内部模拟袖带
- **必须保证 MCU 处于 `seal`**，否则 Tester 打的气会直接从阀2 泄掉，
  读数毫无意义

### B. 读它自己的压力（当独立参考）

```
PRESSURE TESTS → STATIC PRESSURE → GAUGE
  Measured: 0   0.4 mm Hg
  （这个屏没有 START，只有 VENT）
```

手册 `:1802-1835`。用途：外部气源（MCU）打压时，直接读它自己的传感器。
**这正是 `[GAUGE]` 命令对应的那个测量**，只是可以从面板看，也可以通过 COM12 读。

---

## 七、常见错误与后果

| 错误 | 后果 | 怎么发现 |
|---|---|---|
| `Cuff: Internal Adult` | 真实袖带变成并联负荷，容积与包络全错 | 检查点 1 |
| 停在 Preset 3（200/150, 0.60 cc） | 元数据标错，包络峰位置差 49 mmHg | 检查点 3 |
| 接了背面 `LEAK` 口 | `[GAUGE]` 读 0，没有独立参考 | 共节点验证 |
| 中途按 HOME / CUFF | 脉搏中断，那一段数据废 | 按 `pulse_coverage.py` 复核 |
| 泄漏测试时 MCU 在 `vent` | Tester 打的气直接泄掉，Leak Rate 无意义 | 先确认 `pins` = `PC1=LOW` |
| 用 Internal 模式做泄漏测试 | 测的是内部袖带，不是我们的回路 | 屏上 `Cuff:` 行 |

---

## 八、验证命令（我这边跑）

```powershell
# 面板是否真的在打脉搏（80 BPM → 每秒 1.33 次）
python tmp\state_check_20261108.py panel_ready_20261109 5

# 共节点验证：MCU 打 150，看 Tester 面板/串口是否跟随
python tmp\gauge_vs_mcu2_20261109.py --tester-port COM12 --target 150

# 双传感器同时测漏
python tmp\leak_two_sensor_20261109.py 150 120 tee_leak_20261109 COM12
```
