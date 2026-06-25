/**
 * Fiissa — Service Worker offline receipts
 * Stratégie : Network-first, cache des 5 derniers reçus en fallback.
 * Cache les réponses /api/v1/receipts/my et /api/v1/receipts/{id}.
 */
const CACHE  = "fiissa-receipts-v1";
const MAX_RX = 5;

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

/* ── URL matching ── */
function isReceiptsList(url) {
  return (
    url.pathname.endsWith("/receipts/my") ||
    url.pathname.endsWith("/receipts/mine") ||
    url.pathname.endsWith("/receipts/my/")
  );
}

function isReceiptDetail(url) {
  return (
    /\/api\/v1\/receipts\/[a-zA-Z0-9_-]{6,}$/.test(url.pathname) &&
    !url.pathname.endsWith("/my") &&
    !url.pathname.endsWith("/verify") &&
    !url.pathname.endsWith("/export")
  );
}

/* ── Pre-cache last N individual receipts ── */
async function preCacheReceiptDetails(listBody, origin, cache) {
  try {
    const data  = JSON.parse(listBody);
    const items = Array.isArray(data) ? data : (data.items || data.results || []);
    const last5 = items.slice(0, MAX_RX);
    await Promise.all(
      last5.map(async (r) => {
        if (!r.id) return;
        const url = `${origin}/api/v1/receipts/${r.id}`;
        try {
          const res = await fetch(url, { credentials: "include" });
          if (res.ok) await cache.put(url, res);
        } catch {}
      })
    );
  } catch {}
}

/* ── Fetch handler ── */
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);
  if (!isReceiptsList(url) && !isReceiptDetail(url)) return;

  event.respondWith(
    fetch(event.request.clone(), { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) return response;

        const cache  = await caches.open(CACHE);
        const cloned = response.clone();
        await cache.put(event.request, response.clone());

        /* Pour la liste, pré-cacher les détails */
        if (isReceiptsList(url)) {
          const body = await cloned.text();
          await preCacheReceiptDetails(body, url.origin, cache);
        }

        return response;
      })
      .catch(async () => {
        const cache  = await caches.open(CACHE);
        const cached = await cache.match(event.request);
        if (cached) return cached;

        /* Fallback JSON générique offline */
        return new Response(
          JSON.stringify({ offline: true, items: [], message: "Mode hors ligne — données non disponibles" }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      })
  );
});
