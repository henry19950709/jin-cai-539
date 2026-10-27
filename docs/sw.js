const SHELL_CACHE = 'daily539-shell-v2';
const DATA_CACHE = 'daily539-data-v1';
const SHELL = [
  './',
  './index.html',
  './styles.css',
  './app.js',
  './logic.mjs',
  './manifest.webmanifest',
  './icons/icon.svg',
  './icons/icon-180.png',
  './icons/icon-192.png',
  './icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(Promise.all([
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL)),
    caches.open(DATA_CACHE).then((cache) => cache.add('./data/cache.json')),
  ]).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => ![SHELL_CACHE, DATA_CACHE].includes(key))
        .map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || !url.href.startsWith(self.registration.scope)) return;

  if (url.pathname.endsWith('/data/cache.json')) {
    event.respondWith(
      fetch(request).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          event.waitUntil(caches.open(DATA_CACHE).then((cache) => cache.put(request, copy)));
        }
        return response;
      }).catch(async () => (await caches.open(DATA_CACHE).then((cache) => cache.match(request)))
        || new Response('開獎資料無法離線讀取', { status: 503 })),
    );
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).then((response) => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.put('./index.html', copy)));
      }
      return response;
    }).catch(() => caches.match('./index.html')));
    return;
  }
  event.respondWith(fetch(request).then((response) => {
    if (response.ok) {
      const copy = response.clone();
      event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy)));
    }
    return response;
  }).catch(() => caches.match(request)));
});
