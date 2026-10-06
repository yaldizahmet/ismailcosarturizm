/* Coşar Asistan – siteye özel soru-cevap asistanı
   - Yapay zekâ kullanmaz, hiçbir mesajı dışarı göndermez.
   - Tur bilgilerini (tarih, otel, fiyat) admin panelindeki güncel veriden okur.
   - Anlamadığı soruda WhatsApp ve kayıt formuna yönlendirir. */
(function () {
  if (window.__asistanYuklendi) return;
  window.__asistanYuklendi = true;

  var SB_URL = 'https://wpkjxwbvewwgdclbsdya.supabase.co';
  var SB_KEY = 'sb_publishable_bEXKjIeKKN4JrMkOPy3LQg_ZuSlEQNK';
  var TEL = '0533 198 07 81';
  var TEL_LINK = 'tel:+905331980781';
  var WA = 'https://wa.me/905331980781?text=';
  var EPOSTA = 'ismailcosarturizm@gmail.com';
  var ADRES = 'Dr. Mediha Eldem Sk. 81/17 Çankaya / Ankara';

  /* ---------- Yardımcılar ---------- */
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function sade(s) {
    return String(s || '').toLocaleLowerCase('tr')
      .replace(/ç/g, 'c').replace(/ğ/g, 'g').replace(/ı/g, 'i').replace(/İ/g, 'i').replace(/i̇/g, 'i')
      .replace(/ö/g, 'o').replace(/ş/g, 's').replace(/ü/g, 'u').replace(/â/g, 'a').replace(/î/g, 'i').replace(/û/g, 'u')
      .replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
  }
  function kelimeler(s) { return sade(s).split(' ').filter(Boolean); }
  var AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
  function tarih(d) {
    if (!d) return '';
    var p = String(d).split('-');
    if (p.length !== 3 || !(+p[1] >= 1 && +p[1] <= 12)) return String(d);
    return parseInt(p[2], 10) + ' ' + AYLAR[+p[1] - 1] + ' ' + p[0];
  }
  function waLink(metin) { return WA + encodeURIComponent('Merhaba, web sitenizden yazıyorum. ' + metin); }

  /* ---------- Bilgi bankası: SSS sayfasındaki sorular ----------
     Cevaplar doğrudan sss.html'den okunur; SSS güncellenince asistan da güncellenir. */
  var DURAK_SOZ = ['mi', 'mu', 'mı', 'mü', 'misiniz', 'miyim', 'miyiz', 'musunuz', 'var', 'yok', 'ne', 'neler', 'nedir', 'nasil', 'icin', 'ile', 've', 'veya', 'bir', 'bu', 'su', 'da', 'de', 'ben', 'benim', 'biz', 'siz', 'sizin', 'sizde', 'size', 'bana', 'olur', 'olarak', 'gibi', 'kadar', 'hangi', 'mumkun', 'acaba', 'merhaba', 'selam', 'lutfen', 'istiyorum', 'istiyoruz', 'yapabilir', 'yapiliyor', 'oluyor', 'ediyor', 'ki', 'en', 'cok', 'daha', 'ise', 'diye'];
  var sssSoz = null;
  function kok(w) { return w.length > 5 ? w.slice(0, 5) : w; }
  function anlamli(metin) {
    return kelimeler(metin).filter(function (w) { return w.length >= 3 && DURAK_SOZ.indexOf(w) === -1; }).map(kok);
  }
  function sssGetir() {
    if (sssSoz) return sssSoz;
    sssSoz = fetch('sss.html').then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); }).then(function (html) {
      var liste = [], parcalar = html.split('<div class="sss-category"');
      parcalar.slice(1).forEach(function (p) {
        var kat = (p.match(/class="sss-category-title"><span>[^<]*<\/span>\s*([^<]+)</) || [])[1] || '';
        var re = /<div class="sss-item" id="soru-(\d+)">.*?<span class="sss-q-text">(.*?)<\/span>.*?<div class="sss-a">(.*?)<\/div><\/div>/g, m;
        while ((m = re.exec(p))) {
          var soru = m[2].replace(/<[^>]+>/g, ''), cevap = m[3];
          liste.push({ no: m[1], kat: kat.trim(), s: soru, c: cevap, ts: anlamli(soru), tk: anlamli(kat), tc: anlamli(cevap.replace(/<[^>]+>/g, ' ')) });
        }
      });
      var df = {};
      liste.forEach(function (x) { x.ts.concat(x.tk).filter(function (v, i, a) { return a.indexOf(v) === i; }).forEach(function (t) { df[t] = (df[t] || 0) + 1; }); });
      liste.forEach(function (x) { x.df = df; });
      liste.N = liste.length;
      return liste;
    }).catch(function () { sssSoz = null; return []; });
    return sssSoz;
  }
  function benzer(a, b) { return a === b || (a.length >= 4 && b.length >= 4 && (a.indexOf(b) === 0 || b.indexOf(a) === 0)); }
  function sssAra(metin, liste) {
    var sorgu = anlamli(metin).filter(function (v, i, a) { return a.indexOf(v) === i; });
    if (!sorgu.length || !liste.length) return [];
    return liste.map(function (x) {
      var p = 0, soruEslesme = 0, eslesenIdf = 0, toplamIdf = 0;
      sorgu.forEach(function (t) {
        var idf = Math.log(1 + liste.N / ((x.df[t] || 0) + 1));
        toplamIdf += idf;
        if (x.ts.some(function (w) { return benzer(w, t); })) { p += 3 * idf; soruEslesme++; eslesenIdf += idf; }
        else if (x.tk.some(function (w) { return benzer(w, t); })) p += 1 * idf;
        else if (x.tc.some(function (w) { return benzer(w, t); })) p += 0.6 * idf;
      });
      // Sorgudaki kelimelerin çoğu soruda geçiyorsa ödüllendir
      p *= (0.6 + 0.4 * soruEslesme / sorgu.length);
      return { x: x, p: p, se: soruEslesme, kap: toplamIdf ? eslesenIdf / toplamIdf : 0 };
    }).filter(function (r) { return r.se > 0; }).sort(function (a, b) { return b.p - a.p; });
  }
  function sssCevapHtml(x) {
    return x.c + '<div style="margin-top:6px"><a href="sss.html#soru-' + x.no + '" style="font-size:12.5px">📖 Sıkça Sorulan Sorular\'da gör</a></div>';
  }

  var ILETISIM = { k: ['telefon', 'numara', 'adres', 'nerede', 'ofis', 'iletisim', 'ulas', 'mail', 'e posta', 'eposta', 'whatsapp', 'ara'], g: ['telefon', 'adres', 'iletisim', 'ofis'] };
  var SELAM = ['merhaba', 'selam', 'slm', 'gunaydin', 'iyi gunler', 'iyi aksamlar', 'hey', 'sa', 'selamun', 'esselamu'];
  var TESEKKUR = ['tesekkur', 'sagol', 'sag ol', 'eyvallah', 'tamam', 'anladim', 'super', 'harika'];
  var FIYAT = ['fiyat', 'ucret', 'kac para', 'ne kadar', 'kac lira', 'kac dolar', 'kac euro', 'tutar', 'para'];
  var TARIH = ['ne zaman', 'tarih', 'program', 'hangi tarih', 'gidis', 'donus', 'kalkis tarihi', 'yakin', 'bir sonraki', 'en yakin'];
  var KAT = {
    umre: { k: ['umre', 'umreye', 'umrede'], ad: 'Umre', sayfa: 'umre.html' },
    hac: { k: ['hac', 'hacca', 'hacda', 'hacc'], ad: 'Hac', sayfa: 'hac.html' },
    diger: { k: ['yurt disi', 'yurtdisi', 'kultur turu', 'avrupa', 'balkan', 'gezi', 'tatil turu'], ad: 'Yurt dışı', sayfa: 'turlar.html' }
  };

  function eslesme(metinSade, sozcukler, kok) {
    if (kok.indexOf(' ') !== -1) return metinSade.indexOf(kok) !== -1;
    for (var i = 0; i < sozcukler.length; i++) {
      if (kok.length <= 3) { if (sozcukler[i] === kok) return true; }
      else if (sozcukler[i].indexOf(kok) === 0) return true;
    }
    return false;
  }
  function puan(metinSade, sozcukler, k, g) {
    var p = 0;
    (k || []).forEach(function (x) { if (eslesme(metinSade, sozcukler, x)) p += 1; });
    (g || []).forEach(function (x) { if (eslesme(metinSade, sozcukler, x)) p += 2; });
    return p;
  }
  function herhangi(metinSade, sozcukler, liste) {
    for (var i = 0; i < liste.length; i++) if (eslesme(metinSade, sozcukler, liste[i])) return true;
    return false;
  }

  /* ---------- Tur verisi ---------- */
  var turlarSoz = null;
  function turlariGetir() {
    if (turlarSoz) return turlarSoz;
    turlarSoz = fetch(SB_URL + '/rest/v1/turlar?aktif=eq.true&order=tarih&select=id,kategori,baslik,tarih,donus_tarihi,sure,konum,otel,fiyat,fiyat_2,fiyat_3,fiyat_4,para_birimi,kontenjan',
      { headers: { apikey: SB_KEY, Authorization: 'Bearer ' + SB_KEY } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .catch(function () { turlarSoz = null; return null; });
    return turlarSoz;
  }
  var KONTENJAN = { var: 'Yer var', az: 'Az kaldı', dolu: 'Dolu' };
  function turKart(t) {
    var odalar = [['2 kişilik', t.fiyat_2], ['3 kişilik', t.fiyat_3], ['4 kişilik', t.fiyat_4]].filter(function (o) { return o[1] && String(o[1]).trim(); });
    var pb = t.para_birimi || '';
    var fiyat = '';
    if (odalar.length) fiyat = odalar.map(function (o) { return o[0] + ' odada kişi başı <b>' + esc(o[1]) + ' ' + esc(pb) + '</b>'; }).join('<br>');
    else if (t.fiyat && t.kategori !== 'umre') fiyat = 'Kişi başı <b>' + esc(t.fiyat) + ' ' + esc(pb) + '</b>';
    var tarihStr = tarih(t.tarih) + (t.donus_tarihi ? ' – ' + tarih(t.donus_tarihi) : '');
    return '<div class="ca-tur">'
      + '<a class="ca-tur-baslik" href="tur-detay.html?id=' + encodeURIComponent(t.id) + '">' + esc(t.baslik) + ' →</a>'
      + (tarihStr ? '<div>📅 ' + esc(tarihStr) + (t.sure ? ' · ' + esc(t.sure) : '') + '</div>' : '')
      + (t.otel ? '<div>🏨 ' + esc(t.otel) + '</div>' : '')
      + (fiyat ? '<div>' + fiyat + '</div>' : '')
      + (t.kontenjan ? '<div class="ca-kont ca-k-' + esc(t.kontenjan) + '">' + esc(KONTENJAN[t.kontenjan] || '') + '</div>' : '')
      + '</div>';
  }
  function turListesiCevap(kat, baslik) {
    return turlariGetir().then(function (turlar) {
      if (!turlar) return { h: 'Program bilgilerine şu an ulaşamadım. <a href="' + KAT[kat].sayfa + '">' + KAT[kat].ad + ' sayfasından</a> bakabilir ya da bize yazabilirsiniz.', wa: KAT[kat].ad + ' programları hakkında bilgi almak istiyorum.' };
      var liste = turlar.filter(function (t) { return t.kategori === kat; });
      if (!liste.length) return { h: 'Şu anda yayında olan bir ' + KAT[kat].ad.toLocaleLowerCase('tr') + ' programımız görünmüyor. Yeni programlar için bize yazın, açıldığında ilk sizi haberdar edelim.', wa: KAT[kat].ad + ' programları hakkında bilgi almak istiyorum.' };
      return { h: (baslik || 'Güncel ' + KAT[kat].ad + ' programlarımız:') + liste.slice(0, 5).map(turKart).join('') + (liste.length > 5 ? '<div>Tümü için <a href="' + KAT[kat].sayfa + '">' + KAT[kat].ad + ' sayfası</a>.</div>' : ''), wa: KAT[kat].ad + ' programları hakkında bilgi almak istiyorum.' };
    });
  }
  var DURAK = ['umre', 'hac', 'turu', 'tur', 'turlari', 'program', 'programi', 'paket', 'paketi', 'kis', 'yaz', 'ozel', 'ekonomi', 'ekonomik', 'lux', 'vip', 'ile', 've', 'gun', 'gece'];
  function turAdiylaBul(metinSade, sozcukler) {
    return turlariGetir().then(function (turlar) {
      if (!turlar) return null;
      var bulunan = turlar.filter(function (t) {
        return kelimeler(t.baslik + ' ' + (t.konum || '')).some(function (w) {
          return w.length >= 4 && !/^\d+$/.test(w) && DURAK.indexOf(w) === -1 && sozcukler.some(function (s) { return s.length >= 4 && (s.indexOf(w.slice(0, 5)) === 0 || w.indexOf(s.slice(0, 5)) === 0); });
        });
      });
      return bulunan.length ? bulunan : null;
    });
  }

  /* ---------- Cevap üretimi ---------- */
  var GENEL = ['umre', 'hac', 'hacc', 'fiyat', 'ucret', 'para', 'tutar', 'zaman', 'tarih', 'progr', 'tur', 'turu', 'turla', 'paket', 'gidis', 'yakin', 'sonra', 'ilk', 'yurt', 'disi'];
  function cevapla(metin) {
    var m = sade(metin), s = kelimeler(metin);
    if (!m) return Promise.resolve({ h: 'Sorunuzu yazabilir ya da aşağıdaki konulardan birini seçebilirsiniz.' });

    var kategori = null;
    ['umre', 'hac', 'diger'].forEach(function (k) { if (!kategori && herhangi(m, s, KAT[k].k)) kategori = k; });
    var fiyatSoru = herhangi(m, s, FIYAT), tarihSoru = herhangi(m, s, TARIH);
    var ilePuan = puan(m, s, ILETISIM.k, ILETISIM.g);
    var ozelKelime = anlamli(metin).filter(function (t) { return !GENEL.some(function (g) { return benzer(g, t); }); });

    if (s.length <= 4 && herhangi(m, s, SELAM) && !kategori && ozelKelime.length <= 1)
      return Promise.resolve({ h: 'Merhaba, hoş geldiniz! 😊 Umre, Hac ve yurt dışı turlarımız hakkında merak ettiklerinizi sorabilirsiniz.' });
    if (s.length <= 4 && herhangi(m, s, TESEKKUR) && !kategori && ozelKelime.length <= 1)
      return Promise.resolve({ h: 'Rica ederiz! Başka bir sorunuz olursa buradayım. Hayırlı yolculuklar dileriz. 🌙' });

    if (ilePuan >= 2)
      return Promise.resolve({ h: '📞 <a href="' + TEL_LINK + '">' + TEL + '</a><br>✉️ <a href="mailto:' + EPOSTA + '">' + EPOSTA + '</a><br>📍 ' + ADRES + '<br>Tüm iletişim bilgileri: <a href="iletisim.html">İletişim</a>', wa: 'Bilgi almak istiyorum.' });

    // "Umre ne zaman / fiyatı ne kadar" gibi genel program sorusu → canlı program listesi
    var programSorusu = kategori && ozelKelime.length === 0;
    if (programSorusu) {
      if (kategori === 'diger') return turAdiylaBul(m, s).then(function (b) { return b ? turBulunduCevap(b) : turListesiCevap('diger'); });
      return turListesiCevap(kategori);
    }

    return Promise.all([sssGetir(), turAdiylaBul(m, s)]).then(function (r) {
      var liste = r[0], bulunanTur = r[1];
      var sonuc = sssAra(metin, liste);
      var ilk = sonuc[0];
      var guclu = ilk && ilk.p >= 3.5 && ilk.kap >= 0.6;
      var zayif = ilk && !guclu && ilk.p >= 2.2 && ilk.kap >= 0.5;

      // Belirli bir turun adı geçiyorsa (ör. "Balkan turu ne kadar", "İspanya'ya gitmek istiyorum") turu göster;
      // ancak tur hakkında belirli bir SSS sorusu soruluyorsa (ör. "Balkan turunda hangi ülkeler geziliyor") SSS cevabı öncelikli
      if (bulunanTur && (fiyatSoru || tarihSoru || !guclu || ilk.se < 2)) return turBulunduCevap(bulunanTur);

      if (guclu || zayif) {
        var c = { h: sssCevapHtml(ilk.x), wa: ilk.x.s };
        var digerleri = sonuc.slice(1, 4).filter(function (y) { return y.p >= ilk.p * 0.55; }).map(function (y) { return y.x.s; });
        if (digerleri.length) c.chips = digerleri.slice(0, 3);
        if (!guclu) c.h += '<div class="ca-not" style="margin-top:6px">Aradığınız bu değilse sorunuzu biraz daha açık yazabilir ya da bize doğrudan sorabilirsiniz.</div>';
        if (kategori && kategori !== 'diger' && (fiyatSoru || herhangi(m, s, ['ne zaman', 'tarih', 'hangi tarih'])))
          return turListesiCevap(kategori).then(function (l) { c.h += '<br>' + l.h; return c; });
        return c;
      }
      if (kategori) return turListesiCevap(kategori);
      if (fiyatSoru || tarihSoru) return { h: 'Hangi programla ilgileniyorsunuz? Aşağıdan Umre, Hac ya da yurt dışı turlarını seçebilirsiniz.', chips: ['Umre programları', 'Hac programları', 'Yurt dışı turları'] };
      return { h: 'Bu soruyu en doğru şekilde ekibimiz cevaplar. 🙏 WhatsApp\'tan yazabilir, <a href="' + TEL_LINK + '">' + TEL + '</a> numarasından arayabilir ya da <a href="sss.html">Sıkça Sorulan Sorular</a> sayfamıza göz atabilirsiniz.', wa: 'Bir sorum var: ' + metin.slice(0, 200) };
    });
  }
  function turBulunduCevap(bulunan) {
    return { h: (bulunan.length > 1 ? 'Şu programlarımızı buldum:' : 'Bu programımızı buldum:') + bulunan.slice(0, 4).map(turKart).join(''), wa: bulunan[0].baslik + ' hakkında bilgi almak istiyorum.' };
  }

  /* ---------- Arayüz ---------- */
  var css = ''
    + '#caBtn{position:fixed;right:28px;bottom:96px;z-index:998;width:56px;height:56px;border-radius:50%;border:0;cursor:pointer;background:#0B1F3A;color:#E8C46A;box-shadow:0 4px 18px rgba(11,31,58,.4);display:flex;align-items:center;justify-content:center;transition:transform .2s}'
    + '#caBtn:hover{transform:scale(1.07)}'
    + '#caBtn .ca-ipucu{position:absolute;right:66px;white-space:nowrap;background:#fff;color:#0B1F3A;font:600 13px/1 inherit;padding:9px 12px;border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,.15);pointer-events:none}'
    + '#caPanel{position:fixed;right:28px;bottom:96px;z-index:8500;width:370px;max-width:calc(100vw - 32px);height:560px;max-height:calc(100vh - 120px);background:#fff;border-radius:18px;box-shadow:0 18px 60px rgba(0,0,0,.28);display:none;flex-direction:column;overflow:hidden;font-family:inherit}'
    + '#caPanel.acik{display:flex}'
    + '.ca-bas{background:#0B1F3A;color:#fff;padding:14px 16px;display:flex;align-items:center;gap:10px}'
    + '.ca-bas b{display:block;font-size:15px}.ca-bas small{color:rgba(255,255,255,.6);font-size:12px}'
    + '.ca-kapat{margin-left:auto;background:none;border:0;color:#fff;font-size:26px;line-height:1;cursor:pointer;padding:0 4px}'
    + '.ca-akis{flex:1;overflow-y:auto;padding:14px;background:#F8F5EE;display:flex;flex-direction:column;gap:10px}'
    + '.ca-m{max-width:88%;padding:10px 13px;border-radius:14px;font-size:14px;line-height:1.55;word-wrap:break-word}'
    + '.ca-bot{background:#fff;color:#1f2937;border:1px solid #ece6d8;border-top-left-radius:4px;align-self:flex-start}'
    + '.ca-ben{background:#0B1F3A;color:#fff;border-top-right-radius:4px;align-self:flex-end}'
    + '.ca-bot a{color:#9a6f12;font-weight:600}'
    + '.ca-tur{margin-top:8px;padding:9px 11px;border:1px solid #ece6d8;border-radius:10px;background:#FCFAF5;font-size:13px;line-height:1.6}'
    + '.ca-tur-baslik{display:block;font-weight:700;color:#0B1F3A!important;text-decoration:none;margin-bottom:2px}'
    + '.ca-kont{display:inline-block;margin-top:3px;font-size:11.5px;font-weight:700;padding:1px 8px;border-radius:50px;background:#e8f5e9;color:#2e7d32}'
    + '.ca-k-az{background:#fff4e0;color:#b26a00}.ca-k-dolu{background:#fdecea;color:#c62828}'
    + '.ca-not{color:#6b7280;font-size:12.5px}'
    + '.ca-wa{display:inline-flex;align-items:center;gap:6px;margin-top:8px;background:#25D366;color:#fff!important;text-decoration:none!important;font-weight:700;font-size:13px;padding:7px 12px;border-radius:50px}'
    + '.ca-cipler{display:flex;flex-wrap:nowrap;overflow-x:auto;gap:6px;padding:10px 14px 2px;background:#fff;scrollbar-width:none}.ca-cipler::-webkit-scrollbar{display:none}'
    + '.ca-cip{flex:0 0 auto;white-space:nowrap;border:1.5px solid #e2d6b8;background:#fff;color:#0B1F3A;font:600 12.5px/1 inherit;padding:7px 11px;border-radius:50px;cursor:pointer}'
    + '.ca-cip:hover{border-color:#C9972B;background:#FBF6EA}'
    + '.ca-giris{display:flex;gap:8px;padding:10px 14px;background:#fff}'
    + '.ca-giris input{flex:1;border:1.5px solid #e5e7eb;border-radius:50px;padding:10px 14px;font:14px inherit;outline:none;min-width:0}'
    + '.ca-giris input:focus{border-color:#C9972B}'
    + '.ca-giris button{border:0;background:#C9972B;color:#0B1F3A;font-weight:700;border-radius:50px;padding:0 16px;cursor:pointer;font-family:inherit}'
    + '.ca-alt{font-size:11px;color:#9ca3af;text-align:center;padding:0 14px 10px;background:#fff}'
    + '.ca-yaziyor span{display:inline-block;width:6px;height:6px;margin:0 2px;border-radius:50%;background:#C9972B;animation:caZip 1s infinite}'
    + '.ca-yaziyor span:nth-child(2){animation-delay:.15s}.ca-yaziyor span:nth-child(3){animation-delay:.3s}'
    + '@keyframes caZip{0%,60%,100%{opacity:.3;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}'
    + '@media(max-width:520px){#caBtn{right:20px;bottom:88px;width:52px;height:52px}#caPanel{right:0;left:0;bottom:0;width:100%;max-width:100%;height:82vh;max-height:82vh;border-radius:18px 18px 0 0}}';

  var CIPLER = ['Umre programları', 'Hac programları', 'Yurt dışı turları', 'Taksit yapılıyor mu?', 'Valize neler koymalıyım?', 'İletişim'];
  var panel, akis, girdi, ilkAcilis = true;

  function mesajEkle(html, kim) {
    var d = document.createElement('div');
    d.className = 'ca-m ' + (kim === 'ben' ? 'ca-ben' : 'ca-bot');
    d.innerHTML = html;
    akis.appendChild(d);
    akis.scrollTop = akis.scrollHeight;
    return d;
  }
  function botCevap(c) {
    var html = c.h;
    if (c.wa) html += '<div><a class="ca-wa" target="_blank" rel="noopener" href="' + waLink(c.wa) + '">💬 WhatsApp\'tan sor</a></div>';
    mesajEkle(html, 'bot');
  }
  function cipGoster(liste) {
    var kutu = panel.querySelector('.ca-cipler');
    kutu.innerHTML = '';
    liste.forEach(function (t) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'ca-cip'; b.textContent = t;
      b.onclick = function () { gonder(t); };
      kutu.appendChild(b);
    });
  }
  function gonder(metin) {
    metin = String(metin || '').trim();
    if (!metin) return;
    mesajEkle(esc(metin), 'ben');
    girdi.value = '';
    var y = mesajEkle('<span class="ca-yaziyor"><span></span><span></span><span></span></span>', 'bot');
    var bas = Date.now();
    cevapla(metin).then(function (c) {
      setTimeout(function () { y.remove(); botCevap(c); cipGoster(c.chips ? c.chips.concat(CIPLER.slice(0, 3)) : CIPLER); }, Math.max(0, 450 - (Date.now() - bas)));
    }).catch(function () {
      y.remove(); botCevap({ h: 'Bir sorun oluştu. Lütfen bize WhatsApp\'tan yazın ya da <a href="' + TEL_LINK + '">' + TEL + '</a> numarasını arayın.', wa: 'Bilgi almak istiyorum.' });
    });
  }
  function ac() {
    panel.classList.add('acik');
    document.getElementById('caBtn').style.display = 'none';
    var ip = document.querySelector('#caBtn .ca-ipucu'); if (ip) ip.remove();
    if (ilkAcilis) {
      ilkAcilis = false;
      mesajEkle('Merhaba! 👋 Ben <b>Coşar Asistan</b>. Umre, Hac ve yurt dışı turlarımızla ilgili sorularınızı cevaplayabilirim: tarihler, oteller, fiyatlar, gerekli belgeler…<br>Aşağıdan bir konu seçin ya da sorunuzu yazın.', 'bot');
      cipGoster(CIPLER);
      turlariGetir();
      sssGetir();
    }
    if (window.innerWidth > 520) setTimeout(function () { girdi.focus(); }, 50);
  }
  function kapat() {
    panel.classList.remove('acik');
    document.getElementById('caBtn').style.display = 'flex';
  }

  function kur() {
    if (document.getElementById('caBtn')) return;
    var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

    var btn = document.createElement('button');
    btn.id = 'caBtn'; btn.type = 'button'; btn.setAttribute('aria-label', 'Asistana soru sor');
    btn.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2-3 3"/><circle cx="12" cy="16" r=".5" fill="currentColor"/></svg>';
    btn.onclick = ac;
    document.body.appendChild(btn);

    panel = document.createElement('div');
    panel.id = 'caPanel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Coşar Asistan');
    panel.innerHTML = '<div class="ca-bas"><div style="width:36px;height:36px;border-radius:50%;background:#C9972B;color:#0B1F3A;display:flex;align-items:center;justify-content:center;font-weight:800">İC</div><div><b>Coşar Asistan</b><small>Otomatik yanıt · Anında cevap</small></div><button type="button" class="ca-kapat" aria-label="Kapat">&times;</button></div>'
      + '<div class="ca-akis"></div><div class="ca-cipler"></div>'
      + '<form class="ca-giris"><input type="text" maxlength="300" placeholder="Sorunuzu yazın…" aria-label="Sorunuz"><button type="submit">Gönder</button></form>'
      + '<div class="ca-alt">Otomatik asistandır, mesajlar kaydedilmez. Kesin bilgi için: <a href="' + TEL_LINK + '" style="color:inherit">' + TEL + '</a></div>';
    document.body.appendChild(panel);
    akis = panel.querySelector('.ca-akis');
    girdi = panel.querySelector('input');
    panel.querySelector('.ca-kapat').onclick = kapat;
    panel.querySelector('form').onsubmit = function (e) { e.preventDefault(); gonder(girdi.value); };
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && panel.classList.contains('acik')) kapat(); });

    // Küçük ipucu balonu (oturum başına bir kez)
    try {
      if (!sessionStorage.getItem('ca-ipucu')) {
        sessionStorage.setItem('ca-ipucu', '1');
        setTimeout(function () {
          if (panel.classList.contains('acik')) return;
          var ip = document.createElement('span'); ip.className = 'ca-ipucu'; ip.textContent = 'Sorunuz mu var? 👋';
          btn.appendChild(ip);
          setTimeout(function () { if (ip.parentNode) ip.remove(); }, 6000);
        }, 4000);
      }
    } catch (e) {}
  }

  window.cosarAsistan = { ac: ac, cevapla: cevapla };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', kur); else kur();
})();
