const CACHE = "claudio-v3";
const SHELL = ["/", "/static/style.css", "/static/manifest.json"];

self.addEventListener("install", (e) => {
    e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
    self.skipWaiting();
});

self.addEventListener("activate", (e) => {
    e.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (e) => {
    // API 和 player.js 永远走网络
    if (e.request.url.includes("/api/") || e.request.url.includes("player.js")) return;
    e.respondWith(
        caches.match(e.request).then((cached) => cached || fetch(e.request))
    );
});
