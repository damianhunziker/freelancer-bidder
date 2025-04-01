import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// Globales Fehler-Handling hinzufügen
app.config.errorHandler = (err, vm, info) => {
  console.error('Vue Error:', err);
  console.error('Component:', vm);
  console.error('Error Info:', info);
};

// Debug-Modus und DevTools explizit aktivieren
app.config.performance = true
app.config.devtools = true

// Verbindung zu Standalone DevTools
if (process.env.NODE_ENV === 'development') {
  window.__VUE_DEVTOOLS_HOST__ = 'localhost'
  window.__VUE_DEVTOOLS_PORT__ = '8098'
}

// Debug-Logging
console.log('Verfügbare Routen:', router.getRoutes().map(r => r.path))

// Router hinzufügen
app.use(router)

// Debug-Ausgabe vor dem Mounten
console.log('Versuche App zu mounten...');

// App mounten
app.mount('#app')

console.log('App wurde gemounted');
