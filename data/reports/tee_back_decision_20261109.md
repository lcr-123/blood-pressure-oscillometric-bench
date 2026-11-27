# BP Pump 2 要不要接回气路？—— 要，但要先决定"接哪种"

日期 2026-11-09。用户问"bp要不要接回去气路里？"。答案是**要接回去**，因为 59 轮数据集
的工况就是它接在三通上注入脉搏。但要先分清三件不同的事。

## 一、"接回去"是恢复数据集工况，不是加了新东西

`data/raw/` 那 59 轮采集时，气路是：

```
泵(PC8) → 阀1(PB8) → 三通 A ─┬─ 袖带
                              ├─ MPXV5050GP P1（MCU 传感器）
                              ├─ 注射器接头（容积测量时接的）
                              └─ 三通 B ─┬─ 阀2(PC1) → 大气
                                          └─ BP Pump 2 Pressure Port
```

BP Pump 2 不是"可选的额外设备"，**它就是脉搏源**。把它摘掉，回路里既没有脉搏，
也没有那 20 cc 主气室。所以：

- **测容积**：应该摘掉（本次已做，320 cc）
- **复现数据集 / 采新数据**：必须接回（数据集工况 ≈ 340 cc）

## 二、刚测出来的事实：现在它确实没接

`tmp/gauge_vs_mcu2_20261109.py --tester-port COM12 --target 150`：

```
MCU 10 s 内从 142.55 稳定降到 133.95（正常漏气）
Tester [GAUGE] 全程 0.00
VERDICT: the Tester stays at zero while the MCU reads 134 mmHg.
```

**MCU 读到 134 mmHg，而 BP Pump 2 自己的压力端口读 0.00** —— 这直接证明它的压力端口
没接到回路里（如果接了，它的传感器会看到同一个压力）。与你说的"我没有接回"一致。

顺带排除了另一种解释：不是 `[GAUGE]` 坏了。真空测试时 raw 掉过 40 counts，
`[GAUGE]` 在环境压力下读 0 是对的，只是看不到回路压力。

## 三、接回去之后会改变什么（必须记录的口径变化）

| 项 | 摘除（测量工况） | 接回（数据集工况） |
|---|---|---|
| 回路容积 | 320 cc | **≈ 340 cc**（+20 cc 主气室） |
| 每搏压力摆幅（Preset 4，dP 绝热） | 2.35 mmHg | **2.21 mmHg** |
| 泄漏率 | 阀2 单点漏 | 增加 BP Pump 2 内部（标称 <2 mmHg/min @≥300 cc） |
| 独立压力参考 | 无 | **有（`[GAUGE]`，5 Hz / 1 mmHg）** |
| 脉搏源 | 无 | BP Pump 2 步进电机 |

**最后两行是接回的主要理由**：接回之后 `[GAUGE]` 才有意义，而它是我们在
`dataset_limitations.md` 第 1 条上唯一的出路。

## 四、具体怎么接

图：`data/reports/dataset_loop_tee_back_20261109.png`（15.4×9.8 in，含容积账与三条必做动作）

### 拓扑（与 59 轮数据集完全一致）

```
                    ┌──────────────┐
   BP Pump 2        │  MPXV5050GP  │
   Pressure Port    │  P1 → 气路   │
        │           │  P2 → 大气   │
        └──── 三通 A ┴──────────────┘──→ ADS1115 AIN0 → MCU
                    │
                 三通 B
                    ├──────── 真实袖带（缠硬芯，不拆）
                    │
                 三通 C ── ✕ 堵头封死（注射器口）
                    │
                 三通 D ──┬── 阀1（PB8 继电器，释放=HIGH）── 气泵（PC8，出口封死）
                    │
                 阀2（PC1 高 = 通大气）── 大气
```

四个三通其实是同一个节点的四段塑料管，**顺序不重要，重要的是"每根支路都挂在
阀2 关闭侧的同一个封闭容积上"**。图上按 A→B→C→D 排只是为了让每个部件都有位置。

### 接线前的三步

1. **断电、泄压**。MCU 先 `vent`，等串口 `est` 稳定在 5 mmHg 以下（现在约 10，
   再 vent 一次即可）。
2. **确认 BP Pump 2 电源关着**（它是独立仪器，接线时最好断电，避免误触发）。
3. **检查堵头**：三通 C 那个原本接注射器的口，必须换成实心堵头，
   不要用"活塞推到 0 mL 的注射器"代替（它的 26 cc 会进回路）。

### 接哪三个点

| 从 | 到 | 说明 |
|---|---|---|
| BP Pump 2 **前面板 `Pressure Port`** | 三通 A 的空口 | 用 4–6 mm 内径硅胶管，尽量短 |
| MCU 侧三通（现有） | 同一条管路的另一段 | 不需要动 |
| 三通 C | **堵头** | 注射器拆掉 |

**不要用** BP Pump 2 背面的 `LEAK` 或 `PRESSURE RELIEF` 口。手册 `:604-607` 说明
`Pressure Port` 才是"all pressure simulations and tests"那个，内部直连 20 cc 主气室
与它自己的压力传感器。用错口 → `[GAUGE]` 仍然读不到回路压力。

### 接完立刻做的四步验证

```powershell
# 1. MCU 状态与零点
python tmp\state_check_20261108.py after_tee_20261109 5

# 2. 共节点验证：MCU 打到 150，看面板 [GAUGE] 是否跟随
python tmp\gauge_vs_mcu2_20261109.py --tester-port COM12 --target 150
#    期望：MCU 与 Tester 都在 150 附近，差 ≤6 mmHg
#    若 Tester 仍读 0 → 端口没接对

# 3. 泄漏复测（多了 BP Pump 2 一路）
python tmp\leak_hold150_20261107.py 150 120 tee_leak_20261109
python tmp\leak_hold_analyze_20261107.py

# 4. 面板侧独立确认
#    在 BP Pump 2 上手动走 PRESSURE TESTS → PRESSURE LEAK TEST，
#    CUFF 选 External，先 VENT 再 START，看 Leak Rate
```

### 接回后的注意事项

- **容积从 320 变 340 cc**，所有幅值换算已按 340 更新（`data/dataset_dictionary.md`）
- **管子尽量短、两路内径一致**。之前"两传感器差 7%"（`leak_and_pulse_20261107.md`）
  可能就是支路差异，接回后正好重核
- **别忘阀1 与气泵留在回路里**：它们贡献死腔和漏流，属于要测的那 340 cc
- **BP Pump 2 用 External Cuff 模式**（面板 `CUFF` 键切），不要 Internal Adult

## 五、接回之前可以做的事

`[GAUGE]` 虽看不到回路压力，但**链路本身已完全验证**（`[BP_VERSION]` = `Ver 2.01S`、
`[BP_SERIAL]` = `5788005`、60 条突发零丢帧、5 Hz / 1 mmHg 特性已测清）。
所以接回后不需要再排查通信，直接就能跑比对：

```powershell
# 1. 接回后先确认共节点（MCU 打 150，看 [GAUGE] 是否跟随）
python tmp\gauge_vs_mcu2_20261109.py --tester-port COM12 --target 150

# 2. 共节点确认后做静态多点核验
python tmp\gauge_static_sweep_20261109.py --tester-port COM12   # 待写
```

## 六、一句话结论

**要接回。** 因为：①数据集工况就是它接在三通上；②只有接回，`[GAUGE]` 才能提供
独立压力参考，而这是关掉"无独立动态参考"这条限制的唯一途径。接回后注意容积从
320 变 340、并重测一次泄漏率。
