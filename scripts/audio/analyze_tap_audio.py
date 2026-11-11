"""マイク録音から「指が画面を叩く音 → SE が鳴り始める」の間隔を取り出す。
  叩く音: 2-8 kHz の鋭い立ち上がり（直前 20 ms の 6 倍以上、数 ms で減衰）
  SE    : 叩いた後、8 kHz 以上が叩く前の水準の 3 倍を超えて 15 ms 以上続き始める点
直前 60 ms が静かなタップだけを使う（前の SE の余韻と重なるものは捨てる）。
録音途中の（ヘッダ未確定の）wav も読める。
使い方: python scripts/audio/analyze_tap_audio.py prsk/logs/mic/xxx.wav [-v] [--se LO HI]
  --se: SE の検出帯域（Hz）。既定 8000 24000。OboeTester の Blip（1 kHz 正弦波）は --se 800 1300。"""
import sys, numpy as np
sys.stdout.reconfigure(encoding='utf-8')
raw = open(sys.argv[1], 'rb').read(); o = raw.find(b'data') + 8; n = (len(raw) - o) // 2 * 2
x = np.frombuffer(raw[o:o + n], dtype=np.int16).astype(np.float32) / 32768; sr = 48000
H = sr // 2000; per_ms = 2                       # 0.5 ms 刻み
def env(lo, hi):
    out = []
    for s in range(0, len(x), sr * 30):           # 30 秒ずつ（メモリ節約）
        c = x[s:s + sr * 30]; X = np.fft.rfft(c); f = np.fft.rfftfreq(len(c), 1 / sr)
        X[(f < lo) | (f > hi)] = 0; v = np.fft.irfft(X, len(c))
        out.append(np.sqrt((v[:len(v) // H * H].reshape(-1, H) ** 2).mean(1)))
    return np.concatenate(out)
a = sys.argv; se = (float(a[a.index('--se') + 1]), float(a[a.index('--se') + 2])) if '--se' in a else (8000, 24000)
hi, vhi = env(2000, 8000), env(*se)
M = lambda ms: int(ms * per_ms)
res = []; i = M(80)
while i < len(hi) - M(200):
    base = hi[i - M(20):i - M(1)].mean()
    if hi[i] > 0.02 and hi[i] > 6 * base and hi[i + M(6):i + M(12)].mean() < 0.4 * hi[i:i + M(2)].max():
        quiet = vhi[i - M(60):i - M(2)].mean()
        if quiet < 0.008:                          # 直前が静か
            ref = max(vhi[i + M(6):i + M(15)].mean(), quiet, 0.002)
            sm = np.convolve(vhi[i:i + M(200)], np.ones(M(5)) / M(5), 'same')
            hit = next((j for j in range(M(15), M(170)) if sm[j] > 3 * ref and sm[j:j + M(15)].min() > 2 * ref), None)
            # 立ち上がりの始点まで戻る
            if hit is not None:
                while hit > M(15) and sm[hit - 1] > 1.5 * ref: hit -= 1
            res.append((i / per_ms, None if hit is None else hit / per_ms))
        i += M(40)
    else: i += 1
d = np.array([r[1] for r in res if r[1] is not None])
if '-v' in sys.argv:
    for t, v in res: print(f'  tap {t/1000:8.3f}s → SE ' + ('なし' if v is None else f'{v:6.1f} ms'))
print(f'条件を満たすタップ {len(res)} 回 / SE を対応付けできたもの {len(d)} 回')
if len(d) >= 3:
    q = lambda p: np.percentile(d, p)
    print(f'タップ→SE ms: 中央値 {q(50):.1f} / p10 {q(10):.1f} / p25 {q(25):.1f} / p75 {q(75):.1f} / p90 {q(90):.1f} / 最小 {d.min():.1f} / 最大 {d.max():.1f}')
    for lo in range(20, 170, 10):
        c = int(((d >= lo) & (d < lo + 10)).sum()); print(f'  {lo:3d}-{lo+10:<3d} ms {c:4d} ' + '#' * c)
