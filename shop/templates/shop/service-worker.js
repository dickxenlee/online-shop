{% load static %}
// Bump this when the shell/navbar changes so installed PWAs discard old UI.
const CACHE_NAME = 'meiyi-public-v2';
const HOME = '/';
const OFFLINE = '/offline/';
const STATIC_ASSETS = [
  '{% static "shop/favicon.svg" %}',
  '{% static "shop/manifest.webmanifest" %}',
  '{% static "shop/icons/icon-192.png" %}',
  '{% static "shop/icons/icon-512.png" %}'
];
const PRIVATE_PATHS = [
  '/admin/', '/account/', '/checkout/', '/order/', '/payment/', '/login/',
  '/logout/', '/password-reset/'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll([HOME, OFFLINE, ...STATIC_ASSETS]))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  const isPrivate = PRIVATE_PATHS.some(path => url.pathname.startsWith(path));

  if (request.method !== 'GET' || url.origin !== self.location.origin || isPrivate) {
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).then(response => {
        if (url.pathname === HOME && response.ok) {
          caches.open(CACHE_NAME).then(cache => cache.put(HOME, response.clone()));
        }
        return response;
      }).catch(() => caches.match(OFFLINE))
    );
    return;
  }

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then(cached => cached || fetch(request).then(response => {
        if (response.ok) {
          caches.open(CACHE_NAME).then(cache => cache.put(request, response.clone()));
        }
        return response;
      }))
    );
  }
});
