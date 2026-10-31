/* Service worker de avisos push (sin contenido: pide el texto al Worker). */
const FALLBACK = { title: 'Aviso', body: 'Abre la app para ver la novedad.', tag: 'aviso' };
async function cfg() {
  try { const r = await (await caches.open('push-cfg')).match('/cfg'); return r ? await r.json() : null; } catch (e) { return null; }
}
async function idOf(endpoint) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(endpoint));
  return [...new Uint8Array(d)].slice(0, 16).map((b) => b.toString(16).padStart(2, '0')).join('');
}
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('push', (event) => {
  event.waitUntil((async () => {
    let msgs = [];
    try {
      const c = await cfg();
      const sub = await self.registration.pushManager.getSubscription();
      if (c && sub) {
        const r = await fetch(c.worker + '/msg?id=' + await idOf(sub.endpoint), { cache: 'no-store' });
        msgs = ((await r.json()).messages) || [];
      }
    } catch (e) {}
    if (!msgs.length) msgs = [FALLBACK]; // iOS exige mostrar siempre algo
    for (const m of msgs) {
      await self.registration.showNotification(m.title || FALLBACK.title, { body: m.body || '', tag: m.tag || undefined, data: { url: m.url || './' } });
    }
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
