# Connected PC1 Pressure Source comparison

## Purpose and fixture

Compare the prior 60 mmHg Pressure Source capture with PC1 isolated against
one non-human capture with PC1 in the pressure path. Keep the same real cuff
and established electrical supplies/common ground. The BP Pump 2 Pressure
Port, cuff, MPXV5050GP P1, and the already verified pressurized inlet of
PC1 valve2 must share the same line. P2 remains open to ambient. Retain
the verified three-way valve port mapping; do not infer ports from an old
schematic for a different valve. PC0 valve1 stays closed and PC8 pump
relay stays off. Do not connect a person. If tubing was moved, verify
unpowered continuity/shorts and physical port identity, then check the
established supply and logic voltages before powered operation.

The user reported the fixture and BP Pressure Source 60 mmHg setup ready.
Do not start `loaded-pulse-connected` until fresh
serial pressure is stable in 40-80 mmHg and the device pin/calibration/
ADS/fault gates pass. The host can now be armed at verified zero pressure
before the BP panel START and wait up to 90 seconds for the stable window.
A panel setpoint alone is not the measured pressure.
The operator's reported 74 mmHg was an earlier peak, not a synchronized
comparison with the host's later 54.4 mmHg reading. The rejected run log
began at 55.3 mmHg and declined to 54.3 mmHg over 5.417 s before the
diagnostic command, about 11.08 mmHg/min, consistent with the separately
reported leakage. The rapid peak-to-baseline transition was not captured;
do not label it a calibration error from these asynchronous readings.

## One-run procedure and acceptance

The current firmware image `LOADED_PULSE_RESET_20261029` was built with
0 errors/warnings, downloaded, and its 82.326/-19.887 Flash calibration
restored and read back. `tmp/linkpad_capture_io.py loaded-pulse-connected
--firmware LOADED_PULSE_RESET_20261029` uses the firmware's one-second
sealed baseline, three-second 5 ms/200 ms PC1 pulse diagnostic, 40 Hz
sampling, 20-85 mmHg pressure abort, ADS/overflow vent, and pump-off
start gate. On normal completion firmware opens PC1. In this fixture,
that valve should unload the BP/sensor/cuff line; the host sends `vent`,
requires ten fresh post-vent samples within +/-2 mmHg, immediately sends
`seal`, confirms PC0/PC1 LOW and PC8 HIGH, and checks 40 fresh post-seal
samples in [-2,+1] mmHg. It retries vent/zero/seal once on rebound;
continued rebound invalidates export. A stable closeout then exports the
uncalculated `/3` capture. On a failed gate or timeout, no capture may
be interpreted; keep the vent open if fresh zero cannot be verified.
The BP Pump 2 will usually stop once the external line unloads. Check its
panel only if pressure does not return near zero or the next run cannot
begin. No routine panel Stop request is needed for a successful vent.

The first attempted connected run was rejected by the old firmware:
preflight was about 54.4 mmHg, but `loaded pulse` required state IDLE,
while the previous `stop` left EMERGENCY/USER_STOP latched. No capture
was started. Host cleanup vented and sealed, but pressure rebounded to
about 6 mmHg; a further vent gave 100 fresh 0.0 samples, followed by
100 fresh 0.0 after sealing. The firmware now allows the diagnostic to
clear only a previous USER_STOP when all existing calibrated pressure,
ADS, pump and sealed-pin gates pass. Other emergency faults still reject.

Current firmware build: Code 51828, RO 7404, RW 28, ZI 63444; Keil 0
errors/0 warnings. Static RAM 63472/65536, headroom 2064 B; known
stack peak 1344 B with 4096 B reserved. HEX SHA-256
`991CF138DF2DBAFDBE77C20D9CC512E151F95B6CFE268CEB125DB9B25B0B4B76`.
The image was downloaded only after 100 fresh 0.0 mmHg samples, sealed
pins, pump OFF, valid calibration/ADS; full-chip erase produced expected
UNCAL. The original 82.326/-19.887 record was restored and independently
read back VALID. Final preflight showed IDLE, fault NONE, ADS ONLINE,
PC0/PC1 LOW, PC8 HIGH, pump OFF, 102 fresh 0.0 mmHg samples and runtime
stack free2680 B. Firmware host suite: 105 tests passed; bridge suite:
10 passed including connected normal, ADS failure and post-seal rebound.
The connected loaded-pressure capture is still pending.

The second connected attempt did not enter the pulse diagnostic: the fresh
serial pressure peaked at 73.5 mmHg, then fell too quickly for the original
40-sample / 1.5 mmHg stability gate (63.3 to 61.4 mmHg in its final two
seconds). It was vented to fresh 0.0 mmHg and sealed; 100 subsequent fresh
samples remained 0.0 mmHg. The connected host now allows up to 90 seconds
for the 40-sample window to settle, including when armed at zero before
panel START. It still requires 40-80 mmHg, no more than
1.5 mmHg span, fresh readings and an 85 mmHg preflight ceiling. The
connected normal and exception paths share vent, ten fresh near-zero
samples, seal, pin check and 40 fresh post-seal near-zero samples. A single
post-seal rebound triggers one repeat; a second leaves the vent open and
invalidates export. Offline bridge checks: 12 passed, including peak
settling and timeout without a pulse or stop command.

On the next operator START message, a five-second bridge snapshot contained
100 fresh 0.0 mmHg samples; a later three-second snapshot contained 61 more
at 0.0 mmHg. Read-only preflight then confirmed 101 fresh zero readings,
VALID calibration 82.326/-19.89, ADS ONLINE/errors0, old USER_STOP,
PC0/PC1 LOW, PC8 HIGH, pump OFF and runtime stack free2680 B. No connected
pulse command or capture was sent in this round because the pressure window
had already ended. The next BP Pressure Source start must occur after the
host is ready to run the connected capture.

After a complete capture, use `bp_loaded_pulse_audit.py` with the recorded
last MCU valve tick. Compare baseline drift, eight valve phase bins, and
step sizes against the isolated PC1 run. One pressure sensor cannot by
itself isolate valve mechanics, BP source control, tubing compliance, or
pressure-dependent sensing. No BP accuracy or human-use conclusion follows.

## Connected run and interpretation

The next armed run started the diagnostic only after the fresh serial
40-sample pressure window stabilized at 55.8 mmHg. Firmware
`LOADED_PULSE_RESET_20261029` completed 15 pulses and 160 samples over
3974 ms, dropped0, `calc=0`. Strict `/3` export succeeded. Verified file:
`tmp/capture_loaded-pulse-connected_20261029-222316.ndjson`, SHA-256
`5CA1D36B982692960C174416085F7A6FE14B24579FA43EE3DFBE6E8404F7B402`;
last MCU pulse tick `1618296`. The export records two >=5 mmHg drops at
sample indices 80 and 104, each 21 ms after an actual valve command.

