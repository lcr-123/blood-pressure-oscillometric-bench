# Implementation Plan

## Controlled peak-window deflation comparison (2026-11-05)

- [x] Add guarded profile selector; keep power-on normal and fixed200..245/1.8.
- [x] Actual-C selector/gate tests, full159-test suite, Keil0/0 and RAM/stack.
- [x] Verify new HEX download, calibration restore/readback and zero-pulse trace.
- [x] Retain one normal and one peak trial; same-source production-C replay.
- [x] Compare frozen beat support, all origins, deletion sensitivity and phases.
- [x] Restore normal/target50, re-vent after export rebound,15s sealed zero check.
- [x] Save reports/source snapshots and update specs/project notes/journal.

Evidence: `data/reports/standard_bp_peakwindow_comparison_20261105.{json,md,png}`.
Fixed-band beats20->28, measured OLS slope2.916->2.354 (requested1.8 not met),
all-origin peak span27.5->10mmHg, one-trial stability reject->pass. Both original
firmware BP calculations failed; high50% crossing absent. No BP accuracy claim.
Final `peakwindow_final_20261105-123717` passed vent/freshzero/seal +15s sealed
observation at displayed0, safe pins/faultNONE. Archive SHA256
d5cd464918e215d6f660f962ddc8e68339c9833fee16b6fafd082840585ffaf6.
Next: repeated frozen-profile evidence; do not widen target or tune labels.

User OK covers increasing beat support after exact valve timing validation.
Keep normal mode as power-on default. Add explicit `profile normal|peak` plus
read-only `profile`; writes require fresh calibrated sealed zero with no active
capture/export/calculation. Peak profile only applies at inflation target>=200:
fixed 200..245mmHg window targets1.8mmHg/s, outside stays3.0; lower targets and
deflate diagnostic remain unchanged. Window covers the prior212.5..230 peaks
and is declared before observing the new comparison; no panel labels used.
Nominal275->15 takes86.7s at3.0; window adds10s =>96.7s/3867points versus4200
capacity. This is a planning estimate, not a worst-case guarantee. Keep overflow
abort,278host/280firmware ceilings,2s freshness and130s active deadline. One
baseline then one profile trial; preserve failures. Host records profile command,
readback, firmware ID and fixed window in raw metadata; restore normal/target50
at verified closeout. Schema4 waveform/edges and extraction gates are unchanged.
Run real-C selector and profile gate regressions, full suite, Keil/RAM/stack,
verified download and zero pulse before profile inflation. Independent dynamic
pressure accuracy and causal source of ringing remain unverified.


## Synchronous valve timing execution (2026-11-05)

- [x] Add bounded exact open/close trace and cancellation integration.
- [x] Export schema4; strict decoder keeps schema1/2/3 compatibility.
- [x] Test actual C edge timing, wrap, overflow, cancellation and protocol errors.
- [x] Run full suite and Keil rebuild/RAM/stack gates; safe authorized download.
- [x] Record actual hardware evidence and next peak-region comparison limits.

## 2026-11-05 peak instability localization execution

- [x] Add offline bin-margin/contribution and fixed-beat deletion diagnostics.
- [x] Verify all manifest hashes, preserve failures, compare all 8 complete runs.
- [x] Test sharp/flat peaks, single-beat effects, absent valve phase and invalid input.
- [x] Emit reproducible JSON/Markdown/plot, inspect plot and run required tests.
- [x] Record evidence boundaries and next physical experiment in spec/journal.

Results: target275 height leading-bin margins0.36..2.49%,3..4 beats per peak
bin;11/73 deletions alter at least one origin's height/area peak. All deletion
outcomes retained:62 bin-origin unstable,7 gate-failed,4 pass. Passing deletions
are not corrections. No change to original stability/inference decisions.
Physical source remains unresolved: all8 complete valve aggregates show200ms
period and no >=5mmHg steps, but lack a full pulse-event time reference.

Full suite153/153 passed; after adding output overwrite regression, current
diagnostic suite8/8 passed (7 overlap,154 unique current tests covered). Final
report/code reproduction and unchanged prior adaptive/diagnostic reports are
verified in matching validation JSON. Final reviewed plot visually checked.
Artifacts: data/reports/standard_bp_peak_instability_20261105_reviewed.{json,md,png}
and .validation.json. Earlier same-day preliminary diagnostic outputs retained;
reviewed prefix is the final reference. No device I/O, C/header/uvprojx edit,
Keil/flash/calibration action, staging, initial commit or task archive.
Next experiment requires implementing/validating synchronized valve event
logging and controlled peak-region windows before another pneumatic run.

## 2026-11-05 capacity repair execution

- [ ] Freeze legacy result C; implement4200 single-array/ring smoothing and
  cooperative FFT fallback, preserving bitwise output and cancellation.
- [ ] Extend real-C host/decoder/export tests through4200 and overflow4201;
  compare old250 capture through production-C replay; full host suite.
- [ ] Keil rebuild0 errors/warnings, source registration, RAM>=2048 and
  static stack+1024<=4096 gate; lock image/version before authorized download.
- [ ] Fresh safety preflight, download/verify, conditional calibration restore;
  one Preset4/0.55cc target275 trial with130s deadline, stable closeout/target50.
- [ ] Strict decode/replay and upper-tail comparison if complete; retain failure
  otherwise, report runtime timing/stack, wiring and reproducible steps.

## 2026-11-01 range-adaptive Standard BP candidate

- Add a read-only offline estimator with explicit quality abstentions and no
  preset label access during inference. Support seven manual presets and a
  configurable user-defined eighth profile in the audit interface.
- Test distinct synthetic pressure ranges, insufficient high/low coverage,
  absent pulse and abnormal MCU timing. Audit every retained development run
  against stated panel labels only after inference; publish errors and missing
  mode coverage. Keep current firmware/calibration and raw captures unchanged.
- Implemented tools/bp_standard_adaptive.py; development audit is in
  `data/reports/standard_bp_adaptive_20261101.json` and `.md`. Four 120/80
  and one 150/100 runs produce envelope candidates; both 200/150 attempts
  abstain. The 60/30 synthetic range also abstains for missing low-side
  coverage. Earlier apparent SBP/DBP agreement was circular because the
  synthetic generator used the same 50%/60% ratios as the estimator. The
  current report leaves formal SBP/DBP null and retains descriptive ratio
  crossings only as unvalidated research fields.
  The current firmware result path remains unchanged pending independent
  validation and a separate Keil/RAM/non-human integration gate.

## 2026-11-01 multi-setting envelope readiness

- Follow-up non-human PC1 vent/seal zero repeat at 15:45: preflight safe pins,
  IDLE/ONLINE/NONE and calibration were read back; two bounded cycles showed
  open raw means 1407.283/1406.305 and sealed means 1337.975/1335.430.
  Final pins were sealed and pump OFF. A further 30-second read-only segment
  averaged 1337.288, below its 1342.870 pre-switch sealed baseline. The
  single pressure channel cannot identify the physical or electrical cause.
  Evidence: data/reports/valve2_zero_repeat_20261101-154528.md. Continue to
  pause inflation and BP coefficient fitting.

- Added `blood pressure monitor/tools/bp_multisetting_study.py` and two targeted
  tests. The script checks manifest/gate/capture provenance, extracts 10 mmHg
  height and area features only from gated candidates, and groups all attempts
  by the three confirmed panel settings.
- Report: data/reports/standard_bp_multisetting_study_20261101.md and .json.
  Candidate counts are 4/1/0 for 120/80, 150/100 and 200/150. The 120/80
  setting now has two candidate runs with recorded 0.68 cc, but post-capture
  sealed-zero drift blocks cross-run comparability. No BP model
  coefficients were fitted; no serial or firmware changes were made.
  The additional non-human Preset 1 round exported 2369 points with dropped=0
  and exact 25 ms ticks; 10 mmHg height/area gate passed. See
  data/reports/standard120_80_20261101-152030.md for raw hashes, production-C
  replay and the two vent/fresh-zero/seal closeouts. Pause further inflation
  until the zero-point discrepancy is resolved.
- Later read-only EK observations recovered toward the pre-capture raw baseline:
  successive 30-second means 1344.810 and 1343.020 versus 1342.405 before
  capture. This narrows the observed behavior to a transient/recovering offset,
  but does not establish physical zero or root cause with one sensor channel.
  Raw hashes and limitations: data/reports/preset1_zero_recovery_20261101.md.

## 2026-11-01 read-only envelope abstention

- Added `blood pressure monitor/tools/bp_envelope_gate.py` to turn the existing
  height, area and robustness diagnostics into an explicit development-only
  candidate/abstain decision, with no SBP/DBP estimate. It verifies the
  manifest hashes and retains 5/10 mmHg results. The 200/150 round abstains
  because its 170 mmHg bound is not a declared Preset 3 range and its actual
  envelope fails; the incomplete attempt abstains separately.
- Result and interpretation: data/reports/standard_bp_envelope_gate_20261101.json
  and .md. No firmware edit, serial command, inflation or new calibration.

## 2026-11-01 sealed-zero read-only and reference decision

- A 30-second EK read-only record held 601 fresh samples at raw 1312..1316,
  with first/last five-second means differing by 0.26 count and no invalid
  pressure line. The current sealed state is briefly stable, not independently
  certified as true zero pressure. Raw and reference decision are documented in
  data/reports/zero_reference_plan_20261101.md.
- Prior PC1 vent/seal comparison had a repeatable ~51-53 raw-count change,
  approximately 0.7 mmHg equivalent at the active calibration. The ordinary
  BP Pump 2 gauge has 1 mmHg resolution and its documented GAUGE command is
  not evidence of simultaneous Standard BP access. Resolve this with a
  separately logged pressure reference before changing firmware calibration
  or repeating high-pressure dynamic runs.
- The existing MPXV5050GP is the primary pressure sensor, not an independent
  reference. Continue packaging its reproducible raw/envelope development
  dataset now; a second reference is required only for later independent
  pressure-accuracy claims.
- The existing static Pressure Source calibration was already completed and
  documented in calibration_data/manual_static_2026-10-25.json. Its measured
  points support the current 82.326/-19.887 coefficients. Do not ask the
  operator to repeat static calibration or treat the missing dynamic
  synchronized trace as a missing static pressure test.

## 2026-11-01 Preset 3 high-target non-human development capture

- Keil downloaded and verified HIGH_PRESSURE_CAPTURE_20261101; current
  MPXV5050GP/ADS1115 calibration 82.326/-19.887 was restored after full erase
  and read back VALID. High targets >=200 mmHg use a 3.0 mmHg/s deflation
  target; lower targets keep 2.0. Initial no-rise attempt timed out safely;
  operator confirmation of load-side 12 V came afterward.
- After fresh raw-zero stability and non-human fixture confirmation, one
  target-220 retry reached 220.1 mmHg and exported 2289/3300 points over
  57.2 s, dropped0, exact25ms ticks. Strict decode and same-source C replay
  passed. Firmware 190/77/75, valid1 differs from panel 200/150/80; fixed
  170 mmHg oscillogram bound fails the 5 and 10 mmHg screens. Keep development
  status and inspect upper-pressure envelope and DBP crossing offline before
  freezing a new Preset 3 bound for a separate batch.
- Vent/fresh-zero/seal, target50, pump OFF and safe pins confirmed; later
  raw-zero rebound prompted a second independently logged vent/fresh-zero/seal.
  Evidence and limitations: data/reports/standard200_150_20261101-134453.md;
  second closeout: data/raw/preflight/vent_zero_20261101-134738.json.
