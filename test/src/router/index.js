import { createRouter, createWebHistory } from 'vue-router';
import ProjectList from '../components/ProjectList.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'ProjectList',
      component: ProjectList
    }
  ]
});

export default router;