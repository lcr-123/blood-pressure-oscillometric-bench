#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BP Pump 2 Source 模式 · MPXV5050GP 多点静态校准采集脚本
==========================================================
读取血压仪 USART3/CH340 的 [Pressure] 流（20Hz），配合 BP Pump 2 前面板
Pressure Source 逐点加压，记录每点数据并输出：

  1) CSV 原始记录（每点均值/SD：raw、ads_mv、sensor_mv、est_mmhg）
  2) 线性拟合（sensor 电压 V -> mmHg：slope/intercept/R^2）
  3) est 固件读数 vs 面板 Measured 参考的误差表
  4) 建议的 `cal write <slope> <intercept>` 命令

用法：
  python bp_static_calibration.py                    # 自动找 CH340 串口
  python bp_static_calibration.py --port COM5        # 指定串口
  python bp_static_calibration.py --window 8 --skip 1  # 每点记录 8s，丢弃前 1s

交互流程（每点）：
  1) 操作 BP Pump 2：SOURCE 加压到目标 -> 停留在 Pressure Source 屏幕
  2) 回到脚本按 Enter  -> 脚本记录窗口内数据
  3) 输入面板 Measured 值（可回车跳过，事后补 CSV）
  4) 换点重复；输入 q 结束并输出拟合报告

前置：气路按静态校准方案接好（BP Pump 2 Pressure Port <-三通-> 传感器 P1 + 参考容积），
      血压仪已上电、串口正常出 [Pressure] 流。