- Capture script syntax check and 123 host tests pass. Keil rebuild/download
  evidence is retained in blood pressure monitor/MDK-ARM/high_pressure_*_20261101.log.
- Existing strictly decoded capture was re-examined without device I/O. The
  extended descriptive beat extraction found 47 clean beats below 170 mmHg
  and 10 more in 170..200 mmHg, with no qualifying beat above 200 mmHg.
  Evidence: data/reports/preset3_upper_envelope_20261101.md and .json.
  This post hoc extension does not change the failed frozen screen.

## 2026-11-01 offline multiwindow pulse study

- Read-only tool and synthetic tests: blood pressure monitor/tools/bp_multiwindow_pulse.py and test/test_multiwindow_pulse.py. Exact-tick/pressure-window gates, 128/256 strides, existing 0.001V RMS floor, low-noise/valve-only/irregular-tick rejection. No device or firmware operation.
- Strictly decoded 42 historical unique captures plus three current development captures. JSON evidence data/reports/offline_multiwindow_20261101.json; interpretation data/reports/offline_multiwindow_20261101.md. 256 stride gives candidates34/45, 128 stride5/45; all available candidates within one 256-point bin of the existing same-source long-window estimate. These are exploratory agreements, not reference-accuracy validation. No firmware algorithm change justified yet.

## 2026-11-01 Standard120/80 第三轮受控开发采集

- 操作者确认非人体动态气路、面板 120/80/80 和显示脉搏容积 0.68 cc；面板照片及独立压力仍缺。宿主脚本增加每次运行的显式确认与容积参数；缺确认会在任何设备连接/命令之前退出。
- vent→60 新鲜近零→seal 预检通过，封阀后 5 秒 raw1324..1326。target150 单轮峰值150.8，捕获2273点、dropped0、25ms MCU tick；严格解码及生产 C 回放通过。固件120/90/56，离线40..120mmHg节律80 BPM，包络峰值箱仅2脉搏，质量筛查拒绝。
- 正常 vent→60 新鲜近零→seal 后泵关、安全引脚/ADS/UART正常、target恢复50；后续 raw1449..1452/est0.7 回升，再次提示零点待独立验证。停止继续充气。报告 data/reports/standard120_80_20261101-120429.md。前两轮缺脉搏容积，不能将三轮视为严格锁定同条件重复。

## 2026-11-01 同设置非人体开发重复轮

- 操作者确认仅非人体袖带、动态 External Cuff 气路和 Standard BP/Preset 1/120/80/80 BPM。采前 5 秒 raw1315..1318、est0.0；校准、ADS、UART 和安全引脚预检通过。
- 单轮 target150，峰值150.4；自动放气完成，bp.capture/3 共2289点、dropped0、MCU tick 全为25ms。固件119/87/56；严格解码与生产 C 回放按位一致，独立离线节律窗口估计80 BPM。仅为开发样本。
- vent→60条连续新鲜近零→seal 成功，泵OFF、安全引脚、IDLE/ONLINE/NONE、UART及ADS错误0，target恢复50。封阀后 raw 升至约1436/est0.5，停止本次后续充气；单压力通道无法判定残压还是感测链变化。
- 原始记录与判定见 data/reports/standard120_80_20261101-114844.md。尾段弱包络不是开发采集的单独阻断项；完整原始尾段保留，分析窗口事先声明。面板脉搏容积、照片和独立压力仍缺。

## 2026-11-01 non-human PC1 vent/seal zero comparison

- Two bounded zero-pressure PC1 vent/seal cycles with pump OFF, no inflation or calibration change. Open raw means 1367.83/1365.75; sealed means 1317.25/1313.22; all displayed est 0.0. Final sealed 5 s raw 1317..1321, safe pins, IDLE/ONLINE/NONE, UART 0 and ADS 0/0. No failed/Boot/corrupt lines.
- Evidence: `data/reports/valve2_zero_20261101-112951.md`; raw SHA256 664005d4e5420dcb19327a8cfab0376fde26b4b03b99d4901c4152cd083c6935. State association is repeatable; physical versus electrical cause is unresolved without an independent simultaneous pressure channel.

## 2026-11-01 non-human Standard 120/80 development round

- Operator confirmed current dynamic External Cuff fixture, no human, Standard
  BP/Preset 1/120/80/80 BPM. Pulse volume and independent pressure were not
  supplied. Vent/fresh-zero/seal restored raw zero baseline before acquisition.
- One target150 round completed with 2673 points, dropped0, peak151.1, MCU
  result114/81/75 valid1; strict `/3` decode and production-C replay passed.
  Raw and report: `data/reports/standard120_80_20261101-111311.md`.
- First post-seal raw rose despite near-zero displayed pressure. A second
  vent/fresh-zero/seal returned 10-second raw to1324..1332 and est0.0;
  final IDLE/ONLINE/NONE/safe pins/pumpOFF, target restored50. Suspend repeat
  rounds pending independent pressure and pneumatic path evidence.
- Host syntax, 3 cleanup guard tests and full 114-test suite passed. No firmware
  change, Keil build/download or calibration write in this round. Task remains
  in_progress.

## 2026-10-31 next branch-isolation preparation (not executed)

- Reviewed existing wiring, load-off runner/guards/closeout and prior loaded
  valve-only failure. Found SF-01/DC12.0V label evidence, but no exact official
  valve specifications or full pump/driver-module identification.
- Saved data/reports/branch_isolation_plan_20261031.md: single valve1 trial,
  pump OFF, no start/open, first-error termination, separate stop/cleanup attempts,
  stable fresh-zero vent/seal closeout and explicit pass limitations.
- No new actuator commands, firmware/calibration/target change or return of load
  power. Await physical module/terminal/coil-wiring evidence before specifying
  branch disconnection/reconnection and obtaining a new operator state report.
- Cause remains unresolved; task is still in_progress. This preparation is not
  a board test or a claim that a loaded acquisition passed.

## 2026-10-31 load-off switch comparison

- [x] Review-only runner, bounded switching, baseline/final readtest, first-error
  guard and stop/vent/fresh-zero/seal cleanup; syntax and offline guard checks.
- [x] Run once with operator-confirmed BP Stop/load-side12V disconnected.
- [x] Preserve raw transcript/counters/hash and procedural limitations; record
  outcome separately from closeout. Keep load supply disconnected at completion.

Result17:03:40:9/9 cycles passed,readtest400 before/400 after,ADS0/0,UART0,
NONE/IDLE/ONLINE;1484 fresh display records. Closeout60 fresh zero then seal,
post5s100 zeros/safe pins. Report data/reports/load_off_switch_20261031-170340.md.
Initial17:03:03 preflight falsely expected boot identity in help; no actuation,
failure retained. Corrected to prior verified boot evidence/current capability.
No firmware/target/calibration change. Manual close differs from target-stop
ordering; cause remains open, no automatic load-power return.

## 2026-10-31 reading-path isolation test

- [x] Actual-C ADS byte/readiness/raw/scaling/calibration tests; actual manual
  100 mmHg ramp/stop/hold; 15 transaction/status fault combinations and timeout.
- [x] Add sealed-zero `readtest`, 10s/25ms, no GPIO ownership, first-failure
  termination, >=380 samples for pass; active-command/export/stream integration.
- [x] 114 host tests pass; Keil Rebuild and final help-only Build 0 errors/warnings;
  RAM63488/headroom2048, stack4096/known1392+1024 pass; no new production C/S.
- [x] Existing direct-flash authorization: fresh zero/safe pins and closeout,
  UV4 Verify OK16:52:09; boot READ_PATH_TEST_20261031; erased calibration restored
  to82.326/-19.887 and read back VALID. No physical wiring changes/load isolation claim.
- [x] Board PASS_READ_ONLY n400/10000ms; ADS0/0, UART0, IDLE/ONLINE/NONE;
  diagnostic stack1224/free2872. Final vent->fresh zero->seal, post5s99 samples0.
- [x] Preserve method, serial evidence, hashes and limits in
  `data/reports/read_path_test_20261031.md` and executable contract in capture-reliability.
- [ ] Physical loaded-switch cause still unresolved; static PASS does not prove
  hardware damage or exclude hardware-dependent I2C driver faults. Task remains active.

## 2026-10-31 100 mmHg外部静压对照

- 用户要求高压测试并在Pressure Source/100 mmHg设置要求后回复OK；内部泵保持OFF，仅外部BP供压。未烧录、改校准、target或运行内部start/hold/PWM。
- 10秒约200条VALID，估压峰值112.7，后8秒94.9–102.3 mmHg；ADS累计errors1/recoveries1未增加，UART rx_errors0。外部静压未复现失读；不等于内部泵阀切换问题修复，电气和对应软件路径均未被完全排除。
- 首次vent→十条新鲜近零→seal后回压，3秒最高2.9，随后约5.3–5.4mmHg。保留主metadata失败状态；再次vent等60条/约3秒近零→seal后5秒99条估压0，安全引脚、ADS ONLINE。没有独立用户BP按键时间证据。
- 报告`data/reports/external_static100_20261031-162647.md`包含两份原始数据SHA256及方法限制。无有效完整示波法波形；任务仍in_progress。

## 2026-10-31 WRONG_START错误来源追溯

- 按用户要求从16:09首错日志逐层追到生产HAL的I2C_MasterRequestWrite:6707：SB等待失败且START仍为1后设置0x200，发生于地址/配置数据发送之前。
- 10 ms来自ADS传输配置；等待函数先置TIMEOUT并将软件State改回READY，随后错误被WRONG_START覆盖；Master_Transmit再将返回值映射为HAL_ERROR。state0x20不能证明外设健康。
- 解码SR1=0x10为STOPF、CR1=0x101为PE/START；异常来源仍未证明。详见`ads-wrong-start-trace-20261031.md`。
- 本次仅代码/既有记录审查，无生产修改、串口操作、烧录或新充气；问题仍in_progress。

## 2026-10-31 16:09 UART修复后带负载复测

- 用户确认接回12V后执行单轮target30/host ceiling40/limit15s。到压31.0后保持阶段再次ADS读取失败，未观察PWM启动；UART仍有命令响应、rx_errors0。
- ADS首错stage5/HAL_ERROR/reg01/WRONG_START0x200、SR1=0x10/SR2=0、CR1=0x101、PB=0xFFFB、SCL1/SDA1，errors1/recoveries1。UART修复未消除ADS故障，根因仍未解决。
- stop回显后完成vent→十条连续新鲜近零→seal；后检5s100条0.2–0.3mmHg，安全引脚、泵OFF。末态EMERGENCY/USER_STOP，ADS ONLINE，未再次断12V或重启；stop覆盖了末态Fault，保留原始失败行和ADS证据。
- 报告`data/reports/uart_guard_low30_20261031-160924.md`及其中原始/后检SHA256。无新烧录、校准或有效完整波形。暂不重复充气，转向I2C与负载切换/供电路径定位。

## 2026-10-31 UART receive recovery and command integrity

- [x] Review actual HAL RX/error callback ordering and reproduce ORE stopped RX.
- [x] Add bounded error recovery, reject damaged/overflowed lines, freeze the
  command mailbox and atomically snapshot parameters, retain stop/vent priority.
- [x] Correct shifted I2C scan address and reject scan before I2C when active or
  actuator pins are unsafe. No new production C/S files.
- [x] Production-C UART/scan regressions and full 113-test suite pass; Keil
  rebuild zero errors/warnings; RAM headroom2056B and static stack1392+1024 pass.
