/* Çerez bildirimi ve onaya bağlı Google Analytics
   - Onay verilmeden Google Analytics yüklenmez.
   - Tercih tarayıcıda saklanır; footer'daki "Çerez Tercihleri" ile değiştirilebilir. */
(function () {
  var GA_ID = 'G-M69P1Q6LZR';
  var ANAHTAR = 'cerez-tercihi';

  function oku() { try { return localStorage.getItem(ANAHTAR); } catch (e) { return null; } }
  function yaz(v) { try { localStorage.setItem(ANAHTAR, v); } catch (e) {} }

  function gaYukle() {
    if (window.__gaYuklendi) return;
    window.__gaYuklendi = true;
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    gtag('js', new Date());
    gtag('config', GA_ID);
  }

  function gaCerezleriniSil() {
    document.cookie.split(';').forEach(function (c) {
      var ad = c.split('=')[0].trim();
      if (ad.indexOf('_ga') !== 0) return;
      var host = location.hostname, parcalar = host.split('.');
      var alanlar = ['', host, '.' + host];
      for (var i = 1; i < parcalar.length - 1; i++) alanlar.push('.' + parcalar.slice(i).join('.'));
      alanlar.forEach(function (d) {
        document.cookie = ad + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/' + (d ? '; domain=' + d : '');
      });
    });
  }

  var css = ''
    + '#cerezBant{position:fixed;left:16px;right:16px;bottom:16px;z-index:9000;max-width:760px;margin:0 auto;background:#0B1F3A;color:#fff;border:1px solid rgba(201,151,43,.35);border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.35);padding:18px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap;font-size:13.5px;line-height:1.55}'
    + '#cerezBant p{flex:1 1 320px;margin:0;color:rgba(255,255,255,.85)}'
    + '#cerezBant a{color:#E8C46A;text-decoration:underline}'
    + '#cerezBant .cb-btns{display:flex;gap:8px;flex:0 0 auto}'
    + '#cerezBant button{padding:10px 18px;border-radius:8px;font-size:13.5px;font-weight:700;cursor:pointer;font-family:inherit;min-width:104px}'
    + '#cerezBant .cb-red{background:transparent;color:#fff;border:1.5px solid rgba(255,255,255,.55)}'
    + '#cerezBant .cb-kabul{background:#C9972B;color:#0B1F3A;border:1.5px solid #C9972B}'
    + '@media(max-width:520px){#cerezBant .cb-btns{width:100%}#cerezBant button{flex:1}}';

  function bantGoster() {
    if (document.getElementById('cerezBant')) return;
    if (!document.getElementById('cerezStil')) {
      var st = document.createElement('style'); st.id = 'cerezStil'; st.textContent = css; document.head.appendChild(st);
    }
    var b = document.createElement('div');
    b.id = 'cerezBant';
    b.setAttribute('role', 'dialog');
    b.setAttribute('aria-label', 'Çerez bildirimi');
    b.innerHTML = '<p>🍪 Sitemizi nasıl kullandığınızı anlamak için Google Analytics çerezlerini kullanmak istiyoruz. Bu çerezler zorunlu değildir ve yalnızca onay verirseniz çalışır. Ayrıntılar için <a href="kvkk.html#cerez">Çerez Politikası</a>.</p>'
      + '<div class="cb-btns"><button type="button" class="cb-red">Reddet</button><button type="button" class="cb-kabul">Kabul Et</button></div>';
    document.body.appendChild(b);
    b.querySelector('.cb-kabul').onclick = function () { yaz('kabul'); b.remove(); gaYukle(); };
    b.querySelector('.cb-red').onclick = function () {
      var onceKabul = oku() === 'kabul';
      yaz('red'); b.remove(); gaCerezleriniSil();
      if (onceKabul && window.__gaYuklendi) location.reload();
    };
  }

  window.cerezAyarlari = bantGoster;

  var t = oku();
  if (t === 'kabul') gaYukle();
  else if (t !== 'red') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bantGoster); else bantGoster();
  }
})();
