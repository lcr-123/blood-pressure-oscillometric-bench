# Retained BP capture batch audit

This is a retrospective, simulator-only exploration. These captures were used
during method development and are **not** an independent held-out set.
Panel settings are not encoded in the export; do not infer labels from filenames.
Fitted peaks are diagnostic candidates, not reference MAP or clinical BP.

Run from the repository root:

```powershell
python 'blood pressure monitor/tools/bp_capture_batch_report.py' --through 20261029-104132 --output '.trellis/tasks/06-19-bp-firmware-bringup/capture-batch-audit.md'
```

Inputs: `tmp/capture_export_*.verified.ndjson`, sorted by path, through `20261029-104132` inclusive.
Each input passes the strict `bp_capture.decode` count/order/FNV check.
SHA-256 below identifies the exact input bytes. `upper=170` when the first cuff pressure
is >=150 mmHg, otherwise 130; step padding=40 samples (1 s). The study
uses the existing exploratory beat-height and robustness settings.
MAP/DBP values are raw firmware features before fixed output offsets.
DBP time is the first three-sample <=60% smoothed-envelope crossing
after MAP, using MCU ticks. `calc=2` means firmware valid, `3` invalid,
and `0` uncalculated; it is independent of the study screen.

Total: 28 complete verified exports; calculated 27 (valid 17, invalid 10), uncalculated 1.
MAP-to-DBP <=0.75 s: 22/25 with DBP found; firmware valid 14/17, invalid with DBP 8/8.
DBP raw pressure > MAP: 8 captures. These counts describe this selected archive only; 0.75 s
is one beat at 80 BPM, not a validated rejection threshold.

