"""Başvuru formlarını ve 'Kayıt Ol' pencerelerini uçtan uca test eder.
Her form: alanlar doldurulur, gönderilir; veritabanına kayıt + mail isteği + başarı mesajı beklenir.
Ayrıca kesme işareti/tırnak içeren tur başlıklarıyla 'Kayıt Ol' butonlarının çalıştığı kontrol edilir.
Kullanım: önce repo kökünde `python3 -m http.server 8765`, sonra `python3 _test/formlar.py`."""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = sys.argv[:1] + ['__hicbiri__']
exec(open(os.path.join(HERE, 'tara.py'), encoding='utf-8').read().split('sorunlar = []')[0])

db = json.loads(DB)
for t in db['turlar']:
    if t['id'] in ('umre-kasim', 'hac-ekonomi', 'balkanlar-2025'):
        t['baslik'] = "Ramazan'da \"Özel\" Program – " + t['kategori']
MOCK2 = 'window.__DB=' + json.dumps(db, ensure_ascii=False) + ';\n' + open(os.path.join(HERE, 'mock.js'), encoding='utf-8').read()

DOLDUR = """f=>{for(const i of f.querySelectorAll('input,select,textarea')){const t=(i.type||'').toLowerCase(),n=i.name||'';
 if(t==='hidden'||t==='submit'||n==='bot-field')continue;
 if(t==='checkbox'){i.checked=true;continue}
 if(i.tagName==='SELECT'){const o=[...i.options].find(o=>o.value);if(o)i.value=o.value;continue}
 if(t==='email')i.value='test@example.com';else if(t==='tel'||/tel/.test(n))i.value='05330000000';else if(t==='date')i.value='2027-01-01';else i.value='Test Kişi';}
 const b=f.querySelector('button[type=submit],.form-submit,.kayit-submit,button:not([type=button])')||f.parentElement.querySelector('.form-submit'); b.click(); return b.innerText.trim().slice(0,30)}"""

hata = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for sayfa, sec in [('index.html', '#toursGrid .btn-tur'), ('umre.html', '.btn-prog:not([disabled])'), ('hac.html', '#paketGrid button'), ('tur-detay.html?id=balkanlar-2025', '.btn-kayit')]:
        pg = b.new_page(); errs = []; kur(pg, errs)
        pg.route('**cdn.jsdelivr.net/npm/@supabase/**', lambda r, q: r.fulfill(status=200, body=MOCK2, headers={'content-type': 'application/javascript'}))
        pg.goto(BASE + sayfa, wait_until='domcontentloaded'); pg.wait_for_timeout(1200)
        bt = [x for x in pg.query_selector_all(sec) if 'Ramazan' in (x.get_attribute('onclick') or '')]
        ad = ''
        if bt:
            bt[0].click(); pg.wait_for_timeout(400)
            ad = pg.evaluate("(document.querySelector('#kayitProgramAdi,.kayit-program-info')||{}).innerText||''")
        ok = 'Ramazan\'da "Özel"' in ad and not errs
        hata += not ok
        print('✓' if ok else '✗', 'KESME İŞARETİ', sayfa, '->', ad or '(buton yok)', errs)
        pg.close()
    for sayfa, acici, secici in [('index.html', None, '#contactForm'), ('index.html', "kayitModalAc('Test')", '#kayitForm form'),
                                 ('umre.html', "kayitModalAc('Test')", '#kayitForm form'), ('hac.html', "kayitModalAc('Test')", '#kayitModalBg form'),
                                 ('tur-detay.html?id=umre-kasim', "kayitModalAc('Test')", 'form[name=tur-kayit]'), ('iletisim.html', None, '#contactForm, form')]:
        pg = b.new_page(); errs = []; kur(pg, errs); posts = []; mails = []
        pg.route('**/rest/v1/basvurular**', lambda r, q: (posts.append(json.loads(q.post_data)), r.fulfill(status=201, body='', headers={'access-control-allow-origin': '*'})))
        pg.route('https://api.web3forms.com/**', lambda r, q: (mails.append(1), r.fulfill(status=200, body='{"success":true}', headers={'content-type': 'application/json', 'access-control-allow-origin': '*'})))
        pg.goto(BASE + sayfa, wait_until='domcontentloaded'); pg.wait_for_timeout(1100)
        if acici: pg.evaluate(acici); pg.wait_for_timeout(300)
        f = pg.query_selector(secici)
        if not f:
            hata += 1; print('✗ FORM', sayfa, 'form bulunamadı:', secici); pg.close(); continue
        f.evaluate(DOLDUR); pg.wait_for_timeout(1200)
        basari = pg.evaluate("[...document.querySelectorAll('[id*=uccess],[class*=uccess]')].some(e=>e.offsetParent!==null&&getComputedStyle(e).display!=='none')") or 'tesekkur' in pg.url
        ok = len(posts) == 1 and len(mails) == 1 and basari and not errs and (not acici or posts[0].get('program') == 'Test')
        hata += not ok
        print('✓' if ok else '✗', 'FORM', sayfa, acici or '(sayfa formu)', '-> veritabanı:', len(posts), 'mail:', len(mails), 'başarı mesajı:', basari, errs)
        pg.close()
    b.close()
print('\n=== FORM TESTİ:', 'TEMİZ' if not hata else f'{hata} SORUN')
sys.exit(1 if hata else 0)
