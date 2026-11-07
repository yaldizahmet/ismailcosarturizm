/* Çerezsiz ziyaret sayacı
   - Çerez ya da tarayıcı hafızası kullanmaz; kişisel bilgi göndermez.
   - Gönderilenler: sayfa adresi, geldiği site (Google, Instagram…), cihaz türü (telefon/tablet/bilgisayar).
   - Kim olduğu bilinmez; aynı gün içinde aynı kişi bir kez sayılsın diye sunucu anonim bir özet tutar.
   - Hata olursa sessizce vazgeçer; sitenin çalışmasını hiçbir zaman etkilemez. */
(function () {
  try {
    var h = location.hostname, ua = navigator.userAgent || '';
    if (h === 'localhost' || h === '127.0.0.1' || location.protocol === 'file:') return;
    if (navigator.webdriver || /bot|crawl|spider|slurp|facebookexternalhit|preview|lighthouse|headless/i.test(ua)) return;

    var sayfa = location.pathname.replace(/\/index\.html$/, '/') || '/';
    if (/tur-detay/.test(sayfa)) { var id = new URLSearchParams(location.search).get('id'); if (id) sayfa += '?id=' + id.slice(0, 60); }

    var kaynak = '';
    try { if (document.referrer) { var r = new URL(document.referrer).hostname.replace(/^www\./, ''); if (r && r !== h.replace(/^www\./, '')) kaynak = r; } } catch (e) {}
    var utm = new URLSearchParams(location.search).get('utm_source');
    if (utm) kaynak = utm.slice(0, 40);
    if (!kaynak && /Instagram/.test(ua)) kaynak = 'instagram (uygulama)';
    if (!kaynak && /FBAN|FBAV/.test(ua)) kaynak = 'facebook (uygulama)';

    var cihaz = /iPad|Tablet/i.test(ua) || (/Android/i.test(ua) && !/Mobile/i.test(ua)) ? 'tablet' : /Mobi|Android|iPhone/i.test(ua) ? 'telefon' : 'bilgisayar';

    var K = 'sb_publishable_bEXKjIeKKN4JrMkOPy3LQg_ZuSlEQNK';
    fetch('https://wpkjxwbvewwgdclbsdya.supabase.co/rest/v1/rpc/ziyaret_kaydet', {
      method: 'POST', keepalive: true,
      headers: { 'Content-Type': 'application/json', apikey: K, Authorization: 'Bearer ' + K },
      body: JSON.stringify({ p_sayfa: sayfa.slice(0, 200), p_kaynak: kaynak, p_cihaz: cihaz })
    }).catch(function () {});
  } catch (e) {}
})();
