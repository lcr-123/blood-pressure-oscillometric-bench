# -*- coding: utf-8 -*-
"""生成给老师看的项目说明文档（示波法袖带压力采集流程）。"""
import os

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
OUT = os.path.join(os.path.dirname(HERE), "示波法血压采集流程说明.docx")

INK = RGBColor(0x21, 0x27, 0x32)
MUTED = RGBColor(0x6C, 0x78, 0x8A)
ACCENT = RGBColor(0x3A, 0x62, 0xAC)
BODY_CN = "宋体"
HEAD_CN = "黑体"


def set_font(run, cn=BODY_CN, size=10.5, bold=False, color=INK, western="Times New Roman"):
    run.font.name = western
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), cn)
    rfonts.set(qn("w:ascii"), western)
    rfonts.set(qn("w:hAnsi"), western)


def shade(cell, hex_color):
    tcpr = cell._tc.get_or_add_tcPr()
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:color"), "auto")
    el.set(qn("w:fill"), hex_color)
    tcpr.append(el)


def body(doc, text, size=10.5, first_indent=True, space_after=5, align=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.38
    pf.space_before = Pt(0)
    pf.space_after = Pt(space_after)
    if first_indent:
        pf.first_line_indent = Pt(21)
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    set_font(run, size=size)
    return p


def h1(doc, num, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(16)
    pf.space_after = Pt(7)
    pf.keep_with_next = True
    run = p.add_run(f"{num}　{text}")
    set_font(run, cn=HEAD_CN, size=14, bold=True, color=ACCENT)
    # 标题下加一条细分隔线
    pPr = p._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "3")
    bottom.set(qn("w:color"), "C9D4E6")
    borders.append(bottom)
    pPr.append(borders)
    return p


def h2(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(10)
    pf.space_after = Pt(4)
    pf.keep_with_next = True
    run = p.add_run(text)
    set_font(run, cn=HEAD_CN, size=11.5, bold=True)
    return p


def bullet(doc, text, size=10.5):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Pt(21)
    pf.first_line_indent = Pt(-11)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.4
    pf.space_after = Pt(3)
    run = p.add_run("· " + text)
    set_font(run, size=size)
    return p


def figure(doc, name, caption, width_cm=15.6):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(os.path.join(FIG, name), width=Cm(width_cm))
    cp = doc.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp.paragraph_format.space_after = Pt(10)
    run = cp.add_run(caption)
    set_font(run, size=9, color=MUTED)


def fix_table_width(t, widths):
    """python-docx 的 cell.width 不会写 tblGrid，这里把列宽真正写进去。"""
    twips = [int(round(w * 567)) for w in widths]
    tbl = t._tbl
    grid = tbl.find(qn("w:tblGrid"))
    if grid is not None:
        tbl.remove(grid)
    grid = OxmlElement("w:tblGrid")
    for w in twips:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(w))
        grid.append(col)
    tblPr = tbl.tblPr
    tblPr.addnext(grid)
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:type"), "dxa")
    tw.set(qn("w:w"), str(sum(twips)))
    old = tblPr.find(qn("w:tblW"))
    if old is not None:
        tblPr.remove(old)
    tblPr.append(tw)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    old = tblPr.find(qn("w:tblLayout"))
    if old is not None:
        tblPr.remove(old)
    tblPr.append(layout)
    for row in t.rows:
        for i, cell in enumerate(row.cells):
            cell.width = Cm(widths[i])


def table(doc, header, rows, widths, caption=None, font_size=9.5):
    if caption:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_before = Pt(6)
        cp.paragraph_format.space_after = Pt(2)
        cp.paragraph_format.keep_with_next = True
        run = cp.add_run(caption)
        set_font(run, size=9, color=MUTED)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, w in enumerate(widths):
        for cell in t.columns[i].cells:
            cell.width = Cm(w)
    for i, h in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.width = Cm(widths[i])
        shade(cell, "EAF0F9")
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_after = Pt(2)
        para.paragraph_format.space_before = Pt(2)
        run = para.add_run(h)
        set_font(run, cn=HEAD_CN, size=font_size, bold=True)
    for row in rows:
        cells = t.add_row().cells
        for i, text in enumerate(row):
            cells[i].width = Cm(widths[i])
            para = cells[i].paragraphs[0]
            para.paragraph_format.space_after = Pt(2)
            para.paragraph_format.space_before = Pt(2)
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == len(row) - 1 else WD_ALIGN_PARAGRAPH.CENTER
            run = para.add_run(text)
            set_font(run, size=font_size)
    fix_table_width(t, widths)
    return t


def code_block(doc, lines):
    for i, line in enumerate(lines):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Pt(18)
        pf.space_before = Pt(4 if i == 0 else 0)
        pf.space_after = Pt(4 if i == len(lines) - 1 else 0)
        pf.line_spacing = 1.15
        run = p.add_run(line)
        set_font(run, cn="Consolas", size=8.5, western="Consolas", color=RGBColor(0x22, 0x33, 0x44))


def key_takeaway(doc, text):
    """带底色的“这一步为什么重要”提示条。"""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    cell = t.rows[0].cells[0]
    cell.width = Cm(15.6)
    shade(cell, "F2F6FC")
    tcpr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for side, sz in (("left", "24"), ("top", "4"), ("bottom", "4"), ("right", "4")):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), sz)
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "3A62AC" if side == "left" else "D8E2F2")
        borders.append(el)
    tcpr.append(borders)
    para = cell.paragraphs[0]
    para.paragraph_format.space_before = Pt(4)
    para.paragraph_format.space_after = Pt(4)
    para.paragraph_format.line_spacing = 1.35
    run = para.add_run(text)
    set_font(run, size=9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def build():
    doc = Document()

    # 页面：A4，常规页边距
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.4)
    sec.bottom_margin = Cm(2.2)
    sec.left_margin = Cm(2.6)
    sec.right_margin = Cm(2.6)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_CN)

    # ---------------- 标题区
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(24)
    p.paragraph_format.space_after = Pt(4)
    set_font(p.add_run("基于示波法的袖带压力采集流程说明"), cn=HEAD_CN, size=20, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    set_font(p.add_run("MPXV5050GP + ADS1115 + STM32F103ZET6 台架系统"), cn=HEAD_CN, size=12, color=ACCENT)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    set_font(p.add_run("非人体台架验证 · 项目阶段汇报 · 2026 年 11 月"), size=9.5, color=MUTED)

    # ---------------- 0 项目要做什么
    h1(doc, "引言", "这个项目要做什么")
    body(doc,
         "一句话说：把袖带里的压力波形“原样”采下来、存成别人能复核的数据，做一套开放的示波法血压波形数据集。"
         "具体交付三样东西——第一是开放的压力波形数据集（不只是最终那个收缩压／舒张压数字，而是整段原始波形）；"
         "第二是配套的参考算法脚本（从波形怎么算出包络、怎么定三个特征点，全部给出来）；"
         "第三是第三方可复现的验证流程（拿到数据的人能按文档重跑一遍，得到同样的结果）。"
         "这三样合起来服务于一篇数据论文和后续的方法研究。")
    body(doc,
         "为什么值得做这件事：公开的袖带压力波形数据很少，大多数公开数据只给结论性的血压值，"
         "中间那段“压力曲线长什么样、包络怎么长出来”的过程被丢掉了，别人既没法复核也无从改进算法。"
         "我们想把这段中间过程完整留下来——这也是本项目反复强调“可复现”的原因：不是给一条结论曲线，"
         "而是把每一个中间量都摊开。")
    body(doc,
         "当前做到哪一步：硬件链路（MPXV5050GP → ADS1115 → STM32F103ZET6 → 串口 → 电脑）已经打通，"
         "能按固定时序完成充气、封阀、慢放和结构化导出，峰区（200–245 mmHg）还做了专门的降速采集以提高分辨率。"
         "但必须说明边界——目前全部数据来自 BP Pump 2 台架，不是人体；"
         "因此本文不宣称任何临床准确性，也不能替代 ISO 81060-2 的临床验证。"
         "项目现在的定位是“采集链路已经通了”，而不是“血压已经算准了”。")

    body(doc,
         "本文档只讲这条链路的其中一段：数据究竟是怎么来的。重点回答三个问题——"
         "脉搏是什么时候进入气路的、为什么必须是那个时间；气室里的气压怎样一步步变成单片机里的数字；"
         "以及我们怎样从一串数字里把“气压值”和“脉搏”分别认出来。"
         "其余部分（算法整定、指标评估、数据集组织）不在本文范围内。全文插图均为程序绘制的示意图，不含实物照片。")

    # ---------------- 1 系统构成
    h1(doc, "一", "系统构成与一次采集的边界")
    body(doc,
         "整条链路只做一件事：把袖带气室里的气压，变成可以在电脑上逐点复查的数字序列。"
         "硬件分三层——气路（泵、两个阀、袖带、压力传感器）、电子（传感器输出经电阻分压后进入 ADS1115，"
         "再由 STM32F103ZET6 通过 I2C 读取）、软件（固件负责阀序与采样，电脑端脚本负责记录与校验）。")
    body(doc,
         "需要特别说明：本项目当前是纯台架系统，用 BP Pump 2 无创血压模拟器的压力口代替人体，"
         "由它按面板预设向气室注入“脉搏”；因此本文所有数据都不构成任何临床准确性结论。"
         "选它做源的好处是脉搏的幅度、节奏、包络形状都可复现，便于反复验证采集与算法。")

    # ---------------- 2 气路
    h1(doc, "二", "气路：所有器件并接在同一个压力节点上")
    body(doc,
         "气路拓扑非常朴素，但它是后面所有推理的前提：袖带气室、传感器气嘴 P1、BP Pump 2 压力口、"
         "充气支路（泵 + 阀1）、放气支路（阀2）全部并接在同一个三通接头上。也就是说，"
         "这几处看到的压力在稳态下是同一个值，谁也不比谁“更靠上游”。")
    body(doc,
         "传感器选型要说清楚一个容易搞错的点：MPXV5050GP 是单气嘴的 GP 封装（手册 Table 2 记 Case 1369、"
         "# of Ports = Single、Pressure Type = Gauge），整只器件只有一个气嘴，就是 P1 压力侧"
         "（手册 Table 7：Case 1369 的 P1 在“Side with Port Attached”那一面）。"
         "背面的 P2 侧不需要、也不应该再接一根通气管，它靠封装与大气相通。")
    body(doc,
         "正因为是单气嘴、背面敞开，它输出的是表压——袖带内相对当地大气的压力差。"
         "这样“袖带没有压力”就对应“读数约为 0”，零点天然确定，不必再引入绝对压力基准。"
         "反过来说，一旦把背面的通气路径用胶或泡棉封住，参考端就被固定住，读数会随环境气压慢慢漂，"
         "而且低压段的零点会整体偏移——这是这类单气嘴器件最常见的误用。")
    figure(doc, "fig1_pneumatic.png", "图 1　气路构成示意：所有器件共用一个压力节点；传感器只有一个气嘴")
    body(doc,
         "阀门的极性同样被固件写死：充气阀 PB8 低电平吸合，放气阀 PC1 高电平打开，泵继电器 PC8 低电平启动。"
         "之所以强调这一点，是因为阀序错一步，后面的时序推理就全部失效——比如放气阀没关严，"
         "袖带就永远建立不起静压，也就永远不会有脉搏。")
    key_takeaway(doc,
                 "气路收尾有一条铁律：vent（开阀2 通大气）→ 等读数走平、不再下降 → 再 seal（封阀）盘车。"
                 "阀2 不能长期通大气，否则下一次采集的起点不可信。"
                 "但要注意一个反直觉的地方：vent 态的读数不是零点。阀2 线圈通电本身就把压力通道抬高，"
                 "实测同一套气路在 vent 态比 seal 态高 0.4–7.4 mmHg，且随线圈热态变化——"
                 "所以能证明“气路真的空了”的，是 seal 之后的真零点（|读数| ≤ 5.0 mmHg），而不是 vent 态读数回到 0。")

    # ---------------- 3 时序
    h1(doc, "三", "一轮采集的完整时序")
    body(doc,
         "一次采集按固定顺序推进，每一步都在为下一步准备条件。完整一轮的采样段约 70–100 s，"
         "加上充气与收尾，实际操作在 90–110 s 量级。")
    figure(doc, "fig2_timeline.png", "图 2　一轮采集的时序与袖带压力走向（横轴为示意比例）",
           width_cm=15.6)

    table(doc,
          ["#", "步骤", "做什么", "为什么必须这样"],
          [
              ["1", "vent", "开阀2，气室通大气", "把上一轮的残压卸掉。判据是读数走平且不再下降，不是“回到 0”——vent 态读数带着阀2 线圈偏移，本身不是零点"],
              ["2", "seal", "关阀2，形成密闭气室", "只有密闭，后面泵打进去的空气才留得住，压力才能累积"],
              ["3", "充气", "关阀2、开阀1、启动泵，冲到目标 275 mmHg", "目标必须高于面板预设的收缩压（255 mmHg），否则扫不到包络的上升沿"],
              ["4", "停泵封阀", "泵停、阀1 关、阀2 关，短暂静置", "泵与阀动作会激起压力冲击，静置让这段瞬态先衰减掉"],
              ["5", "慢放", "阀2 以 20 ms 周期做 PWM 开合，压力按设定速率下降", "匀速下降把“压力轴”变成“时间轴”，包络才可稳定判读"],
              ["6", "收尾", "降到 15 mmHg 结束，vent 卸压，再 seal", "彻底卸压并回到安全待机态，为下一轮准备干净的起点；空否由 seal 后的真零点验证"],
          ],
          widths=[0.9, 2.1, 5.6, 7.0],
          caption="表 1　时序各步骤的动作与理由")

    h2(doc, "3.1　为什么充气目标是 275 mmHg，而不是“够用就行”")
    body(doc,
         "示波法要从包络上找三个特征点，其中收缩压对应包络上升到一半的位置。若起始压力只到 200 mmHg，"
         "而实际收缩压在 255 mmHg，那么包络的上升沿根本不在记录区间里，特征点无从谈起。"
         "275 mmHg 是按“高于源端预设收缩压、又留出安全余量”取的值；固件另有 280 mmHg 的硬上限，"
         "一旦越限立即停泵放气，不依赖上位机。")
    h2(doc, "3.2　为什么放气要慢，而且峰区还要更慢")
    body(doc,
         "放气速率决定了“每个搏动占据多少个压力点”。常规段设 2.0 mmHg/s，高压段 3.0 mmHg/s，"
         "进入 200–245 mmHg 的峰区降到 1.8 mmHg/s。原因是峰区正是包络最陡、最需要分辨率的位置："
         "降速后每一次搏动被更多采样点覆盖，包络曲线的形状才可信。")
    body(doc,
         "速率本身靠阀2 的 PWM 闭环维持：每 400 ms 用最近约 0.4 s 的压力差算一次实际速率，"
         "做一阶平滑后与目标比较，误差超过 0.4 mmHg/s 才调整阀门开启时长，"
         "避免对每个采样点都做修正而引入抖动。")

    # ---------------- 4 脉搏时机（核心）
    h1(doc, "四", "脉搏是什么时候进入气路的，为什么必须是这个时间")
    body(doc,
         "这是整份文档最需要讲清楚的一点，所以要分“物理上”和“可测上”两个层面回答。")
    body(doc,
         "物理上，脉搏从充气一开始就已经在推气：BP Pump 2 检测到袖带压力被充起来，就开始按预设节律往复"
         "排挤一团 0.55 cc 的空气，这个动作贯穿整个采集过程。"
         "但从“可测信号”的角度，它要等到两个条件同时满足才真正进入气路——"
         "气室已经封阀（容积被闭死），并且里面已经建立了静压（有可被压缩的空气）。"
         "这两件事都在封阀完成的那一刻达成，所以答案是：脉搏在封阀完成的那一刻起，才作为压力搏动出现在测量通道里。")
    h2(doc, "4.1　物理原因：气囊推的是容积，我们测的是压力")
    body(doc,
         "往复排挤的那团空气进入气室后，若气室已经封闭并已有静压 P，则体积被压缩一点点，压力就上升 ΔP，近似有")
    core = doc.add_paragraph()
    core.alignment = WD_ALIGN_PARAGRAPH.CENTER
    core.paragraph_format.space_before = Pt(2)
    core.paragraph_format.space_after = Pt(6)
    set_font(core.add_run("ΔP ≈ P · ΔV / V"), cn=HEAD_CN, size=12, bold=True, color=ACCENT)
    body(doc,
         "式中 ΔV 是挤进来的容积，V 是气室总容积，P 是当时的气室静压。这个式子说明两件事："
         "第一，同样的容积往复，静压越高，产生的压力搏动越大；第二，当 P 接近 0 时，ΔP 也接近 0——"
         "袖带还通着大气，多出来的空气直接跑掉，压力几乎不变。")
    figure(doc, "fig3_whypulse.png",
           "图 3　同一团往复空气在不同气室状态下的压力响应；右侧说明 ΔP 与静压近似成正比", width_cm=15.6)
    body(doc,
         "按本项目的气室规模（袖带 300 cc 以上）与 275 mmHg 的静压估算，0.55 cc 往复对应的 ΔP 只有 1–3 mmHg 量级。"
         "这就是为什么读数看起来“脉搏只引起一点点波纹”——不是信号弱得离谱，而是示波法本来就是测这点波纹。"
         "也正因如此，任何一步错误（阀没关严、管路漏气、充气中采样）都会把这 1–3 mmHg 完全淹没。")
    h2(doc, "4.2　三个时间约束：什么时候能测、什么时候才可信")
    body(doc,
         "把上面两件事按时序排开，就得到三个必须分开看的时刻（对应图 2 的三条虚线）：")
    bullet(doc, "① 充气开始：活塞已经在往复，但阀1 开着、气室没封死，推入的空气直接从放气阀跑掉，"
                "压力搏动测不出来。这一段只记“压力在涨”，不参与血压计算。")
    bullet(doc, "② 封阀完成：气室变成密闭刚性腔，静压 275 mmHg。从这一刻起同样的往复容积才开始被压成可测的 ΔP。"
                "这才是“脉搏进入气路”的时刻。")
    bullet(doc, "③ 开阀约 2 s 后：放气阀首次打开会产生 1–2 s 的压力振铃，幅度远大于真实脉搏。"
                "等振铃衰减、基线匀速下降，包络才干净；算法因此固定跳过前 2 s（80 个样本）的候选区。")
    bullet(doc, "此外收尾时阀2 关闭同样有瞬态，算法在尾部再跳过 15 个样本，避免把这一段当成低压包络；"
                "而充气段整体不采，因为其斜率约 10 mmHg/s，是放气段的 5 倍以上，泵的脉动直接叠在压力上，"
                "脉搏在这种斜率下无法分辨。")
    key_takeaway(doc,
                 "一句话总结：脉搏在“袖带封阀并且已有静压”的那一刻起才成为可测信号；"
                 "而只有在“冲击瞬态过去之后”它才成为可信信号。这两件事共同决定了我们只在慢放段做正式采集。")

    # ---------------- 5 气压→电压
    h1(doc, "五", "气压怎样变成电压、再变成数字")
    body(doc,
         "从气压到串口上的一个整数，中间经过五级换算。每一级只负责一件事，任何一级的系数错了，整条链的读数都会系统性偏移。")
    figure(doc, "fig4_chain.png", "图 4　五级换算链：传感器 → 分压 → ADC → 标定直线 → 串口输出",
           width_cm=15.6)

    h2(doc, "5.1　第一级：压阻传感器把压力变成电压")
    body(doc,
         "MPXV5050GP 是比率式输出的压阻传感器：内部惠斯通电桥在恒定激励下，输出电压与压力近似线性，"
         "同时整体刻度正比于供电电压 VS。其手册给出的传递函数为")
    core = doc.add_paragraph()
    core.alignment = WD_ALIGN_PARAGRAPH.CENTER
    core.paragraph_format.space_before = Pt(2)
    core.paragraph_format.space_after = Pt(6)
    set_font(core.add_run("VOUT = VS × (0.018 · P[kPa] + 0.04)"), cn=HEAD_CN, size=11, bold=True, color=ACCENT)
    body(doc,
         "取 VS = 5.0 V：零压时输出 0.20 V，满量程 50 kPa（约 375 mmHg）时输出 4.7 V，灵敏度约 0.09 V/kPa。"
         "“比率式”三个字很关键——如果 VS 实际是 5.149 V 而不是 5.0 V，整条直线会被整体放大 3%，"
         "这种误差不是靠改一个零点就能补回来的，必须先量准供电电压。项目里已实测并记录该电压轨，原因是它存在漂移。")

    h2(doc, "5.2　第二级：为什么先分压再进 ADC")
    body(doc,
         "传感器在 275 mmHg 附近输出约 3.5 V，接近满量程时更高达 4.7 V；而 ADS1115 的供电上限是 3.3 V，"
         "模拟输入不能超过供电轨。直接把 4.7 V 接进去，轻则削顶，重则损伤输入级。"
         "因此先用电阻分压降到安全范围：上臂 6.823 kΩ、下臂 17.96 kΩ，分压比")
    core = doc.add_paragraph()
    core.alignment = WD_ALIGN_PARAGRAPH.CENTER
    core.paragraph_format.space_before = Pt(2)
    core.paragraph_format.space_after = Pt(6)
    set_font(core.add_run("K = (6.823 + 17.96) / 17.96 = 1.3799"), cn=HEAD_CN, size=11, bold=True, color=ACCENT)
    body(doc,
         "即 ADC 端看到的是传感器电压的 1/1.3799。4.7 V 分压后为 3.41 V，配合 PGA 的 ±4.096 V 量程仍有裕量。"
         "换算时把 K 乘回去即可恢复传感器端电压；代价是 ADC 的 125 µV 分辨率被放大为约 172 µV，"
         "折算到压力约 0.13 mmHg，对 1–3 mmHg 的搏动信号仍绰绰有余。")

    h2(doc, "5.3　第三级：ADS1115 怎样完成量化")
    body(doc,
         "ADS1115 是 16 位 ΔΣ 型 ADC，接在 I2C1（PB6/PB7，地址 0x48）。固件把它配置为：AIN0 单端输入对地、"
         "PGA 增益对应 ±4.096 V 满量程、单次转换模式、数据率 128 SPS。几个选择都有理由：")
    bullet(doc, "单端对地：只需要一路压力信号，省一对差分线，也更容易在台架上查错。")
    bullet(doc, "±4.096 V 档：分压后的最大信号约 3.4 V，落在量程内且不浪费太多分辨率；若用 ±6.144 V 档，每 LSB 变粗。")
    bullet(doc, "单次转换而非连续：采样节奏由固件主循环掌握，避免 ADC 自作主张地连续刷新，读到的数据与压力时刻对不上。")
    bullet(doc, "128 SPS：一次转换约 7.8 ms，是后续 25 ms 采样周期能成立的前提。")
    body(doc,
         "量化关系因此是固定的：满量程 ±4.096 V 对应 16 位有符号数，每 LSB = 4.096 V / 32768 = 125 µV。"
         "固件读回原始码 raw 后，按 raw × 0.000125 得到 ADC 端电压，再乘分压比 K 得到传感器端电压。")

    h2(doc, "5.4　第四级：标定直线把电压翻译成 mmHg")
    body(doc,
         "传感器有制造分散，分压电阻也有实际偏差，所以不能直接套手册公式。项目用 BP Pump 2 的 Pressure Source 模式"
         "在 0/48/92/139/186/235 mmHg 六个静态点上取数，做最小二乘拟合得到一条直线；"
         "2026-11-26 又用 17 个静态点（34–264.85 mmHg）在同一条气路上与 BP Pump 2 自己的读数交叉验证，"
         "发现原来的斜率有约 1% 的系统性偏差，于是重新拟合了一次：")
    core = doc.add_paragraph()
    core.alignment = WD_ALIGN_PARAGRAPH.CENTER
    core.paragraph_format.space_before = Pt(2)
    core.paragraph_format.space_after = Pt(6)
    set_font(core.add_run("P[mmHg] = 81.529 × Vsensor[V] − 20.03"), cn=HEAD_CN, size=11, bold=True, color=ACCENT)
    body(doc,
         "这条直线的斜率决定“每伏代表多少 mmHg”，截距决定零点落在哪个电压上（反解得零点约 0.2457 V，"
         "与手册的 0.20 V 同量级但不相等，这正是器件分散与供电偏离的体现）。"
         "17 个点的拟合残差最大 0.77 mmHg，说明线性模型本身够用；"
         "重标定后最坏总误差从 5.715 降到 2.840 mmHg，17 个点全部落进 BP Pump 2 自身规格"
         " ±(0.5% 读数 + 1) mmHg 之内。")
    body(doc,
         "必须一起记住的是轴的口径：2026-11-26 之前采的所有导出与报告使用的都是旧轴 "
         "82.326 / −19.887。同一段电压用两条轴换算会差 1–3 mmHg，引用旧数据时必须写明轴，"
         "不能把两条轴的数字混在一张表里。")
    body(doc,
         "标定值存在 Flash 末尾一页，带 magic、版本、CRC16 校验，写入后逐字段读回比对；"
         "运行时若校验失败，固件会退回手册默认公式并把串口标记改成 UNCAL，而不是悄悄用一个可疑的斜率。"
         "这一点的意义是：读数永远伴随“它是否可信”的标记。")

    h2(doc, "5.5　第五级：串口把中间量全部摊开")
    body(doc,
         "为了让每一步都能手算复核，固件在一条串口记录里同时给出四个量：原始码、ADC 端电压、传感器端电压、折算压力。"
         "默认以每 250 ms 一条的节奏输出，正式采集时改为每 25 ms 一个样本。")
    code_block(doc, [
        "[Pressure] raw=1401 ads=175mV sensor=242mV est=0.0mmHg VALID",
        "[Pressure] raw=9600 ads=1200mV sensor=1656mV est=115.0mmHg VALID",
    ])
    body(doc,
         "任何人拿到这两行都可以反过来验算：9600 × 0.000125 = 1.2000 V，乘 1.3799 得 1.6559 V，"
         "再乘 81.529 减 20.03 得 115.0 mmHg。这也是本项目“可复现”主张的具体落点——"
         "不是给一条结论曲线，而是把中间量一并公开。")
    body(doc,
         "顺带说明 2026-11-26 之前为什么是 116.4：那段电压乘旧轴 82.326 减 19.887 恰好 116.4，"
         "而 BP Pump 2 的读数更接近 115.0。差的 1.4 mmHg 不是随机噪声，是旧斜率整体偏高 1% 的结果，"
         "在 250 mmHg 附近会放大到 2.7 mmHg——这正是重标定要修的东西。")

    # ---------------- 6 识别
    h1(doc, "六", "怎样从数据里识别出气压值")
    body(doc,
         "这里要区分两个不同的“识别”：一是识别稳态气压值（也就是袖带此刻有多压），"
         "二是识别脉搏（也就是叠加在这条压力曲线上的一点点波动）。前者由上一节的换算直接给出，"
         "后者才需要算法处理。")
    figure(doc, "fig5_waveform.png", "图 5　原始数据形态：全量程曲线，以及放大后看到叠加在斜线上的搏动",
           width_cm=15.6)

    h2(doc, "6.1　稳态气压值：逐点换算即可")
    body(doc,
         "采集得到的每个样本都同时记录 MCU 时间戳、袖带压力 p、振荡输入 v。其中的 p 就是“当前气压值”，"
         "它已经包含分压还原与标定换算，不需要再做任何滤波。之所以敢直接信任它，是因为整条链的误差来源已被逐级确认："
         "分压比来自电阻实测，标定直线来自六点静态拟合，供电电压单独测量并记录。")

    h2(doc, "6.2　脉搏：先去趋势，再取包络")
    body(doc,
         "搏动只有 1–3 mmHg，而压力基线正以每秒几 mmHg 的速度下降，所以不能直接找峰。"
         "固件的做法分三步，对应图 6 的三段曲线：")
    bullet(doc, "去趋势：对每个点，取它前后各 32 个采样点（合计 65 点、约 1.6 s）做最小二乘直线拟合，"
                "用该点实测值减去拟合值。匀速放气的斜坡在残差里趋近于零，叠加的搏动被完整保留。")
    bullet(doc, "整流：对残差取绝对值。搏动是上下对称的波动，取绝对值后每个搏动变成一个向上的鼓包，"
                "便于后续比较幅度。")
    bullet(doc, "平滑：再对整流结果做 32 点（800 ms）滑动平均，得到平滑包络 s。"
                "平滑的目的不是“滤掉脉搏”，而是压掉阀冲击造成的短时振铃，让真实主峰（持续 3–5 s）凸显出来。")
    figure(doc, "fig6_envelope.png", "图 6　去趋势 → 包络 → 特征点：从电压序列里认出气压与脉搏",
           width_cm=15.6)

    h2(doc, "6.3　三个特征点的判据")
    body(doc,
         "包络是一条“先升后降”的钟形曲线，它的形状本身就编码了血压信息。固件用的是经典的比例法：")
    bullet(doc, "MAP（平均压）：在 80–100 mmHg 区间里取平滑包络的全局最大值位置。限定这个区间，是因为"
                "全量程最大很容易被起始瞬态或低压段的 PWM 平台骗走。")
    bullet(doc, "SBP（收缩压）：从高压端往峰顶走，第一次达到 50% 峰高的位置。")
    bullet(doc, "DBP（舒张压）：从峰顶往低压端走，第一次连续 3 个点都低于 60% 峰高的位置。"
                "要求连续 3 点是为了避免下降沿的单个起伏把结果拉偏。")
    body(doc,
         "若某一步找不到特征点，或算出的结果不满足 SBP > MAP > DBP 的生理关系，固件直接判本轮无效、不输出数字，"
         "而不是给一个兜底值。这一取舍是刻意的：宁可承认失败，也不要产出一个看起来合理但错误的血压。")
    key_takeaway(doc,
                 "所以“识别气压值”其实是两件事叠在一起：稳态气压靠换算逐点得到；"
                 "脉搏靠去趋势 + 整流 + 平滑得到包络；血压则靠包络上三个比例点反推。三个环节的输入输出都可从串口逐点复核。")

    # ---------------- 7 数据落盘
    h1(doc, "七", "数据落盘与完整性校验")
    body(doc,
         "正式采集时固件会导出一份结构化记录（schema bp.capture/4），开头声明固件版本、样本数、丢弃数、采样间隔、"
         "标定是否有效与斜率截距，随后逐点给出时间戳、袖带压力、振荡输入、包络与平滑包络，"
         "结尾附 FNV-1a 哈希。浮点值按 IEEE 位模式以整数发出，避免文本格式化带来的精度损失。")
    body(doc,
         "电脑端的解析脚本做的是硬校验而非“尽力读取”：采样间隔必须等于 25 ms、丢弃数必须为 0、"
         "样本数必须在 1–4200 之间、时间戳必须严格递增、点序号必须连续、schema 必须匹配，"
         "任一条件不满足就整份拒绝。这样进入数据集的每一份波形都能追溯到一次完整、未丢点的采集。")

    # ---------------- 8 局限
    h1(doc, "八", "当前边界与已知局限")
    bullet(doc, "全部数据来自 BP Pump 2 台架，不是人体；因此不宣称任何临床准确性，也不能替代 ISO 81060-2 的验证。")
    bullet(doc, "传感器供电轨实测存在漂移，比率式输出会整体改变刻度；目前以单独测量并记录的方式暴露这个问题，尚未根治。")
    bullet(doc, "标定的参考端与实测端来自同一台源，属于结构性弱点。2026-11-26 的 17 点交叉验证把最坏总误差从 "
                "5.715 mmHg 降到 2.840 mmHg、17 点全部落进 BP Pump 2 自身规格，但“同一台源”这个前提没有变，"
                "仍需独立标准器交叉验证。")
    bullet(doc, "峰区降速的实测值仍高于 1.8 mmHg/s 的目标，说明阀门 PWM 闭环还有改进空间。")
    bullet(doc, "固件自带的血压算法（冻结 v2）在 265 轮跨天批次里静默跳过 20 轮（旧轴口径；新轴 26 轮），"
                "21 个“档位 × 参数”格子里能声称“5 mmHg 内”的只有 0 格（旧轴）/ 1 格（新轴，仅 Preset 1 的 MAP，"
                "余量 4.76）。参考算法（三视图中位）在同一批数据上七档过六档（旧轴）/ 五档（新轴），"
                "但它仍是候选算法，没有通过自己的前瞻验证。所以准确说法是：“采集链路通了，"
                "参考算法在台架上接近可用，固件算法还不算准。”")
    bullet(doc, "268–275 mmHg 至今零测量。固件硬上限 280 mmHg、充气目标 275 mmHg，静态交叉验证最高只到 "
                "264.85 mmHg，这一段的高压读数仍是外推。")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(16)
    set_font(p.add_run("— 全文完 —"), size=9, color=MUTED)

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
