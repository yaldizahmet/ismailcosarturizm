"""Yolcu mesajları (yorumlar.js): ana sayfa şeridi ve Umre sayfası bölümü; gerçek veritabanına dokunmaz.
Kullanım: önce repo kökünde `python3 -m http.server 8765`, sonra `python3 _test/yorumlar.py`."""
import json, re, sys
from urllib.parse import unquote
from playwright.sync_api import sync_playwright

import os
BASE = 'http://localhost:8765/'
HERE = os.path.dirname(os.path.abspath(__file__))
MOCK = 'window.__DB=' + open(os.path.join(HERE, 'db.json'), encoding='utf-8').read() + ';\n' + open(os.path.join(HERE, 'mock.js'), encoding='utf-8').read()
GORSEL = 'https://wpkjxwbvewwgdclbsdya.supabase.co/storage/v1/object/public/tur-gorselleri/yorum-1.jpg'
PNG = bytes.fromhex('89504e470d0a1a0a0000000d4948445200000001000000010806000000'
                    '1f15c4890000000d49444154789c6360f80f0000010101005b0b3b3c0000000049454e44ae426082')
YORUMLAR = [
  {'id': 2, 'ad_gorunen': 'Ayşe K***', 'tur': 'Kasım 2026 Umre', 'kategori': 'umre', 'tarih': '2026-11-20', 'gorsel': GORSEL,
   'metin': 'Allah razı olsun, her şey çok güzeldi.\nOtel Harem\'e çok yakındı, rehberimiz her an yanımızdaydı. ' * 4},
  {'id': 1, 'ad_gorunen': '<img src=x onerror=window.__xss=1>', 'tur': None, 'kategori': 'kultur', 'tarih': None,
   'gorsel': 'https://kotu.example/x.jpg', 'metin': 'Balkan turu harikaydı <script>window.__xss=1</script>'},
]
hata = 0
def kontrol(ok, ad, ayrinti=''):
    global hata
    hata += not ok
    print('✓' if ok else '✗', ad, ayrinti)

