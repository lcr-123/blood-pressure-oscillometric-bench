# -*- coding: utf-8 -*-
"""在 raw log 中定位 est 值窗口：python find_est_window.py <log> <lo> <hi>"""
import sys, statistics as st

log = sys.argv[1]
lo, hi = float(sys.argv[2]), float(sys.argv[3])

rows = []
with open(log, encoding='utf-8') as f:
    f.readline()
    for l in f:
        p = l.rstrip().split('\t')
        if len(p) >= 5 and p[4] != 'est':
            rows.append((p[0], int(p[1]), int(p[2]), int(p[3]), float(p[4])))

print('total', len(rows), 'last', rows[-1][0], rows[-1][4])
sel = [(i, r) for i, r in enumerate(rows) if lo <= r[4] <= hi]
print('sel', len(sel))
cl = []
for i, r in sel:
    if cl and i == cl[-1][-1][0] + 1:
        cl[-1].append((i, r))
    else:
        cl.append([(i, r)])
for c in cl[-4:]:
    v = [r[4] for _, r in c]
    ra = [r[1] for _, r in c]
    ad = [r[2] for _, r in c]
    se = [r[3] for _, r in c]
    print(c[0][1][0], '~', c[-1][1][0], 'n', len(c),
          'est', round(st.mean(v), 2), '+/-', round(st.pstdev(v), 2),
          'raw', round(st.mean(ra)), 'ads', round(st.mean(ad), 1),
          'sensor', round(st.mean(se), 1))
