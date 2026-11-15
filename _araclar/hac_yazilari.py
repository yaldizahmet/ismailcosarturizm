"""Hac rehber yazılarını rehber-ravza-ziyareti.html şablonundan üretir (bir kez çalıştırılır; sonra sayfalar elle düzenlenebilir).
python3 _araclar/hac_yazilari.py"""
import json, os, re
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://ismailcosarturizm.com.tr/'
sablon = open(os.path.join(KOK, 'rehber-ravza-ziyareti.html'), encoding='utf-8').read()

KARTLAR = {
    'rehber-hac-nasil-yapilir.html': ('🕋', 'Hac Nasıl Yapılır? Adım Adım', '8–13 Zilhicce: ihram, Arafat, Müzdelife, Mina ve tavaf sırasıyla.'),
    'rehber-hac-kayit-kura.html': ('📝', 'Hac Kayıt ve Kura Süreci', 'Ön kayıt, kura, kesin kayıt: Diyanet sürecinin adımları.'),
    'rehber-hac-valiz-listesi.html': ('🧳', 'Hac Valiz Listesi', 'Belgeler, ihram, Mina ve Arafat çantası için kontrol listesi.'),
    'rehber-ravza-ziyareti.html': ('🕌', 'Ravza Ziyareti ve Nusuk Randevusu', "Medine'de Ravza için Nusuk uygulamasından randevu adım adım."),
    'rehber-yaslilar-icin-umre.html': ('🤲', 'İleri Yaşta Kutsal Topraklar', 'Sağlık, ilaç, otel ve tekerlekli sandalye önerileri.'),
}
def kart(h):
    i, b, a = KARTLAR[h]
    return f'    <a class="rehber-kart" href="{h}"><span class="rehber-kart-ikon" aria-hidden="true">{i}</span><span><b>{b}</b><span>{a}</span></span></a>'

