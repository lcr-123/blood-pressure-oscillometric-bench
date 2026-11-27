# Runtime stack watermark: wiring and non-human validation

## Scope and safety boundary

This increment instruments the existing 4096-byte Cortex-M3 main stack. It does
not change the pressure algorithm, calibration, valve timing, pressure limits,
GPIO polarity, or electrical configuration. Validation remains strictly
non-human: use the existing External Cuff setup with the real cuff as the test
volume and do not connect the cuff to a person.

No wiring or supply change is required. Keep the already verified connections:

- USART3 PB10/PB11 to the existing CH340 serial path, with the established
  common ground.
- I2C1 PB6/PB7 to the existing ADS1115 pressure acquisition path.
- PC0/PC1 valve controls and PC8 pump control through their existing drivers.
- SWD PA13/PA14 for the existing CMSIS-DAP/Keil programming path.
- The existing External Cuff pneumatic path, real cuff volume, MPXV5050GP P1
  pressure port, and P2 atmospheric reference.

Before powered operation, retain the project's established inspection order:
with power removed check wiring, polarity, common ground, shorts, and tubing;
then power the existing setup and measure the already documented key supply and
logic nodes; only then run the firmware. This document introduces no new supply
voltage recommendation.

## Build, download, and calibration recovery

1. Rebuild `blood pressure monitor.uvprojx` with Keil ARMCLANG and require zero
   errors and zero warnings. Confirm `stack_watermark.c` is in the Keil project.
2. Download only with Keil `UV4 -f`. The configured full-chip erase clears the
   Flash calibration.
3. While the pneumatic system is unpressurized, require IDLE, manual OFF,
   ADS ONLINE, PC0/PC1 LOW, PC8 HIGH, and pump OFF.
4. If `cal` reports UNCAL on the unchanged hardware, restore exactly
   `cal write 82.326 -19.887`, require the firmware's `written+verified`
   response, and independently query `cal` for VALID / 82.326 / -19.89.
5. Require fresh near-zero pressure samples and `fault` code NONE before any
   pressure command.

## Dynamic validation sequence

1. Run one non-human 50 mmHg low-pressure start/stop exercise. Confirm the pump
   and valve GPIOs return to their safe states.
2. Close out in the mandatory order: `vent`, wait for consecutive fresh pressure
   samples near 0 mmHg, then immediately `seal`.
3. Run one complete non-human BP Pump 2 Standard BP cycle using the previously
   verified External Cuff, 120/80 mmHg, 80 BPM configuration. Retain the required
   high-pressure hold so the simulator pulse waveform is present.
4. Wait for capture and calculation completion. Again close out with
   `vent` -> consecutive fresh near-zero samples -> `seal`. The simulator may
   stop automatically after external pressure is released.
5. Export the complete `/2` capture. Require strict decoding, no dropped samples,
   monotonic 25 ms MCU ticks, and bit-equal production-C replay of the reported
   envelope, features, result, and validity.
6. Query `stack` twice after the measurement and export path. Require
   `reserved=4096`, `saturated=0`, and at least 1024 bytes free. Also require ADS
   errors/recoveries to remain zero and the final actuator pins to be safe.

Validation passed on 2026-10-28 with a 120/80, 80 BPM Standard BP capture:
2305 points, zero drops, exact 25 ms ticks, strict `/2` decode and bit-equal
production-C replay. Both post-export readings were used=1536/free=2560,
reserved=4096, saturated=0. The low-pressure active-stop run peaked at
29.3 mmHg and closed out safely. This meets the reserve gate for the exercised
path; see `validation.md` for raw evidence and interpretation limits.

## Interpretation limits

The watermark is initialized as the first statement in `main`, after C runtime
ZI initialization and before HAL initialization. It therefore covers the
firmware, interrupt, measurement, calculation, and export paths exercised after
entry to `main`; it does not measure transient C-runtime stack use before
`main`. A 128-byte live-stack guard is conservatively counted as used during
initialization. Pattern coincidence and stack frames that reserve but never
write every byte can make a fill-pattern watermark underestimate the exact
historical MSP depth. Consequently, the runtime result supplements the Keil
callgraph/static budget and 1024-byte reserve gate; it is not an MPU overflow
guard or proof of every possible execution path.

Expected outcome for this test path: the low-pressure and complete Standard BP
runs finish without capture loss, the pneumatic system is vented then sealed,
and the final stack report is not saturated with at least 1024 bytes free.
Simulator agreement is bench evidence only and is not clinical or ISO 81060-2
validation.
