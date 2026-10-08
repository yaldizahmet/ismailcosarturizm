"""Sitedeki tüm bağlantı ve butonları tarar. Kullanım: python3 _test/tara.py [sayfa-filtresi ...]
Önce repo kökünde: python3 -m http.server 8765"""
import json, re, os, sys
from urllib.parse import urlparse, unquote
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE = 'http://localhost:8765/'
DB = open(os.path.join(HERE, 'db.json'), encoding='utf-8').read()
MOCK = 'window.__DB=' + DB + ';\n' + open(os.path.join(HERE, 'mock.js'), encoding='utf-8').read()
PAGES = ['index.html', 'umre.html', 'hac.html', 'turlar.html', 'tur-detay.html?id=umre-kasim', 'tur-detay.html?id=balkanlar-2025',
         'sss.html', 'iletisim.html', 'galeri.html', 'hakkimizda.html', 'belgelerimiz.html', 'kvkk.html', 'tesekkurler.html']
ONLY = sys.argv[1:] or None

ids_cache = {}
def ids_of(fn):
    if fn not in ids_cache:
        try: ids_cache[fn] = set(re.findall(r'\bid="([^"]+)"', open(os.path.join(ROOT, fn), encoding='utf-8').read()))
        except FileNotFoundError: ids_cache[fn] = None
    return ids_cache[fn]

INIT = """
try{localStorage.setItem('cerez-tercihi','red'); sessionStorage.setItem('ca-ipucu','1');}catch(e){}
window.__acilan=[]; window.open=function(u){window.__acilan.push(String(u));return null};
window.__mut=0; new MutationObserver(function(){window.__mut++}).observe(document,{subtree:true,childList:true,attributes:true,characterData:true});
window.alert=function(m){window.__acilan.push('ALERT:'+m)}; window.confirm=function(){return false};
"""
JS_KEYWORDS = set('if for while return function typeof new switch catch void this document window event alert confirm encodeURIComponent decodeURIComponent setTimeout clearTimeout parseInt parseFloat String Number Boolean Array Object JSON Math Date Promise console location history'.split())

def kur(pg, errs):
    pg.on('pageerror', lambda e: errs.append(str(e)[:160]))
    pg.route('**cdn.jsdelivr.net/npm/@supabase/**', lambda r, q: r.fulfill(status=200, body=MOCK, headers={'content-type': 'application/javascript'}))
    pg.route('**/rest/v1/**', lambda r, q: r.fulfill(status=201 if q.method == 'POST' else 200, body='' if q.method == 'POST' else '[]', headers={'content-type': 'application/json', 'access-control-allow-origin': '*'}))
    pg.route('https://api.web3forms.com/**', lambda r, q: r.fulfill(status=200, body='{"success":true}', headers={'content-type': 'application/json', 'access-control-allow-origin': '*'}))
    pg.route(re.compile(r'^https?://(?!localhost)'), lambda r, q: r.abort() if not ('jsdelivr' in q.url or 'web3forms' in q.url or 'supabase' in q.url) else r.fallback())
    pg.add_init_script(INIT)

sorunlar = []
def sorun(sayfa, tur, ayrinti):
    sorunlar.append((sayfa, tur, ayrinti)); print(f'  ✗ [{tur}] {ayrinti}')