YAZILAR = [
 dict(dosya='rehber-hac-nasil-yapilir.html', baslik='Hac Nasıl Yapılır? Adım Adım Hac', h1='Hac Nasıl Yapılır? <em>Adım Adım</em>',
      alt='8–13 Zilhicce günlerinde sırasıyla yapılanlar', ikon='🕋',
      aciklama="Hac, Zilhicce'nin 8–13. günlerinde Mekke, Mina, Arafat ve Müzdelife'de yapılır. İhramdan veda tavafına kadar hac günlerini adım adım anlattık.",
      govde="""<p>Hac, Zilhicce ayının 8–13. günleri arasında Mekke, Mina, Arafat ve Müzdelife'de yapılan ibadetlerden oluşur. Türkiye'den giden hacıların çoğu temettü haccı yapar: önce umre yapıp ihramdan çıkarlar, sonra hac için yeniden ihrama girerler. Aşağıdaki sıra temettü haccına göredir; kesin saatleri rehberiniz kafilenin programına göre bildirir.</p>
<h2>Hacdan önce: Umre</h2>
<p>Mekke'ye varışta mikatta umre için ihrama girilir. Kâbe tavaf edilir, Safa ile Merve arasında sa'y yapılır ve saç tıraşı ya da kısaltmasıyla ihramdan çıkılır. Hac günlerine kadar Mekke'de kalınır.</p>
<h2>8 Zilhicce (Terviye günü): Hac için ihram</h2>
<p>Hac için Mekke'de, kalınan yerden ihrama girilir. Kafileler programına göre bu gün Mina'ya ya da doğrudan Arafat'a geçer; kafilenizin planını rehberiniz bildirir.</p>
<h2>9 Zilhicce (Arefe günü): Arafat vakfesi</h2>
<p>Haccın en önemli rüknü Arafat'ta bulunmaktır (vakfe). Zeval vaktinden (öğle) güneş batımına kadar Arafat'ta dua ve zikirle vakit geçirilir; öğle ile ikindi namazı birlikte kılınır. Güneş batınca akşam namazı kılınmadan Müzdelife'ye hareket edilir.</p>
<h2>9'u 10'a bağlayan gece: Müzdelife</h2>
<p>Müzdelife'de akşam ve yatsı namazı birlikte kılınır, gece burada geçirilir. Bayram sabahı fecirden sonra kısa bir vakfe yapılır. Şeytan taşlamak için nohut büyüklüğünde taşlar genellikle burada toplanır: 13 Zilhicce'de de taşlayacaklar için 70, 12'sinde ayrılacaklar için 49 taş.</p>
<h2>10 Zilhicce (Bayramın 1. günü): Taşlama, kurban, tıraş, tavaf</h2>
<ol>
<li>Mina'da yalnızca büyük cemreye (Akabe) yedi taş atılır.</li>
<li>Temettü ve kıran haccı yapanlar şükran kurbanı keser; kurban vekaletle de kestirilebilir. Nasıl yapılacağını rehberiniz bildirir.</li>
<li>Saç tıraşı ya da kısaltmasıyla ihramdan çıkılır; eşlerle ilgili yasak ziyaret tavafına kadar devam eder.</li>
<li>Haccın farzı olan ziyaret (ifada) tavafı ve ardından sa'y yapılır. Bu tavaf bayramın ilk üç günü içinde yapılmalıdır.</li>
</ol>
<h2>11, 12 ve 13 Zilhicce: Mina'da taşlama</h2>
<p>Bayramın 2. ve 3. günü öğleden sonra üç cemreye sırasıyla (küçük, orta, büyük) yedişer taş atılır. 12 Zilhicce'de güneş batmadan Mina'dan ayrılmak caizdir; Mina'da kalan 13 Zilhicce'de de taşlar. Geceler Mina'daki çadırlarda geçirilir.</p>
<h2>Mekke'den ayrılırken: Veda tavafı</h2>
<p>Mekke'den ayrılmadan önce veda tavafı yapılır. Programına göre kafile hacdan önce ya da sonra Medine'ye gider; Ravza ziyareti için Nusuk randevusu gerekir (ayrıntılar <a href="rehber-ravza-ziyareti.html">Ravza yazımızda</a>).</p>
<h2>Pratik öneriler</h2>
<ul>
<li>Hac günlerinde sıcak ve kalabalık çok fazladır: yanınızda su, şemsiye ve rahat terlik bulunsun.</li>
<li>Kimlik kartınızı, bilekliğinizi ve otel kartınızı üzerinizden ayırmayın.</li>
<li>Mina ve Arafat'ta grubunuzdan ayrılmayın; buluşma noktalarını rehberinizden öğrenin.</li>
<li>Taşlamada kafilenin belirlediği saate uyun; en kalabalık saatlerden kaçınmak güvenlik için önemlidir.</li>
<li>Yaşlı ve hasta hacılar taşlama için vekalet verebilir; rehberinize danışın.</li>
</ul>
<p class="yazi-tarih">Bu yazı genel bilgilendirme amaçlıdır. Dini hükümlerle ilgili ayrıntılar için Diyanet İşleri Başkanlığı'nın hac rehberine ve kafile rehberinize başvurun.</p>"""),
 dict(dosya='rehber-hac-kayit-kura.html', baslik='Hac Kayıt ve Kura Süreci Nasıl İşler?', h1='Hac Kayıt ve <em>Kura Süreci</em>',
      alt='Ön kayıttan kesin kayda Diyanet sürecinin adımları', ikon='📝',
      aciklama="Hacca gitmek için Diyanet'e ön kayıt yaptırıp kurada hak kazanmak gerekir. Ön kayıt, kayıt yenileme, kura ve kesin kayıt adımlarını anlattık.",
      govde="""<p>Türkiye'den hacca gitmek için önce Diyanet İşleri Başkanlığı'na ön kayıt yaptırıp kurada hak kazanmak gerekir. Suudi Arabistan her ülkeye nüfusuna göre kontenjan verir. 2027 haccı için 1.878.046 aday kuraya katıldı, kontenjan 84.942 kişiydi.</p>
<h2>1. Ön kayıt ve kayıt yenileme</h2>
<ul>
<li>İlk kez başvuranlar ön kayıt, daha önce başvurmuş olanlar her yıl kayıt yenileme yapar.</li>
<li>İşlem e-Devlet'ten ya da il ve ilçe müftülüklerinden yapılır. Diyanet bilgi hattı: 0850 260 13 13.</li>
<li>2027 haccı için ilk kez başvuranlardan kişi başı 1.250 TL ön kayıt ücreti alındı; süre 19 Haziran 2026'da doldu.</li>
<li>2028 haccının tarihleri ve ücreti Diyanet tarafından açıklandığında bu yazıyı güncelleyeceğiz.</li>
</ul>
<h2>2. Kura</h2>
<ul>
<li>Kura her yıl yazın noter huzurunda çekilir; 2027 kurası 22 Temmuz 2026'da çekildi.</li>
<li>Sonuç e-Devlet'ten T.C. kimlik numarasıyla öğrenilir; Diyanet ayrıca kayıtlı telefona SMS gönderir.</li>
<li>Bekleme süresi uzadıkça adayın kura katsayısı yükselir, yani çıkma ihtimali artar. Yüksek katsayı tek başına hak kazandırmaz.</li>
<li>Asıl listedekiler kesin kayıt hakkı kazanır. Yedek listedekiler boş kalan yerlere sırayla çağrılır.</li>
</ul>
<h2>3. Kesin kayıt</h2>
<ul>
<li>Kurada çıkanlar belirtilen sürede e-Devlet'ten kesin kayıt yaptırır. 2027 için bu süre 30 Temmuz – 18 Ağustos 2026'ydı.</li>
<li>Kesin kayıtta hacca Diyanet organizasyonuyla mı, yetkili bir seyahat acentasıyla mı gidileceği seçilir.</li>
<li>Sağlık mazereti olan adaylar, heyet raporuyla il müftülüğüne dilekçe verip erteleme isteyebilir.</li>
</ul>
<h2>4. Yolculuk</h2>
<p>2027 haccında gidişlerin 17 Nisan – 11 Mayıs 2027, dönüşlerin 20 Mayıs – 15 Haziran 2027 arasında olması planlanıyor. Kafilenin kesin uçuş tarihleri kesin kayıttan sonra bildirilir.</p>
<h2>Kura sonucunuzu aldınız mı?</h2>
<p>Kesin kayıt adımlarıyla ilgili sorularınız için bizi arayabilir ya da WhatsApp'tan yazabilirsiniz. Hac programlarımızı <a href="hac.html">Hac sayfamızda</a> bulabilirsiniz.</p>
<p class="yazi-tarih">Tarih ve ücretler her yıl değişir; bilgiler Kasım 2026 itibarıyladır. En güncel bilgi için Diyanet İşleri Başkanlığı duyurularına ve müftülüklere başvurun.</p>"""),
 dict(dosya='rehber-hac-valiz-listesi.html', baslik='Hac Valiz Listesi: Mina ve Arafat Dahil', h1='Hac <em>Valiz Listesi</em>',
      alt='Belgeler, ihram, Mina ve Arafat çantası, sağlık', ikon='🧳',
      aciklama='Hac valizi umre valizinden farklıdır: Mina ve Arafat\'ta çadırda kalınır. Belgelerden ihrama, Mina çantasından ilaçlara hac valizi kontrol listesi.',
      govde="""<p>Hac valizi umre valizinden farklıdır: Mina ve Arafat'ta birkaç gün çadırda kalınır, sıcak ve kalabalık daha fazladır. Bu yüzden büyük valizin yanında Mina günleri için küçük bir sırt çantası hazırlayın. Bagaj hakkı havayoluna göre değişir; kafilenize ayrıca bildirilir.</p>
<h2>Belgeler</h2>
<ul>
<li>Pasaport (dönüş tarihinden sonra en az 6 ay geçerli) ve fotokopisi</li>
<li>Hac kimlik kartı ve bileklik (kafile tarafından verilir; hep üzerinizde olsun)</li>
<li>Aşı kartı (menenjit aşısı); o yıl istenen başka aşılar kesin kayıttan sonra bildirilir</li>
<li>Kullandığınız ilaçların raporu ya da reçetesi</li>
<li>Otel kartı ve rehberin telefon numarası (kâğıda yazılı)</li>
</ul>
<h2>İhram ve giyim</h2>
<ul>
<li>Erkekler için en az 2 takım ihram ve ihram kemeri</li>
<li>Kadınlar için rahat, terletmeyen, örtünmeye uygun kıyafetler</li>
<li>Rahat, kaymayan terlik ya da sandalet (Mina'da çok yürünür)</li>
<li>İnce bir hırka ya da şal (gece ve klimalı yerler için)</li>
</ul>
<h2>Mina ve Arafat çantası</h2>
<ul>
<li>Küçük sırt çantası ve bel çantası</li>
<li>Şişme yastık ya da küçük yastık, ince battaniye</li>
<li>Taş kesesi (Müzdelife'de toplanan taşlar için)</li>
<li>Şemsiye (güneş için) ve küçük su şişesi</li>
<li>Kokusuz sabun ve kokusuz ıslak mendil (ihramda kokulu ürün kullanılmaz)</li>
<li>Kulak tıkacı ve göz bandı (çadırda uyumak için)</li>
<li>Telefon şarj aleti ve powerbank</li>
</ul>
<h2>Sağlık</h2>
<ul>
<li>Düzenli kullandığınız ilaçlar (yolculuk süresinden fazla)</li>
<li>Ağrı kesici, ateş düşürücü, mide ilacı (doktorunuza danışarak)</li>
<li>Ayak bakımı için yara bandı ve pişik kremi</li>
<li>Kokusuz güneş kremi ve dudak koruyucu</li>
<li>Maske (kalabalıkta)</li>
</ul>
<h2>Dua ve ibadet</h2>
<ul>
<li>Cep boy Kur'an-ı Kerim, dua kitabı ya da dua listesi</li>
<li>Tesbih ve hafif, katlanabilir seccade</li>
</ul>
<p class="yazi-tarih">Kafilemizdeki misafirler bu listeyi misafir uygulamamızdan işaretleyerek de takip edebilir.</p>"""),
]

