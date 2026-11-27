#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校准数据分析：从桥联记录日志按"面板参考值"切窗口算均值
用法：
  python analyze_calibration.py <raw_log.tsv> --panel 53 50 100 150
说明：
  对每个面板值 X，取日志中 est∈[X-0.75, X+0.75] 的样本，输出均值/SD 与时间范围。
  原理：面板 Measured 与串口 est 测同一气路压力，用户报值时刻 ≈ est 等于该值时刻。
"""
import argparse
import statistics
import sys


def load(log_path):
    rows = []
    with open(log_path, encoding="utf-8") as f:
        header = f.readline()
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 5 and p[4] != "est":
                try:
                    rows.append((p[0], int(p[1]), int(p[2]), int(p[3]), float(p[4])))
                except ValueError:
                    continue
    return rows


def window(rows, lo, hi):
    sel = [r for r in rows if lo <= r[4] <= hi]
    if not sel:
        return None
    est = [r[4] for r in sel]
    raw = [r[1] for r in sel]
    ads = [r[2] for r in sel]
    sen = [r[3] for r in sel]
    return {
        "n": len(sel),
        "t_from": sel[0][0], "t_to": sel[-1][0],
        "est": statistics.mean(est),
        "est_sd": statistics.stdev(est) if len(est) > 1 else 0.0,
        "raw": statistics.mean(raw),
        "raw_sd": statistics.stdev(raw) if len(raw) > 1 else 0.0,
        "ads": statistics.mean(ads),
        "ads_sd": statistics.stdev(ads) if len(ads) > 1 else 0.0,
        "sensor": statistics.mean(sen),
        "sensor_sd": statistics.stdev(sen) if len(sen) > 1 else 0.0,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("log", help="raw_log.tsv 路径")
    ap.add_argument("--panel", nargs="+", type=float, required=True,
                    help="面板 Measured 参考值列表，按采集顺序")
    ap.add_argument("--span", type=float, default=0.75, help="窗口半宽 mmHg")
    args = ap.parse_args()

    rows = load(args.log)
    print("== 日志: %s  总样本: %d ==" % (args.log, len(rows)))
    results = []
    for i, x in enumerate(args.panel, 1):
        w = window(rows, x - args.span, x + args.span)
        if w is None:
            print("点%d 面板=%.1f : 无匹配样本 (est %.1f~%.1f)"
                  % (i, x, x - args.span, x + args.span))
            continue
        results.append((i, x, w))
        print("点%d 面板=%.1f : n=%d t=%s~%s" % (i, x, w["n"], w["t_from"], w["t_to"]))
        print("   est=%.2f +-%.2f | raw=%.1f +-%.1f | ads=%.1f +-%.1f | sensor=%.1f +-%.1f"
              % (w["est"], w["est_sd"], w["raw"], w["raw_sd"],
                 w["ads"], w["ads_sd"], w["sensor"], w["sensor_sd"]))
    print("== 汇总表 ==")
    print("点 | 面板参考 | est均值 | estSD | raw均值 | ads_mV | sensor_mV")
    for i, x, w in results:
        print("%2d | %6.1f | %6.2f | %5.2f | %6.0f | %6.1f | %6.1f"
              % (i, x, w["est"], w["est_sd"], w["raw"], w["ads"], w["sensor"]))


if __name__ == "__main__":
    main()
