"""Kültür turu rehber yazılarını rehber-ravza-ziyareti.html şablonundan üretir (bir kez çalıştırılır; sonra sayfalar elle düzenlenebilir).
python3 _araclar/tur_yazilari.py"""
import json, os, re
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://ismailcosarturizm.com.tr/'
sablon = open(os.path.join(KOK, 'rehber-ravza-ziyareti.html'), encoding='utf-8').read()

KARTLAR = {
    'rehber-balkan-turu.html': ('🌍', 'Balkan Turuna Giderken', 'Vize, sınır geçişleri, para birimleri ve pratik bilgiler.'),
    'rehber-kultur-turu-valiz-listesi.html': ('🧳', 'Kültür Turu Valiz Listesi', 'Belgeler, kıyafet, ilaç ve günlük çanta için kontrol listesi.'),
    'sss.html': ('❓', 'Sıkça Sorulan Sorular', 'Kayıt, ödeme, belgeler ve yolculukla ilgili merak edilenler.'),
}
def kart(h):
    i, b, a = KARTLAR[h]
    return f'    <a class="rehber-kart" href="{h}"><span class="rehber-kart-ikon" aria-hidden="true">{i}</span><span><b>{b}</b><span>{a}</span></span></a>'

TABLO_CSS = """.yazi .tablo-kap{overflow-x:auto;margin:0 0 20px}
.yazi table{width:100%;border-collapse:collapse;font-size:15px}
@media(max-width:520px){.yazi table{font-size:13.5px}.yazi th,.yazi td{padding:8px 6px}}
.yazi th,.yazi td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:top}
.yazi th{background:var(--cream);color:var(--navy);font-weight:700}
.yazi .uyari{background:#fff6e5;border-left:4px solid var(--gold);padding:14px 16px;border-radius:0 var(--r) var(--r) 0;margin:0 0 20px}
"""

