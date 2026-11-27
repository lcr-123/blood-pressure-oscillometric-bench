# Journal - linchuangrui (Part 1)

> AI development session journal
> Started: 2026-06-19

---



## Session 1: Adapt Trellis to STM32 blood pressure firmware

**Date**: 2026-06-19
**Task**: Adapt Trellis to STM32 blood pressure firmware
**Package**: firmware

### Summary

Added firmware-specific Trellis specs under .trellis/spec/firmware/core, created and started the bp-firmware-bringup task, configured firmware as the default package, and documented how future sessions should use the active task and specs before editing STM32 code.

### Main Changes

(Add details)

### Git Commits

(No commits - planning session)

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete

---

## Session 2: Complete capture export and production-C replay

**Date**: 2026-10-25
**Task**: `.trellis/tasks/06-19-bp-firmware-bringup` (in_progress)
**Package**: firmware

Added CAPTURE_EXPORT_20261025 read-only capture evidence API, bounded NDJSON
export, safe command gate and capture-time calibration/provenance. Added strict
offline validation/CSV and actual production-C replay. Numerical algorithm and
hardware settings unchanged. Keil source/header registration synchronized.
Recorded executable protocol contracts and non-human wiring/validation procedure
in capture-export.md and task capture_export_2026-10-25.md.

Verification:70/70 tests; fresh Keil V6.22 build0 errors/0 warnings; RAM63240/
65536B, headroom2296B; static stack budget passes. No flash/inflation/calibration/
wiring changes. New target export/stop/timing and runtime stack watermark pending.
19:40 failed waveform cannot be recovered from old20Hz logs; cause still unknown.
Three valid natural repeated BP rounds remain unmet.

No commit: repository has no HEAD and contains extensive pre-existing untracked
user work; no initial commit, cleanup or task archival performed. This journal
records software delivery only. Next: separately authorized non-human download,
complete new capture and feature investigation before tuning.

---

## Session 3: Validate capture export on target

**Date**: 2026-10-25
**Task**: `.trellis/tasks/06-19-bp-firmware-bringup` (in_progress)

Flashed and verified CAPTURE_EXPORT_20261025 after non-human safety confirmation.
Full erase cleared calibration; safe pins/ADS were checked before restoring only
82.326/-19.887 and reading it back VALID. A natural50mmHg no-pulse capture produced
n321/dropped0/8000ms. Complete export, checksum, production-C replay, stream-off
rejection, mid-export stop cancellation, vent-to-fresh-low/seal closeout and
identical re-export passed. Complete export took5596ms with54ms maximum pressure
delivery gap; observed stop response was23.2ms including host/bridge overhead.

This validates low-pressure transport/replay, not Standard BP validity or clinical
accuracy. Runtime stack watermark, a new Standard BP full waveform, feature-selection
analysis and three valid natural rounds remain open. Task stays in_progress.

User then confirmed non-human External Cuff+real cuff, Standard120/80mmHg,80BPM,
Running and authorized one round. CAPTURE_EXPORT image naturally captured2089 points,
dropped0/52200ms and reported93/90,56 valid1. Complete hash3282054663 export took
37163ms with697 pressure records/max60ms host gap; production-C replay was bit-equal.
MAP/SBP/DBP raw selection was97.0/103.2/95.3mmHg. Large pressure shocks were strongly
phase-associated with the200ms valve schedule (20 of42 >=4mmHg changes exactly on the
period boundary), but valve GPIO/on-time was not exported, so causation is not claimed.
The first FFT window's56.2BPM peak barely beat84.4BPM (0.3031 vs0.3022); later windows
mostly selected75/84.4. No algorithm tuning was changed. Runtime stack watermark,
direct valve correlation and three same-image valid repeatability rounds remain open.
## 2026-10-25 Valve correlation software increment

- Added compact actual-valve-pulse/pressure-step aggregates and `bp.capture/2`;
  kept `/1` decode compatibility and production replay point-only.
- 73/73 tests; Keil0 errors/0 warnings; RAM63304/65536 (2232 free), static stack
  peak1304 +1024 reserve within4096. Runtime watermark remains open.
- No flash or hardware operation. Board remains on `CAPTURE_EXPORT_20261025`.

## 2026-11-05 Shared offline envelope stability increment

User OK authorized offline general-envelope repair before a firmware decision.
Unified adaptive/diagnostic extraction into tools/bp_standard_envelope.py,
selected the longest contiguous eligible interval for cadence, required entire
beats inside it, and added fixed0/2.5/5/7.5mmHg bin-origin and competing-peak
abstentions. Labels and exported firmware envelope fields remain excluded.

146 tests pass, including8 added envelope regressions and existing actual-C
host tests. Audited13 historical attempts:8 complete/5 failed,5 candidates/3
complete high-setting abstentions. Latest Preset4 target275 default215mmHg
peak spans212.5..230 with origin changes, exceeding the declared15mmHg
development sensitivity threshold; it is withheld. This is not an accuracy
interval. Synthetic60/30 still abstains; not all presets have real captures.