def uret(y):
    d, url = y['dosya'], SITE + y['dosya']
    s = sablon
    eski_baslik, eski_acik = 'Ravza Ziyareti ve Nusuk Randevusu', "Ravza-i Mutahhara'ya girmek için Nusuk uygulamasından randevu gerekir. Randevu nasıl alınır, ziyaret kaç dakika sürer, nelere dikkat edilmeli?"
    s = s.replace('rehber-ravza-ziyareti.html"', d + '"').replace('rehber-ravza-ziyareti.html</', d + '</')
    s = s.replace(f'content="{eski_baslik} – İsmail Coşar Turizm"', f'content="{y["baslik"]} – İsmail Coşar Turizm"')
    s = s.replace(f'<title>{eski_baslik} | İsmail Coşar Turizm</title>', f'<title>{y["baslik"]} | İsmail Coşar Turizm</title>')
    s = s.replace(f'content="{eski_acik}"', 'content="' + y['aciklama'].replace('"', '&quot;') + '"')
    s = s.replace('og-umre.jpg', 'og-hac.jpg')
    # JSON-LD
    s = re.sub(r'<script type="application/ld\+json">\{"@context": "https://schema.org", "@type": "Article".*?</script>', lambda m: '<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org", "@type": "Article", "headline": y['baslik'], "description": y['aciklama'], "inLanguage": "tr",
        "datePublished": "2026-11-15", "dateModified": "2026-11-15", "image": SITE + "og-hac.jpg", "mainEntityOfPage": url,
        "author": {"@type": "Organization", "name": "İsmail Coşar Turizm", "url": SITE},
        "publisher": {"@type": "Organization", "name": "İsmail Coşar Turizm", "logo": {"@type": "ImageObject", "url": SITE + "logo.png"}}}, ensure_ascii=False) + '</script>', s, flags=re.S)
    s = re.sub(r'<script type="application/ld\+json">\{"@context": "https://schema.org", "@type": "BreadcrumbList".*?</script>', lambda m: '<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": "Hac", "item": SITE + "hac.html"},
            {"@type": "ListItem", "position": 3, "name": y['baslik'], "item": url}]}, ensure_ascii=False) + '</script>', s, flags=re.S)
    # kahraman alan
    s = s.replace(f'<a href="umre.html">Umre</a> › <span>{eski_baslik}</span>', f'<a href="hac.html">Hac</a> › <span>{y["baslik"]}</span>')
    s = s.replace('<div class="page-badge">🕌 Umre Rehberi</div>', f'<div class="page-badge">{y["ikon"]} Hac Rehberi</div>')
    s = s.replace('<h1>Ravza Ziyareti ve <em>Nusuk Randevusu</em></h1>', f'<h1>{y["h1"]}</h1>')
    s = s.replace('<p class="page-hero-desc">Randevu nasıl alınır, ziyaret kaç dakika sürer?</p>', f'<p class="page-hero-desc">{y["alt"]}</p>')
    # gövde
    i, j = s.index('  <div class="yazi">\n') + len('  <div class="yazi">\n'), s.index('  </div>\n  <div class="yazi-not">')
    s = s[:i] + y['govde'] + '\n' + s[j:]
    s = s.replace('umre%20hakk%C4%B1nda%20bilgi', 'hac%20hakk%C4%B1nda%20bilgi')
    # diğer yazılar
    i, j = s.index('<section class="diger-yazilar">'), s.index('</section>', s.index('<section class="diger-yazilar">')) + len('</section>')
    s = s[:i] + '<section class="diger-yazilar">\n  <h2>Diğer Rehber Yazıları</h2>\n  <div class="rehber-kartlar">\n' + '\n'.join(kart(h) for h in KARTLAR if h != d) + '\n  </div>\n</section>' + s[j:]
    # CTA
    i, j = s.index('<div class="cta-band">'), s.index('<footer>')
    s = s[:i] + """<div class="cta-band">
  <h2>Hac Programlarımızı İnceleyin</h2>
  <p>Paketlerimiz ve kayıt bilgileri Hac sayfamızda.</p>
  <div class="cta-actions">
    <a href="hac.html" class="btn-navy">🕋 Hac Programları</a>
    <a href="https://wa.me/905331980781?text=Merhaba%2C%20hac%20program%C4%B1%20hakk%C4%B1nda%20bilgi%20almak%20istiyorum." class="btn-wa" target="_blank" rel="noopener">💬 WhatsApp</a>
    <a href="tel:+905331980781" class="btn-navy">📞 0533 198 07 81</a>
  </div>
</div>

""" + s[j:]
    assert 'Ravza Ziyareti ve <em>' not in s and len(y['baslik'] + ' | İsmail Coşar Turizm') <= 65, d
    open(os.path.join(KOK, d), 'w', encoding='utf-8').write(s)
    print('yazıldı', d, len(y['baslik'] + ' | İsmail Coşar Turizm'))

for y in YAZILAR: uret(y)
