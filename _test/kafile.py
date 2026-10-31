"""Kafile uygulamasını (kafile/) telefon boyutunda uçtan uca test eder; gerçek veritabanına dokunmaz.
Kafile verisi sahte bir RPC yanıtıyla verilir; saat window.__SIMDI ile sabitlenir.
Kullanım: önce repo kökünde `python3 -m http.server 8765`, sonra `python3 _test/kafile.py`."""
import json, os, re, subprocess, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); KOK = os.path.dirname(HERE)
URL = 'http://localhost:8765/kafile/'
SIMDI = '2026-11-12T11:00:00+03:00'  # kafilenin 3. günü, Mekke saatiyle 11:00
KAFILE = {
  'kod': 'TEST-ABCDE', 'ad': 'Kasım 2026 Umre Kafilesi', 'baslangic': '2026-11-10', 'bitis': '2026-11-23',
  'rehber_ad': "Ali O'Hoca", 'rehber_tel': '0533 000 00 00',
  'oteller': [{'sehir': 'Mekke', 'ad': 'Test Otel <b>kalin</b>', 'adres': 'İbrahim Halil Cd.', 'adres_ar': 'شارع إبراهيم الخليل', 'tel': '+966 12 000 0000', 'konum': 'https://maps.google.com/?q=21.42,39.82'},
              {'sehir': 'Medine', 'ad': 'Medine Oteli', 'adres': '', 'adres_ar': '', 'tel': '', 'konum': ''}],
  'program': [{'tarih': '2026-11-12', 'saat': '05:00', 'baslik': 'Sabah namazı', 'yer': 'Harem'},
              {'tarih': '2026-11-12', 'saat': '14:30', 'baslik': 'Mekke ziyaretleri', 'yer': 'Otel lobisi', 'konum': 'javascript:alert(1)'},
              {'tarih': '2026-11-13', 'saat': '08:00', 'baslik': "Medine'ye hareket", 'yer': 'Lobi'}],
  'duyurular': [{'id': 5, 'baslik': "Medine'ye hareket", 'metin': 'Yarın 08:00 <img src=x onerror=window.__xss=1>', 'onemli': True, 'yazan': 'Ali', 'olusturma': '2026-11-12T07:05:00Z'},
                {'id': 4, 'baslik': 'Saat değişikliği', 'metin': 'Buluşma 14:30\'a alındı.', 'onemli': False, 'yazan': None, 'olusturma': '2026-11-11T18:00:00Z'}]
}

hata = 0
def kontrol(ok, ad, ayrinti=''):
    global hata
    hata += not ok
    print('✓' if ok else '✗', ad, ayrinti)

# Statik dosyalar
r = subprocess.run(['node', '--check', os.path.join(KOK, 'kafile', 'sw.js')], capture_output=True, text=True)
kontrol(r.returncode == 0, 'sw.js sözdizimi', r.stderr.strip()[-150:])
man = json.load(open(os.path.join(KOK, 'kafile', 'manifest.webmanifest'), encoding='utf-8'))
kontrol(man['start_url'] == '/kafile/' and man['scope'] == '/kafile/' and all(os.path.exists(os.path.join(KOK, 'kafile', i['src'])) for i in man['icons'])
        and {'192x192', '512x512'} <= {i['sizes'] for i in man['icons']}, 'manifest: kapsam /kafile/, 192 ve 512 ikonlar mevcut')

