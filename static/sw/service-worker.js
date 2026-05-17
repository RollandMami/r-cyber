/**
 * service-worker.js — R-CYBER Patrimoine
 * Gère : cache offline, IndexedDB, sync différée
 */

const APP_VERSION  = '1.0.0';
const CACHE_STATIC = `rcyber-static-v${APP_VERSION}`;
const CACHE_API    = `rcyber-api-v${APP_VERSION}`;
const CACHE_MODELS = `rcyber-models-v${APP_VERSION}`;
const DB_NAME      = 'rcyber-offline';
const DB_VERSION   = 1;

// ── Ressources à mettre en cache immédiatement ────────────────
const STATIC_PRECACHE = [
    '/',
    '/patrimoines/',
    '/static/viewer/js/viewer.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
];

// ── Installation ──────────────────────────────────────────────
self.addEventListener('install', event => {
    console.log(`[SW] Installation v${APP_VERSION}`);
    event.waitUntil(
        caches.open(CACHE_STATIC)
            .then(cache => cache.addAll(STATIC_PRECACHE))
            .then(() => self.skipWaiting())
    );
});

// ── Activation — nettoyage anciens caches ─────────────────────
self.addEventListener('activate', event => {
    console.log(`[SW] Activation v${APP_VERSION}`);
    const validCaches = [CACHE_STATIC, CACHE_API, CACHE_MODELS];
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => !validCaches.includes(k))
                    .map(k => { console.log(`[SW] Suppression cache obsolète: ${k}`); return caches.delete(k); })
            )
        ).then(() => self.clients.claim())
    );
});

// ── Interception des requêtes ─────────────────────────────────
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // 1. Fichiers JSON des modèles 3D → Cache-first (gros fichiers)
    if (url.pathname.startsWith('/media/patrimoines/json/')) {
        event.respondWith(cacheFirst(event.request, CACHE_MODELS));
        return;
    }

    // 2. Fichiers statiques → Cache-first
    if (url.pathname.startsWith('/static/') || url.hostname !== self.location.hostname) {
        event.respondWith(cacheFirst(event.request, CACHE_STATIC));
        return;
    }

    // 3. API arborescence → Network-first avec fallback IndexedDB
    if (url.pathname.includes('/api/') && url.pathname.includes('/arborescence/')) {
        event.respondWith(networkFirstWithIDB(event.request));
        return;
    }

    // 4. API géométrie viewer → Cache-first (données lourdes)
    if (url.pathname.includes('/geometrie/')) {
        event.respondWith(cacheFirst(event.request, CACHE_MODELS));
        return;
    }

    // 5. Pages HTML → Network-first avec fallback cache
    if (event.request.mode === 'navigate') {
        event.respondWith(networkFirstWithCache(event.request));
        return;
    }

    // 6. Autres → Network avec fallback cache
    event.respondWith(networkFirstWithCache(event.request));
});

// ── Stratégies de cache ───────────────────────────────────────

async function cacheFirst(request, cacheName) {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        return new Response('Ressource non disponible hors ligne', { status: 503 });
    }
}

async function networkFirstWithCache(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_API);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        const cached = await caches.match(request);
        if (cached) return cached;
        // Page offline de fallback
        return caches.match('/offline/') || new Response(offlinePage(), {
            headers: { 'Content-Type': 'text/html; charset=utf-8' }
        });
    }
}

async function networkFirstWithIDB(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const data = await response.clone().json();
            await idbSave('arborescences', data.id || request.url, data);
            const cache = await caches.open(CACHE_API);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        // Fallback IndexedDB
        const url    = new URL(request.url);
        const pk     = url.pathname.split('/').filter(Boolean).find(s => /^\d+$/.test(s));
        const cached = pk ? await idbGet('arborescences', pk) : null;
        if (cached) {
            return new Response(JSON.stringify(cached), {
                headers: { 'Content-Type': 'application/json' }
            });
        }
        return caches.match(request) || new Response('{}', { status: 503 });
    }
}

// ── Sync différée (Background Sync) ──────────────────────────
self.addEventListener('sync', event => {
    if (event.tag === 'sync-offline-changes') {
        console.log('[SW] Background sync déclenché');
        event.waitUntil(syncOfflineChanges());
    }
});