- [x] Authorized load-off download Verify OK; restore82.326/-19.887 and confirm
  new firmware, 100 fresh zero-pressure samples, idle safe pins/faultNONE/rx_errors0.
- [x] Record wiring, download steps, evidence hashes and limitations in
  `uart-code-review-20261031.md`. Loaded-dropout root cause remains unresolved;
  no new inflation or return of12V in this increment.

## 2026-10-31 ADS first-failure bus evidence

- [x] Inspect first-failure HAL path and existing deferred recovery; passive
  five-second snapshot has100 pressure samples/raw1303..1306/est0.
- [x] Capture CR1/GPIOB.IDR read-only, print saved SCL/SDA separately and preserve
  original evidence on calls rejected because ADS is already offline.
- [x] Actual-C driver/control regression:22/22 pass, including unchanged sample,
  no inline recovery, retained snapshots across offline calls and re-init.
- [x] Full suite111/111, Keil0error0warning; RAM63480/65536/headroom2056,
  stack4096/known1352+1024; all production sources registered, host files excluded.
  Procedure and hashes: `ads-bus-diagnostics-20261031.md`.
- [x] User explicitly directed direct flashing without repeated confirmation.
  Fresh calibrated zero and safe pins verified, vent->ten fresh zero samples->seal;
  Keil Verify OK at15:34:35, fresh ADS_BUS_DIAG_20261031 boot. Full erase cleared
  calibration; restored established82.326/-19.887 and verified VALID. Ten seconds
  yielded200 fresh samples, raw1302..1305, est0; IDLE/ONLINE/NONE, ADS0/0,
  stack1184/free2912/saturated0. Load power isolation was not asserted.
  Evidence and limits: `ads-bus-diagnostics-20261031.md`.
- [ ] Use first-failure evidence and controlled physical isolation to repair the
  cause; pass healthy loaded low-pressure acquisition. Diagnostic code is not a
  completed communication repair. Never count the earlier failed rounds as pass.
- 15:38 user-authorized single30mmHg retest FAILED at target echo30.9:
  hold read failure/emergency vent, stage5/HAL_ERROR/WRONG_START0x200,
  SR1=0x0010/SR2=0/CR1=0x0101/IDR=0xFFFB/SCL1/SDA1/errors1/recoveries1.
  No PWM/export. Host stop then vent->ten fresh VALID<=1mmHg->seal, safe pins.
  Post5s99 samples est0.2..0.3, no additional ADS errors. Physical cause unresolved.
  See data/reports/ads_bus_retest_20261031-153810.md; no second inflation.
- 15:41 progressed to valve1-only isolation at fresh zero, PC8 pump OFF.
  One nominal250ms holdopen->close received MCU close echo, then zero fresh
  samples for5s; subsequent close had no bridge ACK. New ADS state unavailable.
  Remote vent/zero/seal NOT confirmed. Requested BP Stop/load power OFF/manual
  unload; operator completion not yet received. Passive snapshot5s also0 samples,
  app process responding and COM6 enumeration do not establish MCU/serial health.
  Evidence: data/reports/valve1_isolation_20261031-154115.md.

## 2026-10-31 post-target hold fault protection

- [x] Confirm audited control-flow defect and record requirements/design.
- [x] Add independent hold sampling and cancel/vent before diagnostics/recovery.
- [x] Exercise real production functions with injected read failures and stream ON/OFF.
- [x] Run full host suite (111/111), Keil rebuild (0 errors/warnings) and RAM/stack/source-registration gates.
- [x] Update safety contracts and document non-human download/verification steps.
- [x] Separately authorized load-off Keil download/Verify OK and fresh firmware-ID check; restore erased established calibration, confirm idle/online/safe pins/fault NONE and record idle stack watermark.
- [x] After communication/MCU restart and explicit user retry authorization, retain physical hold-fault evidence:15:06 target30, reached echo31.2, stage5/HAL_BUSY/TIMEOUT, emergency vent, no PWM-start echo; host stop/vent then ten fresh VALID<=1mmHg samples and seal, final safe pins.
- [ ] Pass healthy bounded non-human low-pressure acquisition. Both14:54 communication-loss and15:06 ADS-failure rounds remain failed; no valid export. See data/reports/restart_low30_failure_20261031-150649.md. Physical trigger unresolved; valve SF-01 flow hypothesis unverified. Load is not confirmed disconnected after the latest round.

Software validation, image identity and 14:49/14:51 board preflight: `hold-safety-20261031.md`.
Firmware ID HOLD_SAFETY_20261031 is running; original calibration restored VALID
82.326/-19.89 after full erase. Ten-second observation200 fresh samples est0,
raw1327..1331 (unclipped reconstruction mean-1.010mmHg; no independent zero-accuracy
claim). Idle/diagnostic stack1424/2672, saturated0; ADS errors0/recoveries0.
No actuator commands or load-on physical trial in this download increment.

Separate14:54 load-on trial failed; preserve the successful download/preflight above.
Raw SHA2565c8156536067867c6165ce0ee0cb35f84a4695bfb8a89699eb33d9a7a668370e.
See `data/reports/restart_low30_failure_20261031-145438.md` and JSON for timeline,
manual safety confirmation and14:59 load-off status ACK timeout. No valid export,
no observed target/hold/PWM transition, no proven ADS/MCU/transport root cause.

15:02 reconnect load-OFF read-only gate passed:200 fresh/10s, est0,
raw1297..1301; IDLE/ONLINE, safe pins, original calibration VALID, NONE/ADS0/0,
stack1424/2672 saturated0. Operator confirms MCU restart/power cycle during
recovery; counters are post-reset only and do not clear the failed physical gate.
No new startup firmware-ID line, actuator command, calibration write or reset
was requested by the assistant. COM6-only enumeration coexists with live data;
absence of a CH340/CH341 display name alone is not disconnect proof.
See `data/reports/reconnect_preflight_20261031-150248.md` and raw metadata.

## 2026-10-31 read-only ADS switching audit

- Audited three first-failure windows without actuator commands or firmware edits.
  Two target-stop windows show stage5 / HAL_BUSY(2) / TIMEOUT(0x20) /
  READY / SR2.BUSY; the HAL pre-transfer BUSY wait uses25ms, independently
  of the driver10ms argument. Another STOP window shows WRONG_START(0x200).
- Confirmed a pending fix: stream read failure during the one-second post-target
  wait does not cancel the timer; the14:21 log then starts PWM and only vents
  on the subsequent failed deflate read. Separate this control-flow defect from
  the still-unproven electrical/physical trigger.
- Read-only5s snapshot receives101 samples, raw1383..1386, est0.0; this does
  not establish fault clearance or transient repair. No raw snapshot retained.
- Next implementation scope and exact evidence are in
  data/reports/ads_switching_audit_20261031.md. No new inflation, reset,
  fault-clear, calibration write, compile or download in this audit.

## 2026-10-31 30 mmHg sealed-hold diagnostic

- Authorized non-human target30 hold: use existing seal to cancel the one-second
  post-target PWM timer; pump-off/sealed pins confirmed before and after hold.
- Trial 14:33:06 reached30.7, then had ADS CONVERSION_START I2C timeout
  (HAL error0x20), one retry/recovery, corrupted failure line and SENSOR_READ
  latch. Treat as INVALID despite original host metadata's completion label.
  Recovered pressure19.6->17.4 over4.042s is descriptive only.
- Completed vent -> ten fresh <=1mmHg samples -> seal, final pump OFF and sealed
  pins; follow-up passive data retained. No firmware/calibration change or reflash.
- Added active read-failure/reinit/corruption guard and final-fault invalidation
  to temporary host collector; syntax plus3 offline guard checks pass. No second
  physical inflation. See data/reports/sealed_hold30_20261031-143306.summary.md.
- Next: investigate pump-stop-associated ADS/I2C transient before another hold;
  do not tune pneumatic PWM or BP coefficients from this invalid comparison.

## 2026-10-31 dataset catalog and capture protocol

- [x] Reuse strict export decoder and inventory all 102 NDJSON files without changing raw data.
- [x] Hash exact MCU records to deduplicate bridge/raw/verified copies; retain file SHA-256 and per-file failure reasons.
- [x] Generate deterministic JSON catalog and Chinese quality report, with missing labels null and no replay claim.
- [x] Freeze the v1 per-run metadata template and refresh project entry documentation.
- [x] Run catalog-specific test, full host suite (110/110) and byte-for-byte repeatability check of generated outputs.
- [ ] Start a prospective small repeated batch only after current BP panel settings and fresh zero/raw checks are recorded.

Read-only preflight on 2026-10-31: EK bridge hello is online, but a five-second
snapshot contained zero fresh serial samples. No actuator or BP command was sent.
Current panel mode/settings were requested but are not yet recorded. Do not
reuse labels from the historical archive or treat this as a zero-pressure pass.

Follow-up on 2026-10-31: the user confirmed Standard BP / Preset #1 /
External Cuff / 120/80 mmHg / 80 BPM. Actual displayed pulse volume was not
separately confirmed. Serial reception recovered. The latest read-only preflight
received 197 samples in 9.80 s: raw 1333..1338, sensor 230..231 mV, est 0.0.
Status is IDLE, calibration VALID 82.326/-19.89, ADS ONLINE, fault NONE,
ADS errors/recoveries 0, PB8 HIGH / PC1 LOW / PC8 HIGH / pump OFF.
Raw-derived unclipped pressure is approximately -0.96..-0.89 mmHg with the
recorded active calibration; displayed zero alone is not an independent zero
check. The earlier fresh window was approximately 223 mV, so between-window
baseline movement remains unresolved. Physical unloaded state and the current
non-human fixture still need confirmation before this batch starts. No actuator
command or calibration change was sent. Settings, bridge log hash and summary:
`data/reports/prospective_preflight_20261031-132512-832862.json`;
original bridge messages: `data/raw/preflight/prospective_preflight_20261031-132512-832862.ndjson`.

The user subsequently confirmed the current fixture is non-human and completely
unloaded. A passive 20 s observation retained 400 fresh samples, raw 1318..1321,
sensor 227..228 mV and est 0.0, without replacement-character lines. Five-second
raw means 1319.27/1319.02/1319.03/1319.73 show low short-term variation; the
unclipped equivalent remains approximately -1.17..-1.13 mmHg. This does not
resolve the earlier between-window baseline changes. See
`data/reports/zero_observation_20261031-132735-752183.json`.
A first development-only Standard 120/80 pilot, target150 with host abort165,
75 s deadline and vent/fresh-zero/seal closeout, is documented in
`data/protocols/pb8_standard_120_80_pilot_20261031.md`; inflation has not started.

## 2026-10-31 PB8 inflation relay migration

- [x] Set valve1 to PB8 OD/NOPULL active LOW, with SET preloaded before init.
- [x] Synchronize `.ioc`, diagnostics, export/loaded-pulse gates and current docs.
- [x] Exercise actual production GPIO/macros and both predicates for all eight
  actuator states using separate GPIOB/GPIOC inputs; update fault-state fixture.
- [x] Full host suite 109/109; Keil rebuild 0 errors/0 warnings; all Core/Src
  files registered and existing headers available through Core/Inc.
- [x] RAM 63472/65536 B (2064 B free), static known stack 1344/4096 B plus
  1024 B reserve passes; not a new board runtime-watermark measurement.
- [x] Record wiring, manufacturer limits and non-human validation procedure in
  `血压仪完整接线方案.md`.
