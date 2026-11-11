"""Ziyaret sayacı (sayac.js): gerçek veritabanına hiçbir şey göndermez; istekler yakalanır.
Site gerçek alan adıyla taklit edilir (sayaç localhost'ta kendini kapatır), dosyalar yerelden verilir.
Kullanım: önce repo kökünde `python3 -m http.server 8765`, sonra `python3 _test/sayac.py`."""
import glob, json, os, re, sys, urllib.request
from playwright.sync_api import sync_playwright

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEREL = 'http://localhost:8765'
ALAN = 'https://ismailcosarturizm.com.tr'
MOCK = 'window.__DB=' + open(os.path.join(KOK, '_test', 'db.json'), encoding='utf-8').read() + ';\n' + open(os.path.join(KOK, '_test', 'mock.js'), encoding='utf-8').read()
hata = 0
def kontrol(ok, ad, ayrinti=''):
    global hata
    hata += not ok
    print('✓' if ok else '✗', ad, ayrinti)

# 1) Yayınlanan her sayfada sayaç var (admin hariç)
eksik = []
for f in sorted(glob.glob(os.path.join(KOK, '*.html'))) + [os.path.join(KOK, 'kafile', 'index.html')]:
    ad = os.path.relpath(f, KOK)
    t = open(f, encoding='utf-8').read()
    if (ad == 'admin.html') == bool(re.search(r'<script[^>]+src="[^"]*sayac\.js"', t)): eksik.append(ad)
kontrol(not eksik, 'Sayaç: tüm site sayfalarında ve misafir uygulamasında var, admin panelinde yok', eksik)

# 2) Arama motoru / yapay zekâ etiketleri
sys.path.insert(0, os.path.join(KOK, '_araclar'))
import sss_ld
sss = open(os.path.join(KOK, 'sss.html'), encoding='utf-8').read()
m = re.search(r'<!-- SSS-LD:BAS -->\s*<script type="application/ld\+json">(.*?)</script>', sss, re.S)
kontrol(m is not None and json.loads(m.group(1)) == sss_ld.ld(sss) and len(sss_ld.sorular(sss)) > 100,
        'SSS: soru-cevap etiketi (FAQPage) sayfadaki sorularla birebir aynı (soru değişince: python3 _araclar/sss_ld.py)')
bozuk = []
for f in sorted(glob.glob(os.path.join(KOK, '*.html'))):
    for j in re.findall(r'<script type="application/ld\+json">(.*?)</script>', open(f, encoding='utf-8').read(), re.S):
        try: json.loads(j)
        except Exception: bozuk.append(os.path.basename(f))
kontrol(not bozuk, 'Yapısal veri (JSON-LD) tüm sayfalarda geçerli', bozuk)
ana = open(os.path.join(KOK, 'index.html'), encoding='utf-8').read()
bt = re.search(r'<title>(.*?)</title>', ana, re.S).group(1); ac_ = re.search(r'<meta name="description" content="(.*?)"', ana).group(1)
kontrol(30 <= len(bt) <= 65 and 50 <= len(ac_) <= 170, 'Ana sayfa: başlık 30–65, açıklama 50–170 karakter', (len(bt), len(ac_)))
import html as _h
uzun = [(os.path.basename(f), len(_h.unescape(re.search(r'<title>(.*?)</title>', open(f, encoding='utf-8').read(), re.S).group(1))))
        for f in sorted(glob.glob(os.path.join(KOK, '*.html')))]
kontrol(all(n <= 65 for _, n in uzun), 'Tüm sayfa başlıkları 65 karakteri geçmiyor (Google\'da kesilmesin)', [x for x in uzun if x[1] > 65])

