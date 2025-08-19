// PWA Verification Script
// This script can be run in the browser console to test PWA functionality

console.log('🔍 PWA Verification Starting...');

// Test 1: Check if service worker is registered
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.ready.then(registration => {
    console.log('✅ Service Worker registered:', registration);
    console.log('   - Scope:', registration.scope);
    console.log('   - Active:', !!registration.active);
  }).catch(err => {
    console.error('❌ Service Worker registration failed:', err);
  });
} else {
  console.error('❌ Service Worker not supported');
}

// Test 2: Check if app is running as PWA
const isPWA = window.matchMedia('(display-mode: standalone)').matches || 
              window.navigator.standalone || 
              document.referrer.includes('android-app://');
console.log('📱 Running as PWA:', isPWA);

// Test 3: Check if offline queue is available
setTimeout(() => {
  if (window.offlineQueue) {
    console.log('✅ Offline Queue available');
    console.log('   - Methods:', Object.getOwnPropertyNames(window.offlineQueue));
  } else {
    console.log('⚠️ Offline Queue not found (may still be loading)');
  }
}, 1000);

// Test 4: Check PWA install prompt availability
window.addEventListener('beforeinstallprompt', (e) => {
  console.log('✅ PWA Install prompt available');
  e.preventDefault();
  window.deferredPrompt = e;
});

// Test 5: Check cache API
if ('caches' in window) {
  caches.keys().then(cacheNames => {
    console.log('✅ Cache API available');
    console.log('   - Cache names:', cacheNames);
    
    // Get cache sizes
    Promise.all(cacheNames.map(async (cacheName) => {
      const cache = await caches.open(cacheName);
      const keys = await cache.keys();
      return { name: cacheName, entries: keys.length };
    })).then(cacheSizes => {
      console.log('   - Cache sizes:', cacheSizes);
    });
  });
} else {
  console.error('❌ Cache API not supported');
}

// Test 6: Check IndexedDB (Dexie)
if ('indexedDB' in window) {
  console.log('✅ IndexedDB available');
  // Try to open our offline database
  const request = indexedDB.open('OfflineQueue', 1);
  request.onsuccess = (event) => {
    const db = event.target.result;
    console.log('✅ OfflineQueue database accessible');
    console.log('   - Version:', db.version);
    console.log('   - Object stores:', Array.from(db.objectStoreNames));
    db.close();
  };
  request.onerror = () => {
    console.log('⚠️ OfflineQueue database not yet created');
  };
} else {
  console.error('❌ IndexedDB not supported');
}

// Test 7: Test network status detection
console.log('🌐 Network status:', navigator.onLine ? 'Online' : 'Offline');
window.addEventListener('online', () => console.log('🟢 Network: Online'));
window.addEventListener('offline', () => console.log('🔴 Network: Offline'));

console.log('🔍 PWA Verification Complete - Check results above');
