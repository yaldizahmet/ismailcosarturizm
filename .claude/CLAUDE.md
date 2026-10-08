# İsmail Coşar Turizm sitesi

Statik site (GitHub Pages, ismailcosarturizm.com.tr) + Supabase (turlar, duyurular, basvurular). Admin paneli: admin.html.

## Yayına almadan önce ZORUNLU

Siteye yapılan HER değişiklikten sonra, commit/push etmeden önce:

```bash
bash _test/calistir.sh
```

Sonuç "TEMİZ" değilse yayına alma. Yeni bir buton, form, sayfa ya da `onclick` fonksiyonu eklendiyse testin onu kapsadığını kontrol et (`_test/README.md`).

## Veriyle ilgili tespitler

"Boş", "eksik", "yok" gibi bir tespiti kullanıcıya söylemeden önce ilgili kaydın ham satırına bak (`select *`). Örnek: tur fiyatı `fiyat` alanında olabilir, `fiyat_2/3/4` boş olsa bile; `coalesce` boş string'i atlamaz.

## Notlar

- Repo public olmak zorunda (ücretsiz GitHub Pages).
- `_` ve `.` ile başlayan klasörler yayınlanmaz; `.md` dosyalarını köke koyma (Jekyll onları sayfaya çevirir).
- İçerik ve politika kararları Ümit Bey'den gelir; onaylanmamış iddia (lisans, sayı, taahhüt) ekleme.
