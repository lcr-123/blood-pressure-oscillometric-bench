# 收尾规则：排气之后必须关阀2，而我有几个脚本漏了这半步

日期 2026-11-10。用户提醒"排气完要记得关放气阀"。查了一遍，**确实有漏，而且是我最常用的
那个"安全收尾"助手。**

## 一、当前状态（已修正）

```
[Pins]   PB8=HIGH PC1=LOW PC8=HIGH pump=OFF      ← PC1=LOW = 阀2 已关闭 ✓
[Status] state=IDLE cal=VALID ads=ONLINE stream=ON
[Fault]  code=0 name=NONE
压力     est median 0.00 mmHg   sensor 240 mV
```

**现在是正确状态：排过气 + 阀2 关闭。**

## 二、漏在哪

### `tmp/vent_now_20261108.py`（最严重）

这是我今天用了十几次的"收尾助手"。它做的事是：

```python
b.command('vent', ...)      # 阀2 打开，通大气
b.observe(7.0)
print(f'VENTED, est median ...')
```

**它只 `vent`，从不 `seal`。** 所以我每次说"回路已 vent 到安全状态"，实际是
**"回路对着大气敞开着"**，而不是"回到零压后封住"。

### `tools/bp_static_crosscheck.py`（今天新写的）

```python
finally:
    cmd(b, 'vent', ...)     # 只有 vent
    b.observe(3.0)
```

同样缺 seal。我昨天写的 `gauge_vs_mcu2_20261109.py` 和 `leak_two_sensor_20261109.py`
**是对的**（它们都 seal 了），但今天这两个没有。

## 三、为什么这不是小事

AGENTS.md 的既定顺序是：

> 完整收尾顺序固定为：`vent` → 等连续新鲜串口样本 `est≈0`（或目标值）→ `seal`。
> **阀2不能长期通大气。**

漏了 `seal` 的实际后果：

1. **袖带长期通大气** → 气囊壁贴在硬芯上被压扁，下次充气时要先"鼓起来"，
   前 30 s 的压缩热行为会变（这正是我这两天一直在处理的那个量）
2. **空气从阀座渗漏路径反向进出** → 漏气率测量会变
3. **下一轮不是从已知状态开始** → 我每次开跑前都记录零点，但零点本身依赖阀状态
   （阀2 通电会把读数抬高约 3.94 mmHg，这是已记录的耦合偏移）

## 四、已修的两处

### `tools/bp_static_crosscheck.py`

```python
# Vent to ambient, then CLOSE valve 2 again. Leaving it open keeps the cuff
# connected to atmosphere indefinitely, which flattens the cuff and lets air
# migrate through the valve seat - and it means the next run starts from an
# unknown mechanical state. The project rule is vent -> wait for a fresh zero ->
# seal, and this is the seal half.
if vent_ok:
    cmd(b, 'seal', r'\[Valve2\] CLOSE PC1=LOW', tries=2)
    ...检查输出里必须是 PC1=LOW，否则打印 WARNING
```

并且把 `final_pins` 写进 JSON，事后可查。

### `tmp/vent_now_20261108.py`

```python
if abs(float(np.median(values))) <= 1.0:
    b.command('seal', ...)      # 只有确认到零压才关阀
    print('SEALED after vent')
else:
    print(f'NOT sealing: pressure still {x:.2f} mmHg')
```

**加了个门槛**：只在读数确实接近 0 时才 seal，避免"高压下直接关阀"把压力封在回路里。

实测：

```
[Deflate] VENT PB8=HIGH PC1=HIGH PC8=HIGH
VENTED, est median 0.20 mmHg over 39 samples
TX seal
[Valve2] CLOSE PC1=LOW
SEALED after vent
```

## 五、我核对过的其他脚本

| 脚本 | vent | seal | 结论 |
|---|---|---|---|
| `tmp/leak_two_sensor_20261109.py` | ✓ | ✓ | 正确 |
| `tmp/gauge_vs_mcu2_20261109.py` | ✓ | ✓ | 正确 |
| `tmp/vent_now_20261108.py` | ✓ | ✗ → **已修** | 曾漏 |
| `tools/bp_static_crosscheck.py` | ✓ | ✗ → **已修** | 曾漏 |

另外 40 多个历史脚本里有大量 `command('seal')`，但那些是流程中间的封阀，不是收尾，
不在此列。

## 六、以后的开跑前检查

既然零点读数依赖阀状态，**每次开跑前应该先确认 `pins` 是 `PC1=LOW`**，而不是只看压力为 0。

`tmp/state_check_20261108.py` 两次检查都读了 `pins`，所以这条已经在流程里了 ——
**只是我当时没把它当成"上一位是否关阀"的证据来看。**

**这条写进规则：`PC1=HIGH` 时看到的 0 mmHg 是"通大气"，不是"封住的零"。**
两者都显示 0，但机械状态完全不同。
