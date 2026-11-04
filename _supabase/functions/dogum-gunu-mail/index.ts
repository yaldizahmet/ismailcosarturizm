// Supabase Edge Function: dogum-gunu-mail
// Her pazartesi 09:00'da (pg_cron, Europe/Istanbul) o haftanın (bugün + 6 gün) doğum günlerini
// ofis e-postasına gönderir. Doğum günü olan yoksa e-posta gönderilmez.
// Kimlik doğrulama: x-bildirim-anahtar başlığı, kasadaki (vault) bildirim_anahtar ile aynı olmalı.
// E-posta Resend ile gider; API anahtarı RESEND_API_KEY ortam sırrındadır (kodda gizli bilgi yoktur).
// İstek gövdesi: {} → normal çalışma; {"deneme": true} → göndermeden listeyi döndürür; {"zorla": true} → liste boşsa da gönderir.
import { createClient } from "npm:@supabase/supabase-js@2.45.4";

const ALICI = "ismailcosarturizm@gmail.com";
const GONDEREN = "İsmail Coşar Turizm <onboarding@resend.dev>";
const PANEL = "https://ismailcosarturizm.com.tr/admin.html";
const json = (v: unknown, durum = 200) => new Response(JSON.stringify(v), { status: durum, headers: { "Content-Type": "application/json" } });
const esc = (s: unknown) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));

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
  let g: { deneme?: boolean; zorla?: boolean } = {};
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
  if (!liste.length && !g.zorla) return json({ gonderildi: false, not: "bu hafta doğum günü yok" });

  const anahtar = Deno.env.get("RESEND_API_KEY");
  if (!anahtar) return json({ hata: "RESEND_API_KEY tanımlı değil" }, 500);
  const satirlar = liste.map((x) => {
    const no = x.izin ? waNumara(x.tel) : "";
    const mesaj = `Sayın ${x.ad}, doğum gününüzü en içten dileklerimizle kutlarız. Nice sağlıklı, huzurlu ve hayırlı yıllara… İsmail Coşar Turizm`;
    return `<tr><td style="padding:10px;border-bottom:1px solid #eee"><b>${esc(x.ad)}</b><br><span style="color:#777;font-size:13px">${esc((gruplar[x.id] || []).join(", "))}</span></td>
      <td style="padding:10px;border-bottom:1px solid #eee">${esc(guzelTarih(x.gun))}${x.yas > 0 && x.yas < 120 ? `<br><span style="color:#777;font-size:13px">${x.yas} yaşına giriyor</span>` : ""}</td>
      <td style="padding:10px;border-bottom:1px solid #eee">${no ? `<a href="https://wa.me/${no}?text=${encodeURIComponent(mesaj)}" style="background:#25D366;color:#fff;padding:8px 12px;border-radius:6px;text-decoration:none;font-weight:bold">WhatsApp ile kutla</a>` : `<span style="color:#999;font-size:13px">${x.izin ? "telefon yok" : "ileti izni yok"}</span>`}</td></tr>`;
  }).join("");
  const html = `<div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#0B1F3A">
    <h2 style="margin-bottom:4px">🎂 Bu haftanın doğum günleri</h2>
    <p style="color:#777;margin-top:0">${esc(guzelTarih(bas))} – ${esc(guzelTarih(bit))}</p>
    ${liste.length ? `<table style="width:100%;border-collapse:collapse;font-size:15px">${satirlar}</table>` : "<p>Bu hafta doğum günü olan misafir yok.</p>"}
    <p style="margin-top:24px"><a href="${PANEL}" style="color:#C9972B">Admin paneli</a> · Bu e-posta her pazartesi otomatik gönderilir.</p></div>`;
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${anahtar}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: GONDEREN, to: [ALICI], subject: `🎂 Bu hafta ${liste.length} misafirimizin doğum günü var`, html }),
  });
  const sonuc = await r.json().catch(() => ({}));
  if (!r.ok) return json({ hata: "e-posta gönderilemedi", durum: r.status, ayrinti: sonuc }, 502);
  return json({ gonderildi: true, kisi: liste.length, id: sonuc.id });
});
