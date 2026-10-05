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

  /* ---------- Bilgi bankası (SSS sayfasından) ----------
     k: anahtar kelime kökleri (sade yazımla, kelimenin başıyla eşleşir)
     Her eşleşen kök +1 puan; 'g' (güçlü) kökler +2 puan. */
  var SSS = [
    { k: ['hizmet', 'neler', 'ne tur', 'hangi tur', 'duzenliyor'], g: ['hangi hizmet', 'neler yapiyor'], c: 'Hac ve Umre organizasyonlarının yanı sıra Balkanlar ve Avrupa başta olmak üzere yurt içi ve yurt dışı kültür, inanç ve grup turları düzenliyoruz. Farklı bütçe ve beklentilere uygun alternatifler sunuyoruz.' },
    { k: ['kalkis', 'nereden', 'hangi sehir', 'katilim'], g: ['kalkis', 'nereden kalk'], c: 'Kalkış noktaları tur programına göre değişir. Ankara başta olmak üzere farklı şehirlerden katılım seçenekleri sunulabiliyor; güncel kalkış noktası her turun programında belirtilir.' },
    { k: ['dahil', 'icinde', 'kapsa'], g: ['neler dahil', 'fiyata dahil', 'ucrete dahil'], c: 'Tura göre değişmekle birlikte konaklama, ulaşım, transferler, rehberlik ve programda belirtilen öğünler fiyata dahil olabilir. Her turun dahil olan ve olmayan hizmetleri, tur detay sayfasında açıkça yazar.' },
    { k: ['haric', 'dahil degil', 'ekstra', 'harc'], g: ['dahil olmayan', 'haric'], c: 'Kişisel harcamalar, ekstra geziler, programda belirtilmeyen yemekler, yurt dışı çıkış harcı gibi kişisel giderler pakete göre ayrıca ücretlendirilebilir.' },
    { k: ['odeme', 'taksit', 'pesin', 'kredi kart', 'kart', 'havale'], g: ['taksit', 'odeme'], c: 'Turun niteliğine ve rezervasyon tarihine göre peşin veya taksitli ödeme seçenekleri sunulabiliyor. Güncel ödeme koşulları için bize ulaşmanız en doğrusu.', wa: 'Ödeme ve taksit seçenekleri hakkında bilgi almak istiyorum.' },
    { k: ['donem', 'hangi ay', 'ayda', 'somestr', 'tatil', 'yil boyu'], g: ['hangi donem', 'hangi ay'], c: 'Yıl içinde her ay Umre organizasyonu düzenliyoruz. Özellikle sömestr ve tatil dönemlerinde farklı süre ve konaklama seçenekleri sunuyoruz.', ek: 'umre' },
    { k: ['otel', 'konum', 'mesafe', 'yakin', 'kabe', 'harem', 'mescid'], g: ['otel nerede', 'mesafe', 'yurume'], c: 'Umre programına göre Mekke ve Medine\'de farklı konum ve standartlarda oteller kullanılıyor. Otelin Kâbe-i Şerif\'e veya Mescid-i Nebevî\'ye mesafesi programda belirtiliyor.', ek: 'umre' },
    { k: ['rehber', 'kafile', 'hoca', 'gorevli'], g: ['rehber', 'kafile baskan'], c: 'Evet. Programlarımızda grup boyunca deneyimli kafile başkanı ve rehberlik hizmeti sunuyoruz.' },
    { k: ['kac gun', 'gun kal', 'sure', 'kac gece', 'medine de', 'mekke de'], g: ['kac gun', 'kac gece'], c: 'Konaklama süresi seçilen pakete göre değişiyor. 10, 14 gün ve farklı sürelerde Umre programları hazırlanabiliyor.', ek: 'umre' },
    { k: ['ilk defa', 'ilk kez', 'bilgilendirme', 'ihram', 'egitim', 'seminer'], g: ['ilk defa', 'ilk kez', 'ihram'], c: 'Evet. Umre öncesinde yolculuk, ihram, umre ibadeti, dikkat edilmesi gerekenler ve programın işleyişi hakkında bilgilendirme yapıyoruz.' },
    { k: ['yasli', 'engelli', 'tekerlekli', 'hasta', 'ozel destek', 'refakat', 'ozel ihtiyac'], g: ['yasli', 'engelli', 'tekerlekli'], c: 'Elbette. Yaşlı misafirlerimizin ve özel ihtiyacı olan yolcularımızın durumunu rezervasyon öncesinde bildirirseniz gerekli planlamayı birlikte yapıyoruz.', wa: 'Özel destek gerektiren bir yolcu için bilgi almak istiyorum.' },
    { k: ['aile', 'cocuk', 'esim', 'beraber', 'birlikte'], g: ['aile', 'cocuk'], c: 'Evet. Aileler için uygun oda ve konaklama seçenekleri sunuyoruz. Aynı aileden katılanların mümkün olduğunca birlikte konaklaması için rezervasyon aşamasında planlama yapılıyor.' },
    { k: ['hac nasil', 'hac organizasyon', 'hac kayit', 'hac basvuru', 'kontenjan'], g: ['hac basvuru', 'hac kayit'], c: 'Hac organizasyonları resmi mevzuat ve yetkili kurumların belirlediği şartlar doğrultusunda yapılıyor. Kontenjan, başvuru ve kayıt süreçleri dönemsel olarak değiştiği için güncel bilgileri biz paylaşıyoruz.', ek: 'hac', wa: 'Hac başvurusu hakkında bilgi almak istiyorum.' },
    { k: ['belge', 'evrak', 'gerekli', 'saglik raporu', 'asi'], g: ['hangi belge', 'evrak', 'gerekli belge'], c: 'Gerekli belgeler dönemsel uygulamalara göre değişebiliyor. Pasaport, başvuru belgeleri, sağlık belgeleri ve diğer resmi evraklar konusunda kayıt sürecinde ayrıntılı bilgilendirme yapıyoruz.', wa: 'Gerekli belgeler hakkında bilgi almak istiyorum.' },
    { k: ['fark', 'arasinda'], g: ['hac ile umre', 'hac ve umre fark', 'farki'], c: 'Hac, belirli bir zaman diliminde ve belirli şartlarla yapılan farz bir ibadettir. Umre ise yılın farklı dönemlerinde yapılabilir. İkisinin program ve hazırlık süreçleri farklıdır.' },
    { k: ['hangi ulke', 'ulkeler', 'rota', 'guzergah', 'makedonya', 'kosova', 'arnavutluk', 'karadag', 'bosna', 'sirbistan'], g: ['hangi ulke', 'rota'], c: 'Programa göre değişmekle birlikte Makedonya, Kosova, Arnavutluk, Karadağ, Bosna-Hersek, Sırbistan ve çevre ülkeleri kapsayan farklı Balkan rotaları düzenliyoruz.', ek: 'diger' },
    { k: ['vize', 'schengen', 'vizesiz'], g: ['vize', 'schengen'], c: 'Vize şartları ziyaret edilecek ülkelere göre değişiyor. Balkan ülkelerinin giriş kuralları farklı olabildiği için rezervasyon öncesinde pasaport ve vize durumunuzu birlikte kontrol ediyoruz.', wa: 'Vize durumu hakkında bilgi almak istiyorum.' },
    { k: ['yildiz', 'kac yildiz', 'balkan otel'], g: ['kac yildiz'], c: 'Balkan turlarında programın kategorisine göre seçilen 4 ve 5 yıldızlı otellerde konaklanıyor. Otel bilgileri tur programı kesinleşince bildiriliyor.' },
    { k: ['yemek', 'ogun', 'kahvalti', 'aksam yemegi', 'yarim pansiyon', 'tam pansiyon'], g: ['yemek', 'ogun'], c: 'Turdan tura değişiyor. Dahil olan öğünler tur programında açıkça belirtiliyor; bazı programlarda kahvaltı ve akşam yemeği dahil.' },
    { k: ['tek basima', 'yalniz', 'tek kisi', 'single'], g: ['tek basima', 'single', 'tek kisilik'], c: 'Evet, tek başına seyahat eden misafirlerimiz de grup turlarına katılabiliyor. Tek kişilik oda isteyenler için pakete göre single oda farkı uygulanabiliyor.' },
    { k: ['rezervasyon', 'kayit', 'nasil katil', 'yer ayirt', 'basvur'], g: ['nasil kayit', 'rezervasyon', 'kayit ol'], c: 'Web sitemizdeki kayıt formundan, telefonla, WhatsApp\'tan veya ofisimizden rezervasyon talebi oluşturabilirsiniz. Kontenjan ve uygunluk kontrolünden sonra kaydınız tamamlanıyor. Her programın yanındaki "Kayıt Ol" butonunu kullanabilirsiniz.', wa: 'Rezervasyon yaptırmak istiyorum.' },
    { k: ['iptal', 'iade', 'vazgec', 'geri odeme'], g: ['iptal', 'iade'], c: 'İptal ve iade koşulları seçilen tura, rezervasyon tarihine ve ilgili hizmet sağlayıcıların kurallarına göre değişiyor. Kayıt sırasında geçerli iptal ve iade şartları size ayrıca bildiriliyor.', wa: 'İptal ve iade koşulları hakkında bilgi almak istiyorum.' },
    { k: ['pasaport', 'gecerlilik'], g: ['pasaport'], c: 'Pasaport geçerlilik şartları gidilecek ülkeye göre değişebiliyor. Seyahat öncesinde pasaportunuzun süresini kontrol etmenizi ve rezervasyon sırasında pasaport durumunuzu bize bildirmenizi öneriyoruz.' },
    { k: ['seyahat oncesi', 'bagaj', 'bulusma', 'ucus saati', 'hazirlik'], g: ['bagaj', 'bulusma'], c: 'Evet. Tur tarihinden önce uçuş, buluşma noktası, otel, transfer, bagaj, gerekli belgeler ve programla ilgili tüm önemli bilgileri sizinle paylaşıyoruz.' },
    { k: ['belgeler', 'lisans', 'yetki', 'tursab', 'diyanet', 'guvenilir', 'resmi'], g: ['yetki belgesi', 'lisans', 'tursab', 'guvenilir'], c: 'A Grubu Seyahat Acentası İşletme Belgemiz (Belge No: 10597) ve Diyanet İşleri Başkanlığı Hac & Umre Organizasyonu Yetki Belgemiz bulunuyor. Belgeleri <a href="belgelerimiz.html">Belgelerimiz</a> sayfasında görebilirsiniz.' }
  ];

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
  function cevapla(metin) {
    var m = sade(metin), s = kelimeler(metin);
    if (!m) return Promise.resolve({ h: 'Sorunuzu yazabilir ya da aşağıdaki konulardan birini seçebilirsiniz.' });

    var kategori = null;
    ['umre', 'hac', 'diger'].forEach(function (k) { if (!kategori && herhangi(m, s, KAT[k].k)) kategori = k; });
    var fiyatSoru = herhangi(m, s, FIYAT), tarihSoru = herhangi(m, s, TARIH);

    // SSS ve iletişim puanları
    var enIyi = null, enPuan = 0;
    SSS.forEach(function (x) { var p = puan(m, s, x.k, x.g); if (p > enPuan) { enPuan = p; enIyi = x; } });
    var ilePuan = puan(m, s, ILETISIM.k, ILETISIM.g);

    // Selam / teşekkür (kısa mesajlar)
    if (s.length <= 4 && herhangi(m, s, SELAM) && enPuan === 0 && !kategori)
      return Promise.resolve({ h: 'Merhaba, hoş geldiniz! 😊 Umre, Hac ve yurt dışı turlarımız hakkında merak ettiklerinizi sorabilirsiniz.' });
    if (s.length <= 4 && herhangi(m, s, TESEKKUR) && enPuan === 0 && !kategori)
      return Promise.resolve({ h: 'Rica ederiz! Başka bir sorunuz olursa buradayım. Hayırlı yolculuklar dileriz. 🌙' });

    if (ilePuan >= 2 && ilePuan >= enPuan)
      return Promise.resolve({ h: '📞 <a href="' + TEL_LINK + '">' + TEL + '</a><br>✉️ <a href="mailto:' + EPOSTA + '">' + EPOSTA + '</a><br>📍 ' + ADRES + '<br>Tüm iletişim bilgileri: <a href="iletisim.html">İletişim</a>', wa: 'Bilgi almak istiyorum.' });

    // Kategori + fiyat/tarih/program sorusu → canlı liste
    if (kategori === 'diger' && (fiyatSoru || tarihSoru || enPuan < 2)) {
      return turAdiylaBul(m, s).then(function (bulunan) {
        if (bulunan) return { h: (bulunan.length > 1 ? 'Şu programlarımızı buldum:' : 'Bu programımızı buldum:') + bulunan.slice(0, 4).map(turKart).join(''), wa: bulunan[0].baslik + ' hakkında bilgi almak istiyorum.' };
        return turListesiCevap('diger');
      });
    }
    if (kategori && (fiyatSoru || tarihSoru || enPuan < 2)) {
      return turListesiCevap(kategori).then(function (c) {
        if (enIyi && enPuan >= 2) c.h = enIyi.c + '<br><br>' + c.h;
        return c;
      });
    }
    // Belirli bir SSS cevabı
    if (enIyi && enPuan >= 2) {
      var c = { h: enIyi.c, wa: enIyi.wa };
      if (enIyi.ek && (fiyatSoru || tarihSoru)) return turListesiCevap(enIyi.ek).then(function (l) { c.h += '<br><br>' + l.h; return c; });
      return Promise.resolve(c);
    }
    // Tur adı geçiyor mu? (ör. "balkan", "ispanya")
    return turAdiylaBul(m, s).then(function (bulunan) {
      if (bulunan) return { h: (bulunan.length > 1 ? 'Şu programlarımızı buldum:' : 'Bu programımızı buldum:') + bulunan.slice(0, 4).map(turKart).join(''), wa: bulunan[0].baslik + ' hakkında bilgi almak istiyorum.' };
      if (fiyatSoru || tarihSoru) return { h: 'Hangi programla ilgileniyorsunuz? Aşağıdan Umre, Hac ya da yurt dışı turlarını seçebilirsiniz.', chips: ['Umre programları', 'Hac programları', 'Yurt dışı turları'] };
      if (enIyi && enPuan === 1) return { h: enIyi.c + '<br><br><span class="ca-not">Sorunuzu tam anlayamadıysam, ekibimize doğrudan sorabilirsiniz.</span>', wa: enIyi.wa };
      return { h: 'Bu soruyu en doğru şekilde ekibimiz cevaplar. 🙏 WhatsApp\'tan yazabilir, <a href="' + TEL_LINK + '">' + TEL + '</a> numarasından arayabilir ya da ilgilendiğiniz programın sayfasındaki <b>Kayıt Ol</b> formunu doldurabilirsiniz; size dönüş yapalım.', wa: 'Bir sorum var: ' + metin.slice(0, 200), oncelikWa: true };
    });
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

  var CIPLER = ['Umre programları', 'Hac programları', 'Yurt dışı turları', 'Ödeme ve taksit', 'Gerekli belgeler', 'İletişim'];
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
    if (c.wa) html += '<br><a class="ca-wa" target="_blank" rel="noopener" href="' + waLink(c.wa) + '">💬 WhatsApp\'tan sor</a>';
    mesajEkle(html, 'bot');
    if (c.chips) cipGoster(c.chips);
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
      setTimeout(function () { y.remove(); botCevap(c); cipGoster(CIPLER); }, Math.max(0, 450 - (Date.now() - bas)));
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
