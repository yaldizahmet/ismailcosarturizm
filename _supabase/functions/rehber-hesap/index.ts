// Rehber hesapları: yalnızca admin rolündeki kullanıcı çağırabilir (kimlik doğrulaması burada yapılır).
// İşlemler: olustur {ad, kullanici_adi, sifre} · sifre {user_id, sifre} · sil {user_id}
// Rehberin giriş adresi: <kullanici_adi>@rehber.ismailcosarturizm.com.tr (admin panelinde yalnızca kullanıcı adı yazılır)
import { createClient } from 'npm:@supabase/supabase-js@2.45.4';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
const ALAN = '@rehber.ismailcosarturizm.com.tr';
const cevap = (govde: unknown, durum = 200) => new Response(JSON.stringify(govde), { status: durum, headers: { ...CORS, 'Content-Type': 'application/json' } });

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS });
  if (req.method !== 'POST') return cevap({ hata: 'Yalnızca POST' }, 405);
  const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!, { auth: { persistSession: false } });

  const jeton = (req.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '');
  const { data: kim } = await db.auth.getUser(jeton);
  if (!kim?.user) return cevap({ hata: 'Oturum geçersiz' }, 401);
  const { data: rol } = await db.from('kullanici_rolleri').select('rol').eq('user_id', kim.user.id).maybeSingle();
  if (rol?.rol !== 'admin') return cevap({ hata: 'Bu işlem için yetkiniz yok' }, 403);

  let g: Record<string, string> = {};
  try { g = await req.json(); } catch { return cevap({ hata: 'Geçersiz istek' }, 400); }
  const sifreUygun = (s: string) => typeof s === 'string' && s.length >= 8 && s.length <= 72;

  // Yalnızca rehber hesapları değiştirilebilir/silinebilir (admin hesabına dokunulmaz)
  const rehberMi = async (id: string) => {
    const { data } = await db.from('kullanici_rolleri').select('rol').eq('user_id', id).maybeSingle();
    return data?.rol === 'rehber';
  };

  if (g.islem === 'olustur') {
    const ad = String(g.ad || '').trim(), ka = String(g.kullanici_adi || '').trim().toLowerCase();
    if (ad.length < 2) return cevap({ hata: 'Ad gerekli' }, 400);
    if (!/^[a-z0-9._-]{3,30}$/.test(ka)) return cevap({ hata: 'Kullanıcı adı 3-30 karakter olmalı; yalnızca küçük harf (Türkçe karaktersiz), rakam, nokta, tire' }, 400);
    if (!sifreUygun(g.sifre)) return cevap({ hata: 'Şifre en az 8 karakter olmalı' }, 400);
    const { data: y, error } = await db.auth.admin.createUser({ email: ka + ALAN, password: g.sifre, email_confirm: true, user_metadata: { ad } });
    if (error || !y.user) return cevap({ hata: /already|registered|exists/i.test(error?.message || '') ? 'Bu kullanıcı adı alınmış' : (error?.message || 'Oluşturulamadı') }, 400);
    const { error: e2 } = await db.from('kullanici_rolleri').insert({ user_id: y.user.id, rol: 'rehber', ad, kullanici_adi: ka });
    if (e2) { await db.auth.admin.deleteUser(y.user.id); return cevap({ hata: e2.message }, 400); }
    return cevap({ tamam: true, user_id: y.user.id });
  }
  if (g.islem === 'sifre') {
    if (!(await rehberMi(g.user_id))) return cevap({ hata: 'Rehber hesabı bulunamadı' }, 404);
    if (!sifreUygun(g.sifre)) return cevap({ hata: 'Şifre en az 8 karakter olmalı' }, 400);
    const { error } = await db.auth.admin.updateUserById(g.user_id, { password: g.sifre });
    if (error) return cevap({ hata: error.message }, 400);
    return cevap({ tamam: true });
  }
  if (g.islem === 'sil') {
    if (!(await rehberMi(g.user_id))) return cevap({ hata: 'Rehber hesabı bulunamadı' }, 404);
    const { error } = await db.auth.admin.deleteUser(g.user_id); // rol ve kafile atamaları da silinir (cascade)
    if (error) return cevap({ hata: error.message }, 400);
    return cevap({ tamam: true });
  }
  return cevap({ hata: 'Bilinmeyen işlem' }, 400);
});
