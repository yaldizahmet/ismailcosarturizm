/* Yolculardan gelen mesajlar (admin panelindeki "Yorumlar" sekmesinden eklenir).
   Az yer kaplasın diye tek satırlık, yana kaydırılan bir şerit olarak gösterilir:
     #yorumGrid           (ana sayfa: Google yorumlarının hemen üstüne şerit eklenir)
     #yolcuMesajlari      (Umre sayfası: data-kategori="umre" ile süzülür; yorum yoksa gizli kalır)
   Hata olursa sessizce hiçbir şey yapmaz; sayfanın geri kalanını asla etkilemez. */
(function () {
  var SB = 'https://wpkjxwbvewwgdclbsdya.supabase.co', K = 'sb_publishable_bEXKjIeKKN4JrMkOPy3LQg_ZuSlEQNK';
  var GORSEL_ON = SB + '/storage/v1/object/public/';
  var RENK = ['#e8f5e9', '#e3f2fd', '#fff3e0', '#fce4ec', '#f3e5f5', '#e0f7fa', '#fff8e1', '#e8eaf6'];
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  var WA = '<svg width="11" height="11" viewBox="0 0 24 24" fill="#25D366" aria-hidden="true"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm5.3 14.1c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .1-3.2-.7-2.7-1.1-4.4-3.9-4.6-4.1-.1-.2-1.1-1.5-1.1-2.8s.7-2 .9-2.3c.3-.3.6-.3.8-.3h.6c.2 0 .4 0 .6.5l.8 2c.1.2.1.4 0 .5l-.3.5-.4.4c-.1.1-.3.3-.1.6.2.3.7 1.2 1.6 2 1.1 1 2 1.3 2.3 1.4.3.1.4.1.6-.1l.8-1c.2-.2.4-.2.6-.1l1.9.9c.3.1.4.2.5.3.1.2.1.7-.1 1.3z"/></svg>';

  function stil() {
    if (document.getElementById('yolcuMesajStil')) return;
    var s = document.createElement('style'); s.id = 'yolcuMesajStil';
    s.textContent =
      '.ym-baslik{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin:0 0 10px;font-size:13px;font-weight:700;color:var(--navy,#0B1F3A)}' +
      '.ym-baslik span{font-size:12px;font-weight:500;color:var(--text-muted,#6b7a94)}' +
      '.ym-serit{display:flex;gap:14px;overflow-x:auto;scroll-snap-type:x mandatory;padding:2px 2px 12px;margin-bottom:28px;-webkit-overflow-scrolling:touch;scrollbar-width:thin}' +
      '.yolcu-mesaji{flex:0 0 280px;max-width:82vw;scroll-snap-align:start;background:#fff;border-radius:18px;border:1px solid rgba(201,151,43,.25);padding:16px 18px;display:flex;flex-direction:column;gap:6px;box-sizing:border-box}' +
      '.ym-ust{display:flex;align-items:center;gap:10px}' +
      '.ym-harf{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:var(--navy,#0B1F3A);flex-shrink:0}' +
      '.ym-resim{margin-left:auto;width:52px;height:52px;border-radius:10px;overflow:hidden;border:1px solid #eee;padding:0;background:#f5f5f5;cursor:zoom-in;flex-shrink:0}' +
      '.ym-resim img{width:100%;height:100%;object-fit:cover;display:block}' +
      '.ym-metin{font-size:13px;color:var(--text-mid,#3a4a62);line-height:1.6;font-style:italic;white-space:pre-line;overflow-wrap:anywhere;margin:0}' +
      '.ym-metin.kisa{display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}' +
      '.ym-devam{background:none;border:0;padding:2px 0;color:var(--gold,#C9972B);font-weight:600;font-size:12.5px;cursor:pointer;align-self:flex-start;font-family:inherit;min-height:28px}' +
      '.ym-alt{margin-top:auto;font-size:10px;color:var(--text-muted,#6b7a94);display:flex;align-items:center;gap:4px}' +
      '#ymBuyuk{position:fixed;inset:0;z-index:9500;background:rgba(0,0,0,.85);display:flex;align-items:center;justify-content:center;padding:16px;cursor:zoom-out}' +
      '#ymBuyuk img{max-width:100%;max-height:100%;border-radius:8px}';
    document.head.appendChild(s);
  }

  function kart(y, i) {
    var ad = String(y.ad || '').trim(), harf = (ad[0] || '?').toLocaleUpperCase('tr');
    var tarih = '';
    if (y.tarih) { try { tarih = new Date(y.tarih + 'T12:00:00').toLocaleDateString('tr-TR', { month: 'long', year: 'numeric' }); } catch (e) {} }
    var metin = String(y.metin || '').trim(), uzun = metin.length > 170 || metin.split('\n').length > 4;
    var resim = (typeof y.gorsel === 'string' && y.gorsel.indexOf(GORSEL_ON) === 0) ? y.gorsel : '';
    return '<div class="yorum-card yolcu-mesaji">' +
      '<div class="ym-ust"><div class="ym-harf" style="background:' + RENK[i % RENK.length] + '">' + esc(harf) + '</div>' +
        '<div style="min-width:0"><div style="font-weight:600;font-size:13px;color:var(--navy,#0B1F3A)">' + esc(ad) + '</div>' +
        (y.tur ? '<div style="font-size:11px;color:var(--text-muted,#6b7a94)">' + esc(y.tur) + '</div>' : '') + '</div>' +
        (resim ? '<button type="button" class="ym-resim" data-ym-buyut="' + esc(resim) + '" aria-label="Fotoğrafı büyüt"><img src="' + esc(resim) + '" alt="" loading="lazy"></button>' : '') +
      '</div>' +
      '<p class="ym-metin' + (uzun ? ' kisa' : '') + '">"' + esc(metin) + '"</p>' +
      (uzun ? '<button type="button" class="ym-devam" data-ym-devam>Devamını oku</button>' : '') +
      '<div class="ym-alt">' + WA + 'WhatsApp mesajı' + (tarih ? ' · ' + esc(tarih) : '') + '</div>' +
      '</div>';
  }

  function serit(l) {
    return '<div class="ym-baslik">Yolcularımızdan gelen mesajlar <span>' + (l.length > 1 ? 'Kaydırın →' : '') + '</span></div>' +
      '<div class="ym-serit" role="list">' + l.map(kart).join('') + '</div>';
  }

  function getir(kategori) {
    var url = SB + '/rest/v1/yorumlar?select=id,ad,tur,kategori,metin,tarih,gorsel&yayinda=eq.true&order=sira.desc,olusturma.desc&limit=20' + (kategori ? '&kategori=eq.' + encodeURIComponent(kategori) : '');
    return fetch(url, { headers: { apikey: K, Authorization: 'Bearer ' + K } }).then(function (r) { return r.ok ? r.json() : []; });
  }

  document.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target.closest('[data-ym-devam],[data-ym-buyut],#ymBuyuk') : null;
    if (!t) return;
    if (t.id === 'ymBuyuk') { t.remove(); return; }
    if (t.hasAttribute('data-ym-devam')) {
      var p = t.previousElementSibling; p.classList.toggle('kisa');
      t.textContent = p.classList.contains('kisa') ? 'Devamını oku' : 'Daha az göster'; return;
    }
    var u = t.getAttribute('data-ym-buyut'); if (!u || u.indexOf(GORSEL_ON) !== 0) return;
    var d = document.createElement('div'); d.id = 'ymBuyuk'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', 'Fotoğraf (kapatmak için dokunun)');
    var img = document.createElement('img'); img.src = u; img.alt = ''; d.appendChild(img); document.body.appendChild(d);
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { var d = document.getElementById('ymBuyuk'); if (d) d.remove(); } });

  function basla() {
    var grid = document.getElementById('yorumGrid'), bolum = document.getElementById('yolcuMesajlari');
    if (grid) getir(null).then(function (l) {
      if (!Array.isArray(l) || !l.length) return;
      stil(); grid.insertAdjacentHTML('beforebegin', '<div id="yolcuSerit">' + serit(l) + '</div>');
    }).catch(function () {});
    if (bolum) getir(bolum.getAttribute('data-kategori') || null).then(function (l) {
      if (!Array.isArray(l) || !l.length) return;
      stil(); var g = bolum.querySelector('.ym-yer'); if (!g) return;
      g.innerHTML = serit(l.slice(0, 10)); bolum.hidden = false;
    }).catch(function () {});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', basla); else basla();
})();