def baglam(b, rpc='veri', konum=None):
    """rpc: 'veri' | 'yok' (kafile bulunamadı) | 'kopuk' (internet yok)"""
    c = b.new_context(viewport={'width': 390, 'height': 844}, service_workers='block', locale='tr-TR',
                      permissions=['geolocation'] if konum else [], geolocation=konum)
    c.add_init_script(f"window.__SIMDI = '{SIMDI}'; window.confirm = function(){{ return true; }};")
    c.__rpc = rpc; c.__istek = []; c.__wa = []
    def rpc_yanit(route, req):
        c.__istek.append(json.loads(req.post_data or '{}'))
        if c.__rpc == 'kopuk': return route.abort()
        kod = (json.loads(req.post_data or '{}').get('p_kod') or '')
        body = json.dumps(KAFILE) if (c.__rpc == 'veri' and kod == 'TEST-ABCDE') else 'null'
        route.fulfill(status=200, body=body, headers={'content-type': 'application/json', 'access-control-allow-origin': '*'})
    c.route('**/rest/v1/rpc/kafile_getir', rpc_yanit)
    c.route('https://wa.me/**', lambda route, req: (c.__wa.append(req.url), route.fulfill(status=200, body='ok')))
    c.route(re.compile(r'^https?://(?!localhost)(?!wa\.me)(?!wpkjxwbvewwgdclbsdya)'), lambda route, req: route.abort())
    return c

def sayfa(c, errs, adres=URL):
    pg = c.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)[:160]))
    pg.goto(adres, wait_until='domcontentloaded'); pg.wait_for_timeout(500)
    return pg

def tasma(pg):
    return pg.evaluate('document.documentElement.scrollWidth > window.innerWidth + 1')