# 3) Tur paylaşım sayfaları (t/<id>.html): önizleme etiketleri ve doğru tura yönlendirme
import xml.dom.minidom
tsay = sorted(glob.glob(os.path.join(KOK, 't', '*.html'))); kotu = []
for f in tsay:
    i = os.path.basename(f)[:-5]; s = open(f, encoding='utf-8').read(); hedef = f'https://ismailcosarturizm.com.tr/tur-detay.html?id={i}'
    gerek = ['property="og:title"', 'property="og:description"', 'property="og:image" content="https://ismailcosarturizm.com.tr/', 'name="robots" content="noindex',
             f'<link rel="canonical" href="{hedef}">', f'url={hedef}"', f'location.replace("{hedef}"']
    if any(g not in s for g in gerek): kotu.append(i)
kontrol(len(tsay) >= 1 and not kotu, f'Tur paylaşım sayfaları ({len(tsay)} adet): önizleme etiketleri var, doğru tura yönlendiriyor', kotu)
try:
    sm = xml.dom.minidom.parse(os.path.join(KOK, 'sitemap.xml')); locs = [n.firstChild.data for n in sm.getElementsByTagName('loc')]
    kontrol(all(f'https://ismailcosarturizm.com.tr/tur-detay.html?id={os.path.basename(f)[:-5]}' in locs for f in tsay) and len(locs) == len(set(locs)),
            'Site haritası geçerli; her yayındaki tur içinde, tekrar yok', len(locs))
except Exception as e: kontrol(False, 'Site haritası geçerli XML', e)

MASA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
def ac(b, yol, ua=MASA, referrer=None, webdriver_gizle=True, yerel=False):
    ctx = b.new_context(user_agent=ua)
    pg = ctx.new_page(); giden = []; errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:160]))
    if webdriver_gizle: pg.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => false })")
    def site(r, q):
        u = q.url.replace(ALAN, YEREL)
        try:
            with urllib.request.urlopen(u) as y: r.fulfill(status=y.status, body=y.read(), headers={'content-type': y.headers.get('content-type', 'text/html')})
        except Exception: r.fulfill(status=404, body='')
    def kayit(r, q):
        giden.append(json.loads(q.post_data or '{}'))
        r.fulfill(status=204, body='', headers={'access-control-allow-origin': '*'})
    pg.route(re.compile(r'^https?://(?!localhost|ismailcosarturizm\.com\.tr)'), lambda r, q: r.abort())
    pg.route('**cdn.jsdelivr.net/npm/@supabase/**', lambda r, q: r.fulfill(status=200, body=MOCK, headers={'content-type': 'application/javascript'}))
    pg.route('**/rest/v1/rpc/ziyaret_kaydet', kayit)
    pg.route('**/rest/v1/**', lambda r, q: r.fulfill(status=200, body='[]', headers={'content-type': 'application/json', 'access-control-allow-origin': '*'}) if 'ziyaret_kaydet' not in q.url else r.fallback())
    if not yerel: pg.route(ALAN + '/**', site)
    pg.goto((YEREL if yerel else ALAN) + yol, referer=referrer, wait_until='domcontentloaded'); pg.wait_for_timeout(900)
    return ctx, pg, giden, errs

