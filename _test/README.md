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
- **Kesme işareti:** tur başlığında `'` ve `"` olsa da "Kayıt Ol" butonlarının çalıştığı.

Veritabanı (`supabase-js`) testte `mock.js` + `db.json` ile taklit edilir; gerçek veritabanına hiçbir şey yazılmaz. `db.json` gerçek turlara benzer örnek veridir; yeni bir tur türü ya da alan eklenirse buraya da eklenmeli.