with sync_playwright() as p:
    b = p.chromium.launch()

    # ── Giriş ──
    c = baglam(b); errs = []; pg = sayfa(c, errs)
    kontrol(pg.is_visible('#giris') and not pg.is_visible('#uygulama'), 'Giriş: kod ekranı açılıyor', errs)
    pg.click('#girisBtn'); pg.wait_for_timeout(200)
    kontrol(pg.is_visible('#girisHata') and 'kodunuzu girin' in pg.inner_text('#girisHata'), 'Giriş: boş kodla uyarı veriyor')
    pg.fill('#kodKutu', 'YANLIS-KOD'); pg.click('#girisBtn'); pg.wait_for_timeout(400)
    kontrol('bulunamadı' in pg.inner_text('#girisHata') and not pg.is_visible('#uygulama'), 'Giriş: yanlış kodla "bulunamadı" diyor')
    c.__rpc = 'kopuk'; pg.click('#girisBtn'); pg.wait_for_timeout(400)
    kontrol('Bağlantı kurulamadı' in pg.inner_text('#girisHata'), 'Giriş: internet yokken bağlantı uyarısı veriyor')
    c.__rpc = 'veri'; pg.fill('#kodKutu', ' test-abcde '); pg.click('#girisBtn'); pg.wait_for_timeout(500)
    kontrol(pg.is_visible('#uygulama') and c.__istek[-1].get('p_kod') == 'TEST-ABCDE', 'Giriş: küçük harf/boşluklu kod düzeltilip kabul ediliyor', errs)

    # ── Bugün ──
    m = pg.inner_text('#ekran')
    kontrol('3. Gün' in m and 'Dönüşe 11 gün' in m, 'Bugün: kafilenin kaçıncı günü ve dönüşe kalan gün doğru', m[:120].replace('\n', ' | '))
    kart = pg.locator('section[aria-label="Sıradaki buluşma"]')
    kontrol(kart.count() == 1 and '14:30' in kart.inner_text() and 'Otel lobisi' in kart.inner_text(), 'Bugün: sıradaki buluşma 14:30 Otel lobisi')
    kontrol(kart.locator('a', has_text='Konumu aç').count() == 0, 'Güvenlik: "javascript:" konum bağlantısı gösterilmiyor')
    kontrol(kart.locator('a', has_text='Rehberi ara').get_attribute('href') == 'tel:+905330000000', 'Bugün: Rehberi ara → tel:+905330000000')
    kontrol(pg.locator('.icerik > .zaman-cizelge .zc-satir.gecti', has_text='Sabah namazı').count() == 1 and pg.locator('.icerik > .zaman-cizelge .zc-satir.simdi', has_text='Mekke ziyaretleri').count() == 1,
            'Bugün: geçen etkinlik soluk, sıradaki vurgulu')
    kontrol('SON DUYURU' in m.upper() and pg.is_visible('#menuNokta'), 'Bugün: son duyuru kartı ve okunmamış duyuru işareti var')
    pg.click('details.tum summary'); pg.wait_for_timeout(200)
    kontrol(pg.locator('details.tum .gun-baslik').count() == 2 and '4. GÜN' in pg.inner_text('details.tum').upper(), 'Bugün: "Tüm program" 2 günü gün numarasıyla listeliyor')
    kontrol(not tasma(pg), 'Bugün: telefonda yatay taşma yok')

    # ── Duyurular ──
    pg.click('.alt-menu [data-sekme="duyurular"]'); pg.wait_for_timeout(300)
    d = pg.locator('article.duyuru')
    kontrol(d.count() == 2 and 'ÖNEMLİ' in d.nth(0).inner_text() and 'Saat değişikliği' in d.nth(1).inner_text(), 'Duyurular: önemli duyuru en üstte, ikisi de listede')
    kontrol(pg.evaluate('!window.__xss') and '<img' in d.nth(0).inner_text(), 'Güvenlik: duyurudaki HTML çalışmıyor, düz yazı gösteriliyor')
    kontrol(not pg.is_visible('#menuNokta'), 'Duyurular: açılınca okunmamış işareti kalkıyor')

    # ── Rehber: sayaç ve valiz ──
    pg.click('.alt-menu [data-sekme="rehber"]'); pg.wait_for_timeout(300)
    for _ in range(3): pg.click('[data-eylem="arttir"]')
    kontrol(pg.inner_text('#sayacSayi') == '3', 'Sayaç: tavaf 3 oldu')
    pg.check('input[data-valiz="Pasaport"]'); pg.wait_for_timeout(100)
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(500)
    kontrol(pg.is_visible('#uygulama'), 'Kayıt: sayfa yenilenince kafile kodu hatırlanıyor (tekrar kod istemiyor)')
    pg.click('.alt-menu [data-sekme="rehber"]'); pg.wait_for_timeout(300)
    kontrol(pg.inner_text('#sayacSayi') == '3' and pg.is_checked('input[data-valiz="Pasaport"]'), 'Kayıt: sayaç ve valiz işaretleri kapanıp açılınca korunuyor')
    pg.click('[data-eylem="mod-say"]'); pg.wait_for_timeout(100)
    kontrol(pg.inner_text('#sayacSayi') == '0' and 'tur' in pg.inner_text('.halka'), "Sayaç: Sa'y ayrı sayılıyor")
    for _ in range(9): pg.click('[data-eylem="arttir"]', force=True)
    kontrol(pg.inner_text('#sayacSayi') == '7' and pg.is_disabled('[data-eylem="arttir"]'), "Sayaç: 7'de duruyor, buton 'Tamamlandı'")
    pg.click('[data-eylem="azalt"]'); s1 = pg.inner_text('#sayacSayi'); pg.click('[data-eylem="sifirla"]')
    kontrol(s1 == '6' and pg.inner_text('#sayacSayi') == '0', 'Sayaç: geri al ve sıfırla çalışıyor')
    pg.click('[data-eylem="mod-tavaf"]')
    kontrol(pg.inner_text('#sayacSayi') == '3', 'Sayaç: tavaf sayısı sa\'y\'dan etkilenmiyor')
    kontrol(not tasma(pg), 'Rehber: telefonda yatay taşma yok')

    # ── Vakitler ──
    pg.click('.alt-menu [data-sekme="vakitler"]'); pg.wait_for_timeout(300)
    def vakitler():
        return [re.findall(r'\d\d:\d\d', s)[0] for s in pg.locator('#vakitListesi .vakit-satir').all_inner_texts()]
    mk = vakitler()
    dk = [int(x[:2]) * 60 + int(x[3:]) for x in mk]
    kontrol(len(mk) == 6 and dk == sorted(dk) and '04:45' <= mk[0] <= '05:30' and '11:55' <= mk[2] <= '12:15' and '17:30' <= mk[4] <= '18:00', 'Vakitler: Mekke 6 vakit sıralı ve makul', ' '.join(mk))
    kontrol('Öğle' in pg.inner_text('#siradakiVakit'), 'Vakitler: 11:00\'de sıradaki vakit Öğle')
    # Bağımsız kontrol: aynı gün için Ümmü'l-Kurâ değerleriyle (timesprayer.com, 30 Ekim 2026 Mekke: 05:05 06:23 12:04 15:20 17:46 19:16) ±2 dk
    ref = pg.evaluate("(() => { const v = window.__namazVakitleri({y:2026,m:10,g:30}, 21.4225, 39.8262, 3, false); return ['imsak','gunes','ogle','ikindi','aksam','yatsi'].map(k => Math.round(v[k]*60)); })()")
    beklenen = [5*60+5, 6*60+23, 12*60+4, 15*60+20, 17*60+46, 19*60+16]
    kontrol(all(abs(a - e) <= 2 for a, e in zip(ref, beklenen)), 'Vakitler: hesap Ümmü\'l-Kurâ referansıyla ±2 dk içinde', str(ref))
    pg.click('[data-eylem="sehir-medine"]'); pg.wait_for_timeout(200)
    kontrol(vakitler() != mk and len(vakitler()) == 6, 'Vakitler: Medine seçilince saatler değişiyor')
    kontrol(not tasma(pg), 'Vakitler: telefonda yatay taşma yok')

    # ── Acil ──
    pg.click('.alt-menu [data-sekme="acil"]'); pg.wait_for_timeout(300)
    hrefler = pg.eval_on_selector_all('#ekran a[href^="tel:"]', 'els => els.map(e => e.getAttribute("href"))')
    kontrol({'tel:+905330000000', 'tel:+96612000000' + '0', 'tel:+905331980781', 'tel:911', 'tel:997', 'tel:+903122922929'} <= set(hrefler), 'Acil: rehber, otel, ofis, 911, 997, konsolosluk numaraları doğru', str(hrefler))
    kontrol('Test Otel <b>kalin</b>' in pg.inner_text('.otel-karti') and 'شارع' in pg.inner_text('.otel-karti'), 'Acil: otel kartı (Arapça adres dahil) düz yazı olarak gösteriliyor')
    kontrol(pg.locator('.otel-karti').count() == 2, 'Acil: iki otel kartı var')
    kontrol(not tasma(pg), 'Acil: telefonda yatay taşma yok')
    kontrol(not errs, 'Hiçbir ekranda JavaScript hatası yok', errs)
    c.close()

    # ── Konum gönder ve kıble (konum izni verilmiş, İstanbul) ──
    c = baglam(b, konum={'latitude': 41.0082, 'longitude': 28.9784}); errs = []
    pg = sayfa(c, errs, URL + '#TEST-ABCDE')
    kontrol(pg.is_visible('#uygulama') and '#' not in pg.url, 'Paylaşılan bağlantı: #KOD ile doğrudan kafile açılıyor, kod adresten siliniyor', errs)
    pg.click('.alt-menu [data-sekme="acil"]'); pg.wait_for_timeout(200)
    pg.click('[data-eylem="konum-gonder"]'); pg.wait_for_timeout(1200)
    kontrol(c.__wa and 'wa.me/905330000000' in c.__wa[-1] and 'maps.google.com%2F%3Fq%3D41.0082' in c.__wa[-1], 'Acil: "Konumumu gönder" rehberin WhatsApp\'ına harita bağlantısıyla gidiyor', (c.__wa or [''])[-1][:120])
    pg.goto(URL, wait_until='domcontentloaded'); pg.wait_for_timeout(400)
    pg.click('.alt-menu [data-sekme="vakitler"]'); pg.click('[data-eylem="kible"]'); pg.wait_for_timeout(800)
    t = pg.inner_text('#kibleYazi'); aci = re.search(r'(\d+)°', t)
    kontrol(aci is not None and 145 <= int(aci.group(1)) <= 158, 'Kıble: İstanbul\'dan yön ~152° hesaplanıyor', t[:90])
    kontrol(not errs, 'Konum/kıble sırasında JavaScript hatası yok', errs)
    c.close()

    # ── Kültür turu (Saraybosna): sayaç yok, yerel saat, yerel vakitler, yerel acil numara ──
    KULTUR = dict(KAFILE, kod='TEST-KULTR', ad='Balkan Turu', tur_turu='kultur', acil_tel='112', baslangic='2026-11-10', bitis='2026-11-16',
                  oteller=[{'sehir': 'Saraybosna', 'ad': 'Test Otel Saraybosna', 'adres': 'Ferhadija 1', 'adres_ar': '', 'tel': '+387 33 000 000', 'konum': ''}],
                  program=[{'tarih': '2026-11-12', 'saat': '09:00', 'baslik': 'Kahvaltı', 'yer': 'Otel'},
                           {'tarih': '2026-11-12', 'saat': '12:30', 'baslik': 'Başçarşı gezisi', 'yer': 'Otel lobisi'}], duyurular=[])
    c = b.new_context(viewport={'width': 390, 'height': 844}, service_workers='block', locale='tr-TR', timezone_id='Europe/Sarajevo',
                      permissions=['geolocation'], geolocation={'latitude': 43.8563, 'longitude': 18.4131})
    c.add_init_script("window.__SIMDI = '2026-11-12T11:00:00+01:00';")
    c.route('**/rest/v1/rpc/kafile_getir', lambda route, req: route.fulfill(status=200, body=json.dumps(KULTUR), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'}))
    c.route(re.compile(r'^https?://(?!localhost)(?!wpkjxwbvewwgdclbsdya)'), lambda route, req: route.abort())
    errs = []; pg = sayfa(c, errs, URL + '#TEST-KULTR')
    kart = pg.locator('section[aria-label="Sıradaki buluşma"]')
    kontrol(kart.count() == 1 and '12:30' in kart.inner_text() and pg.locator('.icerik > .zaman-cizelge .zc-satir.gecti', has_text='Kahvaltı').count() == 1,
            'Kültür turu: program yerel saate göre (Saraybosna 11:00 → sıradaki 12:30)', errs)
    pg.click('.alt-menu [data-sekme="rehber"]'); pg.wait_for_timeout(200)
    m = pg.inner_text('#ekran')
    kontrol(pg.locator('#sayacSayi').count() == 0 and 'Yolculuk Rehberi' in m and 'powerbank' in m and 'Zemzem' not in m and 'Riyali' not in m,
            'Kültür turu: tavaf sayacı ve umreye özel valiz maddeleri yok')
    pg.click('.alt-menu [data-sekme="vakitler"]'); pg.wait_for_timeout(200)
    kontrol(pg.locator('[data-eylem="sehir-mekke"]').count() == 0 and pg.locator('#ekran [data-eylem="konum-vakit"]').count() >= 1, 'Kültür turu: Mekke/Medine yerine "Konumumu kullan" çıkıyor')
    pg.click('#ekran .btn-dolu[data-eylem="konum-vakit"]'); pg.wait_for_timeout(600)
    mk = [re.findall(r'\d\d:\d\d', x)[0] for x in pg.locator('#vakitListesi .vakit-satir').all_inner_texts()]
    kontrol(len(mk) == 6 and '06:30' <= mk[1] <= '07:10' and '11:30' <= mk[2] <= '11:55' and '16:05' <= mk[4] <= '16:40' and 'Öğle' in pg.inner_text('#siradakiVakit'),
            'Kültür turu: Saraybosna vakitleri yerel saatle makul, sıradaki Öğle', ' '.join(mk))
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(400); pg.click('.alt-menu [data-sekme="vakitler"]'); pg.wait_for_timeout(200)
    kontrol(pg.locator('#vakitListesi .vakit-satir').count() == 6, 'Kültür turu: konum hatırlanıyor, tekrar sorulmuyor')
    pg.click('.alt-menu [data-sekme="acil"]'); pg.wait_for_timeout(200)
    hrefler = pg.eval_on_selector_all('#ekran a[href^="tel:"]', 'els => els.map(e => e.getAttribute("href"))')
    kontrol('tel:112' in hrefler and 'tel:911' not in hrefler and 'tel:997' not in hrefler and 'tel:+903122922929' in hrefler and 'tel:+38733000000' in hrefler,
            'Kültür turu: acil ekranında yerel 112 ve konsolosluk var, Suudi numaraları yok', str(hrefler))
    kontrol(not tasma(pg) and not errs, 'Kültür turu: taşma ve JavaScript hatası yok', errs)
    c.close()

    # ── Duyuru bildirimleri (Web Push) — tarayıcının bildirim/servis-çalışanı arayüzü taklit edilir ──
    PUSH_TAKLIT = """
      window.__olaylar = [];
      const kayitli = () => { try { return JSON.parse(localStorage.getItem('test-abone')); } catch (e) { return null; } };
      const abone = (j) => j && ({ toJSON: () => j, unsubscribe: () => { localStorage.removeItem('test-abone'); window.__olaylar.push('unsubscribe'); return Promise.resolve(true); } });
      const kayit = { pushManager: {
        getSubscription: () => Promise.resolve(abone(kayitli())),
        subscribe: (o) => { window.__olaylar.push('subscribe:' + o.userVisibleOnly + ':' + o.applicationServerKey.length);
          const j = { endpoint: 'https://fcm.googleapis.com/fcm/send/TEST', keys: { p256dh: 'B' + 'x'.repeat(86), auth: 'a'.repeat(22) } };
          localStorage.setItem('test-abone', JSON.stringify(j)); return Promise.resolve(abone(j)); } } };
      Object.defineProperty(navigator, 'serviceWorker', { configurable: true, value: { register: () => Promise.resolve(kayit), ready: Promise.resolve(kayit), addEventListener() {} } });
      window.PushManager = function () {};
      const izin = { deger: localStorage.getItem('test-izin') || 'default' };
      window.Notification = { get permission() { return izin.deger; },
        requestPermission: () => { izin.deger = window.__IZIN_YANIT || 'granted'; localStorage.setItem('test-izin', izin.deger); return Promise.resolve(izin.deger); } };
    """
    def push_baglam(izin_yanit='granted', ua=None, push_var=True):
        c = b.new_context(viewport={'width': 390, 'height': 844}, service_workers='block', locale='tr-TR', **({'user_agent': ua} if ua else {}))
        c.add_init_script(f"window.__SIMDI = '{SIMDI}'; window.confirm = function(){{ return true; }}; window.__IZIN_YANIT = '{izin_yanit}';")
        if push_var: c.add_init_script(PUSH_TAKLIT)
        c.__rpc = []
        def rpc(route, req):
            ad = req.url.split('/rpc/')[1]; govde = json.loads(req.post_data or '{}'); c.__rpc.append((ad, govde))
            body = json.dumps(KAFILE) if ad == 'kafile_getir' else 'true'
            route.fulfill(status=200, body=body, headers={'content-type': 'application/json', 'access-control-allow-origin': '*'})
        c.route('**/rest/v1/rpc/**', rpc)
        c.route(re.compile(r'^https?://(?!localhost)(?!wpkjxwbvewwgdclbsdya)'), lambda route, req: route.abort())
        return c
    c = push_baglam(); errs = []; pg = sayfa(c, errs, URL + '#TEST-ABCDE'); pg.wait_for_timeout(300)
    kontrol(pg.locator('#ekran [data-eylem="bildirim-ac"]').count() == 1, 'Bildirim: Bugün ekranında "Bildirimleri aç" kartı var', errs)
    pg.click('#ekran [data-eylem="bildirim-ac"]'); pg.wait_for_timeout(500)
    ab = [g for a_, g in c.__rpc if a_ == 'bildirim_abone_ol']
    kontrol(ab and ab[-1]['p_kod'] == 'TEST-ABCDE' and ab[-1]['p_endpoint'].startswith('https://fcm.googleapis.com/') and ab[-1]['p_p256dh'] and ab[-1]['p_auth']
            and 'subscribe:true:65' in pg.evaluate('window.__olaylar'), 'Bildirim: izin → abonelik (65 baytlık anahtarla) → grup koduyla sunucuya kaydediliyor', str(ab[-1:])[:120])
    kontrol(pg.locator('#ekran [data-eylem="bildirim-ac"]').count() == 0, 'Bildirim: açıldıktan sonra kart kayboluyor')
    pg.click('.alt-menu [data-sekme="duyurular"]'); pg.wait_for_timeout(200)
    kontrol('Bildirimler açık' in pg.inner_text('#ekran'), 'Bildirim: Duyurular ekranında "Bildirimler açık" yazıyor')
    pg.goto(URL + '?sekme=duyurular', wait_until='domcontentloaded'); pg.wait_for_timeout(500)
    kontrol(pg.locator('.alt-menu [data-sekme="duyurular"][aria-current="page"]').count() == 1 and 'sekme=' not in pg.url and 'Bildirimler açık' in pg.inner_text('#ekran'),
            'Bildirim: bildirime dokununca (?sekme=duyurular) uygulama Duyurular\'da açılıyor, abonelik hatırlanıyor')
    pg.click('[data-eylem="bildirim-kapat"]'); pg.wait_for_timeout(400)
    kontrol([g for a_, g in c.__rpc if a_ == 'bildirim_abonelik_sil'] and 'unsubscribe' in pg.evaluate('window.__olaylar') and pg.locator('#ekran [data-eylem="bildirim-ac"]').count() == 1,
            'Bildirim: "Kapat" aboneliği telefondan ve sunucudan siliyor')
    pg.click('#ekran [data-eylem="bildirim-ac"]'); pg.wait_for_timeout(400); n_sil = len([1 for a_, _ in c.__rpc if a_ == 'bildirim_abonelik_sil'])
    pg.click('.alt-menu [data-sekme="bugun"]'); pg.click('[data-eylem="cikis"]'); pg.wait_for_timeout(400)
    kontrol(len([1 for a_, _ in c.__rpc if a_ == 'bildirim_abonelik_sil']) == n_sil + 1, 'Bildirim: "Gruptan çık" aboneliği de siliyor')
    kontrol(not errs, 'Bildirim akışında JavaScript hatası yok', errs)
    c.close()
    c = push_baglam(izin_yanit='denied'); errs = []; pg = sayfa(c, errs, URL + '#TEST-ABCDE'); pg.wait_for_timeout(300)
    pg.click('#ekran [data-eylem="bildirim-ac"]'); pg.wait_for_timeout(300); pg.click('.alt-menu [data-sekme="duyurular"]'); pg.wait_for_timeout(200)
    kontrol('izin verilmemiş' in pg.inner_text('#ekran') and not [1 for a_, _ in c.__rpc if a_ == 'bildirim_abone_ol'], 'Bildirim: izin reddedilince açıklama çıkıyor, sunucuya kayıt yapılmıyor', errs)
    c.close()
    c = push_baglam(ua='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1', push_var=False)
    c.add_init_script("delete window.PushManager;")
    errs = []; pg = sayfa(c, errs, URL + '#TEST-ABCDE'); pg.wait_for_timeout(300); pg.click('.alt-menu [data-sekme="duyurular"]'); pg.wait_for_timeout(200)
    kontrol('Ana Ekrana Ekle' in pg.inner_text('#ekran') and pg.locator('#ekran [data-eylem="bildirim-ac"]').count() == 0, 'Bildirim: ana ekrana kurulmamış iPhone\'da önce kurulum anlatılıyor', errs)
    c.close()
    # Servis çalışanı: gelen bildirimi gösterme ve dokununca uygulamayı açma (node ile)
    sw_test = r"""
      const fs = require('fs'), vm = require('vm'); const dinle = {}; const kayit = [];
      const self = { addEventListener: (a, f) => dinle[a] = f, registration: { scope: 'https://ismailcosarturizm.com.tr/kafile/', showNotification: (b, o) => { kayit.push(['goster', b, o]); return Promise.resolve(); } },
        clients: { matchAll: () => Promise.resolve([]), openWindow: (u) => { kayit.push(['ac', u]); return Promise.resolve(); } }, skipWaiting() {} };
      vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), { self, caches: {}, fetch() {}, URL, location: { origin: 'https://ismailcosarturizm.com.tr' }, console });
      const bekle = []; const olay = (o) => Object.assign(o, { waitUntil: (p) => bekle.push(p) });
      dinle.push(olay({ data: { json: () => ({ baslik: "Medine'ye hareket", metin: 'Yarın 08:00', etiket: 'duyuru-5', url: '/kafile/?sekme=duyurular' }) } }));
      dinle.notificationclick(olay({ notification: { close() {}, data: { url: '/kafile/?sekme=duyurular' } } }));
      Promise.all(bekle).then(() => console.log(JSON.stringify(kayit)));
    """
    r = subprocess.run(['node', '-e', sw_test, os.path.join(KOK, 'kafile', 'sw.js')], capture_output=True, text=True)
    try: k_ = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: k_ = []
    kontrol(len(k_) == 2 and k_[0][1] == "Medine'ye hareket" and k_[0][2]['body'] == 'Yarın 08:00' and k_[0][2]['tag'] == 'duyuru-5'
            and k_[1] == ['ac', 'https://ismailcosarturizm.com.tr/kafile/?sekme=duyurular'], 'Servis çalışanı: bildirimi başlık/metinle gösteriyor, dokununca Duyurular\'ı açıyor', (r.stderr or r.stdout)[-160:])

    # ── Kafile pasife alınmış ──
    c = baglam(b); errs = []; pg = sayfa(c, errs, URL + '#TEST-ABCDE')
    c.__rpc = 'yok'; pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(700)
    kontrol(pg.is_visible('#giris') and 'artık aktif değil' in pg.inner_text('#girisHata'), 'Pasif kafile: telefonda kayıtlıysa bile çıkış yapıp bilgi veriyor', errs)
    c.close()

    # ── İnternet yok ama daha önce girilmiş ──
    c = baglam(b); errs = []; pg = sayfa(c, errs, URL + '#TEST-ABCDE')
    c.__rpc = 'kopuk'; pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(700)
    kontrol(pg.is_visible('#uygulama') and 'İnternet yok' in pg.inner_text('#ekran') and 'Mekke ziyaretleri' in pg.inner_text('#ekran'),
            'Çevrimdışı: son kaydedilen program gösteriliyor, uyarı şeridi var', errs)
    pg.click('[data-eylem="cikis"]'); pg.wait_for_timeout(300)
    kontrol(pg.is_visible('#giris'), 'Kafileden çık: kod ekranına dönüyor')
    c.close()
    b.close()

print('\n=== KAFİLE UYGULAMASI TESTİ:', 'TEMİZ' if not hata else f'{hata} SORUN')
sys.exit(1 if hata else 0)
