<template>
  <div class="home-page">
    <h1>Projektliste</h1>
    <ul>
      <li v-for="project in projects" :key="project.id">{{ project.name }}</li>
    </ul>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'HomeView',
  data() {
    return {
      projects: []
    };
  },
  created() {
    this.fetchProjects();
  },
  methods: {
    fetchProjects() {
      axios.get('http://localhost:5000/api/projects')
        .then(response => {
          this.projects = response.data;
        })
        .catch(error => {
          console.error('There was an error fetching the projects:', error);
        });
    }
  }
}
</script>

<style scoped>
.home-page {
  text-align: center;
  margin-top: 50px;
}
</style>
