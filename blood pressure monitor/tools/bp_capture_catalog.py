"""Read-only inventory of archived firmware captures; no serial or actuator I/O."""

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median

from bp_capture import decode, float32


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data/raw/firmware_capture_exports"
MISSING_METADATA = [
    "panel_mode", "panel_sbp_mmhg", "panel_dbp_mmhg", "panel_bpm",
    "panel_pulse_volume_profile_cc", "pneumatic_configuration", "firmware_hex_sha256",
    "pre_capture_zero", "post_capture_zero", "reference_pressure_evidence",
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def inspect(path, root):
    raw = path.read_bytes()
    row = {"path": path.relative_to(root).as_posix(), "file_sha256": sha256(raw)}
    try:
        capture = decode(raw.decode("utf-8-sig").splitlines())
    except (UnicodeError, ValueError, TypeError, AttributeError) as exc:
        row.update({"status": "decode_failed", "error": str(exc)})
        return row

    header = capture["header"]
    points = capture["points"]
    intervals = [((b["t"] - a["t"]) & 0xFFFFFFFF)
                 for a, b in zip(points, points[1:])]
    pressures = [float32(point["p"]) for point in points]
    # Hash the exact validated MCU records, not bridge envelopes or file names.
    records = "\n".join(capture["raw_lines"]).encode("utf-8") + b"\n"
    row.update({
        "status": "decode_valid",
        "capture_sha256": sha256(records),
        "schema": header["schema"],
        "firmware_marker": header["firmware"],
        "samples": len(points),
        "duration_ms": capture["duration_ms"],
        "estimated_rate_hz": round(1000 * (len(points) - 1) / capture["duration_ms"], 3)
        if capture["duration_ms"] else None,
        "interval_ms": {"min": min(intervals, default=None),
                        "median": median(intervals) if intervals else None,
                        "max": max(intervals, default=None),
                        "over_nominal_25ms": sum(value > 25 for value in intervals)},
        "pressure_mmhg": {"start": pressures[0], "end": pressures[-1],
                          "min": min(pressures), "max": max(pressures)},
        "raw_kind": header["raw_kind"],
        "cal_valid": bool(header["cal_valid"]),
        "calibration": {"slope_mmhg_per_v": float32(header["slope"]),
                        "intercept_mmhg": float32(header["intercept"])},
        "calc_state": header["calc"],
        "valve_pulses": capture["valve"]["pulses"] if capture["valve"] else None,
        "pressure_steps_ge_5mmhg": capture["valve"]["steps"] if capture["valve"] else None,
        "metadata": {key: None for key in MISSING_METADATA},
        "dataset_role": "historical_development",
        "release_ready": False,
        "replay_status": "not_run",
    })
    return row


def catalog(directory, root=ROOT):
    paths = sorted(directory.glob("*.ndjson"))
    if not paths:
        raise ValueError(f"no NDJSON files in {directory}")
    files = [inspect(path, root) for path in paths]
    first_by_capture = {}
    for row in files:
        if row["status"] != "decode_valid":
            continue
        first = first_by_capture.setdefault(row["capture_sha256"], row["path"])
        row["duplicate_of"] = first if first != row["path"] else None
    unique = [row for row in files if row["status"] == "decode_valid" and
              row["duplicate_of"] is None]
    return {
        "schema": "bp.dataset_catalog/1",
        "input_directory": directory.relative_to(root).as_posix(),
        "method": "strict bp_capture.decode; exact validated MCU record SHA-256; decode only",
        "summary": {"files": len(files), "decode_valid_files": sum(
            row["status"] == "decode_valid" for row in files),
            "decode_failed_files": sum(row["status"] == "decode_failed" for row in files),
            "unique_captures": len(unique),
            "duplicate_files": sum(row.get("duplicate_of") is not None for row in files),
            "release_ready_captures": 0},
        "files": files,
    }


def markdown(result):
    summary = result["summary"]
    failures = [row for row in result["files"] if row["status"] == "decode_failed"]
    unique = [row for row in result["files"] if row["status"] == "decode_valid" and
              row["duplicate_of"] is None]
    lines = [
        "# 历史固件波形导出审核", "",
        "本报告由 `bp_capture_catalog.py` 对原始目录只读生成。详细逐文件结果和 SHA-256 见同名 JSON。",
        "严格解码包含固件记录计数、顺序和 FNV 校验；相同 MCU 记录只算一轮。",
        "本次未运行生产 C 回放，也未核对 BP 面板设置或独立参考压力。",
        "", "## 结果", "",
        f"- 扫描文件：{summary['files']}；严格解码通过：{summary['decode_valid_files']}；失败：{summary['decode_failed_files']}。",
        f"- 独立记录序列：{summary['unique_captures']}；重复文件：{summary['duplicate_files']}。",
        "- 可直接发布的正式样本：0。历史文件属于方法开发集，不能充当独立验证集。",
        "- `calc_state` 是固件算法状态，不代表传输质量、面板真值或临床准确性。",
        "- 压力是本机传感器估计值，时间间隔来自 MCU tick；不能代替独立参考仪表。",
        f"- {len(unique)} 轮中的固件算法状态：有效 {sum(row['calc_state'] == 2 for row in unique)}、"
        f"无效 {sum(row['calc_state'] == 3 for row in unique)}、"
        f"未计算 {sum(row['calc_state'] == 0 for row in unique)}；"
        f"采集时长不足 20 秒 {sum(row['duration_ms'] < 20000 for row in unique)} 轮。",
        "", "## 独立记录概览", "",
        "| 文件 | 点数 | 时长 s | 压力范围 mmHg | 间隔最大 ms | >25ms 间隔 | calc |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in unique:
        pressure = row["pressure_mmhg"]
        intervals = row["interval_ms"]
        lines.append(f"| {row['path'].split('/')[-1]} | {row['samples']} | "
                     f"{row['duration_ms'] / 1000:.3f} | "
                     f"{pressure['min']:.1f}..{pressure['max']:.1f} | "
                     f"{intervals['max']} | {intervals['over_nominal_25ms']} | "
                     f"{row['calc_state']} |")
    lines += ["", "## 解码失败", ""]
    if failures:
        lines += ["| 文件 | 原因 |", "| --- | --- |"]
        lines += [f"| {row['path'].split('/')[-1]} | {row['error'].replace('|', '/')} |"
                  for row in failures]
    else:
        lines.append("无。")
    lines += ["", "## 下一批采集门槛", "",
              "1. 采集前记录 BP 模式、面板 SBP/DBP/BPM/各脉搏组容积、完整气路、固件 HEX 哈希和校准读回。",
              "2. 记录采集前后零点、参考压力证据、原始日志 SHA-256 和环境/故障事件。",
              "3. 严格解码通过后，再按预先冻结的质量规则审核；算法开发集与独立验证集分开。",
              "4. 本目录尚未补齐上述标签，不能从文件名或固件算法输出反推面板真值。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    root = ROOT
    directory = args.input.resolve()
    outputs = [args.json.resolve(), args.markdown.resolve()]
    if len(set(outputs)) != 2 or any(path.exists() for path in outputs):
        parser.error("outputs must be distinct new files")
    if not directory.is_dir() or not directory.is_relative_to(root):
        parser.error("input must be an existing directory inside the repository")
    if any(path.is_relative_to(directory) for path in outputs):
        parser.error("outputs must be outside the raw input directory")
    result = catalog(directory, root)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(result), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