The first seal after vent was followed by pressure rebound, so the host
repeated vent/ten fresh near-zero samples/seal/pin check. The second
40-sample post-seal window passed. A later independent 120-sample, six-second
snapshot was stable at 0.9-1.0 mmHg; PC0 and PC1 were confirmed LOW and
PC8 HIGH before export. No panel Stop was needed.

The connected one-second sealed baseline fell 55.5303 to 55.0475 mmHg,
fitted -29.79 mmHg/min. Its three-second pulse interval fell 54.7209 to
36.7434 mmHg (-17.98 mmHg), fitted -383.33 mmHg/min. Each of the 15
0-24 ms phase samples had a large pressure fall (median -4.23, minimum
-5.45 mmHg), followed by a 25-49 ms rebound (median +3.12 mmHg). The
sensor-voltage-equivalent changes match the pressure changes. In the
prior PC1-isolated capture, the sealed baseline fitted -10.95 mmHg/min,
the full pulse interval fell only 0.43 mmHg, and the largest phase-bin
adjacent fall was 0.043 mmHg. At the connected baseline rate, passive
loss over three seconds would be about 1.5 mmHg, far below the observed
17.98 mmHg.

The phase-locked, connection-dependent change demonstrates a real effect
in the sensed pressure/voltage chain during PC1 actuation. It weighs
against a display-only or envelope-algorithm artifact and supports a
pneumatic transient in this fixture. One sensor at 25 ms intervals cannot
resolve the actual 5 ms opening or independently separate valve-port
mechanics, line compliance, BP source behavior and sensing dynamics. This
is diagnostic evidence, not a BP accuracy result or human-use validation.

## Next comparison: 1-4 ms PC1 opening

The new `LOADED_PULSE_WIDTH_20261029` image keeps the original 5 ms loaded
command and adds fixed `loaded pulse 1` through `loaded pulse 4`. The
non-human fixture stays as verified: BP Pump 2 Pressure Source Pressure Port,
real cuff, MPXV5050GP P1 and PC1 pressurized inlet share the line; P2 is
open to ambient. STM32 PC1 drives the vent valve, PC0 stays LOW (inflation
valve closed), PC8 stays HIGH (internal pump relay off), I2C1 PB6/PB7 reads
the ADS1115 at 0x48, and USART3/CH340 carries the serial stream. Preserve
the previously verified supplies, logic levels, polarity and common ground;
no person is connected. If any harness changes, disconnect power and check
port identity, continuity and shorts first, then power up and measure the
documented module rails before operating. Incorrect polarity or power
connection can damage the modules.

Keil `UV4 -r` rebuilt the existing uvprojx with 0 errors/0 warnings:
Code52028, RO7460, RW32, ZI63440. `main.c` is already registered in
the uvprojx; no new C or assembly file was added. Static RAM use is
63472/65536 B, headroom 2064 B; known stack peak1344 B plus 1024 B
reserve fits the 4096 B allocation. Host suite: 105 passed; bridge suite:
13 passed. HEX SHA-256 is
`47E60051EC414BE56AB90CD6AE9534CBD60CE8A99EFC189981C2793F99D4FE35`.
This is a built artifact, not yet downloaded or runtime-validated.

Before Keil `UV4 -f` download, require no person, fresh serial near-zero
pressure, PC0/PC1 LOW, PC8 HIGH, pump OFF, ADS ONLINE/errors0 and valid
current calibration. The Keil download may erase Flash calibration; if
the new image reports UNCAL, restore only `cal write 82.326 -19.887` and
read back VALID 82.326/-19.89 before any pressure test. With BP Pressure
Source set to 60 mmHg, arm one
`python tmp/linkpad_capture_io.py loaded-pulse-connected --pulse-ms 1
--firmware LOADED_PULSE_WIDTH_20261029` and press BP START after host
preflight. Repeat as separate rounds with widths 2, 3 and 4 only after
vent, ten fresh near-zero readings, immediate seal, 40 fresh post-seal
near-zero readings and a new preflight. The host waits for a stable fresh
40-80 mmHg window; pressure outside 20-85 mmHg, ADS failure or capture
overflow invalidates the round. A successful `/3` export should contain
about 160 25 ms samples, 12-16 pulses, `calc=0`, the matching fixed
`on_min=on_max`, no dropped samples and a complete end hash. Use the
recorded last MCU pulse tick with `bp_loaded_pulse_audit.py`; compare
each round's 1 s sealed baseline slope, 3 s net pressure loss, 0-24 ms
fall and 25-49 ms rebound against the connected 5 ms reference. One
sensor and 25 ms sampling cannot resolve the mechanical 1-4 ms opening.

The new image was downloaded through Keil `UV4 -f` after 101 fresh
0.0 mmHg samples, IDLE/fault NONE, ADS ONLINE/errors0, PC0/PC1 LOW,
PC8 HIGH and pump OFF. Flash log reports Full Chip Erase, Programming
Done, Verify OK and application running. The expected UNCAL state was
observed; `cal write 82.326 -19.887` was sent and an independent `cal`
readback reported VALID 82.326/-19.89. A further 101-sample zero-pressure
preflight passed with safe pins and runtime stack free2680 B.

The first armed 1 ms host attempt (`tmp/capture_loaded-pulse-connected_
20261029-224146.ndjson`) saw no stable 40-80 mmHg window within 90 s.
It timed out before sending `loaded pulse 1`, so there is no pulse capture
or width result from this attempt. Host cleanup vented to fresh near-zero,
sealed and confirmed PC0/PC1 LOW and pump OFF; a separate five-second
snapshot then contained 100 fresh 0.0 mmHg samples. No panel Stop was
needed. Widths 1-4 remain to be measured in separate BP START rounds.

The subsequent 1 ms round completed: fresh stable starting gate 59.0 mmHg,
15 pulses, 160 samples over 3974 ms, dropped0, `calc=0`, strict `/3`
end hash valid, valve `on_min=on_max=1`. File:
`tmp/capture_loaded-pulse-connected_20261029-224655.ndjson`, SHA-256
`1902BC021E52D8A567237902FE93C3F313C1E5DF612F7A45DC1981E07417A499`;
last MCU pulse tick `420547`. Sealed baseline fell 58.6401 to 58.1147
mmHg in 974 ms, fitted -33.01 mmHg/min. The 3 s pulse interval fell
58.1005 to 56.8651 mmHg (-1.24 mmHg), fitted -24.97 mmHg/min.
The 0-24 ms valve phase had median adjacent change -0.014 mmHg and
minimum -0.028 mmHg, with matching voltage-equivalent changes; the valve
aggregate recorded no >=5 mmHg steps. The first seal after vent was
followed by a small rebound; the host repeated vent/zero/seal and passed
its 40-sample post-seal gate. A later independent 120-sample window was
stable at 0.9 mmHg. This one round strongly differs from the connected
5 ms reference, but does not establish the actual mechanical valve open
duration or a general operating setting. Widths 2-4 remain pending.

