// Supabase Edge Function: dogum-gunu-mail  (haftalık özet e-postası; ad eski, pg_cron bu adı çağırıyor)
// Her pazartesi 09:00 (pg_cron, İstanbul) ofis e-postasına haftalık özet gönderir:
//   • son 7 günün ziyaretçileri (çerezsiz sayaç), en çok bakılan sayfalar, nereden gelindiği
//   • son 7 günde gelen başvurular
//   • son 7 günde doldurulan tur sonu anketleri
//   • önümüzdeki 7 günün doğum günleri (WhatsApp kutlama bağlantılarıyla)
// Kimlik doğrulama: x-bildirim-anahtar başlığı, kasadaki (vault) bildirim_anahtar ile aynı olmalı.
// E-posta, sitedeki başvuru formlarıyla aynı Web3Forms hesabından gider (erişim anahtarı zaten sitede açık; gizli değil).
// İstek gövdesi: {} → gönderir; {"deneme": true} → göndermeden metni döndürür; {"deneme_mail": true} → konusu "DENEME" ile gönderir.
import { createClient } from "npm:@supabase/supabase-js@2.45.4";

const WEB3FORMS = "e07b7888-be33-4c67-b2aa-01447f3586cf";
const PANEL = "https://ismailcosarturizm.com.tr/admin.html";
const json = (v: unknown, durum = 200) => new Response(JSON.stringify(v), { status: durum, headers: { "Content-Type": "application/json" } });

