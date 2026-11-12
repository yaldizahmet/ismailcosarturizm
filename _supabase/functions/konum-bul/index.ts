// Konum bulma: admin rolündeki kullanıcı (panelden) ya da kasadaki bildirim_anahtar ile (veritabanından, pg_net) çağrılır.
// İşlemler:
//   link {url}            → Google Haritalar bağlantısından (kısa maps.app.goo.gl dahil) enlem/boylam
//   ara {q, sehir?}       → OpenStreetMap (Nominatim) araması: ad + şehir → enlem/boylam
//   rehber_toplu {limit?} → Şehir rehberinde konumu olmayan mekânları toplu bulur (şehir merkezine 25 km'den
//                           uzak sonuç kabul edilmez; bulunamayanlar 'bulunamadi' işaretlenir, haritada çıkmaz)
import { createClient } from 'npm:@supabase/supabase-js@2.45.4';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
const cevap = (govde: unknown, durum = 200) => new Response(JSON.stringify(govde), { status: durum, headers: { ...CORS, 'Content-Type': 'application/json' } });
const UA = 'IsmailCosarTurizm/1.0 (+https://ismailcosarturizm.com.tr)';
const bekle = (ms: number) => new Promise((r) => setTimeout(r, ms));
const gecerli = (lat: number, lng: number) => Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180 && !(lat === 0 && lng === 0);

function mesafeKm(a: number, b: number, c: number, d: number) {
  const r = Math.PI / 180, x = Math.sin((c - a) * r / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin((d - b) * r / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(x));
}

// Google Haritalar adresinden koordinat: önce yerin kendi noktası (!3d…!4d…), sonra ?q= / @ merkez
function adrestenKoordinat(s: string): { lat: number; lng: number } | null {
  let u = s; try { u = decodeURIComponent(s); } catch { /* bozuk % dizisi: olduğu gibi ara */ }
  const desen = [/!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)/, /[?&](?:q|query|ll|destination|center)=(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)/, /@(-?\d+\.\d+),(-?\d+\.\d+)/];
  for (const d of desen) { const m = d.exec(u); if (m && gecerli(+m[1], +m[2])) return { lat: +m[1], lng: +m[2] }; }
  return null;
}
const GOOGLE_ALAN = /^(maps\.app\.goo\.gl|goo\.gl|(www\.)?google\.[a-z.]+|maps\.google\.[a-z.]+)$/i;

