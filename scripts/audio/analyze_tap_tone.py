"""OboeTester Tap-to-Tone（Tone type = Blip、1 kHz 正弦波）の PC マイク録音から「叩く音 → Blip」を測る。
  叩く音: 2 kHz 以上の広帯域エネルギーの鋭い立ち上がり（雑音中央値の 15 倍、直前 20 ms の 8 倍）
  Blip  : 5 ms 窓の 1 kHz 直交検波。タップ後 0〜150 ms の安定した水準（plateau、20 ms 移動中央値の最大）の
          50% を超え、かつ 600 Hz / 1400 Hz の 3 倍を超えた最初の点。窓の中央の時刻を立ち上がりとする。
  叩く音にも 1 kHz 成分があるが広帯域なので、隣接帯域との比で除外する。
  除外: タップ前 20 ms にすでに Blip が鳴っているもの（前の Blip と重なった）、plateau が小さいもの（--min）。
  注意: Blip が小さく録れると立ち上がりの判定が遅れる。イヤホン / 端末をマイクに近づけて録る。
使い方: python scripts/audio/analyze_tap_tone.py <wav> [-v] [--f 1000] [--min 0.3]"""
import sys, numpy as np
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
a = sys.argv; F = float(a[a.index('--f') + 1]) if '--f' in a else 1000.0
MIN = float(a[a.index('--min') + 1]) if '--min' in a else 0.3
raw = open(a[1], 'rb').read(); o = raw.find(b'data') + 8; n = (len(raw) - o) // 2 * 2
x = np.frombuffer(raw[o:o + n], dtype=np.int16).astype(np.float32) / 32768; sr = 48000
H = 24                                     # 0.5 ms 刻み
X = np.fft.rfft(x); X[np.fft.rfftfreq(len(x), 1 / sr) < 2000] = 0; hp = np.fft.irfft(X, len(x))
e = np.sqrt((hp[:len(hp) // H * H].reshape(-1, H) ** 2).mean(1)); noise = np.median(e)
taps = []; i = 200
while i < len(e) - 400:
    if e[i] > 15 * noise and e[i] > 8 * e[i - 40:i - 2].mean(): taps.append(i); i += 600   # 300 ms は次を探さない
    else: i += 1
L = int(.005 * sr); t = np.arange(L) / sr
def mag(s, f):  # タップ前 100 ms 〜 後 200 ms、0.5 ms 刻み。添字 200 がタップ時刻
    c = np.exp(-2j * np.pi * f * t) * np.hanning(L); seg = x[s - int(.1 * sr):s + int(.2 * sr)]
    return np.array([abs((seg[k:k + L] * c).sum()) for k in range(0, len(seg) - L, H)])
res = []
for ti in taps:
    s = ti * H
    if s - int(.1 * sr) < 0 or s + int(.2 * sr) > len(x): continue
    m = mag(s, F); side = np.maximum(mag(s, F * .6), mag(s, F * 1.4))
    post, side_p = m[200:], side[200:]
    plateau = max(np.median(post[k:k + 40]) for k in range(0, 300, 10))
    if plateau < MIN: res.append((s / sr, None, 'plateau 小')); continue
    if np.median(m[160:196]) > .3 * plateau: res.append((s / sr, None, '前の Blip と重なり')); continue
    j = next((j for j in range(6, len(post)) if post[j] > .5 * plateau and post[j] > 3 * side_p[j]), None)
    res.append((s / sr, None if j is None else (j * H + L / 2) / sr * 1000, f'plateau {plateau:.2f}'))
d = np.array([r[1] for r in res if r[1] is not None])
if '-v' in a:
    for tt, v, note in res: print(f'  tap {tt:8.3f}s → Blip ' + ('  なし  ' if v is None else f'{v:6.1f} ms') + f'  {note}')
print(f'タップ {len(res)} 回 / Blip を対応付けできたもの {len(d)} 回')
if len(d) >= 3:
    q = lambda p: np.percentile(d, p)
    print(f'タップ→Blip ms: 中央値 {q(50):.1f} / p10 {q(10):.1f} / p25 {q(25):.1f} / p75 {q(75):.1f} / p90 {q(90):.1f} / 最小 {d.min():.1f} / 最大 {d.max():.1f}')
    for lo in range(0, 200, 10):
        c = int(((d >= lo) & (d < lo + 10)).sum())
        if c: print(f'  {lo:3d}-{lo+10:<3d} ms {c:4d} ' + '#' * c)