Report/plot/hashes: data/reports/standard_bp_envelope_stability_20261105.md
and matching JSON/PNG/manifest/baseline/adaptive/diagnostics. Plot inspected.
No device I/O or C/Keil/flash/calibration work. Device remains on the separately
verified CAPTURE4200_20261105; fixed MAP window/offset debt remains unresolved.
Task remains in_progress. No initial commit or archival: repository has no HEAD
and extensive pre-existing untracked user work; this increment is recorded in
task artifacts and this journal without staging unrelated content.

## 2026-11-05 follow-up: localized offline peak instability

Under the user's OK, added tools/bp_peak_instability.py and8 diagnostic
regressions. Reused shared extraction/gates unchanged. Validated raw/metadata/
verified hashes for all13 attempts; diagnosed8 complete and retained5 failures.
All per-origin bin members, smoothing contributions, leading-bin margins and
every fixed-beat deletion are retained. No favorable subset becomes an estimate.

Latest target275:73 accepted beats, leading height bins only3..4 beats,
top-two height margins0.36..2.49%, origin peak range212.5..230.11/73 deletions
change at least one origin's height/area peak;62 remain unstable,7 fail origin
gates,4 pass. This localizes binning/argmax sensitivity, not physical cause or
calibrated BP error. Full valve event timing is absent; aggregates show200ms
period but zero >=5mmHg steps cannot exclude smaller valve artifacts.

Full153-test suite passed; after adding final output-overwrite regression,
current8-test diagnostic suite passed (7 overlap;154 distinct current tests
covered). Exact reproduction of the final diagnostic and prior adaptive and
diagnostic reports passed; source hashes checked and four-panel plot inspected.
Final evidence: data/reports/standard_bp_peak_instability_20261105_reviewed.md,
matching JSON/PNG and .validation.json. Preliminary outputs remain retained;
the reviewed prefix records current code hashes and is the final reference.

Spec capture-export section20 records contracts and causal boundaries. Next
physical step requires synchronized valve on/off event logging and validated
controlled peak-region windows/repeats; independent dynamic pressure reference
is still absent. No C/header/uvprojx/Keil/flash/calibration/serial/pneumatic
work in this increment. Known on-device fixed-window/offset debt remains.
Task stays in_progress; repo has no HEAD, no initial commit or archival.

## 2026-11-05 follow-up: exact valve timing and peak-window comparison

Implemented600 bounded GPIO open/close pairs, schema4/export/strict decode and
actual-C cancellation/wrap/error regressions. Archived old firmware sources
before new profile build. New firmware PEAK_WINDOW_20261105 adds guarded
profile normal|peak, default normal, fixed200..245 at requested1.8mmHg/s.
159 tests passed, Keil0/0, RAM63360/headroom2176, stack4096 with runtime
used1624/free2472. Download verified and original82.326/-19.887 calibration
restored+read back.25 actual5ms zero pulses complete, no ADS/UART faults.

Normal trial3299 points/413 pulses: closeout initially failed at3.5; manual
unload after HOME/manual clarification allowed freshzero/seal/export. Standard
BP has no Stop; manual paper3-15/PDF51 says HOME returns Main, not proof of
unloading. Keep failed and recovery raw logs. One peak trial3273/410 pulses
completed/exported, both no dropped samples and exact25ms ticks. Each replayed
against matching firmware C, envelope/features/validity bits equal, max error0.

Fixed-band beats20->28, OLS slope2.916->2.354 (not requested1.8), all-origin
peak range212.5..240 ->212.5..222.5, span27.5->10, frozen stability reject->pass.
Peak one-beat deletions10/82 alter peaks;71 pass and11 fail. Both original
firmware BP results failed and high50% crossings absent. Candidate215 is not
independent accuracy proof. Low-side envelope shape and zero baseline differ;
single sequential trials cannot isolate cause. Exact command alignment shows
median0..25ms sample changes-0.980/-0.689 then rebound, physical cause unresolved.

After long export1.4mmHg transient, final check vent->freshzero->seal plus15s
sealed observation stayed displayed0. Final safe pins, faultNONE, ADS0 errors,
normal restored and target50. Raw final preflight peakwindow_final_20261105-123717.
Reports: data/reports/standard_bp_peakwindow_comparison_20261105.{json,md,png},
per-trial analysis/replay and source archives under data/provenance. New archive
SHA256 d5cd464918e215d6f660f962ddc8e68339c9833fee16b6fafd082840585ffaf6.
Plot visually checked; control/capture/safety specs and execution checklist
updated. Next repeat identical frozen peak conditions before other presets;
independent dynamic reference and legacy C window/offset repair still pending.
Task remains in_progress; no staging, initial commit or archive.

