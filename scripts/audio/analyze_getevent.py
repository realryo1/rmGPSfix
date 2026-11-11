"""getevent -lt の出力からタッチ報告間隔の分布を出す。
使い方: python scripts/audio/analyze_getevent.py prsk/logs/<dir>/getevent.txt"""
import re, sys, statistics as st
sys.stdout.reconfigure(encoding="utf-8")
ts = []; downs = 0
for line in open(sys.argv[1], encoding='utf-8', errors='replace'):
    m = re.match(r'\[\s*(\d+\.\d+)\]\s+(\S+)\s+(\S+)\s+(\S+)', line)
    if not m: continue
    t, typ, code, val = float(m[1]), m[2], m[3], m[4]
    if code == 'ABS_MT_TRACKING_ID' and val != 'ffffffff': downs += 1
    if code == 'SYN_REPORT': ts.append(t)
if len(ts) < 2: sys.exit('イベントなし')
d = [(b - a) * 1000 for a, b in zip(ts, ts[1:])]
act = sorted(x for x in d if x < 50)          # 50ms 以上は指が離れている区間とみなす
q = lambda p: act[min(len(act) - 1, int(len(act) * p))]
print(f'SYN_REPORT {len(ts)} 件 / タッチ開始 {downs} 回 / 記録 {ts[-1]-ts[0]:.0f} 秒')
print(f'接触中の報告間隔 ms: n={len(act)} 中央値={q(.5):.3f} 平均={st.mean(act):.3f} '
      f'p1={q(.01):.3f} p5={q(.05):.3f} p95={q(.95):.3f} p99={q(.99):.3f} 最大={act[-1]:.3f}')
print(f'→ 中央値から換算した報告レート {1000/q(.5):.0f} Hz')
bins = [0, 1, 1.5, 2.5, 3.5, 4.5, 6, 9, 13, 20, 50]
for lo, hi in zip(bins, bins[1:]):
    n = sum(lo <= x < hi for x in act)
    print(f'  {lo:>4}–{hi:<4} ms {n:7d} {100*n/len(act):5.1f}% ' + '#' * int(50 * n / len(act)))
