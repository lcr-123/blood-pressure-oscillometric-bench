#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BP 静态校准 · 后台连续记录器
============================
持续读取 USART3/CH340 的 [Pressure] 流，带时间戳写入 TSV，并自动检测
"压力平台"（est 连续稳定段），供 AI 按点切窗计算均值。

用法：
  python bp_serial_logger.py                # 自动找 CH340 并发送 stream start
  python bp_serial_logger.py --port COM5    # 指定串口
  python bp_serial_logger.py --no-cmd       # 不发送 stream start（手动开流）

输出：
  calibration_data/raw_log_<时间戳>.tsv     # 全量原始数据: ts raw ads sensor est
  stdout 实时打印 [LIVE] 与 [PLATEAU] 平台事件
"""

import argparse
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

# 平台判定：最近 WINDOW_N 条 est 的极差 < RANGE 且条数足够 → 平台
WINDOW_N = 80        # 4 秒 @20Hz
RANGE_MMHG = 0.8     # 极差阈值
MIN_N = 60           # 平台最少条数
PLATEAU_MIN_GAP = 3.0  # 与上一平台均值差 > 该值才算新平台


def find_port(preferred=None):
    if preferred:
        return preferred
    for p in list_ports.comports():
        d = (p.description or "").upper()
        h = (p.hwid or "").upper()
        if "CH340" in d or "USB-SERIAL" in d or "1A86" in h:
            return p.device
    ports = [p.device for p in list_ports.comports()]
    if ports:
        raise SystemExit("未找到 CH340 串口。可用串口: %s\n请用 --port 指定。" % ", ".join(ports))
    raise SystemExit("未找到任何串口，请检查 USB 连接。")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="BP 静态校准后台记录器")
    ap.add_argument("--port", default=None)
    ap.add_argument("--no-cmd", action="store_true")
    args = ap.parse_args()

    port = find_port(args.port)
    print("== 串口: %s @ %d ==" % (port, BAUD), flush=True)

    ser = serial.Serial(port, BAUD, timeout=1.0)
    time.sleep(0.3)
    ser.reset_input_buffer()

    if not args.no_cmd:
        ser.write(b"stream start\r\n")
        print("已发送: stream start", flush=True)
        time.sleep(0.5)
        ser.reset_input_buffer()

    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(OUT_DIR, "raw_log_%s.tsv" % ts)
    f = open(log_path, "w", encoding="utf-8", newline="")
    f.write("ts\traw\tads_mv\tsensor_mv\test\n")
    print("日志: %s" % log_path, flush=True)
    print("等待 [Pressure] 流...", flush=True)

    buf = []          # (ts, est, raw, ads, sensor)
    last_plateau = None
    last_live = 0.0

    try:
        while True:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue
            m = RE_PRESSURE.search(line)
            if not m:
                continue
            now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            raw = int(m.group(1))
            ads = int(m.group(2))
            sensor = int(m.group(3))
            est = int(m.group(4)) + int(m.group(5)) * 0.1
            f.write("%s\t%d\t%d\t%d\t%.1f\n" % (now, raw, ads, sensor, est))
            f.flush()
            buf.append((now, est, raw, ads, sensor))
            if len(buf) > WINDOW_N:
                buf.pop(0)

            # 平台检测
            if len(buf) >= MIN_N:
                ests = [b[1] for b in buf]
                rng = max(ests) - min(ests)
                if rng <= RANGE_MMHG:
                    mean = statistics.mean(ests)
                    if (last_plateau is None
                            or abs(mean - last_plateau["mean"]) > PLATEAU_MIN_GAP):
                        sd = statistics.stdev(ests)
                        last_plateau = {
                            "mean": mean, "sd": sd, "n": len(ests),
                            "t_from": buf[0][0], "t_to": buf[-1][0],
                        }
                        print("[PLATEAU] est=%.2f +/-%.2f n=%d t=%s~%s"
                              % (mean, sd, len(ests), buf[0][0], buf[-1][0]),
                              flush=True)

            # 实时显示（2 秒一次）
            if time.time() - last_live >= 2.0:
                last_live = time.time()
                print("[LIVE] t=%s est=%.1f raw=%d ads=%dmV sensor=%dmV"
                      % (buf[-1][0], est, raw, ads, sensor), flush=True)
    except KeyboardInterrupt:
        print("\n记录停止。日志: %s" % log_path, flush=True)
    finally:
        f.close()
        ser.close()


if __name__ == "__main__":
    main()
