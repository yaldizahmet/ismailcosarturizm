"""Her tur için paylaşım sayfası üretir: t/<id>.html (+ t/<id>.jpg).

WhatsApp, Facebook, Instagram gibi uygulamalar bağlantı önizlemesi için sayfadaki og: etiketlerine bakar ve
JavaScript çalıştırmaz. tur-detay.html turu JavaScript ile yüklediği için önizlemede turun adı ve fotoğrafı
görünmüyordu. Bu sayfalar etiketleri hazır taşır, insan açınca da hemen tur-detay.html?id=<id> adresine geçer.

Kullanım:  python3 _araclar/tur_onizleme.py turlar.json [gorsel_klasoru]
  turlar.json  : Supabase'den gelen aktif tur listesi (REST /rest/v1/turlar?aktif=eq.true)
  gorsel_klasoru: (isteğe bağlı) <id>.jpg olarak indirilmiş tur fotoğrafları; varsa 1200×630'a kırpılıp t/ içine yazılır.
Ayrıca sitemap.xml içindeki <!-- TURLAR --> bölümünü günceller. GitHub Action (.github/workflows/tur-onizleme.yml) saatte bir çalıştırır."""
import html, json, os, re, sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://ismailcosarturizm.com.tr'
AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
YEDEK_GORSEL = {'umre': 'og-umre.jpg', 'hac': 'og-hac.jpg'}  # diğerleri: og-turlar.jpg

def tr_kucuk(s): return s.replace('I', 'ı').replace('İ', 'i').lower()
def tr_buyuk(s): return s.replace('i', 'İ').replace('ı', 'I').upper()
def baslik_duzelt(s):
    """Tamamı büyük harfle yazılmış başlığı 'Aralık Ayı Umre Programı (2026) 14 Gün' biçimine çevirir."""
    s = re.sub(r'\s+', ' ', str(s or '')).strip()
    harf = [c for c in s if c.isalpha()]
    if not harf or sum(c.isupper() for c in harf) / len(harf) < 0.7: return s
    kucuk_kal = {'ve', 'ile', 'de', 'da'}
    def kelime(w, ilk):
        k = tr_kucuk(w)
        if not ilk and k in kucuk_kal: return k
        j = next((n for n, c in enumerate(k) if c.isalpha()), 0)  # "(ispanya)" → "(İspanya)"
        return k[:j] + tr_buyuk(k[j:j + 1]) + k[j + 1:]
    return ' '.join(kelime(w, i == 0) for i, w in enumerate(s.split(' ')))

def tarih_araligi(bas, bit):
    m1 = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(bas or '')); m2 = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(bit or ''))
    if not m1: return ''
    y1, a1, g1 = int(m1[1]), int(m1[2]), int(m1[3])
    if not m2: return f'{g1} {AYLAR[a1 - 1]} {y1}'
    y2, a2, g2 = int(m2[1]), int(m2[2]), int(m2[3])
    if (y1, a1) == (y2, a2): return f'{g1}–{g2} {AYLAR[a1 - 1]} {y1}'
    if y1 == y2: return f'{g1} {AYLAR[a1 - 1]} – {g2} {AYLAR[a2 - 1]} {y1}'
    return f'{g1} {AYLAR[a1 - 1]} {y1} – {g2} {AYLAR[a2 - 1]} {y2}'

def guvenli_id(i): return bool(re.fullmatch(r'[A-Za-z0-9_-]{1,80}', str(i or '')))

def aciklama(t):
    p = []
    ta = tarih_araligi(t.get('tarih'), t.get('donus_tarihi'))
    if ta: p.append('📅 ' + ta)
    if t.get('sure'): p.append(str(t['sure']).strip().lower())
    if str(t.get('fiyat') or '').strip(): p.append(f"Kişi başı {str(t['fiyat']).strip()} {str(t.get('para_birimi') or '').strip()}".strip())
    if t.get('konum'): p.append(baslik_duzelt(t['konum']))
    return ' · '.join(p) + ' — İsmail Coşar Turizm'

