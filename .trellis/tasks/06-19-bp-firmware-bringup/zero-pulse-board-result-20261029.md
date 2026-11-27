# Sealed-zero valve pulse check, 2026-10-29

## Purpose and limits

The L2/L3/L4 100/65 captures have a recurrent pressure notch at a fixed
phase after a PC1 command, sometimes 5-9 mmHg. This non-human comparison
checks whether the same sensor chain shows a similarly large notch when the
same 5 ms/200 ms valve drive operates at zero applied pressure. It cannot
prove pneumatic versus electrical origin, and a 25 ms ADC schedule cannot
resolve a disturbance confined to the 5 ms open interval.

## Wiring and safe procedure

No wiring or supply setting was changed from the user-confirmed non-human
fixed setup. The affected MCU signals are PC1 (deflation valve), PC0
(inflation valve, kept LOW), PC8 (pump relay, kept HIGH), I2C1 PB6/PB7
(ADS1115), and USART3 (CH340 serial bridge). The MPXV5050GP output remains
connected through the existing divider to ADS1115 A0. Sensor P2 remains
vented to ambient; the existing cuff/tubing assembly is non-human. Retain
the already verified common ground and power wiring; no new voltage or
connection is authorized by this diagnostic.

For reproduction, with power disconnected check the existing harness for
shorts and unintended continuity, then power the known assembly and verify
the established rail voltages at the module pins before operation. Keil
rebuild the MDK-ARM project and require zero errors/warnings plus the RAM/
stack budget check. With no human connected, use `vent`, verify continuous
fresh near-zero pressure, then `seal`; confirm PC0/PC1 LOW, PC8 HIGH,
ADS ONLINE, calibration VALID and pump OFF. Download only via the established
Keil `UV4 -f` SWD path. A full-chip erase requires restoring the current
MPXV5050GP record `cal write 82.326 -19.887` and reading back VALID before
running the test. Run one `zero pulse`; expect about 25 PC1 pulses, automatic
PC1 LOW, about 200 samples and zero drops. `capture export` should produce a
strictly valid `/3` with `calc=0` and no BP result. Finish `vent` -> fresh
near-zero samples -> `seal`; verify PC0/PC1 LOW, PC8 HIGH. Any ADS failure,
pressure above 1 mmHg or dropped sample requires emergency vent and no
diagnostic interpretation.

## Software and board evidence

- Host firmware suite: 103 tests passed. Bridge failure-path suite: 6 tests
  passed. Keil true rebuild: Code 50252, RO 6868, RW 28, ZI 63444;
  0 errors, 0 warnings. `check_firmware_budget.py`: RAM 63472/65536,
  headroom 2064 B; known stack peak 1336 B plus 1024 B reserve fits
  the 4096 B allocation. `main.c` and `bp_algorithm.c` are in uvprojx.
- Before flash: 92 fresh 0.0 mmHg samples, PC0/PC1 LOW, PC8 HIGH,
  ADS ONLINE/errors0/recoveries0, calibration VALID. HEX SHA-256:
  `7FC6617652173859A13C1790B5971D2A7F684ED4A2DE6E0B7A2404D2E655007E`.
- After `UV4 -f`: IDLE, pump OFF, safe pins, ADS ONLINE and expected UNCAL.
  Restored only `82.326/-19.887`; independent readback showed VALID
  82.326/-19.89 and 92 fresh 0.0 mmHg samples.
- Single run: `[ZeroPulse] done pulses=25 last_tick=140808`, PC1 LOW,
  n=200/dropped=0/span4974ms. Strict `/3` decode passed, with 25 actual
  pulses, period exactly 200ms, on-time exactly 5ms, `calc=0`, no >=5mmHg
  step. Bridge log `tmp/capture_zero-pulse_20261029-171234.ndjson`, SHA-256
  `09CCEAA4DBF6A11640DB8A9C118FC44B23D3F6081C58D48A3AE5FD990818120E`.
  Strict verified export `tmp/capture_zero-pulse_20261029-171234.verified.ndjson`,
  SHA-256 `72A94D91BFB88DA367EDA4D33ED59C957EB2595A55D6003FFAFAFDA8B28CCA6E`.
- Final closeout: `vent` -> fresh low-pressure samples -> `seal` ->
  PC0/PC1 LOW, PC8 HIGH. Later read-only preflight found 100 fresh
  0.0 mmHg samples, ADS errors0/recoveries0 and runtime stack
  used1568/free2528/reserved4096/saturated0.

Reproduce the voltage-phase audit with:

```powershell
python 'blood pressure monitor/tools/bp_zero_pulse_audit.py' tmp/capture_zero-pulse_20261029-171234.verified.ndjson --last-tick 140808
```

Audit script SHA-256:
`FD9248CDEB1F8A09E69C48423B097DAE99F1A9A75BD70252B9716F40FF6BCFF0`.
All 200 displayed pressures were 0.0 mmHg (negative pressure is clipped by
the driver). Unclipped sensor voltage ranged 0.2192316-0.2197490 V, a
0.0426 mmHg equivalent peak-to-peak span, about three ADC codes. Each of
the eight 25 ms valve-phase bins had median adjacent voltage change 0;
the largest single adjacent equivalent change was 0.0284 mmHg.

Under this zero-load condition, a fixed pressure-independent 5-9 mmHg
electrical artifact did not reproduce. The earlier sustained manual `vent`
test shifted baseline by roughly 0.5 mmHg equivalent, also much smaller
than the high-pressure notches. A pressure-dependent pneumatic transient
is now more plausible, but pressure-dependent electrical/sensor effects
and sub-25ms transients remain possible. An independent simultaneous
pressure or electrical measurement would be needed to assign physical
cause. Do not alter BP algorithm or clinical claims from this one test.