The 2 ms round completed separately: stable starting gate 59.3 mmHg,
15 pulses, 160 samples over 3974 ms, dropped0, `calc=0`, complete `/3`
hash and valve `on_min=on_max=2`. File:
`tmp/capture_loaded-pulse-connected_20261029-224904.ndjson`, SHA-256
`7F268F8868E299371269820F6DDAF4B4329B375AD751EEE8F7BCAB71F2574C91`;
last MCU pulse tick `571245`. Sealed baseline fell 58.9383 to 58.4271
mmHg in 974 ms, fitted -32.27 mmHg/min. The 3 s pulse interval fell
58.4129 to 57.1349 mmHg (-1.28 mmHg), fitted -25.48 mmHg/min.
The 0-24 ms phase median adjacent pressure change was -0.014 mmHg,
minimum -0.028 mmHg, matching sensor-voltage-equivalent changes; no
>=5 mmHg step was recorded. Cleanup repeated vent/zero/seal once after
a small post-seal rebound, then passed the fresh near-zero gate; an
independent 120-sample snapshot remained 1.0 mmHg. The 1 and 2 ms
results are close under this fixture, but 3 and 4 ms are still pending.

The 3 ms round then completed after a fresh 40-80 mmHg gate at about
60.5 mmHg: 15 pulses, 160 samples over 3974 ms, dropped0, `calc=0`,
strict `/3` export and `on_min=on_max=3`. File:
`tmp/capture_loaded-pulse-connected_20261029-225055.ndjson`, SHA-256
`94ABAAAA56609A90C699C4701F93CBF5C3A2F930A3B025989AF7F01D45A16E02`;
last MCU pulse tick `672543`. The sealed baseline fell 60.4862 to
59.9891 mmHg in 974 ms (fitted -30.85 mmHg/min). The 3 s pulse interval
fell 59.9465 to 57.9159 mmHg, a -2.0306 mmHg change (fitted
-41.81 mmHg/min). The 0-24 ms phase median was -0.1136 mmHg and its
minimum was -0.3550 mmHg; the voltage-equivalent values matched and no
phase aggregate reached a 5 mmHg step. The host completed vent, fresh
zero confirmation and seal; a later 5 s snapshot contained 100 fresh
0.0 mmHg samples.

The 4 ms round completed after a fresh gate at about 61.9 mmHg: 15 pulses,
160 samples over 3974 ms, dropped0, `calc=0`, strict `/3` export and
`on_min=on_max=4`. File:
`tmp/capture_loaded-pulse-connected_20261029-225402.ndjson`, SHA-256
`99F79BCB2C17D046DC74071AC9B7238E3B87FC2C1F6894411F580D63E520C86C`;
last MCU pulse tick `844894`. The sealed baseline fell 61.6222 to
61.1252 mmHg in 974 ms (fitted -30.15 mmHg/min). The 3 s pulse interval
fell 60.8980 to 51.1424 mmHg, a -9.7555 mmHg change (fitted
-214.25 mmHg/min). The 0-24 ms phase median was -2.2294 mmHg and its
minimum was -2.3856 mmHg, followed by a 25-49 ms rebound median of
1.5478 mmHg; voltage-equivalent values matched. No aggregate phase bin
reached a 5 mmHg step. The host completed the required vent, fresh-zero
and seal sequence; the independent post-seal snapshot initially showed
1.3-1.4 mmHg, so it vented again, confirmed 101 fresh 0.0 mmHg samples,
then sealed and passed a final zero preflight.

Across the connected fixture, the 1/2/3/4 ms pulse-interval losses were
approximately -1.24/-1.28/-2.03/-9.76 mmHg, compared with -17.98 mmHg
for the earlier 5 ms reference. The 0-24 ms medians were
-0.014/-0.014/-0.114/-2.229 mmHg. These single-round observations show
a width-dependent pressure transient in this particular sensed pneumatic
chain; 4 ms produced a materially larger response than 1-3 ms here. It does
not identify the physical opening time or distinguish valve, tubing,
BP source and compliance, because the only pressure channel is sampled
every 25 ms. It also does not establish clinical accuracy or a human-use
setting.

A repeat 3 ms round was acquired to check reproducibility. The stable gate
was 59.7 mmHg; the export again contained 15 pulses, 160 points over
3974 ms, dropped0, `calc=0`, and `on_min=on_max=3`. File:
`tmp/capture_loaded-pulse-connected_20261029-230049.ndjson`, SHA-256
`D0C102CADE03B6243E442D35A413F3F46D27EB3823B85D9F9CE499614A70071C`;
last MCU pulse tick `1268394`. The sealed baseline fell 59.7051 to
59.2081 mmHg (fitted -30.58 mmHg/min), while the pulse interval fell
59.1939 to 57.7313 mmHg (fitted -29.99 mmHg/min). The 0-24 ms median
was -0.0426 mmHg, minimum -0.0568 mmHg, with matching voltage-equivalent
values and no aggregate step. Thus the prior 3 ms -2.03 mmHg interval
loss was not reproduced; at this pressure and fixture, 3 ms did not add a
stable measurable deflation rate over the passive loss. After closeout the
fresh snapshot briefly showed 1.4-1.5 mmHg, so `vent` was repeated,
100 fresh 0.0 mmHg samples were confirmed, and `seal` was sent again.

The current evidence supports treating 4 ms and 5 ms as pressure-disturbing
settings in this fixture, while 1-3 ms have not shown a stable useful
continuous-deflation rate. Do not select a clinical pulse width from this
comparison; the next engineering test should measure the complete closed-loop
deflation slope with the real `deflate` controller and a fresh non-human
pressure source, rather than infer it from the loaded diagnostic pulses.

## 2026-10-30 `deflate test` closeout and retained export

The previously armed non-human `deflate test` was observed on the same
continuous bridge connection. The fresh starting pressure was about
56.8-57.4 mmHg. The pressure then fell to about 1 mmHg after the diagnostic
run; the initial short-connection listener missed the firmware completion line.
The retained capture itself is complete and was exported again only after
`vent`, ten fresh near-zero samples, and `seal` on the same connection.