YAZILAR = [
 dict(dosya='rehber-balkan-turu.html', baslik='Balkan Turuna Giderken Bilmeniz Gerekenler', h1='Balkan Turuna <em>Giderken</em>',
      alt='Vize, para birimleri, sınır geçişleri ve pratik bilgiler', ikon='🌍',
      aciklama="Balkan turunda birkaç ülkeden geçilir. Hangi ülkede vize gerekir, hangi para kullanılır, sınır geçişlerinde nelere dikkat edilir? Kısaca anlattık.",
      govde="""<p>Balkan turumuz Kuzey Makedonya, Sırbistan, Bosna-Hersek, Karadağ, Arnavutluk ve Kosova'dan geçer. Her ülkenin kendi sınır kapısı, para birimi ve giriş kuralı vardır. Yola çıkmadan önce bilmeniz gerekenleri bir araya getirdik.</p>
<h2>Pasaport ve vize</h2>
<p>Turda birçok sınır geçildiği için <strong>pasaportunuzu mutlaka yanınıza alın</strong>. Pasaportunuzun dönüş tarihinden sonra en az 6 ay geçerli olması önerilir.</p>
<div class="tablo-kap"><table>
<thead><tr><th>Ülke</th><th>Türk vatandaşları için</th><th>Para birimi</th></tr></thead>
<tbody>
<tr><td>Kuzey Makedonya</td><td>Vize gerekmez (180 günde 90 gün)</td><td>Denar (MKD)</td></tr>
<tr><td>Sırbistan</td><td>Vize gerekmez (180 günde 90 gün)</td><td>Dinar (RSD)</td></tr>
<tr><td>Bosna-Hersek</td><td>Vize gerekmez (180 günde 90 gün)</td><td>Konvertibl mark (KM)</td></tr>
<tr><td>Karadağ</td><td><strong>1 Kasım 2026'dan beri vize gerekir</strong></td><td>Euro</td></tr>
<tr><td>Arnavutluk</td><td>Vize gerekmez (90 güne kadar)</td><td>Lek (ALL)</td></tr>
<tr><td>Kosova</td><td>Vize gerekmez (180 günde 90 gün)</td><td>Euro</td></tr>
</tbody></table></div>
<div class="uyari"><strong>Karadağ'a dikkat:</strong> Karadağ, 1 Kasım 2026'dan itibaren Türk vatandaşlarından vize istemeye başladı. Geçerli Schengen, ABD ya da İngiltere vizesi veya oturum izni olanlar belirli şartlarla 30 güne kadar vizesiz girebiliyor. Kayıt olmadan önce bu konuyu bizimle konuşun.</div>
<h2>Para</h2>
<ul>
<li>Her ülkenin parası farklıdır; Karadağ ve Kosova'da euro kullanılır.</li>
<li>Yanınıza bir miktar euro nakit alın. Diğer ülkelerde ihtiyacınız kadarını döviz bürosundan ya da ATM'den yerel paraya çevirebilirsiniz.</li>
<li>Bir ülkede kalan yerel parayı sonraki ülkede bozdurmak zor olabilir. Her ülkede ihtiyacınız kadar para çevirin.</li>
<li>Kredi kartı otellerde ve büyük mağazalarda geçer. Çarşılarda ve küçük dükkânlarda nakit daha kullanışlıdır.</li>
<li>Bankanıza yurt dışında kart kullanacağınızı önceden bildirin.</li>
</ul>
<h2>Telefon ve internet</h2>
<ul>
<li>Bu ülkeler Avrupa Birliği üyesi değildir; telefonunuzun yurt dışı (roaming) ücretleri yüksek olabilir.</li>
<li>Yola çıkmadan önce operatörünüzden bu ülkeleri kapsayan bir yurt dışı paketi isteyin.</li>
<li>Otellerin çoğunda ücretsiz Wi-Fi bulunur.</li>
</ul>
<h2>Elektrik prizi</h2>
<p>Bu ülkelerde Türkiye'deki prizlerin aynısı kullanılır. Şarj aletleriniz için ayrıca adaptör gerekmez.</p>
<h2>Yolculuk ve sınır geçişleri</h2>
<ul>
<li>Şehirler arası yolculuklar otobüsle yapılır; bazı günler yol uzundur. Boyun yastığı ve yanınızda su işinizi kolaylaştırır.</li>
<li>Sınır kapılarında bekleme olabilir. Pasaportunuzu el çantanızda, kolay ulaşabileceğiniz bir yerde tutun.</li>
<li>Sınır görevlileri otel ve dönüş bilgisi sorabilir; rehberiniz yol gösterir.</li>
</ul>
<h2>Kıyafet ve hava</h2>
<ul>
<li>Yazın gündüzler sıcak geçer, dağlık bölgelerde ve göl kenarlarında akşamlar serinleyebilir. Yanınıza ince bir hırka ya da mont alın.</li>
<li>Cami ve tekke ziyaretleri için omuzları ve dizleri kapatan kıyafetler giyin; hanımlar başörtüsü bulundursun.</li>
<li>Eski şehirlerin sokakları taş döşelidir. Rahat, daha önce giyilmiş bir ayakkabı tercih edin.</li>
</ul>
<p>Hazırlık için <a href="rehber-kultur-turu-valiz-listesi.html">Kültür Turu Valiz Listemize</a> de göz atın.</p>
<p class="yazi-tarih">Vize kuralları değişebilir; bilgiler Kasım 2026 itibarıyladır. Yola çıkmadan önce Dışişleri Bakanlığı'nın güncel duyurularını kontrol edin.</p>"""),
 dict(dosya='rehber-kultur-turu-valiz-listesi.html', baslik='Kültür Turu Valiz Listesi', h1='Kültür Turu <em>Valiz Listesi</em>',
      alt='Belgeler, kıyafet, ilaç ve günlük çanta için kontrol listesi', ikon='🧳',
      aciklama="Balkanlar, Endülüs ya da Özbekistan: yurt dışı kültür turuna çıkarken valizinize koymanız gerekenleri kontrol listesi olarak hazırladık.",
      govde="""<p>Kültür turlarında her gün yeni bir şehir gezilir, otel sık değişir. Valizi hafif ve düzenli tutmak yolculuğu kolaylaştırır. Aşağıdaki listeyi yola çıkmadan önce kontrol edebilirsiniz.</p>
<h2>Belgeler</h2>
<ul>
<li>Pasaport (dönüş tarihinden sonra en az 6 ay geçerli olması önerilir)</li>
<li>Gerekiyorsa vize (gideceğiniz ülkeye göre; Balkan turu için <a href="rehber-balkan-turu.html">Balkan yazımıza</a> bakın)</li>
<li>Kimlik kartı</li>
<li>Yurt dışı çıkış harcının ödendiğini gösteren belge (harç fiyata dahil değildir, önceden ödenir)</li>
<li>Uçak bileti ve otel bilgileri (telefonda ve çıktı olarak)</li>
<li>Pasaportunuzun fotokopisi ya da telefonda fotoğrafı</li>
</ul>
<h2>Para</h2>
<ul>
<li>Bir miktar euro nakit</li>
<li>Yurt dışında kullanıma açılmış banka ya da kredi kartı</li>
<li>Bozuk paralar için küçük bir cüzdan</li>
</ul>
<h2>Kıyafet</h2>
<ul>
<li>Mevsime uygun, rahat ve katmanlı giyilebilecek kıyafetler</li>
<li>İnce bir mont ya da hırka (akşamlar serin olabilir)</li>
<li>Katlanır şemsiye ya da yağmurluk</li>
<li>Cami ziyaretleri için omuzları ve dizleri kapatan kıyafet; hanımlar için başörtüsü</li>
<li>Akşam yemekleri için bir takım temiz, şık kıyafet</li>
</ul>
<h2>Ayakkabı</h2>
<ul>
<li>Rahat, daha önce giyilmiş yürüyüş ayakkabısı (yeni ayakkabı vurabilir)</li>
<li>Otel için hafif terlik</li>
<li>Camilerde ayakkabıyı koymak için küçük bez torba</li>
</ul>
<h2>İlaç ve kişisel bakım</h2>
<ul>
<li>Düzenli kullandığınız ilaçlar, yolculuk süresinden birkaç gün fazlasıyla, orijinal kutusunda</li>
<li>Reçete ya da ilaç raporunun bir kopyası</li>
<li>Ağrı kesici, mide ilacı, yara bandı</li>
<li>Güneş kremi, güneş gözlüğü, şapka</li>
<li>Diş fırçası, macun, tarak ve kişisel bakım ürünleri (uçakta sıvılar için kurallara dikkat edin)</li>
<li>Islak mendil ve el dezenfektanı</li>
</ul>
<h2>Elektronik</h2>
<ul>
<li>Telefon ve şarj aleti</li>
<li>Taşınabilir şarj cihazı (powerbank; uçakta el bagajında taşınmalıdır)</li>
<li>Gerekirse kulaklık</li>
</ul>
<h2>Günlük çanta</h2>
<p>Gezilerde yanınızda küçük bir sırt çantası bulunsun. İçinde su, pasaport, cüzdan, telefon, powerbank, şemsiye ve atıştırmalık olması gün boyu işinizi kolaylaştırır.</p>
<p class="yazi-tarih">Kafilemizdeki misafirler valiz listesini misafir uygulamamızdan işaretleyerek de takip edebilir.</p>"""),
]

