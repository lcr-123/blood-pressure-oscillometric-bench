# ============================================================ 图 3 时序
def fig3():
    img, d = canvas(1600, 1010)
    title(d, "图 3  一轮采集的时序：脉搏什么时候才“进”得去、才测得到",
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
    d.text((x1, py(15) + 32), "降到 15 mmHg，结束", font=f(21), fill=BLUE, anchor="ra")

    # ---- 三个时刻：只画虚线，文字统一在下面列表里
    for mx in (T0, T1, T2):
        for yy in range(int(yb1 + 8), int(ybot) - 6, 16):
            d.line([mx, yy, mx, yy + 7], fill=(214, 120, 120), width=2)

    # ---- 脉搏注入状态带
    yp0, yp1 = 806, 858
    d.text((100, 772), "气路里脉搏的处境", font=f(22, True), fill=MUTED)
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
    ry = 636
    for num, main, why, edge, tcol in rows:
        d.ellipse([100, ry, 132, ry + 32], fill=WHITE, outline=edge, width=3)
        d.text((116, ry + 16), num, font=f(20, True), fill=tcol, anchor="mm")
        d.text((146, ry + 2), main, font=f(21), fill=INK, anchor="la")
        d.text((146, ry + 36), why, font=f(19), fill=tcol, anchor="la")
        ry += 56

    img.save(os.path.join(OUT, "fig3_timeline.png"))