Exact capture file: `tmp/capture_export_20261030-final.ndjson`, SHA-256
`0A5ADA0E57F86617815725FC73C8566C16BFD6638A9BBB7BA06AB311EAA5A021`.
Strict `bp.capture/3` decode passed: `n=400`, `dropped=0`, nominal and actual
intervals `25..25 ms`, duration `9975 ms`, raw kind `2`, calibration valid,
`pulses=50`, period `200..200 ms`, `on_min=1`, `on_max=4`, `steps=0`, and end
FNV hash `1646158123`. The exported pressure span was `55.6297 -> 54.0251
mmHg`; no aggregate >=5 mmHg pressure step was recorded.

Because the exported last pressure remained above the 45 mmHg floor and the
capture lasted the 10 s maximum (`400` points), this round is consistent with
`reason=timeout`; the direct `[DeflateTest] done ...` line was not captured, so
that reason remains an evidence-based inference rather than a directly logged
field. The final `pins` readback was `PC0=LOW PC1=LOW PC8=HIGH pump=OFF` and
fresh pressure samples were `0.0 mmHg`. `status` still reported
`state=EMERGENCY`, which is the retained safety latch from the prior run;
`vent`/`seal` close the pneumatic path but do not reset that state. No
additional inflation or firmware change was made.

## 2026-10-30 repeated `deflate test` with direct completion log

After an MCU reset, the preflight passed with `state=IDLE`, `cal=VALID`,
`ads=ONLINE`, `fault=NONE`, sealed pins, and 40 fresh samples at
`53.9..54.1 mmHg`. On the same continuous connection the firmware reported:

```text
[DeflateTest] started target=2.0mmHg/s max_on=4ms period=200ms max_duration=10s stop=45mmHg
[DeflateTest] done reason=timeout pulses=50 last_tick=142560 on=4ms; PC1=HIGH venting
```

The retained export is `tmp/deflate_test_connected_20261030.ndjson`, SHA-256
`393A2204CDF1F27031C910188868F78D0DB5E48F4C5B45B4119C698EA8C83633`.
Strict `/3` decode passed: 400 points, 9975 ms, exact 25 ms cadence,
`dropped=0`, 50 pulses at 200 ms, `on_min=1`, `on_max=4`, `steps=0`, end hash
`3814808897`. The pressure fell from `53.9115` to `47.0528 mmHg`, a total
loss of `6.8587 mmHg` and mean `0.688 mmHg/s`. Ten 1 s windows showed the
rate increasing from about `0.10` to about `1.03 mmHg/s`; the final width was
already the 4 ms safety limit. The test therefore timed out above the 45 mmHg
floor, with no >=5 mmHg pressure step.

This is a bounded control/fixture finding, not a clinical result. The current
firmware target is 2.0 mmHg/s, but this connected pneumatic chain produced
only about 1.0 mmHg/s near the 4 ms cap. The result does not yet distinguish
valve flow, tubing/compliance, BP source behavior, or the conservative software
cap. The round was closed with `vent` -> fresh near-zero samples -> `seal`;
post-closeout status returned to `IDLE` and pins were `PC0=LOW PC1=LOW
PC8=HIGH pump=OFF`.

## 2026-10-30 repeated-round comparison

A second same-setting round was completed after a fresh 40-80 mmHg gate
(`54.3..54.6 mmHg`). It again reported
`[DeflateTest] done reason=timeout pulses=50 ... on=4ms`, and the required
vent -> fresh near-zero -> seal closeout returned to `IDLE` with sealed safe
pins. The export `tmp/deflate_test_connected_20261030-repeat.ndjson` passed
strict `/3` decoding: 400 points, 9975 ms, exact 25 ms cadence, dropped0,
50 pulses, `on_min=1`, `on_max=4`, `steps=0`, end hash `2226652166`; SHA-256
`24D8CF31B3A3A840A5AB0E36391B3F6845D1A44575E620922C4743837DC415BB`.

The second pressure span was `54.2523 -> 52.1790 mmHg`, total loss
`2.0732 mmHg`, mean `0.208 mmHg/s`. Its ten 1 s windows stayed around
`0.18..0.25 mmHg/s`, unlike the first round's late `~1.0 mmHg/s`. Both rounds
used the same 50-pulse schedule and ended at the 4 ms cap, yet their rates
differed by more than 3x. This non-repeatability means the present evidence
does not justify an algorithm retune or a hardware verdict. The next useful
measurement is a sealed no-pulse baseline at the same BP source pressure,
followed by another deflate round, so passive source/fixture loss can be
separated from valve-induced loss.

## 2026-10-30 sealed baseline versus filtered deflate round

The planned separation measurement was completed with the same non-human
Pressure Source fixture and the source set near 60 mmHg. With valve 2 sealed
and no `deflate test` command, a 10 s bridge watch recorded approximately
`57.8 -> 56.2 mmHg` over `9.998 s`, or `0.160 mmHg/s` passive loss. The
source was then allowed to settle again at about `58.5..59.4 mmHg` before the
active round.

A same-connection filtered listener (`tmp/deflate_probe_live.py`) sent
`deflate test` and retained only key event lines and pressure samples. It
captured:

```text
[DeflateTest] started target=2.0mmHg/s max_on=4ms period=200ms max_duration=10s stop=45mmHg
[DeflateTest] done reason=floor pulses=49 last_tick=1010483 on=4ms; PC1=HIGH venting
```

The active interval started at `55.3 mmHg`; the last sample before the done
line was `45.5 mmHg` at `9.598 s`, giving `9.8 mmHg` total loss or about
`1.02 mmHg/s`. The post-done vent samples fell to `0.8 mmHg` and are excluded
from that rate. Relative to the sealed baseline, the observed additional loss
was about `0.86 mmHg/s` at this fixture and pressure range. The two starts
differed by about `2.5 mmHg`, so this is a bounded engineering comparison,
not a pressure-matched characterization.

The round was closed with `vent`, 5 s of fresh `0.4 mmHg` samples, then
`seal`. This result shows that the 4 ms pulse schedule can add a measurable
deflation component above passive source/fixture loss in this run. It still
does not identify whether the added component is dominated by valve flow,
tubing/compliance, BP source behavior, or pressure-dependent sensing, and it
does not justify a clinical setting or an algorithm retune by itself.

## 2026-10-30 matched-start repeat

A second paired round used the same filtered listeners. The sealed 10 s
baseline was `54.2 -> 53.0 mmHg`, a `1.2 mmHg` loss or `0.120 mmHg/s`.
The immediately following `deflate test` started at `52.4 mmHg` and reached
`48.6 mmHg` immediately before the done line after `9.948 s`:

