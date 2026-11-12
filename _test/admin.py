"""Admin panelini (admin.html) uçtan uca test eder; gerçek veritabanına dokunmaz.
Oturum açılmış gibi davranan sahte bir Supabase kullanılır; yapılan ekle/güncelle/sil işlemleri kaydedilip kontrol edilir.
Kullanım: önce repo kökünde `python3 -m http.server 8765`, sonra `python3 _test/admin.py`."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 'http://localhost:8765/'
VERI = json.load(open(os.path.join(HERE, 'db.json'), encoding='utf-8'))

SAHTE = 'window.__DB=' + json.dumps(VERI, ensure_ascii=False) + r''';
window.__islem = []; window.__fn = [];
window.__DB.kullanici_rolleri = [{ user_id: 'test-uid', rol: window.__ROL || 'admin', ad: 'Test' }];
(function(){
  function Q(t){
    var tum = (window.__DB[t] = window.__DB[t] || []), satir = tum.slice(), tek = false, mod = 'select', yuk = null, filtre = [];
    var q = {
      select: function(){ return q; },
      eq: function(c, v){ filtre.push([c, v]); satir = satir.filter(function(r){ return r[c] === v; }); return q; },
      order: function(c){ satir.sort(function(a, b){ return a[c] > b[c] ? 1 : a[c] < b[c] ? -1 : 0; }); return q; },
      gte: function(c, v){ satir = satir.filter(function(r){ return r[c] >= v; }); return q; },
      limit: function(){ return q; }, single: function(){ tek = true; return q; }, maybeSingle: function(){ tek = true; return q; },
      insert: function(v){ mod = 'insert'; yuk = v; return q; },
      update: function(v){ mod = 'update'; yuk = v; return q; },
      delete: function(){ mod = 'delete'; return q; },
      then: function(ok, hata){
        if (mod === 'insert') { var liste = Array.isArray(yuk) ? yuk : [yuk]; liste.forEach(function(x){ var y = JSON.parse(JSON.stringify(x)); if (y.id == null) { window.__sayac = (window.__sayac || 1000) + 1; y.id = t === 'kafileler' ? 'uuid-' + window.__sayac : window.__sayac; } /* gerçek DB: kafileler uuid (metin), diğerleri sayı */ if (!y.olusturma) y.olusturma = new Date().toISOString(); tum.push(y); }); window.__islem.push({tablo: t, tur: 'insert', veri: yuk}); }
        if (mod === 'update') { tum.forEach(function(r){ if (filtre.every(function(f){ return r[f[0]] === f[1]; })) Object.assign(r, yuk); }); window.__islem.push({tablo: t, tur: 'update', veri: yuk, filtre: filtre}); }
        if (mod === 'delete') { window.__DB[t] = tum.filter(function(r){ return !filtre.every(function(f){ return r[f[0]] === f[1]; }); }); window.__islem.push({tablo: t, tur: 'delete', filtre: filtre}); }
        var d = mod === 'select' ? (tek ? (satir[0] || null) : satir) : null;
        return Promise.resolve({ data: d, error: null }).then(ok, hata);
      }
    };
    return q;
  }
  window.supabase = { createClient: function(){ return {
    from: Q,
    functions: { invoke: function(ad, o){ var g = o.body; window.__fn.push({ ad: ad, govde: g });
      if (g.islem === 'olustur') { var id = 'rehber-' + window.__fn.length; window.__DB.kullanici_rolleri.push({ user_id: id, rol: 'rehber', ad: g.ad, kullanici_adi: g.kullanici_adi }); return Promise.resolve({ data: { tamam: true, user_id: id }, error: null }); }
      if (g.islem === 'link') return Promise.resolve(/IYI/.test(g.url) ? { data: { lat: 21.4174, lng: 39.8295 }, error: null } : { data: null, error: { message: 'bulunamadı' } });
      if (g.islem === 'sil') window.__DB.kullanici_rolleri = window.__DB.kullanici_rolleri.filter(function(x){ return x.user_id !== g.user_id; });
      return Promise.resolve({ data: { tamam: true }, error: null }); } },
    auth: { getSession: function(){ return Promise.resolve({ data: { session: { user: { id: 'test-uid', email: 'test@test' } } } }); },
            getUser: function(){ return Promise.resolve({ data: { user: { id: 'test-uid', email: 'test@test' } } }); },
            signInWithPassword: function(){ return Promise.resolve({ error: null }); }, signOut: function(){ return Promise.resolve({}); },
            onAuthStateChange: function(){ return { data: { subscription: { unsubscribe: function(){} } } }; } },
    storage: { from: function(){ return { upload: function(){ return Promise.resolve({ error: null }); }, getPublicUrl: function(){ return { data: { publicUrl: '' } }; } }; } }
  }; } };
})();
'''

hata = 0
def kontrol(ok, ad, ayrinti=''):
    global hata
    hata += not ok
    print('✓' if ok else '✗', ad, ayrinti)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1300, 'height': 900}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:160]))
    pg.route('**cdn.jsdelivr.net/npm/@supabase/**', lambda r, q: r.fulfill(status=200, body=SAHTE, headers={'content-type': 'application/javascript'}))
    pg.route(re.compile(r'^https?://(?!localhost)'), lambda r, q: r.abort() if 'jsdelivr' not in q.url else r.fallback())
    pg.add_init_script('window.confirm = function(){ return true; };')
    pg.goto(BASE + 'admin.html', wait_until='domcontentloaded'); pg.wait_for_timeout(1000)
    kontrol(pg.is_visible('#appDiv'), 'Oturum açıkken panel açılıyor', errs)
    kontrol('Test · Yönetici' in pg.inner_text('#kullaniciBilgi'), 'Sağ üstte giriş yapan kullanıcı ve rolü görünüyor', pg.inner_text('#kullaniciBilgi'))

    # Bütün sekmeler hatasız açılıyor
    kontrol(pg.is_visible('#sayfa-ana') and not pg.is_visible('#sayfa-basvuru') and 'Grup Yönetimi' in pg.inner_text('#sayfa-ana') and 'Site Yönetimi' in pg.inner_text('#sayfa-ana'),
            'Girişte Ana Sayfa açılıyor (Başvurular değil); Grup Yönetimi ve Site Yönetimi bölümleri var', errs)
    basliklar = pg.locator('.sidebar .nav-baslik, .sidebar .nav-item').evaluate_all("l => l.map(e => e.id || e.textContent.trim())")
    kontrol(basliklar[:6] == ['btn-ana', 'Grup Yönetimi', 'btn-kafile', 'btn-musteri', 'btn-rehber', 'btn-sehir'] and basliklar[6:11] == ['Site Yönetimi', 'btn-basvuru', 'btn-turlar', 'btn-duyuru', 'btn-yorum'],
            'Menü gruplu: Grup Yönetimi (Gruplar, Müşteriler, Rehber) ve Site Yönetimi (Başvurular, Turlar, Duyurular, Yorumlar)', basliklar)
    pg.locator('#sayfa-ana button', has_text='Müşteriler').click(); pg.wait_for_timeout(300)
    kontrol(pg.is_visible('#sayfa-musteri'), 'Ana Sayfa: kutucuğa basınca ilgili sekme açılıyor')
    for sekme in ['ana', 'basvuru', 'turlar', 'ekle', 'duyuru', 'kafile', 'yorum', 'musteri', 'rehber', 'sehir']:
        errs.clear(); pg.evaluate(f"sekmeAc('{sekme}')"); pg.wait_for_timeout(400)
        kontrol(pg.is_visible(f'#sayfa-{sekme}') and not errs, f'Sekme açılıyor: {sekme}', errs)

    # Tur listesi
    pg.evaluate("sekmeAc('turlar')"); pg.wait_for_timeout(400)
    kontrol(pg.locator('#btn-ekle').count() == 0 and pg.locator('#yeniTurBtn').count() == 1, 'Tur Ekle menüden kalktı; Tur Listesi\'nde "Yeni Tur" butonu var')
    pg.click('#yeniTurBtn'); pg.wait_for_timeout(300)
    kontrol(pg.is_visible('#sayfa-ekle') and pg.is_visible('#n_baslik') and 'active' in (pg.get_attribute('#btn-turlar', 'class') or ''), 'Yeni Tur formu açılıyor, menüde Tur Listesi seçili kalıyor')
    pg.get_by_role('button', name=re.compile('Tur Listesi')).last.click(); pg.wait_for_timeout(400)
    kontrol(pg.is_visible('#sayfa-turlar'), 'Yeni Tur formundan "← Tur Listesi" ile geri dönülüyor')
    pg.click('#yeniTurBtn'); pg.wait_for_timeout(300); pg.evaluate("window.__islem = []")
    pg.fill('#n_baslik', 'Deneme Turu'); pg.get_by_role('button', name=re.compile('Tur Ekle')).click(); pg.wait_for_timeout(500)
    ek = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'insert' and i['tablo'] == 'turlar']
    kontrol(len(ek) == 1 and ek[0]['veri'].get('baslik') == 'Deneme Turu' and pg.is_visible('#sayfa-turlar') and 'Deneme Turu' in pg.inner_text('#sayfa-turlar'), 'Yeni tur eklenince Tur Listesi\'ne dönülüyor ve yeni tur listede', errs)
    pg.evaluate("window.__DB.turlar = window.__DB.turlar.filter(function(x){ return x.baslik !== 'Deneme Turu'; })"); pg.evaluate("sekmeAc('turlar')"); pg.wait_for_timeout(300)
    n_tur = len(VERI['turlar'])
    kontrol(pg.locator('#sayfa-turlar .tur-item').count() == n_tur, 'Tur listesi tüm turları gösteriyor', f"({pg.locator('#sayfa-turlar .tur-item').count()}/{n_tur})")

    # Düzenle -> Kaydet mevcut alanları koruyor
    hedef = VERI['turlar'][1]
    pg.evaluate("window.__islem = []")
    pg.evaluate(f"turDuzenle('{hedef['id']}')"); pg.wait_for_timeout(400)
    pg.fill('#e_sure', '13 GECE 14 GÜN (test)'); pg.evaluate(f"turKaydet('{hedef['id']}')"); pg.wait_for_timeout(400)
    isl = pg.evaluate('window.__islem')
    g = [i for i in isl if i['tur'] == 'update']
    kontrol(len(g) == 1 and g[0]['veri']['sure'] == '13 GECE 14 GÜN (test)' and g[0]['veri']['baslik'] == hedef['baslik'] and g[0]['veri']['otel'] == hedef['otel'],
            'Düzenle → Kaydet doğru turu günceller, diğer alanları korur', errs)

    # Kopyala (yeni özellik; varsa test edilir)
    if pg.evaluate("typeof turKopyala") == 'function':
        pg.evaluate("sekmeAc('turlar')"); pg.wait_for_timeout(400)
        kaynak = next(t for t in VERI['turlar'] if t['program'])
        pg.evaluate("window.__islem = []"); errs.clear()
        pg.locator('#sayfa-turlar .tur-item', has_text=kaynak['id']).get_by_role('button', name=re.compile('Kopyala')).click(); pg.wait_for_timeout(600)
        isl = pg.evaluate('window.__islem'); ek = [i for i in isl if i['tur'] == 'insert']
        kopya = ek[0]['veri'] if ek else {}
        ayni = all(kopya.get(k) == kaynak.get(k) for k in ['kategori', 'otel', 'program', 'aciklama', 'fiyat_2', 'fiyat_3', 'fiyat_4', 'dahil', 'dahil_degil', 'para_birimi', 'sure', 'gorsel'])
        kontrol(len(ek) == 1 and kopya.get('id') != kaynak['id'] and kopya.get('aktif') is False and kopya.get('baslik', '').startswith('(KOPYA)') and ayni,
                'Kopyala: yeni kimlikle, pasif, "(KOPYA)" başlıklı ve tüm bilgileri taşıyan kayıt oluşturur', errs)
        kontrol(not [i for i in isl if i['tur'] in ('update', 'delete')], 'Kopyala: asıl tura dokunmaz')
        kontrol(pg.is_visible('#e_baslik') and pg.input_value('#e_baslik').startswith('(KOPYA)'), 'Kopyala: kopyanın düzenleme ekranı açılır')
        pg.fill('#e_baslik', 'Yeni Ay Umresi'); pg.fill('#e_tarih', '2027-03-01'); pg.select_option('#e_aktif', 'true')
        pg.evaluate("window.__islem = []"); pg.evaluate(f"turKaydet('{kopya.get('id')}')"); pg.wait_for_timeout(400)
        g = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'update']
        kontrol(len(g) == 1 and g[0]['filtre'] == [['id', kopya.get('id')]] and g[0]['veri']['baslik'] == 'Yeni Ay Umresi' and g[0]['veri']['aktif'] is True,
                'Kopyalanan tur düzenlenip kaydedilebiliyor (asıl tur değil, kopya güncelleniyor)', errs)
    else:
        print('· Kopyala özelliği yok, atlandı')

    # ── Kafileler (yolcu uygulaması) ──
    pg.evaluate("sekmeAc('kafile')"); pg.wait_for_timeout(400)
    pg.evaluate("window.__DB.kullanici_rolleri.push({ user_id: 'r-1', rol: 'rehber', ad: 'Rehber Bir', kullanici_adi: 'rehber1' })")
    pg.evaluate("window.__islem = []"); errs.clear()
    pg.get_by_role('button', name=re.compile('Yeni Grup')).click(); pg.wait_for_timeout(300)
    kontrol(pg.locator('.k_rehber').count() == 1 and not pg.is_checked('.k_rehber'), 'Grup formu: rehber hesapları işaretlenebilir listede')
    pg.check('.k_rehber')
    kontrol(re.fullmatch(r'GRUP-[A-Z2-9]{5}', pg.input_value('#k_kod')) is not None, 'Grup: yeni formda otomatik kod üretiliyor (GRUP-…)', pg.input_value('#k_kod'))
    pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(300)
    kontrol(not [i for i in pg.evaluate('window.__islem') if i['tur'] == 'insert'], 'Kafile: adı boşken kaydetmiyor')
    ek0 = pg.input_value('#k_kod')[-5:]; pg.fill('#k_ad', 'Kasım 2026 Umre Kafilesi')
    kontrol(pg.input_value('#k_kod') == 'KASIM-' + ek0, 'Grup: ad yazılınca kod adın ilk kelimesiyle güncelleniyor', pg.input_value('#k_kod'))
    pg.get_by_role('button', name='Yeni kod').click()
    kod = pg.input_value('#k_kod')
    pg.fill('#k_baslangic', '2026-11-10'); pg.fill('#k_bitis', '2026-11-23')
    pg.fill('#k_rehber_ad', "Ali O'Hoca"); pg.fill('#k_rehber_tel', '0533 000 00 00')
    pg.locator('.o_ad').first.fill('Test Otel Mekke'); pg.locator('.o_giris').first.fill('2026-11-10'); pg.locator('.o_cikis').first.fill('2026-11-15')
    pg.locator('.o_konum').first.fill('https://maps.app.goo.gl/IYI123')
    kontrol(pg.inner_text('.otel-blok .o_gece') == '5 gece', 'Grup: otel giriş-çıkışından gece sayısı gösteriliyor')
    pg.get_by_role('button', name=re.compile('Otel ekle')).click()
    kontrol(pg.locator('#k_oteller .otel-blok').count() == 3, 'Grup: "Otel ekle" ile üçüncü otel eklenebiliyor (kültür turları için)')
    pg.fill('#k_inis_sehri', 'Cidde'); pg.fill('#k_donus_sehri', 'Medine'); pg.fill('#k_yorum_link', 'https://g.page/r/ABC/review')
    pg.select_option('#k_tur_turu', 'kultur'); pg.fill('#k_acil_tel', '112')
    satir = pg.locator('#k_program .prog-satir').first
    satir.locator('.p_tarih').fill('2026-11-11'); satir.locator('.p_saat').fill('14:30'); satir.locator('.p_baslik').fill('Mekke ziyaretleri'); satir.locator('.p_yer').fill('Otel lobisi')
    pg.get_by_role('button', name=re.compile('Satır ekle')).click()
    satir = pg.locator('#k_program .prog-satir').nth(1)
    satir.locator('.p_saat').fill('09:00'); satir.locator('.p_baslik').fill('Kahvaltı')
    pg.get_by_role('button', name=re.compile('Satır ekle')).click()  # boş satır kaydedilmemeli
    pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(500)
    ek = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'insert' and i['tablo'] == 'kafileler']
    v = ek[0]['veri'] if ek else {}
    kontrol(len(ek) == 1 and v.get('kod') == kod and v.get('aktif') is True and len(v.get('oteller', [])) == 1
            and [p['baslik'] for p in v.get('program', [])] == ['Kahvaltı', 'Mekke ziyaretleri'] and v.get('rehber_ad') == "Ali O'Hoca" and v.get('tur_turu') == 'kultur' and v.get('acil_tel') == '112'
            and v.get('inis_sehri') == 'Cidde' and v.get('yorum_link') == 'https://g.page/r/ABC/review' and v.get('donus_sehri') == 'Medine' and v['oteller'][0].get('giris') == '2026-11-10' and v['oteller'][0].get('cikis') == '2026-11-15' and (v['oteller'][0].get('lat'), v['oteller'][0].get('lng')) == (21.4174, 39.8295),
            'Kafile: yeni kafile kaydediliyor (boş satır/otel atlanıyor, program tarih+saate göre sıralı)', errs)
    rk = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'kafile_rehberleri' and i['tur'] == 'insert']
    kontrol(len(rk) == 1 and rk[0]['veri'] == [{'kafile_id': v.get('id'), 'user_id': 'r-1'}] and v.get('id') and 'Rehber: Rehber Bir' in pg.inner_text('.kafile-item .grup-rehber'),
            'Grup formu: işaretlenen rehber yeni gruba atanıyor ve listede adı görünüyor', str(rk)[:120])
    kontrol(pg.locator('.kafile-item').count() == 1 and kod in pg.inner_text('#sayfa-kafile') and pg.inner_text('.kafile-item .abone-sayisi') == '0', 'Kafile: listede görünüyor (bildirim açık telefon sayısıyla)')
    href = pg.locator('.kafile-item a', has_text='Paylaş').get_attribute('href') or ''
    kontrol('kafile%2F%23' + kod in href, 'Kafile: Paylaş bağlantısı kodlu uygulama adresini içeriyor')
    pg.evaluate("window.__islem = []")
    pg.locator('.kafile-item').get_by_role('button', name='Düzenle').click(); pg.wait_for_timeout(300)
    kontrol(pg.locator('#k_program .prog-satir').count() == 2 and pg.input_value('#k_rehber_ad') == "Ali O'Hoca" and pg.input_value('#k_tur_turu') == 'kultur' and pg.input_value('#k_acil_tel') == '112', 'Kafile: düzenleme formu kayıtlı bilgilerle açılıyor')
    kontrol(pg.is_checked('.k_rehber'), 'Grup formu: düzenlerken atanmış rehber işaretli geliyor')
    kontrol('haritada işaretli' in pg.inner_text('.otel-blok .o_konum_durum') and "Harem'e kuş uçuşu ~650 m" in pg.inner_text('.otel-blok .o_konum_durum'),
            'Otel konumu: Google bağlantısından enlem/boylam bulunup kaydediliyor; formda Harem uzaklığıyla gösteriliyor', pg.inner_text('.otel-blok .o_konum_durum'))
    pg.uncheck('.k_rehber')
    pg.evaluate("window.__fn = []")
    pg.fill('#k_ad', 'Kasım 2026 Umre Kafilesi (güncel)'); pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(400)
    gu = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'kafileler' and i['tur'] == 'update']
    kontrol(gu and gu[-1]['veri']['oteller'][0].get('lat') == 21.4174 and not [f for f in pg.evaluate('window.__fn') if f['govde'].get('islem') == 'link'],
            'Otel konumu: bağlantı değişmediyse koordinat korunuyor, tekrar sorgulanmıyor')
    rs = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'kafile_rehberleri' and i['tur'] == 'delete']
    kontrol(len(rs) == 1 and ['user_id', 'r-1'] in rs[0]['filtre'] and 'rehber hesabı atanmadı' in pg.inner_text('.kafile-item .grup-rehber'), 'Grup formu: işaret kaldırılınca rehber gruptan çıkarılıyor')
    # konum bağlantısından yer bulunamazsa uyarı; elle koordinat yazılabiliyor
    pg.locator('.kafile-item').get_by_role('button', name='Düzenle').click(); pg.wait_for_timeout(300)
    pg.locator('.o_konum').first.fill('https://maps.app.goo.gl/KOTU'); pg.evaluate("window.__islem = []")
    pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(400)
    gu = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'kafileler' and i['tur'] == 'update']
    kontrol(gu and 'lat' not in gu[-1]['veri']['oteller'][0] and 'yer bulunamadı' in pg.inner_text('body'), 'Otel konumu: bağlantıdan yer bulunamazsa grup yine kaydediliyor, uyarı çıkıyor')
    pg.locator('.kafile-item').get_by_role('button', name='Düzenle').click(); pg.wait_for_timeout(300)
    pg.locator('.o_konum').first.fill('21.4189, 39.8262'); pg.evaluate("window.__islem = []; window.__fn = []")
    pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(400)
    gu = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'kafileler' and i['tur'] == 'update']
    kontrol(gu and (gu[-1]['veri']['oteller'][0].get('lat'), gu[-1]['veri']['oteller'][0].get('lng')) == (21.4189, 39.8262) and not pg.evaluate('window.__fn'), 'Otel konumu: koordinat elle yazılabiliyor')
    pg.evaluate("window.__DB.kullanici_rolleri = window.__DB.kullanici_rolleri.filter(function(x){ return x.user_id !== 'r-1'; })")
    g = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'update']
    kontrol(len(g) == 1 and g[0]['tablo'] == 'kafileler' and g[0]['veri']['ad'].endswith('(güncel)') and len(g[0]['veri']['program']) == 2, 'Kafile: düzenle → kaydet doğru kafileyi güncelliyor', errs)
    pg.evaluate("window.__islem = []")
    pg.locator('.kafile-item').get_by_role('button', name=re.compile('Duyurular')).click(); pg.wait_for_timeout(400)
    pg.get_by_role('button', name=re.compile('Yayınla')).click(); pg.wait_for_timeout(300)
    kontrol(not pg.evaluate('window.__islem'), 'Kafile duyurusu: metin boşken yayınlanmıyor')
    pg.fill('#kd_baslik', 'Medine\'ye hareket'); pg.fill('#kd_metin', 'Yarın 08:00\'de hareket.'); pg.check('#kd_onemli')
    pg.get_by_role('button', name=re.compile('Yayınla')).click(); pg.wait_for_timeout(500)
    ek = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'insert' and i['tablo'] == 'kafile_duyurular']
    kontrol(len(ek) == 1 and ek[0]['veri']['onemli'] is True and ek[0]['veri']['bildirim'] is True and ek[0]['veri']['kafile_id'] is not None and pg.locator('.kafile-duyuru').count() == 1
            and 'gönderiliyor' in pg.inner_text('.kafile-duyuru .bildirim-sonuc'),
            'Kafile duyurusu: yayınlanıyor ve listede görünüyor', errs)
    pg.evaluate("window.__islem = []")
    pg.fill('#kd_metin', 'Sadece bilgi, bildirimsiz.'); pg.uncheck('#kd_bildirim'); pg.get_by_role('button', name=re.compile('Yayınla')).click(); pg.wait_for_timeout(500)
    ek = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'insert' and i['tablo'] == 'kafile_duyurular']
    kontrol(len(ek) == 1 and ek[0]['veri']['bildirim'] is False and 'gönderilmedi' in pg.inner_text('#sayfa-kafile'), 'Kafile duyurusu: "bildirim gönder" kapatılabiliyor')
    pg.evaluate("window.__islem = []")
    pg.locator('.kafile-duyuru', has_text='bildirimsiz').get_by_role('button', name='Sil').click(); pg.wait_for_timeout(400)
    pg.evaluate("window.__islem = []")
    pg.locator('.kafile-duyuru').get_by_role('button', name='Sil').click(); pg.wait_for_timeout(400)
    s_ = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'delete']
    kontrol(len(s_) == 1 and s_[0]['tablo'] == 'kafile_duyurular' and pg.locator('.kafile-duyuru').count() == 0, 'Kafile duyurusu: siliniyor', errs)
    pg.get_by_role('button', name=re.compile('Gruplar')).first.click(); pg.wait_for_timeout(400)

    # ── Katılımcılar (oda listesi) ──
    pg.evaluate("window.__islem = []"); errs.clear()
    pg.locator('.kafile-item').get_by_role('button', name=re.compile('Katılımcılar')).click(); pg.wait_for_timeout(400)
    kontrol('Oda no – Mekke (Test Otel Mekke)'.upper() in pg.inner_text('#kt_kart').upper(), 'Katılımcılar: oda başlığında otel adı da yazıyor')
    kontrol(pg.locator('#kt_kart .kt_oda').count() == 1 and pg.get_attribute('#kt_kart .kt_oda', 'data-otel') == 'Mekke' and 'Henüz kimse' in pg.inner_text('#sayfa-kafile'),
            'Katılımcılar: sayfa açılıyor, kafilenin oteline göre oda alanı (Mekke) var', errs)
    pg.locator('#kt_kart').get_by_role('button', name=re.compile('Ekle')).click(); pg.wait_for_timeout(200)
    kontrol(not pg.evaluate('window.__islem'), 'Katılımcılar: ad boşken eklemiyor')
    pg.fill('#kt_ad', ' Ayşe   Kaya '); pg.fill('#kt_tel', '0533 444 55 66'); pg.fill('#kt_dogum', '1950-05-20'); pg.fill('#kt_kart .kt_oda', '512'); pg.select_option('#kt_kart .kt_tip', '3 kişilik'); kontrol(pg.input_value('#kt_kart .kt_giris') == '2026-11-10' and pg.input_value('#kt_kart .kt_cikis') == '2026-11-15' and pg.inner_text('#kt_kart .kt_gece') == '5 gece', 'Katılımcılar: giriş-çıkış grubun otel tarihleriyle dolu geliyor (5 gece)')
    pg.fill('#kt_kart .kt_giris', '2026-11-11')
    kontrol(pg.inner_text('#kt_kart .kt_gece') == '4 gece', 'Katılımcılar: kişiye özel giriş tarihiyle gece sayısı güncelleniyor (4 gece)')
    pg.check('#kt_izin')
    pg.locator('#kt_kart').get_by_role('button', name=re.compile('Ekle')).click(); pg.wait_for_timeout(500)
    isl = pg.evaluate('window.__islem'); mi = [i for i in isl if i['tablo'] == 'musteriler' and i['tur'] == 'insert']; ki = [i for i in isl if i['tablo'] == 'kafile_katilimcilar' and i['tur'] == 'insert']
    mv = mi[0]['veri'] if mi else {}
    kontrol(len(mi) == 1 and mv.get('ad') == 'Ayşe Kaya' and mv.get('dogum_tarihi') == '1950-05-20' and mv.get('ileti_izni') is True and len(ki) == 1 and ki[0]['veri']['odalar'] == {'Mekke': {'no': '512', 'tip': '3 kişilik', 'giris': '2026-11-11'}}
            and ki[0]['veri']['musteri_id'] == mv.get('id') and pg.locator('.katilimci-satir').count() == 1, 'Katılımcılar: kişi elle ekleniyor (müşteri + oda no, tipi, giriş-çıkış; izin tarihiyle)', errs)
    pg.evaluate("window.__islem = []")
    pg.locator('summary', has_text='Excel').click()
    pg.fill('#kt_yapistir', "Ad Soyad\tTelefon\tDoğum tarihi\tOda\tOda tipi\nMehmet Kaya\t0532 111 22 33\t12.03.1955\t512\t3\nAyşe Kaya\t0533 444 55 66\t\t512\nHasan <b>Ç</b>\t\t31.02.1950\t514\t2 kişilik\n\n")
    pg.get_by_role('button', name=re.compile('Önizle')).click(); pg.wait_for_timeout(200)
    o = pg.inner_text('#kt_onizleme')
    kontrol(pg.locator('.onizleme-tablo tbody tr').count() == 3 and 'Zaten listede' in o and 'tarihi okunamadı' in o and '12.03.1955' in o and '2 kişiyi ekle' in o,
            'Excel yapıştırma: başlık atlanıyor, tarih okunuyor, listede olan ve hatalı tarih işaretleniyor', o.replace('\n', ' | ')[:160])
    pg.get_by_role('button', name=re.compile('kişiyi ekle')).click(); pg.wait_for_timeout(500)
    isl = pg.evaluate('window.__islem'); mi = [i for i in isl if i['tablo'] == 'musteriler' and i['tur'] == 'insert']; ki = [i for i in isl if i['tablo'] == 'kafile_katilimcilar' and i['tur'] == 'insert']
    kontrol(len(mi) == 1 and len(mi[0]['veri']) == 2 and {m['ad'] for m in mi[0]['veri']} == {'Mehmet Kaya', 'Hasan <b>Ç</b>'} and len(ki) == 1 and len(ki[0]['veri']) == 2
            and next(m for m in mi[0]['veri'] if m['ad'] == 'Mehmet Kaya')['dogum_tarihi'] == '1955-03-12' and pg.locator('.katilimci-satir').count() == 3,
            'Excel yapıştırma: 2 yeni kişi tek seferde ekleniyor', errs)
    kontrol(pg.locator('.katilimci-tablo b b').count() == 0 and '<b>Ç</b>' in pg.inner_text('.katilimci-tablo'), 'Güvenlik: isimdeki HTML düz yazı gösteriliyor')
    pg.click('#ktKapatBtn'); pg.wait_for_timeout(200)
    kontrol(pg.locator('#kt_kart').count() == 0 and pg.locator('#kisiEkleBtn').count() == 1, 'Katılımcılar: "Kapat" ile kişi ekleme alanları gizleniyor, yerine "Kişi ekle" butonu')
    pg.evaluate("renderKafileler()"); pg.wait_for_timeout(300)
    pg.locator('.kafile-item').get_by_role('button', name=re.compile('Katılımcılar')).click(); pg.wait_for_timeout(400)
    kontrol(pg.locator('#kt_kart').count() == 0 and pg.locator('.katilimci-satir').count() == 3, 'Katılımcılar: liste doluyken sayfa ekleme alanları kapalı açılıyor')
    pg.click('#kisiEkleBtn'); pg.wait_for_timeout(200)
    kontrol(pg.is_visible('#kt_ad') and pg.locator('#kisiEkleBtn').count() == 0, 'Katılımcılar: "Kişi ekle" ile alanlar açılıyor')
    kontrol(pg.get_by_role('button', name=re.compile('Oda listesini kopyala')).count() == 0, 'Katılımcılar: ayrı "kopyala" butonu yok, tek "Listeyi paylaş" var')
    pg.evaluate("navigator.share = undefined")
    pg.get_by_role('button', name=re.compile('Listeyi paylaş')).click(); pg.wait_for_timeout(200)
    t = pg.evaluate('window.__sonKopya') or ''
    kontrol( '🏨 *Mekke – Test Otel Mekke* (10.11–15.11, 5 gece)' in t and 'Oda 512 (3 kişilik)\n   • Ayşe Kaya [11.11–15.11, 4 gece]\n   • Mehmet Kaya' in t and 'Oda 514 (2 kişilik)\n   • Hasan <b>Ç</b>' in t, 'Oda listesi: odaya göre gruplu, her isim ayrı satırda', t.replace('\n', ' | ')[:160])
    pg.evaluate("window.__islem = []")
    pg.locator('.katilimci-satir', has_text='Mehmet').get_by_role('button', name='Düzenle').click(); pg.wait_for_timeout(200)
    kontrol(pg.input_value('#kt_ad') == 'Mehmet Kaya' and pg.input_value('#kt_kart .kt_oda') == '512', 'Katılımcılar: düzenleme formu kayıtlı bilgilerle açılıyor')
    pg.fill('#kt_kart .kt_oda', '516'); pg.locator('#kt_kart').get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(500)
    g = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'update' and i['tablo'] == 'kafile_katilimcilar']
    kontrol(len(g) == 1 and g[0]['veri'] == {'odalar': {'Mekke': {'no': '516', 'tip': '3 kişilik'}}} and '516' in pg.inner_text('.katilimci-tablo'), 'Katılımcılar: oda numarası değiştiriliyor', errs)
    # Oda doluluğu: 3 kişilik 512'de 2 kişi var; 3 kişilik odaya 4. kişi → uyarı ve onay
    kontrol(pg.locator('.oda-uyarilari').count() == 0, 'Oda doluluğu: kapasite aşılmamışken uyarı yok')
    pg.evaluate("window.__islem = []; window.confirm = function(m){ window.__onay = m; return false; }")
    pg.fill('#kt_ad', 'Ali Veli'); pg.fill('#kt_kart .kt_oda', '512'); pg.select_option('#kt_kart .kt_tip', '3 kişilik')
    pg.locator('#kt_kart').get_by_role('button', name=re.compile('Ekle')).click(); pg.wait_for_timeout(300)
    pg.fill('#kt_ad', 'Bora Ak'); pg.fill('#kt_kart .kt_oda', '512'); pg.select_option('#kt_kart .kt_tip', '3 kişilik')
    pg.locator('#kt_kart').get_by_role('button', name=re.compile('Ekle')).click(); pg.wait_for_timeout(300)
    kontrol(pg.evaluate('window.__onay') is None and pg.locator('.katilimci-satir').count() == 5, 'Oda doluluğu: 3 kişilik odaya 3. kişi uyarısız ekleniyor')
    pg.fill('#kt_ad', 'Zehra Can'); pg.fill('#kt_kart .kt_oda', '512'); pg.select_option('#kt_kart .kt_tip', '3 kişilik')
    pg.evaluate("window.__islem = []; window.__onay = null")
    pg.locator('#kt_kart').get_by_role('button', name=re.compile('Ekle')).click(); pg.wait_for_timeout(300)
    onay = pg.evaluate('window.__onay') or ''
    kontrol('Oda 512' in onay and '4 kişi' in onay and not [i for i in pg.evaluate('window.__islem') if i['tur'] == 'insert'], 'Oda doluluğu: 3 kişilik odaya 4. kişi eklenirken uyarı çıkıyor, "Hayır" denirse eklenmiyor', onay[:120])
    pg.evaluate("window.confirm = function(){ return true; }")
    pg.locator('#kt_kart').get_by_role('button', name=re.compile('Ekle')).click(); pg.wait_for_timeout(500)
    kontrol(len([i for i in pg.evaluate('window.__islem') if i['tablo'] == 'kafile_katilimcilar' and i['tur'] == 'insert']) == 1 and '4 kişi' in pg.inner_text('.oda-uyarilari') and pg.locator('td.oda-dolu').count() == 4,
            'Oda doluluğu: onaylanırsa ekleniyor; listede uyarı kutusu ve dolu oda kırmızı', errs)
    pg.locator('summary', has_text='Excel').click()
    pg.fill('#kt_yapistir', "Can Er\t\t\t514\t2"); pg.get_by_role('button', name=re.compile('Önizle')).click(); pg.wait_for_timeout(200)
    kontrol('Oda 514 dolu' not in pg.inner_text('#kt_onizleme'), 'Oda doluluğu: Excel önizlemesinde boş yer varsa uyarı yok')
    pg.fill('#kt_yapistir', "Can Er\t\t\t514\t2\nNur Er\t\t\t514\t2"); pg.get_by_role('button', name=re.compile('Önizle')).click(); pg.wait_for_timeout(200)
    kontrol(pg.locator('#kt_onizleme .oda-uyari').count() == 2 and 'Oda 514 dolu: 3 kişi' in pg.inner_text('#kt_onizleme'), 'Oda doluluğu: Excel önizlemesinde 2 kişilik odaya 3. kişi uyarısı')
    pg.fill('#kt_yapistir', ''); pg.get_by_role('button', name=re.compile('Önizle')).click(); pg.wait_for_timeout(100)
    for ad in ['Zehra Can', 'Ali Veli', 'Bora Ak']:
        pg.locator('.katilimci-satir', has_text=ad).get_by_role('button', name='Çıkar').click(); pg.wait_for_timeout(400)
    pg.evaluate("window.__islem = []")
    pg.locator('.katilimci-satir', has_text='Hasan').get_by_role('button', name='Çıkar').click(); pg.wait_for_timeout(500)
    s_ = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'delete']
    kontrol(len(s_) == 1 and s_[0]['tablo'] == 'kafile_katilimcilar' and pg.locator('.katilimci-satir').count() == 2, 'Katılımcılar: kafileden çıkarılıyor (müşteri kaydı kalıyor)', errs)
    pg.evaluate("sekmeAc('kafile')"); pg.wait_for_timeout(400)
    kontrol(pg.inner_text('.kafile-item .katilimci-sayisi') == '2', 'Kafile listesinde katılımcı sayısı görünüyor')

    # ── Müşteriler ──
    pg.evaluate("sekmeAc('musteri')"); pg.wait_for_timeout(400); errs.clear()
    kontrol(pg.locator('.musteri-satir').count() == 6 and 'Kasım 2026' in pg.inner_text('.musteri-satir:has-text("Ayşe")'), 'Müşteriler: kafileden çıkarılan dahil herkes, katıldığı turla listede', errs)
    pg.fill('#mu_ara', 'mehm'); pg.wait_for_timeout(200)
    kontrol(pg.locator('.musteri-satir').count() == 1, 'Müşteriler: isimle arama')
    pg.fill('#mu_ara', '4445566'); pg.wait_for_timeout(200)
    kontrol(pg.locator('.musteri-satir').count() == 1 and 'Ayşe' in pg.inner_text('.musteri-tablo'), 'Müşteriler: telefonla arama')
    pg.fill('#mu_ara', ''); pg.select_option('#mu_sira', 'dogum'); pg.wait_for_timeout(200)
    kontrol(pg.locator('.musteri-satir').count() == 6 and not errs, 'Müşteriler: yaklaşan doğum gününe göre sıralama', errs)
    pg.evaluate("window.__islem = []")
    pg.locator('.musteri-satir', has_text='Mehmet').get_by_role('button', name='Düzenle').click(); pg.wait_for_timeout(200)
    pg.check('#mu_izin'); pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(400)
    g = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'update' and i['tablo'] == 'musteriler']
    kontrol(len(g) == 1 and g[0]['veri']['ileti_izni'] is True and g[0]['veri']['ileti_izni_tarih'], 'Müşteriler: izin işaretlenince tarihiyle kaydediliyor', errs)
    pg.evaluate("window.__islem = []")
    pg.locator('.musteri-satir', has_text='Hasan').get_by_role('button', name='Düzenle').click(); pg.wait_for_timeout(200)
    pg.get_by_role('button', name=re.compile('tamamen sil')).click(); pg.wait_for_timeout(400)
    s_ = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'delete']
    kontrol(len(s_) == 1 and s_[0]['tablo'] == 'musteriler' and pg.locator('.musteri-satir').count() == 5, 'Müşteriler: tamamen silinebiliyor', errs)

    # ── Rehber hesapları (admin) ──
    pg.evaluate("sekmeAc('rehber')"); pg.wait_for_timeout(400); errs.clear(); pg.evaluate("window.__fn = []; window.__islem = []")
    pg.fill('#rh_ad', 'Ali Yılmaz'); pg.fill('#rh_ka', 'Ali Yılmaz'); pg.fill('#rh_sifre', 'gizli1234')
    pg.get_by_role('button', name=re.compile('Hesap aç')).click(); pg.wait_for_timeout(300)
    kontrol(not pg.evaluate('window.__fn'), 'Rehber hesabı: Türkçe karakterli/boşluklu kullanıcı adıyla açılmıyor')
    pg.fill('#rh_ka', 'Ali.Yilmaz'); pg.fill('#rh_sifre', 'kisa'); pg.get_by_role('button', name=re.compile('Hesap aç')).click(); pg.wait_for_timeout(300)
    kontrol(not pg.evaluate('window.__fn'), 'Rehber hesabı: kısa şifreyle açılmıyor')
    pg.fill('#rh_sifre', 'gizli1234'); pg.get_by_role('button', name=re.compile('Hesap aç')).click(); pg.wait_for_timeout(500)
    fn = pg.evaluate('window.__fn')
    kontrol(len(fn) == 1 and fn[0]['ad'] == 'rehber-hesap' and fn[0]['govde'] == {'islem': 'olustur', 'ad': 'Ali Yılmaz', 'kullanici_adi': 'ali.yilmaz', 'sifre': 'gizli1234'}
            and pg.locator('.rehber-item').count() == 1 and 'ali.yilmaz' in pg.inner_text('.rehber-item'), 'Rehber hesabı: açılıyor (kullanıcı adı küçük harfe çevriliyor) ve listede', errs)
    gm = pg.inner_text('.rehber-giris-kutu') if pg.locator('.rehber-giris-kutu').count() else ''
    wa = pg.get_attribute('.rehber-giris-wa', 'href') or ''
    kontrol('ismailcosarturizm.com.tr/admin.html' in gm and 'ali.yilmaz' in gm and 'gizli1234' in gm and wa.startswith('https://wa.me/?text=') and 'gizli1234' in wa,
            'Rehber hesabı: açılınca giriş adresi, kullanıcı adı ve şifre "WhatsApp ile gönder" kutusunda', gm[:120])
    pg.locator('.rehber-giris-kutu').get_by_role('button', name=re.compile('Kopyala')).click(); pg.wait_for_timeout(200)
    kontrol('Kullanıcı adı: ali.yilmaz' in (pg.evaluate('window.__sonKopya') or ''), 'Rehber hesabı: giriş bilgisi kopyalanabiliyor')
    wb = pg.get_attribute('.rehber-item .rehber-bilgi-wa', 'href') or ''
    kontrol('admin.html' in wb and 'ali.yilmaz' in wb and 'gizli1234' not in wb, 'Rehber hesabı: listede "Giriş adresini gönder" (şifresiz)')
    pg.locator('.rehber-giris-kutu').get_by_role('button', name='Kapat').click(); pg.wait_for_timeout(300)
    kontrol(pg.locator('.rehber-giris-kutu').count() == 0, 'Rehber hesabı: bilgi kutusu kapatılınca şifre ekrandan kalkıyor')
    kontrol(pg.locator('#rh_kart').count() == 0 and pg.locator('#yeniRehberBtn').count() == 1, 'Rehber hesabı: rehber varken "Yeni rehber hesabı" alanları kapalı, "Yeni rehber" butonu var')
    pg.click('#yeniRehberBtn'); pg.wait_for_timeout(300)
    kontrol(pg.is_visible('#rh_ad'), 'Rehber hesabı: "Yeni rehber" ile alanlar açılıyor')
    pg.locator('#rh_kart').get_by_role('button', name='Vazgeç').click(); pg.wait_for_timeout(300)
    kontrol(pg.locator('#rh_kart').count() == 0, 'Rehber hesabı: "Vazgeç" ile alanlar kapanıyor')
    rid = pg.get_attribute('.rehber-item', 'data-user')
    pg.locator('.rehber-item .rh_kafile').first.check(); pg.wait_for_timeout(300)
    ek = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'kafile_rehberleri' and i['tur'] == 'insert']
    kontrol(len(ek) == 1 and ek[0]['veri']['user_id'] == rid and ek[0]['veri']['kafile_id'], 'Rehber hesabı: kafile işaretlenince rehbere atanıyor')
    pg.evaluate("window.__islem = []"); pg.locator('.rehber-item .rh_kafile').first.uncheck(); pg.wait_for_timeout(300)
    sl = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'kafile_rehberleri' and i['tur'] == 'delete']
    kontrol(len(sl) == 1 and ['user_id', rid] in sl[0]['filtre'] and len(sl[0]['filtre']) == 2, 'Rehber hesabı: işaret kaldırılınca yalnızca o atama siliniyor')
    pg.evaluate("window.__fn = []"); pg.fill('.rehber-item .rh_yeni_sifre', 'yenisifre99'); pg.get_by_role('button', name='Şifreyi değiştir').click(); pg.wait_for_timeout(300)
    fn = pg.evaluate('window.__fn')
    kontrol(len(fn) == 1 and fn[0]['govde'] == {'islem': 'sifre', 'user_id': rid, 'sifre': 'yenisifre99'} and pg.input_value('.rehber-item .rh_yeni_sifre') == '' and 'yenisifre99' in pg.inner_text('.rehber-giris-kutu'), 'Rehber hesabı: şifre değiştiriliyor, yeni şifre gönderilmek üzere gösteriliyor')
    pg.evaluate("window.__fn = []"); pg.get_by_role('button', name='Hesabı sil').click(); pg.wait_for_timeout(400)
    fn = pg.evaluate('window.__fn')
    kontrol(len(fn) == 1 and fn[0]['govde'] == {'islem': 'sil', 'user_id': rid} and pg.locator('.rehber-item').count() == 0 and not errs, 'Rehber hesabı: siliniyor', errs)

    # ── Şehir rehberi ──
    pg.evaluate("""window.__DB.sehir_rehberi = [
      { id: 501, sehir: 'Saraybosna', diger_adlar: ['Sarajevo'], tur: 'gezi', ad: 'Sarı Tabya', aciklama: 'Manzara', harita: 'https://www.google.com/maps/search/?api=1&query=x', sira: 100, yayinda: false, lat: 43.85, lng: 18.43, konum_kaynak: 'otomatik' },
      { id: 502, sehir: 'Saraybosna', diger_adlar: ['Sarajevo'], tur: 'yemek', ad: '<b>Željo</b>', aciklama: '', harita: null, sira: 90, yayinda: false, lat: null, lng: null, konum_kaynak: 'bulunamadi' },
      { id: 503, sehir: 'Mostar', diger_adlar: [], tur: 'gezi', ad: 'Mostar Köprüsü', aciklama: '', harita: null, sira: 80, yayinda: true }];""")
    pg.evaluate("sekmeAc('sehir')"); pg.wait_for_timeout(400); errs.clear()
    kontrol(pg.input_value('#sr_sehir') == 'Mostar' and pg.locator('#sr_sehir option').count() == 2 and pg.locator('.mekan-item').count() == 1, 'Şehir rehberi (admin): şehirler listede, seçili şehrin mekanları görünüyor', errs)
    pg.select_option('#sr_sehir', 'Saraybosna'); pg.wait_for_timeout(200)
    kontrol(pg.locator('.mekan-item').count() == 2 and pg.locator('.mekan-item .badge-red').count() == 2 and '2 taslak' in pg.inner_text('#sr_sehir') and pg.locator('.mekan-item h4 b b').count() == 0,
            'Şehir rehberi (admin): taslaklar işaretli, isimdeki HTML düz yazı')
    pg.evaluate("window.__islem = []"); pg.locator('.mekan-item[data-id="501"]').get_by_role('button', name='Yayınla').click(); pg.wait_for_timeout(300)
    g = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'sehir_rehberi' and i['tur'] == 'update']
    kontrol(len(g) == 1 and g[0]['veri'] == {'yayinda': True} and g[0]['filtre'] == [['id', 501]] and pg.locator('.mekan-item[data-id="501"] .badge-green').count() == 1, 'Şehir rehberi (admin): tek mekan yayınlanıyor')
    pg.evaluate("window.__islem = []"); pg.get_by_role('button', name=re.compile('tümünü yayınla')).click(); pg.wait_for_timeout(300)
    g = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'sehir_rehberi' and i['tur'] == 'update']
    kontrol(len(g) == 1 and g[0]['filtre'] == [['sehir', 'Saraybosna']] and pg.locator('.mekan-item .badge-red').count() == 0, 'Şehir rehberi (admin): şehrin tümü tek tuşla yayınlanıyor')
    pg.evaluate("window.__islem = []"); pg.get_by_role('button', name=re.compile('Mekan ekle')).click(); pg.wait_for_timeout(200)
    kontrol(pg.input_value('#sr_f_sehir') == 'Saraybosna' and pg.input_value('#sr_f_diger') == 'Sarajevo', 'Şehir rehberi (admin): yeni mekan formu seçili şehirle açılıyor')
    pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(200)
    kontrol(not pg.evaluate('window.__islem'), 'Şehir rehberi (admin): mekan adı boşken kaydetmiyor')
    pg.select_option('#sr_f_tur', 'yemek'); pg.fill('#sr_f_ad', 'Inat Kuća'); pg.fill('#sr_f_aciklama', 'Boşnak yemekleri'); pg.fill('#sr_f_harita', 'javascript:alert(1)')
    pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(200)
    kontrol(not pg.evaluate('window.__islem'), 'Şehir rehberi (admin): https olmayan harita bağlantısı kabul edilmiyor')
    pg.fill('#sr_f_harita', ''); pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(400)
    ek = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'sehir_rehberi' and i['tur'] == 'insert']
    v = ek[0]['veri'] if ek else {}
    kontrol(len(ek) == 1 and v.get('sehir') == 'Saraybosna' and v.get('tur') == 'yemek' and v.get('yayinda') is False and v.get('harita', '').startswith('https://www.google.com/maps/search/') and v.get('sira') < 90 and v.get('diger_adlar') == ['Sarajevo'],
            'Şehir rehberi (admin): yeni mekan taslak olarak, harita aramasıyla ve listenin sonuna ekleniyor', errs)
    # Konum (uygulama haritası): durum yazısı, elle koordinat, bağlantıdan bulma
    pg.evaluate("window.__islem = []; window.__fn = []; SR.sehir = 'Saraybosna'; sehirCiz()"); pg.wait_for_timeout(200)
    kontrol('Uygulama haritasında' in pg.inner_text('.mekan-item[data-id="501"] .sr-konum') and 'bulunamadı' in pg.inner_text('.mekan-item[data-id="502"] .sr-konum'),
            'Şehir rehberi (admin): mekanın haritada olup olmadığı listede yazıyor')
    pg.locator('.mekan-item[data-id="501"]').get_by_role('button', name='Düzenle').click(); pg.wait_for_timeout(200)
    kontrol(pg.input_value('#sr_f_konum') == '43.85, 18.43', 'Şehir rehberi (admin): düzenle formunda mevcut koordinat görünüyor')
    pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(300)
    g = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'sehir_rehberi' and i['tur'] == 'update']
    kontrol(len(g) == 1 and 'lat' not in g[0]['veri'] and 'konum_kaynak' not in g[0]['veri'], 'Şehir rehberi (admin): koordinata dokunulmadıysa konum değişmiyor')
    pg.evaluate("window.__islem = []; SR.sehir = 'Saraybosna'; sehirCiz()"); pg.wait_for_timeout(200)
    pg.locator('.mekan-item[data-id="502"]').get_by_role('button', name='Düzenle').click(); pg.wait_for_timeout(200)
    pg.fill('#sr_f_konum', 'Saraybosna'); pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(200)
    kontrol(not pg.evaluate('window.__islem'), 'Şehir rehberi (admin): geçersiz koordinat kaydedilmiyor')
    pg.fill('#sr_f_konum', '43.8597, 18.4313'); pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(300)
    g = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'sehir_rehberi' and i['tur'] == 'update']
    kontrol(len(g) == 1 and g[0]['veri'].get('lat') == 43.8597 and g[0]['veri'].get('lng') == 18.4313 and g[0]['veri'].get('konum_kaynak') == 'elle', 'Şehir rehberi (admin): elle girilen koordinat kaydediliyor')
    pg.evaluate("window.__islem = []; SR.sehir = 'Saraybosna'; sehirCiz(); sehirMekanYeni()"); pg.wait_for_timeout(200)
    pg.fill('#sr_f_ad', 'Baščaršija'); pg.fill('#sr_f_harita', 'https://maps.app.goo.gl/IYI9'); pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(400)
    ek = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'sehir_rehberi' and i['tur'] == 'insert']
    kontrol(len(ek) == 1 and ek[0]['veri'].get('lat') == 21.4174 and ek[0]['veri'].get('konum_kaynak') == 'otomatik', 'Şehir rehberi (admin): Google bağlantısından konum bulunuyor', errs)
    pg.evaluate("window.__islem = []; SR.sehir = 'Saraybosna'; sehirCiz(); sehirMekanYeni()"); pg.wait_for_timeout(200)
    pg.fill('#sr_f_ad', 'Vrelo Bosne'); pg.fill('#sr_f_harita', 'https://maps.app.goo.gl/KOTU'); pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(400)
    ek = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'sehir_rehberi' and i['tur'] == 'insert']
    kontrol(len(ek) == 1 and 'lat' not in ek[0]['veri'] and 'bulunamadı' in pg.inner_text('#toast'), 'Şehir rehberi (admin): konum bulunamazsa yine kaydediyor ve uyarıyor', errs)
    pg.evaluate("window.__islem = []"); pg.locator('.mekan-item[data-id="503"]').count()
    pg.select_option('#sr_sehir', 'Mostar'); pg.wait_for_timeout(200); pg.locator('.mekan-item[data-id="503"]').get_by_role('button', name='Sil').click(); pg.wait_for_timeout(300)
    s_ = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'delete']
    kontrol(len(s_) == 1 and s_[0]['tablo'] == 'sehir_rehberi' and s_[0]['filtre'] == [['id', 503]] and not errs, 'Şehir rehberi (admin): mekan siliniyor', errs)

    pg.evaluate("sekmeAc('kafile')"); pg.wait_for_timeout(400)
    pg.evaluate("window.__islem = []")
    pg.locator('.kafile-item').get_by_role('button', name='Sil').click(); pg.wait_for_timeout(400)
    s_ = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'delete']
    kontrol(len(s_) == 1 and s_[0]['tablo'] == 'kafileler' and pg.locator('.kafile-item').count() == 0, 'Kafile: siliniyor', errs)

    # ── Yorumlar (WhatsApp mesajları) ──
    pg.evaluate("sekmeAc('yorum')"); pg.wait_for_timeout(400); pg.evaluate("window.__islem = []"); errs.clear()
    pg.get_by_role('button', name=re.compile('Yeni Yorum')).click(); pg.wait_for_timeout(200)
    hedef_tur = next(t for t in VERI['turlar'] if t['kategori'] == 'diger')
    kontrol(pg.locator('#y_tur_sec option').count() == pg.evaluate('window.__DB.turlar.length') + 1, 'Yorum: tanımlı turlar (pasifler dahil) listede seçilebiliyor')
    pg.select_option('#y_tur_sec', hedef_tur['id'])
    kontrol(pg.input_value('#y_tur') == hedef_tur['baslik'] and pg.input_value('#y_kategori') == 'kultur', 'Yorum: tur seçilince tur adı ve kategori (Kültür) kendiliğinden doluyor')
    kontrol(pg.is_disabled('#y_kategori'), 'Yorum: listeden tur seçilince kategori değiştirilemiyor')
    pg.select_option('#y_tur_sec', '')
    kontrol(not pg.is_disabled('#y_kategori'), 'Yorum: tur seçimi kaldırılınca kategori yeniden seçilebiliyor')
    pg.select_option('#y_kategori', 'umre')
    pg.fill('#y_ad', "Zeynep Ela  Çalışkan")
    kontrol(pg.inner_text('#y_adOnizleme') == 'Zeynep Ela Ç*******', 'Yorum: formda sitede görünecek maskeli isim önizleniyor', pg.inner_text('#y_adOnizleme'))
    pg.fill('#y_ad', "Ayşe Kaya"); pg.fill('#y_tur', 'Kasım 2026 Umre'); pg.fill('#y_metin', "Allah razı olsun,\nher şey çok güzeldi.")
    pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(300)
    kontrol(not [i for i in pg.evaluate('window.__islem') if i['tur'] == 'insert'], 'Yorum: yolcu izni işaretlenmeden kaydedilmiyor')
    pg.set_input_files('#sayfa-yorum input[type=file]', files=[{'name': 'm.png', 'mimeType': 'image/png', 'buffer': bytes.fromhex('89504e470d0a1a0a0000000d4948445200000001000000010806000000'
        '1f15c4890000000d49444154789c6360f80f0000010101005b0b3b3c0000000049454e44ae426082')}]); pg.wait_for_timeout(800)
    kontrol('Yüklendi' in pg.inner_text('#y_gorselDurum'), 'Yorum: fotoğraf seçilince küçültülüp yükleniyor', pg.inner_text('#y_gorselDurum'))
    pg.check('#y_izin'); pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(400)
    ek = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'insert' and i['tablo'] == 'yorumlar']
    v = ek[0]['veri'] if ek else {}
    kontrol(len(ek) == 1 and v.get('ad') == 'Ayşe Kaya' and 'ad_gorunen' not in v and v.get('kategori') == 'umre' and v.get('izin') is True and v.get('yayinda') is True and 'güzeldi' in v.get('metin', ''),
            'Yorum: izinle kaydediliyor (varsayılan Umre, yayında)', errs)
    kontrol(pg.locator('.yorum-item').count() == 1 and 'Yayında' in pg.inner_text('.yorum-item') and 'Ayşe Kaya' in pg.inner_text('.yorum-item h4')
            and pg.inner_text('.yorum-item .ad-gorunen') == 'Ayşe K***', 'Yorum: listede tam isim ve sitede görünecek hali (Ayşe K***)')
    pg.evaluate("window.__islem = []"); pg.locator('.yorum-item').get_by_role('button', name='Gizle').click(); pg.wait_for_timeout(400)
    g = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'update']
    kontrol(len(g) == 1 and g[0]['veri'] == {'yayinda': False} and 'Gizli' in pg.inner_text('.yorum-item'), 'Yorum: "Gizle" siteden kaldırıyor, kayıt duruyor')
    pg.locator('.yorum-item').get_by_role('button', name='Düzenle').click(); pg.wait_for_timeout(300)
    kontrol(pg.input_value('#y_ad') == 'Ayşe Kaya' and pg.is_checked('#y_izin') and not pg.is_checked('#y_yayinda'), 'Yorum: düzenleme formu kayıtlı bilgilerle açılıyor')
    pg.select_option('#y_tur_sec', hedef_tur['id']); pg.fill('#y_tur', 'Balkan Turu 2027'); pg.check('#y_yayinda'); pg.evaluate("window.__islem = []")
    pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(400)
    g = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'update']
    kontrol(len(g) == 1 and g[0]['veri']['kategori'] == 'kultur' and g[0]['veri']['tur_id'] == hedef_tur['id'], 'Yorum: kilitli kategori ve seçilen tur kaydediliyor')
    pg.locator('.yorum-item').get_by_role('button', name='Düzenle').click(); pg.wait_for_timeout(300)
    kontrol(pg.input_value('#y_tur_sec') == hedef_tur['id'] and pg.is_disabled('#y_kategori') and pg.input_value('#y_tur') == 'Balkan Turu 2027',
            'Yorum: tur adı kısaltılsa da düzenlemede seçili tur ve kilitli kategoriyle açılıyor')
    pg.get_by_role('button', name='İptal').click(); pg.wait_for_timeout(300)
    pg.evaluate("window.__islem = []"); pg.locator('.yorum-item').get_by_role('button', name='Sil').click(); pg.wait_for_timeout(400)
    s_ = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'delete']
    kontrol(len(s_) == 1 and s_[0]['tablo'] == 'yorumlar' and pg.locator('.yorum-item').count() == 0 and not errs, 'Yorum: siliniyor', errs)

    # Telefon görünümü: her sekmede yatay taşma yok, seçili sekme üst şeritte görünür
    pg.set_viewport_size({'width': 390, 'height': 844})
    for sekme, ek in [('basvuru', ''), ('turlar', ''), ('turlar', "sekmeAc('ekle')"), ('duyuru', ''), ('kafile', ''), ('yorum', ''), ('yorum', 'yorumYeni()'), ('kafile', 'kafileYeni()'), ('turlar', f"turDuzenle('{VERI['turlar'][1]['id']}')")]:
        errs.clear(); pg.evaluate(f"sekmeAc('{sekme}')"); pg.wait_for_timeout(250)
        if ek: pg.evaluate(ek); pg.wait_for_timeout(250)
        genis = pg.evaluate('document.documentElement.scrollWidth')
        gorunur = pg.evaluate(f"(() => {{ const r = document.getElementById('btn-{sekme}').getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth + 1; }})()")
        kontrol(genis <= 391 and gorunur and not errs, f'Telefon: {sekme}{" / " + ek.split("(")[0] if ek else ""} sığıyor, sekme görünür', f'(genişlik {genis})')
    pg.set_viewport_size({'width': 1300, 'height': 900})

    # Sil onayla çalışıyor
    pg.evaluate("sekmeAc('turlar')"); pg.wait_for_timeout(400)
    pg.evaluate("window.__islem = []"); son = VERI['turlar'][-1]['id']
    pg.evaluate(f"turSil('{son}')"); pg.wait_for_timeout(400)
    s = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'delete']
    kontrol(len(s) == 1 and s[0]['filtre'] == [['id', son]], 'Sil yalnızca seçilen turu siler', errs)

    # ── Akıllı yapıştırma: ofisin gerçek oda listesi düzeni (uydurma isimlerle) ve transfer listesi ──
    ap = b.new_page(viewport={'width': 1300, 'height': 900}); errs = []
    ap.on('pageerror', lambda e: errs.append(str(e)[:160]))
    ap.route('**cdn.jsdelivr.net/npm/@supabase/**', lambda r, q: r.fulfill(status=200, body=SAHTE, headers={'content-type': 'application/javascript'}))
    ap.route(re.compile(r'^https?://(?!localhost)'), lambda r, q: r.abort() if 'jsdelivr' not in q.url else r.fallback())
    ap.add_init_script('window.confirm = function(){ return true; };')
    ap.goto(BASE + 'admin.html', wait_until='domcontentloaded'); ap.wait_for_timeout(400)
    ap.evaluate("""window.__DB.kafileler = [{ id: 'k9', kod: 'KASIM-BBBBB', ad: 'Kasım Umre', aktif: true, tur_turu: 'umre', baslangic: '2026-11-05', bitis: '2026-11-18',
      oteller: [{ sehir: 'Mekke', ad: 'Samama', giris: '2026-11-05', cikis: '2026-11-15' }, { sehir: 'Medine', ad: 'Saraya Harmony', giris: '2026-11-15', cikis: '2026-11-18' }], program: [] }];
      window.__DB.musteriler = []; window.__DB.kafile_katilimcilar = []; sekmeAc('kafile'); kafileKatilimcilar('k9');""")
    ap.wait_for_timeout(500); ap.locator('summary', has_text='Excel').click()
    OFIS = ('\t\t\tMEKKE\t\t\t\t\tMedine\n\t\t\tYÜRÜME\n\tODA SAYISI\t\t\tGİRİŞ\tÇIKIŞ\tGECE\t\tODA SAYISI\tGİRİŞ\n'
            '\t10\t\t\t05.11.2026\t15.11.2026\t10\t\t10.01.1900\t15.11.2026\n'
            'S.N\tOD SY\tTİPİ\tADI\tSOYADI\tMK. OTELİ\tGRŞ TRH\tARA TRH\tÇKŞ TRH\tMD. OTELİ\tG.SY\tŞUBE\n'
            '1\t1\tDBL\tALİ\tYILMAZ\tSAMAMA\t05.11.2026\t15.11.2026\t18.11.2026\tSARAYA HARMONY\t14\tCOŞAR\n'
            '2\t\t\tAYŞE\tYILMAZ\tSAMAMA\t05.11.2026\t15.11.2026\t18.11.2026\tSARAYA HARMONY\t14\t\n'
            '3\t2\t"TRPL /KNG\n/EKSTRA BED"\tVELİ\tDEMİR\tSAMAMA\t05.11.2026\t15.11.2026\t18.11.2026\tSARAYA HARMONY\t14\tCOŞAR\n'
            '4\t\t\tFATMA\tDEMİR\tSAMAMA\t05.11.2026\t15.11.2026\t18.11.2026\tSARAYA HARMONY\t14\t\n'
            '5\t\t\tZEYNEP\tDEMİR\tSAMAMA\t07.11.2026\t15.11.2026\t18.11.2026\tSARAYA HARMONY\t12\t\n'
            '7\t4\tDBL\tSAIT\tBULMUS\tSAMAMA\t05.11.2026\t15.11.2026\t18.11.2026\tSARAYA HARMONY\t14\t\n'
            '6\t3\tSNGL\tHASAN\tKARA\tSAMAMA\t05.11.2026\t15.11.2026\t18.11.2026\tSARAYA HARMONY\t14\tCOŞAR\n'
            '\t\t\t\t\tSAMAMA\t05.11.2026\t15.11.2026\t18.11.2026\tSARAYA HARMONY\n')
    ap.evaluate("t => { document.getElementById('kt_yapistir').value = t; }", OFIS)
    ap.get_by_role('button', name=re.compile('Önizle')).click(); ap.wait_for_timeout(300)
    es = ap.evaluate("KT.eslesme")
    kontrol(es[:10] == ['sira', 'no', 'tip', 'ad', 'soyad', 'yok', 'giris', 'ara', 'cikis', 'yok'], 'Akıllı yapıştırma: başlık satırı bulunuyor, kolonlar başlıklarından tanınıyor (üstteki başlık/özet satırları atlanıyor)', es)
    v = ap.evaluate("KT.onizleme")
    adlar = [x['ad'] for x in v]
    kontrol(adlar == ['Ali Yılmaz', 'Ayşe Yılmaz', 'Veli Demir', 'Fatma Demir', 'Zeynep Demir', 'Sait Bulmus', 'Hasan Kara'], 'Akıllı yapıştırma: ad + soyad birleşiyor, BÜYÜK HARF isim düzeltiliyor (ALİ → Ali, Türkçe karaktersiz SAIT → Sait), isimsiz satır atlanıyor', adlar)
    o = {x['ad']: x['odalar'] for x in v}
    kontrol(o['Ayşe Yılmaz'] == {'Mekke': {'no': '1', 'tip': 'DBL'}, 'Medine': {'no': '1', 'tip': 'DBL'}} and o['Fatma Demir']['Mekke'] == {'no': '2', 'tip': 'TRPL/KNG/EKSTRA BED'}
            and o['Zeynep Demir']['Mekke'] == {'no': '2', 'tip': 'TRPL/KNG/EKSTRA BED', 'giris': '2026-11-07'} and o['Hasan Kara']['Mekke'] == {'no': '3', 'tip': 'SNGL'},
            'Akıllı yapıştırma: birleştirilmiş oda no/tip alttakilere uygulanıyor; otel tarihinden farklı giriş kişiye özel kaydediliyor', str(o)[:200])
    kontrol(ap.locator('#kt_onizleme .oda-uyari').count() == 0 and '3 kişiyi' not in ap.inner_text('#kt_onizleme') and '7 kişiyi ekle' in ap.inner_text('#kt_onizleme'),
            'Akıllı yapıştırma: TRPL + ekstra yatak odasında 3 kişi uyarı vermiyor, 7 kişi eklenebilir', errs)
    # kolonu elle değiştir: TİPİ → Kullanma; seçim hatırlanır
    ap.select_option('#kt_onizleme .kolon-sec[data-i="2"]', 'yok'); ap.wait_for_timeout(200)
    v = ap.evaluate("KT.onizleme")
    kontrol('tip' not in v[0]['odalar']['Mekke'], 'Akıllı yapıştırma: kolon eşleştirmesi elle değiştirilince önizleme güncelleniyor')
    ap.get_by_role('button', name=re.compile('Önizle')).click(); ap.wait_for_timeout(200)
    kontrol(ap.evaluate("KT.eslesme[2]") == 'yok', 'Akıllı yapıştırma: aynı başlıklı tablo tekrar yapıştırılınca elle yapılan eşleştirme hatırlanıyor')
    ap.select_option('#kt_onizleme .kolon-sec[data-i="2"]', 'tip'); ap.wait_for_timeout(200)
    ap.evaluate("window.__islem = []"); ap.get_by_role('button', name=re.compile('kişiyi ekle')).click(); ap.wait_for_timeout(500)
    ki = [i for i in ap.evaluate('window.__islem') if i['tablo'] == 'kafile_katilimcilar' and i['tur'] == 'insert']
    kontrol(len(ki) == 1 and len(ki[0]['veri']) == 7 and ap.locator('.katilimci-satir').count() == 7 and ap.locator('.oda-uyarilari').count() == 0 and not errs,
            'Akıllı yapıştırma: 7 kişi odalarıyla ekleniyor, oda uyarısı yok', errs)
    # toplu oda numarası girişi
    ap.click('#odaGirBtn'); ap.wait_for_timeout(200)
    kontrol(ap.locator('.toplu-oda .to_no').count() == 14 and ap.locator('.katilimci-tablo').count() == 0, 'Oda numaraları: herkes için Mekke ve Medine kutusu (7 kişi × 2 otel), tek ekranda')
    def kutu(ad, otel): return ap.locator(f'.toplu-oda tr:has-text("{ad}") .to_no[data-otel="{otel}"]')
    for ad, mk in [('Ali Yılmaz', '512'), ('Ayşe Yılmaz', '512'), ('Veli Demir', '514'), ('Fatma Demir', '514'), ('Zeynep Demir', '514'), ('Sait Bulmus', '512')]:
        kutu(ad, 'Mekke').fill(mk)
    kutu('Hasan Kara', 'Mekke').fill(''); kutu('Ali Yılmaz', 'Medine').fill('301')
    ap.evaluate("window.__islem = []; window.confirm = function(m){ window.__onay = m; return false; }")
    ap.get_by_role('button', name=re.compile('Hepsini kaydet')).click(); ap.wait_for_timeout(300)
    kontrol('Oda 512' in (ap.evaluate('window.__onay') or '') and not ap.evaluate('window.__islem'), 'Oda numaraları: DBL odaya 3 kişi yazılınca uyarı; "Hayır" denirse hiçbir şey kaydedilmiyor')
    kutu('Sait Bulmus', 'Mekke').fill('516')
    ap.evaluate("window.__islem = []; window.__onay = null")
    ap.get_by_role('button', name=re.compile('Hepsini kaydet')).click(); ap.wait_for_timeout(600)
    g = {x['filtre'][0][1]: x['veri']['odalar'] for x in ap.evaluate('window.__islem') if x['tablo'] == 'kafile_katilimcilar' and x['tur'] == 'update'}
    ali = next((v for v in g.values() if v.get('Medine', {}).get('no') == '301'), {})
    kontrol(ap.evaluate('window.__onay') is None and len(g) == 7 and ali == {'Mekke': {'no': '512', 'tip': 'DBL'}, 'Medine': {'no': '301', 'tip': 'DBL'}}
            and any(v['Mekke'] == {'no': '514', 'tip': 'TRPL/KNG/EKSTRA BED', 'giris': '2026-11-07'} for v in g.values())
            and any(v['Mekke'] == {'tip': 'SNGL'} for v in g.values()), 'Oda numaraları: tek Kaydet ile hepsi yazılıyor; tip ve kişiye özel tarih korunuyor, silinen numara kalkıyor', str(g)[:200])
    kontrol(ap.locator('.toplu-oda').count() == 0 and ap.locator('.katilimci-satir').count() == 7 and not errs, 'Oda numaraları: kaydedince liste normal görünümüne dönüyor', errs)
    ap.evaluate("window.confirm = function(){ return true; }")
    # transfer listesi → program
    ap.evaluate("kafileDuzenle('k9')"); ap.wait_for_timeout(400)
    TRANSFER = ('ISMAIL COSAR TURIZM\tGELIS PC670 /DONUS PC689\tMAWEKEB\n\t\t\t\tTARIH\tSAAT\n'
                'BUS\t1\tJAD AIRPORT\tMAKKAH HOTEL\t05.11.2026\t11:00\nBUS\t1\tMAKKAH\tMAZARAT\t07.11.2026\t08:00\n'
                'BUS\t1\tMEDINAH TRAIN STATION\tMEDINAH HOTEL\t15.11.2026\t17:20\n')
    ap.locator('summary', has_text='Transfer').click(); ap.fill('#k_program_yapistir', TRANSFER)
    ap.get_by_role('button', name=re.compile('Programa ekle')).click(); ap.wait_for_timeout(200)
    satir = [(s.locator('.p_tarih').input_value(), s.locator('.p_saat').input_value(), s.locator('.p_baslik').input_value(), s.locator('.p_yer').input_value()) for s in ap.locator('#k_program .prog-satir').all()]
    kontrol(satir == [('2026-11-05', '11:00', '🚌 Makkah Hotel', 'Jad Airport'), ('2026-11-07', '08:00', '🚌 Mazarat', 'Makkah'), ('2026-11-15', '17:20', '🚌 Medinah Hotel', 'Medinah Train Station')],
            'Transfer listesi: tarihli satırlar programa ekleniyor (başlık satırları atlanıyor, "Medinah" Türkçe ı ile bozulmuyor)', satir)
    ap.evaluate("window.__islem = []"); ap.get_by_role('button', name=re.compile('Kaydet')).click(); ap.wait_for_timeout(400)
    g = [i for i in ap.evaluate('window.__islem') if i['tur'] == 'update' and i['tablo'] == 'kafileler']
    kontrol(len(g) == 1 and len(g[0]['veri']['program']) == 3 and not errs, 'Transfer listesi: kaydedilince program gruba yazılıyor', errs)
    ap.close()

    # ── Doğum günleri: ana sayfa kartı + tur sırasında 🎂 ──
    dp = b.new_page(viewport={'width': 390, 'height': 844}); errs = []
    dp.on('pageerror', lambda e: errs.append(str(e)[:160]))
    dp.route('**cdn.jsdelivr.net/npm/@supabase/**', lambda r, q: r.fulfill(status=200, body=SAHTE, headers={'content-type': 'application/javascript'}))
    dp.route(re.compile(r'^https?://(?!localhost)'), lambda r, q: r.abort() if 'jsdelivr' not in q.url else r.fallback())
    dp.goto(BASE + 'admin.html', wait_until='domcontentloaded'); dp.wait_for_timeout(400)
    dp.evaluate("""(() => { const g = n => { const d = new Date(); d.setDate(d.getDate() + n); return (1960) + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
      window.__DB.musteriler = [
        { id: 'd1', ad: 'Bugün Doğan', telefon: '0532 111 22 33', dogum_tarihi: g(0), ileti_izni: true },
        { id: 'd2', ad: 'Yarın Doğan', telefon: '05321112234', dogum_tarihi: g(1), ileti_izni: false },
        { id: 'd3', ad: 'Uzak Doğan', telefon: '05321112235', dogum_tarihi: g(20), ileti_izni: true },
        { id: 'd4', ad: 'Tarihsiz Kişi', telefon: '05321112236', dogum_tarihi: null, ileti_izni: true }];
      window.__DB.kafileler = [{ id: 'k5', kod: 'X-AAAAA', ad: 'Doğum Testi', aktif: true, baslangic: g(-2).replace('1960', String(new Date().getFullYear())), bitis: g(3).replace('1960', String(new Date().getFullYear())), oteller: [], program: [] }];
      window.__DB.kafile_katilimcilar = [{ id: 51, kafile_id: 'k5', musteri_id: 'd1', odalar: {} }, { id: 52, kafile_id: 'k5', musteri_id: 'd3', odalar: {} }];
      sekmeAc('ana'); })()"""); dp.wait_for_timeout(500)
    satir = dp.locator('.dogum-kart .dogum-satir')
    kontrol(satir.count() == 2 and 'Bugün Doğan' in satir.nth(0).inner_text() and 'bugün' in satir.nth(0).inner_text() and 'yarın' in satir.nth(1).inner_text()
            and 'Uzak' not in dp.inner_text('#sayfa-ana'), 'Doğum günü kartı: ana sayfada önümüzdeki 7 gün, en yakını üstte', dp.inner_text('#sayfa-ana')[-200:])
    h = dp.get_attribute('.dogum-satir a.dogum-wa', 'href') or ''
    kontrol(dp.locator('.dogum-wa').count() == 1 and h.startswith('https://wa.me/905321112233?text=') and 'Bug%C3%BCn%20Do%C4%9Fan' in h and 'ileti izni yok' in satir.nth(1).inner_text(),
            'Doğum günü kartı: WhatsApp butonu kişinin numarasına ve adına hazır mesajla; izni olmayanda buton yok', h[:80])
    kontrol('yaşına giriyor' in satir.nth(0).inner_text() and dp.evaluate('document.documentElement.scrollWidth') <= 391, 'Doğum günü kartı: yaş görünüyor, telefonda taşmıyor')
    dp.evaluate("sekmeAc('kafile'); kafileKatilimcilar('k5')"); dp.wait_for_timeout(500)
    kontrol(dp.locator('.katilimci-satir', has_text='Bugün Doğan').locator('.tur-dogum').count() == 1 and dp.locator('.katilimci-satir', has_text='Uzak Doğan').locator('.tur-dogum').count() == 0 and not errs,
            'Katılımcılar: doğum günü tur tarihlerine denk gelen kişide 🎂 işareti', errs)
    # ── Ziyaretçiler sayfası ──
    dp.evaluate("""(() => { const s = (gun, saat) => { const d = new Date(); d.setDate(d.getDate() - gun); d.setHours(saat, 10, 0, 0); return d.toISOString(); };
      window.__DB.ziyaretler = [
        { zaman: s(0, 9), sayfa: '/', kaynak: 'google.com', cihaz: 'telefon', ziyaretci: 'a' },
        { zaman: s(0, 9), sayfa: '/tur-detay.html?id=TID', kaynak: '', cihaz: 'telefon', ziyaretci: 'a' },
        { zaman: s(0, 10), sayfa: '/', kaynak: 'l.instagram.com', cihaz: 'telefon', ziyaretci: 'b' },
        { zaman: s(0, 11), sayfa: '/tesekkurler.html', kaynak: '', cihaz: 'bilgisayar', ziyaretci: 'c' },
        { zaman: s(2, 14), sayfa: '/', kaynak: '', cihaz: 'bilgisayar', ziyaretci: 'a' },
        { zaman: s(20, 14), sayfa: '/umre.html', kaynak: '', cihaz: 'telefon', ziyaretci: 'd' }];
      sekmeAc('ana'); })()""".replace('TID', 'umre-kis')); dp.wait_for_timeout(500)
    kontrol('Bugün 3 ziyaretçi' in dp.inner_text('#anaZiyaret'), 'Ana sayfa: Ziyaretçiler kutusunda bugünkü ziyaretçi sayısı', dp.inner_text('#anaZiyaret'))
    dp.evaluate("sekmeAc('ziyaret')"); dp.wait_for_timeout(500)
    zt = dp.inner_text('#sayfa-ziyaret')
    kutular = dp.locator('.zy-kutular > div').all_inner_texts()
    kontrol(kutular[0].startswith('4') and kutular[1].startswith('5') and kutular[2].startswith('50%'), 'Ziyaretçiler: son 7 gün 4 ziyaretçi, 5 görüntüleme, %50 telefon', kutular)
    kontrol('Ana sayfa' in zt and 'Tur: EKİM AYI UMRE PROGRAMI (2026) 14 GÜN' in zt and 'Başvuru gönderildi' in zt and 'Umre turları' not in zt, 'Ziyaretçiler: sayfalar okunur adlarla (tur detayı tur adıyla); 7 günden eski kayıt yok', zt[:300])
    kontrol('Google' in zt and 'Instagram' in zt and 'Doğrudan' in zt and dp.locator('.zy-grafik > div').count() == 7, 'Ziyaretçiler: kaynaklar (Google, Instagram, Doğrudan) ve 7 günlük grafik')
    # grafikte bir güne dokununca o günün rakamları
    dp.locator('.zy-dilim').nth(4).click(); dp.wait_for_timeout(300)   # 2 gün önce: yalnız 'a', ana sayfa, doğrudan, bilgisayar
    kut = dp.locator('.zy-kutular > div').all_inner_texts(); st = dp.inner_text('#sayfa-ziyaret')
    kontrol(kut[0].startswith('1') and kut[1].startswith('1') and kut[2].startswith('0%') and dp.locator('.zy-dilim.secili').count() == 1
            and 'toplamına dön' in st and dp.locator('.card', has_text='Nereden geldiler').locator('.zy-satir').all_inner_texts()[0].startswith('Doğrudan') and dp.locator('.card', has_text='Nereden geldiler').locator('.zy-satir').count() == 1 and dp.locator('.zy-grafik > div').count() == 7,
            'Ziyaretçiler: grafikte bir güne dokununca kutular ve listeler o günün rakamlarını gösteriyor', kut)
    dp.locator('.zy-dilim').nth(5).click(); dp.wait_for_timeout(300)   # kayıt olmayan gün
    kontrol(dp.locator('.zy-kutular > div').first.inner_text().startswith('0') and dp.locator('.zy-bos').count() == 1, 'Ziyaretçiler: kaydı olmayan gün seçilince "kayıt yok" yazıyor')
    dp.locator('.zy-dilim').nth(5).click(); dp.wait_for_timeout(300)
    kontrol(dp.locator('.zy-kutular > div').first.inner_text().startswith('4') and dp.locator('.zy-dilim.secili').count() == 0, 'Ziyaretçiler: aynı güne tekrar dokununca dönem toplamına dönüyor')
    dp.locator('.zy-dilim').nth(6).click(); dp.wait_for_timeout(300); dp.click('.zy-temizle'); dp.wait_for_timeout(300)
    kontrol(dp.locator('.zy-kutular > div').first.inner_text().startswith('4') and not errs, 'Ziyaretçiler: "toplamına dön" butonu seçimi kaldırıyor', errs)
    dp.locator('.zy-donem', has_text='Son 30 gün').click(); dp.wait_for_timeout(500)
    kontrol('Umre turları' in dp.inner_text('#sayfa-ziyaret') and dp.locator('.zy-grafik > div').count() == 30, 'Ziyaretçiler: "Son 30 gün" seçilince eski kayıtlar da geliyor')
    dp.locator('.zy-donem', has_text='Bugün').click(); dp.wait_for_timeout(500)
    kontrol(dp.locator('.zy-kutular > div').first.inner_text().startswith('3') and dp.locator('.zy-grafik > div').count() == 24 and dp.evaluate('document.documentElement.scrollWidth') <= 391 and not errs,
            'Ziyaretçiler: "Bugün" saat saat; telefonda taşmıyor', errs)
    dp.evaluate("sekmeAc('kafile')"); dp.wait_for_timeout(400)
    # ── Turu eski müşterilere duyur ──
    dp.evaluate("window.__acilan = []; window.open = function(u){ window.__acilan.push(u); return null; }; localStorage.clear(); sekmeAc('turlar')"); dp.wait_for_timeout(500)
    dp.locator('#sayfa-turlar .tur-item', has_text='umre-kis').locator('.tur-duyur-btn').click(); dp.wait_for_timeout(500)
    tdm = dp.input_value('#td_mesaj'); tdt = dp.inner_text('#sayfa-turlar')
    kontrol(dp.locator('.td-satir').count() == 3 and 'Yarın Doğan' not in tdt and '1 kişi izinsiz' in tdt and '{ad}' in tdm and 'ismailcosarturizm.com.tr/t/umre-kis.html' in tdm,
            'Tur duyurusu: yalnızca ileti izni ve telefonu olan müşteriler listeleniyor; hazır mesajda tur bağlantısı var', tdt[:200])
    dp.click('.td-link-insta'); dp.wait_for_timeout(200)
    kontrol(dp.evaluate('window.__sonKopya') == 'https://ismailcosarturizm.com.tr/t/umre-kis.html?utm_source=instagram', 'Tur duyurusu: paylaşım bağlantısı (Instagram için işaretli) kopyalanıyor', dp.evaluate('window.__sonKopya'))
    dp.fill('#td_mesaj', 'Merhaba {ad}, yeni tur!')
    dp.locator('.td-satir', has_text='Bugün Doğan').locator('.td-gonder').click(); dp.wait_for_timeout(300)
    acilan = dp.evaluate('window.__acilan')
    kontrol(len(acilan) == 1 and acilan[0] == 'https://wa.me/905321112233?text=Merhaba%20Bug%C3%BCn%20Do%C4%9Fan%2C%20yeni%20tur!',
            'Tur duyurusu: "WhatsApp ile gönder" kişinin numarasına, adı yerleştirilmiş (düzenlenmiş) mesajla açılıyor', acilan)
    kontrol('3 kişi · 1 gönderildi' in dp.inner_text('#td_sayi') and 'Gönderildi' in dp.locator('.td-satir', has_text='Bugün Doğan').inner_text() and dp.locator('.td-satir').last.get_attribute('data-id') == 'd1'
            and dp.input_value('#td_mesaj') == 'Merhaba {ad}, yeni tur!', 'Tur duyurusu: gönderilen kişi işaretlenip sona alınıyor; yazılan mesaj korunuyor')
    dp.select_option('#td_filtre', 'k5'); dp.wait_for_timeout(200)
    kontrol(dp.locator('.td-satir').count() == 2 and 'Tarihsiz' not in dp.inner_text('#sayfa-turlar'), 'Tur duyurusu: gruba göre süzülebiliyor')
    dp.evaluate("renderTurlar()"); dp.wait_for_timeout(400)
    dp.locator('#sayfa-turlar .tur-item', has_text='umre-kis').locator('.tur-duyur-btn').click(); dp.wait_for_timeout(500)
    kontrol('1 gönderildi' in dp.inner_text('#td_sayi') and dp.evaluate('document.documentElement.scrollWidth') <= 391 and not errs, 'Tur duyurusu: kime gönderildiği hatırlanıyor; telefonda taşmıyor', errs)
    # ── Tur sonu anket sonuçları ──
    dp.evaluate("""window.__DB.kafile_anketler = [
        { id: 1, kafile_id: 'k5', cihaz: 'c1', rehber: 5, otel: 3, genel: 5, yorum: 'Rehber <b>çok</b> ilgiliydi', olusturma: new Date().toISOString() },
        { id: 2, kafile_id: 'k5', cihaz: 'c2', rehber: 4, otel: 2, genel: 4, yorum: null, olusturma: new Date().toISOString() },
        { id: 3, kafile_id: 'baska', cihaz: 'c3', rehber: 1, otel: 1, genel: 1, yorum: 'başka grup', olusturma: new Date().toISOString() }];
      sekmeAc('kafile')"""); dp.wait_for_timeout(500)
    kontrol('(2 · 4,5★)' in dp.inner_text('.kafile-item .anket-btn'), 'Anket: Gruplar listesinde yanıt sayısı ve genel ortalama', dp.inner_text('.kafile-item .anket-btn'))
    dp.click('.kafile-item .anket-btn'); dp.wait_for_timeout(500)
    at = dp.inner_text('#sayfa-kafile'); ortlar = dp.locator('.anket-ort b').all_inner_texts()
    kontrol('2 yanıt' in at and [o.split()[0] for o in ortlar] == ['4,5', '2,5', '4,5'] and dp.locator('.anket-yorum-satir').count() == 1 and 'başka grup' not in at
            and '<b>çok</b>' in at and dp.locator('.anket-yorum-satir b').count() == 0 and dp.evaluate('document.documentElement.scrollWidth') <= 391 and not errs,
            'Anket: soru soru ortalama, yazılan yorumlar (HTML düz yazı), yalnızca o grubun yanıtları', [ortlar, errs])
    dp.evaluate("sekmeAc('kafile')"); dp.wait_for_timeout(400)
    # Telefonda uygulama görünümü: alt sekme çubuğu + "Diğer" menüsü
    kontrol(dp.is_visible('.mobil-alt') and dp.is_visible('.mobil-ust') and not dp.is_visible('.sidebar') and dp.locator('.mobil-alt button.active').get_attribute('data-m') == 'kafile',
            'Telefon: altta sekme çubuğu, üstte marka çubuğu; açık sekme işaretli')
    dp.click('.mobil-alt [data-m="ana"]'); dp.wait_for_timeout(300)
    kontrol(dp.is_visible('#sayfa-ana') and dp.locator('.mobil-alt button.active').get_attribute('data-m') == 'ana', 'Telefon: alt çubuktan Ana Sayfa açılıyor')
    dp.click('.mobil-alt [data-m="diger"]'); dp.wait_for_timeout(200)
    kontrol(dp.is_visible('#mobilDiger'), 'Telefon: "Diğer" menüsü açılıyor')
    dp.click('#mobilDiger button:has-text("Tur Listesi")'); dp.wait_for_timeout(400)
    kontrol(dp.is_visible('#sayfa-turlar') and not dp.is_visible('#mobilDiger') and dp.locator('.mobil-alt button.active').get_attribute('data-m') == 'diger', 'Telefon: Diğer → Tur Listesi açılıyor, menü kapanıyor')
    kontrol('Turlar' in dp.inner_text('.mobil-alt [data-m="diger"]'), 'Telefon: alt çubukta "Diğer" yerine açık sayfanın adı (Turlar) görünüyor')
    dp.click('.mobil-alt [data-m="diger"]'); dp.wait_for_timeout(200); dp.mouse.click(195, 100); dp.wait_for_timeout(200)
    kontrol(not dp.is_visible('#mobilDiger') and dp.evaluate('document.documentElement.scrollWidth') <= 391 and not errs, 'Telefon: Diğer menüsü boşluğa basınca kapanıyor; sayfa yana taşmıyor', errs)
    dp.close()

    # ── Rehber rolüyle giriş: yalnızca kafilesinin katılımcı/oda listesi ──
    for vp in [{'width': 1300, 'height': 900}, {'width': 390, 'height': 844}]:
        rp = b.new_page(viewport=vp); errs = []
        rp.on('pageerror', lambda e: errs.append(str(e)[:160]))
        rp.route('**cdn.jsdelivr.net/npm/@supabase/**', lambda r, q: r.fulfill(status=200, body=SAHTE, headers={'content-type': 'application/javascript'}))
        rp.route(re.compile(r'^https?://(?!localhost)'), lambda r, q: r.abort() if 'jsdelivr' not in q.url else r.fallback())
        rp.add_init_script("""window.confirm = function(){ return true; }; window.__ROL = 'rehber';
          window.__VERI_EK = function(){ window.__DB.kafileler = [{ id: 'k1', kod: 'KASIM-AAAAA', ad: 'Kasım Kafilesi', aktif: true, oteller: [{ sehir: 'Mekke', ad: 'Otel A' }], program: [] }];
            window.__DB.musteriler = [{ id: 'm1', ad: 'Ayşe Kaya', telefon: '0533', dogum_tarihi: '1950-01-02', ileti_izni: true }];
            window.__DB.kafile_katilimcilar = [{ id: 7, kafile_id: 'k1', musteri_id: 'm1', odalar: { Mekke: '512' } }]; };""")
        rp.goto(BASE + 'admin.html', wait_until='domcontentloaded'); rp.wait_for_timeout(300); rp.evaluate('window.__VERI_EK(); sekmeAc("kafile")'); rp.wait_for_timeout(500)
        gorunen = [x for x in ['ana', 'basvuru', 'turlar', 'duyuru', 'yorum', 'musteri', 'rehber', 'sehir'] if rp.is_visible('#btn-' + x)] + (['başlık'] if rp.locator('.nav-baslik:visible').count() else [])
        kontrol(rp.is_visible('#appDiv') and not gorunen and 'Gruplarım' in rp.inner_text('#btn-kafile'), f'Rehber ({vp["width"]}px): menüde yalnızca "Gruplarım" var', gorunen or errs)
        rp.evaluate("sekmeAc('basvuru')"); rp.wait_for_timeout(300)
        kontrol(rp.is_visible('#sayfa-kafile') and not rp.is_visible('#sayfa-basvuru'), 'Rehber: başka sekmeye geçemiyor')
        kontrol('Test · Rehber' in rp.inner_text('#kullaniciBilgi') and rp.is_visible('#kullaniciBilgi'), 'Rehber: sağ üstte kullanıcı adı ve rolü görünüyor', rp.inner_text('#kullaniciBilgi'))
        kontrol(rp.locator('.kafile-item').count() == 1 and rp.locator('.kafile-item button').count() == 1, 'Rehber: kafilede düzenle/sil/duyuru yok, yalnızca "Katılımcılar ve odalar"')
        h = rp.get_attribute('.kafile-item a.rehber-paylas', 'href') or ''
        kontrol('KASIM-AAAAA' in rp.inner_text('.kafile-item') and h.startswith('https://wa.me/?text=') and 'kafile%2F%23KASIM-AAAAA' in h, 'Rehber: misafir kodu görünüyor, "Misafir kodunu paylaş" WhatsApp bağlantısı kodlu')
        rp.locator('.kafile-item button').click(); rp.wait_for_timeout(400)
        kontrol(rp.locator('#kt_kart').count() == 0 and rp.locator('summary', has_text='Excel').count() == 0 and rp.locator('.katilimci-satir button', has_text='Çıkar').count() == 0
                and rp.locator('.katilimci-satir').count() == 1, 'Rehber: listeyi görüyor; ekleme, Excel ve çıkarma yok', errs)
        rp.evaluate("window.__islem = []"); rp.locator('.katilimci-satir').get_by_role('button', name='Düzenle').click(); rp.wait_for_timeout(200)
        kontrol(rp.locator('#kt_izin').count() == 0 and rp.input_value('#kt_kart .kt_oda') == '512', 'Rehber: düzenleme formu açılıyor (ileti izni alanı yok)')
        rp.fill('#kt_kart .kt_oda', '520'); rp.fill('#kt_tel', '0533 999 88 77'); rp.locator('#kt_kart').get_by_role('button', name=re.compile('Kaydet')).click(); rp.wait_for_timeout(500)
        isl = rp.evaluate('window.__islem')
        mu = [i for i in isl if i['tablo'] == 'musteriler' and i['tur'] == 'update']; ku = [i for i in isl if i['tablo'] == 'kafile_katilimcilar' and i['tur'] == 'update']
        kontrol(len(mu) == 1 and 'ileti_izni' not in mu[0]['veri'] and mu[0]['veri']['telefon'] == '0533 999 88 77' and len(ku) == 1 and ku[0]['veri'] == {'odalar': {'Mekke': {'no': '520'}}}
                and not [i for i in isl if i['tur'] in ('insert', 'delete')] and not errs, 'Rehber: oda ve telefonu düzeltebiliyor (izin değişmiyor, ekleme/silme yok)', errs)
        rp.evaluate("window.__paylasilan = null; navigator.share = function(v){ window.__paylasilan = v; return Promise.resolve(); }")
        rp.get_by_role('button', name=re.compile('Listeyi paylaş')).click(); rp.wait_for_timeout(200)
        pv = rp.evaluate('window.__paylasilan') or {}
        kontrol('Oda 520' in (pv.get('text') or '') and 'Ayşe Kaya' in pv.get('text', '') and 'oda listesi' in (pv.get('title') or ''), 'Rehber: "Listeyi paylaş" telefonun paylaş menüsünü oda listesiyle açıyor', pv)
        kontrol(rp.locator('#odaGirBtn').count() == 1, 'Rehber: "Oda numaralarını gir" butonu var')
        rp.evaluate("KT.liste.forEach(x => x.kat.odalar = {}); window.__paylasilan = null"); rp.get_by_role('button', name=re.compile('Listeyi paylaş')).click(); rp.wait_for_timeout(200)
        pt = (rp.evaluate('window.__paylasilan') or {}).get('text', '')
        kontrol('katılımcı listesi' in pt and '\n1. Ayşe Kaya' in pt and 'Oda numaraları henüz belli değil' in pt and '🏨' not in pt, 'Rehber: oda girilmemişse paylaşılan metin sade numaralı isim listesi', pt)
        kontrol(rp.evaluate('document.documentElement.scrollWidth') <= vp['width'] + 1, 'Rehber: sayfa yana taşmıyor')
        kontrol(not rp.is_visible('.mobil-alt'), 'Rehber: alt sekme çubuğu yok (tek ekranı var)')
        kontrol(rp.locator('.anket-btn').count() == 0, 'Rehber: anket sonuçları butonu yok')
        rp.evaluate("sekmeAc('kafile')"); rp.wait_for_timeout(400)
        kontrol(rp.get_by_text('Çıkış', exact=False).locator('visible=true').count() == 1, 'Rehber: tek bir "Çıkış" var (menüde tekrar yok)')
        kontrol(rp.evaluate("getComputedStyle(document.querySelector('.rehber-paylas')).textAlign") == 'center', 'Rehber: "Misafir kodunu paylaş" yazısı ortalı')
        rp.close()
    b.close()

print('\n=== ADMIN TESTİ:', 'TEMİZ' if not hata else f'{hata} SORUN')
sys.exit(1 if hata else 0)
