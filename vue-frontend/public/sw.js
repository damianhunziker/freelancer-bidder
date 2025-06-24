// Service Worker for Push Notifications
const CACHE_NAME = 'freelancer-bidder-v1';

// Install event
self.addEventListener('install', (event) => {
  console.log('[ServiceWorker] Install');
  self.skipWaiting();
});

// Activate event
self.addEventListener('activate', (event) => {
  console.log('[ServiceWorker] Activate');
  event.waitUntil(self.clients.claim());
});

// Push event - handles incoming push notifications
self.addEventListener('push', (event) => {
  console.log('[ServiceWorker] Push received', event);
  
  let notificationData = {
    title: '🤖 Freelancer Bidder',
    body: 'New auto-bidding activity',
    icon: '/favicon.ico',
    badge: '/favicon.ico',
    tag: 'auto-bid-notification',
    requireInteraction: false,
    vibrate: [200, 100, 200],
    data: {
      url: '/',
      timestamp: Date.now()
    }
  };

  // Parse push data if available
  if (event.data) {
    try {
      const pushData = event.data.json();
      notificationData = {
        ...notificationData,
        ...pushData
      };
    } catch (error) {
      console.warn('[ServiceWorker] Failed to parse push data:', error);
      notificationData.body = event.data.text() || notificationData.body;
    }
  }

  // Show notification
  event.waitUntil(
    self.registration.showNotification(notificationData.title, notificationData)
  );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
  console.log('[ServiceWorker] Notification clicked', event);
  
  event.notification.close();
  
  // Focus or open the app
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      // Try to focus existing window
      for (const client of clients) {
        if (client.url.includes(self.location.origin)) {
          return client.focus();
        }
      }
      // Open new window if no existing window found
      return self.clients.openWindow('/');
    })
  );
});

// Background sync (optional - for offline functionality)
self.addEventListener('sync', (event) => {
  console.log('[ServiceWorker] Background sync', event);
  
  if (event.tag === 'auto-bid-sync') {
    event.waitUntil(
      // Handle background sync for auto-bidding
      handleBackgroundSync()
    );
  }
});

async function handleBackgroundSync() {
  try {
    // This could be used to sync auto-bidding data when coming back online
    console.log('[ServiceWorker] Handling background sync');
  } catch (error) {
    console.error('[ServiceWorker] Background sync failed:', error);
  }
} 