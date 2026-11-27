"""Validate bp.capture/1..4 export and replay production C, offline only.

Example: python tools/bp_capture.py capture.ndjson --csv capture.csv --report replay.json
Accepts direct serial text or EK-OmniProbe text RX envelopes. No serial/TCP writes.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile

from host_build import PROJECT, build_replay

SCHEMAS = {"bp.capture/1", "bp.capture/2", "bp.capture/3", "bp.capture/4"}
CURRENT_SCHEMA = "bp.capture/4"
VALVE_SCHEMAS = SCHEMAS - {"bp.capture/1"}
STEP_SCHEMAS = {"bp.capture/3", "bp.capture/4"}
STEP_TRACE_MAX = 12
FEATURES = {"map_i", "map_p", "sbp_found", "sbp_p", "dbp_found", "dbp_p"}
VALVE_FIELDS = {"pulses", "period_min", "period_max", "on_min", "on_max",
                "threshold", "steps", "phase", "rise_found", "rise_i",
                "rise_d", "rise_phase", "rise_on", "fall_found", "fall_i",
                "fall_d", "fall_phase", "fall_on"}


def uint(value, name, maximum=0xFFFFFFFF):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f"{name}: expected uint <= {maximum}")
    return value


def float32(bits):
    value = struct.unpack("<f", struct.pack("<I", uint(bits, "float bits")))[0]
    if not math.isfinite(value):
        raise ValueError("nonfinite float32")
    return value


def fnv(data, previous=2166136261):
    for byte in data:
        previous = ((previous ^ byte) * 16777619) & 0xFFFFFFFF
    return previous


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(text):
    return json.loads(text, object_pairs_hook=unique_object)


def capture_lines(lines):
    """Keep exact MCU record bytes; ignore telemetry projections and TX echoes."""
    for line in lines:
        text = line.rstrip("\r\n")
        try:
            obj = load_json(text)
        except (ValueError, TypeError):
            if any(schema in text for schema in SCHEMAS):
                raise ValueError("malformed capture JSON")
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("schema") in SCHEMAS:
            yield text, obj
        elif obj.get("type") == "text":
            for entry in obj.get("lines", []):
                if entry.get("direction") != "rx":
                    continue
                raw = entry.get("text", "").rstrip("\r\n")
                if not any(schema in raw for schema in SCHEMAS):
                    continue
                if entry.get("truncated", False):
                    raise ValueError("truncated bridge capture line")
                item = load_json(raw)
                if not isinstance(item, dict) or item.get("schema") not in SCHEMAS:
                    raise ValueError("malformed bridge capture line")
                yield raw, item


def keys(record, expected):
    if set(record) != {"schema", "type"} | expected:
        raise ValueError(f"unexpected {record.get('type')} fields")


def decode(lines):
    header = valve = timing = features = end = None
    points, steps, pulses, raw_lines = [], [], [], []
    checksum = 2166136261
    elapsed = 0
    for raw, record in capture_lines(lines):
        kind = record.get("type")
        if end is not None:
            raise ValueError("extra capture after end; provide exactly one transfer")
        if kind == "begin":
            if header is not None:
                raise ValueError("duplicate/restarted begin; previous capture incomplete")
            keys(record, {"firmware", "n", "dropped", "interval_ms", "raw_kind", "cal_valid", "slope", "intercept", "calc"})
            if not isinstance(record["firmware"], str) or not record["firmware"]:
                raise ValueError("missing firmware identity")
            if record["schema"] not in SCHEMAS:
                raise ValueError("unsupported capture schema")
            if not 1 <= uint(record["n"], "n", 4200):
                raise ValueError("empty capture")
            if uint(record["dropped"], "dropped") != 0:
                raise ValueError("overflow capture is incomplete")
            if uint(record["interval_ms"], "interval_ms") != 25:
                raise ValueError("unsupported nominal interval")
            if uint(record["raw_kind"], "raw_kind") not in (1, 2):
                raise ValueError("unknown voltage provenance")
            uint(record["cal_valid"], "cal_valid", 1)
            float32(record["slope"])
            float32(record["intercept"])
            if uint(record["calc"], "calc", 4) == 1:
                raise ValueError("export while calculating")
            header = record
        elif header is None:
            raise ValueError("missing begin")
        elif record.get("schema") != header["schema"]:
            raise ValueError("mixed capture schemas")
        elif kind == "point":
            keys(record, {"i", "t", "p", "v", "e", "s"})
            if valve is not None or features is not None or uint(record["i"], "i") != len(points) or len(points) >= header["n"]:
                raise ValueError("point missing, duplicate, out of order or excess")
            uint(record["t"], "tick")
            float32(record["p"])
            float32(record["v"])
            for field in ("e", "s"):
                if header["calc"] in (2, 3):
                    if float32(record[field]) < 0:
                        raise ValueError("negative envelope")
                elif record[field] is not None:
                    raise ValueError("partial calculation must not export stale envelopes")
            if points:
                delta = (record["t"] - points[-1]["t"]) & 0xFFFFFFFF
                if not 0 < delta < 0x80000000:
                    raise ValueError("nonforward MCU ticks")
                elapsed += delta
                if elapsed >= 0x80000000:
                    raise ValueError("ambiguous tick span")
            points.append(record)
        elif kind == "valve":
            if header["schema"] not in VALVE_SCHEMAS:
                raise ValueError("valve record is not valid in bp.capture/1")
            keys(record, VALVE_FIELDS | ({"trace_n"} if header["schema"] in STEP_SCHEMAS else set()))
            if valve is not None or features is not None or len(points) != header["n"]:
                raise ValueError("early/duplicate valve record")
            pulse_count = uint(record["pulses"], "pulse_count")
            period_min = uint(record["period_min"], "period_min")
            period_max = uint(record["period_max"], "period_max")
            on_min = uint(record["on_min"], "on_min", 255)
            on_max = uint(record["on_max"], "on_max", 255)
            step_count = uint(record["steps"], "steps", header["n"] - 1)
            if float32(record["threshold"]) != 5.0:
                raise ValueError("unsupported pressure-step threshold")
            phase = record["phase"]
            if not isinstance(phase, list) or len(phase) != 9:
                raise ValueError("phase: expected nine bins")
            phase = [uint(value, f"phase[{index}]", step_count)
                     for index, value in enumerate(phase)]
            if sum(phase) != step_count:
                raise ValueError("phase bins do not sum to pressure steps")
            if pulse_count == 0:
                if any((period_min, period_max, on_min, on_max, step_count)):
                    raise ValueError("zero-pulse diagnostics contain events")
            else:
                if not 1 <= on_min <= on_max:
                    raise ValueError("invalid valve on-time range")
                if pulse_count == 1 and (period_min != 0 or period_max != 0):
                    raise ValueError("single pulse must not claim a period")
                if pulse_count > 1 and not 1 <= period_min <= period_max < 0x80000000:
                    raise ValueError("invalid valve pulse period range")
            for prefix, sign in (("rise", 1), ("fall", -1)):
                found = uint(record[f"{prefix}_found"], f"{prefix}_found", 1)
                index = uint(record[f"{prefix}_i"], f"{prefix}_i", header["n"] - 1)
                delta = float32(record[f"{prefix}_d"])
                phase_ms = uint(record[f"{prefix}_phase"], f"{prefix}_phase")
                on_ms = uint(record[f"{prefix}_on"], f"{prefix}_on", 255)
                if found:
                    phase_bin = phase_ms // 25 if phase_ms < 200 else 8
                    if (index == 0 or pulse_count == 0 or not on_min <= on_ms <= on_max or
                            sign * delta < 5.0 or phase[phase_bin] == 0):
                        raise ValueError(f"invalid {prefix} pressure-step evidence")
                elif any((index, delta, phase_ms, on_ms)):
                    raise ValueError(f"absent {prefix} evidence must be zero")
            if record["rise_found"] + record["fall_found"] > step_count:
                raise ValueError("maximum-event flags exceed pressure steps")
            if header["schema"] in STEP_SCHEMAS:
                if uint(record["trace_n"], "trace_n", STEP_TRACE_MAX) != min(step_count, STEP_TRACE_MAX):
                    raise ValueError("incomplete step trace count")
            valve = record
        elif kind == "step":
            if header["schema"] not in STEP_SCHEMAS:
                raise ValueError("step trace requires bp.capture/3")
            keys(record, {"i", "phase", "on"})
            if valve is None or timing is not None or features is not None or len(steps) >= valve["trace_n"]:
                raise ValueError("early, excess or late step trace")
            index = uint(record["i"], "step i", header["n"] - 1)
            phase_ms = uint(record["phase"], "step phase", 255)
            on_ms = uint(record["on"], "step on", 255)
            if (index == 0 or (steps and index <= steps[-1]["i"]) or
                    abs(float32(points[index]["p"]) - float32(points[index - 1]["p"])) < 5.0 or
                    not valve["on_min"] <= on_ms <= valve["on_max"]):
                raise ValueError("invalid step trace evidence")
            phase_bin = phase_ms // 25 if phase_ms < 200 else 8
            if valve["phase"][phase_bin] == 0:
                raise ValueError("step trace phase absent from aggregate")
            steps.append(record)
        elif kind == "timing":
            keys(record, {"n", "errors", "complete"})
            if (header["schema"] != CURRENT_SCHEMA or valve is None or
                    timing is not None or features is not None or len(steps) != valve["trace_n"]):
                raise ValueError("early, duplicate or unsupported timing")
            count = uint(record["n"], "timing n", 600)
            errors = uint(record["errors"], "timing errors", 15)
            complete = uint(record["complete"], "timing complete", 1)
            if count > valve["pulses"] or complete != int(errors == 0 and count == valve["pulses"]):
                raise ValueError("inconsistent timing completeness")
            if not errors and not complete:
                raise ValueError("missing timing without an explicit error")
            timing = record
        elif kind == "pulse":
            keys(record, {"i", "open", "close"})
            if (header["schema"] != CURRENT_SCHEMA or timing is None or features is not None or
                    uint(record["i"], "pulse i") != len(pulses) or len(pulses) >= timing["n"]):
                raise ValueError("early, excess, duplicate or out-of-order pulse")
            opened = uint(record["open"], "pulse open")
            closed = uint(record["close"], "pulse close")
            width = (closed - opened) & 0xFFFFFFFF
            if width > 255:
                raise ValueError("unrepresentable actual pulse width")
            if pulses:
                period = (opened - pulses[-1]["open"]) & 0xFFFFFFFF
                previous_width = (pulses[-1]["close"] - pulses[-1]["open"]) & 0xFFFFFFFF
                if not 1 <= period <= 255 or previous_width > period:
                    raise ValueError("invalid pulse period or overlapping edges")
            # Pulses can begin before the first sample and end after the last.
            # Require the shared clock to place them within one bounded capture.
            relative = (opened - points[0]["t"]) & 0xFFFFFFFF
            if relative >= 0x80000000:
                relative -= 0x100000000
            if not -255 <= relative <= elapsed + 255:
                raise ValueError("pulse outside capture clock window")
            pulses.append(record)
        elif kind == "features":
            keys(record, FEATURES)
            if (features is not None or len(points) != header["n"] or
                    (header["schema"] in VALVE_SCHEMAS and valve is None) or
                    (header["schema"] in STEP_SCHEMAS and len(steps) != valve["trace_n"]) or
                    (header["schema"] == CURRENT_SCHEMA and
                     (timing is None or len(pulses) != timing["n"]))):
                raise ValueError("early/duplicate features")
            if header["schema"] == CURRENT_SCHEMA and timing["complete"] and len(pulses) > 1:
                periods = [((b["open"] - a["open"]) & 0xFFFFFFFF)
                           for a, b in zip(pulses, pulses[1:])]
                if min(periods) != valve["period_min"] or max(periods) != valve["period_max"]:
                    raise ValueError("pulse timing disagrees with period aggregate")
            uint(record["map_i"], "map_i", header["n"] - 1)
            for field in ("map_p", "sbp_p", "dbp_p"):
                float32(record[field])
            for field in ("sbp_found", "dbp_found"):
                uint(record[field], field, 1)
            features = record
        elif kind == "end":
            keys(record, {"n", "hash"})
            if (features is None or uint(record["n"], "end n") != len(points) or
                    (header["schema"] in VALVE_SCHEMAS and valve is None)):
                raise ValueError("incomplete point/feature count")
            if uint(record["hash"], "hash") != checksum:
                raise ValueError("capture checksum mismatch")
            end = record
        else:
            raise ValueError("unknown capture record")
        if kind != "end":
            checksum = fnv(raw.encode("utf-8"), checksum)
        raw_lines.append(raw)
    if end is None:
        raise ValueError("no complete capture end; never accept cancelled/truncated export")
    return {"header": header, "points": points, "valve": valve, "steps": steps,
            "timing": timing, "pulses": pulses,
            "features": features,
            "end": end, "raw_lines": raw_lines, "duration_ms": elapsed}


def replay(capture, exe):
    data = "".join(f"{row['p']} {row['v']} {row['t']}\n" for row in capture["points"])
    process = subprocess.run([str(exe)], input=data, capture_output=True,
                             text=True, timeout=30)
    if process.returncode:
        raise RuntimeError(f"C replay failed: {process.stderr}")
    rows = [load_json(line) for line in process.stdout.splitlines()]
    result, envelopes = rows[0], rows[1:]
    if result["firmware"] != capture["header"]["firmware"]:
        raise ValueError("firmware identity differs from local production C")
    if len(envelopes) != len(capture["points"]):
        raise ValueError("C replay point count differs")
    comparison = None
    if capture["header"]["calc"] in (2, 3):
        comparison = {"max_envelope_abs_error_v": 0.0, "max_smooth_abs_error_v": 0.0,
                      "envelope_bits_equal": True, "feature_bits_equal": True,
                      "validity_equal": bool(result["valid"]) == (capture["header"]["calc"] == 2)}
        for original, computed in zip(capture["points"], envelopes):
            if original["i"] != computed["i"]:
                raise ValueError("C replay point order differs")
            for field, metric in (("e", "max_envelope_abs_error_v"), ("s", "max_smooth_abs_error_v")):
                comparison[metric] = max(comparison[metric], abs(float32(original[field]) - float32(computed[field])))
                comparison["envelope_bits_equal"] &= original[field] == computed[field]
        comparison["feature_bits_equal"] = all(result[field] == capture["features"][field] for field in FEATURES)
    intervals = [((b["t"] - a["t"]) & 0xFFFFFFFF) for a, b in zip(capture["points"], capture["points"][1:])]
    sources = (PROJECT / "Core/Src/bp_algorithm.c", PROJECT / "Core/Inc/bp_algorithm.h",
               PROJECT / "Core/Src/bp_capture_export.c", PROJECT / "Core/Inc/bp_capture_export.h",
               PROJECT / "Core/Inc/bp_control.h", PROJECT / "tools/host/bp_replay.c")
    return {"source": "offline production C; host floating point, not target validation",
            "n": len(capture["points"]), "duration_ms": capture["duration_ms"],
            "interval_min_ms": min(intervals, default=None), "interval_max_ms": max(intervals, default=None),
            "capture_cal_valid": capture["header"]["cal_valid"],
            "raw_voltage_source": {1: "ADS pin V", 2: "reconstructed sensor V"}[capture["header"]["raw_kind"]],
            "valve": capture["valve"],
            "steps": capture["steps"],
            "timing": capture["timing"], "pulses": capture["pulses"],
            "source_sha256": {str(path.relative_to(PROJECT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
            "result": result, "comparison": comparison}


def write_csv(capture, output):
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["i", "mcu_tick_ms", "elapsed_ms", "pressure_mmhg", "algorithm_input_v", "envelope_v", "smooth_v", "p_bits", "v_bits", "e_bits", "s_bits"])
        elapsed = 0
        previous = None
        for row in capture["points"]:
            if previous is not None:
                elapsed += (row["t"] - previous) & 0xFFFFFFFF
            previous = row["t"]
            writer.writerow([row["i"], row["t"], elapsed, float32(row["p"]), float32(row["v"]),
                             float32(row["e"]) if row["e"] is not None else "",
                             float32(row["s"]) if row["s"] is not None else "",
                             row["p"], row["v"], row["e"], row["s"]])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--ndjson", type=Path, help="validated exact capture records only")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--decode-only", action="store_true")
    args = parser.parse_args()
    outputs = [path.resolve() for path in (args.csv, args.ndjson, args.report) if path]
    if len(set(outputs)) != len(outputs) or args.input.resolve() in outputs or any(path.exists() for path in outputs):
        parser.error("outputs must be distinct new files and must not overwrite input")
    with args.input.open(encoding="utf-8-sig") as stream:
        capture = decode(stream)
    report = {"n": len(capture["points"]), "duration_ms": capture["duration_ms"],
              "header": capture["header"], "valve": capture["valve"],
              "steps": capture["steps"], "timing": capture["timing"], "pulses": capture["pulses"]}
    if not args.decode_only:
        with tempfile.TemporaryDirectory(prefix="bp-replay-") as directory:
            report = replay(capture, build_replay(Path(directory)))
    if args.csv:
        write_csv(capture, args.csv)
    if args.ndjson:
        args.ndjson.write_text("\n".join(capture["raw_lines"]) + "\n", encoding="utf-8")
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
