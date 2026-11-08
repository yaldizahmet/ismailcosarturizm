"""Kafile uygulamasını (kafile/) telefon boyutunda uçtan uca test eder; gerçek veritabanına dokunmaz.
Kafile verisi sahte bir RPC yanıtıyla verilir; saat window.__SIMDI ile sabitlenir.
Kullanım: önce repo kökünde `python3 -m http.server 8765`, sonra `python3 _test/kafile.py`."""
from urllib.parse import unquote
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

def sayfa(c, errs, adres=URL, karsilama=False):
    pg = c.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)[:160]))
    if not karsilama:  # karşılama ekranı yalnızca kendi testinde; diğer testler doğrudan Bugün ile başlasın
        pg.add_init_script("try{['TEST-ABCDE','TEST-KULTR'].forEach(function(k){localStorage.setItem('kafile-karsilandi-'+k,'true')})}catch(e){}")
    pg.goto(adres, wait_until='domcontentloaded'); pg.wait_for_timeout(500)
    return pg

def tasma(pg):
    return pg.evaluate('document.documentElement.scrollWidth > window.innerWidth + 1')

with sync_playwright() as p:
    b = p.chromium.launch()

    # ── Giriş ──
    c = baglam(b); errs = []; pg = sayfa(c, errs, karsilama=True)
    kontrol(pg.is_visible('#giris') and not pg.is_visible('#uygulama'), 'Giriş: kod ekranı açılıyor', errs)
    kontrol(pg.evaluate("(()=>{const i=document.querySelector('#giris .giris-marka img');return !!i&&i.complete&&i.naturalWidth>0})()"), 'Giriş: şirket logosu görünüyor')
    pg.click('#girisBtn'); pg.wait_for_timeout(200)
    kontrol(pg.is_visible('#girisHata') and 'kodunuzu girin' in pg.inner_text('#girisHata'), 'Giriş: boş kodla uyarı veriyor')
    pg.fill('#kodKutu', 'YANLIS-KOD'); pg.click('#girisBtn'); pg.wait_for_timeout(400)
    kontrol('bulunamadı' in pg.inner_text('#girisHata') and not pg.is_visible('#uygulama'), 'Giriş: yanlış kodla "bulunamadı" diyor')
    c.__rpc = 'kopuk'; pg.click('#girisBtn'); pg.wait_for_timeout(400)
    kontrol('Bağlantı kurulamadı' in pg.inner_text('#girisHata'), 'Giriş: internet yokken bağlantı uyarısı veriyor')
    c.__rpc = 'veri'; pg.fill('#kodKutu', ' test-abcde '); pg.click('#girisBtn'); pg.wait_for_timeout(500)
    kontrol(pg.is_visible('#uygulama') and c.__istek[-1].get('p_kod') == 'TEST-ABCDE', 'Giriş: küçük harf/boşluklu kod düzeltilip kabul ediliyor', errs)

    # ── Karşılama (yalnızca ilk girişte) ──
    k = pg.inner_text('#ekran') if pg.locator('#karsilama').count() else ''
    kontrol('Hoş geldiniz' in k and pg.locator('#adimBildirim').count() == 1 and pg.locator('#adimKur').count() == 1 and not pg.is_visible('.alt-menu'),
            'Karşılama: ilk girişte "Hoş geldiniz", 2 adım (bildirim, kurulum); alt menü gizli', k[:100].replace('\n', ' | '))
    kontrol('REHBERİNİZ' in k.upper() and pg.locator('#ekran header.bas .marka img').count() == 1, 'Karşılama: rehber bilgisi ve logo var')
    kontrol(not tasma(pg), 'Karşılama: telefonda yatay taşma yok')
    pg.click('[data-eylem="karsilama-bitti"]'); pg.wait_for_timeout(200)
    kontrol(pg.locator('#karsilama').count() == 0 and pg.is_visible('.alt-menu') and '3. Gün' in pg.inner_text('#ekran'), 'Karşılama: "Başla" ile Bugün ekranına geçiyor')
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(500)
    kontrol(pg.locator('#karsilama').count() == 0 and '3. Gün' in pg.inner_text('#ekran'), 'Karşılama: ikinci açılışta tekrar çıkmıyor')

    # ── Bugün ──
    m = pg.inner_text('#ekran')
    kontrol('3. Gün' in m and 'Dönüşe 11 gün' in m, 'Bugün: kafilenin kaçıncı günü ve dönüşe kalan gün doğru', m[:120].replace('\n', ' | '))
    kart = pg.locator('section[aria-label="Sıradaki buluşma"]')
    kontrol(kart.count() == 1 and '14:30' in kart.inner_text() and 'Otel lobisi' in kart.inner_text(), 'Bugün: sıradaki buluşma 14:30 Otel lobisi')
    kontrol(kart.locator('a', has_text='Konumu aç').count() == 0, 'Güvenlik: "javascript:" konum bağlantısı gösterilmiyor')
    kontrol(kart.locator('a', has_text='Rehberi ara').get_attribute('href') == 'tel:+905330000000', 'Bugün: Rehberi ara → tel:+905330000000')
    kontrol(pg.locator('.icerik > .zaman-cizelge .zc-satir.gecti', has_text='Sabah namazı').count() == 1 and pg.locator('.icerik > .zaman-cizelge .zc-satir.simdi', has_text='Mekke ziyaretleri').count() == 1,
            'Bugün: geçen etkinlik soluk, sıradaki vurgulu')
    # Programı paylaş
    pg.evaluate("window.__pv = null; navigator.share = function(v){ window.__pv = v; return Promise.resolve(); }")
    pg.click('[data-eylem="program-paylas"]'); pg.wait_for_timeout(200)
    kontrol(pg.is_visible('#paylasPerde') and pg.locator('[data-kapsam="gun"]').count() == 1 and pg.locator('[data-kapsam="tum"]').count() == 1, 'Program paylaş: "Bugünün programı" ve "Tüm program" seçenekleri açılıyor')
    pg.click('[data-kapsam="gun"]'); pg.wait_for_timeout(200)
    pt = (pg.evaluate('window.__pv') or {}).get('text', '')
    kontrol('Bugün · 3. Gün' in pt and '✅' in pt and any(l.startswith('✅') and 'Sabah namazı' in l for l in pt.split('\n')) and any(l.startswith('▫️') and 'Mekke ziyaretleri' in l for l in pt.split('\n'))
            and pg.locator('#paylasPerde').count() == 0, 'Program paylaş: bugünün programı; geçen etkinlik ✅, sıradakiler ▫️', pt[:200])
    pg.click('[data-eylem="program-paylas"]'); pg.wait_for_timeout(200); pg.click('[data-kapsam="tum"]'); pg.wait_for_timeout(200)
    pt = (pg.evaluate('window.__pv') or {}).get('text', '')
    kontrol('– Program*' in pt and '📍 *3. Gün' in pt and '\n*4. Gün' in pt and '▫️ 08:00' in pt and '(bugün)' in pt and 'ismailcosarturizm.com.tr' in pt and 'TEST-ABCDE' not in pt,
            'Program paylaş: tüm program gün gün; bugün 📍, gelecek günler işaretsiz; grup kodu metinde yok', pt[:400].replace('\n', ' | '))
    pg.evaluate("delete navigator.share; navigator.share = undefined; window.__sonPaylasim = null")
    pg.click('[data-eylem="program-paylas"]'); pg.wait_for_timeout(200); pg.click('[data-kapsam="gun"]'); pg.wait_for_timeout(400)
    kontrol(pg.evaluate('window.__sonPaylasim') and 'kopyalandı' in pg.inner_text('#bildirim') and not errs, 'Program paylaş: paylaş menüsü olmayan cihazda kopyalayıp haber veriyor', errs)
    kontrol('SON DUYURU' in m.upper() and pg.is_visible('#menuNokta'), 'Bugün: son duyuru kartı ve okunmamış duyuru işareti var')
    pg.click('details.tum summary'); pg.wait_for_timeout(200)
    kontrol(pg.locator('details.tum .gun-baslik').count() == 2 and '4. GÜN' in pg.inner_text('details.tum').upper(), 'Bugün: "Tüm program" 2 günü gün numarasıyla listeliyor')
    kontrol(not tasma(pg), 'Bugün: telefonda yatay taşma yok')
    kontrol(pg.locator('#yorumKart').count() == 0, 'Google yorumu: tur devam ederken Bugün ekranında yorum kartı yok')

    # ── Duyurular ──
    pg.click('.alt-menu [data-sekme="duyurular"]'); pg.wait_for_timeout(300)
    d = pg.locator('article.duyuru')
    kontrol(d.count() == 2 and 'ÖNEMLİ' in d.nth(0).inner_text() and 'Saat değişikliği' in d.nth(1).inner_text(), 'Duyurular: önemli duyuru en üstte, ikisi de listede')
    kontrol(pg.evaluate('!window.__xss') and '<img' in d.nth(0).inner_text(), 'Güvenlik: duyurudaki HTML çalışmıyor, düz yazı gösteriliyor')
    kontrol(not pg.is_visible('#menuNokta'), 'Duyurular: açılınca okunmamış işareti kalkıyor')

    # ── Logo: her ekranın üstünde ──
    for sk in ['bugun', 'duyurular', 'rehber', 'vakitler', 'acil']:
        pg.click(f'.alt-menu [data-sekme="{sk}"]'); pg.wait_for_timeout(250)
        kontrol(pg.evaluate("(()=>{const i=document.querySelector('#ekran header.bas .marka img');return !!i&&i.complete&&i.naturalWidth>0})()"), f'Logo: {sk} ekranında şirket logosu var')

    # ── Rehber: sayaç ve valiz ──
    pg.click('.alt-menu [data-sekme="rehber"]'); pg.wait_for_timeout(300)
    kontrol(pg.locator('#gecmisBos').count() == 1 and pg.locator('#gecmisPaylas').count() == 0, 'Geçmiş: hiç sayım yokken paylaş butonu yok, açıklama var')
    for _ in range(3): pg.click('[data-eylem="arttir"]')
    kontrol(pg.inner_text('#sayacSayi') == '3', 'Sayaç: tavaf 3 oldu')
    pg.check('input[data-valiz="Pasaport"]'); pg.wait_for_timeout(100)
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(500)
    kontrol(pg.is_visible('#uygulama'), 'Kayıt: sayfa yenilenince kafile kodu hatırlanıyor (tekrar kod istemiyor)')
    pg.click('.alt-menu [data-sekme="rehber"]'); pg.wait_for_timeout(300)
    kontrol(pg.inner_text('#sayacSayi') == '3' and pg.is_checked('input[data-valiz="Pasaport"]'), 'Kayıt: sayaç ve valiz işaretleri kapanıp açılınca korunuyor')
    pg.click('[data-eylem="mod-say"]'); pg.wait_for_timeout(100)
    kontrol(pg.inner_text('#sayacSayi') == '0' and 'tur' in pg.inner_text('.halka'), "Sayaç: Sa'y ayrı sayılıyor")
    wa0 = unquote((pg.get_attribute('#gecmisPaylas', 'href') or '').split('text=', 1)[-1]) if pg.locator('#gecmisPaylas').count() else ''
    kontrol('tavaf 3/7' in (pg.inner_text('#gecmisDevam') if pg.locator('#gecmisDevam').count() else '') and 'Devam eden: tavaf 3/7 şavt' in wa0 and 'Henüz tamamlanan' in wa0,
            'Paylaş: 7 tamamlanmadan da paylaşılabiliyor (devam eden 3/7 şavt)', wa0.replace('\n', ' | ')[:140])
    for _ in range(7): pg.click('[data-eylem="arttir"]')
    kontrol(pg.inner_text('#sayacSayi') == '7' and pg.locator('[data-eylem="arttir"]').count() == 0 and 'Yeni' in pg.inner_text('[data-eylem="yeni"]'),
            "Sayaç: 7'de tamamlanıyor, büyük buton 'Yeni sa'ye başla' oluyor")
    g = pg.inner_text('#gecmisListe') if pg.locator('#gecmisListe').count() else ''
    kontrol('Bugün' in g and "1 sa'y" in g and '11:00' in g, "Geçmiş: tamamlanan sa'y bugünün altında saatiyle kaydediliyor", g.replace('\n', ' | ')[:120])
    pg.click('[data-eylem="yeni"]')
    kontrol(pg.inner_text('#sayacSayi') == '0' and "1 sa'y" in pg.inner_text('#gecmisListe'), 'Sayaç: "Yeni" ile sıfırdan başlıyor, geçmiş korunuyor')
    for _ in range(7): pg.click('[data-eylem="arttir"]')
    kontrol("2 sa'y" in pg.inner_text('#gecmisListe'), "Geçmiş: ikinci sa'y eklendi")
    pg.click('[data-eylem="azalt"]'); s1 = pg.inner_text('#sayacSayi')
    kontrol(s1 == '6' and "1 sa'y" in pg.inner_text('#gecmisListe'), 'Geçmiş: 7\'den geri alınca kayıt da geri alınıyor')
    pg.click('[data-eylem="sifirla"]')
    kontrol(pg.inner_text('#sayacSayi') == '0', 'Sayaç: geri al ve sıfırla çalışıyor')
    pg.click('[data-eylem="mod-tavaf"]'); pg.click('[data-eylem="arttir"]'); pg.click('[data-eylem="arttir"]'); pg.click('[data-eylem="arttir"]'); pg.click('[data-eylem="arttir"]')
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(400); pg.click('.alt-menu [data-sekme="rehber"]'); pg.wait_for_timeout(200)
    kontrol(pg.inner_text('#sayacSayi') == '7' and "1 tavaf, 1 sa'y" in pg.inner_text('#gecmisListe') and "Toplam: 1 tavaf, 1 sa'y" in pg.inner_text('#gecmisToplam'),
            'Geçmiş: tavaf da kaydediliyor, sayfa yenilenince geçmiş ve özet korunuyor')
    wa = unquote((pg.get_attribute('#gecmisPaylas', 'href') or '').split('text=', 1)[-1])
    kontrol(wa and (pg.get_attribute('#gecmisPaylas', 'href') or '').startswith('https://wa.me/?text=') and 'Umre geçmişim – Kasım 2026 Umre Kafilesi' in wa
            and "12 Kasım Perşembe: 1 tavaf (11:00), 1 sa'y (11:00)" in wa and "Toplam: 1 tavaf, 1 sa'y" in wa,
            'Geçmiş: "WhatsApp\'ta paylaş" tarihli ve saatli özet metniyle açılıyor', wa.replace('\n', ' | ')[:140])
    pg.click('[data-eylem="yeni"]'); pg.click('[data-eylem="arttir"]'); pg.click('[data-eylem="arttir"]'); pg.click('[data-eylem="arttir"]')
    pg.click('[data-eylem="mod-say"]')
    pg.click('[data-eylem="mod-tavaf"]')
    kontrol(pg.inner_text('#sayacSayi') == '3', 'Sayaç: tavaf sayısı sa\'y\'dan etkilenmiyor')
    pg.click('[data-eylem="gecmis-temizle"]'); pg.wait_for_timeout(100)
    kontrol(pg.locator('#gecmisListe').count() == 0 and 'tavaf 3/7' in pg.inner_text('#gecmisDevam') and pg.locator('#gecmisPaylas').count() == 1, 'Geçmiş: "Geçmişi temizle" çalışıyor, devam eden sayaç paylaşılabilir kalıyor')
    kontrol(not tasma(pg), 'Rehber: telefonda yatay taşma yok')
    kontrol(pg.get_attribute('.yorum-satir', 'href') == 'https://maps.app.goo.gl/kcsyZAUVKr1JB5UH9', 'Google yorumu: bağlantı girilmemişse işletmenin Google Haritalar sayfası')

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
    kontrol(pg.locator('#pusulaOkGrup path').count() == 1 and pg.get_attribute('#pusulaOkGrup path', 'fill') == '#E4B84A', 'Kıble: pusulada yalnızca sarı ok var (karıştıran arka uç yok)')
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
    MEKANLAR = [{'id': 1, 'sehir': 'Saraybosna', 'diger_adlar': ['Sarajevo', 'Bosna'], 'tur': 'gezi', 'ad': 'Sarı Tabya', 'aciklama': 'Gün batımı manzarası.', 'harita': 'https://www.google.com/maps/search/?api=1&query=Zuta%20Tabija', 'sira': 100},
                {'id': 2, 'sehir': 'Saraybosna', 'diger_adlar': ['Sarajevo', 'Bosna'], 'tur': 'yemek', 'ad': 'Ćevabdžinica Željo', 'aciklama': '<img src=x onerror=window.__xss=1>', 'harita': None, 'sira': 90},
                {'id': 3, 'sehir': 'Mostar', 'diger_adlar': [], 'tur': 'gezi', 'ad': 'Mostar Köprüsü', 'aciklama': '', 'harita': 'javascript:alert(1)', 'sira': 80}]
    c.__mekan_istek = []
    def mekan_yanit(route, req):
        c.__mekan_istek.append(req.url); route.fulfill(status=200, body=json.dumps(MEKANLAR), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'})
    c.route('**/rest/v1/sehir_rehberi**', mekan_yanit)
    c.__il = []; c.__il_ad = ('Saraybosna', 'Bosna-Hersek')
    def il_yanit(route, req):
        c.__il.append(req.url); route.fulfill(status=200, body=json.dumps({'city': c.__il_ad[0], 'countryName': c.__il_ad[1]}), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'})
    c.route('https://api.bigdatacloud.net/**', il_yanit)
    c.add_init_script("""window.__paylas = []; navigator.share = function(d){ window.__paylas.push({ text: d.text, files: (d.files || []).map(function(f){ return f.type + ':' + f.size; }) }); return Promise.resolve(); };
      navigator.canShare = function(d){ return true; };""")
    errs = []; pg = sayfa(c, errs, URL + '#TEST-KULTR')
    kart = pg.locator('section[aria-label="Sıradaki buluşma"]')
    kontrol(kart.count() == 1 and '12:30' in kart.inner_text() and pg.locator('.icerik > .zaman-cizelge .zc-satir.gecti', has_text='Kahvaltı').count() == 1,
            'Kültür turu: program yerel saate göre (Saraybosna 11:00 → sıradaki 12:30)', errs)
    pg.click('.alt-menu [data-sekme="rehber"]'); pg.wait_for_timeout(200)
    m = pg.inner_text('#ekran')
    kontrol(pg.locator('#sayacSayi').count() == 0 and 'Yolculuk Rehberi' in m and 'powerbank' in m and 'Zemzem' not in m and 'Riyali' not in m,
            'Kültür turu: tavaf sayacı ve umreye özel valiz maddeleri yok')
    pg.wait_for_timeout(300); m = pg.inner_text('#ekran')
    kontrol(c.__mekan_istek and 'yayinda=eq.true' in c.__mekan_istek[0] and 'Şehir rehberi' in m and 'Sarı Tabya' in m and 'Željo' in m and 'Mostar Köprüsü' not in m
            and m.index('Sarı Tabya') < m.index('powerbank'), 'Şehir rehberi: kültür turunda en üstte; otel şehri (Saraybosna) mekanları, başka şehir yok', errs)
    kontrol(pg.locator('.sehir-sec').count() == 0 and pg.locator('.mekan').count() == 2, 'Şehir rehberi: tek şehirde şehir seçici yok, 2 mekan')
    h1 = pg.get_attribute('.mekan[data-mekan="1"] a', 'href'); h2 = pg.get_attribute('.mekan[data-mekan="2"] a', 'href')
    kontrol(h1.endswith('Zuta%20Tabija') and h2.startswith('https://www.google.com/maps/search/?api=1&query=') and 'Saraybosna' in unquote(h2), 'Şehir rehberi: "Haritada aç" Google Haritalar bağlantısı (yoksa ad+şehirle arama)')
    kontrol(pg.evaluate('!window.__xss') and '<img' in pg.inner_text('.mekan[data-mekan="2"]'), 'Güvenlik: mekan açıklamasındaki HTML çalışmıyor')
    pg.click('.mekan[data-mekan="2"] [data-eylem="mekan-paylas"]'); pg.wait_for_timeout(300)
    kontrol(pg.is_visible('#paylasPerde') and 'Željo' in pg.inner_text('#paylasPerde') and pg.locator('#paylasPerde [data-eylem="yazi-paylas"]').count() == 0
            and pg.locator('#paylasPerde label.btn-dolu[for="paylasFoto"]').count() == 1 and pg.get_attribute('#paylasKamera', 'capture') == 'environment' and pg.locator('#paylasPerde label[for="paylasKamera"]').count() == 1
            and pg.locator('#paylasOnizleme img').count() == 0,
            'Paylaş: panel açılıyor; "Fotoğraf çek" (kamera) ve "Galeriden seç" öne çıkıyor, "Yazıyla paylaş" yok')
    from PIL import Image as _I; import io as _io
    _b = _io.BytesIO(); _I.new('RGB', (800, 600), (40, 120, 200)).save(_b, 'JPEG')
    pg.set_input_files('#paylasFoto', files=[{'name': 'f.jpg', 'mimeType': 'image/jpeg', 'buffer': _b.getvalue()}]); pg.wait_for_timeout(1200)
    kontrol(pg.locator('#paylasOnizleme img').count() == 1 and pg.evaluate("(() => { const i = document.querySelector('#paylasOnizleme img'); return i.naturalWidth === 1080 && i.naturalHeight === 1350; })()"),
            'Paylaş: seçilen fotoğraftan logolu 1080×1350 görsel hazırlanıyor', errs)
    pg.click('#paylasPerde [data-eylem="foto-gonder"]'); pg.wait_for_timeout(300)
    py = pg.evaluate('window.__paylas')
    kontrol(len(py) == 1 and len(py[-1]['files']) == 1 and py[-1]['files'][0].startswith('image/jpeg:') and '📍 Ćevabdžinica Željo, Saraybosna' in py[-1]['text'] and 'İsmail Coşar Turizm' in py[-1]['text'],
            'Paylaş: fotoğraflı görsel, mekan ve firma adıyla paylaşıma gidiyor', str(py)[:140])
    ilk = pg.get_attribute('#paylasOnizleme img', 'src')
    pg.set_input_files('#paylasKamera', files=[{'name': 'k.jpg', 'mimeType': 'image/jpeg', 'buffer': _b.getvalue()}]); pg.wait_for_timeout(1200)
    kontrol(pg.get_attribute('#paylasOnizleme img', 'src') != ilk, 'Paylaş: kamerayla çekilen fotoğraftan da görsel hazırlanıyor', errs)
    ilk = pg.get_attribute('#paylasOnizleme img', 'src')
    pg.click('#paylasPerde [data-eylem="hazir-gorsel"]'); pg.wait_for_timeout(1200)
    kontrol(pg.locator('#paylasOnizleme img').count() == 1 and pg.get_attribute('#paylasOnizleme img', 'src') != ilk and pg.evaluate("document.querySelector('#paylasOnizleme img').naturalWidth") == 1080,
            'Paylaş: alternatif olarak fotoğrafsız hazır görsel hazırlanıyor', errs)
    pg.click('#paylasPerde [data-eylem="foto-gonder"]'); pg.wait_for_timeout(300)
    py = pg.evaluate('window.__paylas')
    kontrol(len(py) == 2 and len(py[-1]['files']) == 1 and py[-1]['files'][0].startswith('image/jpeg:'), 'Paylaş: hazır görsel paylaşıma gidiyor', str(py[-1])[:120])
    pg.click('#paylasPerde [data-eylem="paylas-kapat"]'); pg.wait_for_timeout(100)
    kontrol(pg.locator('#paylasPerde').count() == 0 and not tasma(pg), 'Paylaş: panel kapanıyor, taşma yok')
    pg.click('.alt-menu [data-sekme="vakitler"]'); pg.wait_for_timeout(200)
    kontrol(pg.locator('[data-eylem="sehir-mekke"]').count() == 0 and pg.locator('#ekran [data-eylem="konum-vakit"]').count() >= 1, 'Kültür turu: Mekke/Medine yerine "Konumumu kullan" çıkıyor')
    if pg.locator('#ekran .btn-dolu[data-eylem="konum-vakit"]').count(): pg.click('#ekran .btn-dolu[data-eylem="konum-vakit"]')
    else: print('  (konum izni zaten verili: açılışta kendiliğinden alındı)')
    pg.wait_for_timeout(600)
    mk = [re.findall(r'\d\d:\d\d', x)[0] for x in pg.locator('#vakitListesi .vakit-satir').all_inner_texts()]
    kontrol(len(mk) == 6 and '06:30' <= mk[1] <= '07:10' and '11:30' <= mk[2] <= '11:55' and '16:05' <= mk[4] <= '16:40' and 'Öğle' in pg.inner_text('#siradakiVakit'),
            'Kültür turu: Saraybosna vakitleri yerel saatle makul, sıradaki Öğle', ' '.join(mk))
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(400); pg.click('.alt-menu [data-sekme="vakitler"]'); pg.wait_for_timeout(200)
    kontrol(pg.locator('#vakitListesi .vakit-satir').count() == 6, 'Kültür turu: konum hatırlanıyor, tekrar sorulmuyor')
    kontrol('Saraybosna, Bosna-Hersek' in pg.inner_text('#konumIl') and 'alındı: ' in pg.inner_text('#konumIl') and c.__il and 'latitude=43.86' in c.__il[0] and 'longitude=18.41' in c.__il[0],
            'Kültür turu: namaz ekranında konumun il/ülke adı ve alınma saati görünüyor (yalnızca yaklaşık konum soruluyor)', (pg.inner_text('#konumIl'), c.__il[:1]))
    n_il = len(c.__il)
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(600)
    kontrol(len(c.__il) == n_il, 'Kültür turu: 30 dakikadan yeni konum açılışta yeniden alınmıyor')
    # 30 dakikadan eski konum + yeni şehir (Mostar) → açılışta kendiliğinden yenilenir
    pg.evaluate("(() => { const k = JSON.parse(localStorage.getItem('kafile-konum')); k.zaman = Date.now() - 31 * 60 * 1000; localStorage.setItem('kafile-konum', JSON.stringify(k)); })()")
    c.set_geolocation({'latitude': 43.3438, 'longitude': 17.8078}); c.__il_ad = ('Mostar', 'Bosna-Hersek')
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(900); pg.click('.alt-menu [data-sekme="vakitler"]'); pg.wait_for_timeout(300)
    k = pg.evaluate("JSON.parse(localStorage.getItem('kafile-konum'))")
    kontrol(abs(k['enlem'] - 43.3438) < 0.001 and 'Mostar' in pg.inner_text('#konumIl'), 'Kültür turu: açılışta 30 dakikadan eski konum kendiliğinden yenileniyor (Mostar)', pg.inner_text('#konumIl'))
    # konum alınamazsa eski konum kullanılır
    pg.evaluate("(() => { const k = JSON.parse(localStorage.getItem('kafile-konum')); k.zaman = Date.now() - 31 * 60 * 1000; localStorage.setItem('kafile-konum', JSON.stringify(k)); })()")
    c.clear_permissions()
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(900); pg.click('.alt-menu [data-sekme="vakitler"]'); pg.wait_for_timeout(300)
    kontrol(pg.locator('#vakitListesi .vakit-satir').count() == 6 and 'Mostar' in pg.inner_text('#konumIl') and not errs, 'Kültür turu: konum alınamazsa eski konumla vakitler gösteriliyor, izin penceresi açılmıyor', errs)
    c.grant_permissions(['geolocation'])
    pg.click('.alt-menu [data-sekme="acil"]'); pg.wait_for_timeout(200)
    hrefler = pg.eval_on_selector_all('#ekran a[href^="tel:"]', 'els => els.map(e => e.getAttribute("href"))')
    kontrol('tel:112' in hrefler and 'tel:911' not in hrefler and 'tel:997' not in hrefler and 'tel:+903122922929' in hrefler and 'tel:+38733000000' in hrefler,
            'Kültür turu: acil ekranında yerel 112 ve konsolosluk var, Suudi numaraları yok', str(hrefler))
    kontrol(not tasma(pg) and not errs, 'Kültür turu: taşma ve JavaScript hatası yok', errs)
    c.close()
    # Şehir rehberi: iki şehir (Bosna yazılmış otel → Saraybosna, Mostar), şehir seçici, çevrimdışı açılış
    K2 = dict(KULTUR, oteller=[{'sehir': 'Bosna', 'ad': 'Otel A'}, {'sehir': 'Mostar', 'ad': 'Otel B'}], bitis='2026-11-12', yorum_link='https://g.page/r/TEST/review')
    c = b.new_context(viewport={'width': 360, 'height': 760}, service_workers='block', locale='tr-TR', timezone_id='Europe/Sarajevo')
    c.add_init_script("window.__SIMDI = '2026-11-12T11:00:00+01:00';")
    c.route('**/rest/v1/rpc/kafile_getir', lambda route, req: route.fulfill(status=200, body=json.dumps(K2), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'}))
    c.route(re.compile(r'^https?://(?!localhost)(?!wpkjxwbvewwgdclbsdya)'), lambda route, req: route.abort())
    c.route('**/rest/v1/sehir_rehberi**', lambda route, req: route.fulfill(status=200, body=json.dumps(MEKANLAR), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'}))
    errs = []; pg = sayfa(c, errs, URL + '#TEST-KULTR'); pg.click('.alt-menu [data-sekme="rehber"]'); pg.wait_for_timeout(400)
    kontrol(pg.get_attribute('.yorum-satir', 'href') == 'https://g.page/r/TEST/review', 'Google yorumu: Rehber ekranında grubun yorum bağlantısı')
    pg.click('.alt-menu [data-sekme="bugun"]'); pg.wait_for_timeout(200)
    kontrol(pg.locator('#yorumKart a').get_attribute('href') == 'https://g.page/r/TEST/review' and 'Google' in pg.inner_text('#yorumKart'), 'Google yorumu: dönüş günü Bugün ekranında "Google\'da yorum yap" kartı')
    pg.click('.alt-menu [data-sekme="rehber"]'); pg.wait_for_timeout(300)
    kontrol(pg.locator('.sehir-sec button').all_inner_texts() == ['Saraybosna', 'Mostar'] and 'Sarı Tabya' in pg.inner_text('#ekran'), 'Şehir rehberi: "Bosna" yazılan otel Saraybosna ile eşleşiyor; iki şehir seçilebiliyor', errs)
    pg.click('.sehir-sec button:has-text("Mostar")'); pg.wait_for_timeout(200)
    m = pg.inner_text('#ekran'); hm = pg.get_attribute('.mekan[data-mekan="3"] a', 'href') or ''
    kontrol('Mostar Köprüsü' in m and 'Sarı Tabya' not in m and hm.startswith('https://www.google.com/maps/'), 'Şehir rehberi: Mostar seçilince Mostar mekanları; "javascript:" bağlantısı yerine harita araması')
    pg.click('.alt-menu [data-sekme="vakitler"]'); pg.wait_for_timeout(300)
    kontrol(pg.locator('#ekran .btn-dolu[data-eylem="konum-vakit"]').count() == 1 and pg.locator('#vakitListesi').count() == 0, 'Kültür turu: konum izni yokken açılışta izin istenmiyor, "Konumumu kullan" butonu çıkıyor')
    pg.click('.alt-menu [data-sekme="rehber"]'); pg.wait_for_timeout(200)
    c.unroute('**/rest/v1/sehir_rehberi**'); c.route('**/rest/v1/**', lambda route, req: route.abort())
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(500); pg.click('.alt-menu [data-sekme="rehber"]'); pg.wait_for_timeout(300)
    kontrol('Sarı Tabya' in pg.inner_text('#ekran') and not tasma(pg) and not errs, 'Şehir rehberi: internet yokken de son kaydedilen mekanlar görünüyor', errs)
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
    c = push_baglam(); errs = []; pg = sayfa(c, errs, URL + '#TEST-ABCDE', karsilama=True); pg.wait_for_timeout(300)
    kontrol(pg.locator('#adimBildirim [data-eylem="bildirim-ac"]').count() == 1, 'Karşılama: "Bildirimleri aç" butonu var', errs)
    pg.click('#adimBildirim [data-eylem="bildirim-ac"]'); pg.wait_for_timeout(500)
    kontrol('Bildirimler açık' in pg.inner_text('#adimBildirim') and pg.locator('#adimBildirim .adim-no.tamam').count() == 1, 'Karşılama: bildirim açılınca adım ✓ oluyor')
    pg.evaluate("localStorage.removeItem('test-abone'); localStorage.removeItem('test-izin')"); pg.close()
    errs = []; pg = sayfa(c, errs, URL + '#TEST-ABCDE'); pg.wait_for_timeout(300)
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
    kontrol(pg.locator('#ekran a.yonetici-giris[href="/admin.html"]').count() == 1, 'Bugün ekranının altında "Rehber / yönetici girişi" bağlantısı')
    pg.click('[data-eylem="cikis"]'); pg.wait_for_timeout(300)
    kontrol(pg.is_visible('#giris'), 'Kafileden çık: kod ekranına dönüyor')
    kontrol(pg.is_visible('#giris a.yonetici-giris') and pg.get_attribute('#giris a.yonetici-giris', 'href') == '/admin.html', 'Kod ekranında "Rehber / yönetici girişi" bağlantısı admin paneline gidiyor')
    c.close()
    b.close()

print('\n=== KAFİLE UYGULAMASI TESTİ:', 'TEMİZ' if not hata else f'{hata} SORUN')
sys.exit(1 if hata else 0)
