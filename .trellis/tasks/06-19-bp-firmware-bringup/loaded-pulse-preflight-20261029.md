# Loaded-pressure valve pulse: software and zero-pressure preflight

The user updated the observed sealed leak to approximately 11 mmHg/min.
That is about 0.73 mmHg in four seconds if the rate remains constant. It is
only a planning estimate; the one-second sealed baseline in the next capture
must determine the actual local drift. No loaded-pressure run is recorded yet.

## Build and bench state

- Firmware ID: `LOADED_PULSE_DIAG_20261029`. Keil full rebuild on 2026-10-29:
  Code 51776, RO 7400, RW 28, ZI 63444; 0 errors, 0 warnings.
  `main.c`, `bp_control.c`, and `bp_algorithm.c` are present in the uvprojx.
- Static RAM budget: 63472/65536 B, headroom 2064 B. Known stack peak
  1344 B plus 1024 B reserve fits the 4096 B stack allocation. The
  target runtime watermark still needs confirmation under the loaded run.
- Host firmware suite: 105 tests passed, including a synthetic 11 mmHg/min
  baseline and valve-phase notch; bridge tests: 7 passed. Python capture
  and audit scripts compile. The loaded phase audit has not yet been
  exercised against a live `/3` capture.
- Before flash: 101 recent 0.0 mmHg samples, PC0/PC1 LOW, PC8 HIGH,
  ADS ONLINE/errors0/recoveries0, calibration VALID 82.326/-19.89,
  fault NONE, runtime stack used1568/free2528/saturated0.
- New HEX SHA-256:
  `D04DA5BE33B79FFB1A9F64BEC5CB7260DAB0F9A6771D85DA65EF10C45232A23C`.
  Download used the established Keil `UV4 -f` SWD path. After download,
  startup was IDLE with PC0/PC1 LOW, PC8 HIGH, ADS ONLINE and expected
  UNCAL. Restored only `cal write 82.326 -19.887`, then independently read
  back VALID 82.326/-19.89.
- After restoration, 101 fresh 0.0 mmHg samples and safe pins passed
  `tmp/linkpad_capture_io.py preflight`. The `--firmware` option now verifies
  the immutable capture header after a complete export; a live status
  response does not carry the software ID.

## Non-human loaded run procedure

Keep the previously verified fixed, non-human assembly. STM32 PC1 drives
the deflation valve, PC0 the inflation valve, PC8 the pump relay; I2C1
PB6/PB7 reads ADS1115 A0 from the current MPXV5050GP sensor and USART3
reports to CH340. The sensor P2 remains open to ambient. Do not change the
existing module supplies or common-ground wiring for this diagnostic. If
any harness is moved, disconnect power first and check continuity/shorts
and pin identity, then check the established module rail voltages after
power-up before operating pressure hardware; a reversed or wrong supply
can damage the modules. No person may be connected.

Use only the BP Pump 2 Pressure Source function at 60 mmHg with its Pressure
Port connected to the previously verified non-human static three-way
sensor/cuff fixture. Do not substitute External Cuff or Vent/Zero Port.
The user's confirmation of this panel and fixture state is pending. With
the fixture sealed, observe fresh 40-80 mmHg serial readings, a recent
40-sample span no more than 1.5 mmHg, PC0/PC1 LOW, PC8 HIGH, ADS ONLINE,
calibration VALID and fault NONE. Stop the plan if these gates fail.

Run only one `python tmp/linkpad_capture_io.py loaded-pulse`. It commands a
one-second sealed baseline and three seconds of 5 ms/200 ms PC1 pulses; the
internal pump remains OFF. **In the actual static fixture, PC1 is isolated
from the BP Pressure Source/MPXV5050GP/cuff three-way line.** Firmware opens
PC1 on completion but this does not vent that line. The host closes PC1 with
`seal` and retains the capture. Stop the BP Pump 2 at its panel to release
the static source, confirm consecutive fresh near-zero samples, then run
`python tmp/linkpad_capture_io.py export --firmware LOADED_PULSE_DIAG_20261029`.
The export strictly checks the complete `/3` capture; expect approximately
160 samples, 12-16 pulses, no dropped points, `calc=0`, and no BP result.
Pressure outside 20-85 mmHg, ADC failure or capture overflow must stop
the diagnostic and invalidate the run. Firmware `vent` only controls the
isolated PC1 valve in this fixture. The operator must use the BP panel
Stop when its Pressure Source leaves the static line pressurized; fresh
serial readings near zero confirm that the external line has unloaded.

## First board run and corrected interpretation

The user reported panel 75 mmHg. Host gate passed at 58.2 mmHg on the STM32
sensor. The run completed 15 PC1 pulses, 160 samples, 3974 ms, dropped0.
The initial host script incorrectly assumed PC1 could vent the static line;
after `vent` the serial pressure remained approximately 50 mmHg. The script
was stopped, PC1 was closed with `seal`, and the operator used the BP panel
Stop. Fresh pressure fell to approximately 1 mmHg. Strict `/3` export then
passed with `calc=0`, firmware ID `LOADED_PULSE_DIAG_20261029`, and no
>=5 mmHg steps. Verified file:
`tmp/capture_export_20261029-175604.verified.ndjson`, SHA-256
`CF21678398C06C02D40D6DE45382B69C46A1A8C1676A4CFC31391B2A3CDDE95A`.

The sealed 40-sample baseline went 58.1005 to 57.9159 mmHg in 974 ms;
linear fit -10.945 mmHg/min. The 120-sample pulse interval went 57.9301
to 57.5041 mmHg in 2975 ms; linear fit -8.554 mmHg/min. Across 15 pulses,
the largest adjacent fall in the eight 25 ms phase bins was 0.0426 mmHg.
This tests pressure-dependent electrical/sensing coupling from an isolated
PC1 drive; it does **not** test pneumatic valve opening in the BP static
line. Do not compare the absent 5-9 mmHg notch as proof that the active
valve/fixture is mechanically sound. The panel 75 vs sensor 58 mmHg
disagreement is also unresolved; BP panel mode and reference meaning need
confirmation before treating 75 as a reference pressure.

After export, use `bp_loaded_pulse_audit.py <verified.ndjson> --last-tick
<tick-from-test.pulse_result>` to compare fitted sealed-baseline drift,
pulse-interval drift and pressure/voltage changes in eight 25 ms valve
phase bins. This shared sensor trace can establish reproducible association,
but cannot alone identify valve mechanics, BP pressure regulation or
pressure-dependent electrical coupling as the physical cause.
