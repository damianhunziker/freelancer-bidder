import { createRouter, createWebHistory } from 'vue-router';
import Home from '../views/HomeSite.vue'; // Stellen Sie sicher, dass der Pfad korrekt ist
// import HomeSite from '@/views/HomeSite' // Commented out as it's not used currently
import ProjectListView from '../views/ProjectList.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'HomeSite',
      component: Home
    },
    {
      path: '/projects',
      name: 'ProjectList',
      component: ProjectListView,
      beforeEnter: (to, from, next) => {
        console.log('ProjectList Route wird betreten');
        next();
      }
    },
    {
      path: '/jobs',
      name: 'Jobs',
      component: ProjectListView,
      beforeEnter: (to, from, next) => {
        console.log('Jobs Route wird betreten');
        next();
      }
    },
    // Catch-all Route für nicht gefundene Pfade
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: {
        template: '<div>Seite nicht gefunden. Path: {{ $route.path }}</div>',
        mounted() {
          console.log('404 Route wurde gemounted für Pfad:', this.$route.path);
        }
      }
    }
  ]
});

// Navigation Guard für        Routes
router.beforeEach((to, from, next) => {
  // Skip navigation for API routes
  if (to.path.startsWith('/api/')) {
    console.log('API Route detected, skipping navigation:', to.path);
    next(false);
    return;
  }
  console.log('Navigation zu:', to.path);
  next();
});

router.afterEach((to) => {
  console.log('Navigation abgeschlossen zu:', to.path);
});

export default router; 