const CACHE_NAME = 'auspoty-v3';
const STATIC_ASSETS = ['/', '/index.html', '/style.css', '/script.js', '/manifest.json'];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)).catch(() => {})
    );
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    e.waitUntil(clients.claim());
});

// Fetch: cache-first untuk static, network-first untuk API
self.addEventListener('fetch', (e) => {
    const url = e.request.url;
    // Jangan intercept YouTube/Google requests
    if (url.includes('youtube.com') || url.includes('googleapis.com') ||
        url.includes('gstatic.com') || url.includes('ytimg.com') ||
        url.includes('firestore') || url.includes('firebase')) {
        return;
    }
    e.respondWith(
        fetch(e.request).catch(() =>
            caches.match(e.request).then(r => r || new Response('Offline'))
        )
    );
});

// Background sync keep-alive — kirim pesan ke semua client setiap 25 detik
// agar tab tidak di-throttle browser saat background
self.addEventListener('message', (e) => {
    if (e.data && e.data.type === 'KEEP_ALIVE') {
        // Balas agar client tahu SW masih aktif
        e.ports[0] && e.ports[0].postMessage({ type: 'ALIVE' });
    }
});