with sync_playwright() as p:
    b = p.chromium.launch()
    for sayfa in PAGES:
        if ONLY and not any(o in sayfa for o in ONLY): continue
        dosya = sayfa.split('?')[0]
        for vp_ad, vp in [('masaüstü', {'width': 1300, 'height': 900}), ('mobil', {'width': 390, 'height': 820})]:
            print(f'== {sayfa} ({vp_ad})')
            pg = b.new_page(viewport=vp); errs = []; kur(pg, errs)
            pg.goto(BASE + sayfa, wait_until='domcontentloaded'); pg.wait_for_timeout(1300)
            if errs: sorun(sayfa, 'yükleme hatası', '; '.join(errs))
            # --- Bağlantılar (yalnız masaüstünde, statik) ---
            if vp_ad == 'masaüstü':
                linkler = pg.eval_on_selector_all('a[href]', 'els=>els.map(e=>[e.getAttribute("href"),(e.innerText||e.getAttribute("aria-label")||"").trim().slice(0,40)])')
                for href, metin in linkler:
                    if href.startswith(('http://', 'https://')):
                        u = urlparse(href)
                        if 'ismailcosarturizm' in u.netloc:
                            yol = u.path.lstrip('/') or 'index.html'
                            if ids_of(yol) is None: sorun(sayfa, 'kırık bağlantı', f'{href} ({metin})')
                        if 'wa.me' in href and not re.match(r'https://wa\.me/90\d{10}', href): sorun(sayfa, 'WhatsApp bağlantısı', href)
                        continue
                    if href.startswith('tel:'):
                        if re.sub(r'\D', '', href) not in ('905331980781', '05331980781'): sorun(sayfa, 'telefon', href)
                        continue
                    if href.startswith('mailto:'):
                        if 'ismailcosarturizm@gmail.com' not in href: sorun(sayfa, 'e-posta', href)
                        continue
                    if href.startswith('javascript:') or href == '#': continue
                    yol, _, capa = href.partition('#')
                    yol = unquote(yol.split('?')[0]) or dosya
                    idler = ids_of(yol)
                    if idler is None: sorun(sayfa, 'kırık bağlantı', f'{href} ({metin})'); continue
                    if capa and capa not in idler:
                        dinamik = yol == dosya and pg.query_selector('[id="%s"]' % capa)
                        if not dinamik and not (yol == 'sss.html' and capa.startswith('soru-')):
                            sorun(sayfa, 'kırık çapa', f'{href} ({metin})')
                # --- onclick vb. içindeki fonksiyonlar tanımlı mı ---
                olaylar = pg.eval_on_selector_all('[onclick],[onsubmit],[oninput],[onchange],[onkeydown],[onkeyup]', 'els=>els.flatMap(e=>["onclick","onsubmit","oninput","onchange","onkeydown","onkeyup"].filter(a=>e.hasAttribute(a)).map(a=>e.getAttribute(a)))')
                adlar = set()
                for kod in olaylar:
                    kod = re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", "''", kod)
                    for m in re.finditer(r'(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(', kod):
                        if m.group(1) not in JS_KEYWORDS: adlar.add(m.group(1))
                for ad in sorted(adlar):
                    if pg.evaluate(f'typeof window["{ad}"]') != 'function': sorun(sayfa, 'tanımsız fonksiyon', f'{ad}()')
            pg.close()
            # --- Tıklama testi: her görünür buton, her seferinde temiz sayfada ---
            SEC = 'button:not([type=submit]):not([disabled]),[onclick]:not(a[href]:not([href="#"])),a[href="#"]'
            pg = b.new_page(viewport=vp); errs = []; kur(pg, errs)
            pg.goto(BASE + sayfa, wait_until='domcontentloaded'); pg.wait_for_timeout(1100)
            n = pg.eval_on_selector_all(SEC, 'els=>els.length')
            HIT = """e=>{const r=e.getBoundingClientRect(); if(!r.width||!r.height) return false;
              e.scrollIntoView({block:'center'}); const q=e.getBoundingClientRect();
              const t=document.elementFromPoint(q.x+q.width/2,q.y+q.height/2); if(!t) return false;
              let x=e; while(x){ if(getComputedStyle(x).pointerEvents==='none'||getComputedStyle(x).opacity==='0'||getComputedStyle(x).visibility==='hidden') return false; x=x.parentElement;}
              return e.contains(t)||t.contains(e) ? true : 'kapali:'+(t.id||t.className||t.tagName)}"""
            for i in range(n):
                if i:
                    pg.goto(BASE + sayfa, wait_until='domcontentloaded'); pg.wait_for_timeout(900)
                el = pg.query_selector_all(SEC)
                if i >= len(el): break
                e = el[i]
                if not e.is_visible(): continue
                h = e.evaluate(HIT)
                if h is False: continue
                etiket = (e.inner_text() or e.get_attribute('aria-label') or e.get_attribute('id') or '').strip().replace('\n', ' ')[:45]
                if h is not True:
                    sorun(sayfa, f'üstü kapalı ({vp_ad})', f'"{etiket}" -> {h}'); continue
                def dene():
                    pg.goto(BASE + sayfa, wait_until='networkidle'); pg.wait_for_timeout(500)
                    x = pg.query_selector_all(SEC)[i]
                    x.scroll_into_view_if_needed(); pg.wait_for_timeout(250)
                    u0 = pg.url; errs.clear(); pg.evaluate('window.__mut=0;window.__acilan=[]')
                    try:
                        x.click(timeout=4000)
                    except Exception as ex:
                        return ('tıklanamıyor', str(ex).splitlines()[0][:90])
                    pg.wait_for_timeout(500)
                    if errs: return ('tıklama hatası', '; '.join(errs))
                    if not (pg.evaluate('window.__mut') > 0 or pg.url != u0 or pg.evaluate('window.__acilan.length') > 0):
                        return ('etkisiz buton', '')
                    return None
                # Şüpheli sonuç yeniden denenir; iki denemede de aynı sorun çıkarsa raporlanır (zamanlama kaynaklı yanlış alarmları eler)
                sonuc = dene()
                if sonuc: sonuc = dene()
                if sonuc:
                    sorun(sayfa, f'{sonuc[0]} ({vp_ad})', f'"{etiket}"' + (f': {sonuc[1]}' if sonuc[1] else ''))
            pg.close()
    b.close()

print('\n=== ÖZET:', len(sorunlar), 'sorun')
for s in sorted(set(sorunlar)): print(' -', *s)
