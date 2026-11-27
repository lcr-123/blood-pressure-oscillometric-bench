#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BP 静态校准 · 桥联后台记录器（EK-OmniProbe TCP/NDJSON）
========================================================
通过 EK-OmniProbe 本机桥（默认端口 8765）持续读取 [Pressure] 流，
带时间戳写入 TSV，自动检测"压力平台"供按点切窗，实时打印 LIVE/PLATEAU。

要求：用户在 EK-OmniProbe 串口工作台已连接设备、已开 AI 桥联。

用法：
  python bp_bridge_logger.py                 # 默认 localhost:8765
  python bp_bridge_logger.py --port 8765
输出：
  calibration_data/raw_log_<时间戳>.tsv
"""

import argparse
import json
import os
import re
import socket
import statistics
import sys
import time
import datetime

RE_PRESSURE = re.compile(
    r"\[Pressure\] raw=(\d+) ads=(-?\d+)mV sensor=(-?\d+)mV est=(-?\d+)\.(\d)mmHg\s+(\w+)"
)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_data")

WINDOW_N = 80        # 4 秒 @20Hz
RANGE_MMHG = 0.8     # 平台极差阈值
MIN_N = 60           # 平台最少条数
PLATEAU_MIN_GAP = 3.0  # 新平台判定：与上一平台均值差


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="BP 静态校准桥联记录器")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    print("== 连接桥联 %s:%d ==" % (args.host, args.port), flush=True)
    sock = socket.create_connection((args.host, args.port), timeout=10)
    sock.settimeout(None)
    print("已连接，等待 telemetry...", flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(OUT_DIR, "raw_log_%s.tsv" % ts)
    f = open(log_path, "w", encoding="utf-8", newline="")
    f.write("ts\traw\tads_mv\tsensor_mv\test\n")
    print("日志: %s" % log_path, flush=True)

    buf = []
    last_plateau = None
    last_live = 0.0
    fobj = sock.makefile("r", encoding="utf-8", errors="replace")

    try:
        for line in fobj:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            lines = msg.get("lines") if isinstance(msg, dict) else None
            if not lines:
                continue
            for item in lines:
                if not isinstance(item, dict):
                    continue
                if item.get("direction") != "rx":
                    continue
                text = item.get("text") or ""
                m = RE_PRESSURE.search(text)
                if not m:
                    continue
                # 时间戳：优先宿主时间戳（ms）→ 本地时间
                t_ms = item.get("timestamp")
                if t_ms:
                    now = datetime.datetime.fromtimestamp(t_ms / 1000.0).strftime("%H:%M:%S.%f")[:-3]
                else:
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

                if time.time() - last_live >= 2.0:
                    last_live = time.time()
                    print("[LIVE] t=%s est=%.1f raw=%d ads=%dmV sensor=%dmV"
                          % (buf[-1][0], est, raw, ads, sensor), flush=True)
    except KeyboardInterrupt:
        print("\n记录停止。日志: %s" % log_path, flush=True)
    finally:
        f.close()
        sock.close()


if __name__ == "__main__":
    main()