async function linkCoz(adres: string) {
  let u: URL;
  try { u = new URL(adres); } catch { return { hata: 'Geçersiz bağlantı' }; }
  if (u.protocol !== 'https:' || !GOOGLE_ALAN.test(u.hostname)) return { hata: 'Yalnızca Google Haritalar bağlantısı kabul edilir' };
  let su = u.toString();
  for (let i = 0; i < 6; i++) {
    const k = adrestenKoordinat(su); if (k) return k;
    const r = await fetch(su, { redirect: 'manual', headers: { 'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'tr' } });
    const yer = r.headers.get('location');
    if (r.status >= 300 && r.status < 400 && yer) {
      const y = new URL(yer, su);
      if (y.protocol !== 'https:' || !GOOGLE_ALAN.test(y.hostname)) {
        // consent.google.com gibi ara sayfalar: asıl adres "continue" parametresinde
        const devam = y.searchParams.get('continue'); if (devam) { su = devam; continue; }
        return { hata: 'Bağlantı Google Haritalar dışına gidiyor' };
      }
      su = y.toString(); continue;
    }
    // Sayfanın içinde yerin koordinatı geçer: "…!3d21.4!4d39.8…" ya da [[[mesafe,boylam,enlem]
    const html = (await r.text()).slice(0, 600000);
    const k2 = adrestenKoordinat(html); if (k2) return k2;
    const m = /\[\[\[[\d.]+,(-?\d+\.\d+),(-?\d+\.\d+)\]/.exec(html);
    if (m && gecerli(+m[2], +m[1])) return { lat: +m[2], lng: +m[1] };
    break;
  }
  return { hata: 'Bağlantıdan konum çıkarılamadı. Haritada yere uzun basıp çıkan koordinatı (ör. 21.4189, 39.8262) yazabilirsiniz.' };
}

async function nominatim(q: string) {
  const u = 'https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&accept-language=tr&q=' + encodeURIComponent(q);
  const r = await fetch(u, { headers: { 'User-Agent': UA } });
  if (!r.ok) return null;
  const d = await r.json().catch(() => []);
  return d && d[0] && gecerli(+d[0].lat, +d[0].lon) ? { lat: +d[0].lat, lng: +d[0].lon, ad: String(d[0].display_name || '') } : null;
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS });
  if (req.method !== 'POST') return cevap({ hata: 'Yalnızca POST' }, 405);
  const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!, { auth: { persistSession: false } });
  const ic = req.headers.get('x-bildirim-anahtar');
  if (ic) {
    const { data: ayar } = await db.rpc('bildirim_ayarlari');
    const a = String(ayar?.bildirim_anahtar || '');
    let f = a.length === ic.length && a.length > 0 ? 0 : 1; for (let i = 0; i < Math.min(a.length, ic.length); i++) f |= a.charCodeAt(i) ^ ic.charCodeAt(i);
    if (f !== 0) return cevap({ hata: 'yetkisiz' }, 401);
  } else {
    const jeton = (req.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '');
    const { data: kim } = await db.auth.getUser(jeton);
    if (!kim?.user) return cevap({ hata: 'Oturum geçersiz' }, 401);
    const { data: rol } = await db.from('kullanici_rolleri').select('rol').eq('user_id', kim.user.id).maybeSingle();
    if (rol?.rol !== 'admin') return cevap({ hata: 'Bu işlem için yetkiniz yok' }, 403);
  }

  let g: Record<string, unknown> = {};
  try { g = await req.json(); } catch { return cevap({ hata: 'Geçersiz istek' }, 400); }

  if (g.islem === 'link') {
    const s = await linkCoz(String(g.url || ''));
    return cevap(s, 'hata' in s ? 422 : 200);
  }
  if (g.islem === 'ara') {
    const q = [String(g.q || '').trim(), String(g.sehir || '').trim()].filter(Boolean).join(', ').slice(0, 200);
    if (q.length < 3) return cevap({ hata: 'Arama metni kısa' }, 400);
    const s = await nominatim(q);
    return s ? cevap(s) : cevap({ hata: 'Bulunamadı' }, 404);
  }
  if (g.islem === 'rehber_toplu') {
    const limit = Math.min(Math.max(Number(g.limit) || 15, 1), 25); // Nominatim: saniyede en çok 1 istek
    const { data: liste, error } = await db.from('sehir_rehberi').select('id, sehir, ad, harita').is('lat', null).or('konum_kaynak.is.null,konum_kaynak.neq.bulunamadi').order('id').limit(limit);
    if (error) return cevap({ hata: error.message }, 500);
    const merkez: Record<string, { lat: number; lng: number } | null> = {};
    let bulunan = 0, bulunamayan = 0;
    for (const m of liste ?? []) {
      if (!(m.sehir in merkez)) { merkez[m.sehir] = await nominatim(m.sehir); await bekle(1100); }
      const c = merkez[m.sehir];
      // Önce Google bağlantısındaki koordinat (varsa), sonra ad + şehir araması
      let k: { lat: number; lng: number } | null = m.harita ? adrestenKoordinat(m.harita) : null;
      if (!k) { k = await nominatim(m.ad + ', ' + m.sehir); await bekle(1100); }
      if (!k) {
        const sorgu = /query=([^&]+)/.exec(m.harita || '');
        if (sorgu) { k = await nominatim(decodeURIComponent(sorgu[1])); await bekle(1100); }
      }
      const yakin = k && c ? mesafeKm(k.lat, k.lng, c.lat, c.lng) <= 25 : false;
      if (k && yakin) { await db.from('sehir_rehberi').update({ lat: k.lat, lng: k.lng, konum_kaynak: 'otomatik' }).eq('id', m.id); bulunan++; }
      else { await db.from('sehir_rehberi').update({ konum_kaynak: 'bulunamadi' }).eq('id', m.id); bulunamayan++; }
    }
    const { count } = await db.from('sehir_rehberi').select('id', { count: 'exact', head: true }).is('lat', null).or('konum_kaynak.is.null,konum_kaynak.neq.bulunamadi');
    return cevap({ islenen: (liste ?? []).length, bulunan, bulunamayan, kalan: count ?? 0 });
  }
  return cevap({ hata: 'Bilinmeyen işlem' }, 400);
});
