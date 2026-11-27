"""Is a mean really over the limit, or cannot the sample tell?

The estimator output is judged against ``|mean| <= 5 mmHg`` and ``sd <= 8 mmHg``.
When a cell lands a tenth of a millimetre over the mean limit the interesting
question is not "by how much", it is "could this sample have told the two apart".
This tool answers that with a Student-t interval and nothing else:

* the interval of the mean,
* whether the limit sits inside it (in which case the cell is *not resolved*,
  which is a different verdict from *fails*),
* how many more rounds would narrow the interval enough for the upper end to fall
  below the limit -- and, when the observed mean is already above the limit, why
  no number of rounds can do that (the interval shrinks *around* the mean).

It never reads a corpus, never runs the estimator and never touches hardware: it
is arithmetic on summary statistics, so the numbers can be audited by hand.

    python tools/sbp_mean_ci.py
    python tools/sbp_mean_ci.py --cell "P5/SBP:39:5.15:5.09" --cell "P7/SBP:36:5.05:6.46"
    python tools/sbp_mean_ci.py --limit 5 --cell "MAP:155:4.9:5.4"

Defaults reproduce the two cells that ``data/reports/precision_levers_20261115.md``
section 1.2 discusses, i.e. the last published scoring run with the two
unestablished-panel rounds retired (firmware 61ca1da3..., 11-09 onwards).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIMIT = 5.0
DEFAULT_CELLS = ("P5/SBP:39:5.15:5.09", "P7/SBP:36:5.05:6.46")


def t_quantile_975(df: int) -> float:
    """Two-sided 95% Student t critical value (Cornish-Fisher, ~1e-3 for df >= 10)."""
    z = 1.959963985
    a = z
    return (
        a
        + (a**3 + a) / (4 * df)
        + (5 * a**5 + 16 * a**3 + 3 * a) / (96 * df**2)
        + (3 * a**7 + 19 * a**5 + 17 * a**3 - 15 * a) / (384 * df**3)
    )


def rounds_for_upper_below(n: int, mean: float, sd: float, limit: float) -> int | None:
    """Rounds needed for mean + t*SE to fall below the limit, mean and sd fixed.

    ``None`` means the observed mean is already at or above the limit: the
    interval only shrinks around that mean, so no sample size reaches below.
    """
    if abs(mean) >= limit:
        return None
    for candidate in range(n, 2_000_000):
        if abs(mean) + t_quantile_975(candidate - 1) * sd / math.sqrt(candidate) < limit:
            return candidate
    return None


def describe(name: str, n: int, mean: float, sd: float, limit: float) -> dict:
    se = sd / math.sqrt(n)
    t = t_quantile_975(n - 1)
    half = t * se
    lo, hi = mean - half, mean + half
    overshoot = abs(mean) - limit
    needed = rounds_for_upper_below(n, mean, sd, limit)
    return {
        "cell": name,
        "n": n,
        "mean": mean,
        "sd": sd,
        "se": round(se, 4),
        "t": round(t, 4),
        "ci95": [round(lo, 2), round(hi, 2)],
        "limit_inside_ci": lo < limit < hi,
        "half_width_mmhg": round(half, 3),
        "overshoot_mmhg": round(overshoot, 2),
        "overshoot_in_se": round(overshoot / se, 3),
        "rounds_for_upper_below_limit": needed,
        "rounds_to_halve_half_width": int(math.ceil(n * 4)),
    }


def print_block(row: dict, limit: float) -> None:
    print(f"{row['cell']}: n={row['n']} mean={row['mean']:+.2f} sd={row['sd']:.2f}")
    print(
        f"  SE {row['se']:.3f}, t(df={row['n'] - 1}) {row['t']:.3f}, "
        f"half-width {row['half_width_mmhg']:.2f} mmHg"
    )
    print(
        f"  95% CI  [{row['ci95'][0]:+.2f}, {row['ci95'][1]:+.2f}]   "
        f"contains {limit}: {row['limit_inside_ci']}"
    )
    print(
        f"  overshoot {row['overshoot_mmhg']:+.2f} mmHg = "
        f"{row['overshoot_in_se']:+.2f} SE"
    )
    if row["rounds_for_upper_below_limit"]:
        print(
            f"  rounds for the CI to clear {limit}: "
            f"about {row['rounds_for_upper_below_limit']}"
        )
    else:
        print(
            f"  rounds for the CI to clear {limit}: none - the observed mean is "
            f"already beyond the limit, so the interval shrinks around it"
        )
    print(f"  rounds to halve the half-width: about {row['rounds_to_halve_half_width']}")
    print()


def parse_cell(text: str) -> tuple[str, int, float, float]:
    name, n, mean, sd = text.split(":")
    return name, int(n), float(mean), float(sd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--cell",
        action="append",
        metavar="NAME:N:MEAN:SD",
        help="cell to describe; repeatable (default: the two P5/P7 SBP cells)",
    )
    parser.add_argument("--limit", type=float, default=DEFAULT_LIMIT)
    parser.add_argument(
        "--out",
        type=Path,
        help="write the per-cell description as JSON",
    )
    args = parser.parse_args()

    cells = [parse_cell(text) for text in (args.cell or list(DEFAULT_CELLS))]
    report = {}
    for name, n, mean, sd in cells:
        if n < 2:
            parser.error(f"{name}: needs at least two rounds")
        row = describe(name, n, mean, sd, args.limit)
        report[name] = row
        print_block(row, args.limit)

    unresolved = [name for name, row in report.items() if row["limit_inside_ci"]]
    print(
        f"cells whose interval still contains the {args.limit:g} mmHg limit: "
        f"{unresolved if unresolved else 'none'}"
    )
    if unresolved:
        print(
            "Those cells are not resolved at this sample size. Reporting them as "
            "'fails' overstates what the sample supports; reporting 'passes' would "
            "too. Say 'not resolved' and give the interval."
        )

    if args.out:
        out = args.out if args.out.is_absolute() else ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