def uret(y):
    d, url = y['dosya'], SITE + y['dosya']
    s = sablon
    eski_baslik, eski_acik = 'Ravza Ziyareti ve Nusuk Randevusu', "Ravza-i Mutahhara'ya girmek için Nusuk uygulamasından randevu gerekir. Randevu nasıl alınır, ziyaret kaç dakika sürer, nelere dikkat edilmeli?"
    s = s.replace('rehber-ravza-ziyareti.html"', d + '"').replace('rehber-ravza-ziyareti.html</', d + '</')
    s = s.replace(f'content="{eski_baslik} – İsmail Coşar Turizm"', f'content="{y["baslik"]} – İsmail Coşar Turizm"')
    s = s.replace(f'<title>{eski_baslik} | İsmail Coşar Turizm</title>', f'<title>{y["baslik"]} | İsmail Coşar Turizm</title>')
    s = s.replace(f'content="{eski_acik}"', 'content="' + y['aciklama'].replace('"', '&quot;') + '"')
    s = s.replace('og-umre.jpg', 'og-turlar.jpg')
    s = s.replace('.yazi ol{', TABLO_CSS + '.yazi ol{', 1)
    s = re.sub(r'<script type="application/ld\+json">\{"@context": "https://schema.org", "@type": "Article".*?</script>', lambda m: '<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org", "@type": "Article", "headline": y['baslik'], "description": y['aciklama'], "inLanguage": "tr",
        "datePublished": "2026-11-20", "dateModified": "2026-11-20", "image": SITE + "og-turlar.jpg", "mainEntityOfPage": url,
        "author": {"@type": "Organization", "name": "İsmail Coşar Turizm", "url": SITE},
        "publisher": {"@type": "Organization", "name": "İsmail Coşar Turizm", "logo": {"@type": "ImageObject", "url": SITE + "logo.png"}}}, ensure_ascii=False) + '</script>', s, flags=re.S)
    s = re.sub(r'<script type="application/ld\+json">\{"@context": "https://schema.org", "@type": "BreadcrumbList".*?</script>', lambda m: '<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": "Kültür Turları", "item": SITE + "turlar.html"},
            {"@type": "ListItem", "position": 3, "name": y['baslik'], "item": url}]}, ensure_ascii=False) + '</script>', s, flags=re.S)
    s = s.replace(f'<a href="umre.html">Umre</a> › <span>{eski_baslik}</span>', f'<a href="turlar.html">Kültür Turları</a> › <span>{y["baslik"]}</span>')
    s = s.replace('<div class="page-badge">🕌 Umre Rehberi</div>', f'<div class="page-badge">{y["ikon"]} Tur Rehberi</div>')
    s = s.replace('<h1>Ravza Ziyareti ve <em>Nusuk Randevusu</em></h1>', f'<h1>{y["h1"]}</h1>')
    s = s.replace('<p class="page-hero-desc">Randevu nasıl alınır, ziyaret kaç dakika sürer?</p>', f'<p class="page-hero-desc">{y["alt"]}</p>')
    i, j = s.index('  <div class="yazi">\n') + len('  <div class="yazi">\n'), s.index('  </div>\n  <div class="yazi-not">')
    s = s[:i] + y['govde'] + '\n' + s[j:]
    s = s.replace('umre%20hakk%C4%B1nda%20bilgi', 'k%C3%BClt%C3%BCr%20turlar%C4%B1%20hakk%C4%B1nda%20bilgi')
    i, j = s.index('<section class="diger-yazilar">'), s.index('</section>', s.index('<section class="diger-yazilar">')) + len('</section>')
    s = s[:i] + '<section class="diger-yazilar">\n  <h2>Diğer Rehber Yazıları</h2>\n  <div class="rehber-kartlar">\n' + '\n'.join(kart(h) for h in KARTLAR if h != d) + '\n  </div>\n</section>' + s[j:]
    i, j = s.index('<div class="cta-band">'), s.index('<footer>')
    s = s[:i] + """<div class="cta-band">
  <h2>Kültür Turlarımızı İnceleyin</h2>
  <p>Balkanlar, Endülüs ve Özbekistan programlarımız Kültür Turları sayfamızda.</p>
  <div class="cta-actions">
    <a href="turlar.html" class="btn-navy">🌍 Kültür Turları</a>
    <a href="https://wa.me/905331980781?text=Merhaba%2C%20k%C3%BClt%C3%BCr%20turlar%C4%B1%20hakk%C4%B1nda%20bilgi%20almak%20istiyorum." class="btn-wa" target="_blank" rel="noopener">💬 WhatsApp</a>
  </div>
</div>

""" + s[j:]
    assert 'Ravza Ziyareti ve <em>' not in s and 'Nusuk' not in s.split('<article')[1].split('</article>')[0] and len(y['baslik'] + ' | İsmail Coşar Turizm') <= 70, d
    open(os.path.join(KOK, d), 'w', encoding='utf-8').write(s)
    print('yazıldı', d, len(y['baslik'] + ' | İsmail Coşar Turizm'))

for y in YAZILAR: uret(y)
