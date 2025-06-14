<template>
  <div>
    <h1>Projects</h1>
    <ul>
      <li v-for="project in projects" :key="project.id">
        {{ project.title }} - {{ project.description }}
      </li>
    </ul>
  </div>
</template>

<script>
import ReconnectingWebSocket from 'reconnecting-websocket';

export default {
  data() {
    return {
      projects: [],
      scoreLimit: 70  // Set the score limit here
    };
  },
  created() {
    this.connect();
  },
  methods: {
    connect() {
      const rws = new ReconnectingWebSocket('ws://localhost:6789');
      rws.addEventListener('message', (event) => {
        console.log(event);
        const allProjects = JSON.parse(event.data);
        this.projects = allProjects.filter(project => project.score > this.scoreLimit);
      });
    }
  }
};
</script> 