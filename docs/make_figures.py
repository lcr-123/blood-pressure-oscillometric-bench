# -*- coding: utf-8 -*-
"""生成项目文档用的 AI 风格示意图（全部程序绘制，不用实物照片）。"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

FONT = r"C:\Windows\Fonts\msyh.ttc"
FONTB = r"C:\Windows\Fonts\msyhbd.ttc"

INK = (33, 39, 50)
MUTED = (108, 120, 138)
BLUE_F, BLUE_E = (228, 239, 253), (78, 128, 210)
AMBER_F, AMBER_E = (254, 242, 222), (196, 138, 48)
GREEN_F, GREEN_E = (227, 245, 234), (62, 158, 110)
GRAY_F, GRAY_E = (241, 243, 247), (166, 176, 192)
RED = (198, 68, 68)
WHITE = (255, 255, 255)
BLUE = (58, 98, 172)
ORANGE = (198, 110, 60)


def f(size, bold=False):
    return ImageFont.truetype(FONTB if bold else FONT, size)


def canvas(w, h, bg=(252, 253, 255)):
    img = Image.new("RGB", (w, h), bg)
    return img, ImageDraw.Draw(img)


def box(d, x0, y0, x1, y1, title, sub=None, fill=GRAY_F, edge=GRAY_E,
        ts=30, ss=22, radius=18, tcol=INK, scol=MUTED):
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=edge, width=3)
    cx = (x0 + x1) / 2
    if sub:
        d.text((cx, (y0 + y1) / 2 - 18), title, font=f(ts, True), fill=tcol, anchor="mm")
        d.text((cx, (y0 + y1) / 2 + 20), sub, font=f(ss), fill=scol, anchor="mm")
    else:
        d.text((cx, (y0 + y1) / 2), title, font=f(ts, True), fill=tcol, anchor="mm")


def arrow(d, x0, y0, x1, y1, color=MUTED, width=4, head=14):
    d.line([x0, y0, x1, y1], fill=color, width=width)
    if y0 == y1:
        if x1 > x0:
            d.polygon([(x1, y1), (x1 - head, y1 - head * 0.62), (x1 - head, y1 + head * 0.62)], fill=color)
        else:
            d.polygon([(x1, y1), (x1 + head, y1 - head * 0.62), (x1 + head, y1 + head * 0.62)], fill=color)
    else:
        if y1 > y0:
            d.polygon([(x1, y1), (x1 - head * 0.62, y1 - head), (x1 + head * 0.62, y1 - head)], fill=color)
        else:
            d.polygon([(x1, y1), (x1 - head * 0.62, y1 + head), (x1 + head * 0.62, y1 + head)], fill=color)


def title(d, main, sub=None):
    d.text((60, 40), main, font=f(43, True), fill=INK)
    if sub:
        d.text((62, 104), sub, font=f(23), fill=MUTED)


def note(d, x, y, lines, size=23, color=MUTED, gap=34):
    for i, line in enumerate(lines):
        d.text((x, y + i * gap), line, font=f(size), fill=color)


# ============================================================ 图 1 气路
def fig1():
    img, d = canvas(1600, 920)
    title(d, "图 1  气路构成：所有器件并接在同一个压力节点上",
          "袖带、传感器气嘴 P1、BP Pump 2 压力口、充气支路、放气支路共用一个三通；传感器背面 P2 侧与大气相通。")

    y0, y1 = 340, 462
    box(d, 636, 168, 1088, 296, "BP Pump 2 压力口", "示波脉搏源（只发送脉搏）", AMBER_F, AMBER_E)
    d.text((1112, 196), "按面板预设合成示波包络", font=f(22), fill=MUTED)
    d.text((1112, 232), "向气室往复推 0.55 cc", font=f(22), fill=MUTED)
    arrow(d, 862, 298, 862, 336)

    box(d, 55, y0, 330, y1, "气泵 PUMP", "PC8 低电平启动")
    box(d, 390, y0, 665, y1, "阀1 充气阀", "PB8 低电平吸合", AMBER_F, AMBER_E)
    box(d, 725, y0, 1000, y1, "三通接头", "唯一压力节点", BLUE_F, BLUE_E)
    box(d, 1052, y0, 1540, y1, "非人体袖带", "刚性芯 + ≥300 cc 气室", GREEN_F, GREEN_E)

    arrow(d, 332, 401, 386, 401)
    arrow(d, 667, 401, 721, 401)
    arrow(d, 1002, 401, 1048, 401)

    # 下方分支：传感器与放气阀
    d.line([862, 462, 862, 508], fill=MUTED, width=4)
    d.line([800, 508, 1280, 508], fill=MUTED, width=4)
    d.line([800, 508, 800, 546], fill=MUTED, width=4)
    d.line([1280, 508, 1280, 546], fill=MUTED, width=4)
    arrow(d, 800, 508, 800, 546)
    arrow(d, 1280, 508, 1280, 546)

    box(d, 1068, 548, 1492, 694, "阀2 放气阀", "PC1 高电平打开", AMBER_F, AMBER_E)

    # 传感器：单气嘴 GP 封装，只有一个口
    d.rounded_rectangle([588, 548, 1012, 700], radius=18, fill=BLUE_F, outline=BLUE_E, width=3)
    d.text((800, 582), "MPXV5050GP（单气嘴）", font=f(27, True), fill=INK, anchor="mm")
    d.text((800, 626), "气嘴 P1 → 三通（唯一压力口）", font=f(20), fill=MUTED, anchor="mm")
    d.text((800, 664), "背面 P2 侧 → 大气，不要封胶", font=f(20), fill=MUTED, anchor="mm")

    d.text((800, 730), "单气嘴 = 表压器件：气嘴接气路，背面靠封装与大气相通，读到的是相对大气的压差",
           font=f(19), fill=MUTED, anchor="ma")
    arrow(d, 1280, 696, 1280, 762)
    d.text((1280, 786), "通大气（vent）", font=f(25, True), fill=RED, anchor="ma")

    d.line([60, 826, 1540, 826], fill=(228, 232, 240), width=2)
    note(d, 60, 848, ["使用铁律：vent（通大气）→ 等连续新鲜样本 est≈0 → 再 seal（封阀）；阀2 不能长期通大气。"],
         size=23, color=INK)
    img.save(os.path.join(OUT, "fig1_pneumatic.png"))


# ============================================================ 图 4 换算链
def fig4_chain():
    img, d = canvas(1600, 880)
    title(d, "图 4  气压 → 电压 → 数字量 → 压力值：五级换算链",
          "每级只做一件事；任何一级的系数错了，整条链的读数都会系统性偏移。")

    stages = [
        ("① 传感器", "0.2 – 4.7 V", ["MPXV5050GP", "0.09 V/kPa", "VS 变化 → 刻度变"], BLUE_F, BLUE_E),
        ("② 电阻分压", "÷ 1.3799", ["上 6.823 kΩ", "下 17.96 kΩ", "为的是不超过 3.3 V"], GREEN_F, GREEN_E),
        ("③ ADS1115", "125 µV / LSB", ["PGA ±4.096 V", "16 bit 单次转换", "I2C 0x48"], AMBER_F, AMBER_E),
        ("④ 标定直线", "82.326·V − 19.887", ["斜率 + 零点", "flash 内 CRC16", "static 6 点拟合"], GRAY_F, GRAY_E),
        ("⑤ 串口输出", "est = … mmHg", ["raw / ads / sensor", "同帧可手算复核", "每 25 ms 一条"], BLUE_F, BLUE_E),
    ]
    x, w, gap = 40, 256, 42
    for i, (t, val, subs, fl, ed) in enumerate(stages):
        d.rounded_rectangle([x, 200, x + w, 470], radius=18, fill=fl, outline=ed, width=3)
        d.text((x + w / 2, 242), t, font=f(27, True), fill=INK, anchor="mm")
        d.text((x + w / 2, 302), val, font=f(22, True), fill=ed, anchor="mm")
        for k, s in enumerate(subs):
            d.text((x + w / 2, 360 + k * 38), s, font=f(19), fill=MUTED, anchor="mm")
        if i < 4:
            arrow(d, x + w + 5, 335, x + w + gap - 7, 335)
        x += w + gap

    d.text((40, 508), "三个算例（和串口输出同格式，可当场手算复核）", font=f(27, True), fill=INK)
    rows = [
        ("封阀零点", "raw = 1401", "ads = 175.1 mV", "sensor = 241.6 mV", "est ≈ 0.0 mmHg"),
        ("中段压力", "raw = 9600", "ads = 1.2000 V", "sensor = 1.6559 V", "est ≈ 116.4 mmHg"),
        ("接近满量程", "raw = 15484", "ads = 1.9355 V", "sensor = 2.6708 V", "est ≈ 200.0 mmHg"),
    ]
    y = 560
    for label, *cells in rows:
        d.rounded_rectangle([40, y, 1560, y + 74], radius=12, fill=(248, 250, 253),
                            outline=(226, 231, 240), width=2)
        d.text((72, y + 37), label, font=f(23, True), fill=MUTED, anchor="lm")
        for j, c in enumerate(cells):
            d.text((320 + j * 302, y + 37), c, font=f(24), fill=INK, anchor="lm")
        y += 86

    note(d, 40, y + 14, [
        "关键：① 的零点/灵敏度由器件手册决定，② 由电阻实测决定，④ 由静态标定决定——三级系数任一错，整条链一起偏。",
    ], size=21, color=INK)
    img.save(os.path.join(OUT, "fig4_chain.png"))


# ============================================================ 图 2 时序
def fig2_timeline():
    img, d = canvas(1600, 990)
    title(d, "图 2  一轮采集的时序：脉搏什么时候才“进”得去、才测得到",
          "横轴为示意比例，非真实秒数；完整一轮为 90–110 s 量级。")

    x0, x1 = 100, 1500
    segs = [("vent\n通大气", 150), ("seal\n封阀", 96), ("充气 → 275 mmHg", 330),
            ("静置", 78), ("慢放：峰区 200–245 降速", 600), ("vent\n收尾", 146)]
    yb0, yb1 = 180, 252
    x = x0
    for label, w in segs:
        fl, ed = GRAY_F, GRAY_E
        if "充气" in label:
            fl, ed = AMBER_F, AMBER_E
        elif "慢放" in label:
            fl, ed = GREEN_F, GREEN_E
        d.rectangle([x, yb0, x + w, yb1], fill=fl, outline=ed, width=2)
        parts = label.split("\n")
        if len(parts) == 2:
            d.text((x + w / 2, (yb0 + yb1) / 2 - 15), parts[0], font=f(22, True), fill=INK, anchor="mm")
            d.text((x + w / 2, (yb0 + yb1) / 2 + 20), parts[1], font=f(18), fill=MUTED, anchor="mm")
        else:
            d.text((x + w / 2, (yb0 + yb1) / 2), label, font=f(20, True), fill=INK, anchor="mm")
        x += w

    T0 = x0 + 150 + 96            # 充气开始
    T1 = T0 + 330                 # 封阀完成（静置开始）
    T2 = T1 + 78 + 18             # 开阀约 2 s 后

    # ---- 压力曲线
    ytop, ybot = 330, 604
    d.text((100, 300), "袖带压力 / mmHg", font=f(22, True), fill=MUTED)

    def py(p):
        return ybot - (p / 300.0) * (ybot - ytop)

    for gv in (0, 100, 200, 275):
        gy = py(gv)
        d.line([x0, gy, x1, gy], fill=(238, 241, 247), width=1)
        d.text((x0 - 14, gy), str(gv), font=f(19), fill=MUTED, anchor="rm")

    xs, ys = [], []
    x = x0
    for i, (label, w) in enumerate(segs):
        if i < 2:
            seg = np.zeros(24)
        elif i == 2:
            seg = 275 * (np.linspace(0, 1, 60) ** 1.25)
        elif i == 3:
            seg = np.full(8, 275.0)
        elif i == 4:
            seg = np.linspace(275, 15, 120)
        else:
            seg = np.full(18, 15.0)
        for k, pv in enumerate(seg):
            xs.append(x + w * k / max(len(seg) - 1, 1))
            ys.append(py(pv))
        x += w
    d.line(list(zip(xs, ys)), fill=BLUE, width=4, joint="curve")
    d.text((T1 - 16, py(275) - 18), "充到 275", font=f(21, True), fill=BLUE, anchor="rb")
    d.text((x1, py(15) + 46), "降到 15 mmHg，结束", font=f(21), fill=BLUE, anchor="ra")

    # ---- 三个时刻：只画虚线，文字统一在下面列表里
    for mx in (T0, T1, T2):
        for yy in range(int(yb1 + 8), int(ybot) - 6, 16):
            d.line([mx, yy, mx, yy + 7], fill=(214, 120, 120), width=2)

    # ---- 脉搏注入状态带
    yp0, yp1 = 672, 724
    d.text((100, 644), "气路里脉搏的处境", font=f(22, True), fill=MUTED)
    bands = [(x0, T1, GRAY_F, GRAY_E, "活塞在动 · 但气室没封 → 量不到 ΔP", MUTED),
             (T1, T2, (252, 232, 232), (216, 140, 140), "被冲击淹没", (150, 60, 60)),
             (T2, T1 + 600, GREEN_F, GREEN_E, "有效搏动区：基线平稳 · 幅度足够 → 正式采集", (38, 110, 76)),
             (T1 + 600, x1, GRAY_F, GRAY_E, "收尾", MUTED)]
    for a, b, fl, ed, label, tc in bands:
        d.rectangle([a, yp0, b, yp1], fill=fl, outline=ed, width=2)
        d.text(((a + b) / 2, (yp0 + yp1) / 2), label, font=f(19, True), fill=tc, anchor="mm")

    # ---- ①②③ 解释列表
    rows = [
        ("1", "充气阶段：活塞已经在往复推气，但阀1 开着、气室没封死，推入的空气直接跑掉 —— 压力搏动测不出来。",
         "所以这一段只记“压力在涨”，不参与血压计算。", GRAY_E, (110, 118, 132)),
        ("2", "封阀完成：气室变成密闭刚性腔，静压 275 mmHg。从这一刻起，同样一团往复容积才被压成可测的 ΔP。",
         "这才是“脉搏进入气路”的时刻：物理上它一直在，作为可测信号它从封阀开始。", AMBER_E, (150, 100, 30)),
        ("3", "开阀约 2 s 后：放气阀一开就有冲击振铃，1–2 s 内它比脉搏本身还大。",
         "等振铃衰减、基线匀速，包络才干净；固件因此丢掉放气最初 2 s（80 个样本）。", GREEN_E, (38, 110, 76)),
    ]
    ry = 754
    for num, main, why, edge, tcol in rows:
        d.ellipse([100, ry, 132, ry + 32], fill=WHITE, outline=edge, width=3)
        d.text((116, ry + 16), num, font=f(20, True), fill=tcol, anchor="mm")
        d.text((146, ry + 2), main, font=f(21), fill=INK, anchor="la")
        d.text((146, ry + 36), why, font=f(19), fill=tcol, anchor="la")
        ry += 56

    img.save(os.path.join(OUT, "fig2_timeline.png"))


# ============================================================ 图 3 为什么要有静压
def fig3_whypulse():
    img, d = canvas(1600, 830)
    title(d, "图 3  同一团 0.55 cc 空气，为什么只有“封阀 + 有静压”时才推得出压力搏动",
          "左：气室状态不同，压力响应天差地别；右：ΔP 与静压近似成正比，这正是示波法能用的前提。")

    panels = [
        (60, "① 充气中 · 阀1 开 · P ≈ 20 mmHg",
         "空气被推入后直接从打开的阀跑掉，", "ΔP ≈ 0.05 mmHg，淹没在充气斜率里"),
        (570, "② 封阀瞬间 · P = 275 mmHg",
         "气室成了密闭刚性腔，容积被压成压力，", "ΔP ≈ 2.9 mmHg，但叠加阀冲击振铃"),
        (1080, "③ 慢放峰区 · P = 215 mmHg",
         "基线匀速下降，搏动对称地叠在上面，", "ΔP ≈ 2.3 mmHg，这才是干净信号"),
    ]
    tw = 460
    for px, head, l1, l2 in panels:
        d.text((px, 176), head, font=f(21, True), fill=INK)
        d.text((px, 210), l1, font=f(19), fill=MUTED)
        d.text((px, 240), l2, font=f(19), fill=MUTED)
        d.rounded_rectangle([px, 276, px + tw, 466], radius=14, fill=WHITE,
                            outline=(214, 222, 236), width=2)

    tt2 = np.linspace(0, 2.0, 900)
    pw = pulse_wave(tt2)

    # ① 几乎平线
    y = 276 + 95 - 0.4 * pw
    d.line([(60 + 20 + i * 420 / 899, y[i]) for i in range(900)], fill=BLUE, width=3)
    d.text((60 + 14, 276 + 20), "P ≈ 20", font=f(18), fill=MUTED, anchor="la")
    d.text((60 + tw - 12, 276 + 34), "ΔP ≈ 0.05", font=f(20, True), fill=RED, anchor="ra")

    # ② 有搏动 + 衰减振铃
    ring = 16 * np.exp(-tt2 / 0.35) * np.sin(2 * np.pi * 3.2 * tt2)
    y = 276 + 110 - (11 * pw + ring)
    d.line([(570 + 20 + i * 420 / 899, y[i]) for i in range(900)], fill=BLUE, width=3)
    d.text((570 + 14, 276 + 20), "P = 275", font=f(18), fill=MUTED, anchor="la")
    d.text((570 + tw - 12, 276 + 34), "ΔP ≈ 2.9 + 振铃", font=f(20, True), fill=RED, anchor="ra")

    # ③ 匀速下降 + 搏动
    y = 276 + 55 + 70 * (tt2 / 2.0) - 9 * pw
    d.line([(1080 + 20 + i * 420 / 899, y[i]) for i in range(900)], fill=BLUE, width=3)
    d.text((1080 + 14, 276 + 20), "P = 215 ↓", font=f(18), fill=MUTED, anchor="la")
    d.text((1080 + tw - 12, 276 + 34), "ΔP ≈ 2.3", font=f(20, True), fill=GREEN_E, anchor="ra")

    # 右：ΔP ∝ P
    ax0, ax1 = 200, 1300
    ay0, ay1 = 556, 686

    def gx(p):
        return ax0 + (p / 300.0) * (ax1 - ax0)

    def gy(v):
        return ay1 - (v / 3.6) * (ay1 - ay0)

    d.text((100, 496), "压力搏动幅度 ΔP 与静压 P 的关系", font=f(23, True), fill=INK)
    for gv in (0, 1, 2, 3):
        yy = gy(gv)
        d.line([ax0, yy, ax1, yy], fill=(238, 241, 247), width=1)
        d.text((ax0 - 12, yy), f"{gv}", font=f(18), fill=MUTED, anchor="rm")
    d.text((ax0 - 18, ay0 - 12), "ΔP / mmHg", font=f(18), fill=MUTED, anchor="ls")
    for pv in (0, 100, 200, 300):
        d.line([gx(pv), ay1, gx(pv), ay1 + 6], fill=MUTED, width=2)
        d.text((gx(pv), ay1 + 12), str(pv), font=f(18), fill=MUTED, anchor="ma")
    d.text((ax1, ay1 + 44), "P / mmHg", font=f(18), fill=MUTED, anchor="ra")

    k = 2.45 / 215.0
    d.line([(gx(0), gy(0)), (gx(300), gy(k * 300))], fill=ORANGE, width=4)
    for pv, lb, dx, dy, anc in ((20, "① 20", 10, -16, "lb"), (215, "③ 215", 12, 10, "lt"),
                                 (275, "② 275", -6, -26, "rb")):
        cx, cy = gx(pv), gy(k * pv)
        d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=RED)
        d.text((cx + dx, cy + dy), lb, font=f(19, True), fill=RED, anchor=anc)

    note(d, 100, 760, [
        "只记一条关系：ΔP ∝ P。静压翻倍，同样一团往复容积推出来的搏动也翻倍；P→0 时 ΔP→0，所以低压段信号几乎看不见。",
    ], size=20, color=INK)
    img.save(os.path.join(OUT, "fig3_whypulse.png"))


# ============================================================ 图 5 波形
def pulse_wave(t):
    ph = (t / 0.75) % 1.0
    up = np.clip(ph / 0.18, 0, 1)
    down = np.exp(-np.clip(ph - 0.18, 0, None) / 0.30)
    return np.where(ph < 0.18, up, down)


def fig5_waveform():
    img, d = canvas(1600, 1000)
    title(d, "图 5  采到的原始数据长什么样：下降斜坡上叠着脉搏",
          "横轴为时间（s），纵轴为折算后的袖带压力（mmHg）；按本机标定与 80 BPM 合成，用于示意形态。")

    fs = 40.0
    t = np.arange(0, 106, 1 / fs)
    p = np.zeros_like(t)
    for i, ti in enumerate(t):
        if ti < 6:
            p[i] = 0
        elif ti < 34:
            p[i] = 275 * ((ti - 6) / 28) ** 1.25
        elif ti < 36:
            p[i] = 275
        elif ti < 104:
            p[i] = 275 - (ti - 36) * (260 / 68)
        else:
            p[i] = 275 - 260
    amp = 0.05 + 1.40 * np.exp(-((p - 200) / 42.0) ** 2)
    amp[t < 8] = 0.0
    sig = p + amp * pulse_wave(t)

    ax0, ax1, ay0, ay1 = 130, 1520, 190, 505
    d.rectangle([ax0, ay0, ax1, ay1], fill=WHITE, outline=(226, 231, 240), width=2)
    d.text((ax0, ay0 - 12), "① 全量程（0 – 275 mmHg）：充气 → 封阀 → 慢放", font=f(22, True), fill=INK, anchor="lb")
    for gv in (0, 100, 200, 275):
        yy = ay1 - (gv / 290) * (ay1 - ay0)
        d.line([ax0, yy, ax1, yy], fill=(238, 241, 247), width=1)
        d.text((ax0 - 14, yy), str(gv), font=f(20), fill=MUTED, anchor="rm")
    xs = ax0 + (t / 106) * (ax1 - ax0)
    ys = ay1 - (sig / 290) * (ay1 - ay0)
    d.line(list(zip(xs, ys)), fill=BLUE, width=2)
    for xt in (0, 20, 40, 60, 80, 100):
        d.text((ax0 + (xt / 106) * (ax1 - ax0), ay1 + 14), str(xt), font=f(20), fill=MUTED, anchor="ma")
    d.text((ax1, ay1 + 14), "t / s", font=f(20), fill=MUTED, anchor="ra")

    bx0, bx1, by0, by1 = 130, 1520, 600, 860
    d.rectangle([bx0, by0, bx1, by1], fill=WHITE, outline=(226, 231, 240), width=2)
    d.text((bx0, by0 - 12), "② 放大 60 – 72 s：同一条曲线，搏动就叠在斜线上", font=f(22, True), fill=INK, anchor="lb")
    m = (t >= 60) & (t <= 72)
    tt, ss = t[m], sig[m]
    ylo, yhi = ss.min() - 2, ss.max() + 22
    for k in np.arange(np.ceil(ylo / 5) * 5, yhi, 5.0):
        yy = by1 - ((k - ylo) / (yhi - ylo)) * (by1 - by0)
        d.line([bx0, yy, bx1, yy], fill=(238, 241, 247), width=1)
        d.text((bx0 - 14, yy), f"{k:.0f}", font=f(20), fill=MUTED, anchor="rm")
    xs2 = bx0 + ((tt - 60) / 12) * (bx1 - bx0)
    ys2 = by1 - ((ss - ylo) / (yhi - ylo)) * (by1 - by0)
    d.line(list(zip(xs2, ys2)), fill=BLUE, width=3)
    d.text((ax1, by1 + 14), "t / s", font=f(20), fill=MUTED, anchor="ra")

    # 基线（橙色）
    pa = 275 - (60.5 - 36) * (260 / 68)
    pb = 275 - (71.5 - 36) * (260 / 68)
    ya = by1 - ((pa - ylo) / (yhi - ylo)) * (by1 - by0)
    ybk = by1 - ((pb - ylo) / (yhi - ylo)) * (by1 - by0)
    d.line([bx0 + 6, ya, bx1 - 6, ybk], fill=AMBER_E, width=3)
    d.text((bx0 + 18, by1 - 74), "橙色 = 缓变基线（放气斜坡 ≈ 3.8 mmHg/s）", font=f(21, True),
           fill=(150, 100, 30), anchor="la")
    d.text((bx0 + 18, by1 - 38), "蓝色 = 基线 + 脉搏（峰–峰 ≈ 2.8 mmHg，周期 0.75 s）", font=f(21),
           fill=INK, anchor="la")

    idx = np.where((t >= 66.0) & (t <= 66.4))[0]
    for i in idx:
        cx = bx0 + ((t[i] - 60) / 12) * (bx1 - bx0)
        cy = by1 - ((sig[i] - ylo) / (yhi - ylo)) * (by1 - by0)
        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=RED)
    d.text((bx0 + 16, by1 + 14), "红点 = 每 25 ms 取一个样本（40 Hz）", font=f(21, True), fill=RED, anchor="la")

    note(d, 130, 900, ["每个样本同时记下：MCU tick、袖带压力 p、振荡输入 v、包络 e、平滑包络 s。"], size=21)
    img.save(os.path.join(OUT, "fig5_waveform.png"))


# ============================================================ 图 6 包络
def fig6_envelope():
    fs = 40.0
    t = np.arange(0, 78, 1 / fs)
    p = 275 - t * (265 / 78.0)
    amp = 0.05 + 1.40 * np.exp(-((p - 215) / 42.0) ** 2)
    v = (p + amp * pulse_wave(t) + 19.887) / 82.326

    n = len(v)
    W = 32                                                    # 与固件 extract_envelope_value 一致
    resid = np.zeros(n)
    for i in range(n):
        lo, hi = max(0, i - W), min(n - 1, i + W)
        ys = v[lo:hi + 1]
        xs = np.arange(lo, hi + 1, dtype=float)
        xm, ym = xs.mean(), ys.mean()
        dx = xs - xm
        var = (dx ** 2).sum()
        a = ((dx * (ys - ym)).sum() / var) if var > 1e-12 else 0.0
        resid[i] = v[i] - (a * (i - xm) + ym)                 # 拟合值取在窗中心
    e = np.abs(resid)
    s = np.convolve(e, np.ones(32) / 32.0, mode="same")       # 与固件 32 点平滑一致

    lo_i, hi_i = 120, n - 60
    valid = slice(lo_i, hi_i)
    tv, pv, vv, rv, ev, sv = t[valid], p[valid], v[valid], resid[valid], e[valid], s[valid]

    j = int(np.argmax(sv))
    mp = pv[j]
    peak = sv[j]
    up = np.where(sv[:j] >= 0.5 * peak)[0]
    sbp = pv[up[0]] if len(up) else pv[0]
    dn = np.where(sv[j:] <= 0.6 * peak)[0]
    dbp = pv[j + dn[0]] if len(dn) else pv[-1]

    img, d = canvas(1600, 1090)
    title(d, "图 6  从电压序列里“认出”气压与脉搏：去趋势 → 包络 → 特征点",
          "三段共用同一条时间轴；纵轴依次为 V、V、mV（示意数值，用于说明形态与判据）。")

    panels = [(180, 360, "① 传感器端电压 sensor 序列：放气斜坡上叠着搏动"),
              (432, 606, "② 去趋势残差：逐点减去 65 点局部最小二乘基线"),
              (700, 900, "③ 包络：|残差| 再做 32 点平均，横轴换成对应的袖带压力")]
    ax0, ax1 = 130, 1520
    for (y0, y1, label) in panels:
        d.text((ax0, y0 - 14), label, font=f(22, True), fill=INK, anchor="lb")
        d.rectangle([ax0, y0, ax1, y1], fill=WHITE, outline=(226, 231, 240), width=2)

    def series(y0, y1, data, col, width=2, pad=0.10, xarr=None):
        lo, hi = float(np.min(data)), float(np.max(data))
        rng = (hi - lo) or 1.0
        lo -= rng * pad
        hi += rng * pad
        xx = ax0 + (np.asarray(xarr) / t.max()) * (ax1 - ax0)
        yy = y1 - ((np.asarray(data) - lo) / (hi - lo)) * (y1 - y0)
        d.line(list(zip(xx, yy)), fill=col, width=width)
        return lo, hi

    series(*panels[0][:2], data=vv, col=BLUE, width=2, xarr=tv)
    lo2, hi2 = series(*panels[1][:2], data=rv, col=GREEN_E, width=2, xarr=tv)
    yz = panels[1][1] - ((0 - lo2) / (hi2 - lo2)) * (panels[1][1] - panels[1][0])
    d.line([ax0, yz, ax1, yz], fill=(206, 212, 222), width=1)

    y0, y1 = panels[2][0], panels[2][1]
    lo3, hi3 = 0.0, float(sv.max()) * 1.68
    xx = ax0 + ((275 - pv) / (275 - 5)) * (ax1 - ax0)
    yy = y1 - ((sv - lo3) / (hi3 - lo3)) * (y1 - y0)
    d.line(list(zip(xx, yy)), fill=ORANGE, width=3)
    for gv in (250, 200, 150, 100, 50):
        gx = ax0 + ((275 - gv) / (275 - 5)) * (ax1 - ax0)
        d.line([gx, y1 - 8, gx, y1], fill=(180, 186, 196), width=1)
        d.text((gx, y1 + 24), str(gv), font=f(19), fill=MUTED, anchor="ma")
    d.text((ax1, y1 + 52), "袖带压力 / mmHg（从高到低）", font=f(21), fill=MUTED, anchor="ra")

    for ratio, colr, lbl, dy, anc in ((0.6, GREEN_E, "60%", -8, "rs"), (0.5, BLUE, "50%", 22, "rs")):
        ly = y1 - ((peak * ratio - lo3) / (hi3 - lo3)) * (y1 - y0)
        d.line([ax0, ly, ax1, ly], fill=colr, width=1)
        d.text((ax1 - 12, ly + dy), f"{lbl} 峰高", font=f(19), fill=colr, anchor=anc)

    def mark(pval, lbl, colr):
        """竖线画满面板；标注统一放在面板顶部一行，文字右挂竖线避免互相覆盖。"""
        gx = ax0 + ((275 - pval) / (275 - 5)) * (ax1 - ax0)
        d.line([gx, y0 + 4, gx, y1], fill=colr, width=2)
        d.text((gx + 9, y0 + 30), lbl, font=f(20, True), fill=colr, anchor="ls")

    # 三个特征点按压力从高到低排列：高压侧（左）的标注不会被右边的压住
    for nm, pval, colr in sorted([("SBP", sbp, BLUE), ("MAP", mp, RED), ("DBP", dbp, GREEN_E)],
                                 key=lambda z: -z[1]):
        mark(pval, f"{nm} = {pval:.0f}", colr)

    note(d, 130, 985, [
        "判据写死在固件里：MAP = 平滑包络全局最大的位置；SBP = 高压侧首次 ≥50% 峰高；DBP = 低压侧连续 3 点 ≤60% 峰高。",
        "固件还额外排除 80 mmHg 以下与 100 mmHg 以上的 MAP 候选，以及放气起始 2 s、收尾 15 个样本的阀门冲击瞬态。",
    ], size=20, color=INK, gap=40)
    img.save(os.path.join(OUT, "fig6_envelope.png"))


if __name__ == "__main__":
    fig1(); fig2_timeline(); fig3_whypulse(); fig4_chain(); fig5_waveform(); fig6_envelope()
    for name in sorted(os.listdir(OUT)):
        print(name, os.path.getsize(os.path.join(OUT, name)))
