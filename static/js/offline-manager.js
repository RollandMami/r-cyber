/**
 * offline-manager.js
 * Gère : enregistrement SW, sync offline, bannière connexion, file d'attente
 */

const OfflineManager = (function () {

    const DB_NAME    = 'rcyber-offline';
    const DB_VERSION = 1;
    let   db         = null;
    let   isOnline   = navigator.onLine;

    // ── Init ──────────────────────────────────────────────────
    async function init() {
        await _openDB();
        await _registerSW();
        _setupConnectivityListeners();
        _renderStatusBanner();
        console.log('[Offline] Manager initialisé, en ligne:', isOnline);
    }

    // ── Service Worker ────────────────────────────────────────
    async function _registerSW() {
        if (!('serviceWorker' in navigator)) return;
        try {
            const reg = await navigator.serviceWorker.register('/static/sw/service-worker.js', {
                scope: '/'
            });
            console.log('[SW] Enregistré:', reg.scope);

            // Écoute les messages du SW
            navigator.serviceWorker.addEventListener('message', _onSWMessage);

            // Vérifie les mises à jour au démarrage
            reg.addEventListener('updatefound', () => {
                const newWorker = reg.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        _showUpdateBanner();
                    }
                });
            });

            // Demande au SW de vérifier la version APK
            if (reg.active) {
                reg.active.postMessage({ type: 'CHECK_UPDATE' });
            }
        } catch (err) {
            console.error('[SW] Échec enregistrement:', err);
        }
    }

    function _onSWMessage(event) {
        const { type, version, apk_url, changelog } = event.data;
        if (type === 'UPDATE_AVAILABLE') {
            _showAPKUpdateDialog(version, apk_url, changelog);
        }
        if (type === 'SYNC_SUCCESS') {
            _showToast('✅ Synchronisation réussie', 'success');
        }
    }

    // ── Connectivité ──────────────────────────────────────────
    function _setupConnectivityListeners() {
        window.addEventListener('online', () => {
            isOnline = true;
            _renderStatusBanner();
            _triggerSync();
            _showToast('🟢 Connexion rétablie — synchronisation en cours…', 'success');
        });
        window.addEventListener('offline', () => {
            isOnline = false;
            _renderStatusBanner();
            _showToast('🔴 Hors ligne — les modifications seront synchronisées plus tard', 'warning');
        });
    }

    function _renderStatusBanner() {
        let banner = document.getElementById('offline-banner');
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'offline-banner';
            banner.style.cssText = `
                position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
                padding: 0.5rem 1rem; font-size: 0.82rem; font-weight: 600;
                text-align: center; transition: all 0.3s ease;
                display: flex; align-items: center; justify-content: center; gap: 0.5rem;
            `;
            document.body.prepend(banner);
        }
        if (isOnline) {
            banner.style.display = 'none';
        } else {
            banner.style.display = 'flex';
            banner.style.background = '#b91c1c';
            banner.style.color      = '#fff';
            banner.innerHTML = '📡 Mode hors ligne — données locales affichées';
        }
    }

    // ── File d'attente des modifications ──────────────────────

    /**
     * Enregistre une modification à synchroniser plus tard.
     * Utilisé à la place d'un fetch() direct quand hors ligne.
     */
    async function queueChange(url, method, data, csrfToken) {
        const change = { url, method, data, csrf: csrfToken, timestamp: Date.now() };
        await _idbAdd('pending-changes', change);
        console.log('[Offline] Modification mise en file:', url);
        _showToast('📝 Modification enregistrée localement', 'info');

        // Essaie une sync immédiate si en ligne
        if (isOnline) await _triggerSync();
    }

    /**
     * Remplace fetch() pour les formulaires — gère online/offline automatiquement.
     */
    async function smartFetch(url, options = {}) {
        if (isOnline) {
            try {
                const response = await fetch(url, options);
                return response;
            } catch {
                isOnline = false;
                _renderStatusBanner();
            }
        }
        // Hors ligne — met en file
        if (options.method && options.method !== 'GET') {
            const csrf = options.headers?.['X-CSRFToken'] ||
                         document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
            let data = {};
            if (options.body instanceof FormData) {
                options.body.forEach((v, k) => { data[k] = v; });
            } else if (typeof options.body === 'string') {
                try { data = JSON.parse(options.body); } catch { data = { raw: options.body }; }
            }
            await queueChange(url, options.method, data, csrf);
        }
        // Retourne une réponse fictive pour ne pas casser le flux UI
        return new Response(JSON.stringify({ offline: true, queued: true }), {
            status: 202, headers: { 'Content-Type': 'application/json' }
        });
    }

    async function _triggerSync() {
        if (!('serviceWorker' in navigator)) return;
        const reg = await navigator.serviceWorker.ready;
        if ('sync' in reg) {
            await reg.sync.register('sync-offline-changes');
            console.log('[Offline] Background sync enregistré');
        } else {
            // Fallback si Background Sync non supporté
            await _syncNow();
        }
    }

    async function _syncNow() {
        const pending = await _idbGetAll('pending-changes');
        if (pending.length === 0) return;
        console.log(`[Offline] Sync manuelle: ${pending.length} élément(s)`);
        for (const change of pending) {
            try {
                const response = await fetch(change.url, {
                    method:  change.method,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken':  change.csrf,
                    },
                    body: JSON.stringify(change.data),
                });
                if (response.ok) {
                    await _idbDelete('pending-changes', change.id);
                    _showToast(`✅ Synchronisé: ${change.url}`, 'success');
                }
            } catch (err) {
                console.warn('[Offline] Sync échouée:', err);
            }
        }
    }

    // ── Bannières UI ──────────────────────────────────────────

    function _showUpdateBanner() {
        const banner = document.createElement('div');
        banner.style.cssText = `
            position: fixed; bottom: 1rem; left: 50%; transform: translateX(-50%);
            background: #1e3a5f; color: #fff; border-radius: 14px;
            padding: 0.85rem 1.5rem; z-index: 9998; box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            display: flex; align-items: center; gap: 1rem; font-size: 0.88rem;
            max-width: 90vw;
        `;
        banner.innerHTML = `
            <span>🔄 Mise à jour disponible</span>
            <button onclick="OfflineManager.applyUpdate()" style="
                background:#2196f3;border:none;border-radius:8px;
                color:#fff;padding:0.4rem 1rem;cursor:pointer;font-weight:600;
            ">Actualiser</button>
            <button onclick="this.parentElement.remove()" style="
                background:transparent;border:none;color:rgba(255,255,255,0.5);
                cursor:pointer;font-size:1.2rem;padding:0;
            ">×</button>
        `;
        document.body.appendChild(banner);
    }

    function _showAPKUpdateDialog(version, apkUrl, changelog) {
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed; inset: 0; background: rgba(0,0,0,0.7);
            z-index: 10000; display: flex; align-items: center; justify-content: center;
            backdrop-filter: blur(6px);
        `;
        overlay.innerHTML = `
            <div style="background:#1a1a2e;border:1px solid rgba(255,255,255,0.1);
                        border-radius:20px;padding:2rem;max-width:340px;width:90%;
                        color:#fff;font-family:system-ui,sans-serif;">
                <div style="font-size:2rem;text-align:center;margin-bottom:1rem;">🚀</div>
                <h3 style="margin:0 0 0.5rem;font-size:1.1rem;text-align:center;">
                    Mise à jour disponible
                </h3>
                <p style="color:rgba(255,255,255,0.6);font-size:0.85rem;text-align:center;margin:0 0 1rem;">
                    Version ${version} est disponible
                </p>
                ${changelog ? `
                <div style="background:rgba(255,255,255,0.05);border-radius:10px;
                            padding:0.75rem;margin-bottom:1rem;font-size:0.8rem;
                            color:rgba(255,255,255,0.7);max-height:120px;overflow-y:auto;">
                    ${changelog}
                </div>` : ''}
                <div style="display:flex;gap:0.75rem;">
                    <button onclick="this.closest('[style*=fixed]').remove()"
                            style="flex:1;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);
                                   border-radius:10px;color:#fff;padding:0.65rem;cursor:pointer;font-size:0.85rem;">
                        Plus tard
                    </button>
                    <a href="${apkUrl}" download
                       style="flex:2;background:#2196f3;border:none;border-radius:10px;
                              color:#fff;padding:0.65rem;cursor:pointer;font-size:0.85rem;
                              font-weight:700;text-align:center;text-decoration:none;display:flex;
                              align-items:center;justify-content:center;gap:0.4rem;">
                        ⬇️ Installer v${version}
                    </a>
                </div>
                <p style="font-size:0.72rem;color:rgba(255,255,255,0.3);text-align:center;margin:0.75rem 0 0;">
                    L'application se mettra à jour automatiquement
                </p>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    function _showToast(message, type = 'info') {
        const colors = { success: '#15803d', warning: '#92400e', info: '#1e3a5f', error: '#b91c1c' };
        const toast  = document.createElement('div');
        toast.style.cssText = `
            position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%);
            background: ${colors[type] || colors.info}; color: #fff;
            border-radius: 10px; padding: 0.6rem 1.2rem;
            font-size: 0.82rem; font-weight: 500; z-index: 9997;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
            animation: fadeInUp 0.3s ease; white-space: nowrap;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3500);
    }

    function applyUpdate() {
        if (navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
        }
        window.location.reload();
    }

    // ── IndexedDB helpers ─────────────────────────────────────
    function _openDB() {
        return new Promise((resolve, reject) => {
            const req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onupgradeneeded = e => {
                const d = e.target.result;
                ['arborescences','patrimoines','pending-changes','documents'].forEach(store => {
                    if (!d.objectStoreNames.contains(store))
                        d.createObjectStore(store, { keyPath: 'id', autoIncrement: store === 'pending-changes' });
                });
            };
            req.onsuccess = e => { db = e.target.result; resolve(db); };
            req.onerror   = e => reject(e.target.error);
        });
    }

    function _idbAdd(store, value) {
        return new Promise((resolve, reject) => {
            const tx  = db.transaction(store, 'readwrite');
            const req = tx.objectStore(store).add(value);
            req.onsuccess = e => resolve(e.target.result);
            req.onerror   = e => reject(e.target.error);
        });
    }

    function _idbGetAll(store) {
        return new Promise((resolve, reject) => {
            const tx  = db.transaction(store, 'readonly');
            const req = tx.objectStore(store).getAll();
            req.onsuccess = e => resolve(e.target.result || []);
            req.onerror   = e => reject(e.target.error);
        });
    }

    function _idbDelete(store, key) {
        return new Promise((resolve, reject) => {
            const tx = db.transaction(store, 'readwrite');
            tx.objectStore(store).delete(key);
            tx.oncomplete = resolve;
            tx.onerror    = e => reject(e.target.error);
        });
    }

    // ── API publique ──────────────────────────────────────────
    return { init, queueChange, smartFetch, applyUpdate, isOnline: () => isOnline };

})();

// Auto-init au chargement
document.addEventListener('DOMContentLoaded', () => OfflineManager.init());
