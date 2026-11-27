"""Offline peak sensitivity localization; no BP inference or device I/O.

Reuse frozen shared features/gates. Beat deletion is a deterministic perturbation
of already extracted beats, not a correction, repeatability or error estimate.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import scipy

from bp_capture import decode
from bp_standard_envelope import (BIN, BIN_ORIGINS, assess_stability, bin_beats,
                                  extract, summarize_bins)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data/reports/standard_bp_envelope_stability_20261105.manifest.json"
DEFAULT_PREFIX = ROOT / "data/reports/standard_bp_peak_instability_20261105"


def variants(beats):
    """Expose every occupied bin, its members and shared smoothed values."""
    output = []
    for origin in BIN_ORIGINS:
        bins = bin_beats(beats, origin)
        for row in bins:
            row["beat_indices"] = [i for i, beat in enumerate(beats)
                                   if row["low_mmhg"] <= beat[0] < row["low_mmhg"] + BIN]
        summary = summarize_bins(bins)
        qualified = [row for row in bins if row["used_for_envelope"]]
        features = {}
        for name, envelope in summary["envelopes"].items():
            values = envelope.get("smoothed_values", [])
            order = sorted(range(len(values)), key=lambda i: (-values[i], i))
            top = []
            for index in order[:3]:
                # Edge padding can duplicate a bin; retain each actual weight.
                contributions = [{"weight": weight, **qualified[j]}
                                 for j, weight in ((max(0, index - 1), 0.25),
                                                   (index, 0.5),
                                                   (min(len(values) - 1, index + 1), 0.25))]
                top.append({"center_mmhg": qualified[index]["center_mmhg"],
                            "count": qualified[index]["count"],
                            "smoothed": values[index],
                            "relative_to_max": values[index] / values[order[0]]
                            if values[order[0]] > 0 else None,
                            "contributions": contributions})
            margin = (1 - top[1]["relative_to_max"] if len(top) >= 2 and
                      top[1]["relative_to_max"] is not None else None)
            features[name] = {"top_bins": top, "top_two_relative_margin": margin}
        output.append({"origin_mmhg": origin, "bins": bins,
                       "summary": summary, "features": features})
    return output


def deletion_sensitivity(beats, baseline_variants):
    """Keep all deletions, including gate failures; never choose a best subset."""
    trials = []
    for index, beat in enumerate(beats):
        reduced = beats[:index] + beats[index + 1:]
        stability = assess_stability(reduced)
        changed = []
        for original, perturbed in zip(baseline_variants, stability["variants"]):
            if (original["summary"].get("height_area_peaks_mmhg") !=
                    perturbed.get("height_area_peaks_mmhg")):
                changed.append(original["origin_mmhg"])
        trials.append({"removed_beat_index": index,
                       "removed_beat": list(beat), "changed_origins_mmhg": changed,
                       "status": stability["status"], "reason": stability["reason"],
                       "peak_range_mmhg": stability["peak_range_mmhg"],
                       "peak_span_mmhg": stability["peak_span_mmhg"],
                       "variants": [{"origin_mmhg": row["origin_mmhg"],
                                     "status": row["status"], "reason": row["reason"],
                                     "peaks_mmhg": row.get("height_area_peaks_mmhg")}
                                    for row in stability["variants"]]})
    return {"method": "delete one fixed extracted beat; no re-extraction; all origins retained",
            "meaning": "sensitivity only; not a confidence interval or BP error",
            "trial_count": len(trials),
            "peak_changed_trials": sum(bool(row["changed_origins_mmhg"]) for row in trials),
            "outcome_counts": dict(Counter(row["reason"] or "pass" for row in trials)),
            "trials": trials}


def valve_observability(capture):
    """Aggregate valve records cannot supply a complete event phase reference."""
    timing = capture.get('timing')
    if timing and timing['complete'] and capture.get('pulses'):
        return {"aggregate": capture.get('valve'),
                "threshold_step_trace_count": len(capture.get('steps', [])),
                "full_pulse_event_timestamps_available": True,
                "phase_alignment_possible": True,
                "physical_cause": "unresolved",
                "limitations": ["GPIO command timestamps are not mechanical valve motion or ADS conversion apertures.",
                                "No >=5mmHg steps does not exclude smaller valve artifacts.",
                                "No synchronized independent dynamic pressure reference."]}
    return {"aggregate": capture.get("valve"),
            "threshold_step_trace_count": len(capture.get("steps", [])),
            "full_pulse_event_timestamps_available": False,
            "phase_alignment_possible": False,
            "physical_cause": "unresolved",
            "limitations": ["No full valve pulse start times relative to samples.",
                            "tick modulo period is not measured valve phase.",
                            "No >=5mmHg steps does not exclude smaller valve artifacts.",
                            "No synchronized independent dynamic pressure reference."]}


def diagnose(capture):
    extraction = extract(capture)
    beats = extraction.pop("beats")
    result = {"extraction": extraction, "beats": [list(beat) for beat in beats],
              "bp_output_allowed": False, "valve": valve_observability(capture)}
    if extraction["status"] != "ready":
        return {**result, "status": "extraction_abstained",
                "reason": extraction["reason"], "variants": [], "deletions": None}
    all_variants = variants(beats)
    stability = assess_stability(beats)
    baseline = all_variants[0]["summary"]
    peak = baseline.get("candidate_peak_mmhg")
    # Descriptive neighbor dips only. Do not flag/reject/remove these beats.
    dips = []
    for i in range(1, len(beats) - 1):
        if peak is None or abs(beats[i][0] - peak) > 3 * BIN:
            continue
        neighbor_mean = (beats[i - 1][1] + beats[i + 1][1]) / 2
        if neighbor_mean > 0 and beats[i][1] < min(beats[i - 1][1], beats[i + 1][1]):
            dips.append({"beat_index": i, "pressure_mmhg": beats[i][0],
                         "height_v": beats[i][1], "neighbor_mean_height_v": neighbor_mean,
                         "height_to_neighbor_mean": beats[i][1] / neighbor_mean})
    return {**result, "status": "diagnosed", "reason": None,
            "stability": stability, "variants": all_variants,
            "local_height_dips_within_30mmhg_of_baseline_peak": dips,
            "deletions": deletion_sensitivity(beats, all_variants)}


def checked_bytes(path, expected_hash):
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_hash:
        raise ValueError(f"SHA256 mismatch: {path}")
    return content


def audit(manifest_path, root=ROOT):
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    rows = []
    for run in manifest["runs"]:
        evidence = {}
        contents = {}
        for kind in ("raw", "metadata", "verified"):
            if f"{kind}_path" in run:
                path = root / run[f"{kind}_path"]
                contents[kind] = checked_bytes(path, run[f"{kind}_sha256"])
                evidence[kind] = {"path": run[f"{kind}_path"],
                                  "sha256": run[f"{kind}_sha256"]}
        row = {"run_id": run["run_id"], "panel_setting_mmhg": run["panel_setting_mmhg"],
               "inflation_target_mmhg": run.get("inflation_target_mmhg"),
               "outcome": run["outcome"], "sources": evidence}
        if run["outcome"] != "export_received":
            row.update(status="capture_incomplete", reason=run.get("failure_reason"))
        else:
            row.update(diagnose(decode(contents["verified"].decode("utf-8-sig").splitlines())))
        rows.append(row)
    code_hashes = {}
    for name in (Path(__file__).name, "bp_standard_envelope.py", "bp_capture.py"):
        code_hashes[name] = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
    return {"schema": "bp.peak_instability/1",
            "scope": "offline development sensitivity; physical cause unresolved; no BP inference",
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "code_sha256": code_hashes,
            "environment": {"python": platform.python_version(), "numpy": np.__version__,
                            "scipy": scipy.__version__},
            "counts": dict(Counter(row["status"] for row in rows)), "runs": rows}


def markdown(report):
    lines = ["# 高压包络峰不稳定诊断（2026-11-05）", "",
             "已定位到的算法机制是：提取后的逐搏幅度起伏、少量搏动的分箱中位数与相邻箱平滑，"
             "会使接近并列的顶部箱交换最大值。物理成因仍未确定。", "",
             "所有分箱和删一搏结果均保留。删搏仅在已提取的搏动上进行，不重新滤波/检测，"
             "不作为修正、独立重复、置信区间或血压误差。没有改动提取或判定门限。", "",
             "## 全部尝试", "",
             "| 记录 | 面板设置 | 搏数 | 四起点峰位范围 mmHg | 删一搏改变峰位 | 删搏结果 |",
             "| --- | --- | ---: | --- | --- | --- |"]
    for run in report["runs"]:
        label = "/".join(map(str, run["panel_setting_mmhg"]))
        if run["status"] != "diagnosed":
            reason = run.get("reason") or run["status"]
            lines.append(f"| {run['run_id']} | {label} | — | {reason} | — | — |")
            continue
        span = run["stability"]["peak_range_mmhg"]
        deletion = run["deletions"]
        outcomes = "; ".join(f"{key}: {count}" for key, count in deletion["outcome_counts"].items())
        lines.append(f"| {run['run_id']} | {label} | {len(run['beats'])} | {span} | "
                     f"{deletion['peak_changed_trials']}/{deletion['trial_count']} | {outcomes} |")
    for run in report["runs"]:
        if run["status"] != "diagnosed" or run["panel_setting_mmhg"] != [255, 195]:
            continue
        lines += ["", f"## {run['run_id']}", "",
                  f"现行稳定性判定：`{run['stability']['reason']}`。", "",
                  "margin 为最大与第二大平滑箱幅度之差除以最大幅度；第二大箱可能与最大箱相邻。", "",
                  "| 分箱起点 | height 峰 mmHg / 搏数 / margin | area 峰 mmHg / 搏数 / margin |",
                  "| --- | --- | --- |"]
        for variant in run["variants"]:
            cells = []
            for feature in ("height", "area"):
                diagnostic = variant["features"][feature]
                top = diagnostic["top_bins"]
                margin = diagnostic["top_two_relative_margin"]
                margin_text = f"{100 * margin:.2f}%" if margin is not None else "不可用"
                cells.append(f"{top[0]['center_mmhg']:g} / {top[0]['count']} / {margin_text}"
                             if top else "无合格分箱")
            lines.append(f"| {variant['origin_mmhg']:g} | {' | '.join(cells)} |")
        lines += ["", "顶部 ±30 mmHg 范围内的逐搏局部凹陷（相对时间顺序两邻搏均值，描述性）：", ""]
        for dip in run["local_height_dips_within_30mmhg_of_baseline_peak"]:
            lines.append(f"- 搏 {dip['beat_index']}：{dip['pressure_mmhg']:.2f} mmHg，"
                         f"{1000 * dip['height_v']:.2f} mV，邻搏均值的"
                         f"{100 * dip['height_to_neighbor_mean']:.1f}%。")
    lines += ["", "## 因果边界与下一步", "",
              "本批完整记录中的阀数据仅有周期/开阀时间范围和大阶跃摘要，"
              "没有完整阀脉冲绝对时间戳及相对采样的起始相位。不能用 tick%200 冒充阀相位；"
              "没有 ≥5 mmHg 阶跃也不能排除更小的阀伪影。当前无法区分气路/阀动作、"
              "模拟器动态输出、传感器/电源或提取滤波造成的起伏。", "",
              "下一步应先设计同一压力区间的重复采集及同步阀事件记录：保持面板、袖带、"
              "校准和气路条件，比较峰位附近慢放气与短暂停阀窗口；停止充气后等待稳定，"
              "记录完整样本和每次开/关阀时间。按预先固定规则比较幅度凹陷是否随阀相位"
              "重复出现。若要声称压力波形准确，还需同步独立动态压力参考。"
              "具体时序与安全状态机需另行实现验证。本轮没有进行设备操作。", "",
              "## 复现与证据", "", "```powershell",
              'python "blood pressure monitor/tools/bp_peak_instability.py" '
              '--output-prefix data/reports/standard_bp_peak_instability_reproduction', "```", "",
              "工具拒绝覆盖既有输出；再次运行请指定尚不存在的前缀。", "",
              f"manifest SHA256：`{report['manifest_sha256']}`。",
              "同名前缀 JSON 保留全部输入哈希、代码哈希、环境、分箱成员及平滑贡献、"
              "每次删搏的所有起点和失败原因；PNG 对比两份高压采集。"
              "历史报告与原始文件保留。SBP/DBP 不输出，板上旧算法问题仍待修复。", ""]
    return "\n".join(lines)


def plot(report, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    selected = [run for run in report["runs"] if run["status"] == "diagnosed"][-2:]
    if not selected:
        raise ValueError("no diagnosed captures to plot")
    fig, axes = plt.subplots(len(selected), 2, figsize=(13, 4 * len(selected)), squeeze=False)
    for row_index, run in enumerate(selected):
        beats = np.array(run["beats"])
        for col, feature in enumerate(("height", "area")):
            ax = axes[row_index, col]
            ax.scatter(beats[:, 0], 1000 * beats[:, col + 1], color="black", s=18,
                       alpha=0.65, label="fixed extracted beats", zorder=3)
            for variant in run["variants"]:
                qualified = [row for row in variant["bins"] if row["used_for_envelope"]]
                envelope = variant["summary"]["envelopes"][feature]
                ax.plot([row["center_mmhg"] for row in qualified],
                        1000 * np.array(envelope.get("smoothed_values", [])), marker=".",
                        label=f"origin {variant['origin_mmhg']:g} mmHg")
            peaks = run["stability"]["peak_range_mmhg"]
            if peaks:
                ax.set_xlim(min(peaks) - 50, max(peaks) + 50)
            target = run.get("inflation_target_mmhg")
            ax.set_title(f"Target {target} / {feature}: {run['stability']['reason']}", fontsize=10)
            ax.set_xlabel("Cuff pressure (mmHg)")
            ax.set_ylabel("Height (mV)" if feature == "height" else "Area (mV s)")
            ax.grid(alpha=0.25)
            ax.legend(fontsize=8)
    fig.suptitle("Peak sensitivity: fixed 10 mmHg bins, unchanged extraction and gates", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-prefix", type=Path, default=DEFAULT_PREFIX)
    args = parser.parse_args()
    outputs = [args.output_prefix.with_suffix(suffix).resolve() for suffix in (".json", ".md", ".png")]
    reports = (ROOT / "data/reports").resolve()
    if any(reports not in path.parents or path == args.manifest.resolve() for path in outputs):
        parser.error("outputs must be under data/reports and must not replace manifest")
    # Never replace an older report or a manifest-referenced evidence file.
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    inputs = {(ROOT / value).resolve() for run in manifest["runs"]
              for key, value in run.items() if key.endswith("_path") and value}
    if any(path in inputs for path in outputs):
        parser.error("output collides with input evidence")
    if any(path.exists() for path in outputs):
        parser.error("output already exists; use a new --output-prefix")
    report = audit(args.manifest)
    outputs[0].write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                          encoding="utf-8")
    outputs[1].write_text(markdown(report), encoding="utf-8")
    plot(report, outputs[2])
    print(json.dumps({"outputs": [str(path) for path in outputs], "counts": report["counts"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
