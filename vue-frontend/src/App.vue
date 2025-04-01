<template>
  <div id="app">
    <nav class="navigation" v-if="$route.path !== '/projects'">
      <router-link to="/" class="nav-link">Home</router-link>
      <router-link to="/projects" class="nav-link">Projects</router-link>
    </nav>
    
    <!-- Nur router-view verwenden -->
    <router-view></router-view>
  </div>
</template>

<script>
export default {
  name: 'App',
  mounted() {
    window.debugLog('App Component wurde gemounted');
    
    // Router-Navigation überwachen
    this.$router.beforeEach((to, from, next) => {
      window.debugLog(`Navigation startet: von ${from.path} nach ${to.path}`);
      next();
    });

    // Komponenten-Rendering überwachen
    this.$router.afterEach((to) => {
      window.debugLog(`Route geladen: ${to.path}`);
      // Prüfen welche Komponente geladen wurde
      to.matched.forEach(record => {
        window.debugLog(`Geladene Komponente: ${record.components.default.name} für Pfad ${to.path}`);
      });
    });
  },
  errorCaptured(err, vm, info) {
    window.debugLog(`Fehler in ${vm.$options.name}: ${err.message}`);
    console.error('Fehler in Komponente gefangen:', {
      error: err,
      komponente: vm.$options.name,
      info: info
    });
    return false;
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

.navigation {
  padding: 20px;
  margin-bottom: 20px;
}

.nav-link {
  margin: 0 10px;
  color: #2c3e50;
  text-decoration: none;
  padding: 5px 15px;
  border-radius: 4px;
}

.nav-link:hover {
  background-color: #eee;
}

.router-link-active {
  color: #42b983;
  font-weight: bold;
}
</style>
