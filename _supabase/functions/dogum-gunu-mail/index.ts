// Supabase Edge Function: dogum-gunu-mail
// Her pazartesi 09:00 (pg_cron, İstanbul) o haftanın (bugün + 6 gün) doğum günlerini
// ofis e-postasına gönderir. Doğum günü olan yoksa e-posta gönderilmez.
// Kimlik doğrulama: x-bildirim-anahtar başlığı, kasadaki (vault) bildirim_anahtar ile aynı olmalı.
// E-posta, sitedeki başvuru formlarıyla aynı Web3Forms hesabından gider (erişim anahtarı zaten sitede açık; gizli değil).
// İstek gövdesi: {} → normal çalışma; {"deneme": true} → göndermeden listeyi döndürür; {"deneme_mail": true} → konusu "DENEME" olan bir e-posta gönderir.
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

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return json({ hata: "yalnızca POST" }, 405);
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
  const { data: ayar, error: ayarHata } = await db.rpc("bildirim_ayarlari");
  if (ayarHata || !ayar?.bildirim_anahtar) return json({ hata: "ayarlar okunamadı" }, 500);
  if (!esit(req.headers.get("x-bildirim-anahtar") ?? "", ayar.bildirim_anahtar)) return json({ hata: "yetkisiz" }, 401);
  let g: { deneme?: boolean; deneme_mail?: boolean } = {};
  try { g = await req.json(); } catch { /* boş gövde */ }

  const bas = bugunTR(), bit = gunEkle(bas, 6);
  const { data: mus, error } = await db.from("musteriler").select("id, ad, telefon, dogum_tarihi, ileti_izni").not("dogum_tarihi", "is", null);
  if (error) return json({ hata: error.message }, 500);
  const liste: { ad: string; gun: string; yas: number; tel: string; izin: boolean; id: string }[] = [];
  for (const m of mus ?? []) {
    for (let i = 0; i <= 6; i++) {
      const t = gunEkle(bas, i);
      if (t.slice(5) === String(m.dogum_tarihi).slice(5)) {
        liste.push({ id: m.id, ad: m.ad, gun: t, yas: Number(t.slice(0, 4)) - Number(String(m.dogum_tarihi).slice(0, 4)), tel: m.telefon || "", izin: !!m.ileti_izni });
      }
    }
  }
  liste.sort((a, b) => a.gun.localeCompare(b.gun) || a.ad.localeCompare(b.ad, "tr"));

  // Hangi gruplarla gitti?
  const gruplar: Record<string, string[]> = {};
  if (liste.length) {
    const { data: kat } = await db.from("kafile_katilimcilar").select("musteri_id, kafile_id").in("musteri_id", liste.map((x) => x.id));
    const { data: kaf } = await db.from("kafileler").select("id, ad");
    const ad: Record<string, string> = Object.fromEntries((kaf ?? []).map((k) => [k.id, k.ad]));
    for (const k of kat ?? []) (gruplar[k.musteri_id] = gruplar[k.musteri_id] || []).push(ad[k.kafile_id] || "");
  }
  if (g.deneme) return json({ bas, bit, liste });
  if (!liste.length && !g.deneme_mail) return json({ gonderildi: false, not: "bu hafta doğum günü yok" });

  // Web3Forms düz metin gönderir; her kişi ayrı paragraf, WhatsApp bağlantısı tıklanabilir
  const metin = [
    `${guzelTarih(bas)} – ${guzelTarih(bit)} arasında doğum günü olan misafirlerimiz:`, "",
    ...(liste.length ? liste.map((x, i) => {
      const no = x.izin ? waNumara(x.tel) : "";
      const mesaj = `Sayın ${x.ad}, doğum gününüzü en içten dileklerimizle kutlarız. Nice sağlıklı, huzurlu ve hayırlı yıllara… İsmail Coşar Turizm`;
      return [`${i + 1}) ${x.ad} – ${guzelTarih(x.gun)}${x.yas > 0 && x.yas < 120 ? ` (${x.yas} yaşına giriyor)` : ""}`,
        (gruplar[x.id] || []).length ? `   Gruplar: ${gruplar[x.id].join(", ")}` : "",
        no ? `   WhatsApp ile kutla: https://wa.me/${no}?text=${encodeURIComponent(mesaj)}` : `   (${x.izin ? "telefon yok" : "ileti izni yok"})`, ""].filter(Boolean).join("\n");
    }) : ["Bu hafta doğum günü olan misafir yok."]),
    "", `Admin paneli: ${PANEL}`, "Bu e-posta her pazartesi 09:00'da otomatik gönderilir.",
  ].join("\n");
  const r = await fetch("https://api.web3forms.com/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ access_key: WEB3FORMS, from_name: "İsmail Coşar Turizm – Doğum Günleri",
      subject: (g.deneme_mail ? "DENEME – " : "") + `🎂 Bu hafta ${liste.length} misafirimizin doğum günü var`, "Doğum günleri": metin }),
  });
  const sonuc = await r.json().catch(() => ({}));
  if (!r.ok || !sonuc.success) return json({ hata: "e-posta gönderilemedi", durum: r.status, ayrinti: sonuc }, 502);
  return json({ gonderildi: true, kisi: liste.length });
});
