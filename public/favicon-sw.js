self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('favicon-cache-v3').then((cache) => {
      return cache.addAll([
        '/images/1.png?v=2',
      ]);
    })
  );
});

// Force activation
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(keyList.map((key) => {
        if (key !== 'favicon-cache-v3' && key.includes('favicon-cache')) {
          return caches.delete(key);
        }
      }));
    })
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.url.includes('/images/1.png')) {
    event.respondWith(
      caches.match('/images/1.png?v=2')
        .then((response) => {
          return response || fetch(event.request);
        })
    );
  }
}); 