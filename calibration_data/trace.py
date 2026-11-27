# -*- coding: utf-8 -*-
"""抽样查看日志轨迹：python trace.py <log> <t_from> <t_to> [step]"""
import sys

log = sys.argv[1]
t0, t1 = sys.argv[2], sys.argv[3]
step = int(sys.argv[4]) if len(sys.argv) > 4 else 20

rows = []
with open(log, encoding='utf-8') as f:
    f.readline()
    for l in f:
        p = l.rstrip().split('\t')
        if len(p) >= 5 and p[4] != 'est':
            rows.append((p[0], int(p[1]), int(p[2]), int(p[3]), float(p[4])))

sel = [r for r in rows if t0 <= r[0] <= t1]
print('n in range', len(sel))
# 找峰值：est 最大值附近
mx = max(sel, key=lambda r: r[4])
print('peak:', mx[0], mx[4])
for r in sel[::step]:
    print(r[0], r[1], r[2], r[3], r[4])
