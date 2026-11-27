# Prospective 100/65 non-human waveform protocol (locked before L1)

## Question and limits

Under a second fixed BP Pump 2 User Defined setting, test whether the
existing beat-height screen is repeatable and whether its fitted peaks
are separate from the already completed 150/100 pilot. This is an
engineering waveform comparison. The panel labels are not an independent
pressure reference, and no simultaneous independent gauge is available.
No absolute MAP, SBP/DBP accuracy or human-use conclusion is permitted.

## Fixed condition and acquisition

- Planned order: three new non-human slots L1, L2, L3. Include each attempt
  regardless of firmware validity or screen outcome. Do not substitute an
  unrecorded repeat for a failed slot. A retry of the same retained RAM
  capture's export is a transport retry, not a new acquisition.
- Before L1, the operator must explicitly confirm BP Pump 2 User Defined
  100/65 mmHg, 80 BPM, 0.7 cc, External Cuff, cuff fixed to the same
  non-human fixture and unchanged tubing/connections. Stop this matched
  series if any setting, volume, fixture or plumbing changes.
- Use the current `CAPTURE_COMPACT_20261028` image and existing
  `python tmp/linkpad_lowpressure_check.py --user-defined` path: target
  150 mmHg, host abort on first fresh reported pressure >=165 mmHg,
  75-second acquisition deadline, device-fault/pressure-freshness checks
  and firmware emergency paths. The sampled host ceiling does not prove
  a hard peak bound between samples. A run with >=3100/3300 points or any
  dropped sample ends the series pending a storage/safety review.
- Before every inflation, obtain a fresh five-second zero-pressure serial
  snapshot and the script's `status`, `pins`, `cal`, `fault` preflight:
  cal VALID 82.326/-19.887, ADS ONLINE, manual OFF, PC0/PC1 LOW,
  PC8 HIGH, pump OFF and fresh sealed near-zero pressure. On any hardware
  reconnection or power cycle, first check unpowered shorts/polarity,
  then established supply/logic levels. Retain the documented common
  ground, STM32 PB6/PB7 ADS1115 sensor, PB10/PB11 USART3 bridge,
  PC0/PC1 valves, PC8 pump relay and External Cuff path. No new supply
  or connector assumption is made.
- After each natural capture or abort, complete `stop` -> `vent` -> fresh
  near-zero -> `seal`, then check *new* post-seal samples. If pressure
  rebounds above the export preflight range `[-2,+1]` mmHg, repeat
  vent -> fresh zero -> seal and recheck before exporting the retained
  capture. BP Pump 2 normally stops after external pressure returns to
  zero; check the panel only if it does not settle, continues oscillating
  or cannot begin another run. No human contact.
- Save the acquisition bridge log, complete raw export, strict verified
  NDJSON, CSV and production-C replay; record each raw and verified
  export SHA-256. Strict decode requires complete order/count/FNV,
  dropped=0 and exact 25 ms MCU intervals. Never join partial exports.

## Locked analysis and decision

1. Use `bp_oscillogram_study.analyze(capture, 40, 130)` on each strict
   verified capture. Do not feed the panel pressure label, firmware BP
   validity or the 150/100 fitted peaks into beat extraction. The current
   label-free pulse gate, 0.9-2.5 Hz beat filter, >=5 mmHg step exclusion
   with 40-sample padding, 5 mmHg bins, tail/fit conditions, >=3 beats
   in strongest bin, <=15 mmHg occupied gap and <=7.5 mmHg maximum
   leave-one-bin-out shift remain unchanged.
2. Each slot succeeds only if `status=diagnostic_only` **and**
   `height.robustness.screen=pass`. Retain and report every failure reason.
   A fitted center is a diagnostic beat-height peak, not true MAP.
3. Report success count out of all three planned slots. Only 3/3 successes
   and a <=7.5 mmHg range of the three fitted centers support repeatability
   at this lower simulator condition. Any abort, missing complete capture,
   failed screen or wider range does not support that statement.
4. Only if both the prior 150/100 series and this 100/65 series meet their
   within-condition repeatability rules, compare all six fitted centers.
   Report whether the groups are strictly nonoverlapping and the minimum
   between-group gap; do not choose a new threshold based on the result.
   Nonoverlap supports condition discrimination in this fixture only.
5. Secondary observations: label-free BPM, firmware `calc` and output,
   raw MAP/DBP features, MAP-to-DBP elapsed time, pressure-step counts,
   peak-bin beat support and tail ratios. The 0.75-second temporal count
   remains descriptive and cannot reject a capture. No firmware MAP
   window, ratios, offsets or pressure calibration are changed by this
   experiment.

## Frozen tools and comparison cohort

SHA-256 before L1:

| File | SHA-256 |
| --- | --- |
| `blood pressure monitor/tools/bp_oscillogram_study.py` | `C12F8E88EAECA81E06E8C124AA333DB5A6F0B78633BAA7FF8E90CB646B32F12C` |
| `blood pressure monitor/tools/bp_beat_analysis.py` | `B6B4A45CDFDF76C28D64169DD9A6A729470B03C3205FB2944B605427198BAF47` |
| `blood pressure monitor/tools/bp_capture.py` | `8C3AE426EDD106AA7B591D7422D135DFE7626D7EF416A36D150CE9BF66D42894` |
| `blood pressure monitor/tools/bp_capture_batch_report.py` | `D8FD1466A6278FB0488F77AF38983F2091967390463B65FB5BBE557C4E042023` |
| `tmp/linkpad_lowpressure_check.py` | `86A3460EC2BFC027C8962C19C3DA715F616270A9E94671313811F3EDB98C241D` |
| `tmp/linkpad_capture_io.py` | `DE0B0230BAF1C41552DB670DEFE54B5D444D01F6AC3F6347214E78CD441FC4C3` |

The 150/100 comparison cohort is exactly P1/P2/P3 from
`prospective-waveform-results-20261029.md`, strict verified export IDs
`112521`, `112950`, `113351` on 2026-10-29, with fitted centers
118.26, 119.26 and 119.88 mmHg. No new 150/100 capture may be added to
that comparison after the lower-condition results are viewed.
