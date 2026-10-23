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
        if (mod === 'insert') { var liste = Array.isArray(yuk) ? yuk : [yuk]; liste.forEach(function(x){ tum.push(JSON.parse(JSON.stringify(x))); }); window.__islem.push({tablo: t, tur: 'insert', veri: yuk}); }
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
    for sekme in ['basvuru', 'turlar', 'ekle', 'duyuru']:
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

    # Sil onayla çalışıyor
    pg.evaluate("sekmeAc('turlar')"); pg.wait_for_timeout(400)
    pg.evaluate("window.__islem = []"); son = VERI['turlar'][-1]['id']
    pg.evaluate(f"turSil('{son}')"); pg.wait_for_timeout(400)
    s = [i for i in pg.evaluate('window.__islem') if i['tur'] == 'delete']
    kontrol(len(s) == 1 and s[0]['filtre'] == [['id', son]], 'Sil yalnızca seçilen turu siler', errs)
    b.close()

print('\n=== ADMIN TESTİ:', 'TEMİZ' if not hata else f'{hata} SORUN')
sys.exit(1 if hata else 0)
