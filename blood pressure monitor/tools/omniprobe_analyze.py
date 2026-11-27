#!/usr/bin/env python3
"""Parse EK-OmniProbe NDJSON captures of the BP firmware pressure stream."""
import json
import re
import statistics
import sys
from pathlib import Path

LINE_RE = re.compile(
    r"\[Pressure\] raw=(\d+) ads=(\d+)mV sensor=(\d+)mV est=([\d.]+)mmHg (VALID|UNCAL)"
)


def parse_ndjson(path):
    samples = []
    text_lines = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "text":
                for l in msg.get("lines", []):
                    text_lines += 1
                    m = LINE_RE.search(l.get("text", ""))
                    if m:
                        samples.append(
                            {
                                "ts_ms": l.get("timestamp"),
                                "raw": int(m.group(1)),
                                "ads_mv": int(m.group(2)),
                                "sensor_mv": int(m.group(3)),
                                "est_mmhg": float(m.group(4)),
                                "cal": m.group(5),
                            }
                        )
    return samples, text_lines


def summarize(samples):
    if not samples:
        return {}
    def stats(key):
        vals = [s[key] for s in samples]
        return {
            "count": len(vals),
            "min": min(vals),
            "max": max(vals),
            "mean": statistics.fmean(vals),
            "stddev": statistics.pstdev(vals),
            "last": vals[-1],
        }
    summary = {k: stats(k) for k in ("raw", "ads_mv", "sensor_mv", "est_mmhg")}
    summary["first_ts_ms"] = samples[0]["ts_ms"]
    summary["last_ts_ms"] = samples[-1]["ts_ms"]
    return summary


if __name__ == "__main__":
    path = sys.argv[1]
    samples, text_lines = parse_ndjson(path)
    print(f"file: {Path(path).name}")
    print(f"text lines: {text_lines}, parsed pressure samples: {len(samples)}")
    if not samples:
        sys.exit(2)
    s = summarize(samples)
    span_ms = s["last_ts_ms"] - s["first_ts_ms"]
    rate = 1000.0 * (len(samples) - 1) / span_ms if span_ms > 0 else 0.0
    print(f"duration: {span_ms} ms, effective rate: {rate:.1f} Hz")
    for k in ("raw", "ads_mv", "sensor_mv", "est_mmhg"):
        st = s[k]
        print(
            f"{k}: min={st['min']} max={st['max']} mean={st['mean']:.3f} "
            f"stddev={st['stddev']:.3f} last={st['last']}"
        )
    cals = {x["cal"] for x in samples}
    print(f"calibration flags seen: {sorted(cals)}")
