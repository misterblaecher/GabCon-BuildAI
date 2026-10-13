/* GabCon Studio PWA: static shell only; NEVER cache builds, blueprints or API data. */
'use strict';
const CACHE = 'gabcon-studio-shell-v3';
const STATIC = ['/', '/style.css', '/app.js', '/prompt.js', '/formats.js', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png'];
const ALLOWED = new Set(STATIC);
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(STATIC)).then(() => self.skipWaiting())
  );
});
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('gabcon-studio-shell-') && key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  // Only app shell may be cached. No secrets, API responses, renders, or exports.
  if (url.origin !== self.location.origin || !ALLOWED.has(url.pathname)) return;
  event.respondWith(
    fetch(event.request).then(response => {
      if (response.ok && response.type === 'basic') {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then(cache => cache.put(event.request, copy)));
      }
      return response;
    }).catch(async () => (await caches.match(event.request)) || Response.error())
  );
});