- [x] Authorized Keil download: retry1 Verify OK/Application running, exit 0;
  restore and independently read back calibration 82.326/-19.887.
- [x] Read back PB8 HIGH / PC1 LOW / PC8 HIGH, IDLE, ADS ONLINE, fault NONE.
- [x] User confirmed relay holdopen/close observation; non-human 30 mmHg trial
  reached target and stopped pump, recorded peak 33.0 mmHg, then vented to
  <=1 mmHg before seal; final 0.2 mmHg, idle pins and no fault.
  See `pb8-relay-20261031.md` and the raw NDJSON. Earlier raw sensor dips,
  baseline shift and one corrupted serial line remain acquisition-quality issues;
  this trial verifies low-pressure inflation only.

Build evidence: `blood pressure monitor/MDK-ARM/build_pb8_20261031.log`.
Prior PC0 logs/experiments below retain their original pin mapping and are
historical evidence only. See `pb8-relay-20261031.md` for this increment.

## 2026-10-29 connected pulse-width comparison

- [x] Add bounded fixed 1-4 ms loaded-pulse commands while retaining 5 ms.
- [x] Make the connected bridge request and verify one fixed pulse width;
  accept fixed 1-5 ms in the offline audit.
- [x] Add width and rejection regressions; run 105 firmware host tests,
  13 bridge tests, Keil rebuild and static RAM/stack budget.
- [x] After fresh zero-pressure and electrical/pin preflight, download and
  restore/read back calibration after full-chip erase.
- [x] Capture separate non-human 1-4 ms rounds and compare baseline drift,
  net loss, valve-phase pressure and voltage notches to the 5 ms record.

## 2026-10-29 loaded valve-pulse comparison

- [x] Add bounded `loaded pulse` firmware mode with fresh-pressure/pin gate,
  1s sealed baseline, 3s 5ms/200ms pulses and automatic residual vent.
- [x] Add safety-contract coverage and a host one-shot capture/closeout path
  with stable starting pressure and strict `/3` validation.
- [x] Run host suites, true Keil rebuild, Keil source sync and RAM/stack gate.
- [x] Non-human preflight, download/calibration readback, one BP Source run,
  voltage/pressure phase audit and closeout. See loaded-pulse-preflight-20261029.md.
- [x] Record evidence, limitations, wiring and validation steps; update
  capture-safety spec.

## 2026-10-29 sealed-zero pulse diagnostic

- [x] Bound PC1 pulses to 5 ms/200 ms for 5 s, acquire 25 ms pressure and
  sensor-voltage samples, and close PC1 on normal completion.
- [x] Gate start on fresh sealed zero/valid calibration/ADS/pump off, emergency
  vent on ADS, pressure or buffer fault, and keep stop/vent/seal reachable.
- [x] Block conflicting commands while active; add a safety contract test.
- [x] Run 103 host tests, zero-warning Keil rebuild and RAM/stack gate;
  verify project source registration (2064 B static RAM headroom).
- [x] Complete live non-human preflight, controlled Keil download and
  calibration readback; acquire one zero-pulse `/3` export and analyze raw
  sensor voltage against pulse phase. See `zero-pulse-board-result-20261029.md`.

## 2026-10-29 bounded step trace

- [x] Record up to 12 step-to-pulse associations in the existing valve
  diagnostics, leaving pressure/tick/envelope storage and control unchanged.
- [x] Emit checksummed `/3` step rows and preserve strict `/1` and `/2`
  decoding, including the host capture bridge schema recognition.
- [x] Cover real-C lifecycle, cap, old schemas, missing/reordered/tampered
  trace rows and full host regressions.
- [x] Rebuild Keil, inspect its project file and run the RAM/stack gate.
- [x] Complete safe board preflight, controlled download/calibration readback
  and one non-human trace capture; keep physical-cause interpretation bounded.

## Resume safety correction (2026-10-26)

- [x] Recovered the current execution point: `CAPTURE_VALVE_20261025` software is
  complete, while the board still runs `CAPTURE_EXPORT_20261025`; no prior flash or
  inflation authorization carries into this session.
- [x] Reconciled the calibration source of truth. The finalized 2026-10-25 record
  is `cal write 82.326 -19.887`; `88.3/-19.96` is rollback-only. Updated active
  restore scripts, top-level safety guidance, current wiring notes and historical
  document warnings. No serial helper was executed and no target calibration changed.
- [x] Re-ran six helper-script syntax checks, the full 73-test suite, a true Keil
  rebuild (0 errors/0 warnings; Code48432, RO6136, RW28, ZI63276), Keil source
  registration checks and the RAM/static-stack budget (2232 B RAM headroom).
- [x] Started the EK-OmniProbe bridge and obtained explicit full authorization for
  the scoped non-human download. Pre-flash evidence: IDLE, manual OFF, ADS ONLINE,
  pressure0.0, PC0/PC1 LOW, PC8 HIGH and pump OFF. `UV4 -f` full erase/program/
  Verify OK used the prechecked HEX SHA256
  `BEE4C399F96A0C758B4930C223CCF64C3E339A5756419ABE670476D7BA3146AB`.
  Post-flash UNCAL/safe pins/ADS ONLINE/Fault NONE were verified before restoring
  only `82.326/-19.887`; independent readback was VALID and the final100-sample
  snapshot remained0.0mmHg. No pump/valve command or pressure operation occurred.
- [x] Completed the new-image non-human low-pressure gates. Active-inflation stop
  triggered at22.4mmHg (473ms after START), produced the required STOP pin state,
  then vented to55 fresh post-vent samples with the final10 all0.0 before seal.
  A separate natural50mmHg round peaked50.7, captured377 points/dropped0 over
  9400ms at25ms intervals, and finished the expected no-pulse invalid calculation.
  Its `/2` export contained begin+377 points+one valve+features+end, hash2688858164;
  valve evidence recorded48 actual pulses, 200ms period and1..4ms on-time with no
  >=5mmHg steps. Strict decode and production-C replay passed with zero envelope/
  smooth error and equal bits/features/validity. Every closeout followed vent ->
  fresh low pressure -> seal; final pins were sealed/pump OFF and ADS errors0.
- [x] Acquired and strictly decoded one new non-human Standard BP `bp.capture/2`
  waveform with valve aggregates. Reference120/80mmHg,80BPM produced113/91,75,
  valid1; n2225/dropped0/span55600ms with every tick delta25ms. The complete export
  hash423181647 contained279 pulses, period200ms and on-time1..4ms. No >=5mmHg
  step occurred, so the valve aggregate correctly reported steps0. Offline pressure
  differences still showed six >=2mmHg and four >=3mmHg changes, all at
  elapsed%200=0; maximum fall was-3.93mmHg19 samples before MAP. The prior
  +/-14mmHg shocks did not reproduce: smaller phase association remains, but valve
  causation of feature/DBP error is not established and no tuning was changed.
  Production-C replay was bit-equal with zero envelope/smooth error.
- [x] Runtime stack watermark implementation and host tests; Keil build/budget
  and idle baseline pass. On 2026-10-28, complete Standard BP, calculation,
  strict `/2` export/replay and two post-export stack reads passed; used=1536,
  free=2560, saturated=0. Detailed evidence is in `validation.md`.
- [x] Three valid natural same-image repeatability rounds with complete verified
  `/2` waveforms, recorded in `validation.md` on 2026-10-27.

## Current software delivery: valve-pulse correlation evidence (2026-10-25)

- [x] Add a compact reset-scoped valve diagnostics aggregate and public record/read
  API; call the record API only from the actual `DeflatePulse_Start()` PC1-open path.
- [x] Count >=5.0 mmHg consecutive pressure steps by 25 ms pulse phase and retain
  maximum signed rise/fall evidence without changing algorithm calculations.
- [x] Upgrade firmware export to `bp.capture/2` with one checksummed valve row.
- [x] Keep strict `bp.capture/1` decode compatibility; require exactly one valve row
  for `/2`, reject missing/duplicate/reordered/tampered records, and include it in
  offline reports while production replay still consumes only point samples.
- [x] Add real production-C lifecycle/roundtrip and static actual-open-path tests;
  correct stale 70% DBP comments to the existing 60% constant without behavior change.
- [x] Run the full host suite, Keil rebuild, budget/map/callgraph checks, and confirm
  all firmware sources remain registered in the Keil project with >=2048 B RAM free.
- [x] Update the capture-export spec and validation record. Stop before flash,
  calibration changes, pneumatic operation, or Standard BP testing pending separate
  authorization.

Software result: firmware marker `CAPTURE_VALVE_20261025`;73/73 tests pass;
Keil ARMCLANG V6.22 reports0 errors/0 warnings (Code48432, RO6136, RW28,
ZI63276). RAM63304/65536B leaves2232B; static known stack peak1304B plus1024B
reserve fits the4096B stack. Runtime watermark remains unmeasured. On 2026-10-26
the exact rebuilt HEX above was flashed and verified under explicit authorization;
the erased calibration was restored and read back, with safe pins and0.0mmHg idle
telemetry confirmed. No pump/valve or pressure operation was performed. A new `/2`
  low-pressure target capture is validated; a Standard BP `/2` capture is pending.

## Current software delivery: capture export / replay (2026-10-25)

Software and non-human low-pressure target validation complete. New image
CAPTURE_EXPORT_20261025;70/70 host
tests pass; Keil V6.22 zero errors/warnings; RAM63240/65536B (2296B headroom),
stack budget passes, runtime watermark unmeasured. Full nominal40Hz samples,
MCU ticks, capture-time calibration/provenance and completed envelopes are
exported through the bounded bp.capture/1 protocol and replayed by production C.
Image flashed/verified; erased calibration was restored to82.326/-19.887 and read
back VALID after safe GPIO/ADS checks. Natural50mmHg capture n321/dropped0/span8s;
complete export/replay, stream-off rejection, stop cancellation (23.2ms observed),
fresh pressure during export (max host gap54ms) and re-export passed. No algorithm
arithmetic/tuning or electrical settings changed.
One new Standard120/80,80BPM waveform is complete: n2089/dropped0/span52.2s,
target result93/90,56 valid1 and bit-equal production-C replay. Feature analysis
shows valve-schedule-correlated pressure shocks dominate the MAP/SBP/DBP envelope;
the first256-point FFT chooses a near-tied56BPM bin while later windows recover the
75/84BPM neighborhood. No tuning change was made; direct valve trace is still needed.
See capture_export_2026-10-25.md for wiring, evidence and next physical gates.
The19:40 root cause remains unknown; the notes below retain historical evidence.

## Cooperative calculation execution (2026-10-25, repeatability blocked by invalid BP)

19:40 repeatability follow-up: user confirmed non-human External Cuff+real cuff,
120/80mmHg,80BPM,Running and authorized two sequential complete rounds, with
the second conditional on the first passing. First requested round FAILED valid
BP acceptance; second was NOT started. No retries, firmware/algorithm/calibration/
wiring changes. Pre-test5s100 fresh samples est0.2; status/pins/cal/fault passed.
Target150 reached151.4, hold1013ms, natural done; current Capture2177/2800,
dropped0,duration54400ms,interval25ms. BP calculation failed; DBGFAIL MAP92.9,
SBP125.4,DBP93.7. Existing calculate_result rejects dbp>map_pressure; this is
the direct rejection condition, not proof of the waveform/root cause.
Host script STANDARD_COMPLETE=False, exit1, correctly withheld a valid result.
Log: tmp/linkpad_standard_20261025-194047.ndjson.

