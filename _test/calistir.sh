#!/usr/bin/env bash
# Sitenin tam testi: tüm sayfalarda bağlantı/buton taraması + başvuru formları.
# Kullanım (repo kökünden): bash _test/calistir.sh
# Gereken: python3, playwright (Chromium). Yayına almadan önce çalıştırılmalı.
set -u
cd "$(dirname "$0")/.."
KOK=$(pwd)
CIKTI=$(mktemp -d)
python3 -m http.server 8765 >/dev/null 2>&1 &
SUNUCU=$!
trap 'kill $SUNUCU 2>/dev/null; rm -rf "$CIKTI"' EXIT
sleep 1

echo "▶ JavaScript sözdizimi kontrolü"
python3 - <<'EOF' || exit 1
import re, subprocess, glob, sys, tempfile, os
bad = 0
for fn in sorted(glob.glob('*.html')) + sorted(glob.glob('*.js')):
    s = open(fn, encoding='utf-8').read()
    parcalar = [s] if fn.endswith('.js') else [m.group(1) for m in re.finditer(r'<script(?![^>]*\bsrc=)(?![^>]*application/ld\+json)[^>]*>(.*?)</script>', s, re.S)]
    for kod in parcalar:
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as t:
            t.write('(async function(){' + kod + '\n})')
        r = subprocess.run(['node', '--check', t.name], capture_output=True, text=True); os.unlink(t.name)
        if r.returncode: bad += 1; print('  ✗', fn, r.stderr.strip().splitlines()[-1][:150])
print('  ✓ temiz' if not bad else f'  {bad} hata'); sys.exit(1 if bad else 0)
EOF

echo "▶ Bağlantı ve buton taraması (sayfalar paralel)"
for p in index umre hac turlar "id=umre-kasim" "id=balkan" sss iletisim galeri hakkimizda belgelerimiz kvkk tesekkurler; do
  python3 _test/tara.py "$p" > "$CIKTI/${p//[^a-z]/_}.txt" 2>&1 &
done
wait $(jobs -p | grep -v "^$SUNUCU$") 2>/dev/null
SORUN=$(cat "$CIKTI"/*.txt | grep "✗" | sort -u)
if [ -n "$SORUN" ]; then echo "$SORUN"; else echo "  ✓ tüm bağlantılar ve butonlar çalışıyor"; fi

echo "▶ Başvuru formları"
python3 _test/formlar.py 2>&1 | grep -E "^(✓|✗|===)"
FORM=${PIPESTATUS[0]}

echo
if [ -z "$SORUN" ] && [ "$FORM" = 0 ]; then echo "=== SONUÇ: TEMİZ — yayına alınabilir"; exit 0; else echo "=== SONUÇ: SORUN VAR — yayına almadan önce düzelt"; exit 1; fi
