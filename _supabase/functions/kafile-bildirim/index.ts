// Supabase Edge Function: kafile-bildirim
// Bir grup duyurusu eklenince veritabanı tetikleyicisi (kafile_duyuru_bildir) bu fonksiyonu çağırır;
// fonksiyon o grubun bildirim açmış tüm telefonlarına Web Push bildirimi gönderir.
// Kimlik doğrulama: istek başlığındaki x-bildirim-anahtar, kasadaki (vault) anahtarla aynı olmalı.
// VAPID anahtarları da kasadan okunur; kodda gizli bilgi yoktur.
import webpush from "npm:web-push@3.6.7";
import { createClient } from "npm:@supabase/supabase-js@2.45.4";

const IZINLI = /^https:\/\/(fcm\.googleapis\.com|updates\.push\.services\.mozilla\.com|web\.push\.apple\.com|[a-z0-9.-]+\.push\.apple\.com|[a-z0-9.-]+\.notify\.windows\.com)\//;
const json = (v: unknown, durum = 200) => new Response(JSON.stringify(v), { status: durum, headers: { "Content-Type": "application/json" } });

function esit(a: string, b: string) { // sabit süreli karşılaştırma
  if (a.length !== b.length) return false;
  let f = 0;
  for (let i = 0; i < a.length; i++) f |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return f === 0;
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return json({ hata: "yalnızca POST" }, 405);
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });

  const { data: ayar, error: ayarHata } = await db.rpc("bildirim_ayarlari");
  if (ayarHata || !ayar?.bildirim_anahtar) return json({ hata: "ayarlar okunamadı" }, 500);
  if (!esit(req.headers.get("x-bildirim-anahtar") ?? "", ayar.bildirim_anahtar)) return json({ hata: "yetkisiz" }, 401);

  let duyuruId: number;
  try { duyuruId = Number((await req.json()).duyuru_id); } catch { return json({ hata: "geçersiz istek" }, 400); }
  if (!Number.isInteger(duyuruId)) return json({ hata: "geçersiz duyuru" }, 400);

  const { data: d } = await db.from("kafile_duyurular").select("id, kafile_id, baslik, metin, bildirim").eq("id", duyuruId).single();
  if (!d) return json({ hata: "duyuru bulunamadı" }, 404);
  if (!d.bildirim) return json({ gonderilen: 0, not: "bildirim kapalı" });
  const { data: k } = await db.from("kafileler").select("ad, aktif").eq("id", d.kafile_id).single();
  if (!k?.aktif) return json({ gonderilen: 0, not: "grup aktif değil" });
  const { data: aboneler } = await db.from("bildirim_abonelikleri").select("id, endpoint, p256dh, auth").eq("kafile_id", d.kafile_id);

  webpush.setVapidDetails("mailto:ismailcosarturizm@gmail.com", ayar.bildirim_vapid_public, ayar.bildirim_vapid_private);
  const icerik = JSON.stringify({
    baslik: d.baslik || "Yeni duyuru",
    metin: String(d.metin || "").slice(0, 180),
    grup: k.ad,
    etiket: "duyuru-" + d.id,
    url: "/kafile/?sekme=duyurular",
  });

  let gonderilen = 0, silinen = 0, hatali = 0;
  const hatalar: string[] = [];
  await Promise.all((aboneler ?? []).map(async (a) => {
    if (!IZINLI.test(a.endpoint)) { hatali++; return; }
    try {
      await webpush.sendNotification({ endpoint: a.endpoint, keys: { p256dh: a.p256dh, auth: a.auth } }, icerik, { TTL: 86400, urgency: "high" });
      gonderilen++;
    } catch (e) {
      const kod = (e as { statusCode?: number }).statusCode;
      if (kod === 404 || kod === 410) { // telefon uygulamayı kaldırmış ya da izni kapatmış: aboneliği sil
        await db.from("bildirim_abonelikleri").delete().eq("id", a.id); silinen++;
      } else { hatali++; if (hatalar.length < 3) hatalar.push(String(kod ?? (e as Error).message).slice(0, 120)); }
    }
  }));

  const sonuc = { gonderilen, silinen, hatali, toplam: (aboneler ?? []).length, hatalar, zaman: new Date().toISOString() };
  await db.from("kafile_duyurular").update({ bildirim_sonuc: sonuc }).eq("id", d.id);
  return json(sonuc);
});