def sayfa(b, yol, veri, vp={'width': 1300, 'height': 900}):
    pg = b.new_page(viewport=vp); errs = []; istekler = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:160]))
    def yorum(r, q):
        istekler.append(unquote(q.url))
        kat = re.search(r'kategori=eq\.(\w+)', q.url)
        tid = re.search(r'tur_id=eq\.([\w-]+)', q.url)
        l = [y for y in veri if (not kat or y['kategori'] == kat.group(1)) and (not tid or y.get('tur_id') == tid.group(1))]
        r.fulfill(status=200, body=json.dumps(l), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'})
    pg.route(re.compile(r'^https?://(?!localhost)'), lambda r, q: r.abort())
    pg.route('**cdn.jsdelivr.net/npm/@supabase/**', lambda r, q: r.fulfill(status=200, body=MOCK, headers={'content-type': 'application/javascript'}))
    pg.route('**/rest/v1/yorumlar**', yorum)
    pg.route('**/rest/v1/**', lambda r, q: r.fulfill(status=200, body='[]', headers={'content-type': 'application/json', 'access-control-allow-origin': '*'}) if 'yorumlar' not in q.url else r.fallback())
    pg.route('**/storage/v1/object/public/**', lambda r, q: r.fulfill(status=200, body=PNG, headers={'content-type': 'image/png'}))
    pg.goto(BASE + yol, wait_until='domcontentloaded'); pg.wait_for_timeout(1200)
    return pg, errs, istekler

with sync_playwright() as p:
    b = p.chromium.launch()
    # Ana sayfa
    pg, errs, ist = sayfa(b, 'index.html', YORUMLAR)
    kontrol(pg.locator('#yolcuSerit').count() == 1 and pg.evaluate("document.getElementById('yolcuSerit').nextElementSibling.id") == 'yorumGrid',
            'Ana sayfa: yolcu mesajları şeridi Google yorumlarının hemen üstünde', errs)
    kontrol(pg.locator('#yolcuSerit .yolcu-mesaji').count() == 2 and pg.locator('#yorumGrid > .yorum-card').count() == 20, 'Ana sayfa: 2 mesaj eklendi, 20 Google yorumu yerinde')
    kontrol(pg.evaluate('!window.__xss') and '<img src=x' in pg.inner_text('#yolcuSerit'), 'Güvenlik: isim/metindeki HTML çalışmıyor, düz yazı')
    kontrol(ist and all('select=id,ad_gorunen,' in u and ',ad,' not in u for u in ist) and 'Ayşe K***' in pg.inner_text('#yolcuSerit'),
            'Gizlilik: site yalnızca maskeli ismi istiyor ve gösteriyor (Ayşe K***)')
    kontrol(pg.locator('#yolcuSerit img[src*="kotu.example"]').count() == 0 and pg.locator('#yolcuSerit .ym-resim').count() == 1, 'Güvenlik: yalnızca kendi depomuzdaki fotoğraf gösteriliyor')
    h = pg.evaluate("getComputedStyle(document.querySelector('.ym-serit')).overflowX")
    yuk = pg.evaluate("document.getElementById('yolcuSerit').getBoundingClientRect().height")
    kontrol(h == 'auto' and yuk < 420, 'Az yer: tek satırlık kaydırılan şerit', f'(yükseklik {round(yuk)} px)')
    uzun = pg.locator('#yolcuSerit .ym-metin').first
    kontrol('kisa' in (uzun.get_attribute('class') or ''), 'Uzun mesaj 4 satırla kısaltılıyor')
    pg.locator('#yolcuSerit [data-ym-devam]').first.click(); pg.wait_for_timeout(100)
    kontrol('kisa' not in (uzun.get_attribute('class') or '') and 'Daha az' in pg.locator('#yolcuSerit [data-ym-devam]').first.inner_text(), '"Devamını oku" mesajın tamamını açıyor')
    pg.locator('#yolcuSerit .ym-resim').click(); pg.wait_for_timeout(150)
    kontrol(pg.locator('#ymBuyuk img').count() == 1, 'Fotoğrafa dokununca büyüyor')
    pg.locator('#ymBuyuk').click(); pg.wait_for_timeout(100)
    kontrol(pg.locator('#ymBuyuk').count() == 0 and not errs, 'Büyük fotoğraf dokununca kapanıyor', errs)
    pg.close()
    pg, errs, _ = sayfa(b, 'index.html', YORUMLAR, {'width': 390, 'height': 844})
    kontrol(pg.evaluate('document.documentElement.scrollWidth') <= 391 and pg.locator('#yolcuSerit .yolcu-mesaji').count() == 2 and not errs, 'Telefon: sayfa yana taşmıyor, şerit kendi içinde kayıyor', errs)
    pg.close()
    pg, errs, _ = sayfa(b, 'index.html', [])
    kontrol(pg.locator('#yolcuSerit').count() == 0 and pg.locator('#yorumGrid > .yorum-card').count() == 20 and not errs, 'Mesaj yoksa şerit hiç eklenmiyor', errs)
    pg.close()
    # Umre sayfası
    pg, errs, ist = sayfa(b, 'umre.html', YORUMLAR)
    kontrol(pg.is_visible('#yolcuMesajlari') and pg.locator('#yolcuMesajlari .yolcu-mesaji').count() == 1 and any('kategori=eq.umre' in u for u in ist),
            'Umre sayfası: yalnızca umre mesajları gösteriliyor', errs)
    pg.close()
    pg, errs, ist = sayfa(b, 'turlar.html', YORUMLAR)
    kontrol(pg.is_visible('#yolcuMesajlari') and pg.locator('#yolcuMesajlari .yolcu-mesaji').count() == 1 and any('kategori=eq.kultur' in u for u in ist),
            'Turlar sayfası: kültür turu mesajları gösteriliyor', errs)
    pg.close()
    pg, errs, ist = sayfa(b, 'hac.html', YORUMLAR)
    kontrol(not pg.is_visible('#yolcuMesajlari') and any('kategori=eq.hac' in u for u in ist) and not errs, 'Hac sayfası: hac mesajı yoksa bölüm gizli', errs)
    pg.close()
    pg, errs, ist = sayfa(b, 'tur-detay.html?id=balkanlar-2025', [dict(YORUMLAR[1], tur_id='balkanlar-2025')])
    kontrol(pg.is_visible('#yolcuMesajlari') and any('tur_id=eq.balkanlar-2025' in u for u in ist), 'Tur detayı: yalnızca o tur seçilerek eklenmiş mesajlar isteniyor ve gösteriliyor', errs)
    pg.close()
    pg, errs, _ = sayfa(b, 'umre.html', [])
    kontrol(not pg.is_visible('#yolcuMesajlari') and not errs, 'Umre sayfası: mesaj yoksa bölüm gizli', errs)
    pg.close()
    b.close()

print('\n=== YORUM TESTİ:', 'TEMİZ' if not hata else f'{hata} SORUN')
sys.exit(1 if hata else 0)