```text
[DeflateTest] done reason=timeout pulses=50 last_tick=1489498 on=4ms; PC1=HIGH venting
```

The active rate was about `0.38 mmHg/s`, giving an estimated pulse-related
addition of about `0.26 mmHg/s` above that round's passive baseline. This is
substantially below the previous paired round's estimated `0.86 mmHg/s`
addition, despite the same 4 ms limit and 50-pulse schedule. The difference
confirms that the current source/fixture is not repeatable enough to choose a
software width or infer a hardware fault. The round was closed with `vent`,
5 s of fresh `0.3..0.4 mmHg` samples, and `seal`.

## 2026-10-30 60 s sealed leak baseline

To separate long-term passive source/fixture loss from the valve effect, a
60 s sealed no-pulse listener was run at the same nominal 60 mmHg source
setting. It recorded `55.6 -> 50.2 mmHg` over `59.940 s`, a total loss of
`5.4 mmHg` or `0.090 mmHg/s` (`5.4 mmHg/min`). The run was then closed with
`vent`, 5 s of fresh `0.4..0.6 mmHg` samples, and `seal`.

This confirms a persistent passive leak/drift in the connected source and
fixture. It is far below the first paired active rate (`1.02 mmHg/s`) but is
large enough that short 10 s windows can bias the estimated pulse addition.
The next comparison should use a pressure-matched baseline immediately before
each active round, with the BP source and all fittings held unchanged.

## 2026-10-30 third paired repeat

With the source settled at `55.2..56.0 mmHg`, the sealed 10 s baseline was
`54.2 -> 52.7 mmHg` over `9.949 s`, or `0.151 mmHg/s`. The immediately
following filtered `deflate test` started at `52.2 mmHg` and reached `45.4
mmHg` before the done line after `7.599 s`:

```text
[DeflateTest] done reason=floor pulses=39 last_tick=2050798 on=4ms; PC1=HIGH venting
```

The active rate was about `0.90 mmHg/s`, giving an estimated pulse-related
addition of about `0.74 mmHg/s`. This is close to the first paired round
(`~0.86 mmHg/s`) but far above the second (`~0.26 mmHg/s`) at nearly the same
starting pressure. The three paired rounds therefore confirm a repeatability
problem in the pneumatic/source fixture; no software width or algorithm
change is justified. Closeout was `vent`, 5 s of fresh `0.4..0.5 mmHg`
samples, then `seal`.

## 2026-10-30 fourth paired repeat

After the previous closeout, the same non-human Pressure Source fixture was
returned to about 61 mmHg and allowed to settle. The sealed 10 s baseline was
`59.3 -> 57.9 mmHg` over `9.949 s`, a total loss of `1.4 mmHg` or
`0.141 mmHg/s`. The immediately following filtered `deflate test` started at
`56.6 mmHg` and reached `46.6 mmHg` immediately before its completion line:

```text
[DeflateTest] started target=2.0mmHg/s max_on=4ms period=200ms max_duration=10s stop=45mmHg
[DeflateTest] done reason=timeout pulses=50 last_tick=2564864 on=4ms; PC1=HIGH venting
```

The active interval lost about `10.0 mmHg` in 10 s, or approximately
`1.00 mmHg/s`. Relative to the adjacent sealed baseline, the estimated
pulse-related addition was therefore about `0.86 mmHg/s`. This agrees with the
first and third paired rounds and remains far above the second round's
`0.26 mmHg/s`, so fixture/source repeatability is still the dominant unresolved
factor. No firmware or algorithm change is justified from this dataset.

The round was closed with fresh near-zero samples (`0.4..0.5 mmHg`) followed by
`seal`; no human contact was used.

## 2026-10-30 BP Pump External Leak Test

Using the BP Pump 2 Pressure Leak Test with the existing non-human External
fixture, the test began measuring at approximately `55 mmHg` and reported
`6.0 mmHg/min` after 60 seconds. This agrees with the independent sealed
baseline of `5.4 mmHg/min` (`55.6 -> 50.2 mmHg` in 59.940 s), confirming that
the observed low-pressure passive decline is a real total leak of the connected
BP Pump + tubing + cuff + DUT path rather than a serial-estimation artifact.

The result is a system leak figure, not a BP Pump-only or valve-only figure.
The next useful comparison is the same External configuration at a higher
setpoint (for example 150 mmHg) to quantify pressure dependence. Internal Adult
should only be used as a separate manual configuration or with a verified
closed pressure-port setup; it is not directly interchangeable with this
External result.

## 2026-10-30 BP Pump External Leak Test at high pressure

With the same non-human External configuration, the BP Pump Leak Test began at
approximately `139 mmHg` and reported `10 mmHg/min` after 60 seconds. Compared
with the `6.0 mmHg/min` result beginning near `55 mmHg`, the total connected
system leak increased by about 1.7x as pressure increased. This confirms a
pressure-dependent passive leak in the BP Pump + tubing + cuff + DUT chain.

The two points are sufficient to explain the observed faster high-pressure
decay, but they do not locate the leak. They also show that at the previous
~55-60 mmHg deflate tests, passive loss was roughly `0.10 mmHg/s`, much smaller
than the active valve-related loss. No algorithm or pulse-width change is
justified from this result.

## 2026-10-30 pneumatic-path clarification

The Leak Test rounds used the previously verified shared pressure line, not a
sensor-only branch: BP Pump 2 `Pressure Port`, the real non-human cuff,
MPXV5050GP P1, and the pressurized inlet of valve 2 (PC1) were all connected to
the same line. Valve 1 (PC0) stayed closed and the internal pump relay (PC8)
stayed off; P2 remained open to ambient. For the leak measurements, valve 2 was
also closed (`seal`), so the reported `6` and `10 mmHg/min` include the closed
valve-2 branch and its seat, as well as the BP Pump, tubing, cuff, sensor branch,
and other fittings.

This is still a valid total-system leak result. It must not be described as a
pressure-port-to-sensor-only measurement. Isolating valve-2 seat leakage would
require a separately verified way to remove and cap that branch; do not infer
the three-way valve ports from the old schematic.

## 2026-10-30 BP Pump and cuff-only External comparison

Following the proposed non-human comparison setup with the BP Pump 2 Pressure
Port connected directly to the same real cuff, without the DUT tee, sensor,
or valve branches, the operator reported these Pressure Leak Test results:

