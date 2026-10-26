const CACHE_NAME = 'ui-archive-v5';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './asset/icon.png',
  './asset/thumbnail_placeholder.svg',
  './scripts/theme.js',
  './scripts/render.js',
  './styles/main.css',
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
    }).then(() => self.skipWaiting())
  );
});

// Activate Service Worker
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

function putInCache(request, response) {
  // Partial (206) and error responses cannot or should not be cached
  if (response.status === 200) {
    const copy = response.clone();
    caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
  }
  return response;
}

// Pages and data must stay fresh; fall back to cache only when offline
function networkFirst(request) {
  return fetch(request)
    .then((response) => putInCache(request, response))
    .catch((error) => {
      // month.html is the same page for every ?cat=&y=&m= combination
      return caches.match(request, { ignoreSearch: request.mode === 'navigate' }).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        throw error;
      });
    });
}

// Serve static assets from cache immediately, refresh them in the background
function staleWhileRevalidate(event, request) {
  return caches.match(request).then((cachedResponse) => {
    const networkFetch = fetch(request).then((response) => putInCache(request, response));
    if (cachedResponse) {
      event.waitUntil(
        networkFetch.catch((error) => console.warn('Background refresh failed:', request.url, error))
      );
      return cachedResponse;
    }
    return networkFetch;
  });
}

// Fetch events
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Let the browser handle analytics, YouTube thumbnails and non-GET requests
  if (request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  if (request.mode === 'navigate' || url.pathname.includes('/data/')) {
    event.respondWith(networkFirst(request));
  } else {
    event.respondWith(staleWhileRevalidate(event, request));
  }
});