Timing gates separately passed: Calc work1581/wall2276/max_step31/extract1461/
smooth89/finish31ms,568 steps. Pressure1456 records, max host gap84ms, no
nonpositive or>200ms gaps; inflate+hold62/max60ms,deflate1089/max51ms,
calculation+output60/max84ms. Done-to-next31ms, straddling-done60ms. This is
not a successful repeatability round despite clean capture and responsive logs.

Failure cleanup stop ->vent ->fresh low pressure ->seal completed; revised
post-vent timestamp filter was used on hardware. Last10 before seal est1.0..0.9,
all after firmware VENT (1792928514715); seal requested1792928517386.93.
Pins PC0/PC1 LOW,PC8 HIGH,pump OFF; VALID/ONLINE/manual OFF,ADS errors0/
recoveries0,expected USER_STOP,target50 restored,log final est0.7. Later read-only
5s100 samples est3.7 throughout: do not claim sustained zero or auto-inflate.
User reminded to Stop BP Pump2 separately; panel stop not independently verified.

Current COOP complete natural acquisitions: one valid BP at19:24, one rejected
BP at19:40;19:33 cancellation is a separate case. Three-valid-round acceptance
is NOT met; no valid three-round range/statistics available. Next useful work:
design complete40Hz waveform export/offline replay to investigate envelope
feature selection and pressure reversals before tuning or another inflation.
Runtime stack watermark remains open. Detailed evidence in hardening record.
All lower time-stamped notes are historical, including earlier pending wording.

19:33 calculation-stop follow-up: user approved the proposed next test. Same
non-human circuit/calibration/firmware, target150; firmware reached150.4, held,
naturally ended with Capture2353/dropped0/duration58800ms. Host requested stop
387.6ms after done; Safety STOP response548ms after done /160.4ms after host
request (includes client/bridge/serial overhead, not isolated MCU latency).
CALC_STOP_COMPLETE=True,104 fresh Pressure records in the5s observation,
no BP/Calc anywhere in the log; total1545 Pressure/max host gap60ms.
Pending calculation is inferred from unchanged Begin/Step flow and capture,
not a direct runtime phase readout. One cancellation case passed, not every
phase. Not a Standard BP accuracy/repeatability round: pulses were unnecessary
and simulator panel state/reference output was not independently read back.
Log tmp/linkpad_calc_stop_20261025-193307.ndjson, exit0.

Stop/vent/seal closeout verified safe pins/VALID/ONLINE/errors0/recoveries0,
expected USER_STOP, target50 restored, final est0.1. Last10 low samples before
seal were all0.7;3 preceded the final vent, all followed the earlier stop that
already opened the vent for>5s. Do not claim10 strictly post-vent samples in
this run. Subsequent read-only5s100 samples est0.8..0.9, not exact-zero proof.
Fixed host cleanup to count only timestamps after vent command completion;
offline queue-regression plus5 cancellation/failure tests pass, py_compile OK.
This cleanup refinement has not been re-run on hardware; no repeat inflation.
No firmware/build/download/wiring/calibration changes. Runtime stack watermark,
two further complete COOP Standard BP rounds and full40Hz export remain open.

19:24 COOP Standard BP follow-up: user confirmed120/80mmHg,80BPM,External
Cuff+real cuff and authorized one round. Target150; firmware target-reached152.0,
hold~1s, natural deflation done. Capture2057/dropped0/duration51400ms/interval25ms;
BP118/68 Pulse84 valid1. Calc work1500/wall2160/max_step30/extract1385/smooth85/
finish30ms,538 steps. First board timing gate PASSED: max_step30<=50ms and
whole-log Pressure host-delivery max80<=200ms (1414 records, no nonpositive
or >200ms gaps). Inflate+hold max60ms, deflation1029 records/max51ms;
calculation+output57 records/max80ms. Done-to-next-Pressure32ms, straddling
done gap60ms. Previous1858ms post-done gap did not recur in this round;
2s freshness abort unchanged. Host timestamps/sampleRateHz0 do not prove
internal40Hz acquisition timing or complete waveform export.
Evidence: tmp/linkpad_standard_20261025-192443.ndjson, script exit0.

Closeout stop ->vent ->10 fresh<=1 ->seal; safe pins PC0/PC1 LOW,PC8 HIGH,
pump OFF,cal VALID/ADS ONLINE/errors0/recoveries0. USER_STOP is expected
closeout latch. Target50 restored, log final est0.6; subsequent read-only5s
snapshot101 samples all est1.6, so no sustained-zero claim or blind vent retry.
BP Pump2 panel Stop remains a separate user action. Relative to configured
reference, result differs -2/-12mmHg,+4BPM; no accuracy/clinical pass claimed.
Only one complete round on COOP firmware; calculation-time stop, repeatability,
runtime stack watermark and complete40Hz export remain open. No further
inflation automatically authorized; no firmware/Keil/download/wiring changes.

Host-only script follow-up before this round: retain75s acquisition deadline;
on natural done, open one30s calculation observation window, requiring both
BP and Calc plus nonzero/dropped0 Capture. Keep2s freshness abort,165mmHg
host ceiling and cleanup unchanged. Python py_compile passed; not in uvprojx.

19:17 low-pressure follow-up: first attempt at19:16 ended at the host5s trigger
deadline without reaching20mmHg; user then reported the actuator supply had not
been plugged in and explicitly requested a retry. Stop/vent/seal completed;
do not count that attempt as an active-pressure stop pass or firmware timeout.
Retry with unchanged target50 passed: stop during inflation, no target-reached
auto-stop, observed peak26.2mmHg. Vent ->10 fresh samples each1.0 ->seal;
final est0, safe pins, VALID/ONLINE, ADS errors/recoveries0, expected USER_STOP.
Subsequent read-only5s snapshot100 samples all est0. Log:
tmp/linkpad_lowpressure_20261025-191708.ndjson (444 samples, max host gap58ms).
No calculation/capture timing established: stop was before deflation, Capture n0.
Await user panel confirmation/start of Standard BP120/80,80BPM,External Cuff
before a complete natural deflation/calculation timing round. No further start
command is implied while the simulator remains in the prior confirmed Stop state.

19:10 resume follow-up: user continued after the explicit calibration-restoration
request. Read-only status/pins/cal/fault confirmed UNCAL, IDLE, ADS ONLINE,
pump OFF and sealed pins. Restored only `cal write 82.326 -19.887`; firmware
reported written+verified and independent cal readback VALID / 82.326 / -19.89
(display rounding). Five-second post-write snapshot received100 fresh samples,
all est0; faults/errors/recoveries0. Evidence:
tmp/coop_resume_20261025-191026.ndjson. No flash, actuator command, rewiring or
new inflation. This is sensor telemetry, not independent proof of zero pressure.
Await physical restoration of the original actuator supply, with no human
connected and BP Pump2 Stop, before the already-planned low-pressure stop test.
Cooperative calculation board timing and Standard BP repeatability remain pending.

19:06 download follow-up: user confirmed non-human / simulator Stop / actuator
supply off. Keil full-chip erase, programming and verify passed; startup log
confirms CAPTURE_SAFE_COOP_20261025, ADS init OK and sealed pump-OFF pins.
Full erase cleared calibration (UNCAL). No inflation performed; awaiting explicit
restoration approval for the known 82.326/-19.887 record and physical actuator
supply restoration. Logs: tmp/coop_flash_20261025-190604.log and
tmp/coop_postflash_20261025-190604.ndjson. Board timing gate remains pending.

Result: 59/59 host/static tests pass, including legacy bit-equivalence and real
main calculation-helper execution. Keil 0 errors / 0 warnings; code45928,
RO5108, RW28, ZI63180. RAM63208/65536 (headroom2328), stack4096,
known peak1192 +1024 reserve passes; runtime high-water remains unmeasured.
No flash or actuator commands. Existing production C files remain in uvprojx;
host-only files excluded. No HEAD: no mixed initial commit or task archive.
Next: safe download, low-pressure stop, final-step/host-gap timing, then two more
Standard BP rounds and a separate full-waveform export. See hardening record.

- Add Begin/Step/Cancel calculation API and bounded extraction/smoothing batches;
  preserve floating-point operation order and synchronous compatibility API.
- Record MCU work/wall/max-step/phase timings; output from main, never algorithm.
- Integrate both relay-only and full-control callers; cancel on stop/reset and
  actuator overrides, keep normal final valve state and fresh pressure stream.
- Regression: legacy envelope bit-equivalence, successful/failed jobs, frozen
  capture, cancellation/restart, tick wrap/timing, control/main integration.
- Run full host/static tests, Keil rebuild, RAM/stack budget and project sync.
- Document unchanged wiring, non-human download/low-pressure/timing acceptance;
  do not flash, operate actuators, relax safety limits or claim bench timing.

## Standard BP software hardening (2026-10-25, first full bench round passed; repeatability pending)

18:10 follow-up: user authorized inflation/deflation. LINKPAD target150 reached
150.9, held ~1s and naturally finished: Capture2521 / dropped0 / 63000ms,
BP117/74 Pulse75 valid1. Deflation pressure delivery1261 records, max host gap55ms;
the previous ~94mmHg interruption did not recur this round. Whole-log max gap
1858ms is AFTER done, across Calculate/output; MCU duration not yet measured.
Keep the 2-second freshness gate: only142ms margin, not a fully resolved timing
issue. OmniProbe+firmware changed together; no driver-causation claim.
Stop/vent ->10 fresh <=1 ->seal confirmed safe pins, ADS errors/recoveries0,
expected USER_STOP latch; target50 restored. Log final est0.2, subsequent read-only
5s snapshot1.8..1.9, not sustained zero. Simulator panel Stop is separate.
Evidence: tmp/linkpad_standard_20261025-181059.ndjson. Two more successful rounds,
runtime stack/timing checks and full40Hz export remain outstanding; no further
inflation authorized by this closeout. See software_hardening_2026-10-25.md.

18:08: user confirmed actuator supply restored. Low-pressure active-inflation
STOP test passed with target50, stop requested at first >=20 sample; observed
peak30.6, no auto-target stop. Vent then 10 fresh <=1 samples and seal; final
est0, safe pins, ADS errors/recoveries0, expected USER_STOP latch. Capture n=0
because stop preceded deflation. No Standard BP yet: simulator was confirmed
Stop for flashing/low-pressure tests; user must start verified panel mode next.

18:04 follow-up: user confirmed download safety preconditions; UV4 flash/verify
passed and boot marker LINKPAD was read back. Full erase cleared calibration;
original 82.326/-19.887 restored and verified VALID. Idle/ONLINE/safe pins/fault
NONE, then 30-second snapshot600 with est=0. No actuator commands were sent.
Await user restoration of existing actuator supply before low-pressure testing;
do not infer powered actuators from earlier permission to test.

Transport follow-up: OmniProbe updated to 3.2.2; read-only 5-second check received
100 samples, est=0 (host sampleRateHz unknown). Both failed captures crossed a
65 ->64-byte pressure-line boundary at ads=1000 ->999. Added conditional CRLF
padding in main.c only, marker CAPTURE_SAFE_LINKPAD_20261025. Formatter regression
failed on the old code and passed after the change. Driver causation remains
unproven; do not claim the transport or Standard BP bench gate is resolved.
Build/budget passed; no new flash, pressure operation or calibration write.
See software_hardening_2026-10-25.md for safety confirmation and validation steps.

