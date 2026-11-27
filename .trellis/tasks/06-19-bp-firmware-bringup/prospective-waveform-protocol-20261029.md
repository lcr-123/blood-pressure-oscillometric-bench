# Prospective non-human waveform repeatability protocol (locked 2026-10-29)

## Question and scope

Test whether the existing **exploratory** beat-height quality screen yields a
repeatable, complete oscillogram under one fixed BP Pump 2 simulator setting.
The archive used to choose the screen is excluded from this prospective set.
This is a three-run engineering pilot, not a clinical accuracy study or an
independent pressure calibration. No simultaneous independent pressure gauge
is available. A simulator panel label cannot establish true SBP, DBP or MAP.

## Fixed condition and run order

- Three new sequential non-human captures, slots P1, P2 and P3. Do not replace
  a failed or invalid slot with an unrecorded retry. Record every attempted
  run, including aborts and incomplete exports. An export retry of the **same**
  retained MCU capture is transport verification, not an additional run.
- Operator confirmed on 2026-10-29 that BP Pump 2 remains at User Defined
  150/100 mmHg, 80 BPM, 0.7 cc, External Cuff, with the cuff fixed on a
  non-human fixture; connections and pneumatic path are unchanged. Record any
  setting/fixture change before another run and stop this matched series.
- The existing STM32 image `CAPTURE_COMPACT_20261028` uses target 180 mmHg.
  The host aborts on the first fresh reported pressure >=190 mmHg or on stale
  pressure, device fault, timeout or capture overflow. This sampled host
  boundary cannot guarantee that pressure never briefly exceeds 190 mmHg;
  the firmware's independent safety path remains essential. Do not run the
  target-190 mode or increase the target. A run using >=3100 of the 3300
  points or any nonzero dropped count ends this series until the
  storage/safety budget is reassessed.
- Before each run: fresh five-second serial zero snapshot; `status`, `pins`,
  `cal`, `fault` preflight with cal VALID 82.326/-19.887, ADS ONLINE,
  manual OFF, PC0/PC1 LOW, PC8 HIGH, pump OFF and fresh sealed pressure near
  zero. If hardware is disconnected or powered again, first check unpowered
  polarity/shorts, then established supply and logic levels; do not infer
  new voltage or pin assignments. Use only the previously documented power
  and common ground. MCU PB6/PB7 connect the ADS1115 sensor path, PB10/PB11
  USART3 the bridge, PC0/PC1 the valves, and PC8 the pump relay.
- Acquire a natural full waveform with the existing bounded host script.
  Close every pressure run with `stop` -> `vent` -> fresh near-zero samples ->
  `seal`; verify sealed pins and post-seal fresh zero. BP Pump 2 normally
  stops when the external pressure has returned to zero; check its panel
  only if pressure does not settle, keeps oscillating or the next run cannot
  start. Export only after the post-seal gate. No human contact.
- Preserve the raw bridge acquisition log, raw export, verified NDJSON,
  production-C replay report and SHA-256 of each raw export. Capture order is
  determined by the acquisition start, not by which result looks plausible.

## Locked analysis

1. Require the strict `bp_capture.decode` complete begin/points/valve/
   features/end sequence, FNV checksum, zero dropped points, 25 ms nominal
   interval and exact 25 ms MCU tick differences. A failed transport export
   may be retried from the same retained capture after a fresh post-seal
   preflight; never join partial transfers.
2. Use `bp_oscillogram_study.analyze(capture, step_padding_samples=40,
   upper_pressure=170)` without panel SBP/DBP or firmware validity as input.
   Its existing pulse gate, 0.9-2.5 Hz beat filter, 5 mmHg step exclusion,
   5 mmHg occupied bins, Gaussian fit, rise/fall tails, fit consistency,
   >=3 beats in the strongest bin, <=15 mmHg occupied-bin gap and <=7.5
   mmHg maximum leave-one-bin-out shift remain unchanged.
3. A per-run **screen success** requires `status=diagnostic_only` **and**
   `height.robustness.screen=pass`. Every other status is a failure with its
   reason retained. A `pass` alone is insufficient if the oscillogram is
   incomplete or its peak is unstable. The Gaussian center is a diagnostic
   peak, not true MAP.
4. Report the number of successes out of the three planned slots. Only 3/3
   successes plus a <=7.5 mmHg range of the three fitted centers supports
   the narrow statement that this screen is repeatable under this bench
   condition. Fewer usable runs, any abort, or a wider range does not support
   that statement. It does not justify firmware parameter changes or BP
   accuracy claims, even on success.
5. Secondary diagnostics only: production-C replay equality, firmware
   `calc`/validity, raw MAP/DBP features, DBP crossing elapsed time, and
   whether that time is <=0.75 s (one nominal 80 BPM beat). The 0.75 s
   count is **not** a rejection gate. Do not change this protocol or the
   analysis code after viewing P1/P2/P3 to improve their outcomes.

## Frozen implementation identities

SHA-256, repository-relative paths, recorded before P1:

| File | SHA-256 |
| --- | --- |
| `blood pressure monitor/tools/bp_oscillogram_study.py` | `C12F8E88EAECA81E06E8C124AA333DB5A6F0B78633BAA7FF8E90CB646B32F12C` |
| `blood pressure monitor/tools/bp_beat_analysis.py` | `B6B4A45CDFDF76C28D64169DD9A6A729470B03C3205FB2944B605427198BAF47` |
| `blood pressure monitor/tools/bp_capture.py` | `8C3AE426EDD106AA7B591D7422D135DFE7626D7EF416A36D150CE9BF66D42894` |
| `blood pressure monitor/tools/bp_capture_batch_report.py` | `906BB6A1E5649C393D7B4B2F4E73E6644DBE1CA5021519AEC304936DFE8C1F0C` |
| `tmp/linkpad_lowpressure_check.py` | `86A3460EC2BFC027C8962C19C3DA715F616270A9E94671313811F3EDB98C241D` |
| `tmp/linkpad_capture_io.py` | `DE0B0230BAF1C41552DB670DEFE54B5D444D01F6AC3F6347214E78CD441FC4C3` |

Only the host 180 mmHg abort boundary changed before this freeze, from 195
to 190 mmHg; the offline fake-bridge suite passed 20/20. Firmware C,
Keil project, calibration and pressure-control behavior were not edited.
