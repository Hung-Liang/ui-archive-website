const CACHE_NAME = 'ui-archive-v1';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './asset/icon.png',
  './scripts/theme.js',
  './scripts/render.js',
  './scripts/language.js',
  './data/index.json',
  './data/all_videos_index.json',
  './data/last_update.json'
];

// Install Service Worker
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Caching assets');
      return cache.addAll(ASSETS);
    })
  );
});

// Activate Service Worker
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
});

// Fetch events
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      return cachedResponse || fetch(event.request);
    })
  );
});
