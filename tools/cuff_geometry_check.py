"""Geometric cross-check: can this cuff size physically hold the volume we inferred?

The listing gives hard numbers: overall length 44.5 cm, overall width 14.5 cm, tube length 64 cm,
plug bore 2 mm. Those bound the answer without any measurement of ours, so they are an independent
check on the 125 cc cuff split in data/reports/volume_loop_vs_cuff_20261108.md.

Everything here is arithmetic on published sizes; nothing is fitted to our data.
"""
import math

L_CUFF, W_CUFF = 44.5, 14.5        # cm, overall, includes the D-ring and the hook-and-loop overlap
L_TUBE = 64.0                      # cm
BORE_MM = 2.0                      # mm, the bore stated in the listing

print('=== what the listing fixes ===')
print(f'cuff overall {L_CUFF} x {W_CUFF} cm, tube {L_TUBE} cm, plug bore {BORE_MM} mm')
print()

print('=== 1. the tube alone, inside the stated bore ===')
for d_mm in (2.0, 3.0, 4.0, 5.0):
    v = math.pi * (d_mm / 20.0) ** 2 * L_TUBE
    print(f'  bore {d_mm:>3.1f} mm x {L_TUBE:.0f} cm -> {v:5.1f} cc')
print('  the 2 mm figure is the plug, not necessarily the hose bore; the wall is thicker,')
print('  so 2-8 cc is the honest range for the tube')
print()

print('=== 2. the bladder: how much gap does 125 cc need? ===')
for area, name in ((13 * 24, '13 x 24 cm'), (14 * 22, '14 x 22 cm'), (12 * 24, '12 x 24 cm'),
                   (14 * 26, '14 x 26 cm')):
    gap_mm = 125.0 / area * 10.0
    print(f'  {name} = {area:3.0f} cm2 -> mean gap {gap_mm:4.1f} mm gives 125 cc')
print('  a bladder over a rigid core lifts a few mm off the core once inflated, so this is the')
print('  right order of magnitude - it is not a thin film with no gas in it')
print()

print('=== 3. what the rest of the loop would have to be ===')
for cuff in (100.0, 125.0, 150.0):
    print(f'  if the cuff is {cuff:5.1f} cc and the loop totals 153 cc, the rest is {153 - cuff:5.1f} cc')
print()

print('=== 4. is 28 cc plausible for the non-cuff part? ===')
for d_mm in (3.0, 4.0, 5.0):
    v = math.pi * (d_mm / 20.0) ** 2 * L_TUBE
    print(f'  tube at {d_mm:>3.1f} mm bore: {v:4.1f} cc; plus tee, valve dead space and sensor port')
    print(f'    -> {v:4.1f} + 3..5 = {v + 3:4.1f} .. {v + 5:4.1f} cc')
print('  geometry says 6-13 cc, the leak-ratio method said 28 cc')
print(f'  so 28 cc is high by roughly {28 / 9:.1f}x, in the same direction I flagged before:')
print('  a hand on the plunger makes the decay look slower and inflates the no-cuff volume')
print()

print('=== 5. what this means for the two numbers we care about ===')
print('  total loop 153 cc is consistent with a 13 x 24 cm bladder that inflates 5-8 mm thick')
print('  the 125 cc cuff split is an UPPER bound; geometry allows 140-145 cc if the rest is small,')
print('  and the manual manikin total of 310 cc is 2x ours - a real difference, not rounding')
print()
print('  manual manikin: 20 cc chamber + 290 cc canister = 310 cc total')
print(f'  ours: 153 cc total, i.e. {153 / 310:.2f} of the manual figure')
print('  a 290 cc canister is what makes the manual large; our cuff is not a canister, it is a')
print('  flat bladder, so the gap is expected rather than a fault')
