"""Admin panelini (admin.html) uçtan uca test eder; gerçek veritabanına dokunmaz.
Oturum açılmış gibi davranan sahte bir Supabase kullanılır; yapılan ekle/güncelle/sil işlemleri kaydedilip kontrol edilir.
Kullanım: önce repo kökünde `python3 -m http.server 8765`, sonra `python3 _test/admin.py`."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 'http://localhost:8765/'
VERI = json.load(open(os.path.join(HERE, 'db.json'), encoding='utf-8'))

SAHTE = 'window.__DB=' + json.dumps(VERI, ensure_ascii=False) + r''';
window.__islem = [];
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
        if (mod === 'insert') { var liste = Array.isArray(yuk) ? yuk : [yuk]; liste.forEach(function(x){ var y = JSON.parse(JSON.stringify(x)); if (y.id == null) { window.__sayac = (window.__sayac || 1000) + 1; y.id = t === 'kafile_duyurular' ? window.__sayac : 'uuid-' + window.__sayac; } /* gerçek DB: kafile uuid (metin), duyuru bigint */ if (!y.olusturma) y.olusturma = new Date().toISOString(); tum.push(y); }); window.__islem.push({tablo: t, tur: 'insert', veri: yuk}); }
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
    auth: { getSession: function(){ return Promise.resolve({ data: { session: { user: { email: 'test@test' } } } }); },
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
    for sekme in ['basvuru', 'turlar', 'ekle', 'duyuru', 'kafile']:
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
    pg.get_by_role('button', name=re.compile('Yeni Kafile')).click(); pg.wait_for_timeout(300)
    kontrol(re.fullmatch(r'KAFILE-[A-Z2-9]{5}', pg.input_value('#k_kod')) is not None, 'Kafile: yeni formda otomatik kod üretiliyor', pg.input_value('#k_kod'))
    pg.get_by_role('button', name=re.compile('Kaydet')).click(); pg.wait_for_timeout(300)
    kontrol(not [i for i in pg.evaluate('window.__islem') if i['tur'] == 'insert'], 'Kafile: adı boşken kaydetmiyor')
    pg.fill('#k_ad', 'Kasım 2026 Umre Kafilesi'); pg.get_by_role('button', name='Yeni kod').click()
    kod = pg.input_value('#k_kod')
    pg.fill('#k_baslangic', '2026-11-10'); pg.fill('#k_bitis', '2026-11-23')
    pg.fill('#k_rehber_ad', "Ali O'Hoca"); pg.fill('#k_rehber_tel', '0533 000 00 00')
    pg.locator('.o_ad').first.fill('Test Otel Mekke')
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
            and [p['baslik'] for p in v.get('program', [])] == ['Kahvaltı', 'Mekke ziyaretleri'] and v.get('rehber_ad') == "Ali O'Hoca" and v.get('tur_turu') == 'kultur' and v.get('acil_tel') == '112',
            'Kafile: yeni kafile kaydediliyor (boş satır/otel atlanıyor, program tarih+saate göre sıralı)', errs)
    kontrol(pg.locator('.kafile-item').count() == 1 and kod in pg.inner_text('#sayfa-kafile'), 'Kafile: listede görünüyor')
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
    kontrol(len(ek) == 1 and ek[0]['veri']['onemli'] is True and ek[0]['veri']['kafile_id'] is not None and pg.locator('.kafile-duyuru').count() == 1,
            'Kafile duyurusu: yayınlanıyor ve listede görünüyor', errs)
    pg.evaluate("window.__islem = []")
    pg.locator('.kafile-duyuru').get_by_role('button', name='Sil').click(); pg.wait_for_timeout(400)
    s_ = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'delete']
    kontrol(len(s_) == 1 and s_[0]['tablo'] == 'kafile_duyurular' and pg.locator('.kafile-duyuru').count() == 0, 'Kafile duyurusu: siliniyor', errs)
    pg.get_by_role('button', name=re.compile('Kafileler')).first.click(); pg.wait_for_timeout(400)
    pg.evaluate("window.__islem = []")
    pg.locator('.kafile-item').get_by_role('button', name='Sil').click(); pg.wait_for_timeout(400)
    s_ = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'delete']
    kontrol(len(s_) == 1 and s_[0]['tablo'] == 'kafileler' and pg.locator('.kafile-item').count() == 0, 'Kafile: siliniyor', errs)

    # Sil onayla çalışıyor
    pg.evaluate("sekmeAc('turlar')"); pg.wait_for_timeout(400)
    pg.evaluate("window.__islem = []"); son = VERI['turlar'][-1]['id']
    pg.evaluate(f"turSil('{son}')"); pg.wait_for_timeout(400)
    s = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'delete']
    kontrol(len(s) == 1 and s[0]['filtre'] == [['id', son]], 'Sil yalnızca seçilen turu siler', errs)
    b.close()

print('\n=== ADMIN TESTİ:', 'TEMİZ' if not hata else f'{hata} SORUN')
sys.exit(1 if hata else 0)
