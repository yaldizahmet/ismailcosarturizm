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

    # Bütün sekmeler hatasız açılıyor
    kontrol(pg.is_visible('#sayfa-ana') and not pg.is_visible('#sayfa-basvuru') and 'Grup Yönetimi' in pg.inner_text('#sayfa-ana') and 'Site Yönetimi' in pg.inner_text('#sayfa-ana'),
            'Girişte Ana Sayfa açılıyor (Başvurular değil); Grup Yönetimi ve Site Yönetimi bölümleri var', errs)
    basliklar = pg.locator('.sidebar .nav-baslik, .sidebar .nav-item').evaluate_all("l => l.map(e => e.id || e.textContent.trim())")
    kontrol(basliklar[:6] == ['btn-ana', 'Grup Yönetimi', 'btn-kafile', 'btn-musteri', 'btn-rehber', 'btn-sehir'] and basliklar[6:12] == ['Site Yönetimi', 'btn-basvuru', 'btn-turlar', 'btn-ekle', 'btn-duyuru', 'btn-yorum'],
            'Menü gruplu: Grup Yönetimi (Gruplar, Müşteriler, Rehber) ve Site Yönetimi (Başvurular, Turlar, Duyurular, Yorumlar)', basliklar)
    pg.locator('#sayfa-ana button', has_text='Müşteriler').click(); pg.wait_for_timeout(300)
    kontrol(pg.is_visible('#sayfa-musteri'), 'Ana Sayfa: kutucuğa basınca ilgili sekme açılıyor')
    for sekme in ['ana', 'basvuru', 'turlar', 'ekle', 'duyuru', 'kafile', 'yorum', 'musteri', 'rehber', 'sehir']:
        errs.clear(); pg.evaluate(f"sekmeAc('{sekme}')"); pg.wait_for_timeout(400)
        kontrol(pg.is_visible(f'#sayfa-{sekme}') and not errs, f'Sekme açılıyor: {sekme}', errs)

    # Tur listesi
    pg.evaluate("sekmeAc('turlar')"); pg.wait_for_timeout(400)
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
    pg.evaluate("window.__islem = []"); errs.clear()
    pg.get_by_role('button', name=re.compile('Yeni Grup')).click(); pg.wait_for_timeout(300)
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
            and v.get('inis_sehri') == 'Cidde' and v.get('yorum_link') == 'https://g.page/r/ABC/review' and v.get('donus_sehri') == 'Medine' and v['oteller'][0].get('giris') == '2026-11-10' and v['oteller'][0].get('cikis') == '2026-11-15',
            'Kafile: yeni kafile kaydediliyor (boş satır/otel atlanıyor, program tarih+saate göre sıralı)', errs)
    kontrol(pg.locator('.kafile-item').count() == 1 and kod in pg.inner_text('#sayfa-kafile') and pg.inner_text('.kafile-item .abone-sayisi') == '0', 'Kafile: listede görünüyor (bildirim açık telefon sayısıyla)')
    href = pg.locator('.kafile-item a', has_text='Paylaş').get_attribute('href') or ''
    kontrol('kafile%2F%23' + kod in href, 'Kafile: Paylaş bağlantısı kodlu uygulama adresini içeriyor')
    pg.evaluate("window.__islem = []")
    pg.locator('.kafile-item').get_by_role('button', name='Düzenle').click(); pg.wait_for_timeout(300)
    kontrol(pg.locator('#k_program .prog-satir').count() == 2 and pg.input_value('#k_rehber_ad') == "Ali O'Hoca" and pg.input_value('#k_tur_turu') == 'kultur' and pg.input_value('#k_acil_tel') == '112', 'Kafile: düzenleme formu kayıtlı bilgilerle açılıyor')
    pg.fill('#k_ad', 'Kasım 2026 Umre Kafilesi (güncel)'); pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(400)
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
    pg.fill('#kt_yapistir', "Ad Soyad\tTelefon\tDoğum tarihi\tOda\nMehmet Kaya\t0532 111 22 33\t12.03.1955\t512\t3\nAyşe Kaya\t0533 444 55 66\t\t512\nHasan <b>Ç</b>\t\t31.02.1950\t514\t2 kişilik\n\n")
    pg.get_by_role('button', name=re.compile('Önizle')).click(); pg.wait_for_timeout(200)
    o = pg.inner_text('#kt_onizleme')
    kontrol(pg.locator('.onizleme-tablo tbody tr').count() == 3 and 'Zaten listede' in o and 'Tarih okunamadı' in o and '12.03.1955' in o and '2 kişiyi ekle' in o,
            'Excel yapıştırma: başlık atlanıyor, tarih okunuyor, listede olan ve hatalı tarih işaretleniyor', o.replace('\n', ' | ')[:160])
    pg.get_by_role('button', name=re.compile('kişiyi ekle')).click(); pg.wait_for_timeout(500)
    isl = pg.evaluate('window.__islem'); mi = [i for i in isl if i['tablo'] == 'musteriler' and i['tur'] == 'insert']; ki = [i for i in isl if i['tablo'] == 'kafile_katilimcilar' and i['tur'] == 'insert']
    kontrol(len(mi) == 1 and len(mi[0]['veri']) == 2 and {m['ad'] for m in mi[0]['veri']} == {'Mehmet Kaya', 'Hasan <b>Ç</b>'} and len(ki) == 1 and len(ki[0]['veri']) == 2
            and next(m for m in mi[0]['veri'] if m['ad'] == 'Mehmet Kaya')['dogum_tarihi'] == '1955-03-12' and pg.locator('.katilimci-satir').count() == 3,
            'Excel yapıştırma: 2 yeni kişi tek seferde ekleniyor', errs)
    kontrol(pg.locator('.katilimci-tablo b b').count() == 0 and '<b>Ç</b>' in pg.inner_text('.katilimci-tablo'), 'Güvenlik: isimdeki HTML düz yazı gösteriliyor')
    pg.get_by_role('button', name=re.compile('Oda listesini kopyala')).click(); pg.wait_for_timeout(200)
    t = pg.evaluate('window.__sonKopya') or ''
    kontrol( '🏨 Mekke – Test Otel Mekke (10.11–15.11, 5 gece)' in t and 'Oda 512 (3 kişilik): Ayşe Kaya [11.11–15.11, 4 gece], Mehmet Kaya' in t and 'Oda 514 (2 kişilik): Hasan <b>Ç</b>' in t, 'Oda listesi: odaya göre gruplu metin kopyalanıyor', t.replace('\n', ' | ')[:160])
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
    rid = pg.get_attribute('.rehber-item', 'data-user')
    pg.locator('.rehber-item .rh_kafile').first.check(); pg.wait_for_timeout(300)
    ek = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'kafile_rehberleri' and i['tur'] == 'insert']
    kontrol(len(ek) == 1 and ek[0]['veri']['user_id'] == rid and ek[0]['veri']['kafile_id'], 'Rehber hesabı: kafile işaretlenince rehbere atanıyor')
    pg.evaluate("window.__islem = []"); pg.locator('.rehber-item .rh_kafile').first.uncheck(); pg.wait_for_timeout(300)
    sl = [i for i in pg.evaluate('window.__islem') if i['tablo'] == 'kafile_rehberleri' and i['tur'] == 'delete']
    kontrol(len(sl) == 1 and ['user_id', rid] in sl[0]['filtre'] and len(sl[0]['filtre']) == 2, 'Rehber hesabı: işaret kaldırılınca yalnızca o atama siliniyor')
    pg.evaluate("window.__fn = []"); pg.fill('.rehber-item .rh_yeni_sifre', 'yenisifre99'); pg.get_by_role('button', name='Şifreyi değiştir').click(); pg.wait_for_timeout(300)
    fn = pg.evaluate('window.__fn')
    kontrol(len(fn) == 1 and fn[0]['govde'] == {'islem': 'sifre', 'user_id': rid, 'sifre': 'yenisifre99'} and pg.input_value('.rehber-item .rh_yeni_sifre') == '', 'Rehber hesabı: şifre değiştiriliyor')
    pg.evaluate("window.__fn = []"); pg.get_by_role('button', name='Hesabı sil').click(); pg.wait_for_timeout(400)
    fn = pg.evaluate('window.__fn')
    kontrol(len(fn) == 1 and fn[0]['govde'] == {'islem': 'sil', 'user_id': rid} and pg.locator('.rehber-item').count() == 0 and not errs, 'Rehber hesabı: siliniyor', errs)

    # ── Şehir rehberi ──
    pg.evaluate("""window.__DB.sehir_rehberi = [
      { id: 501, sehir: 'Saraybosna', diger_adlar: ['Sarajevo'], tur: 'gezi', ad: 'Sarı Tabya', aciklama: 'Manzara', harita: 'https://www.google.com/maps/search/?api=1&query=x', sira: 100, yayinda: false },
      { id: 502, sehir: 'Saraybosna', diger_adlar: ['Sarajevo'], tur: 'yemek', ad: '<b>Željo</b>', aciklama: '', harita: null, sira: 90, yayinda: false },
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
    for sekme, ek in [('basvuru', ''), ('turlar', ''), ('ekle', ''), ('duyuru', ''), ('kafile', ''), ('yorum', ''), ('yorum', 'yorumYeni()'), ('kafile', 'kafileYeni()'), ('turlar', f"turDuzenle('{VERI['turlar'][1]['id']}')")]:
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
        gorunen = [x for x in ['ana', 'basvuru', 'turlar', 'ekle', 'duyuru', 'yorum', 'musteri', 'rehber', 'sehir'] if rp.is_visible('#btn-' + x)] + (['başlık'] if rp.locator('.nav-baslik:visible').count() else [])
        kontrol(rp.is_visible('#appDiv') and not gorunen and 'Gruplarım' in rp.inner_text('#btn-kafile'), f'Rehber ({vp["width"]}px): menüde yalnızca "Gruplarım" var', gorunen or errs)
        rp.evaluate("sekmeAc('basvuru')"); rp.wait_for_timeout(300)
        kontrol(rp.is_visible('#sayfa-kafile') and not rp.is_visible('#sayfa-basvuru'), 'Rehber: başka sekmeye geçemiyor')
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
        kontrol(rp.evaluate('document.documentElement.scrollWidth') <= vp['width'] + 1, 'Rehber: sayfa yana taşmıyor')
        rp.close()
    b.close()

print('\n=== ADMIN TESTİ:', 'TEMİZ' if not hata else f'{hata} SORUN')
sys.exit(1 if hata else 0)