| Connected path | Start of 60 s interval | Panel leak rate |
| --- | ---: | ---: |
| BP Pump + cuff only | 139 mmHg | 6.0 mmHg/min |
| BP Pump + cuff only | 60 mmHg | 2.0 mmHg/min |
| BP Pump + cuff + DUT branches | 139 mmHg | 10 mmHg/min |
| BP Pump + cuff + DUT branches | about 55 mmHg | 6.0 mmHg/min |

The matched high-pressure comparison shows a 4 mmHg/min higher *displayed*
total-system leak rate after adding the DUT path. The low-pressure comparison
shows the same numerical difference, but its starting pressures differ by about
5 mmHg. These pressure-decay rates cannot be subtracted to obtain the valve's
own airflow or leak rate because the connected volume/compliance and fittings
change with the configuration. The result points to the added DUT path or its
connections as a contributor, without locating a specific valve or excluding
a reconnection effect. An A-B-A repeat with the original complete path and the
same cuff fixation is the next check before branch isolation.

## 2026-10-30 complete-path repeat after cuff-only comparison

After restoring the original connected non-human path, the operator reported a
Pressure Leak Test starting at `137 mmHg` and showing `12.0 mmHg/min` after
60 seconds. The earlier complete-path run started at `139 mmHg` and showed
`10 mmHg/min`; the BP Pump + cuff-only comparison at `139 mmHg` showed
`6.0 mmHg/min`. Thus both complete-path high-pressure runs showed higher
displayed pressure-decay rates than the cuff-only comparison, with 2 mmHg/min
variation between the two complete-path runs. This supports an added-path or
connection contribution, but it does not identify a particular valve or
permit direct subtraction as airflow because the configurations differ in
volume/compliance.

The live serial bridge still showed about `118 mmHg` after the panel result.
Firmware `vent` was sent, followed by 5 s of fresh `0.0..0.1 mmHg` samples;
`seal` was then sent and 3 s of fresh samples stayed at `0.0 mmHg`. No tubing
was moved while pressurized. Further branch isolation requires a verified
gas-tight cap and the previously verified valve-port mapping.

## 2026-10-30 syringe substituted for valve-2 branch

With the existing non-human cuff still connected, the operator replaced the
pressurized valve-2 branch endpoint with a syringe as a temporary closed end.
The BP Pump 2 External Pressure Leak Test began its 60 s interval at about
`56 mmHg` and displayed `5.0 mmHg/min`. This is below the earlier complete
path result of `6.0 mmHg/min` starting near `55 mmHg`, but still above the
BP Pump + cuff-only result of `2.0 mmHg/min` starting near `60 mmHg`.

The 1 mmHg/min displayed difference from the complete path is too small to
identify valve 2 as the main leak. The syringe seal, piston motion, and changed
gas volume/compliance are additional uncertainties. The live serial bridge
still showed `48.6..48.7 mmHg` after the panel result. Because valve 2 is
physically disconnected, firmware `vent` cannot unload this shared line;
use the BP Pump panel `VENT` and confirm both panel and fresh serial pressure
are near zero before moving any tubing. Do not increase test pressure with
this improvised syringe endpoint before its mechanical stability is verified.

The operator subsequently reported holding the syringe plunger by hand and
observing no visible movement during the test. This excludes obvious plunger
travel but does not verify syringe-tip or piston-seal leakage, and hand force
may change the effective compliance. Fresh serial samples first declined from
about `5.0` to `1.0 mmHg`, then held at `0.0 mmHg` for 5 seconds; firmware
`seal` was acknowledged after the zero check. No higher-pressure syringe test
was performed.

## 2026-10-30 syringe substituted for valve-1 branch

Following restoration of valve 2, the operator substituted the same syringe
for the pressurized valve-1 branch. BP Pump External Leak Test began its 60 s
interval near `56 mmHg` and displayed `5.0 mmHg/min`, the same panel rate as
the valve-2 substitution. The complete path had displayed `6.0 mmHg/min`
near `55 mmHg`, and BP Pump + cuff only `2.0 mmHg/min` near `60 mmHg`.
Neither single-branch substitution caused a large reduction in displayed
pressure decay. These observations do not isolate either valve's own leak,
because the syringe seal, hand-held plunger, joints, and gas compliance are
uncontrolled across configurations.

After the report, serial pressure was about `64 mmHg`. Firmware `vent` was
acknowledged; fresh samples then settled at `2.8..2.9 mmHg` for at least
15 seconds rather than reaching zero. Do not move tubing or send `seal` while
this residual pressure persists. BP Pump panel `VENT` is required for the
remaining closeout, followed by fresh serial near-zero confirmation and
`seal`. No further pressure test was started.

The operator subsequently used the BP Pump panel vent. A five-second bridge
snapshot then contained 100 fresh `est=0.0 mmHg` samples. Firmware `seal` was
sent through the bridge (`serial.write` acknowledged), and another 60 fresh
samples over three seconds remained at `est=0.0 mmHg`. The branch-isolation
round is now closed at zero pressure; the valve-1 branch remains substituted
by the syringe. The two single-valve substitutions each displayed
`5.0 mmHg/min` near `56 mmHg`, so neither identifies a dominant valve leak.

## 2026-10-30 sensor-and-cuff-only External comparison

The operator then measured a reduced path containing the BP Pump Pressure
Port, the same real cuff, and MPXV5050GP P1, with the valve branches removed.
The External Leak Test began near `55 mmHg` and displayed `5.0 mmHg/min` after
60 seconds. This is lower than the earlier complete path at a similar pressure
(`6.0 mmHg/min` near `55 mmHg`), but it is not lower than the cuff-only result
near `60 mmHg` (`2.0 mmHg/min`). The remaining difference may be from the
sensor branch or reconnection/volume effects; it does not by itself prove a
sensor fitting leak. The pressure must be released with the BP panel `VENT`
because neither valve is currently in this path, then confirmed near zero
before reconnecting any branch.

The operator used the BP panel `VENT`. A subsequent five-second bridge
snapshot contained 100 fresh readings at `est=0.0..0.1 mmHg`; the reduced
pressure path is depressurized. The next comparison is a BP Pump + cuff-only
repeat beginning near `55 mmHg`, to see whether the earlier `2.0 mmHg/min`
baseline reproduces after reconnection. No valve command can vent the currently
isolated BP/cuff/sensor line.

The BP Pump + cuff-only repeat began near `58 mmHg` and displayed
`5.0 mmHg/min` after 60 seconds, rather than the earlier cuff-only
`2.0 mmHg/min` near `60 mmHg`. This now matches the sensor-and-cuff-only
`5.0 mmHg/min` near `55 mmHg`. The cuff-only baseline is not reproducible
across reconnections, so the sensor branch cannot be named as the leak source
from these comparisons. Keep the direct BP/cuff connection and cuff fixation
unchanged for an immediate same-pressure repeat after panel vent to zero.

