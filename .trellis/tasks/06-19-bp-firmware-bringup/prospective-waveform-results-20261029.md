# Prospective non-human waveform results (2026-10-29)

Protocol: `prospective-waveform-protocol-20261029.md`, SHA-256
`CDFD3E315F1C776AC9D6AF5E9A317AA015AC29C66759930BF46A9BC2B7CA8730`
before P1. The six frozen implementation hashes in that protocol were
rechecked after P3 and remained unchanged. The operator confirmed the
same User Defined 150/100 mmHg, 80 BPM, 0.7 cc, External Cuff setting,
fixed non-human cuff and unchanged connections before P1.
After all three slots and the hash check, only the batch-report CLI gained
an inclusive archive cutoff; its per-capture `inspect()` and the locked
oscillogram analysis were not changed during this study.

## Three planned slots

| Slot | Acquisition log | Complete export | Peak observed | n/3300 | Firmware SBP/DBP, BPM | Raw MAP/DBP | MAP-to-DBP | Clean beats | Strongest-bin beats | Fit peak | Jackknife shift | Locked result |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| P1 | `tmp/linkpad_user_defined_180_20261029-111948.ndjson` | `tmp/capture_export_20261029-112521.ndjson` | 180.3 mmHg | 2761 | 147/93, 84 | 99.81/98.03 mmHg | 1.150 s | 58 | 3 | 118.26 mmHg | 2.25 mmHg | `diagnostic_only`, pass |
| P2 | `tmp/linkpad_user_defined_180_20261029-112724.ndjson` | `tmp/capture_export_20261029-112950.ndjson` | 180.6 mmHg | 2889 | 149/82, 75 | 95.22/87.24 mmHg | 3.450 s | 66 | 3 | 119.26 mmHg | 1.91 mmHg | `diagnostic_only`, pass |
| P3 | `tmp/linkpad_user_defined_180_20261029-113119.ndjson` | `tmp/capture_export_20261029-113351.ndjson` | 180.4 mmHg | 2673 | 149/82, 75 | 99.04/87.84 mmHg | 3.625 s | 58 | 3 | 119.88 mmHg | 1.37 mmHg | `diagnostic_only`, pass |

All three captures have dropped=0, exact 25 ms MCU intervals, a complete
`bp.capture/2` FNV-verified end, and matching production-C replay: envelope
bits, feature bits and validity are equal, with 0.0 V maximum envelope and
smooth difference. The label-free pulse estimate is 80 BPM for each. The
occupied-bin maximum gap is 10 mmHg in each; the strongest bin has exactly
the required three beats, so support is at the locked minimum. The
height-curve low/high tail ratios are P1 0.345/0.670, P2 0.407/0.296,
P3 0.434/0.244. No source or threshold changed between slots.

Raw/verified export SHA-256:

| Slot | Raw bridge export | Strict verified NDJSON |
| --- | --- | --- |
| P1 | `359479FAC47E38D50C8126B50E0384A37BC2A72D7347ECB2DC7F96CA1E24AED2` | `512E5604C14BD57B99ABB91D32C9CA931DA2190959B16CFAA40ECEC48E954C0D` |
| P2 | `B3A95FAF9BA4482F71A6CBA43CFBCB85902D8F6EE95AE2152983187C576E84CC` | `AFD30B9C041B3C127AE2089A275395EEFFE06F345DF351B1FEF59948DE3C0A75` |
| P3 | `E023BB8FB61E7AE12ECCF73275407669BA7D49F58336948CF626623075EE8FFD` | `C0E8E332364683763D6B5BD9CC75B211921F2E85972DE82ECB00A1E762BFA477` |

The three companion `.verified.ndjson`, `.csv` and `.replay.json` files use
the same export IDs. A P1 preliminary export command with optional
`--firmware` stopped at host preflight: current status lines omit `sw=`.
Its log is `tmp/capture_export_20261029-112422.ndjson`; it sent no
`capture export`, then performed stop/vent/seal. The later successful P1
export is the **same retained 2761-point capture**, not a fourth run.
The actual export begin record confirmed `CAPTURE_COMPACT_20261028`.

## Prespecified decision

Screen success is 3/3. The fitted centers span 119.88-118.26 = 1.62 mmHg,
below the locked 7.5 mmHg range limit. Therefore this exploratory
beat-height screen was repeatable in this one non-human simulator condition.
All three firmware results were valid, but their DBP output spans 82-93
mmHg and their firmware MAP features lie at 95.22-99.81 mmHg, well below
the independent fitted peak candidates. None of the prospective
MAP-to-DBP intervals is <=0.75 s; this temporal count remains descriptive
and is not a validated quality gate.

This result does **not** validate the fitted peak as true MAP or the
firmware's SBP/DBP as accurate. No independent simultaneous pressure trace
or clinical reference is available, and the panel setting is operator
reported rather than encoded in the exports. Keep MAP bounds, SBP/DBP
ratios, compensation and firmware unchanged. Different simulator settings
and pressure sources require separate validation.

## Physical closeout and next gate

Each natural acquisition ended with stop -> vent -> fresh near-zero ->
seal. The first post-seal five-second snapshots rebounded to 3.9-4.1,
3.7-3.9 and 4.1-4.2 mmHg for P1/P2/P3, respectively. No export was made
at that pressure. A second vent yielded 100 fresh 0.0 mmHg samples, and
each subsequent seal yielded another 100 fresh 0.0 mmHg samples before
export. The final diagnostic-only preflight
`tmp/capture_preflight_20261029-113633.ndjson` confirmed 92 fresh 0.0
mmHg samples, PC0/PC1 LOW, PC8 HIGH, pump OFF, cal VALID, ADS ONLINE,
errors/recoveries 0/0 and the retained P3 capture. The bridge 5-second
snapshot after P3 export also had 100/100 samples at 0.0 mmHg.

No wiring, power, firmware C, Keil project/image or calibration changed.
The host script's 180 mmHg abort line was reduced to 190 mmHg before the
protocol freeze; 20 fake-bridge tests and syntax checks passed. No Keil
build/download was needed. For any later pressure work, retain the
documented STM32 PB6/PB7 ADS1115, PB10/PB11 USART3, PC0/PC1 valve, PC8
pump relay and BP Pump 2 External Cuff connections, established supplies
and common ground. After any reconnection, check unpowered polarity and
shorts, then powered levels. Require the same non-human fixture, fresh
sealed zero/ADS/cal/pins gate, pressure abort and vent -> fresh zero ->
seal closeout. Do not repeat target190 while component pressure ratings
and the small 3300-point budget margin remain unresolved.
