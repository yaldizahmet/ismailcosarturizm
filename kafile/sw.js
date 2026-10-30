/* Coşar Kafile – çevrimdışı çalışma için önbellek.
   Yalnızca /kafile/ klasörünü kapsar; sitenin geri kalanına karışmaz.
   Kafile verisi (Supabase) önbelleğe alınmaz; uygulama son veriyi kendi saklar. */
var SURUM = 'kafile-v1';
var KABUK = ['./', './index.html', './manifest.webmanifest', './ikon-192.png', './ikon-512.png'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(SURUM).then(function (c) { return c.addAll(KABUK); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (adlar) {
    return Promise.all(adlar.filter(function (a) { return a.indexOf('kafile-') === 0 && a !== SURUM; }).map(function (a) { return caches.delete(a); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (e) {
  var r = e.request;
  if (r.method !== 'GET') return;
  var url = new URL(r.url);
  // Sayfa açılışı: önce ağ (güncel sürüm), yoksa önbellek
  if (r.mode === 'navigate' && url.origin === location.origin) {
    e.respondWith(fetch(r).then(function (yanit) {
      var kopya = yanit.clone();
      caches.open(SURUM).then(function (c) { c.put('./index.html', kopya); });
      return yanit;
    }).catch(function () { return caches.match('./index.html'); }));
    return;
  }
  // Uygulama dosyaları ve Google yazı tipleri: önce önbellek, arkada güncelle
  var yazitipi = url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com';
  var uygulama = url.origin === location.origin && url.pathname.indexOf('/kafile/') === 0;
  if (!yazitipi && !uygulama) return;
  e.respondWith(caches.open(SURUM).then(function (c) {
    return c.match(r).then(function (eski) {
      var ag = fetch(r).then(function (yanit) { if (yanit && (yanit.ok || yanit.type === 'opaque')) c.put(r, yanit.clone()); return yanit; }).catch(function () { return eski; });
      return eski || ag;
    });
  }));
});