17:44 second attempt, explicitly requested by user: fresh zero-pressure gate
passed (100/100 est=0), same target150 and unchanged safety limits. Reached
150.9, held, deflated, then host freshness timeout recurred. Independent log
shows 2089ms gap followed by 41 same-host-timestamp samples near 94 mmHg.
Capture973 / dropped0 / 24300ms, ADS errors0 / recoveries0. Stop/vent/seal
confirmed, final est1.1, safe pins, target50 restored. No completed BP round.
Do not repeat inflation until transport delay is investigated; see validation log.

17:28 Standard BP attempt: target 150 reached 150.5 mmHg, held ~1 second,
then deflated. Host pressure delivery gap 2129ms exceeded the unchanged
2-second freshness limit, triggering host stop/vent; not a proven ADS failure.
909 capture points / dropped=0 / 22700ms; ADS errors=0, recoveries=0.
Sealed after 10 consecutive <=2 samples, confirmed safe pins, restored target50.
No completed BP result or natural deflation completion; three-run gate pending.
Subsequent vent/seal cleared low residual pressure; 30-second unpressurized
observation received 600 samples at est=0..0.1, largest host timestamp gap51ms.
See software_hardening_2026-10-25.md for logs and transport-batching caveats.
Do not relax the freshness gate or treat internal capture timing as proven.

Validation follow-up at 17:21: user confirmed a non-human, depressurized bench,
BP Pump 2 Stop and actuator supply disconnected. UV4 flash/verify succeeded;
boot confirmed CAPTURE_SAFE_20261025 / capacity=2800. Full erase cleared the
calibration; original 82.326 / -19.887 was restored and read back VALID.
ADS ONLINE, errors=0, recoveries=0; PC0/PC1 LOW, PC8 HIGH, pump OFF. No start
or deflation PWM command was sent. User must restore the existing actuator
supply before low-pressure stop and Standard BP testing. See validation record
in software_hardening_2026-10-25.md; dynamic verification remains pending.

17:24 low-pressure follow-up: target 50 auto-stop reported 50.4 mmHg, then
1-second hold and 314 deflation samples / dropped=0 / 7825ms. No ADS errors.
Host stop trigger missed the sampled peak, so active-inflation manual stop is
not claimed verified. Later stop/vent confirmed pump OFF; pressure settled to
1.1 mmHg, failing the original <=1 zero gate. After fresh 5-second observation,
sealed at an explicit <=2 mmHg low-residual closeout target to avoid leaving
valve2 energized; this is NOT zero-point acceptance. Final pins safe, expected
USER_STOP latch remains. Await independent panel pressure / Standard BP setup
confirmation before further inflation; no Standard BP repeatability claim yet.

- Remove the algorithm's 8 KiB local percentile buffer (existing stack is only
  1 KiB); preserve the percentile signal gate and all current algorithm ratios.
- Budget 2800 samples / nominal 70 seconds and a 4 KiB stack within 64 KiB SRAM.
  Reject overflow explicitly; every acquisition caller must emergency-stop.
- Preserve ADS1115 HAL failure status/stage/register snapshot; recover the I2C1
  peripheral only on a later offline Init, never before returning an active read
  failure to the safety caller. Do not change electrical settings/calibration.
- Add capture summaries, bounded offline stream retries, regression tests, Keil
  build and map/callgraph checks. Document non-human validation; do not flash or
  operate actuators automatically. ADS offline root cause remains unproven.

Result: 51/51 tests passed (including 12 executable real-C host regressions).
Keil 0 errors / 0 warnings; RAM 63168/65536 including 4096-byte stack; known
maximum stack 1112 bytes with indirect-call/cycle caveat. Budget gate passed.
Production files already present in uvprojx; test-only C remains excluded.
See `software_hardening_2026-10-25.md` for validation, remaining limits and the
five-part bug analysis. No flash/actuator operation performed; task stays active.

## Phase 1: Trellis Setup For This Firmware Project

- Add firmware-specific specs under `.trellis/spec/firmware/`.
- Update the task PRD/design so future sessions know this is an STM32 project.
- Point `implement.jsonl` and `check.jsonl` at the firmware specs.

## Phase 2: Code Review Before Firmware Changes

- Compare `Core/Inc/main.h` with `血压仪完整接线方案.md`.
- Trace startup order in `main.c`.
- Trace state transitions in `bp_control.c`.
- Trace ADS1115 pressure conversion in `ads1115.h` and `ads1115.c`.
- Trace ESP8266 initialization and upload placeholder in `esp8266.c`.

## Phase 3: First Firmware Feature

Recommended first coding task: add button-driven start/stop handling in the main loop with debouncing, because the state machine exists but has no visible start trigger in `main.c`.

Acceptance for that follow-up:

- PA0 starts measurement only from idle state.
- PA1 calls emergency stop.
- Button handling does not block pressure safety checks.
- Debug logs show start/stop events on USART3.

## Staged Non-WiFi Completion

### Stage 1: Actuator Contract And Interlocks

- Decouple valve macros from PC8 pump control.
- Align GPIO startup levels with the confirmed actuator contract.
- Align relay-only debug commands and `bp_control.c` transitions.
- Build the Keil target.
- Validate PC0/PC1/PC8 without a cuff, pump, valve coil, or human connected.

Status: code, Keil build, and user hardware validation passed on 2026-08-25.

### Stage 2: Standalone ADS1115 Acquisition

- Initialize and probe ADS1115 even while relay-only mode is enabled.
- Return initialization status and guard driver calls against invalid state.
- Read one coherent AIN0 sample with conversion-ready polling and timeout.
- Print raw code, A0 voltage, reconstructed sensor voltage, and provisional mmHg.
- Keep all actuators in their existing state during pressure diagnostics.
- Build the Keil target and validate first with no human connected.

### Later Stages

- ADS1115 standalone pressure acquisition and calibration.
- Slow-deflation control with an observed mmHg/s acceptance band.
- Sampling/buffer/algorithm corrections and reference waveform tests.
- Buttons, complete measurement state machine, and result reporting.
- Non-human end-to-end validation before any human-contact test.
- ESP8266/WiFi remains out of scope.

## Stage 2 Status

Passed on 2026-08-25: code and non-human hardware validation complete; Keil build
reports zero errors and zero warnings.

## Calibration-Wait Safety Hardening

- Add BP_Fault_t storage, names, timestamps, reset, and nonblocking emergency stop.
- Lock full BP_Control_Start() while BP_SENSOR_CALIBRATION_VALID is zero.
- Route full-measurement sensor failure, inflate timeout, and over-pressure to vent.
- Keep relay-only mode and old serial commands; keep physical buttons disabled.
- Add help/status/pins/fault and 250 ms pressure stream commands.
- Add a 5000 ms automatic timeout to relay-only start/open.
- Add nominal 4-second IWDG, debugger freeze, and main-loop refresh.
- Synchronize iwdg.c and the HAL driver into .ioc and the Keil project.
- Add Python static safety contract tests.
- Build with Keil and require zero errors and zero warnings.

Status: implementation, 12 static tests, Keil build, and non-human hardware
command/timeout/watchdog validation passed by 2026-08-26.

## Stage 3A: Hardware-Safe Calibration Dry Run

- Add a standard-library Python calibration tool under `blood pressure monitor/tools/`.
- Accept calibration and independent verification samples through one normalized
  record contract.
- Fit a linear pressure model and derive voltage zero/sensitivity when applicable.
- Produce machine-readable JSON and point-by-point CSV reports.
- Add deterministic simulation that never opens serial ports or commands pressure.
- Add unit tests for fitting, independent verification, invalid inputs, and report
  generation.
- Run the dry run and require PASS with the configured synthetic tolerance.

Stage 3B, deferred until a suitable sensor is connected, will add EK-OmniProbe live
sampling, guarded parameter write/readback, and supported Ansur-driven pressure steps.

## Stage 3C: Sensor-Agnostic Calibration Foundation (2026-09-19, code complete)

Completed before the live BP Pump 2 calibration so the fitted sensor, and any
replacement sensor later, calibrates through the same protocol:

- Corrected `MPXV7007_SENSITIVITY_V_PER_KPA` 0.57f -> 0.286f (datasheet).
- Added `bp_cal.[ch]`: Flash-persisted linear calibration record
  (`slope_mmhg_per_unit`, `intercept_mmhg`) at 0x0807F800 with magic + CRC16,
  write/read-back verify, clear, and runtime validity.
- Pressure conversion routes through `BP_Cal_GetPressure_mmHg()`; full
  measurement unlocks only when a stored record is valid.
- USART3 commands: `cal`, `cal clear`, `cal write <slope> <intercept>`.
- Keil build 0 Error(s) 0 Warning(s); 17 static safety-contract tests + 4
  calibration-tool tests pass.

Pending: non-human hardware validation per validation.md (cal write/readback,
reset persistence, cal clear). After that, the BP Pump 2 two-point calibration
(0 / 50 mmHg) computes the real zero/gain and writes it with `cal write`.
# Active increment: capture export / replay (2026-10-25)

- [x] Add immutable capture context/revision/read API without numerical changes.
- [x] Add bounded exporter, command/safe-state gate and Keil source registration.
- [x] Add strict offline decoder, CSV/NDJSON conversion and production-C replay.
- [x] Real C lifecycle/roundtrip + malformed/lost/duplicate/cancel tests; old suite (70/70).
- [x] Fresh Keil0error0warning; RAM/stack gate; contracts and non-human procedure.
- [x] Flash and non-human target export/timing/stop validation under separate authorization.
- [x] Acquire a new complete failed/valid waveform and investigate feature selection.
- [x] Runtime stack watermark implementation, tests, Keil build/budget, idle
  baseline and complete Standard BP/calculation/export-path target high-water
  validation (2026-10-28).
- [x] Three valid natural BP repeatability rounds with complete verified `/2` waveforms (2026-10-27).
- The separately authorized flash, calibration restoration and one50mmHg non-human
  validation are complete; no further flashing, inflation or calibration change is implied.

## 2026-10-28 offline Standard BP follow-up

- [x] Strictly reanalyze the seven saved 100/65 and 150/100 `/2` waveforms and
  preserve invalid results as evidence (see `validation.md`).
- [x] Add host-only, cadence-gated peak diagnostics and measured-rate capture
  capacity projection; 80/80 host tests pass. Existing smoothed envelopes do
  not yield reliable 80 bpm beat peaks, so no new BP candidates are published.
- [x] Establish that target180 projects 2805-2972 points for four 150/100 runs
  and that enlarging arrays for target190 would exceed current SRAM headroom.
- [x] Design a bounded full-waveform acquisition/storage path for higher target
  pressure, with overflow vent and static RAM/stack proof. Non-human target190
  board validation is recorded below; 150/100 repeats remain budget-limited.
- [x] Add a separate host-only raw-voltage cadence diagnostic and validate it
  across saved 100/65, 120/80, and 150/100 reference conditions, including the
  single target190 capture. All16 strict exports show an approximately80bpm
  component; existing smoothed-envelope peaks still fail as beat markers.
  This does not authorize changing firmware MAP bands or SBP/DBP coefficients.
- [x] Add label-free host-only pulse estimation with explicit signal-quality
  rejection. Synthetic 60/80/100 BPM and adversarial noise/valve/unstable/tick
  cases pass; all16 retained 80 BPM exports estimate80 without feeding the
  setting into the algorithm. Keep the firmware pulse estimator unchanged
  until a different-rate physical reference and target resource review exist.

## 2026-10-28 bounded capture storage increment

- [x] Replace only the private per-sample timestamp storage with byte deltas;
  retain public sample snapshots and exact float32 inputs.
