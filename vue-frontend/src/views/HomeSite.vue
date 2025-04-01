<template>
  <div class="home-page">
    <h1>Projektliste</h1>
    <ul>
      <li v-for="project in projects" :key="project.id">{{ project.name }}</li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'HomeView',
  data() {
    return {
      projects: [
        { id: 1, name: 'Projekt 1' },
        { id: 2, name: 'Projekt 2' }
      ]
    };
  }
}
</script>

<style scoped>
.home-page {
  text-align: center;
  margin-top: 50px;
}
</style> 