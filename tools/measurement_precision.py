"""How precise is one capture? Reproduce the numbers in
`data/reports/measurement_precision_20261112.md`.

Three questions, three sections:

1. `halves`   -- split one capture's own beats into two independent halves and ask how far
                 apart the two SBP estimates are. If the halves disagree as much as whole
                 captures do, then one capture is already a noisy measurement.
2. `groups`   -- define one measurement as the median of k consecutive captures at the same
                 panel setting (blocks never cross a session, no resampling) and ask how the
                 spread shrinks with k.
3. `budget`   -- how many captures would be needed before the 95% upper bound on sd clears 8.

Everything here is read-only: exports in, numbers out. No frozen constant is touched, and
`tools/reference_bp.py` is imported, never modified (its sha256 is pinned by the v1/v2/v3
freeze records).

The export's `t` column is all zeros, so the sample rate has to come from the protocol:
`BP_CAPTURE_INTERVAL_MS` is 25 ms, i.e. 40 Hz. Do not try to measure it from the file.
"""

from __future__ import annotations

import argparse
import json
import statistics
import struct
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks, medfilt
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dataset_tiers  # noqa: E402
import reference_bp  # noqa: E402
import validity_v2  # noqa: E402

FS = 40.0
LAYERS = ("frozen_baseline_v2", "prospective_v1", "prospective_v2", "v3_acceptance")
QUANTITIES = (("sbp", "SBP"), ("dbp", "DBP"), ("map", "MAP"))


def upper_bound(sd: float, n: int) -> float:
    """One-sided 95% upper confidence bound on the population sd."""
    if n < 2:
        return float("inf")
    return sd * ((n - 1) / chi2.ppf(0.05, n - 1)) ** 0.5


def scored_captures() -> list[dict]:
    """Every gate-passing capture in the four protocol layers, with its frozen errors."""
    rows = []
    for meta in dataset_tiers.collect():
        if meta["tier"] not in LAYERS:
            continue
        path = ROOT / meta["export"]
        if not path.is_file() or not validity_v2.check(str(path))["usable"]:
            continue
        result = reference_bp.estimate(reference_bp.load(path))
        ok = result["status"] == "ok"
        rows.append({
            "run": meta["run_id"],
            "preset": meta["preset"],
            "stamp": str(meta.get("captured_at") or ""),
            "panel_sbp": meta["panel_sbp_mmhg"],
            "status": result["status"],
            "export": path,
            "sbp": (result["sbp_mmhg"] - meta["panel_sbp_mmhg"]) if ok else None,
            "dbp": (result["dbp_mmhg"] - meta["panel_dbp_mmhg"]) if ok else None,
            "map": (None if result["status"].startswith("unresolved_map")
                    else result["map_mmhg"] - meta["panel_map_mmhg"]),
        })
    rows.sort(key=lambda r: (r["preset"], r["stamp"]))
    return rows