- [x] Set capacity to 3300, reject zero/>255 ms intersample gaps, preserve
  overflow invalidation and both callers' emergency-vent behavior.
- [x] Update strict host decoder, capacity diagnostics, real-C replay fixtures
  and timestamp/overflow regressions without changing `/2` wire semantics.
- [x] Run full host suite, fresh zero-warning Keil rebuild, project registration
  check, RAM >=2048 B headroom and static stack gate.
- [x] Record non-human wiring, calibration/zero preflight, low-pressure download
  gate, full export/replay and vent -> fresh zero -> seal procedure. Do not flash
  or inflate in this software increment.
- [x] Separately authorized compact-image board gate on2026-10-28: Keil
  download/verified calibration restore, target50 active stop, user-confirmed
  non-human120/80,80bpm baseline, complete2161-point `/2` strict export and
  bit-equal production-C replay. Both post-export stack reads1536/2560,
  saturated0; ADS errors0/recoveries0. Retain the initially rejected export
  preflight (sealed pressure rebound3.1-3.5mmHg) as failed-gate evidence.
- [x] With explicit user authorization, complete one non-human target190
  150/100 run, full `/2` strict export/production-C replay and two dynamic stack
  reads. No overflow occurred, but the capture used3153/3300 points and the
  cuff/tubing/fitting ratings remain undocumented.
- [ ] Before repeating target190: verify each connected pneumatic component's
  pressure rating and provide a repeatable capture budget with more than147
  points of worst-case margin; do not raise the pressure target.
- [x] Acquire a user-confirmed non-human100/65,80bpm capture on the compact
  image at target150. Preserve its complete2097-point `/2` as invalid BP
  evidence (`DBP86.6 > MAP86.3`), strictly decode and replay it, and take two
  post-export stack readings. No threshold or calibration change.
- [x] After one no-inflation timeout was safely vented and a target50 diagnostic
  passed, acquire one independent100/65 target150 round:2177 points/dropped0,
  118/68/56 valid1, complete `/2` strict decode and bit-equal production-C
  replay; two post-export stack checks1536/2560, ADS errors0. Keep the timed-out
  attempt and invalid earlier waveform as separate records; do not merge or
  relabel them.

## 2026-10-30 deflate-test closeout observation

- [x] Complete same-connection closeout of the armed non-human `deflate test`:
  `vent` -> ten fresh near-zero samples -> `seal`, then read `pins/status`.
- [x] Re-export and strictly decode the retained `/3` capture. The export has
  400 points over 9975 ms at exact 25 ms cadence, dropped0, 50 pulses at
  200 ms, `on_min=1`, `on_max=4`, no >=5 mmHg step, and end hash `1646158123`.
  The capture pressure was 55.6297 -> 54.0251 mmHg, so the 10 s timeout is
  inferred from the bounded test contract; the missed direct done line is not
  retroactively claimed. Artifact and SHA-256 are recorded in
  `connected-source-protocol-20261029.md`.
- [x] Confirm final pneumatic pins `PC0=LOW PC1=LOW PC8=HIGH pump=OFF` and
  fresh `0.0 mmHg`; retain the observed `state=EMERGENCY` latch as a status
  finding because `vent`/`seal` do not call `BP_Control_Reset()`.

## 2026-10-30 repeated deflate-test result

- [x] After MCU reset, pass the fresh 40-80 mmHg gate and capture the direct
  completion line: `reason=timeout`, `pulses=50`, final `on=4ms`.
- [x] Strictly decode the new `/3` export: 400 points, 9975 ms, exact 25 ms
  cadence, dropped0, pressure `53.9115 -> 47.0528 mmHg`, mean loss rate
  `0.688 mmHg/s`, end hash `3814808897`, and no >=5 mmHg step.
- [x] Record the bounded finding that the observed rate rose to about
  `1.0 mmHg/s` near the 4 ms cap but did not reach the 2.0 mmHg/s target.
  Do not change the cap or claim a hardware/software root cause from this
  single fixture round; the next diagnostic must separate control cap from
  pneumatic flow and BP source behavior.

- [x] Repeat the unchanged test once more. The second round also timed out at
  `on=4ms`, but measured only `0.208 mmHg/s` (`54.2523 -> 52.1790 mmHg`) versus
  `0.688 mmHg/s` in the first round. Both strict `/3` exports had 400 points,
  dropped0, 50 pulses and no >=5 mmHg step. The >3x rate difference is not
  repeatable enough to justify changing the algorithm or declaring a hardware
  fault; a sealed no-pulse baseline is the next diagnostic.


## 2026-10-31 15:46 通信恢复检查（负载断电）

- 用户在要求“BP Stop、断开泵阀负载电源、手动卸压”后回复“OK了”，据此记录人工安全收尾已完成；不追认此前失败的远程 vent/seal。
- EK TCP8765仍返回hello，serial写权限true；3秒0条新鲜压力，查询status在1.5秒内未收到桥接ACK，不能确认MCU/ADS当前状态。
- 证据：data/raw/preflight/bridge_recovery_20261031-154615.ndjson。只发status查询，未烧录、未执行泵阀切换。
- Windows枚举COM6（VID_FAED/PID_4870/MI_02）状态OK；不能据此认定CH340当前存在或断线。micu-omniprobe进程Responding=true不证明串口链路正常。
- 界面工具原生管道不可用（系统找不到指定的文件），无法代点EK重连；已请求用户断开/重连原串口并开始接收，负载继续断电。
- 待恢复新鲜接收与ACK后，先核对版本、校准、状态、故障和近零数据，再做负载断电PB8短时切换对照。读取根因仍未解决，暂无新的实测通过结论。


## 2026-10-31 15:48 重连及负载断电PB8对照

- 用户回复已完成EK重连。5s100新鲜样本/est0，IDLE/VALID/ONLINE/NONE，ADS0/0，安全引脚。未请求复位/下载，未观察新Boot，不能说明计数清零原因。
- 沿用用户已确认的泵阀负载断电状态，单次holdopen -> 名义250ms -> close（宿主起止约323ms）；PC8始终HIGH。试前/切换后各5s100条新鲜VALID est0，ADS仍0/0，无丢流。
- vent -> 十条连续新鲜近零 -> seal完成，末态PB8 HIGH/PC1 LOW/PC8 HIGH/泵OFF，stack1184/free2912/saturated0。
- 只通过负载断电逻辑切换门限。继电器5V控制侧供电范围待用户核对；单次对照不能认定线圈反冲或排除软件。没有新充气、固件或校准修改，带负载读取修复验收仍未通过。
- 原始、元数据及限制：data/reports/valve1_load_off_20261031-154839.md。后续保持负载断电，先核对模块型号、断电范围及抑制/供电布线。

## 后续操作者确认：断电范围

用户明确回复“只断了泵阀的12V”。据此补充：15:48负载断电对照期间继电器5V保持供电，隔离的是泵阀12V负载电源。保留上文当时未确认的历史描述，本条解除供电范围不明这一限制；不追认未独立观测的继电器触点或阀机械动作。

这一确认增强了12V负载接入/切换路径相关性的线索。15:41泵未运行的单阀切换后出现断流，而15:48断开12V后的控制切换及收尾没有复现故障；仍是两次不同状态下的单次对照，不能直接证明线圈反冲、触点拉弧、共电源/地线耦合中的具体原因，也不构成软件无缺陷或带负载修复验收。

下一步维持12V负载断电，核对继电器模块及触点侧/阀线圈接线、供电和共地结构、现有抑制器件及器件资料；在确认型号/极性/驱动要求前，不提供新的接线或指定抑制器件。不再无差别重复充气。

## 2026-10-31 17:39 requested retry: read-only gate

- Repeated zero-pressure readtest through EK GUI bridge: PASS_READ_ONLY n400/10000ms, ADS errors0/recoveries0, UART rx_errors0, NONE/IDLE/ONLINE/manualOFF; initial and final PB8 HIGH/PC1 LOW/PC8 HIGH.
- Five-second baseline100 and post-observation100 display records all est0; 409 fresh display records total. No actuator command, target/calibration change, firmware change or power return.
- Physical diode installation, pump branch isolation and current12V state are not newly confirmed. Loaded-switch retry remains pending; do not treat static PASS as repaired.
- Report: data/reports/readonly_retry_20261031-173923.md; raw SHA25635cba282f3748d1fc3cb8e7f392e15daf59ad0e103a31887e8d3b9c087e3120e.


## 2026-10-31 17:41 original-configuration retry FAILED

- User explicitly requested unchanged hardware/no diode retry. One target30/start, ceiling40/deadline15s; target echo30.8 then hold pressure read failure/emergency vent. No repeat inflation, firmware/calibration change or export.
- ADS first-failure retained stage5/HAL_BUSY2/TIMEOUT0x20/SR2.BUSY/CR1=0x0801, SCL/SDA HIGH, errors1/recoveries1; UART0. Corrupted target log wording retained. USER_STOP is terminal host stop, not original trigger.
- Independent stop then stable vent->60 fresh zeros over2950ms->seal; post5s100 zeros, safe pins/pumpOFF/manualOFF/ONLINE. Trial failed; closeout passed. Target30 retained, no power change claim.
- Report data/reports/original_config_low30_20261031-174142.md; raw SHA256 87d869bf073e0e400eb902c1a2ca686b0dbff1606bb868ec761f7252b8eaa4bb. Static read PASS does not establish loaded repair. Cause remains unresolved and task stays in_progress.


## 2026-10-31 17:47 powered valve-only switch FAILED

- User explicitly requests powered open/close under unchanged hardware. One holdopen/250ms nominal observation/close, no start/open, PC8 HIGH throughout commanded states; pump not physically isolated or independently observed.
- Fresh zero baseline100; immediately after close echo, corrupted sample-failed line and ADS HAL_BUSY/TIMEOUT, SR1 STOPF/SR2 BUSY, SCL/SDA HIGH. Errors1->2/recoveries1->2, UART0. Trigger does not require a pump start command or pressure rise; exact electrical/software mechanism remains unproved.
- Stop and independent stable closeout succeeded:60 fresh zeros/2942ms->seal, post5s100 zero, safe pins/pumpOFF/ONLINE/manualOFF. No repeat switch or firmware/calibration/target change.
- data/reports/valve1_live_20261031-174749.md; raw SHA256 01f180565aaf289a4631cbf137b5d3f39572edb06cd65b6803c33474b1adad04. Await suppression comparison; task in_progress.

## 2026-10-31 18:10 operator-reported diode comparison FAILED

- User reports instructed diode wiring complete and authorizes powered relay switching. Actual device model/polarity/breadboard continuity not independently verified. One holdopen/250ms nominal observation/close; no start/open, pump commanded OFF, no firmware/calibration/target changes.
- Initial NONE/IDLE/ONLINE, ADS0/0, UART0; baseline100 VALID zero. Close echo immediately followed by corrupted sample-failed text and HAL_BUSY/TIMEOUT/SR2.BUSY, SCL/SDA HIGH. Final ADS1/1 and SENSOR_READ: current wiring has not repaired the issue.
- STOP echo timed out; do not claim confirmed STOP execution. Independent vent echo ->60 fresh zero samples over2949ms->seal ->5s100 zeros, final safe pins/pumpOFF/manualOFF/ONLINE. Load12V not disconnected by agent.
- Syntax and existing guard3 tests passed; raw command/order/hash audit passed. Report data/reports/valve1_diode_20261031-181000.md; raw SHA256 aa0d8bf796c7e567aa8128daf6bf7e60246fd3d082ebf5ef8aa5cec6c43179d7. Task remains in_progress; inspect actual suppression connection before further loaded retries; no proof of exclusive hardware/software root cause.

