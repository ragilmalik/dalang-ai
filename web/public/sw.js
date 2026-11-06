/* Dalang AI service worker: the public wall (/pentas, /gallery) and its shell keep working offline.
 * Pages: network first, the last good copy when offline. Build assets (/_next/static, hashed): cache first.
 * Posters and the hero clip: cache first, refreshed in the background. Never cached: /api (live data, votes,
 * uploads), film videos (range requests), anything that is not a GET. Any other page that cannot load while offline
 * gets a small offline page instead of the browser's error screen. */
const V = "dalang-r6-1";
const SHELL = ["/pentas", "/gallery", "/manifest.webmanifest", "/icon-192.png", "/hero/sample-poster.webp"];
const PAGES = /^\/(pentas|gallery|watch\/[^/]+)?$/;
const OFFLINE_HTML =
  '<!doctype html><html lang="id"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
  "<title>Dalang AI · offline</title>" +
  '<body style="background:#0C0A1E;color:#F5ECDE;font-family:sans-serif;text-align:center;padding:3rem 1.25rem;line-height:1.5">' +
  '<h1 style="color:#ECBA54;font-family:Georgia,serif">Dalang AI</h1>' +
  "<p>Sedang offline. Film baru dibuat lewat internet, jadi sambungkan dulu lalu muat ulang halaman ini.</p>" +
  '<p lang="en">You are offline. New films are made over the internet, so connect and reload this page.</p>' +
  '<p><a style="color:#ECBA54;display:inline-block;padding:.75rem 1rem" href="/pentas">Pentas</a> masih bisa dibuka · ' +
  '<span lang="en">The showcase still opens.</span></p>' +
  '<p><button onclick="location.reload()" style="font:inherit;padding:.75rem 1.25rem;border-radius:999px;border:0;' +
  'background:#ECBA54;color:#1C122E;font-weight:700">Muat ulang · Reload</button></p></html>';
const offline = () => new Response(OFFLINE_HTML, { headers: { "Content-Type": "text/html; charset=utf-8" } });

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches
      .open(V)
      .then((c) => Promise.all(SHELL.map((u) => c.add(new Request(u, { cache: "reload" })).catch(() => {}))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((ks) => Promise.all(ks.filter((k) => k !== V).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function networkFirst(req) {
  const c = await caches.open(V);
  try {
    const r = await fetch(req);
    if (r.ok) c.put(req, r.clone());
    return r;
  } catch {
    const hit = (await c.match(req, { ignoreSearch: false })) || (await c.match(new URL(req.url).pathname));
    return hit || offline();
  }
}

async function cacheFirst(req, refresh) {
  const c = await caches.open(V);
  const hit = await c.match(req);
  const net = fetch(req)
    .then((r) => {
      if (r.ok && r.status === 200) c.put(req, r.clone());
      return r;
    })
    .catch(() => null);
  if (hit) {
    if (refresh) net.catch(() => {});
    return hit;
  }
  return (await net) || Response.error();
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  const p = url.pathname;
  if (p.startsWith("/api/") || /\.(mp4|webm|m4a|wav)$/.test(p)) return;
  if (req.mode === "navigate") {
    if (PAGES.test(p)) e.respondWith(networkFirst(req));
    else e.respondWith(fetch(req).catch(offline)); // not cached (private films), just a kind page when offline
    return;
  }
  if (p.startsWith("/_next/static/")) return e.respondWith(cacheFirst(req, false));
  if (p.startsWith("/hero/") || /^\/media\/[^/]+\/poster\.jpg$/.test(p) || /^\/icon/.test(p))
    return e.respondWith(cacheFirst(req, true));
});
