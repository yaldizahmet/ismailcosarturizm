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
- **Kesme işareti:** tur başlığında `'` ve `"` olsa da "Kayıt Ol" butonlarının çalıştığı.

Veritabanı (`supabase-js`) testte `mock.js` + `db.json` ile taklit edilir; gerçek veritabanına hiçbir şey yazılmaz. `db.json` gerçek turlara benzer örnek veridir; yeni bir tur türü ya da alan eklenirse buraya da eklenmeli.