## 2026-10-31 18:13 requested diode-config retry FAILED

- 18:12:47 preflight-only record rejected retained SENSOR_READ, with no actuator commands. Added explicit historical-fault retry option to existing host runner: recovered matched counters and stable fresh zero/counters are required; default remains strict. No reboot or firmware/calibration/target change.
- Baseline101 VALID zero, ADS1/1 unchanged. Exactly one holdopen/nominal250ms/close, pump commandedOFF. After close, corrupted failure line status1/HAL_ERROR err0x200 stage5/SR1=0x10/SR2=0/CR1=0x0101, SCL/SDA HIGH. ADS1->2/recoveries1->2; differs from previous HAL_BUSY/TIMEOUT details.
- STOP echo confirmed, independent vent->60 new VALID zero over2942ms->seal; post5s99 zeros, safe pins/pumpOFF/ONLINE/manualOFF. Terminal EMERGENCY/USER_STOP is host stop, not trigger. No load12V isolation claim.
- Syntax/guard3/raw order-and-hash audit passed. Report data/reports/valve1_diode_20261031-181318.md; raw SHA256 51d8084633863367992aefb86b99e2b3616475a374d4745a564437bc2d6869d4. Operator-reported diode configuration still does not solve loaded switching; actual suppression connection/effect remains unverified. Task in_progress.

## 2026-10-31 18:24 valve1 coil-disconnected comparison: NOT REPRODUCED once

- User corrects earlier COM wording to NO. Do not treat that historical wording as confirmed miswiring. User reports one valve1 lead disconnected/insulated while fully off, then confirms MCU followed by relay/load power returned. Physical isolation, supply voltage, diode/contacts not independently measured.
- Existing runner gains explicit --coil-disconnected metadata/profile; strict initial gate used, NONE/IDLE/ONLINE/VALID/UART0/ADS0/0. Before/after each100 new VALID zero samples, one holdopen/nominal250ms/close, PC8 commandedHIGH, no start/open or target/calibration/firmware change.
- No failed/corrupted/Boot lines, ADS errors/recoveries0 throughout. Vent->60 new zeros over2949ms->seal, post100 zeros, safe final pins/pumpOFF/manualOFF/IDLE/NONE/ONLINE. No subsequent12V disconnect claim; valve lead remains reported open/insulated.
- Syntax/guard3/raw command-counter-order-hash audit passed. Report data/reports/valve1_coil_disconnected_20261031-182417.md; raw SHA256 effd14f928dc5df1e8e96fab5b54ca52195df724185d8dd3ff286feb67646597.
- Supports loaded valve switching path involvement, not proof of a defective coil, unique interference mechanism, or software correctness. Loaded repair and original target/hold acceptance remain pending; task in_progress.


## 2026-10-31 18:37 valve-end diode wiring retry: NOT REPRODUCED once

- User confirms wiring completion after NO/valve-positive/diode-cathode common-junction instructions and OK after power-up instruction. Actual polarity, junction continuity, valve-end proximity and supply voltage not independently measured. Prior clarification: relay VCC/GND/IN retained during earlier coil-disconnected comparison.
- Existing strict runner unchanged. NONE/IDLE/ONLINE/VALID/UART0/ADS0/0; baseline100, one holdopen/nominal250ms/close (host command interval 0.285317s), post99 new VALID zero samples. Pump commandedOFF, not independently isolated/observed. No failure, corrupted or Boot lines; ADS0/0 throughout.
- Independent vent->60 fresh zero samples/2950ms->seal->post99 zeros. Final NONE/IDLE/ONLINE/manualOFF, UART0, safe pins,378 fresh samples. No target/calibration/firmware change or compile/download.
- Raw ACK/order/zero-before-seal/hash audit passed. Report data/reports/valve1_diode_20261031-183711.md; raw SHA256 672c6e88cae944a36b27cbfb1e4bb7d8e876ab4560c9e08e4fdcbcef211b211b. Single loaded comparison supports the wiring-change hypothesis but does not prove unique root cause, software correctness or full repair. Original30mmHg target/hold validation pending; task in_progress.


## 2026-10-31 18:39 valve-end diode low30 retry: read fault NOT REPRODUCED once

- User requests repeat after powered single-valve pass. Operator-reported valve-end diode common-junction configuration retained; actual connection, polarity, supply and mechanical switching not independently measured. Added explicit --valve-end-diode metadata/profile option to existing host runner; control logic unchanged. Syntax and offline guard3 pass.
- One target30/start, ceiling40/freshness2s/deadline15s. Initial/final NONE/IDLE/ONLINE/VALID/manualOFF/UART0/ADS0/0; target30.6 stopped pump, about1s hold, PWM/natural deflation completion. No read failure, corruption or Boot. 97 captured points/2400ms/25ms/dropped0; strict /3 decode/checksum passed;13 valve pulses,200ms period,on1..3ms.
- Hold pressure fell 30.6->20.1mmHg over1002ms host timestamps before PWM. This includes target-stop transient; no unique leak/valve/sensor cause established. Low30 yielded calculation failed/no valid BP; never treat flow completion as algorithm or medical validation.
- Stable vent->60 fresh VALID near-zero/2950ms->seal, post5s100 zero and extra3s zero. Safe final pins/pumpOFF; no new power-state claim. No firmware/calibration/compile/download; target30 retained.
- Audit commands/ACK/zero-before-seal/diagnostics/raw hash passed. Report data/reports/valve_end_diode_low30_20261031-183921.md; raw SHA256 df7db564f5f60a9eb9fa67ad2163aafde7fa5d970224d6d3f39b89b1c302adce; runner SHA256 3f7718a6de2ea0eda4937a896cb4fc99a3f4bb852fa8abfeb5a60eae16003ad3.
- Original loaded read-fault path passed once under new operator-reported wiring. Sealed static pressure-loss check and full measurement remain pending, cause not exclusively proved; task in_progress.


## 2026-10-31 18:42 low30 sealed5s repeat: acquisition OK, pressure loss remains

- One operator-authorized nonhuman target30/start; target echo30.2, peak display30.8. Immediately seal cancels pending hold/PWM, safe pins confirmed; no PWM-start line. Diode wiring/power/nonhuman configuration carried forward from user confirmation, not independently measured.
- Initial/final NONE/IDLE/ONLINE/VALID/manualOFF/UART0/ADS0/0;440 fresh records, no read failure/corruption/Boot.100 hold records22.3->17.6mmHg/4.949s,mean0.950mmHg/s; late window 18.8->17.6mmHg/2.949s,mean0.407mmHg/s. Earlier target-stop transient retained. Procedural hold completion is not a gas-tightness PASS; no unique pneumatic/mechanical/sensor cause proved by pin readback.
- Stable vent->60 fresh VALID nearzero/2950ms->seal->5s100 zero plus3s zero; final safe pins/pumpOFF. No firmware/calibration/build/download; target30 retained.
- Host hold runner now reuses stable closeout, separates STOP errors from independent vent, checks initial/final UART+ADS counters and retains diagnostics/config. Syntax+guard3 pass; raw command/ACK/noPWM/order/hash audit pass.
- Report data/reports/sealed_hold30_20261031-184235.md; raw SHA256 9a403785ba0a3c1dc88c4487e62aefaa5b2ae2b24130ef329d258cf9a382f863; runner SHA256 b35bf5a2a930f50b5a6820b5ddc2312d8d6b7ee95175cb2bf6960ac52c8c5412. Acquisition fault not reproduced; pressure-loss localization and full measurement remain pending, task in_progress.
## Target275 execution (2026-11-05)

- [x] Preserve280 hard stop; expose target275 and distinct version ID.
- [x] Full137 host tests; Keil rebuild0 errors/0 warnings; RAM headroom2048B,
  known stack1392B plus1024 reserve fits4096B.
- [x] Verify download and fresh version; restore82.326/-19.887 only after UNCAL;
  confirm target275 accepted/280 rejected, fresh calibrated zero and safe pins.
- [x] Complete one authorized nonhuman275 trial, retain all raw/metadata:
  reached275.3, SAMPLE_OVERFLOW at3300 points/82475ms/dropped1; trial failed.
- [x] Verify vent/fresh-zero/seal, target50, ADS/UART0. Protected export rejected;
  no complete capture, strict replay or full tail comparison possible. Preserve
  failure and report data/reports/standard255_195_target275_20261105.md.

## Target275 capacity4200 retained trial analysis (2026-11-05)

- [x] Resume exported trial `standard255_195_target275_capacity4200_20261105-111540`;
  3129 points/78200ms/dropped0, strict /3 checksum and all25ms ticks pass.
- [x] Current production-C replay matches target envelope/smooth/features/validity
  bit-for-bit; firmware calculation failed. Offline unchanged label-blind analysis
  yields candidate peak215mmHg,79.69BPM,73 beats,21 qualified bins55..255.
- [x] Compare prior250 trial: high-side qualified edge225->255, normalized tail
  height90.76%->64.62%,area85.71%->66.68%; high50% crossing still absent.
- [x] Record old firmware MAP80..100 search, SBP250/DBP150 upper limits and
  fixed -10/-5 output compensation as confirmed cross-preset obstacles; target
  chose MAP84.5 and SBP257 failed range gate. No BP accuracy PASS.
- [x] Preserve reported vent/fresh-zero/seal, restored target50, ADS/UART0 and
  safe pins from metadata; this continuation performed offline analysis only.
- Evidence: `data/reports/standard255_195_target275_capacity4200_20261105-111540.md`
  plus same-prefix CSV, verified transfer, replay, diagnostics, adaptive and PNG.
- Next: general envelope extraction validation using retained data and independent
  repeats; preserve missing-crossing abstention and275/280 pressure boundaries.

# 2026-11-05 shared envelope increment execution

- [x] Share extraction and binning between adaptive inference and diagnostics.
- [x] Add four-origin stability gate and explicit diagnostic failure propagation.
- [x] Test fragment/tick/whole-beat rejection, competing peaks, label independence,
      bin-origin sensitivity, synthetic range/cadence and retained real data.
- [x] Audit six historical complete captures plus Preset4 target250/275; preserve
      original failures and reports, hash inputs, emit a new report and plot.
- [x] Run full host/Python checks; decide explicitly whether to port/flash.
- [x] Update code-spec and session progress. No device I/O in this increment.

Outcome:146/146 tests pass, including actual production-C host regressions.
13 retained attempts:8 complete,5 historical failures;5 envelope candidates and
3 complete-capture abstentions. Latest target275 baseline215mmHg changes to
212.5..230 across four origins (17.5 span > declared15), so primary peak is null.
Six synthetic fixed profiles and user-defined83 remain candidates; lowest40
profile remains unsupported because of low-side coverage. No independent
accuracy claim. Shared longest-contiguous-window processing discards late
20mmHg boundary reentries rather than concatenating them for Welch.

Deployment decision:not ready for firmware; no C/headers/uvprojx edits, Keil
rebuild, download, serial writes, pressure round or calibration changes. Known
on-device80..100 MAP window,-10/-5 compensation and short FFT remain open.
Artifacts:data/reports/standard_bp_envelope_stability_20261105.{md,json,png},
plus .manifest.json/.before.json/.adaptive.json/.diagnostics.json. Plot visually
checked. Code/source hashes and reproduction commands are included. Repo still
has no HEAD and all project files pre-exist untracked; no initial commit or
task archival was performed. Broader bringup task stays in_progress.

