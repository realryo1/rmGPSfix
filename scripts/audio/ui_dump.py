"""端末の画面の UI 要素（テキスト・ID・座標）を一覧する。使い方: adb exec-out uiautomator dump /dev/tty > x.xml; python scripts/audio/ui_dump.py x.xml"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
s = open(sys.argv[1], encoding='utf-8', errors='ignore').read()
for n in re.findall(r'<node [^>]*>', s):
    g = lambda k: (re.search(k + r'="([^"]*)"', n) or [None, ''])[1]
    t, r = g('text'), g('resource-id').split('/')[-1]
    if t or r: print(f"{g('bounds'):24s} {g('class').split('.')[-1]:14s} {r:28s} {t} {'[checked]' if g('checked')=='true' else ''}")
