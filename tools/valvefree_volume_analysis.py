"""Turn the panel readings from the valve-free test into a volume, for a single full-stroke pull.

The circuit:

    BP Pump 2 Pressure Port --- tee --- cuff (on its mandrel)
                                 \\---- 20 mL syringe

Why a single pull to the mechanical end stop, rather than pulling to a graduation:

  - nothing has to be read under pressure, so there is no "aim at 20" to get wrong
  - the end stop is a physical position, so the same volume is reproduced every time
  - the cost is that the full-stroke volume is not exactly the nominal 20 mL, so it enters with a
    tolerance instead of a reading error. At 21 mL nominal +-1.5 mL that is 7 percent of G, which
    propagates to 7 percent of V - comparable to the 0.5 mL misread it replaces, and far less
    likely to happen

The price of one pull instead of two: there is only ONE equation, so the two-equation
cross-check that used to expose a misread is gone. Two substitutes:

  1. the round trip. Pull to the end, then push back to 0. In a sealed loop the pressure must
     return to the line it started on. If it does not, air entered or the volume did not return,
     and the reading is not evidence.
  2. two readings per state, 60 s apart, so the leak is measured rather than assumed.

Usage, times in seconds counted from pressing <START>:

    python tools/valvefree_volume_analysis.py --p0 185 --p0b 179 --t0 90 --t1 150 \
        --p2 80 --p2b 74 --t2 240 --t3 300 --g-pull 21 --g-sigma 1.5 \
        [--p3 172 --p3b 166 --t4 390 --t5 450]

The pressures are integers copied off the display, so each carries +-0.5 mmHg. That quantisation is
propagated; it turns out to be a small term compared with the tolerance on the full-stroke volume and
with the atmospheric pressure.
"""
import argparse
import math

MANIFOLD_CC = 20.0        # manual Figure 3-1: main manifold approximately 20 cc, always in series
CANISTER_CC = 290.0       # opened only to simulate an internal adult cuff; expected closed here
TUBING_CC = 6.5           # hose, tee, luer between the instrument port and the bladder
QUANTUM = 0.5             # integer display


def parse_args():
    p = argparse.ArgumentParser(description='volume from panel readings, single full-stroke pull')
    p.add_argument('--p0', type=float, required=True, help='gauge at the start plate, plunger home')
    p.add_argument('--p0b', type=float, required=True, help='gauge 60 s later, constant volume')
    p.add_argument('--t0', type=float, default=90.0, help='time of p0, seconds after START')
    p.add_argument('--t1', type=float, default=150.0, help='time of p0b')
    p.add_argument('--p2', type=float, required=True, help='gauge after the pull settles')
    p.add_argument('--p2b', type=float, required=True, help='gauge 60 s later, constant volume')
    p.add_argument('--t2', type=float, default=240.0, help='time of p2')
    p.add_argument('--t3', type=float, default=300.0, help='time of p2b')
    p.add_argument('--p3', type=float, default=None, help='optional: gauge after pushing back home')
    p.add_argument('--p3b', type=float, default=None, help='optional: 60 s later')
    p.add_argument('--t4', type=float, default=None, help='time of p3')
    p.add_argument('--t5', type=float, default=None, help='time of p3b')
    p.add_argument('--g1', type=float, default=0.0, help='graduation before the pull, mL')
    p.add_argument('--g-pull', type=float, default=20.0,
                   help='graduation after the pull: nominal full stroke of the barrel')
    p.add_argument('--g-sigma', type=float, default=1.5,
                   help='tolerance on the full-stroke volume, mL. Use 0.5 if a graduation was read')
    p.add_argument('--atm', type=float, default=760.0, help='local atmospheric pressure, mmHg')
    p.add_argument('--t-pull', type=float, default=None, help='instant of the pull, defaults to t1')
    return p.parse_args()


def line_through(t_a, p_a, t_b, p_b):
    slope = (p_b - p_a) / (t_b - t_a)
    return slope, p_a - slope * t_a


def volume(p_abs_1, g1, p_abs_2, g2):
    return (p_abs_2 * g2 - p_abs_1 * g1) / (p_abs_1 - p_abs_2)


