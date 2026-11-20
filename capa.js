/* Sayfa içi bağlantı (ör. umre.html#rehber) düzeltmesi
   Tarayıcı bağlantıdaki bölüme hemen kayar; ama programlar ve yorumlar sonradan yüklenip
   üstte yer kaplayınca bölüm aşağı kayar ve ziyaretçi yanlış yerde kalır.
   Sayfa yüklenirken birkaç saniye boyunca, ziyaretçi kendisi kaydırmadığı sürece, bölümü yeniden başa getirir. */
(function () {
  var h = location.hash;
  if (!h || h.length < 2 || !('ResizeObserver' in window)) return;
  var hedef;
  try { hedef = document.getElementById(decodeURIComponent(h.slice(1))); } catch (e) { return; }
  if (!hedef) return;
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  var bitti = false, ro;
  function git() {
    if (bitti) return;
    var nav = document.querySelector('nav'), st = nav && getComputedStyle(nav).position;
    hedef.style.scrollMarginTop = (st === 'fixed' || st === 'sticky') ? nav.offsetHeight + 'px' : '';
    hedef.scrollIntoView({ block: 'start' });
  }
  function dur() { if (bitti) return; bitti = true; if (ro) ro.disconnect(); ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (o) { removeEventListener(o, dur, true); }); }
  ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (o) { addEventListener(o, dur, { capture: true, passive: true }); });
  ro = new ResizeObserver(git); ro.observe(document.body);
  addEventListener('load', function () { git(); setTimeout(git, 600); });
  setTimeout(function () { git(); dur(); }, 5000);
  git();
})();
