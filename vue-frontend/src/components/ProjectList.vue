<template>
  <div class="project-list" :class="{ 'dark-theme': isDarkTheme }">
    <div class="logo-container" :class="{ 'dark-theme': isDarkTheme }">
      <img src="https://vyftec.com/wp-content/uploads/2024/10/Element-5-3.svg" alt="Vyftec Logo" class="logo">
      <button class="theme-toggle" @click="toggleTheme">
        <i :class="isDarkTheme ? 'fas fa-sun' : 'fas fa-moon'"></i>
      </button>
    </div>

    <!-- Projects list -->
    <div v-if="!loading && projects.length > 0" class="projects">
      <div v-for="project in sortedProjects" 
           :key="project.project_url" 
           class="project-card"
           :class="{ 
             'new-project': project.isNew,
             'removed-project': project.isRemoved,
             'expanded': project.showDescription,
             'fade-in': project.isNew
           }"
           @click="toggleDescription(project)">
        <div class="project-header">
          <div class="project-metrics">
            <span class="metric" title="Country">
              <img 
                :src="`https://flagcdn.com/24x18/${getCountryCode(project.project_details.country)}.png`"
                :srcset="`https://flagcdn.com/48x36/${getCountryCode(project.project_details.country)}.png 2x`"
                width="24"
                height="18"
                :alt="project.project_details.country"
                class="country-flag"
              >
              {{ project.project_details.country }}
            </span>
            <span class="metric" title="Completed Projects">
              <i class="fas fa-check-circle"></i> {{ project.project_details.employer_complete_projects }}
            </span>
            <span class="metric" title="Employer Rating">
              <i class="fas fa-star"></i> {{ project.project_details.employer_overall_rating?.toFixed(1) }}
            </span>
            <span class="metric" title="Score">
              <i class="fas fa-chart-bar"></i> {{ project.bid_score }}
            </span>
            <span v-if="project.project_details.earnings" class="metric" title="Earnings">
              <i class="fas fa-dollar-sign"></i> {{ formatSpending(project.project_details.earnings) }}
            </span>
          </div>
          <h3 class="project-title">{{ project.project_details.title }}</h3>
        </div>
        
        <div class="project-info">
          <div class="description-container">
            <p class="description" v-html="project.showDescription 
              ? nl2br(project.project_details.description) 
              : nl2br(project.project_details.description?.substring(0, 150) + '...')">
            </p>
            <div v-if="project.showDescription" class="explanation-section">
              <h4>KI-Bewertung:</h4>
              <p class="explanation">{{ project.bid_text }}</p>
            </div>
          </div>
        </div>
        
        <div class="project-footer">
          <span class="timestamp">{{ formatDate(project.timestamp) }}</span>
          <div class="project-actions" @click.stop>
            <button class="action-button view" @click="handleProjectClick(project)">
              <i class="fas fa-external-link-alt"></i>
            </button>
            <button class="action-button question" @click="handleQuestionClick(project)">
              <i class="fas fa-question-circle"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- No projects state -->
    <div v-if="!loading && projects.length === 0" class="no-projects">
      No projects found
    </div>
  </div>
</template>

<script>
import { defineComponent } from 'vue';

console.log('das ist die projektliste per javascript auf der projekt liste seite');