def main():
    a = parse_args()
    g1, g2 = a.g1, a.g_pull
    t_pull = a.t_pull if a.t_pull is not None else a.t1

    print('=== the readings ===')
    print()
    print(f'  home, plunger at {g1:g} mL : {a.p0:g} mmHg at {a.t0:g} s, '
          f'{a.p0b:g} mmHg at {a.t1:g} s')
    print(f'  pulled, plunger at {g2:g} mL: {a.p2:g} mmHg at {a.t2:g} s, '
          f'{a.p2b:g} mmHg at {a.t3:g} s')
    if a.p3 is not None:
        print(f'  pushed home again        : {a.p3:g} mmHg at {a.t4:g} s, '
              f'{a.p3b if a.p3b is not None else float("nan"):g} mmHg at '
              f'{(a.t5 if a.t5 is not None else float("nan")):g} s')
    print(f'  pull taken at {t_pull:g} s, atmospheric pressure {a.atm:g} mmHg')
    print()

    s1, i1 = line_through(a.t0, a.p0, a.t1, a.p0b)
    s2, i2 = line_through(a.t2, a.p2, a.t3, a.p2b)
    rate1, rate2 = -s1 * 60.0, -s2 * 60.0

    print('=== drift in each state, i.e. the leak ===')
    print()
    print(f'  home   {rate1:+7.2f} mmHg/min      pulled {rate2:+7.2f} mmHg/min')
    if rate1 <= 0.0:
        print('  WARNING: the pressure did not fall at all in the home state. Either the settle time')
        print('  was too short and the gas was still warming, or a reading was misremembered.')
    if abs(rate1 - rate2) > 0.60 * max(abs(rate1), abs(rate2), 1.0):
        print('  NOTE: the two rates differ by more than 60 percent. A pinhole leak drains a smaller')
        print('  volume faster, so some difference is expected - the pulled state has the larger')
        print('  volume and should leak slower. If the pulled state leaks FASTER, suspect air')
        print('  getting in past the plunger while it was being pulled.')
    print()

    p1 = i1 + s1 * t_pull
    p2 = i2 + s2 * t_pull
    print('=== both states referred to the instant of the pull ===')
    print()
    print(f'  home   {p1:8.2f} mmHg  ({s1 * (t_pull - a.t1):+6.2f} from the {a.t1:g} s reading)')
    print(f'  pulled {p2:8.2f} mmHg  ({s2 * (t_pull - a.t2):+6.2f} from the {a.t2:g} s reading)')
    print()

    v_leak = volume(a.atm + p1, g1, a.atm + p2, g2)
    v_last = volume(a.atm + a.p0b, g1, a.atm + a.p2b, g2)
    print('=== volume ===')
    print()
    print(f'  with the leak removed      V = {v_leak:6.1f} cc')
    print(f'  from the last pair only    V = {v_last:6.1f} cc   '
          f'(leak correction {v_last - v_leak:+.1f} cc)')
    print()

    # --- uncertainty ------------------------------------------------------------
    d_abs = (a.atm + p1) - (a.atm + p2)
    dv_dp1 = -g2 * (a.atm + p2) / d_abs ** 2
    dv_dp2 = g2 * (a.atm + p1) / d_abs ** 2
    sd_point = QUANTUM / math.sqrt(3.0)
    span1 = max(abs(a.t1 - a.t0), 1e-6)
    span2 = max(abs(a.t3 - a.t2), 1e-6)
    sd_p1 = math.hypot(sd_point, sd_point * math.sqrt(2.0) / span1 * abs(t_pull - a.t0))
    sd_p2 = math.hypot(sd_point, sd_point * math.sqrt(2.0) / span2 * abs(t_pull - a.t2))
    sd_display = math.hypot(dv_dp1 * sd_p1, dv_dp2 * sd_p2)
    sd_g = abs(v_leak) * a.g_sigma / g2
    sd_total = math.hypot(sd_display, sd_g)

    print('=== uncertainty ===')
    print()
    print(f'  integer display, four readings   +-{sd_display:5.2f} cc')
    print(f'  full-stroke volume +-{a.g_sigma:g} mL       +-{sd_g:5.2f} cc   '
          f'({sd_g / abs(v_leak) * 100:4.1f} %)')
    print(f'  combined                          +-{sd_total:5.2f} cc   '
          f'({sd_total / abs(v_leak) * 100:4.1f} %)')
    print()
    if a.g_sigma >= 1.0:
        print('  the dominant term is not the display but the fact that a full stroke is not exactly')
        print('  the nominal capacity. If the stopper stopped at a readable graduation, rerun with')
        print('  --g-pull at that value and --g-sigma 0.5 and the volume tightens about fivefold.')
        print()

    # --- round trip -------------------------------------------------------------
    if a.p3 is not None and a.t4 is not None:
        print('=== round trip: is the loop still sealed? ===')
        print()
        expected = i1 + s1 * a.t4
        diff = a.p3 - expected
        print(f'  after pushing home at {a.t4:g} s: measured {a.p3:g} mmHg')
        print(f'  the start-state line extrapolated to that instant predicts {expected:8.2f} mmHg')
        print(f'  difference {diff:+7.2f} mmHg')
        print()
        print('  This difference alone does not settle anything. A pressure-dependent leak drops')
        print('  more slowly at low pressure, so the constant-rate extrapolation over-predicts the')
        print('  drop and leaves the measured value HIGHER - the same sign that air ingress would')
        print('  produce. So the difference is reported, not judged.')
        print()
        if a.p3b is not None and a.t5 is not None:
            s3, _ = line_through(a.t4, a.p3, a.t5, a.p3b)
            rate3 = -s3 * 60.0
            print('  the discriminating measurement is the drift rate at the RETURNED home state:')
            print()
            print(f'    start  home plateau  {rate1:+7.2f} mmHg/min (at about {a.p0:g} mmHg)')
            print(f'    after  home plateau  {rate3:+7.2f} mmHg/min (at about {a.p3:g} mmHg)')
            print()
            if rate3 > rate1 + 1.5:
                print('  FAIL: the loop leaks faster after being pulled and pushed back. A pinhole')
                print('  leaks more slowly at lower pressure, so this cannot be the same leak. Air is')
                print('  getting in past the plunger. Replace the syringe and repeat.')
            elif rate3 > rate1 + 0.5:
                print('  WARN: the returned drift is slightly higher than the start drift, and the')
                print('  returned pressure is lower, so it should have been slightly lower. Marginal;')
                print('  repeat if the number matters.')
            else:
                print('  PASS: the returned drift is not larger than the start drift, at a lower')
                print('  pressure. That is what a fixed leak looks like, so no air got past the')
                print('  plunger and the full stroke is reproducible.')
            print()
        else:
            print('  Without a second reading after the return, the drift rates cannot be compared,')
            print('  and the pressure difference above cannot be interpreted. Read twice.')
            print()

    # --- atmosphere -------------------------------------------------------------
    print('=== how much the assumed atmospheric pressure matters ===')
    print()
    print('  the gas law needs absolute pressure, so p + atm. This is the largest systematic term.')
    print()
    print(f'  {"assumed atm":>12} {"V (cc)":>9} {"delta":>8}')
    for atm in (a.atm - 30, a.atm - 15, a.atm, a.atm + 15, a.atm + 30):
        v = volume(atm + p1, g1, atm + p2, g2)
        print(f'  {atm:12.0f} {v:9.1f} {v - v_leak:+8.1f}')
    print()
    print('  read the local value off a weather app rather than assuming sea level: 15 mmHg of')
    print('  error in atm moves this result by the amount in the delta column.')

    print()
    print('=== interpretation ===')
    print()
    print(f'  measured loop = instrument manifold + tubes + bladder + syringe hub = {v_leak:.0f} cc')
    print()
    if v_leak > 300.0:
        print(f'  above 300 cc, so the {CANISTER_CC:.0f} cc canister looks like it is IN circuit.')
        print('  The manual describes it as an internal-cuff simulation feature, which a static')
        print('  SOURCE test should not need, but the number says otherwise. Both 20 and 290 are')
        print('  nominal manual figures, so this branch gives an upper bound only:')
        print(f'      bladder <= {v_leak - MANIFOLD_CC - CANISTER_CC - TUBING_CC:.0f} cc')
    else:
        print(f'  below 300 cc, consistent with only the {MANIFOLD_CC:.0f} cc manifold in series.')
        print(f'      bladder ~ {v_leak - MANIFOLD_CC - TUBING_CC:.0f} cc '
              f'+-{sd_total:.0f}')
        loop = v_leak - MANIFOLD_CC + 6.0
        print(f'      dataset loop ~ {loop:.0f} cc   '
              f'(adds valve 1 / pump dead ends, valve 2 and the sensor port)')
        print()
        print('  the figures already on file:')
        print('      gas law from the panel pulse volume   158 cc, assumes the panel figure is right')
        print('      leak ratio against the syringe test   109-219 cc, assumes one leak path')
        print(f'      this test                             {loop:.0f} cc +-{sd_total:.0f}, '
              f'assumes only atm')
    print()
    print('=== what this does not establish ===')
    print()
    print('  it is static: no pulses, so it says nothing about dynamic response or about whether')
    print('  the panel pulse volume is correct. And it disturbed the cuff wrapping, so the wrapping')
    print('  has to be redone - and re-measured - before any further dataset round.')


if __name__ == '__main__':
    main()
