# Site testleri

Bu klasör sitede yayınlanmaz (GitHub Pages, `_` ile başlayan klasörleri yayınlamaz).

```bash
bash _test/calistir.sh
```

Ne kontrol edilir:

- **JavaScript sözdizimi:** tüm sayfalardaki betikler ve `.js` dosyaları
- **Bağlantılar:** sayfalar arası geçişler, `#bölüm` çapaları, telefon / e-posta / WhatsApp bağlantıları
- **Butonlar:** masaüstü ve telefon boyutunda, her buton temiz bir sayfada tek tek tıklanır; hata veren, hiçbir şey yapmayan, üstü kapalı olanlar raporlanır. `onclick` içindeki her fonksiyonun sayfada tanımlı olduğu da kontrol edilir.
- **Formlar:** 6 başvuru formu doldurulup gönderilir; veritabanı kaydı, mail bildirimi ve "Talebiniz alındı" mesajı beklenir.
- **Admin paneli:** oturum açık sahte veritabanıyla bütün sekmeler, Düzenle/Kaydet, Kopyala ve Sil; asıl veriye dokunulmadığı kontrol edilir.
- **Rehber yazıları:** `rehber-*.html` sayfaları da bağlantı/buton taramasında; yeni bir rehber sayfası eklenirse `tara.py` PAGES listesine ve `calistir.sh` döngüsüne eklenmeli.
- **Kafile uygulaması (`kafile/`):** telefon boyutunda kod girişi (yanlış kod, internet yok), Bugün/Duyurular/Rehber/Vakitler/Acil ekranları, sayaç ve valiz listesinin kalıcılığı, paylaşılan `#KOD` bağlantısı, pasif kafile, çevrimdışı açılış, konum gönderme, kıble yönü, namaz vakitlerinin Ümmü'l-Kurâ referansıyla karşılaştırılması ve HTML enjeksiyonu. Uygulamadaki butonlar `onclick` yerine `data-sekme` / `data-eylem` kullanır; yeni bir eylem eklenirse `kafile.py`'ye testi eklenmeli.
- **Admin – Kafileler sekmesi:** kafile ekle/düzenle/sil, program satırları, otel bilgileri, duyuru yayınla/sil, paylaş bağlantısı.
- **Yolcu mesajları (`yorumlar.js`):** ana sayfada Google yorumlarının üstünde kaydırılan şerit, Umre sayfasında yalnızca umre mesajları, HTML enjeksiyonu, yalnızca kendi depomuzdaki fotoğraflar, "Devamını oku", fotoğraf büyütme, telefonda taşma; admin "Yorumlar" sekmesi (izin zorunlu, gizle/yayınla, sil).
- **Admin – Katılımcılar ve Müşteriler:** kafileye kişi ekleme (elle ve Excel'den yapıştırma; başlık satırı, tarih biçimleri, listede olan/hatalı tarih uyarısı), oda numarası düzenleme, kafileden çıkarma, oda listesini kopyalama, müşteri arama (isim/telefon), doğum gününe göre sıralama, ileti izni ve silme. Rehber hesapları (aç, kafile ata, şifre, sil) ve rehber rolüyle giriş: menüde yalnızca "Kafilelerim", yalnızca düzeltme (ekleme/çıkarma/ileti izni yok).
- **Şehir rehberi:** uygulamada kültür turunda Rehber ekranının en üstünde otel şehirlerine göre mekanlar (diğer adlarla eşleşme, şehir seçici, çevrimdışı), "Haritada aç", "Buradayım, paylaş" (yazı ve 1080×1350 fotoğraflı görsel); admin "Şehir Rehberi" sekmesi (taslak/yayın, toplu yayın, ekle, sil, https dışı bağlantı engeli).
- **Kesme işareti:** tur başlığında `'` ve `"` olsa da "Kayıt Ol" butonlarının çalıştığı.

Veritabanı (`supabase-js`) testte `mock.js` + `db.json` ile taklit edilir; gerçek veritabanına hiçbir şey yazılmaz. `db.json` gerçek turlara benzer örnek veridir; yeni bir tur türü ya da alan eklenirse buraya da eklenmeli.

## Ziyaret sayacı (`sayac.py`)

`sayac.js` her site sayfasında ve misafir uygulamasında olmalı, admin panelinde olmamalı. Test, gerçek alan adını taklit ederek gönderilen kaydı yakalar (veritabanına yazmaz): sayfa adı, kaynak, cihaz; botlar, otomatik tarayıcı ve localhost sayılmaz; veritabanına ulaşılamazsa sayfa etkilenmez. Yeni bir site sayfası eklenirse `<script src="sayac.js" defer></script>` eklenmeli ve admin panelindeki `SAYFA_ADLARI` listesine okunur adı yazılmalı.

Aynı dosya ayrıca SSS sayfasındaki soru-cevap etiketinin (FAQPage) görünen sorularla aynı olduğunu, JSON-LD bloklarının geçerli olduğunu ve ana sayfa başlık/açıklama uzunluklarını kontrol eder. SSS'ye soru eklenir ya da değişirse `python3 _araclar/sss_ld.py` çalıştırın.

## Anket, tur duyurusu, haftalık özet

- `kafile.py`: tur sonu anketi (dönüş günü kartı, yıldız zorunluluğu, gönderim, tekrar sormama, Değiştir).
- `admin.py`: Gruplar → Anket sonuçları (ortalama, yorumlar; rehber görmez) ve Tur Listesi → 📣 Duyur (yalnızca ileti izni + telefonu olanlar, {ad} yerleştirme, gönderildi işareti).
- Haftalık özet e-postası `_supabase/functions/dogum-gunu-mail` içinde; `{"deneme": true}` gövdesiyle çağrılınca göndermeden metni döndürür.

## Tur paylaşım sayfaları

`t/<id>.html` ve `t/<id>.jpg` dosyalarını `.github/workflows/tur-onizleme.yml` saatte bir yeniden üretir (elle düzenlemeyin). Üreten betik `_araclar/tur_onizleme.py`. `sayac.py` her sayfanın önizleme etiketlerini, doğru tura yönlendirmesini ve site haritasını kontrol eder.