export default defineComponent({
  name: 'ProjectList',
  data() {
    console.log('[ProjectList] data() aufgerufen');
    return {
      projects: [],
      loading: true,
      error: null,
      pollingInterval: null,
      lastUpdate: null,
      showDebug: false,
      showDebugContent: false,
      cacheStats: null,
      bidTextCache: new Map(),
      chatGPTResponses: [],
      lastSeenTimestamp: null,
      currentTimeWindow: 3600,
      masonry: null,
      removedProjects: new Set(),
      lastKnownProjects: new Set(),
      isDarkTheme: false,
      systemThemeQuery: null
    }
  },
  beforeCreate() {
    console.log('[ProjectList] beforeCreate aufgerufen');
  },
  created() {
    console.log('[ProjectList] created aufgerufen');
    // Prüfen ob die Komponente korrekt initialisiert wurde
    console.log('[ProjectList] this.$options:', this.$options);
    console.log('[ProjectList] this.$router:', this.$router);
  },
  beforeMount() {
    console.log('[ProjectList] beforeMount aufgerufen');
  },
  mounted() {
    console.log('[ProjectList] mounted aufgerufen');
    console.log('[ProjectList] DOM Element:', this.$el);
    console.log('[ProjectList] Starting loadProjects...');
    this.loadProjects();
    console.log('[ProjectList] Starting polling...');
    this.startPolling();

    // Add animation delay to project cards
    this.$nextTick(() => {
      const cards = this.$el.querySelectorAll('.project-card');
      cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.05}s`;
      });
    });

    // Check for saved theme preference first
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      this.isDarkTheme = savedTheme === 'dark';
      document.body.classList.toggle('dark-theme', this.isDarkTheme);
    } else {
      // If no saved preference, check system preference
      this.systemThemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
      this.isDarkTheme = this.systemThemeQuery.matches;
      document.body.classList.toggle('dark-theme', this.isDarkTheme);
      this.systemThemeQuery.addEventListener('change', this.handleSystemThemeChange);
    }
  },
  beforeUnmount() {
    console.log('[ProjectList] beforeUnmount aufgerufen');
    // Clean up event listener
    if (this.systemThemeQuery) {
      this.systemThemeQuery.removeEventListener('change', this.handleSystemThemeChange);
    }
    this.stopPolling();
  },
  unmounted() {
    console.log('[ProjectList] unmounted aufgerufen');
  },
  errorCaptured(err, vm, info) {
    console.error('[ProjectList] Fehler:', {
      error: err,
      komponente: vm.$options.name,
      info: info
    });
    return false;
  },
  computed: {
    sortedProjects() {
      return [...this.projects].sort((a, b) => {
        // Convert timestamps to Date objects for comparison
        const dateA = new Date(a.timestamp);
        const dateB = new Date(b.timestamp);
        // Sort in descending order (newest first)
        return dateB - dateA;
      });
    }
  },
  methods: {
    toggleTheme() {
      this.isDarkTheme = !this.isDarkTheme;
      localStorage.setItem('theme', this.isDarkTheme ? 'dark' : 'light');
      document.body.classList.toggle('dark-theme', this.isDarkTheme);
    },
    handleSystemThemeChange(e) {
      // Only update if user hasn't manually set a preference
      if (!localStorage.getItem('theme')) {
        this.isDarkTheme = e.matches;
        document.body.classList.toggle('dark-theme', this.isDarkTheme);
      }
    },
    initMasonry() {
      // Remove old masonry initialization
    },
    startPolling() {
      // Poll every 10 seconds
      this.pollingInterval = setInterval(async () => {
        try {
          await this.checkForNewProjects();
        } catch (error) {
          console.error('[ProjectList] Error during polling:', error);
          // Don't stop polling on error, just log it
        }
      }, 10000);
    },
    stopPolling() {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval);
        this.pollingInterval = null;
      }
    },
    async checkForNewProjects() {
      console.log('[ProjectList] checkForNewProjects aufgerufen');

      try {
        const response = await fetch('/api/jobs', {
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('[ProjectList] Received data:', data);
        
        // Create a Set of current project URLs
        const currentProjectUrls = new Set(data.map(job => job.project_url));
        console.log('[ProjectList] Current project URLs:', currentProjectUrls);
        
        // Find new projects by comparing with lastKnownProjects
        const newProjects = data.filter(job => !this.lastKnownProjects.has(job.project_url));
        console.log('[ProjectList] New projects:', newProjects);
        
        // Update lastKnownProjects with current project URLs
        this.lastKnownProjects = currentProjectUrls;
        
        // Add new projects to the beginning of the list with fade-in effect
        for (const job of newProjects) {
          const project = {
            ...job,
            isNew: true
          };
          this.projects.unshift(project);
          console.log('[ProjectList] Added project:', project);
          
          // Remove the fade-in effect after animation
          setTimeout(() => {
            project.isNew = false;
          }, 1000);
        }
        
        // Update masonry layout after adding new projects
        if (newProjects.length > 0) {
          this.$nextTick(() => {
            if (this.masonry) {
              this.masonry.reloadItems();
            }
          });
        }

      } catch (error) {
        console.error('[ProjectList] Error checking for new projects:', error);
      }
    },
    async loadProjects() {
      try {
        console.log('[ProjectList] Starting loadProjects...');
        this.loading = true;
        this.error = null;
        console.log('[ProjectList] Fetching from /api/jobs...');
        const response = await fetch('/api/jobs', {
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
          }
        });
        console.log('[ProjectList] Response status:', response.status);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('[ProjectList] Received data:', data);
        
        // Create a Set of current project URLs
        const currentProjectUrls = new Set(data.map(job => job.project_url));
        console.log('[ProjectList] Current project URLs:', currentProjectUrls);
        
        // Find new projects by comparing with lastKnownProjects
        const newProjects = data.filter(job => !this.lastKnownProjects.has(job.project_url));
        console.log('[ProjectList] New projects:', newProjects);
        
        // Update lastKnownProjects with current project URLs
        this.lastKnownProjects = currentProjectUrls;
        
        // Add new projects to the beginning of the list with fade-in effect
        for (const job of newProjects) {
          const project = {
            ...job,
            isNew: true
          };
          this.projects.unshift(project);
          console.log('[ProjectList] Added project:', project);
          
          // Remove the fade-in effect after animation
          setTimeout(() => {
            project.isNew = false;
          }, 1000);
        }
        
        // Update masonry layout after adding new projects
        this.$nextTick(() => {
          if (this.$refs.masonry) {
            this.$refs.masonry.reloadItems();
          }
        });
      } catch (error) {
        console.error('[ProjectList] Error loading projects:', error);
        this.error = 'Failed to load projects. Please try again.';
      } finally {
        console.log('[ProjectList] Setting loading to false');
        this.loading = false;
      }
    },
    formatDate(timestamp) {
      return new Date(timestamp).toLocaleString();
    },
    
    async handleProjectClick(project) {
      try {
        console.log('project', project);

        // First open the project URL in a new tab
        window.open(project.project_url, '_blank');

        // Check cache first
        if (this.bidTextCache.has(project.project_url)) {
          console.log('Using cached bid text for project:', project.project_url);
          const cachedText = this.bidTextCache.get(project.project_url);
          await navigator.clipboard.writeText(cachedText);
          console.log('Successfully copied cached text to clipboard');
          return;
        }

        // Check if bid_text exists and is a string
        if (!project.bid_text || typeof project.bid_text !== 'string') {
          console.error('No bid text available');
          return;
        }

        // Parse the JSON bid_text
        let bidData;
        try {
          bidData = JSON.parse(project.bid_text);
        } catch (e) {
          console.error('Failed to parse bid_text JSON:', e);
          return;
        }

        // Extract first and third paragraphs from bid_teaser
        const paragraphs = [];
        if (bidData.bid_teaser?.first_paragraph) {
          paragraphs.push(bidData.bid_teaser.first_paragraph);
        }
        if (bidData.bid_teaser?.third_paragraph) {
          paragraphs.push(bidData.bid_teaser.third_paragraph);
        }

        if (paragraphs.length === 0) {
          console.error('No valid paragraphs found in bid text');
          return;
        }

        // Format the paragraphs
        const formattedParagraphs = paragraphs.map((para, index) => {
          if (index === 1) { // Third paragraph
            return para.replace(/Bye for now!/, '\n\nBye for now!')
                      .replace(/ - Damian/, '\n - Damian');
          }
          return para;
        });

        // Join the paragraphs with double newlines
        const formattedBidText = formattedParagraphs.join('\n\n');

        // Store in cache
        this.bidTextCache.set(project.project_url, formattedBidText);
        console.log('Stored bid text in cache for project:', project.project_url);

        // Copy the paragraphs
        await navigator.clipboard.writeText(formattedBidText);
        console.log('Successfully copied paragraphs to clipboard');

        // Optional: Clear old cache entries after a certain time (e.g., 1 hour)
        setTimeout(() => {
          this.bidTextCache.delete(project.project_url);
          console.log('Cleared cache for project:', project.project_url);
        }, 3600000); // 1 hour in milliseconds

      } catch (error) {
        console.error('Error copying bid text:', error);
      }
    },
    async handleQuestionClick(project) {
      try {
        // Check if bid_text exists and is a string
        if (!project.bid_text || typeof project.bid_text !== 'string') {
          console.error('No bid text available');
          return;
        }

        // Parse the JSON bid_text
        let bidData;
        try {
          bidData = JSON.parse(project.bid_text);
        } catch (e) {
          console.error('Failed to parse bid_text JSON:', e);
          return;
        }

        // Copy the question if it exists
        if (bidData.bid_teaser?.question) {
          await navigator.clipboard.writeText(bidData.bid_teaser.question);
          console.log('Successfully copied question to clipboard');
        } else {
          console.error('No question found in bid text');
        }
      } catch (error) {
        console.error('Error copying question:', error);
      }
    },
    toggleDescription(project) {
      project.showDescription = !project.showDescription;
      this.$nextTick(() => {
        const card = this.$el.querySelector(`[data-project-url="${project.project_url}"]`);
        if (card) {
          if (project.showDescription) {
            card.classList.add('expanded', 'zooming');
            setTimeout(() => {
              card.classList.remove('zooming');
              card.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest',
                inline: 'nearest'
              });
            }, 500);
          } else {
            card.classList.remove('expanded', 'zooming');
          }
        }
      });
    },
    getCountryCode(country) {
      if (!country) return 'us';
      const countryMap = {
        'Australia': 'au',
        'United States': 'us',
        'United Kingdom': 'gb',
        'Canada': 'ca',
        'Germany': 'de',
        'France': 'fr',
        'Italy': 'it',
        'Spain': 'es',
        'Japan': 'jp',
        'China': 'cn',
        'India': 'in',
        'Brazil': 'br',
        'Russia': 'ru',
        'South Korea': 'kr',
        'New Zealand': 'nz',
        'Singapore': 'sg',
        'Israel': 'il',
        'Sweden': 'se',
        'Norway': 'no',
        'Denmark': 'dk',
        'Finland': 'fi',
        'Netherlands': 'nl',
        'Belgium': 'be',
        'Austria': 'at',
        'Switzerland': 'ch',
        'Ireland': 'ie',
        'Portugal': 'pt',
        'Greece': 'gr',
        'Poland': 'pl',
        'Czech Republic': 'cz',
        'Hungary': 'hu',
        'Romania': 'ro',
        'Bulgaria': 'bg',
        'Croatia': 'hr',
        'Slovakia': 'sk',
        'Slovenia': 'si',
        'Estonia': 'ee',
        'Latvia': 'lv',
        'Lithuania': 'lt',
        'Cyprus': 'cy',
        'Luxembourg': 'lu',
        'Malta': 'mt',
        'Iceland': 'is',
        'Liechtenstein': 'li',
        'Monaco': 'mc',
        'San Marino': 'sm',
        'Vatican City': 'va',
        'Andorra': 'ad'
      };
      return countryMap[country] || 'us';
    },
    formatSpending(score) {
      if (!score) return 'N/A';
      if (score < 1000) return `$${score.toFixed(0)}`;
      if (score < 10000) return `$${(score/1000).toFixed(1)}k`;
      if (score < 100000) return `$${(score/1000).toFixed(0)}k`;
      return `$${(score/1000).toFixed(1)}k`;
    },
    toggleDebug() {
      this.showDebug = !this.showDebug;
      if (this.showDebug) {
        this.fetchCacheStats();
      }
    },
    toggleDebugContent() {
      console.log('Debug: toggleDebugContent called');
      console.log('Debug: Current showDebugContent value:', this.showDebugContent);
      this.showDebugContent = !this.showDebugContent;
      console.log('Debug: New showDebugContent value:', this.showDebugContent);
      
      if (this.showDebugContent) {
        console.log('Debug: Fetching cache stats...');
        this.fetchCacheStats();
      }
    },
    async fetchCacheStats() {
      console.log('Debug: fetchCacheStats called');
      try {
        const response = await window.fetch('/cache/stats', {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        });
        console.log('Debug: Cache stats response:', response);
        if (response.ok) {
          this.cacheStats = await response.json();
          console.log('Debug: Cache stats updated:', this.cacheStats);
        }
      } catch (error) {
        console.error('Error fetching cache stats:', error);
      }
    },
    closeDebug() {
      this.showDebug = false;
    },
    nl2br(str) {
      if (!str) return '';
      return str.replace(/\n/g, '<br>');
    }
  }
});
</script>

<style scoped>
.project-list {
  width: 100%;
  margin: 0;
  min-height: 100vh;
  background-color: #fff8f0;
  transition: background-color 0.3s ease, color 0.3s ease;
}

.project-list.dark-theme {
  background-color: #1a2b3c;
  color: #ffffff;
}

/* Add global styles for body */
:global(body) {
  margin: 0;
  padding: 0;
  background-color: #fff8f0;
  transition: background-color 0.3s ease, color 0.3s ease;
}

:global(body.dark-theme) {
  background-color: #1a2b3c;
  color: #ffffff;
}

.logo-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: background-color 0.3s ease;
}

.logo-container.dark-theme {
  background: rgba(26, 43, 60, 0.8);
}

.theme-toggle {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.theme-toggle:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.dark-theme .theme-toggle {
  color: #fff;
}

.dark-theme .theme-toggle:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.logo {
  height: 40px;
  width: auto;
}

.project-card {
  background: #fff8f0;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 10px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: all 0.3s ease;
  opacity: 1;
  transform: translateY(0);
  height: fit-content;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  break-inside: avoid;
  cursor: pointer;
}

.dark-theme .project-card {
  background: #2a3b4c;
  border-color: #3a4b5c;
  color: #fff;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.dark-theme .project-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.project-header {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 5px;
}

.project-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.metric {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 0.85em;
  color: #666;
  white-space: nowrap;
}

.dark-theme .metric {
  color: #aaa;
}

.country-flag {
  border-radius: 2px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.project-title {
  font-size: 1.2em;
  font-weight: 600;
  margin-bottom: 3px;
  color: #2c3e50;
}

.dark-theme .project-title {
  color: #fff;
}

.project-info {
  margin: 3px 0;
}

.description {
  font-size: 0.8em;
  color: #666;
  margin: 3px 0;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: all 0.3s ease;
  text-align: left;
}

.dark-theme .description {
  color: #aaa;
}

.project-card.expanded .description {
  font-size: 0.9em;
  -webkit-line-clamp: unset;
  display: block;
  text-align: left;
}

.project-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 3px;
  padding-top: 3px;
  border-top: 1px solid #eee;
}

.dark-theme .project-footer {
  border-top-color: #3a4b5c;
}

.timestamp {
  font-size: 0.8em;
  color: #666;
}

.dark-theme .timestamp {
  color: #aaa;
}

.project-actions {
  display: flex;
  gap: 6px;
  z-index: 3;
}

.action-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  color: white;
  font-size: 1.1rem;
}

.action-button.view {
  background-color: #4CAF50;
}

.action-button.question {
  background-color: #2196F3;
}

.action-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.action-button i {
  font-size: 1.1rem;
}

.explanation-section {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #eee;
}

.dark-theme .explanation-section {
  border-top-color: #3a4b5c;
}

.explanation-section h4 {
  color: #333;
  margin-bottom: 5px;
  font-size: 1em;
}

.dark-theme .explanation-section h4 {
  color: #fff;
}

.explanation {
  font-size: 0.85em;
  line-height: 1.3;
  color: #666;
  white-space: pre-line;
  text-align: left;
  background-color: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  margin: 0;
}

.dark-theme .explanation {
  background-color: #3a4b5c;
  color: #aaa;
}

.loading {
  text-align: center;
  padding: 20px;
  color: #666;
}

.error {
  color: #ff4444;
  padding: 20px;
  text-align: center;
  background-color: #ffebee;
  border-radius: 4px;
  margin: 10px 0;
}

.no-projects {
  text-align: center;
  padding: 20px;
  color: #666;
  font-style: italic;
}

.notification {
  position: fixed;
  top: 20px;
  right: 20px;
  background-color: #4CAF50;
  color: white;
  padding: 15px 25px;
  border-radius: 4px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2);
  z-index: 1000;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.projects {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 20px;
  padding: 20px;
  width: 100%;
  max-width: 2000px;
  margin: 0 auto;
}

.project-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s ease;
  position: relative;
  z-index: 1;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.project-card.expanded {
  z-index: 2;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}

.project-card.expanded .project-content {
  max-height: none;
}

.project-content {
  max-height: 200px;
  overflow: hidden;
  transition: max-height 0.3s ease;
}

.project-description {
  padding: 15px;
  background: #f8f9fa;
  border-top: 1px solid #eee;
  transition: all 0.3s ease;
}

.project-card.expanded .project-description {
  max-height: none;
  opacity: 1;
}

.new-project {
  animation: highlightNew 2s ease-out;
}

.removed-project {
  animation: fadeOut 1s ease-out forwards;
}

@keyframes highlightNew {
  0% {
    background-color: #e8f5e9;
    transform: translateY(-10px);
  }
  100% {
    background-color: #fff;
    transform: translateY(0);
  }
}

@keyframes fadeOut {
  0% {
    background-color: #ffebee;
    opacity: 1;
    transform: translateY(0);
  }
  100% {
    background-color: #ffebee;
    opacity: 0;
    transform: translateY(20px);
  }
}

.description-container {
  margin-top: 10px;
}

.toggle-description {
  background: none;
  border: none;
  color: #4CAF50;
  cursor: pointer;
  padding: 5px 0;
  font-size: 0.9em;
  text-decoration: underline;
  margin-top: 5px;
  display: block;
}

.toggle-description:hover {
  color: #45a049;
}

.header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.control-buttons {
  display: flex;
  gap: 10px;
}

.debug-toggle {
  background-color: #666;
  color: white;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.debug-toggle.active {
  background-color: #ff4444;
}

.debug-toggle:hover {
  opacity: 0.9;
}

.debug-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.8);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  overflow-y: auto;
}

.debug-content {
  background-color: #fff;
  border-radius: 8px;
  padding: 20px;
  max-width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.debug-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 10px;
}

.close-button {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  padding: 5px;
  font-size: 1.2em;
  transition: color 0.3s;
}

.close-button:hover {
  color: #ff4444;
}

.debug-content h3 {
  margin: 0;
  color: #333;
}

.debug-section {
  margin-bottom: 20px;
  background: white;
  border-radius: 4px;
  padding: 15px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.debug-section h4 {
  color: #333;
  margin-bottom: 10px;
  padding-bottom: 5px;
  border-bottom: 1px solid #eee;
}

.debug-section pre {
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
}

#debug {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0,0,0,0.8);
  color: white;
  font-family: monospace;
  max-height: 200px;
  overflow-y: auto;
  transition: all 0.3s ease;
  transform: translateY(calc(100% - 30px));
  z-index: 1000;
}

#debug.debug-open {
  transform: translateY(0);
  max-height: 80vh;
}

#debug-toggle {
  width: 100%;
  background: rgba(0,0,0,0.8);
  color: white;
  border: none;
  padding: 5px 10px;
  cursor: pointer;
  font-family: monospace;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 8px;
}

#debug-toggle:hover {
  background: rgba(0,0,0,0.9);
}

#debug-content {
  padding: 10px;
  max-height: calc(80vh - 30px);
  overflow-y: auto;
  background: rgba(0,0,0,0.8);
}

.chatgpt-responses {
  max-height: 400px;
  overflow-y: auto;
  background: #f8f9fa;
  border-radius: 4px;
  padding: 10px;
}

.response-item {
  margin-bottom: 15px;
  padding: 10px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.response-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}

.project-title {
  font-weight: bold;
  color: #333;
}

.response-content {
  margin: 0;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 0.9em;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
}

/* Large desktop view (5 boxes per row) */
@media (min-width: 1600px) {
  .projects {
    grid-template-columns: repeat(5, 1fr);
  }
  .project-card.expanded {
    grid-column: span 2;
  }
}

/* Desktop view (4 boxes per row) */
@media (max-width: 1599px) {
  .projects {
    grid-template-columns: repeat(4, 1fr);
  }
  .project-card.expanded {
    grid-column: span 2;
  }
}

/* Tablet view (2 boxes per row) */
@media (max-width: 1200px) {
  .projects {
    grid-template-columns: repeat(2, 1fr);
  }
  .project-card.expanded {
    grid-column: span 2;
  }
}

/* Mobile view (1 box per row) */
@media (max-width: 768px) {
  .projects {
    grid-template-columns: 1fr;
  }
  .project-card.expanded {
    grid-column: span 1;
  }
}

/* Add smooth transitions for all theme-dependent elements */
.project-card,
.logo-container,
.metric,
.project-title,
.description,
.timestamp,
.explanation-section,
.explanation {
  transition: all 0.3s ease;
}
</style>
