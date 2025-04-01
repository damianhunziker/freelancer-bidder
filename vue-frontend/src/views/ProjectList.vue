<template>
  <div class="project-list-view">
    <ProjectList />
  </div>
</template>

<script>
import ProjectList from '../components/ProjectList.vue'

export default {
  name: 'ProjectListView',
  components: {
    ProjectList
  }
}
</script>