"""Prediction card for tmp/dataset_loop_step_20261109.py.

Prints what the pulled-side reading should be for each candidate loop volume, so
that the operator can tell WHILE the run is happening whether the plunger actually
moved. A pull that did nothing looks exactly like a working pull if you are only
watching the numbers scroll by, and that mistake costs a whole run.

    P_pulled = (atm + P_home) * V / (V + 26) - atm

The 26 mL is the full stroke the operator measured at rest. Using a nominal 20 mL
here would put every prediction 55 mmHg off at V = 150, which is exactly the kind
of error the card exists to prevent.
"""
import sys

ATM = 760.0
STROKE = 26.0

CANDIDATES = [
    (362.0, 'cuff is huge, canister closed in SOURCE mode'),
    (300.0, 'upper end of a plausible hard-core cuff loop'),
    (150.0, 'the earlier gas-law estimate'),
    (123.0, 'cuff 103 cc plus tubing and tee'),
    (72.0, 'cuff 52 cc, canister in circuit in both modes'),
]

def main():
    home_values = [int(a) for a in sys.argv[1:]] or [200, 240, 280, 300]
    print(f'full stroke {STROKE:.0f} mL, atmosphere {ATM:.0f} mmHg\n')
    header = '  '.join(f'{h:>6}' for h in home_values)
    print(f'  {"loop V":>9} {header} mmHg   makes sense at 240?')
    for v, why in CANDIDATES:
        cells = []
        for h in home_values:
            p = (ATM + h) * v / (v + STROKE) - ATM
            cells.append(f'{p:6.1f}' if p >= 5.0 else ' CLAMP')
        at240 = (ATM + 240) * v / (v + STROKE) - ATM
        verdict = 'yes' if at240 >= 5.0 else 'no - needs a higher target'
        print(f'  {v:7.0f} cc {"  ".join(cells)}   {verdict:24} {why}')
    print()
    print('  the minimum target that keeps a given loop above the clamp:')
    for v in (72.0, 123.0, 150.0, 300.0, 362.0):
        need = (ATM + 5.0) * (v + STROKE) / v - ATM
        print(f'    V = {v:5.0f} cc  ->  target >= {need:6.1f} mmHg')
    print()
    print('  so 240 mmHg is the best single choice. Everything from 123 cc up reads')
    print('  positive, and if the reading DOES clamp that is itself the answer for the')
    print('  small-loop branch - repeat at 275 mmHg, the firmware ceiling, to get a')
    print('  number instead of a floor. 72 cc needs 282 mmHg, which the firmware will')
    print('  not accept (max safe = 280), so a clamped result at 275 stays a bound:')
    print('  "below 123 cc", which still rules out the cuff being huge.')
    print()

    print('how to read it during the run')
    print('  the first pulled sample appears within a second of the pull. If it is close to the')
    print('  starting pressure, or if it only drifts down slowly, the plunger did not move.')
    print('  If the loop is small the reading may hit 0.0 and stay there - that is the clamp,')
    print('  and the run has to be repeated at a higher target rather than trusted.')
    print()

    print('what each outcome means for the dataset')
    print('  near 340 cc   the cuff holds about 315 cc. The dataset circuit is then 362 cc and')
    print('                the panel pulse volume of 0.55 cc is 2.4 times smaller than the gas')
    print('                it actually displaces. Every volume statement in the dataset needs')
    print('                that factor.')
    print('  near  50 cc   the cuff holds about 40 cc and the canister was in circuit in SOURCE')
    print('                mode. The dataset circuit is then about 72 cc, and the 362 cc number')
    print('                must not be quoted as a dataset property at all.')
    print('  in between    neither nominal figure explains it, so the circuit is not what the')
    print('                schematic says. Fix the plumbing before measuring again.')
    print()
    print('  the previous gas-law estimate of 153 cc is wrong in BOTH branches, which is why')
    print('  this run matters more than refining it.')


if __name__ == '__main__':
    main()
