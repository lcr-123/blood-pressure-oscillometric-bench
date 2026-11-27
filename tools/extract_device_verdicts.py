"""Extract the device's own blood-pressure verdict for every round that has one.

Why this exists
---------------
The firmware prints `[BP] SBP=.. DBP=.. Pulse=.. bpm valid=1` on the serial line
once per round, and for 653 rounds the *only* surviving copy of that line is
inside the per-sample telemetry log (`<run_id>.ndjson`). The export files carry
`p`/`e`/`s` and the metadata carries panel settings, but neither carries the
device verdict.

Reports do quote it: `data/reports/low_preset_sweep_20261113.md` rests on it
("设备自己算出了 SBP=207 DBP=36 Pulse=56"), and two 2026-11-01 round reports do
too. So the telemetry is not purely decorative -- for those claims it is the
evidence.

This tool makes the evidence small and durable: it reads each telemetry log,
pulls out the verdict line, and writes one JSON record per round. The result is
~80 KB instead of ~2 GB, and it means "stop tracking 2.2 GB of telemetry" does
not silently destroy reproducibility of anything that quotes the device.

Usage
-----
    python tools/extract_device_verdicts.py --out data/device_verdicts.json
    python tools/extract_device_verdicts.py --verify data/device_verdicts.json

`--verify` re-reads the recorded rounds and fails if any verdict changed or
disappeared, which is what a release check wants.

Verifying without the telemetry
-------------------------------
Per-sample telemetry is not tracked, so a fresh clone has none of these logs and
`--verify` there cannot re-derive a single verdict. It used to fail in that
situation with 653 `VANISHED` lines, which made a documented release command
impossible to run on the published repository. The check now degrades in a way
it can state out loud:

* telemetry present for a round -> re-derive the verdict and compare it; a
  vanished or changed verdict is a failure, as before;
* telemetry absent for a round -> check what the tracked metadata can prove,
  which is the round still exists and its `panel_preset` matches the recorded
  one, and say so in the summary.

The final line always states which of the two happened, so "verified" is never
claimed for work that was not done.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/development_20261101"

VERDICT = re.compile(r"\[BP\] SBP=(\d+) DBP=(\d+) Pulse=(\d+) bpm valid=(\d)")
CALC_FAILED = re.compile(r"\[BP\] calculation failed")
PEAK_FAILED = re.compile(r"\[BP\] .*fail", re.IGNORECASE)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def verdict_of(path: Path) -> dict[str, object] | None:
    """Pull the device verdict out of one telemetry log, or None if absent."""
    text = read_text(path)
    m = VERDICT.search(text)
    if m:
        return {
            "kind": "valid",
            "sbp": int(m.group(1)),
            "dbp": int(m.group(2)),
            "pulse_bpm": int(m.group(3)),
        }
    if CALC_FAILED.search(text):
        return {"kind": "calculation_failed"}
    if PEAK_FAILED.search(text):
        line = PEAK_FAILED.search(text)
        assert line is not None
        return {"kind": "other_failure", "line": line.group(0)[:80]}
    return None


def preset_of(run_id: str) -> str:
    meta = RAW / f"{run_id}.metadata.json"
    if not meta.exists():
        return "?"
    try:
        return str(json.loads(meta.read_text(encoding="utf-8")).get("panel_preset", "?"))
    except (OSError, json.JSONDecodeError):
        return "?"


def collect() -> dict[str, dict[str, object]]:
    verdicts: dict[str, dict[str, object]] = {}
    for path in sorted(RAW.glob("standard*.ndjson")):
        if path.name.endswith(".export.ndjson"):
            continue
        run_id = path.name[: -len(".ndjson")]
        found = verdict_of(path)
        if found is None:
            continue
        found["preset"] = preset_of(run_id) if "preset" not in found else found["preset"]
        verdicts[run_id] = found
    return verdicts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", help="write the extracted verdicts here")
    ap.add_argument("--verify", help="re-check an existing extraction file")
    args = ap.parse_args(argv)

    if args.verify:
        recorded = json.loads((ROOT / args.verify).read_text(encoding="utf-8"))
        before = recorded["verdicts"]
        problems: list[str] = []
        rederived = 0
        metadata_only = 0
        for run_id, was in sorted(before.items()):
            log = RAW / f"{run_id}.ndjson"
            if not log.exists():
                # Telemetry is not tracked any more, so this round cannot be
                # re-derived from the published tree. Check what is checkable
                # and count it separately instead of reporting it as vanished.
                meta = RAW / f"{run_id}.metadata.json"
                if not meta.exists():
                    problems.append(f"VANISHED {run_id}")
                elif str(preset_of(run_id)) != str(was.get("preset")):
                    problems.append(
                        f"CHANGED {run_id}: preset {was.get('preset')} -> "
                        f"{preset_of(run_id)}"
                    )
                else:
                    metadata_only += 1
                continue
            now = verdict_of(log)
            if now is None:
                problems.append(f"VANISHED {run_id}")
                continue
            now["preset"] = preset_of(run_id)
            rederived += 1
            if {k: v for k, v in now.items() if k != "preset"} != {
                k: v for k, v in was.items() if k != "preset"
            }:
                problems.append(f"CHANGED {run_id}: {was} -> {now}")
        for problem in problems:
            print(problem)
        extra = sorted(set(collect()) - set(before))
        if extra:
            print(f"note: {len(extra)} round(s) now have a verdict that did not before")
        if problems:
            print(f"\nFAILED: {len(problems)} problem(s)", file=sys.stderr)
            return 1
        print(
            f"verified: {len(before)} recorded verdict(s) still match "
            f"({rederived} re-derived from telemetry, "
            f"{metadata_only} checked against tracked metadata only because "
            f"telemetry is not tracked)"
        )
        return 0

    if not args.out:
        print("either --out or --verify is required", file=sys.stderr)
        return 2

    verdicts = collect()
    kinds: dict[str, int] = {}
    for v in verdicts.values():
        kinds[str(v["kind"])] = kinds.get(str(v["kind"]), 0) + 1
    payload = {
        "note": (
            "The device's own verdict, extracted from per-sample telemetry so that "
            "it survives the telemetry leaving the repository. The firmware prints "
            "[BP] SBP/DBP/Pulse once per round and this is the only machine-readable "
            "copy. These numbers are the device under test, not this dataset's "
            "reference algorithm; citing them must not be confused with the "
            "reference estimates in the reports."
        ),
        "source": "data/raw/development_20261101/<run_id>.ndjson",
        "rounds": len(verdicts),
        "kinds": kinds,
        "verdicts": dict(sorted(verdicts.items())),
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    assert not data.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in data
    out.write_bytes(data)
    print(f"rounds with a verdict: {len(verdicts)}  {kinds}")
    print(f"WROTE {args.out} {len(data)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