async function syncOfflineChanges() {
    const pending = await idbGetAll('pending-changes');
    console.log(`[SW] ${pending.length} modification(s) à synchroniser`);

    for (const change of pending) {
        try {
            const response = await fetch(change.url, {
                method:  change.method,
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': change.csrf },
                body:    JSON.stringify(change.data),
            });
            if (response.ok) {
                await idbDelete('pending-changes', change.id);
                console.log(`[SW] Sync OK: ${change.url}`);
                // Notifie le client
                const clients = await self.clients.matchAll();
                clients.forEach(c => c.postMessage({ type: 'SYNC_SUCCESS', change }));
            }
        } catch (err) {
            console.warn(`[SW] Sync échouée pour ${change.url}:`, err);
        }
    }
}

// ── Vérification de mise à jour ───────────────────────────────
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'CHECK_UPDATE') {
        checkForUpdate(event.source);
    }
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

async function checkForUpdate(client) {
    try {
        const response = await fetch('/api/version/', { cache: 'no-store' });
        if (!response.ok) return;
        const data = await response.json();
        if (data.version !== APP_VERSION) {
            client.postMessage({
                type:        'UPDATE_AVAILABLE',
                version:     data.version,
                apk_url:     data.apk_url,
                changelog:   data.changelog,
                current:     APP_VERSION,
            });
        }
    } catch { /* pas de connexion */ }
}

// ── IndexedDB helpers ─────────────────────────────────────────

function openDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = e => {
            const db = e.target.result;
            // Arborescences cachées
            if (!db.objectStoreNames.contains('arborescences'))
                db.createObjectStore('arborescences', { keyPath: 'id' });
            // Patrimoines pour consultation offline
            if (!db.objectStoreNames.contains('patrimoines'))
                db.createObjectStore('patrimoines', { keyPath: 'id' });
            // Modifications en attente de sync
            if (!db.objectStoreNames.contains('pending-changes'))
                db.createObjectStore('pending-changes', { keyPath: 'id', autoIncrement: true });
            // Documents téléchargés offline
            if (!db.objectStoreNames.contains('documents'))
                db.createObjectStore('documents', { keyPath: 'id' });
        };
        req.onsuccess = e => resolve(e.target.result);
        req.onerror   = e => reject(e.target.error);
    });
}

async function idbSave(store, key, value) {
    const db  = await openDB();
    return new Promise((resolve, reject) => {
        const tx  = db.transaction(store, 'readwrite');
        const obj = typeof value === 'object' ? { ...value, id: key } : { id: key, value };
        tx.objectStore(store).put(obj);
        tx.oncomplete = resolve;
        tx.onerror    = e => reject(e.target.error);
    });
}

async function idbGet(store, key) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx  = db.transaction(store, 'readonly');
        const req = tx.objectStore(store).get(key);
        req.onsuccess = e => resolve(e.target.result);
        req.onerror   = e => reject(e.target.error);
    });
}

async function idbGetAll(store) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx  = db.transaction(store, 'readonly');
        const req = tx.objectStore(store).getAll();
        req.onsuccess = e => resolve(e.target.result || []);
        req.onerror   = e => reject(e.target.error);
    });
}

async function idbDelete(store, key) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(store, 'readwrite');
        tx.objectStore(store).delete(key);
        tx.oncomplete = resolve;
        tx.onerror    = e => reject(e.target.error);
    });
}

// ── Page offline HTML ─────────────────────────────────────────
function offlinePage() {
    return `<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Hors ligne — R-CYBER</title>
    <style>
        body { font-family: system-ui, sans-serif; background: #0d0f1a; color: #fff;
               display: flex; align-items: center; justify-content: center;
               min-height: 100vh; margin: 0; flex-direction: column; gap: 1rem; }
        .icon { font-size: 3rem; }
        h1 { font-size: 1.4rem; margin: 0; }
        p  { color: rgba(255,255,255,0.5); font-size: 0.9rem; text-align: center; max-width: 280px; }
        button { background: #2196f3; border: none; border-radius: 10px;
                 color: #fff; padding: 0.75rem 2rem; font-size: 0.95rem;
                 cursor: pointer; margin-top: 0.5rem; }
    </style>
</head>
<body>
    <div class="icon">📡</div>
    <h1>Vous êtes hors ligne</h1>
    <p>Les données déjà consultées restent accessibles. Reconnectez-vous pour synchroniser.</p>
    <button onclick="location.reload()">Réessayer</button>
</body>
</html>`;
}