"""

import argparse
import csv
import os
import re
import statistics
import sys
import time
import datetime

import serial
from serial.tools import list_ports

RE_PRESSURE = re.compile(
    r"\[Pressure\] raw=(\d+) ads=(-?\d+)mV sensor=(-?\d+)mV est=(-?\d+)\.(\d)mmHg\s+(\w+)"
)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_data")
BAUD = 115200


def find_port(preferred=None):
    """定位 CH340 / USB-SERIAL 串口。"""
    if preferred:
        return preferred
    for p in list_ports.comports():
        d = (p.description or "").upper()
        h = (p.hwid or "").upper()
        if "CH340" in d or "USB-SERIAL" in d or "1A86" in h:
            return p.device
    ports = [p.device for p in list_ports.comports()]
    if ports:
        raise SystemExit(
            "未找到 CH340 串口。可用串口: %s\n请用 --port 指定。" % ", ".join(ports)
        )
    raise SystemExit("未找到任何串口，请检查 USB 连接。")


def parse_line(line):
    m = RE_PRESSURE.search(line)
    if not m:
        return None
    return {
        "raw": int(m.group(1)),
        "ads_mv": int(m.group(2)),
        "sensor_mv": int(m.group(3)),
        "est_mmhg": int(m.group(4)) + int(m.group(5)) * 0.1,
        "cal": m.group(6),
    }


def drain_serial(ser, seconds):
    """排空串口缓冲，丢弃加压瞬态/旧数据。"""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        ser.read(ser.in_waiting or 1)
        time.sleep(0.02)


def record_window(ser, window_s, skip_s):
    """记录窗口内所有 [Pressure] 行，返回字段字典（列表）和条数。"""
    fields = {"raw": [], "ads_mv": [], "sensor_mv": [], "est_mmhg": []}
    if skip_s > 0:
        drain_serial(ser, skip_s)
    end = time.monotonic() + window_s
    n = 0
    while time.monotonic() < end:
        line = ser.readline().decode("utf-8", errors="replace").strip()
        if not line:
            continue
        d = parse_line(line)
        if d:
            n += 1
            for k in fields:
                fields[k].append(d[k])
    return fields, n


def stats(fields):
    out = {}
    for k, v in fields.items():
        if len(v) == 0:
            out[k] = None
            continue
        out[k] = {
            "mean": statistics.mean(v),
            "sd": statistics.stdev(v) if len(v) > 1 else 0.0,
            "min": min(v),
            "max": max(v),
            "n": len(v),
        }
    return out


def linear_fit(xs, ys):
    """最小二乘 y = a*x + b，返回 (a, b, r2)。"""
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0:
        return None
    a = sxy / sxx
    b = my - a * mx
    r2 = (sxy * sxy) / (sxx * syy) if syy else 1.0
    return a, b, r2


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="BP Pump 2 Source 静态校准采集")
    ap.add_argument("--port", default=None, help="串口号，如 COM5")
    ap.add_argument("--window", type=float, default=5.0, help="每点记录秒数（默认 5s≈100 条）")
    ap.add_argument("--skip", type=float, default=0.5, help="记录前丢弃秒数（默认 0.5s）")
    ap.add_argument("--no-cmd", action="store_true", help="不发送 stream start/stop（手动开流）")
    args = ap.parse_args()

    port = find_port(args.port)
    print("== 串口: %s @ %d ==" % (port, BAUD))

    ser = serial.Serial(port, BAUD, timeout=1.0)
    time.sleep(0.3)
    ser.reset_input_buffer()

    if not args.no_cmd:
        ser.write(b"stream start\r\n")
        print("已发送: stream start")
        time.sleep(0.5)
        ser.reset_input_buffer()
    print("等待 [Pressure] 流... 确认串口正常后继续。")

    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(OUT_DIR, "calibration_%s.csv" % ts)
    f_csv = open(csv_path, "w", newline="", encoding="utf-8-sig")
    w = csv.writer(f_csv)
    w.writerow([
        "point", "target_setpoint", "panel_measured", "raw_mean", "raw_sd",
        "ads_mv_mean", "ads_mv_sd", "sensor_mv_mean", "sensor_mv_sd",
        "est_mmhg_mean", "est_mmhg_sd", "n_samples", "cal_status",
    ])

    records = []
    point = 0
    print("\n每点操作: BP Pump 2 加压到目标 -> 停留屏幕 -> 回这里按 Enter 记录。输入 q 结束。")
    while True:
        point += 1
        print("\n--- 第 %d 点 ---" % point)
        try:
            resp = input("BP Pump 2 加压完成? 按 Enter 开始记录 / q 结束 / 其他=目标值备注: ").strip()
        except EOFError:
            break
        if resp.lower() == "q":
            break
        fields, n = record_window(ser, args.window, args.skip)
        if n == 0:
            print("!! 未收到 [Pressure] 行，检查串口/固件流。")
            point -= 1
            continue
        st = stats(fields)
        cal = ""
        s = st["est_mmhg"]["mean"]
        print("   记录 %d 条: est=%.2f±%.2f mmHg | sensor=%.1f±%.1f mV | ads=%.1f±%.1f mV | raw=%.0f±%.0f"
              % (n, s, st["est_mmhg"]["sd"],
                 st["sensor_mv"]["mean"], st["sensor_mv"]["sd"],
                 st["ads_mv"]["mean"], st["ads_mv"]["sd"],
                 st["raw"]["mean"], st["raw"]["sd"]))
        # 校准状态从最后一行抓
        try:
            resp = input("输入 BP Pump 2 面板 Measured mmHg（回车跳过）: ").strip()
            if resp:
                panel = float(resp)
            else:
                panel = ""
        except EOFError:
            panel = ""
        row = [
            point, resp if resp and not resp.lower() == "q" else "", panel,
            "%.1f" % st["raw"]["mean"], "%.2f" % st["raw"]["sd"],
            "%.2f" % st["ads_mv"]["mean"], "%.2f" % st["ads_mv"]["sd"],
            "%.2f" % st["sensor_mv"]["mean"], "%.2f" % st["sensor_mv"]["sd"],
            "%.2f" % s, "%.2f" % st["est_mmhg"]["sd"], n, cal,
        ]
        w.writerow(row)
        f_csv.flush()
        records.append({
            "point": point,
            "panel": panel,
            "sensor_v": st["sensor_mv"]["mean"] / 1000.0,
            "ads_v": st["ads_mv"]["mean"] / 1000.0,
            "est": s,
        })
        print("   -> 已写入 %s" % csv_path)

    f_csv.close()

    # ---- 拟合 ----
    fit_recs = [r for r in records if r["panel"] != ""]
    print("\n== 汇总 ==")
    print("记录点: %d | 含面板参考: %d" % (len(records), len(fit_recs)))
    rep = ["BP Pump 2 Source 静态校准报告", "=" * 46, "时间: %s" % ts]
    rep.append("有效点: %d / 总点: %d" % (len(fit_recs), len(records)))

    if len(fit_recs) >= 2:
        xs = [r["sensor_v"] for r in fit_recs]
        ys = [float(r["panel"]) for r in fit_recs]
        fit = linear_fit(xs, ys)
        if fit:
            a, b, r2 = fit
            print("线性拟合 sensor V -> mmHg:  slope=%.3f mmHg/V  intercept=%.2f mmHg  R^2=%.4f"
                  % (a, b, r2))
            print("建议: cal write %.3f %.3f" % (a, b))
            rep += [
                "", "拟合 (sensor 电压 V -> mmHg, 最小二乘):",
                "  slope     = %.3f mmHg/V" % a,
                "  intercept = %.2f mmHg" % b,
                "  R^2       = %.4f" % r2,
                "  建议命令  : cal write %.3f %.3f" % (a, b),
            ]
        xs2 = [r["ads_v"] for r in fit_recs]
        fit2 = linear_fit(xs2, ys)
        if fit2:
            a2, b2, r22 = fit2
            print("线性拟合 ads  V -> mmHg:  slope=%.3f mmHg/V  intercept=%.2f mmHg  R^2=%.4f"
                  % (a2, b2, r22))
            rep += [
                "拟合 (ads 电压 V -> mmHg):",
                "  slope     = %.3f mmHg/V" % a2,
                "  intercept = %.2f mmHg" % b2,
                "  R^2       = %.4f" % r22,
            ]
        rep += ["", "每点误差表 (est 固件读数 vs 面板 Measured 参考):",
                "  点 | 参考mmHg | est mmHg | 误差 | sensor mV | ads mV"]
        for r in fit_recs:
            e = r["est"] - float(r["panel"])
            rep.append("  %2d | %8.1f | %7.2f | %+6.2f | %9.1f | %9.1f"
                       % (r["point"], float(r["panel"]), r["est"], e,
                          r["sensor_v"] * 1000, r["ads_v"] * 1000))
    else:
        print("含面板参考的点 <2，无法拟合。可在 CSV 里补面板值后重跑（保留同一 CSV）。")
        rep.append("含面板参考的点不足 2 个，未拟合。请补面板值后重新分析。")

    rep_path = os.path.join(OUT_DIR, "calibration_%s_report.txt" % ts)
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write("\n".join(rep) + "\n")
    print("\nCSV  : %s" % csv_path)
    print("报告 : %s" % rep_path)

    if not args.no_cmd:
        ser.write(b"stream stop\r\n")
        print("已发送: stream stop")
    ser.close()


if __name__ == "__main__":
    main()