Without moving the direct BP/cuff connection, the next External Leak Test
began near `64 mmHg` and displayed `4.0 mmHg/min` after 60 seconds. The
same-connection repeats (`58/5.0` and `64/4.0`) differ by `1.0 mmHg/min`;
the earlier `60/2.0` result has not reproduced. Since the pressure was
higher in the lower-rate repeat, this change cannot be attributed simply
to pressure dependence. The cuff/pressure-port path and test setup therefore
have a variable baseline. The sensor-only result (`55/5.0`) is within that
baseline, so it provides no isolated evidence of a sensor-branch leak.
The full monitor path can still add pressure-dependent loss, especially at
higher pressure, but the current syringe substitutions and reconnections
cannot assign it to either valve. This External total-path rate must not be
compared with the BP Pump's internal `<2 mmHg/min` specification, which
requires the separately specified >=300 cc internal test setup.

With the same direct BP Pump + cuff connection retained, a high-pressure
External Leak Test began at `139 mmHg` and displayed `7.0 mmHg/min` after
60 seconds. The earlier direct-path test at `139 mmHg` displayed
`6.0 mmHg/min`; the complete-path high-pressure tests displayed
`10.0 mmHg/min` at `139 mmHg` and `12.0 mmHg/min` at `137 mmHg`. Thus the
direct high-pressure baseline reproduced within `1.0 mmHg/min`, while both
complete-path readings were higher. This supports an additional connected-
path or reconnection contribution at high pressure, but changed pneumatic
volume/compliance prevents interpreting the numerical rate difference as
the added branch's airflow. A high-pressure sensor-and-cuff-only comparison
without a syringe is the next discriminating test, after BP panel vent and
confirmed zero pressure before any tubing change.

The high-pressure sensor-and-cuff-only External test began at `144 mmHg` and
displayed `6.0 mmHg/min` after 60 seconds. This overlaps the direct BP/cuff
high-pressure readings of `6.0` and `7.0 mmHg/min` at `139 mmHg`, and is below
the complete-path readings of `10.0` and `12.0 mmHg/min` near `139 mmHg`.
Adding the sensor branch did not increase the displayed high-pressure decay
in this test. The remaining added path includes the valve branches and their
connectors, but the measurement does not distinguish valve seats from joints
or changing pneumatic compliance. A subsequent five-second serial snapshot
still showed 100 fresh `est=136.7..136.9 mmHg` samples. Because both valves
are disconnected from this pressure path, BP panel `VENT` and a fresh zero
check are required before any further plumbing change.

The operator then reported using the BP panel vent. The first five-second
bridge snapshot was `est=1.2..1.4 mmHg` over 101 fresh samples, followed by
an eight-second snapshot fixed at `1.8 mmHg` over 160 fresh samples. This did
not satisfy the earlier zero-pressure criterion. The small positive reading
may be retained pressure or sensor zero drift; the two cannot be separated
from this data. Keep the pressure path unchanged until the panel vent state
and a stable near-zero serial reading are checked.

The operator confirmed the BP panel displayed `0 mmHg`, vented the path to
atmosphere, and then restored a connection. A fresh five-second bridge
snapshot subsequently contained 100 `est=0.0 mmHg` samples. The earlier
`1.8 mmHg` reading therefore cleared after atmospheric venting; whether it
represented small trapped pressure or transient zero shift remains unknown.
The exact restored branch topology was not stated and must be confirmed
before further pressurization or valve actuation.

The operator clarified that the restored topology is `BP + cuff + MPXV5050GP
P1`, with no valve branch. A firmware `seal` command was acknowledged while
the fresh serial pressure was zero. The next planned isolation adds only the
previously verified pressurized inlet of valve 2, with valve 1 and the syringe
excluded; this must be done unpowered and only after confirming the panel is
at zero.

Fixture correction: the operator has only one tee, already occupied by BP,
cuff, and sensor P1. The four-way arrangement above cannot be built with that
tee. Do not substitute a hand-held syringe for the remaining branch at high
pressure. For a valve-2-only panel leak comparison, depressurize first and
replace the sensor P1 branch on that same tee with valve 2's previously
verified pressurized inlet: BP + cuff + valve 2 only. P1 is then open to
atmosphere and cannot monitor this test; use only the BP panel External Leak
Test and panel VENT, with firmware pump/valve diagnostics inactive. Confirm
valve-2 closed state after power-up and before pressurization. The comparison
is a total pressure-decay rate for a changed volume, not valve-seat airflow.

The BP + cuff + valve-2-only External Leak Test began near `57 mmHg` and
displayed `5.0 mmHg/min` after 60 seconds. This equals the recent direct
BP/cuff repeats (`58/5.0`, `64/4.0`) and is below the complete-path
`6.0 mmHg/min` near `55 mmHg`. With a closed valve-2 branch added, the
displayed low-pressure decay did not increase, so this test gives no evidence
that valve 2's seat is a dominant leak. Because P1 was vented to atmosphere,
no serial pressure data accompanies this reading. The next comparison is the
same configuration near `139 mmHg`, after panel vent and confirmed zero
pressure before any tubing change.

The same BP + cuff + valve-2-only configuration then began a high-pressure
External Leak Test at `140 mmHg` and displayed `6.0 mmHg/min` after 60 seconds.
This overlaps the direct BP/cuff results (`139/6.0`, `139/7.0`) and the
sensor-and-cuff result (`144/6.0`), while the complete path remained higher
(`139/10.0`, `137/12.0`). The closed valve-2 branch therefore shows no
measurable dominant contribution in either pressure range. The remaining
single-branch check is valve 1, using the same tee and volume conditions.

The BP + cuff + valve-1-only configuration then began a high-pressure External
Leak Test at `143 mmHg` and displayed `11.0 mmHg/min` after 60 seconds. This
is close to the complete-path results (`139/10.0`, `137/12.0`) and well above
the valve-2-only result (`140/6.0`) and the direct/sensor baselines near
`6.0..7.0`. The valve-1 branch, its connector, or its selected port is now
the leading contributor to the added high-pressure decay. The test cannot
separate a valve-seat leak from tubing/fitting leakage or pressure-dependent
compliance. A matched low-pressure valve-1-only run near `57 mmHg` is needed
before opening or replacing hardware; vent with the BP panel and confirm zero
before changing the tee.

