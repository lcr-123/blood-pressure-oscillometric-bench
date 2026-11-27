"""Draw the dataset pneumatic loop with the BP Pump 2 teed back in.

Why a new drawing instead of editing the syringe one: the syringe diagram shows the
MEASUREMENT configuration (BP Pump 2 removed, syringe fitted). The dataset configuration
differs in two ways that both change the numbers - the Tester is in the loop (its 20 cc
main manifold is always in circuit per manual Figure 3-1, :1317-1322) and the syringe is
out, because its 26 cc would otherwise be part of the volume.

The topology is not invented. It is the one the 59 dataset runs used, recorded in the
per-run metadata ("dynamic External Cuff circuit") and drawn in
data/raw/development_20261101/development_schematic_20261106.png. What is new here is
that the Tester is shown as a member of the loop rather than as an external pulse source,
and that the three actions needed to restore it are called out.

Pneumatic facts encoded:
  - Tester Pressure Port sits directly on a ~20 cc main manifold that also carries its
    own pressure transducer, which is why [GAUGE] only becomes meaningful once teed in.
  - Valve 2 (PC1, high = open) is the ONLY path to atmosphere, so "seal" is literally
    valve 2 closing. That is what makes it the boundary of the trapped volume.
  - Valve 1 (PB8 relay, released = HIGH) isolates the pump after inflation, and the pump
    outlet is capped, so the loop cannot leak down backwards through the pump.

Layout note: every block is placed on a grid with at least 4 mm of clearance, because the
first draft let the valve 1, pump and valve 2 boxes overlap and buried the tee D label
under the trapped-volume callout. Fonts stay on the CJK family - asking matplotlib for
DejaVu Sans Mono silently drops every Chinese glyph while still rendering the numbers,
which reads like a layout bug rather than a font one.
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle

matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'reports' / 'dataset_loop_tee_back_20261109.png'

PNEU = '#1f4e79'
SEAL = '#c00000'
OK = '#2e7d32'
MUTED = '#5f5f5f'
GOLD = '#8a6d00'
GREY = '#8c8c8c'
SPINE = 44.0

fig, ax = plt.subplots(figsize=(15.4, 9.8))
ax.set_xlim(0, 154)
ax.set_ylim(0, 98)
ax.axis('off')

ax.text(77, 94.4, '数据集气路：把 BP Pump 2 接回三通后的完整连接（2026-11-09）',
        ha='center', fontsize=16.5, fontweight='bold', color='#111111')
ax.text(77, 90.4, '这是 59 轮数据集实际使用的工况；回路容积 ≈ 340 cc，BP Pump 2 是唯一的脉搏源',
        ha='center', fontsize=10.6, color=MUTED)


def box(x, y, w, h, text, color=PNEU, fill='#eaf1f8', fontsize=9.2, lw=1.5, style='solid'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.5',
                                linewidth=lw, edgecolor=color, facecolor=fill,
                                linestyle=style, zorder=4))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center',
            fontsize=fontsize, color=color, linespacing=1.45, zorder=5)


def tee(y, label, side='right'):
    ax.add_patch(Circle((SPINE, y), 1.5, facecolor='white', edgecolor=PNEU,
                        linewidth=1.8, zorder=6))
    dx = 3.2 if side == 'right' else -3.2
    ax.text(SPINE + dx, y + 1.2, label, ha='left' if side == 'right' else 'right',
            va='bottom', fontsize=9.0, color=PNEU, zorder=6)


def seg(x1, y1, x2, y2, color=PNEU, lw=2.2, style='-', zorder=3):
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw, linestyle=style,
            solid_capstyle='round', zorder=zorder)


# --- BP Pump 2, now a member of the loop ------------------------------------
box(2, 76.0, 26, 9.4, 'BP Pump 2\nPressure Port', fontsize=9.0)
seg(28, 80.7, SPINE, 80.7)
tee(80.7, '三通 A')
ax.add_patch(Rectangle((2.9, 76.9), 24.2, 7.6, facecolor='none', edgecolor=GOLD,
                       linewidth=1.0, linestyle=(0, (3, 2)), zorder=5))
ax.text(15, 74.2, '内部：20 cc 主气室\n+ 它自己的压力传感器\n（290 cc 罐体在 External 下关闭）',
        ha='center', va='top', fontsize=8.0, color=GOLD, linespacing=1.4)

# --- MCU sensor on the same node -------------------------------------------
seg(SPINE, 80.7, 70, 80.7)
box(70, 73.6, 33, 14.0, 'MPXV5050GP\nP1 → 压力气路\nP2 → 大气', fontsize=9.0)
ax.text(86.5, 71.8, '→ ADS1115 AIN0 → MCU', ha='center', va='top', fontsize=8.2, color=MUTED)

# --- cuff ------------------------------------------------------------------
seg(SPINE, 80.7, SPINE, 65.0)
tee(65.0, '三通 B')
seg(SPINE, 65.0, 17.0, 65.0)
seg(17.0, 65.0, 17.0, 61.0)
box(2, 47.0, 30, 14.0, '真实袖带\n缠在硬芯上\n与数据集同一绑法（不拆）\n气囊 ≈ 315 cc', fontsize=8.8)

# --- syringe port: capped in this configuration ----------------------------
seg(SPINE, 65.0, SPINE, 47.0)
tee(47.0, '三通 C')
seg(SPINE, 47.0, 68, 47.0, color=GREY, style=(0, (5, 3)))
box(68, 39.5, 34, 15.0, '注射器口\n【本次必须拆掉并用堵头封死】\n否则回路容积 +26 cc 且不确定',
    color=SEAL, fill='#fdeaea', fontsize=8.6, style='dashed')

# --- trapped volume callout (empty space right of the spine) ---------------
ax.text(84, 27.5, '阀2 关闭后被困住的容积：\n三通 A–B–C–D 全部支路 + 袖带\n+ 传感器口 + 阀1/气泵死腔\n+ BP Pump 2 主气室',
        ha='center', va='center', fontsize=8.4, color=SEAL, linespacing=1.6,
        bbox=dict(boxstyle='round,pad=0.55', facecolor='#fff4f4',
                  edgecolor='#e8b4b4', linewidth=1.0), zorder=6)

# --- valve 1 / pump branch -------------------------------------------------
seg(SPINE, 47.0, SPINE, 34.0)
tee(34.0, '三通 D', 'left')
seg(SPINE, 34.0, 12.5, 34.0)
seg(12.5, 34.0, 12.5, 28.0)
box(1, 20.4, 23, 7.6, '阀1（PB8 继电器）\n释放 = HIGH = 关闭', fontsize=8.4)
seg(12.5, 20.4, 12.5, 15.4)
box(1, 7.8, 23, 7.6, '气泵（PC8 低有效）\n出气口已封死', fontsize=8.4)

# --- valve 2: the only path to atmosphere ----------------------------------
seg(SPINE, 34.0, SPINE, 20.0)
box(30, 12.0, 28, 8.0, '阀2（PC1 高电平 = 通大气）', color=SEAL, fill='#fdeaea', fontsize=8.8)
seg(58, 16.0, 68, 16.0, color=SEAL)
seg(66, 6.0, 66, 26.0, color=SEAL, lw=1.6, style=(0, (6, 3)))
seg(66, 16.0, 74, 16.0, color=SEAL)
ax.text(75.5, 16.0, '大气', ha='left', va='center', fontsize=9.6, color=SEAL, fontweight='bold')
ax.text(66, 27.2, '封闭边界', ha='center', va='bottom', fontsize=8.4, color=SEAL)
ax.text(66, 4.8, 'seal = 关这里', ha='center', va='top', fontsize=8.4, color=SEAL)

# --- right-hand panel: the three things to do ------------------------------
ax.add_patch(Rectangle((108, 52), 44, 38.5, facecolor='#f8f8f8', edgecolor='#d0d0d0'))
ax.text(110, 88.6, '要动的三件事', fontsize=11.2, fontweight='bold', color=PNEU)
steps = [
    ('1. 接回 BP Pump 2', OK),
    ('   用前面板 Pressure Port，不是背面', PNEU),
    ('   的 LEAK / PRESSURE RELIEF 口。', PNEU),
    ('   接到三通 A。', PNEU),
    ('', MUTED),
    ('2. 拆掉注射器', OK),
    ('   三通 C 用堵头封死。若活塞留在', PNEU),
    ('   回路里，容积就是 340 + 26 cc', PNEU),
    ('   且不确定。', PNEU),
    ('', MUTED),
    ('3. 接回后重测漏气率', OK),
    ('   多了一路 BP Pump 2（内部标称', PNEU),
    ('   <2 mmHg/min @≥300 cc）。历史干', PNEU),
    ('   袖带稳态 6.5 mmHg/min，若明显', PNEU),
    ('   变差就是这一段的问题。', PNEU),
]
y = 84.4
for text, color in steps:
    if text:
        ax.text(110, y, text, fontsize=8.4, color=color)
    y -= 2.12

# --- volume ledger --------------------------------------------------------
ax.add_patch(FancyBboxPatch((108, 31.5), 44, 18.0, boxstyle='round,pad=0.5',
                            linewidth=1.4, edgecolor=GOLD, facecolor='#fff8e1'))
ax.text(110, 47.4, '容积账（数据集工况）', fontsize=10.2, fontweight='bold', color=GOLD)
ledger = [
    'BP Pump 2 主气室          20 cc',
    '袖带气囊                 ≈315 cc',
    '管路+三通+阀死腔+传感器口    ≈25 cc',
    '───────────────────────────',
    '合计                     ≈340 cc',
]
y = 44.4
for text in ledger:
    ax.text(110, y, text, fontsize=8.4, color='#6b5300')
    y -= 2.34
ax.text(110, 33.0, '测量工况（摘除 BP Pump 2）= 320 cc', fontsize=8.2, color=MUTED)

# --- why it has to go back ------------------------------------------------
ax.add_patch(FancyBboxPatch((108, 6.0), 44, 23.0, boxstyle='round,pad=0.5',
                            linewidth=1.4, edgecolor=PNEU, facecolor='#eaf1f8'))
ax.text(110, 26.8, '为什么必须接回', fontsize=10.2, fontweight='bold', color=PNEU)
why = [
    '① 59 轮数据集就是这个工况，',
    '    摘掉就不是同一个回路。',
    '② 只有接回，[GAUGE] 才看得到',
    '    回路压力（现测：MCU 134，',
    '    面板 0 → 端口未接入）。',
    '③ 它是唯一的脉搏源，摘掉就没有',
    '    包络可采。',
    '',
    '接回后可立即验证共节点：',
    '    python tmp\\gauge_vs_mcu2_20261109.py',
    '        --tester-port COM12 --target 150',
]
y = 24.2
for text in why:
    if text:
        ax.text(110, y, text, fontsize=8.0, color=PNEU)
    y -= 2.00

fig.tight_layout()
fig.savefig(OUT, dpi=170, facecolor='white')
print(f'wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size} bytes')