def sayfa(t, gorsel_url):
    i = t['id']; hedef = f'{SITE}/tur-detay.html?id={i}'
    b = html.escape(baslik_duzelt(t.get('baslik') or 'Tur')); a = html.escape(aciklama(t))
    return f'''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{b} | İsmail Coşar Turizm</title>
<meta name="description" content="{a}">
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="{html.escape(hedef)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="İsmail Coşar Turizm">
<meta property="og:locale" content="tr_TR">
<meta property="og:title" content="{b}">
<meta property="og:description" content="{a}">
<meta property="og:url" content="{SITE}/t/{i}.html">
<meta property="og:image" content="{html.escape(gorsel_url)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{b}">
<meta name="twitter:description" content="{a}">
<meta name="twitter:image" content="{html.escape(gorsel_url)}">
<meta http-equiv="refresh" content="0; url={html.escape(hedef)}">
<script>location.replace({json.dumps(hedef)} + (location.search ? '&' + location.search.slice(1) : ''));</script>
</head>
<body style="font-family:sans-serif;padding:40px;text-align:center">
<p><a href="{html.escape(hedef)}">{b}</a></p>
</body>
</html>
'''

def gorsel_hazirla(kaynak, hedef):
    """Fotoğrafı 1200×630 (önizleme oranı) kırpıp ~150 KB JPEG olarak yazar. Başarısızsa False."""
    try:
        from PIL import Image, ImageOps
        im = Image.open(kaynak); im = ImageOps.exif_transpose(im).convert('RGB')
        im = ImageOps.fit(im, (1200, 630), Image.LANCZOS, centering=(0.5, 0.45))
        im.save(hedef, 'JPEG', quality=80, optimize=True, progressive=True)
        return True
    except Exception as e:
        print('görsel hazırlanamadı:', kaynak, e); return False

def main():
    turlar = json.load(open(sys.argv[1], encoding='utf-8'))
    gk = sys.argv[2] if len(sys.argv) > 2 else None
    td = os.path.join(KOK, 't'); os.makedirs(td, exist_ok=True)
    yazilan = set()
    for t in turlar:
        i = t.get('id')
        if not guvenli_id(i) or not t.get('aktif', True): continue
        gurl = f"{SITE}/{YEDEK_GORSEL.get(t.get('kategori'), 'og-turlar.jpg')}"
        jpg = os.path.join(td, i + '.jpg')
        if gk and os.path.exists(os.path.join(gk, i + '.jpg')) and gorsel_hazirla(os.path.join(gk, i + '.jpg'), jpg): pass
        if os.path.exists(jpg):
            gurl = f'{SITE}/t/{i}.jpg?v={os.path.getsize(jpg)}'  # boyut değişince WhatsApp yeni resmi alsın
            yazilan.add(i + '.jpg')
        open(os.path.join(td, i + '.html'), 'w', encoding='utf-8').write(sayfa(t, gurl)); yazilan.add(i + '.html')
    for f in os.listdir(td):  # artık yayında olmayan turların sayfalarını kaldır
        if f not in yazilan and f.endswith(('.html', '.jpg')): os.remove(os.path.join(td, f))
    # site haritası: aktif turların detay sayfaları
    sm = os.path.join(KOK, 'sitemap.xml'); x = open(sm, encoding='utf-8').read()
    blok = '  <!-- TURLAR (otomatik: _araclar/tur_onizleme.py) -->\n' + ''.join(
        f'  <url>\n    <loc>{SITE}/tur-detay.html?id={t["id"]}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
        for t in turlar if guvenli_id(t.get('id')) and t.get('aktif', True)) + '  <!-- /TURLAR -->\n'
    if '<!-- TURLAR' in x: x = re.sub(r'  <!-- TURLAR.*?<!-- /TURLAR -->\n', lambda m: blok, x, flags=re.S)
    else: x = x.replace('</urlset>', blok + '</urlset>')
    open(sm, 'w', encoding='utf-8').write(x)
    print(len([f for f in yazilan if f.endswith('.html')]), 'tur sayfası')

if __name__ == '__main__': main()