The same BP + cuff + valve-1-only configuration began a low-pressure External
Leak Test at `58 mmHg` and displayed `4.0 mmHg/min` after 60 seconds. This is
within the recent direct BP/cuff results (`58/5.0`, `64/4.0`) and does not
show an added low-pressure loss. Together with `143/11.0` for valve 1 and
`140/6.0` for valve 2, the valve-1 configuration has a notably higher
high-pressure reading but similar low-pressure reading. This is consistent
with pressure-dependent loss somewhere in the valve-1 branch or its
connections, but one reading per pressure/configuration cannot distinguish
valve-seat leakage from fittings, changed volume/compliance, or run variation.
Do not claim a confirmed faulty valve or compute its leak rate by subtraction.

The BP + cuff + valve-1-only configuration was then repeated without changing
the tee or cuff fixation: a low-pressure External Leak Test began at `57 mmHg`
and displayed `4.0 mmHg/min`, and a high-pressure test began at `138 mmHg` and
displayed `12.0 mmHg/min`. These reproduce the earlier valve-1 readings
(`58/4.0`, `143/11.0`). The high-pressure excess over the valve-2-only
configuration (`140/6.0`) and the direct/sensor baselines (`6.0..7.0`) is
therefore repeatable and pressure-dependent, localized by elimination to the
valve-1 branch. The operator clarified that the valve-1 port connected in the
de-energized state has been capped throughout these tests. Earlier advice to
add a cap, or to leave that port open, was incorrect. The existing cap and its
joint are part of the tested branch. The results cannot distinguish leakage
at this cap, the valve body/seat, or the inlet tubing and fittings. No extra
cap or port swap is justified by these observations. First inspect the
existing cap and branch joints without pressure; any subsequent localization
test must retain the verified port mapping and non-human setup. All closeouts
after high-pressure runs must use BP panel `VENT` and confirmed zero before
touching tubing.

After checking the existing valve-1 cap, inlet tube, and tee connection without
changing the topology, the operator repeated the high-pressure External Leak
Test at `136 mmHg`; the displayed rate was still `12.0 mmHg/min`. This matches
the prior valve-1 results (`143/11.0`, `138/12.0`) and shows no improvement
from reseating/checking the external joints. The leading fault boundary is now
the valve-1 assembly or its capped port/seat behavior, but the cap seal itself
is not independently excluded. Do not continue high-pressure repeats without
a new isolation method; vent to panel zero before any tubing change.

The operator then replaced the original valve-1 de-energized-port cap with a
syringe at the same port. At `139 mmHg`, the External Leak Test displayed
`5.0 mmHg/min`, versus `11.0..12.0 mmHg/min` with the original cap and
`6.0..7.0 mmHg/min` for the direct/sensor/valve-2 baselines. This A/B change
strongly implicates the original cap or its joint as the dominant high-pressure
leak contribution, assuming the syringe tip remained sealed and its plunger
did not move. It argues against the valve-1 body being the main leak. The
syringe interface and hand force remain uncontrolled, so this is provisional;
confirm with a verified gas-tight cap or a second independent plug before
declaring the cap defective. Vent with the BP panel before replacing the
temporary syringe.

The syringe-substituted valve-1 branch was repeated at high pressure: the
External Leak Test began at `145 mmHg` and displayed `4.0 mmHg/min`, matching
the previous syringe result (`139/5.0`) and the direct-path baseline. Two
independent syringe runs therefore remove the original cap's `11.0..12.0`
mmHg/min excess while leaving the valve body unchanged. The cap or its joint
is now the leading leak source with substantially stronger evidence; the
remaining uncertainty is syringe-tip sealing, piston compliance, and changed
volume. Use a verified gas-tight replacement cap for confirmation rather than
continuing high-pressure tests with a hand-held syringe. Vent to panel zero
before replacing the temporary endpoint.

After the syringe run, a five-second bridge snapshot contained 100 fresh
`est=0.0 mmHg` samples, confirming that the shared line was depressurized
before any endpoint change. No verified replacement cap is currently
available, so the cap-versus-valve distinction remains provisional and no
further hand-held-syringe high-pressure repeat is recommended.

The original valve-1 cap was then restored. A high-pressure External Leak Test
began at `138 mmHg` and displayed `14.0 mmHg/min`, higher than the earlier
original-cap results (`136/12.0`, `138/12.0`, `143/11.0`) and far above the
same-port syringe substitutions (`139/5.0`, `145/4.0`). Restoring the cap
therefore reproduces a large high-pressure excess and strengthens the
conclusion that the original cap or its interface is the dominant leak source
in this setup. This remains a system-level A/B result rather than a certified
cap leak-rate measurement; the valve body was not independently isolated.
Do not continue high-pressure testing with this cap. Vent with the BP panel,
confirm fresh serial pressure near zero, and leave the branch disconnected or
use the syringe only as a temporary, non-certified endpoint until a verified
gas-tight replacement cap is available.

## 2026-10-31 replacement cap confirms the original cap leak

With a new replacement cap installed on the same valve-1 de-energized port,
the External Leak Test began at `142 mmHg` and displayed `7.0 mmHg/min` after
60 seconds. This matches the direct/sensor/valve-2 baseline (`6.0..7.0`), the
provisional syringe results (`139/5.0`, `145/4.0`), and is far below the
original-cap results (`136/12.0`, `138/12.0`, `143/11.0`, `138/14.0`). With
the volume/compliance caveats, this A/B sequence identifies the original cap
or its interface as the dominant high-pressure leak and shows no significant
valve-1 body contribution. The measured rates are total system-decay figures,
not a certified cap airflow specification. The complete-path high-pressure
readings (`139/10.0`, `137/12.0`) should be re-checked after this replacement
before attributing them to hardware; today's leak tests used no human subject.

With the new cap kept in place and the full connected path restored, the
External Leak Test began at `136 mmHg` and displayed `8.0 mmHg/min` after
60 seconds, below the earlier complete-path readings (`139/10.0`,
`137/12.0`) and close to the direct-path baseline. A five-second bridge
snapshot afterwards showed 100 fresh samples at `est=127.9..128.3 mmHg`,
confirming the path was still pressurized; BP panel `VENT` and fresh serial
near-zero confirmation are required before any tubing change. The remaining
`1.0..2.0 mmHg/min` excess over single-branch baselines may come from the
added DUT branches, reconnection effects, or run variation; it does not
localize a specific leak and no firmware or algorithm change follows.

After the complete-path run, BP panel venting was followed by 100 fresh serial
samples at `est=0.8..0.9 mmHg`. Firmware `seal` was acknowledged, and a further
60 fresh samples remained at `est=1.1..1.2 mmHg`, with no material rebound.
The new cap therefore passed the immediate closeout check; the connected
system remains characterized by about `8.0 mmHg/min` at `136 mmHg` in this
round, and the original-cap leak is considered resolved for the current setup.
