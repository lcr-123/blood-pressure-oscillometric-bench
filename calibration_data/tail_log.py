# -*- coding: utf-8 -*-
"""读日志最后 N 行：python tail_log.py <log> [n]"""
import sys

log = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 5

rows = []
with open(log, encoding='utf-8') as f:
    f.readline()
    for l in f:
        p = l.rstrip().split('\t')
        if len(p) >= 5 and p[4] != 'est':
            rows.append((p[0], int(p[1]), int(p[2]), int(p[3]), float(p[4])))

print('total', len(rows))
for r in rows[-n:]:
    print(r[0], r[1], r[2], r[3], r[4])
