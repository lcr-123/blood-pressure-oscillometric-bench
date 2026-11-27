"""Prediction card: what the script will print during the syringe run, for each candidate volume.

This exists so that during the run nobody has to wait for the offline fit to know whether the number
is going to land near 150 or near 400. After the first pull the answer is already visible: a 9 mL
pull from 200 mmHg either drops to about 147 or drops to about 179.

Numbers include the leak, because the operator will be looking at live readings that have the leak
in them: 0.108 mmHg/s at 200 mmHg, which is what this rig measures at that pressure.
"""
ATM = 760.0
LEAK = 0.108          # mmHg/s, measured on this loop
SETTLE = 90.0         # seconds between reaching target and reading plateau A
PLATEAU_A = 30.0      # seconds of plateau A
PLATEAU_BC = 45.0     # seconds of plateau B and C
START = 200.0
G1, G2, G3 = 0.0, 9.0, 18.0

print('=' * 78)
print(f'预测卡：从 {START:.0f} mmHg 起，拉 {G2:.0f} mL 再拉 {G3:.0f} mL')
print(f'（已含漏气 {LEAK} mmHg/s；静置 {SETTLE:.0f} s 后读平台 A）')
print('=' * 78)
print()

header = f'{"V(cc)":>7} | {"平台A读":>9} | {"拉9后":>8} | {"平台B读":>9} | {"拉18后":>8} | {"平台C读":>9}'
print(header)
print('-' * len(header))

for V in (120.0, 153.0, 220.0, 310.0, 400.0):
    p_abs_start = ATM + START

    # Plateau A: constant volume V+g1, leak drains it for SETTLE + half of plateau A.
    p_a_mid = (p_abs_start * (V + G1) / (V + G1)) - ATM - LEAK * (SETTLE + PLATEAU_A / 2)
    p_a_end = START - LEAK * SETTLE

    # Pull 1: same moles, volume goes from V+g1 to V+g2.
    p_b_start = (ATM + p_a_end) * (V + G1) / (V + G2) - ATM
    p_b_mid = p_b_start - LEAK * (PLATEAU_BC / 2)

    # Pull 2.
    p_b_end = p_b_start - LEAK * PLATEAU_BC
    p_c_start = (ATM + p_b_end) * (V + G2) / (V + G3) - ATM
    p_c_mid = p_c_start - LEAK * (PLATEAU_BC / 2)

    tag = ''
    if V == 153.0:
        tag = '  <- 我的估计'
    elif V == 400.0:
        tag = '  <- 文献推断'
    print(f'{V:7.0f} | {p_a_mid:9.1f} | {p_b_start:8.1f} | {p_b_mid:9.1f} | '
          f'{p_c_start:8.1f} | {p_c_mid:9.1f}{tag}')

print()
print('读法：只看「拉9后」这一列。')
print('  V=153 -> 掉到约 138 mmHg（掉了 51，因为前面 90 s 静置已经漏掉 10）')
print('  V=400 -> 掉到约 169 mmHg（掉了 20）')
print('  两者差 31 mmHg，而手抖带来的噪声是 0.27 mmHg（松手）/ 4.7 mmHg（手按着）。')
print()
print('判读（对着「拉9后」的实测读数）：')
print('  >165      -> 回流容积 300 cc 以上，我的 153 cc 错了')
print('  155-165   -> 约 220-300 cc，两个假设都不对，需要看第三段')
print('  130-145   -> 约 140-170 cc，支持 153 cc')
print('  <130      -> 小于 130 cc，比估计还小，检查是不是有东西堵着')
print()
print('三个平台的预期值（V=153）：200 -> 189 -> 138 -> 135 -> 86 -> 83')
print('三个平台的预期值（V=400）：200 -> 189 -> 169 -> 167 -> 145 -> 142')
print()
print('注意「平台A读」在所有假设下都是 188.7：它只由漏气决定，不携带容积信息。')
print('所以 A 段的作用是确认沉降结束、漏气率正常，不是用来分档的。')
