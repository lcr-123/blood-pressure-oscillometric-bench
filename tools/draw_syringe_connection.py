"""Draw the syringe connection, third attempt.

Fixes over the previous two: tee labels are placed away from the boxes they used to collide with,
the cuff sits beside the spine instead of on top of it, the valve 1 / pump branch joins a single
vertical instead of a box corner, and the sealed / open boundary is labelled on the correct side.

The topology is not invented here. It is the one already recorded in tmp/plumbing_answer_20261108.py:
the syringe goes on the sealed side of valve 2, on the same node as the cuff and the pressure sensor.
Put it on the atmospheric side and `seal` vents it, which would measure the syringe instead of the loop.
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle

matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'reports' / 'syringe_connection_20261109.png'

PNEU = '#1f4e79'
SEAL = '#c00000'
OK = '#2e7d32'
MUTED = '#5f5f5f'
GOLD = '#8a6d00'
SPINE = 52.0

fig, ax = plt.subplots(figsize=(14.6, 9.4))
ax.set_xlim(0, 146)
ax.set_ylim(0, 94)
ax.axis('off')

ax.text(73, 90.6, '注射器测容积：气路连接（2026-11-09）',
        ha='center', fontsize=16, fontweight='bold', color='#111111')
ax.text(73, 86.6, '所有原有部件都留在回路里，只增加一支 20 mL 注射器；'
                  '注射器必须接在阀2 的封闭侧',
        ha='center', fontsize=10.2, color=MUTED)


def box(x, y, w, h, text, color=PNEU, fill='#eaf1f8', fontsize=9.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.55',
                                linewidth=1.5, edgecolor=color, facecolor=fill))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
            fontsize=fontsize, color=color, linespacing=1.42)


def tee(y, label, where='right'):
    ax.add_patch(Circle((SPINE, y), 1.45, facecolor='white', edgecolor=PNEU, linewidth=1.7))
    if where == 'right':
        ax.text(SPINE + 2.8, y + 1.5, label, ha='left', va='bottom', fontsize=9.0, color=PNEU)
    elif where == 'left':
        ax.text(SPINE - 2.8, y + 1.5, label, ha='right', va='bottom', fontsize=9.0, color=PNEU)
    else:
        ax.text(SPINE, y + 3.0, label, ha='center', va='bottom', fontsize=9.0, color=PNEU)


def seg(x1, y1, x2, y2, color=PNEU, lw=2.0, style='-'):
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw, linestyle=style,
            solid_capstyle='round')


# --- top: BP Pump 2 into tee A ----------------------------------------------
box(4, 76, 22, 8.4, 'BP Pump 2\nPressure Port')
seg(26, 80.2, SPINE, 80.2)
tee(80.2, '三通 A', 'up')

# sensor branch, right of tee A
seg(SPINE, 80.2, 66, 80.2)
box(66, 74.4, 30, 11.6, 'MPXV5050GP\nP1 → 压力气路\nP2 → 大气')

# --- cuff, beside the spine -------------------------------------------------
seg(SPINE, 80.2, SPINE, 62.0)
seg(SPINE, 62.0, 34, 62.0)
box(6, 56.5, 28, 11.0, '真实袖带\n缠在硬芯上，不拆\n与数据集同一绑法', fontsize=8.6)

# --- tee C carries the syringe ---------------------------------------------
seg(SPINE, 62.0, SPINE, 48.0)
tee(48.0, '三通 C', 'left')
ax.text(SPINE + 2.8, 45.6, '← 注射器接这个口', ha='left', va='center',
        fontsize=8.6, color=OK)
seg(SPINE, 48.0, 68, 48.0, color=OK)
box(68, 41.5, 32, 13.0, '20 mL 注射器\n活塞推到 0 mL 顶到底\n拉 9 → 18 mL，每段夹住',
    color=OK, fill='#eaf5ea', fontsize=8.8)

# --- valve 1 / pump branch, one junction -----------------------------------
seg(SPINE, 48.0, SPINE, 30.0)
tee(30.0, '三通 B', 'up')
seg(SPINE, 30.0, 22, 30.0)
seg(22, 30.0, 22, 34.0)
box(4, 34.0, 30, 8.4, '阀1（PB8 继电器）\n断电常开口 → 封死', fontsize=8.4)
seg(22, 30.0, 22, 25.0)
box(4, 16.6, 30, 8.4, '气泵（PC8）\n出气口封死', fontsize=8.4)

# --- the sealed / open boundary --------------------------------------------
seg(2, 17.6, 100, 17.6, color=SEAL, lw=1.3, style=(0, (7, 4)))
ax.text(60, 19.0, '↑ 阀2 关闭后的封闭侧：袖带、传感器、注射器、阀1 与泵支路都在这一侧',
        ha='left', va='bottom', fontsize=8.6, color=SEAL)
ax.text(60, 15.4, '↓ 通大气侧（只有 vent 时打开）',
        ha='left', va='top', fontsize=8.6, color=SEAL)

seg(SPINE, 17.6, SPINE, 13.2)
box(12, 5.4, 36, 7.8, '阀2（PC1 高有效）\nseal 关闭 / vent 通大气', color=SEAL, fill='#fdeaea',
    fontsize=8.6)
seg(48, 9.3, 58, 9.3, color=SEAL)
ax.text(59, 9.3, '→ 大气（vent 时）', ha='left', va='center', fontsize=8.6, color=SEAL)

# --- annotation panel -------------------------------------------------------
ax.add_patch(Rectangle((104, 28), 40, 50, facecolor='#f8f8f8', edgecolor='#d0d0d0'))
ax.text(106, 74.5, '为什么必须这样接', fontsize=10.6, fontweight='bold', color=PNEU)
notes = [
    ('注射器接三通 C：与袖带、', PNEU),
    ('传感器同一节点，位于阀2', PNEU),
    ('关闭后的封闭侧。', PNEU),
    ('', MUTED),
    ('阀2 就是"密封"本身：', SEAL),
    ('  seal → PC1=LOW，关闭', SEAL),
    ('  vent → PC1=HIGH，通大气', SEAL),
    ('', MUTED),
    ('若接到阀2 的常开侧：', SEAL),
    ('  seal 一关，注射器直接', SEAL),
    ('  通大气，公式里的 V 变成', SEAL),
    ('  20 cc，测出的是注射器', SEAL),
    ('  而不是整个回路。', SEAL),
    ('', MUTED),
    ('袖带不能拆：要测的就是', PNEU),
    ('产数据集那个回路。', PNEU),
    ('', MUTED),
    ('阀1、气泵留在回路：它们', PNEU),
    ('贡献死腔和漏流，两者都', PNEU),
    ('属于要测的那 153 cc。', PNEU),
]
y = 71.0
for text, color in notes:
    if text:
        ax.text(106, y, text, fontsize=8.4, color=color)
    y -= 2.18

# --- force requirement ------------------------------------------------------
ax.add_patch(FancyBboxPatch((104, 4.0), 40, 21.5, boxstyle='round,pad=0.6',
                            linewidth=1.5, edgecolor=GOLD, facecolor='#fff8e1'))
ax.text(106, 22.4, '受力与锁定', fontsize=10.2, fontweight='bold', color=GOLD)
force_lines = [
    '200 mmHg 下活塞受力 0.85 kgf',
    '（内径 20 mm，面积 3.1 cm²）',
    '',
    '用扎带或夹子把推杆压在筒口',
    '法兰上；拉完必须松手——',
    '手接触噪声 4.7 mmHg，是松手',
    '（0.27 mmHg）的 17 倍。',
]
y = 19.9
for text in force_lines:
    if text:
        ax.text(106, y, text, fontsize=8.4, color='#6b5300')
    y -= 2.05

fig.tight_layout()
fig.savefig(OUT, dpi=170, facecolor='white')
print(f'wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size} bytes')
