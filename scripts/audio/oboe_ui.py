"""OboeTester の Round Trip Latency 画面を adb + uiautomator で操作する補助。
  python scripts/audio/oboe_ui.py set <spinnerのresource-id> <選ぶ文字列> [out|in]
  python scripts/audio/oboe_ui.py check <checkboxのresource-id> <on|off> [out|in]
  python scripts/audio/oboe_ui.py avg     （出力・入力の設定欄を閉じて AVERAGE を押し、結果を表示）
  python scripts/audio/oboe_ui.py list <spinnerのresource-id> [out|in]  （選択肢の一覧）"""
import re, subprocess, sys, time, os
sys.stdout.reconfigure(encoding='utf-8')
env = dict(os.environ, MSYS_NO_PATHCONV='1')
def adb(*a): return subprocess.run(['adb', *a], capture_output=True, env=env).stdout.decode('utf-8', 'ignore')
def nodes():
    for _ in range(5):
        s = adb('exec-out', 'uiautomator', 'dump', '/dev/tty')
        if '<node' in s: break
        time.sleep(1)
    out = []
    for n in re.findall(r'<node [^>]*>', s):
        g = lambda k: (re.search(k + r'="([^"]*)"', n) or [None, ''])[1]
        b = list(map(int, re.findall(r'\d+', g('bounds'))))
        out.append(dict(id=g('resource-id').split('/')[-1], text=g('text'), checked=g('checked') == 'true', b=b))
    return out
def tap(n): b = n['b']; adb('shell', 'input', 'tap', str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2)); time.sleep(.8)
def section(which):  # 指定した側の設定欄だけを開く
    for n in nodes():
        if n['id'] == 'toggle_stream_config':
            want = which and which.upper() in n['text']
            if n['text'].startswith('Show') and want: tap(n); return section(which)
            if n['text'].startswith('Hide') and not want: tap(n); return section(which)
def find(id_, ns, which):
    c = [n for n in ns if n['id'] == id_]
    return c[0] if c else None
cmd = sys.argv[1]
if cmd in ('set', 'list'):
    which = sys.argv[4] if len(sys.argv) > 4 else (sys.argv[3] if cmd == 'list' and len(sys.argv) > 3 else 'out')
    section(which); sp = find(sys.argv[2], nodes(), which); tap(sp)
    opts = [n for n in nodes() if n['id'] in ('text1', 'device_name') and n['text'] and n['b'][0] >= sp['b'][0] - 5]
    if cmd == 'list': print([o['text'] for o in opts]); adb('shell', 'input', 'keyevent', 'KEYCODE_BACK'); time.sleep(.5)
    else:
        pick = lambda opts: next((o for o in opts if o['text'] == sys.argv[3]), None) or next((o for o in opts if sys.argv[3] in o['text']), None)
        o = pick(opts)
        if o is None and opts:  # リストが途中までスクロールしているときは上へ戻す
            b = opts[0]['b']; x = str((b[0] + b[2]) // 2)
            adb('shell', 'input', 'swipe', x, str(b[3]), x, str(b[3] + 1200), '300'); time.sleep(.8)
            opts = [n for n in nodes() if n['id'] in ('text1', 'device_name') and n['text'] and n['b'][0] >= sp['b'][0] - 5]
            o = pick(opts)
        if o is None: print('見つからない:', [o['text'] for o in opts]); adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
        else: tap(o); print('選択:', o['text'])
elif cmd == 'check':
    which = sys.argv[4] if len(sys.argv) > 4 else 'out'
    section(which); n = find(sys.argv[2], nodes(), which)
    if n['checked'] != (sys.argv[3] == 'on'): tap(n)
    print(sys.argv[2], '=', sys.argv[3])
elif cmd == 'avg':
    section(None); n = next(n for n in nodes() if n['id'] == 'button_average'); tap(n)
    for _ in range(30):
        time.sleep(2); ns = nodes()
        st = next((n['text'] for n in ns if n['id'] == 'text_status'), '')
        if 'average.latency.msec' in st or 'failed' in st.lower() and 'num.failed' not in st: break
    info = [n['text'].replace('&#10;', ' | ') for n in ns if n['id'] in ('streamInfo', 'statusView')]
    for i in info: print('  ', i[:160])
    print('  ', st.replace('&#10;', ' | ')[:400])