function esit(a: string, b: string) {
  if (a.length !== b.length) return false;
  let f = 0;
  for (let i = 0; i < a.length; i++) f |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return f === 0;
}
// İstanbul saatine göre bugünün tarihi (YYYY-MM-DD)
function bugunTR() { return new Date(Date.now() + 3 * 3600 * 1000).toISOString().slice(0, 10); }
function gunEkle(t: string, n: number) { const d = new Date(t + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
const GUNLER = ["Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"];
const AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
function guzelTarih(t: string) { const d = new Date(t + "T12:00:00Z"); return `${d.getUTCDate()} ${AYLAR[d.getUTCMonth()]} ${GUNLER[d.getUTCDay()]}`; }
function waNumara(tel: string) {
  let d = String(tel || "").replace(/\D/g, "");
  if (d.length === 10 && d[0] === "5") d = "90" + d; else if (d.length === 11 && d[0] === "0") d = "9" + d; else if (d.startsWith("00")) d = d.slice(2);
  return d.length >= 11 ? d : "";
}

const SAYFA_ADLARI: Record<string, string> = { "/": "Ana sayfa", "/umre.html": "Umre turları", "/hac.html": "Hac", "/turlar.html": "Tüm turlar", "/iletisim.html": "İletişim",
  "/hakkimizda.html": "Hakkımızda", "/belgelerimiz.html": "Belgelerimiz", "/galeri.html": "Galeri", "/sss.html": "Sık sorulan sorular", "/kvkk.html": "KVKK",
  "/tesekkurler.html": "Başvuru gönderildi (teşekkür sayfası)", "/kafile/": "Misafir uygulaması", "/rehber-ilk-umre.html": "Rehber: İlk umre",
  "/rehber-umre-donemleri.html": "Rehber: Umre dönemleri", "/rehber-umre-valiz-listesi.html": "Rehber: Valiz listesi" };
function kaynakAdi(k: string | null) {
  const s = String(k || "").toLowerCase();
  if (!s) return "Doğrudan / WhatsApp";
  if (/google/.test(s)) return "Google";
  if (/instagram/.test(s)) return "Instagram";
  if (/facebook|^fb|\.fb\./.test(s)) return "Facebook";
  return s;
}
const trGun = (iso: string) => new Date(new Date(iso).getTime() + 3 * 3600 * 1000).toISOString().slice(0, 10);
const say = <T,>(dizi: T[], anahtar: (x: T) => string) => { const g: Record<string, number> = {}; for (const x of dizi) { const a = anahtar(x); g[a] = (g[a] || 0) + 1; } return Object.entries(g).sort((a, b) => b[1] - a[1]); };

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return json({ hata: "yalnızca POST" }, 405);
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
  const { data: ayar, error: ayarHata } = await db.rpc("bildirim_ayarlari");
  if (ayarHata || !ayar?.bildirim_anahtar) return json({ hata: "ayarlar okunamadı" }, 500);
  if (!esit(req.headers.get("x-bildirim-anahtar") ?? "", ayar.bildirim_anahtar)) return json({ hata: "yetkisiz" }, 401);
  let g: { deneme?: boolean; deneme_mail?: boolean } = {};
  try { g = await req.json(); } catch { /* boş gövde */ }

  const bas = bugunTR(), bit = gunEkle(bas, 6), onceki = gunEkle(bas, -7);
  const haftaBasi = new Date(onceki + "T00:00:00+03:00").toISOString(); // geçen pazartesi 00:00 (İstanbul)
  const [zy, bv, an, mu, tl, kf] = await Promise.all([
    db.from("ziyaretler").select("zaman, sayfa, kaynak, ziyaretci").gte("zaman", haftaBasi).limit(20000),
    db.from("basvurular").select("created_at, ad_soyad, telefon, program, hizmet, form, durum").gte("created_at", haftaBasi).order("created_at"),
    db.from("kafile_anketler").select("kafile_id, rehber, otel, genel, yorum").gte("olusturma", haftaBasi),
    db.from("musteriler").select("id, ad, telefon, dogum_tarihi, ileti_izni").not("dogum_tarihi", "is", null),
    db.from("turlar").select("id, baslik"),
    db.from("kafileler").select("id, ad"),
  ]);
  const ilkHata = [zy, bv, an, mu, tl, kf].find((x) => x.error);
  if (ilkHata) return json({ hata: ilkHata.error!.message }, 500);
  const turAd: Record<string, string> = Object.fromEntries((tl.data ?? []).map((x) => [x.id, x.baslik]));
  const kafAd: Record<string, string> = Object.fromEntries((kf.data ?? []).map((k) => [k.id, k.ad]));
  const sayfaAdi = (s: string) => { const m = /^\/tur-detay\.html\?id=(.+)$/.exec(s); return m ? "Tur: " + (turAd[m[1]] || m[1]) : (SAYFA_ADLARI[s] || s); };
  const s: string[] = [];

  // 1) Ziyaretçiler (bugün hariç son 7 gün)
  const z = (zy.data ?? []).filter((x) => trGun(x.zaman) < bas);
  const kisi = new Set(z.map((x) => trGun(x.zaman) + x.ziyaretci)).size;
  s.push(`📊 ZİYARETÇİLER (${guzelTarih(onceki)} – ${guzelTarih(gunEkle(bas, -1))})`);
  if (z.length) {
    s.push(`${kisi} ziyaretçi · ${z.length} sayfa görüntüleme`, "", "En çok bakılan sayfalar:");
    say(z, (x) => x.sayfa).slice(0, 6).forEach(([ad, n]) => s.push(`   ${n} × ${sayfaAdi(ad)}`));
    s.push("", "Nereden geldiler: " + say(z, (x) => kaynakAdi(x.kaynak)).slice(0, 4).map(([ad, n]) => `${ad} (${n})`).join(", "));
  } else s.push("Bu hafta ziyaret kaydı yok.");

  // 2) Başvurular
  const b = bv.data ?? [];
  s.push("", "", `📥 BAŞVURULAR: ${b.length}`);
  b.forEach((x, i) => s.push(`${i + 1}) ${x.ad_soyad || "(isimsiz)"}${x.telefon ? " · " + x.telefon : ""}${x.program || x.hizmet ? " · " + (x.program || x.hizmet) : ""}${x.durum === "yeni" ? " · HENÜZ BAKILMADI" : ""}`));
  if (!b.length) s.push("Bu hafta yeni başvuru gelmedi.");

  // 3) Tur sonu anketleri
  const a = an.data ?? [];
  if (a.length) {
    s.push("", "", `📝 ANKET: ${a.length} yeni yanıt`);
    const ort = (l: typeof a, k: "rehber" | "otel" | "genel") => (l.reduce((t, x) => t + x[k], 0) / l.length).toFixed(1).replace(".", ",");
    for (const [kid] of say(a, (x) => x.kafile_id)) {
      const l = a.filter((x) => x.kafile_id === kid);
      s.push(`${kafAd[kid] || "Grup"}: ${l.length} yanıt · Rehber ${ort(l, "rehber")} · Otel ${ort(l, "otel")} · Genel ${ort(l, "genel")} (5 üzerinden)`);
      l.filter((x) => x.yorum).forEach((x) => s.push(`   “${String(x.yorum).slice(0, 300)}”`));
    }
  }

  // 4) Doğum günleri (bugün + 6 gün)
  const liste: { ad: string; gun: string; yas: number; tel: string; izin: boolean }[] = [];
  for (const m of mu.data ?? []) for (let i = 0; i <= 6; i++) {
    const t = gunEkle(bas, i);
    if (t.slice(5) === String(m.dogum_tarihi).slice(5)) liste.push({ ad: m.ad, gun: t, yas: Number(t.slice(0, 4)) - Number(String(m.dogum_tarihi).slice(0, 4)), tel: m.telefon || "", izin: !!m.ileti_izni });
  }
  liste.sort((x, y) => x.gun.localeCompare(y.gun) || x.ad.localeCompare(y.ad, "tr"));
  s.push("", "", `🎂 DOĞUM GÜNLERİ (${guzelTarih(bas)} – ${guzelTarih(bit)}): ${liste.length}`);
  liste.forEach((x, i) => {
    const no = x.izin ? waNumara(x.tel) : "";
    const mesaj = `Sayın ${x.ad}, doğum gününüzü en içten dileklerimizle kutlarız. Nice sağlıklı, huzurlu ve hayırlı yıllara… İsmail Coşar Turizm`;
    s.push(`${i + 1}) ${x.ad} – ${guzelTarih(x.gun)}${x.yas > 0 && x.yas < 120 ? ` (${x.yas} yaşına giriyor)` : ""}`,
      no ? `   WhatsApp ile kutla: https://wa.me/${no}?text=${encodeURIComponent(mesaj)}` : `   (${x.izin ? "telefon yok" : "ileti izni yok"})`);
  });
  if (!liste.length) s.push("Bu hafta doğum günü olan misafir yok.");

  s.push("", "", `Ayrıntılar için admin paneli: ${PANEL}`, "Bu e-posta her pazartesi 09:00'da otomatik gönderilir.");
  const metin = s.join("\n");
  const konu = `📊 Haftalık özet: ${kisi} ziyaretçi · ${b.length} başvuru · ${liste.length} doğum günü`;
  if (g.deneme) return json({ konu, metin });

  const r = await fetch("https://api.web3forms.com/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ access_key: WEB3FORMS, from_name: "İsmail Coşar Turizm – Haftalık Özet", subject: (g.deneme_mail ? "DENEME – " : "") + konu, "Haftalık özet": metin }),
  });
  const sonuc = await r.json().catch(() => ({}));
  if (!r.ok || !sonuc.success) return json({ hata: "e-posta gönderilemedi", durum: r.status, ayrinti: sonuc }, 502);
  return json({ gonderildi: true, konu });
});
