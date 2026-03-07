/**
 * Service Worker for Offline-First PWA
 * 
 * Caches critical UI assets and handles background sync for transactions.
 * Implements store-and-forward mechanism for intermittent connectivity.
 */

const CACHE_NAME = 'olaa-cache-v1';
const TRANSACTION_QUEUE_KEY = 'olaa-offline-queue';

// Critical assets to cache for offline use
const CRITICAL_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/styles/main.css',
  '/app.js',
  '/offline.html'
];

// Install event - cache critical assets
self.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[ServiceWorker] Caching critical assets');
      return cache.addAll(CRITICAL_ASSETS);
    })
  );
  // Force activation even if old service worker exists
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  // Take control immediately
  self.clients.claim();
});

// Fetch event - network-first strategy with offline fallback
self.addEventListener('fetch', (event: FetchEvent) => {
  const { request } = event;
  const url = new URL(request.url);

  // API requests - network first, then fallback to queue
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }

  // Static assets - cache first, then network
  event.respondWith(handleStaticRequest(request));
});

/**
 * Handle API requests with offline queuing
 */
async function handleApiRequest(request: Request): Promise<Response> {
  try {
    // Try network first
    const response = await fetch(request);
    
    // If successful and it's a POST to transactions, clear from queue
    if (request.method === 'POST' && 
        request.url.includes('/api/transactions') && 
        response.ok) {
      // Signal successful sync
      await broadcastMessage({ type: 'SYNC_SUCCESS', url: request.url });
    }
    
    return response;
  } catch (error) {
    console.log('[ServiceWorker] Network failed, queuing request');
    
    // For POST requests, queue them for later sync
    if (request.method === 'POST') {
      const clonedRequest = request.clone();
      await queueOfflineRequest(clonedRequest);
      
      // Return a queued response
      return new Response(
        JSON.stringify({ 
          status: 'queued', 
          message: 'Request queued for when connection is restored',
          timestamp: Date.now()
        }),
        { 
          status: 202,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }
    
    // For GET requests, return cached or error
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    return new Response(
      JSON.stringify({ error: 'Offline - No cached data available' }),
      { 
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * Handle static asset requests (cache-first strategy)
 */
async function handleStaticRequest(request: Request): Promise<Response> {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const response = await fetch(request);
    
    // Cache successful responses
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return await caches.match('/offline.html');
    }
    
    throw error;
  }
}

/**
 * Queue offline request for later sync
 */
async function queueOfflineRequest(request: Request): Promise<void> {
  const queue = await getOfflineQueue();
  
  const requestData = {
    url: request.url,
    method: request.method,
    headers: Object.fromEntries(request.headers.entries()),
    body: await request.text(),
    timestamp: Date.now(),
    id: generateIdempotencyId()
  };
  
  queue.push(requestData);
  await saveOfflineQueue(queue);
  
  // Notify client about queued request
  await broadcastMessage({ 
    type: 'REQUEST_QUEUED', 
    id: requestData.id,
    timestamp: requestData.timestamp
  });
}

/**
 * Get offline queue from IndexedDB
 */
async function getOfflineQueue(): Promise<any[]> {
  return new Promise((resolve) => {
    const request = indexedDB.open('OlaaDB', 1);
    
    request.onupgradeneeded = (event: any) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(TRANSACTION_QUEUE_KEY)) {
        db.createObjectStore(TRANSACTION_QUEUE_KEY, { keyPath: 'id' });
      }
    };
    
    request.onsuccess = (event: any) => {
      const db = event.target.result;
      const transaction = db.transaction([TRANSACTION_QUEUE_KEY], 'readonly');
      const store = transaction.objectStore(TRANSACTION_QUEUE_KEY);
      const getAllRequest = store.getAll();
      
      getAllRequest.onsuccess = () => {
        resolve(getAllRequest.result || []);
      };
      
      getAllRequest.onerror = () => {
        resolve([]);
      };
    };
    
    request.onerror = () => {
      resolve([]);
    };
  });
}

/**
 * Save offline queue to IndexedDB
 */
async function saveOfflineQueue(queue: any[]): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('OlaaDB', 1);
    
    request.onupgradeneeded = (event: any) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(TRANSACTION_QUEUE_KEY)) {
        db.createObjectStore(TRANSACTION_QUEUE_KEY, { keyPath: 'id' });
      }
    };
    
    request.onsuccess = (event: any) => {
      const db = event.target.result;
      const transaction = db.transaction([TRANSACTION_QUEUE_KEY], 'readwrite');
      const store = transaction.objectStore(TRANSACTION_QUEUE_KEY);
      
      // Clear existing queue
      store.clear();
      
      // Add all items
      queue.forEach(item => {
        store.put(item);
      });
      
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    };
    
    request.onerror = () => reject(request.error);
  });
}

/**
 * Generate idempotency ID
 */
function generateIdempotencyId(): string {
  const timestamp = Date.now().toString();
  const random = Math.random().toString(36).substring(2);
  return `sw_${timestamp}_${random}`;
}

/**
 * Broadcast message to all clients
 */
async function broadcastMessage(message: any): Promise<void> {
  const clients = await self.clients.matchAll();
  clients.forEach(client => {
    client.postMessage(message);
  });
}

/**
 * Background sync for queued transactions
 */
async function performBackgroundSync(): Promise<void> {
  const queue = await getOfflineQueue();
  
  if (queue.length === 0) {
    return;
  }
  
  console.log(`[ServiceWorker] Syncing ${queue.length} queued requests`);
  
  const successfulIds: string[] = [];
  
  for (const item of queue) {
    try {
      const response = await fetch(item.url, {
        method: item.method,
        headers: new Headers(item.headers),
        body: item.body
      });
      
      if (response.ok) {
        successfulIds.push(item.id);
        await broadcastMessage({ 
          type: 'SYNC_SUCCESS', 
          id: item.id 
        });
      }
    } catch (error) {
      console.log(`[ServiceWorker] Failed to sync ${item.id}:`, error);
    }
  }
  
  // Remove successfully synced items
  if (successfulIds.length > 0) {
    const updatedQueue = queue.filter(item => !successfulIds.includes(item.id));
    await saveOfflineQueue(updatedQueue);
  }
}

// Listen for sync events
self.addEventListener('sync', (event: SyncEvent) => {
  if (event.tag === 'sync-transactions') {
    event.waitUntil(performBackgroundSync());
  }
});

// Periodic background sync (if supported)
self.addEventListener('periodicsync', (event: PeriodicSyncEvent) => {
  if (event.tag === 'periodic-transaction-sync') {
    event.waitUntil(performBackgroundSync());
  }
});

// Message handler for manual sync triggers
self.addEventListener('message', (event: ExtendableMessageEvent) => {
  if (event.data && event.data.type === 'TRIGGER_SYNC') {
    event.waitUntil(performBackgroundSync());
  }
});

console.log('[ServiceWorker] Olaa Service Worker loaded');