| Export | SHA-256 | n | calc | upper | MAP | DBP | gap s | study | screen | fitted peak | reasons |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |
| 20261025-210212 | 7ec23890a0f0e6d75456b820be01048f624a543541a4bdcd221abf3512733daa | 321 | 3 | 130 | 0.00 | - | - | pulse_unreliable | - | - | - |
| 20261025-211153 | f5a57067aeb07cf1063c784740e539b81695a4d5466fc053ae31a0a911741969 | 2089 | 2 | 130 | 97.01 | 95.28 | 0.475 | insufficient_bins | - | - | - |
| 20261026-180333 | f029994da7f4b97a43afeaf00ca6acd9f1883f50f68914adb1586ae6f2ef3bbd | 377 | 3 | 130 | 0.00 | - | - | pulse_unreliable | - | - | - |
| 20261026-180916 | ef9ffcfafc5c5b6e4067cf1ba57564c748a673215ce40b3db38077cedbb8cd4c | 2225 | 2 | 130 | 97.05 | 96.21 | 0.550 | unstable_peak | pass | 95.29 | - |
| 20261027-214442 | 18aa57741021c37b438a0f880a702318278d8c850a0cef76e393b8a93a1f15c7 | 2129 | 2 | 130 | 88.39 | 87.67 | 0.425 | diagnostic_only | reject | 97.84 | weak_peak_support |
| 20261027-220211 | 685bec39f59913ce02c9484b8456d35e47ab5c4784c36158132a3d9fdc5461da | 1921 | 2 | 130 | 93.60 | 93.33 | 0.650 | diagnostic_only | reject | 93.39 | weak_peak_support |
| 20261027-220714 | dd620c1d3a9057bd87ebb8e624f000abb83a8f4e8e16035f393d6fb8a29e5fa4 | 1737 | 2 | 130 | 95.82 | 95.12 | 0.675 | diagnostic_only | reject | 95.38 | weak_peak_support |
| 20261028-113752 | aedc8496d9329d72d174898ff7139294c58160112e4590aa1fd6c49d6ae8889c | 2305 | 2 | 130 | 92.34 | 91.29 | 0.750 | diagnostic_only | pass | 94.79 | - |
| 20261028-114718 | 03ad60f96cafdf0a84b25df9da5d8d015dae18f732698781d7f67fc71291ee90 | 2233 | 3 | 130 | 80.37 | 80.45 | 0.725 | diagnostic_only | pass | 78.58 | - |
| 20261028-115410 | 89bfe025ec8637c2086d6752bc8985ecc29515440a631be97a983870cc797ab4 | 2377 | 3 | 130 | 95.13 | 95.73 | 0.400 | incomplete_oscillogram | reject | 114.63 | pressure_coverage_gap, jackknife_unstable |
| 20261028-115823 | 2755c630396a07a9c1ddb4bf37b5f2414227b8087e0f4100d8a4182321f17c3a | 2241 | 2 | 130 | 99.45 | 99.01 | 0.575 | diagnostic_only | reject | 115.92 | jackknife_unstable |
| 20261028-120531 | 81e344a83607a7ea1aa095b35ddf7856ada980b142d8795a8e277bacae219d44 | 2289 | 3 | 130 | 95.39 | 96.02 | 0.450 | diagnostic_only | pass | 79.21 | - |
| 20261028-120941 | 88bb03d574d1be30ad076fc62ed01ce726a0f7c6a15f41d7c839b468f03f54a7 | 2217 | 3 | 130 | 97.46 | 98.19 | 0.400 | diagnostic_only | pass | 78.96 | - |
| 20261028-121553 | 1c40dee09ec5512c0e53f87f29217f14f415ccf94ffa2182c3f70fbb37070e41 | 2379 | 2 | 130 | 81.74 | 76.29 | 1.650 | unstable_peak | pass | 78.24 | - |
| 20261028-123230 | 52d8a98d6ab6b3a36e2305ee79e0b72b34d3fb7ae434e2c50e441d50107d0480 | 2242 | 2 | 130 | 85.99 | 78.68 | 1.325 | diagnostic_only | pass | 116.11 | - |
| 20261028-163539 | e85e127f32d3ed866e73ecad42ea19f149a0b57771016733d9b35c22cf5e9782 | 2161 | 2 | 130 | 86.23 | 85.78 | 0.400 | insufficient_bins | - | - | - |
| 20261028-170426 | de7e1538ce54b10c931cb7d807d4c573e13d49b9129372af294db79e69400d8a | 3153 | 2 | 170 | 95.86 | 95.72 | 0.500 | unstable_peak | reject | 117.37 | weak_peak_support, pressure_coverage_gap, jackknife_unstable |
| 20261028-172032 | e7463918f7e00c9fff09025199cc296b5b3a82ca8552d8ea61e0616530f19315 | 2097 | 3 | 130 | 86.34 | 86.56 | 0.650 | diagnostic_only | reject | 78.30 | weak_peak_support |
| 20261028-173648 | 5cd58246945823d33912d03eb203bc6da2477501af29ee370cccc43504550bd0 | 2177 | 2 | 130 | 81.45 | 73.85 | 3.050 | unstable_peak | pass | 78.68 | - |
| 20261028-175901 | 92006ae0d4b1ebd867f18196be4f7b054f25befea1fae02353f6488a43cc56c0 | 1921 | 2 | 130 | 95.39 | 92.95 | 0.650 | unstable_peak | reject | 78.58 | weak_peak_support |
| 20261028-180524 | 2d9e388203aa2ddd64119718112538909f0a12b1c0d4caee80a070eddef28911 | 2009 | 2 | 130 | 85.29 | 84.74 | 0.700 | diagnostic_only | reject | 80.82 | weak_peak_support |
| 20261028-181030 | 585ce9fc8762357bfe29ac8724ffba1d7505191936f32efb27ca539763b454eb | 2057 | 2 | 130 | 91.30 | 91.09 | 0.675 | diagnostic_only | reject | 80.19 | weak_peak_support |
| 20261028-194221 | 25ccc60009b10eea10c23e2be01e564c5a76a3689a4ab416003574c2e82126fc | 2409 | 2 | 130 | 98.93 | 98.07 | 0.450 | incomplete_oscillogram | pass | 118.26 | - |
| 20261028-212208 | dd59e6bef7f19d4f0c4fa471db03cb267e07e239c1df14224909294cf258cad4 | 2185 | 3 | 130 | 90.78 | 91.46 | 0.350 | incomplete_oscillogram | reject | 130.00 | jackknife_unstable |
| 20261028-222538 | f000697056df8187c736a209417a03c5fa5655691e47026e3e2cd5e8c26bb7ed | 739 | 0 | 170 | - | - | - | calculation_incomplete | - | - | - |
| 20261028-223729 | b946e53581b51fad2428a87809879b7d066da051c2bc9185bbb9e072cb99fd39 | 2569 | 3 | 170 | 83.21 | 83.56 | 0.325 | diagnostic_only | reject | 123.23 | weak_peak_support |
| 20261028-232501 | f35735a3ed13ca0297a5b77f919d5257eccdc2e89fc9b858e028c6137bc5d5c9 | 2921 | 3 | 170 | 86.23 | 86.80 | 0.375 | diagnostic_only | pass | 117.02 | - |
| 20261029-104132 | 297f11ce8c447b316f72393f92e3d2abae075a8a08ef97131610d72c955a0ce3 | 2753 | 2 | 170 | 97.63 | 95.43 | 0.525 | incomplete_oscillogram | reject | 122.60 | weak_peak_support, jackknife_unstable |

## Interpretation

A near-immediate DBP threshold crossing appears in both firmware-valid and
firmware-invalid captures. The production `DBP > MAP` gate explains the
invalid flags where pressure ripples reverse the raw feature ordering,
but passing that gate does not establish a multi-beat falling envelope.
The independent beat-height screen and firmware validity answer different
questions; neither supplies a reference pressure trace or clinical truth.
Do not fit firmware MAP bounds, ratios, or offsets to this archive.
A separately collected and frozen set with known panel settings and
independent pressure evidence is needed before selecting a new algorithm.