TEL = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36'
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, g, errs = ac(b, '/index.html', ua=TEL, referrer='https://www.google.com/')
    kontrol(len(g) == 1 and g[0] == {'p_sayfa': '/', 'p_kaynak': 'google.com', 'p_cihaz': 'telefon'} and not errs,
            'Sayaç: ana sayfa bir kez sayılıyor (sayfa "/", kaynak google.com, telefon)', [g, errs])
    kontrol(pg.evaluate('document.cookie') == '' and pg.evaluate('localStorage.length') == 0, 'Sayaç: çerez ve tarayıcı hafızası kullanmıyor')
    ctx.close()
    ctx, pg, g, errs = ac(b, '/tur-detay.html?id=balkan&fbclid=abc')
    kontrol(len(g) == 1 and g[0]['p_sayfa'] == '/tur-detay.html?id=balkan' and g[0]['p_cihaz'] == 'bilgisayar' and g[0]['p_kaynak'] == '',
            'Sayaç: tur detayında hangi tur olduğu kaydediliyor, diğer adres parçaları atılıyor', g)
    ctx.close()
    ctx, pg, g, errs = ac(b, '/umre.html?utm_source=instagram')
    kontrol(len(g) == 1 and g[0]['p_kaynak'] == 'instagram', 'Sayaç: utm_source ile gelen kaynak (instagram) kaydediliyor', g)
    ctx.close()
    ctx, pg, g, errs = ac(b, '/kafile/')
    kontrol(len(g) == 1 and g[0]['p_sayfa'] == '/kafile/', 'Sayaç: misafir uygulamasının açılışı sayılıyor', g)
    ctx.close()
    ctx, pg, g, errs = ac(b, '/index.html', ua='Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)')
    kontrol(not g, 'Sayaç: Google botu sayılmıyor', g)
    ctx.close()
    ctx, pg, g, errs = ac(b, '/index.html', webdriver_gizle=False)
    kontrol(not g, 'Sayaç: otomatik tarayıcı (test, bot) sayılmıyor', g)
    ctx.close()
    ctx, pg, g, errs = ac(b, '/index.html', yerel=True)
    kontrol(not g, 'Sayaç: bilgisayardaki denemelerde (localhost) çalışmıyor', g)
    ctx.close()
    # Tur detayında "Bu turu paylaş": t/<id>.html bağlantısı
    tid = json.load(open(os.path.join(KOK, '_test', 'db.json'), encoding='utf-8'))['turlar'][0]['id']
    ctx, pg, g, errs = ac(b, '/tur-detay.html?id=' + tid)
    pg.evaluate("window.__pv = null; navigator.share = function(v){ window.__pv = v; return Promise.resolve(); }")
    pg.click('#turPaylas'); pg.wait_for_timeout(200)
    pv = pg.evaluate('window.__pv') or {}
    kontrol(pv.get('url') == f'https://ismailcosarturizm.com.tr/t/{tid}.html' and pv.get('title') and not errs, 'Tur detayı: "Bu turu paylaş" önizlemeli bağlantıyı (t/…html) paylaşıyor', [pv, errs])
    pg.evaluate("navigator.share = undefined"); pg.click('#turPaylas'); pg.wait_for_timeout(300)
    kontrol('kopyalandı' in pg.inner_text('#turPaylas'), 'Tur detayı: paylaş menüsü olmayan cihazda bağlantı kopyalanıyor')
    ctx.close()
    # Paylaşım sayfası açılınca tura geçiyor (utm korunuyor)
    ctx, pg, g, errs = ac(b, f'/t/{os.path.basename(tsay[0])[:-5]}.html?utm_source=instagram')
    pg.wait_for_timeout(800)
    kontrol('/tur-detay.html?id=' + os.path.basename(tsay[0])[:-5] in pg.url and any(x.get('p_kaynak') == 'instagram' for x in g), 'Paylaşım sayfası açılınca tur detayına geçiyor; Instagram kaynağı sayaca ulaşıyor', [pg.url, g])
    ctx.close()
    # Veritabanına ulaşılamazsa site etkilenmiyor
    ctx = b.new_context(user_agent=MASA); pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:160]))
    pg.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => false })")
    pg.route(re.compile(r'^https?://(?!localhost|ismailcosarturizm\.com\.tr)'), lambda r, q: r.abort())
    pg.route(ALAN + '/**', lambda r, q: r.fulfill(status=200, body=urllib.request.urlopen(q.url.replace(ALAN, YEREL)).read(), headers={'content-type': 'text/html' if q.url.endswith(('.html', '/')) else 'application/javascript' if q.url.endswith('.js') else 'application/octet-stream'}))
    pg.goto(ALAN + '/iletisim.html', wait_until='domcontentloaded'); pg.wait_for_timeout(900)
    kontrol(not errs and pg.locator('form').count() >= 1, 'Sayaç: veritabanına ulaşılamazsa sessizce vazgeçiyor, sayfa normal çalışıyor', errs)
    ctx.close()
    b.close()

print('\n=== SAYAÇ TESTİ:', 'TEMİZ' if not hata else f'{hata} SORUN')
sys.exit(1 if hata else 0)
