/* Service worker de avisos push.
   1) Si el push trae el texto (cifrado), lo muestra al instante.
   2) Si no, pide los mensajes pendientes al Worker (respaldo).
   Siempre muestra algo: iOS lo exige. */
const FALLBACK = { title: 'Aviso', body: 'Abre la app para ver la novedad.', tag: 'aviso' };
const hm = (t) => new Date(t).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'America/Santiago' });
async function cfg() {
  try { const r = await (await caches.open('push-cfg')).match('/cfg'); return r ? await r.json() : null; } catch (e) { return null; }
}
async function idOf(endpoint) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(endpoint));
  return [...new Uint8Array(d)].slice(0, 16).map((b) => b.toString(16).padStart(2, '0')).join('');
}
function show(m) {
  let body = m.body || '';
  // Si el aviso llegó muy tarde, lo dice (así no confunde un "en 10 min" viejo).
  if (m.ts && Date.now() - m.ts > 10 * 60e3) body += ` · enviado a las ${hm(m.ts)}`;
  return self.registration.showNotification(m.title || FALLBACK.title, { body, tag: m.tag || undefined, data: { url: m.url || './' } });
}
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('push', (event) => {
  event.waitUntil((async () => {
    let msgs = [];
    try { if (event.data) { const j = event.data.json(); if (j && j.title) msgs = [j]; } } catch (e) {}
    if (!msgs.length) {
      try {
        const c = await cfg();
        const sub = await self.registration.pushManager.getSubscription();
        if (c && sub) {
          const r = await fetch(c.worker + '/msg?id=' + await idOf(sub.endpoint), { cache: 'no-store' });
          msgs = ((await r.json()).messages) || [];
        }
      } catch (e) {}
    }
    if (!msgs.length) msgs = [FALLBACK];
    for (const m of msgs) await show(m);
  })());
});
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    if (all.length) return all[0].focus();
    return self.clients.openWindow((event.notification.data && event.notification.data.url) || './');
  })());
});