def load_oscillation(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Pressure and raw oscillation voltage from one export, in recording order."""
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    points = [record for record in records if record.get("type") == "point"]
    as_float = lambda bits: struct.unpack("<f", struct.pack("<I", int(bits)))[0]
    pressure = np.array([as_float(point["p"]) for point in points], dtype=float)
    voltage = np.array([as_float(point["v"]) for point in points], dtype=float)
    return pressure, voltage


def beat_amplitudes(pressure: np.ndarray, voltage: np.ndarray,
                    trough_window_s: float = 1.2) -> np.ndarray:
    """(pressure, peak-to-trough amplitude) for every pulse, as the per-beat classifier sees it.

    `trough_window_s` bounds how far back the trough may sit. A pulse is about 0.75 s, so the
    default 1.2 s keeps the trough inside the same beat. Pass `None` to take the previous
    trough however far back it is -- that is what the first ad-hoc split-half script did by
    accident (its sample-rate lookup was poisoned by the all-zero `t` column), and it is kept
    only so the two answers can be compared.
    """
    centred = voltage - medfilt(voltage, 61)
    span = float(centred.max() - centred.min())
    peaks, _ = find_peaks(centred, prominence=0.2 * span)
    troughs, _ = find_peaks(-centred, prominence=0.2 * span)
    window = None if trough_window_s is None else int(trough_window_s * FS)
    out = []
    for index in peaks:
        earlier = troughs[troughs < index]
        if window is not None:
            earlier = earlier[earlier >= index - window]
        if len(earlier) == 0:
            continue
        out.append((float(pressure[index]), float(centred[index] - centred[earlier[-1]])))
    return np.array(out) if out else np.zeros((0, 2))


def ratio_crossing(beats: np.ndarray, ratio: float = 0.5, minimum: int = 2) -> float | None:
    """Systolic-side pressure where the binned envelope falls below `ratio` of its peak.

    `minimum` is how many beats a 2 mmHg bin needs to contribute. The split-half numbers in
    the report use `minimum=1` (each half has half the beats, so demanding 2 would drop bins
    and move the crossing); the whole-capture numbers use the stricter `minimum=2`.
    """
    if len(beats) < 20:
        return None
    edges = np.arange(40.0, 280.0, 2.0)
    index = np.digitize(beats[:, 0], edges) - 1
    xs, ys = [], []
    for i in range(len(edges) - 1):
        values = beats[index == i][:, 1]
        if len(values) >= minimum:
            xs.append(float(edges[i] + 1.0))
            ys.append(float(np.median(values)))
    if len(ys) < 10:
        return None
    ys = np.array(ys)
    target = ratio * ys.max()
    for k in range(len(ys) - 1, 0, -1):
        if ys[k - 1] >= target and ys[k] < target:
            return xs[k]
    return None


def published_captures() -> list[dict]:
    """The 62-round published corpus, gate-passing and estimable -- the split-half population."""
    rows = []
    for meta in dataset_tiers.collect():
        if not meta.get("published_corpus"):
            continue
        path = ROOT / meta["export"]
        if not path.is_file() or not validity_v2.check(str(path))["usable"]:
            continue
        result = reference_bp.estimate(reference_bp.load(path))
        if result["status"] != "ok":
            continue
        rows.append({"run": meta["run_id"], "preset": meta["preset"],
                     "stamp": str(meta.get("captured_at") or ""),
                     "panel_sbp": meta["panel_sbp_mmhg"], "export": path})
    rows.sort(key=lambda r: (r["preset"], r["stamp"]))
    return rows


def section_halves(rows: list[dict], draws: int, keep: float, seed: int) -> dict:
    """Split-half and bootstrap noise inside a single capture.

    Two beat definitions are reported side by side, and the report must not depend on which
    one is picked:

    * `bounded`  -- a beat's trough must lie within 1.2 s of its peak (`trough_window_s=1.2`).
    * `unbounded` -- take the last trough before the peak regardless of distance. This is what
      the first ad-hoc split-half script did, because its 1.2 s window was computed from the
      export's all-zero `t` column and therefore came out as a million samples.

    Bin rule: `minimum=1` for the halves (each half has half the beats), `minimum=2` for the
    bootstrap column (a bin needs two beats to be trusted).
    """
    rng = np.random.default_rng(seed)
    per_round = []
    for row in rows:
        pressure, voltage = load_oscillation(row["export"])
        bounded = beat_amplitudes(pressure, voltage)
        unbounded = beat_amplitudes(pressure, voltage, trough_window_s=None)
        if len(bounded) < 16 or len(unbounded) < 16:
            continue
        record = {"run": row["run"], "preset": row["preset"], "beats": len(bounded)}
        usable = True
        for tag, beats in (("bounded", bounded), ("unbounded", unbounded)):
            halves = [ratio_crossing(beats[offset::2], minimum=1) for offset in (0, 1)]
            if any(h is None for h in halves):
                usable = False
                break
            record["half_gap_" + tag] = halves[0] - halves[1]
        if not usable:
            continue
        for tag, beats in (("bounded", bounded), ("unbounded", unbounded)):
            draws_out = []
            for _ in range(draws):
                pick = beats[rng.integers(0, len(beats), size=int(keep * len(beats)))]
                crossing = ratio_crossing(pick, minimum=2)
                if crossing is not None:
                    draws_out.append(crossing)
            if len(draws_out) < draws // 4:
                usable = False
                break
            record["bootstrap_sd_" + tag] = statistics.stdev(draws_out)
        if not usable:
            continue
        per_round.append(record)

    def summarise(selection: list[dict]) -> dict:
        out = {"n": len(selection),
               "beats_median": statistics.median([r["beats"] for r in selection]) if selection else None}
        for tag in ("bounded", "unbounded"):
            for field in ("half_gap", "bootstrap_sd"):
                key = field + "_" + tag
                values = [r[key] for r in selection if key in r]
                if not values:
                    out[key + "_sd" if field == "half_gap" else key + "_median"] = None
                    continue
                if field == "half_gap":
                    out["half_gap_" + tag + "_sd"] = statistics.stdev(values) if len(values) > 1 else None
                    out["half_gap_" + tag + "_median"] = statistics.median(values)
                    out["half_gap_" + tag + "_min"] = min(values)
                    out["half_gap_" + tag + "_max"] = max(values)
                else:
                    out["bootstrap_sd_" + tag + "_median"] = statistics.median(values)
        return out

    return {
        "all": summarise(per_round),
        "per_preset": {p: summarise([r for r in per_round if r["preset"] == p]) for p in (1, 2, 3, 4)},
    }


def section_envelope_halves(rows: list[dict]) -> dict:
    """The same split-half idea applied to the firmware's own smoothed envelope.

    The envelope is binned on the **systolic side only** (up to the panel SBP + 5 mmHg), which
    is the region the crossing can live in; binning across the whole deflation dilutes the
    peak and makes the halves look far more consistent than they are. Bin rule: three samples
    per 2 mmHg bin.
    """

    def crossing_of(pressure, smooth, ceiling, ratio=0.5):
        edges = np.arange(40.0, ceiling + 2.0, 2.0)
        index = np.digitize(pressure, edges) - 1
        xs, ys = [], []
        for i in range(len(edges) - 1):
            values = smooth[index == i]
            if len(values) >= 3:
                xs.append(float(edges[i] + 1.0))
                ys.append(float(np.median(values)))
        if len(ys) < 12:
            return None
        top = max(ys)
        for k in range(len(ys) - 1, 0, -1):
            if ys[k - 1] >= ratio * top and ys[k] < ratio * top:
                return xs[k]
        return None

    per_round = []
    for row in rows:
        capture = reference_bp.load(row["export"])
        pressure = np.asarray(capture["pressure"], dtype=float)
        smooth = np.asarray(capture["smooth"], dtype=float)
        ceiling = float(row["panel_sbp"]) + 5.0
        even = crossing_of(pressure[0::2], smooth[0::2], ceiling)
        odd = crossing_of(pressure[1::2], smooth[1::2], ceiling)
        if even is None or odd is None:
            continue
        per_round.append({"run": row["run"], "preset": row["preset"], "gap": even - odd})

    def summarise(selection: list[dict]) -> dict:
        gaps = [r["gap"] for r in selection]
        return {"n": len(selection),
                "sd": statistics.stdev(gaps) if len(gaps) > 1 else None,
                "median": statistics.median(gaps) if gaps else None,
                "min": min(gaps) if gaps else None,
                "max": max(gaps) if gaps else None}

    return {"all": summarise(per_round),
            "per_preset": {p: summarise([r for r in per_round if r["preset"] == p]) for p in (1, 2, 3, 4)}}


def section_groups(rows: list[dict], ks: tuple[int, ...]) -> dict:
    """Disjoint blocks of k consecutive captures in the same session; one measurement = median."""
    out = {}
    for k in ks:
        out[k] = {}
        for quantity, _ in QUANTITIES:
            blocks = defaultdict(list)
            for row in rows:
                if row[quantity] is not None:
                    blocks[(row["preset"], row["stamp"][:10])].append(row[quantity])
            medians, used = [], 0
            for key in sorted(blocks):
                values = blocks[key]
                for start in range(0, len(values) - k + 1, k):
                    chunk = values[start:start + k]
                    if len(chunk) == k:
                        medians.append(statistics.median(chunk))
                        used += k
            if len(medians) < 3:
                continue
            sd = statistics.stdev(medians)
            out[k][quantity] = {
                "groups": len(medians), "captures": used,
                "mean": statistics.fmean(medians), "sd": sd,
                "upper95": upper_bound(sd, len(medians)),
                "captures_needed_for_upper8": _groups_needed(sd) * k,
            }
    return out


def _groups_needed(sd: float, limit: float = 8.0, ceiling: int = 400) -> int:
    need = 3
    while need < ceiling and upper_bound(sd, need) > limit:
        need += 1
    return need


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draws", type=int, default=120, help="bootstrap draws per capture")
    parser.add_argument("--keep", type=float, default=0.8, help="fraction of beats per draw")
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--ks", default="1,2,3,4,5", help="block sizes for the grouping table")
    parser.add_argument("--json", help="write the whole result here")
    parser.add_argument("--skip-halves", action="store_true")
    args = parser.parse_args()

    rows = scored_captures()
    payload = {"captures": len(rows), "scored": {q: sum(1 for r in rows if r[q] is not None)
                                                 for q, _ in QUANTITIES}}

    print("scored captures: %d  (SBP %d, DBP %d, MAP %d)"
          % (len(rows), payload["scored"]["sbp"], payload["scored"]["dbp"], payload["scored"]["map"]))

    if not args.skip_halves:
        # The split-half test needs a capture whose frozen estimate stood, so it runs on the
        # published corpus the reports have always used (62 rounds, gate-passing, status ok).
        halves_rows = published_captures()
        payload["halves_population"] = len(halves_rows)
        payload["halves"] = section_halves(halves_rows, args.draws, args.keep, args.seed)
        # The ad-hoc envelope script used the four protocol layers rather than the published
        # corpus, so both populations are reported and the report must not depend on the pick.
        # The `_ok` variants keep only the captures whose frozen estimate actually stood.
        payload["envelope_halves"] = {
            "published_ok": section_envelope_halves(halves_rows),
            "layers_ok": section_envelope_halves([r for r in rows if r["status"] == "ok"]),
            "layers_all": section_envelope_halves(rows),
        }
        block = payload["halves"]["all"]
        print()
        print("1. inside ONE capture: split its own beats into two halves and compare crossings")
        print("   n=%d  beats median %.0f" % (block["n"], block["beats_median"]))
        print("   %-9s %10s %10s %12s %12s" % ("beats", "half sd", "half med", "boot sd", "range"))
        for tag in ("bounded", "unbounded"):
            print("   %-9s %10.2f %+10.2f %12.1f %12s"
                  % (tag, block["half_gap_" + tag + "_sd"], block["half_gap_" + tag + "_median"],
                     block["bootstrap_sd_" + tag + "_median"],
                     "%+.0f..%+.0f" % (block["half_gap_" + tag + "_min"],
                                       block["half_gap_" + tag + "_max"])))
        print("   %4s %5s %12s %12s %12s %12s"
              % ("pre", "n", "hd sd bnd", "hd sd unb", "boot bnd", "boot unb"))
        for preset, sub in payload["halves"]["per_preset"].items():
            if not sub["n"]:
                continue
            print("   %4d %5d %12.2f %12.2f %12.1f %12.1f"
                  % (preset, sub["n"], sub["half_gap_bounded_sd"], sub["half_gap_unbounded_sd"],
                     sub["bootstrap_sd_bounded_median"], sub["bootstrap_sd_unbounded_median"]))
        print()
        print("1b. same split applied to the FIRMWARE smoothed envelope (even vs odd samples)")
        for population in ("published_ok", "layers_ok", "layers_all"):
            block = payload["envelope_halves"][population]["all"]
            print("   %-10s n=%d  sd %.2f  median %+.2f  range %+.1f..%+.1f"
                  % (population, block["n"], block["sd"], block["median"],
                     block["min"], block["max"]))
            print("      %4s %5s %12s" % ("pre", "n", "halves sd"))
            for preset, sub in payload["envelope_halves"][population]["per_preset"].items():
                if not sub["n"]:
                    continue
                print("      %4d %5d %12.2f" % (preset, sub["n"], sub["sd"]))

    ks = tuple(int(part) for part in args.ks.split(",") if part.strip())
    payload["groups"] = section_groups(rows, ks)
    print()
    print("2. one measurement = median of k consecutive captures in the same session")
    print("   %2s %5s %7s %6s %9s %8s %10s %10s"
          % ("k", "qty", "groups", "cap", "mean", "sd", "95% upper", "verdict"))
    for k in ks:
        for quantity, label in QUANTITIES:
            entry = payload["groups"][k].get(quantity)
            if not entry:
                continue
            verdict = "PASS" if abs(entry["mean"]) <= 5.0 and entry["upper95"] <= 8.0 else "fail"
            print("   %2d %5s %7d %6d %+9.2f %8.2f %10.2f %10s"
                  % (k, label, entry["groups"], entry["captures"], entry["mean"],
                     entry["sd"], entry["upper95"], verdict))
        print()

    print("3. captures needed so that the 95% upper bound on sd clears 8")
    print("   planning uses the conservative sd (theory for a median of k: 1.2533*sigma/sqrt(k))")
    print("   %-3s %8s %8s %8s %8s %9s" % ("qty", "sigma1", "k=4 theory", "groups", "captures", "empirical"))
    for quantity, label in QUANTITIES:
        base = payload["groups"][1].get(quantity)
        best = payload["groups"][min(4, max(ks))].get(quantity)
        if base is None or best is None:
            continue
        # 1.2533 is the asymptotic sd of the sample median in units of sigma.
        theory = 1.2533 * base["sd"] / (4 ** 0.5)
        groups = _groups_needed(theory)
        empirical = _groups_needed(best["sd"]) * 4 if best["sd"] < 8 else None
        print("   %-3s %8.2f %8.2f %8d %8d %9s"
              % (label, base["sd"], theory, groups, groups * 4,
                 "%d" % empirical if empirical else "n/a"))

    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("\nwritten: %s" % args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
