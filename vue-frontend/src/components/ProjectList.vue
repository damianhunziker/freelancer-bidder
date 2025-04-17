<template>
  <div class="project-list" :class="{ 'dark-theme': isDarkTheme }">
    <div class="logo-container" :class="{ 'dark-theme': isDarkTheme }">
      <img src="https://vyftec.com/wp-content/uploads/2024/10/Element-5-3.svg" alt="Vyftec Logo" class="logo" :class="{ 'inverted': isDarkTheme }">
      <div class="header-controls">
        <button class="theme-toggle" @click="toggleTheme">
          <i :class="isDarkTheme ? 'fas fa-sun' : 'fas fa-moon'"></i>
        </button>
        <button class="sound-toggle" @click="toggleSound">
          <i :class="isSoundEnabled ? 'fas fa-volume-up' : 'fas fa-volume-mute'"></i>
        </button>
        <button class="test-sound" @click="playTestSound">
          <i class="fas fa-music"></i>
        </button>
      </div>
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
             'fade-in': project.isNew,
             'missing-file': missingFiles.has(project.project_details.id)
           }"
           @click="handleCardClick($event, project)">
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
            <span v-if="project.project_details.employer_complete_projects && project.project_details.employer_complete_projects !== 'N/A'" class="metric" title="Completed Projects">
              <i class="fas fa-check-circle completed-icon"></i> {{ project.project_details.employer_complete_projects }}
            </span>
            <span v-if="project.project_details.employer_overall_rating && project.project_details.employer_overall_rating !== 0.0" class="metric" title="Employer Rating">
              <i class="fas fa-star rating-icon"></i> {{ project.project_details.employer_overall_rating?.toFixed(1) }}
            </span>
            <span v-if="project.bid_score" class="metric" title="Score">
              <i class="fas fa-chart-bar score-icon"></i> {{ project.bid_score }}
            </span>
            <span v-if="getProjectEarnings(project) && getProjectEarnings(project) !== 0" class="metric" title="Earnings">
              <i class="fas fa-dollar-sign earnings-icon"></i> {{ formatSpending(getProjectEarnings(project)) }}
            </span>
            <span v-if="project.project_details.bid_stats && project.project_details.bid_stats.bid_count" class="metric" title="Bids">
              <i class="fas fa-gavel bids-icon"></i> {{ project.project_details.bid_stats.bid_count }}
            </span>
            <span v-if="project.project_details.bid_stats && project.project_details.bid_stats.bid_avg" class="metric" title="Avg Bid">
              <i class="fas fa-coins avg-bid-icon"></i> ${{ project.project_details.bid_stats.bid_avg.toFixed(0) }}
            </span>
          </div>
          <h3 class="project-title">{{ project.project_details.title }}</h3>
        </div>
        
        <div class="project-info">
          <div class="description-container">
            <div v-if="project.project_details.jobs && project.project_details.jobs.length > 0" class="skills-container">
              <div class="skills-badges">
                <span v-for="skill in project.project_details.jobs" :key="skill.id" class="skill-badge">
                  {{ skill.name }}
                </span>
              </div>
            </div>
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
          <span class="elapsed-time" title="Time since posting">
            <i class="far fa-clock"></i> {{ getElapsedTime(project.timestamp) }}
          </span>
          <div class="project-actions" @click.stop>
            <button class="action-button expand" 
                    :class="{ 'clicked': project.expandClicked }"
                    @click="handleExpandClick(project)">
              <i class="fas fa-expand-alt"></i>
            </button>
            <button class="action-button view" 
                    :class="{ 'clicked': project.viewClicked }"
                    @click="handleProjectClick(project)">
              <i class="fas fa-external-link-alt"></i>
            </button>
            <button class="action-button question"
                    :class="{ 'clicked': project.questionClicked }"
                    @click="handleQuestionClick(project)">
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
      systemThemeQuery: null,
      isSoundEnabled: true,
      audioContext: null,
      audioInitialized: false,
      timeUpdateInterval: null,
      missingFiles: new Set(),
      fileCheckInterval: null
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

    // Initialize theme immediately
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      this.isDarkTheme = savedTheme === 'dark';
    } else {
      this.systemThemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
      this.isDarkTheme = this.systemThemeQuery.matches;
    }
    this.applyTheme();
    
    // Initialize sound preference
    const soundEnabled = localStorage.getItem('soundEnabled');
    if (soundEnabled !== null) {
      this.isSoundEnabled = soundEnabled === 'true';
    }
    
    // Create audio element properly
    this.createAudioElement();
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
    
    // Start timer to update elapsed times
    this.timeUpdateInterval = setInterval(() => {
      this.forceUpdate();
    }, 1000);

    this.startFileChecking();
  },
  beforeUnmount() {
    console.log('[ProjectList] beforeUnmount aufgerufen');
    // Clean up event listener
    if (this.systemThemeQuery) {
      this.systemThemeQuery.removeEventListener('change', this.handleSystemThemeChange);
    }
    this.stopPolling();
    
    // Clear time update interval
    if (this.timeUpdateInterval) {
      clearInterval(this.timeUpdateInterval);
    }

    this.stopFileChecking();
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
  watch: {
    isDarkTheme: {
      handler() {
        this.applyTheme();
      },
      immediate: true
    }
  },
  methods: {
    applyTheme() {
      document.body.classList.toggle('dark-theme', this.isDarkTheme);
      document.documentElement.classList.toggle('dark-theme', this.isDarkTheme);
    },
    toggleTheme() {
      this.isDarkTheme = !this.isDarkTheme;
      localStorage.setItem('theme', this.isDarkTheme ? 'dark' : 'light');
    },
    handleSystemThemeChange(e) {
      // Only update if user hasn't manually set a preference
      if (!localStorage.getItem('theme')) {
        this.isDarkTheme = e.matches;
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
        
        // Play sound if there are new projects
        if (newProjects.length > 0) {
          // Play the notification sound immediately when new projects are found
          await this.playNotificationSound();
        }
        
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
        
        // Debug earnings data structure
        if (data.length > 0) {
          console.log('[ProjectList] First project details:', data[0].project_details);
          console.log('[ProjectList] Earnings path check:', {
            directEarnings: data[0].project_details.earnings,
            employerEarningsScore: data[0].project_details.employer_earnings_score,
            nestedOwnerEarnings: data[0].project_details.owner?.earnings
          });
        }
        
        // Create a Set of current project URLs
        const currentProjectUrls = new Set(data.map(job => job.project_url));
        console.log('[ProjectList] Current project URLs:', currentProjectUrls);
        
        // Find new projects by comparing with lastKnownProjects
        const newProjects = data.filter(job => !this.lastKnownProjects.has(job.project_url));
        console.log('[ProjectList] New projects:', newProjects);
        
        // Update lastKnownProjects with current project URLs
        this.lastKnownProjects = currentProjectUrls;
        
        // Play sound if there are new projects on initial load
        if (newProjects.length > 0) {
          // Play the notification sound for initial projects
          await this.playNotificationSound();
        }
        
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
    
    getElapsedTime(timestamp) {
      if (!timestamp) return 'N/A';
      
      const now = new Date();
      const created = new Date(timestamp);
      const diffMs = now - created;
      
      // Convert to seconds, minutes, hours, days
      const seconds = Math.floor(diffMs / 1000) % 60;
      const minutes = Math.floor(diffMs / (1000 * 60)) % 60;
      const hours = Math.floor(diffMs / (1000 * 60 * 60)) % 24;
      const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      
      // Format the time parts
      const parts = [];
      if (days > 0) parts.push(`${days}d`);
      if (hours > 0 || days > 0) parts.push(`${hours}h`);
      if (minutes > 0 || hours > 0 || days > 0) parts.push(`${minutes}m`);
      parts.push(`${seconds}s`);
      
      return parts.join(' ');
    },
    
    forceUpdate() {
      // This will trigger a reactivity update for all components
      this.$forceUpdate();
    },
    
    showNotification(message, type = 'success') {
      // You can implement this using a notification library like vue-toastification
      // or create a simple notification system
      const notification = document.createElement('div')
      notification.className = `notification ${type}`
      notification.textContent = message
      document.body.appendChild(notification)
      
      // Remove notification after 3 seconds
      setTimeout(() => {
        notification.remove()
      }, 3000)
    },
    
    async handleProjectClick(project) {
      try {
        // Get bid text from cache or project data
        let bidText = this.bidTextCache.get(project.project_details.id)
        if (!bidText) {
          // Check if ranking and bid_teaser exist
          if (project.ranking?.bid_teaser) {
            const teaser = project.ranking.bid_teaser
            // Format the text to copy with all paragraphs and question
            bidText = `${teaser.first_paragraph}\n\n${teaser.second_paragraph}\n\n${teaser.third_paragraph}\n\n${teaser.question}`
            this.bidTextCache.set(project.project_details.id, bidText)
          } else {
            throw new Error('No valid bid text available')
          }
        }

        // Copy to clipboard
        await navigator.clipboard.writeText(bidText)
        this.showNotification('Text copied to clipboard!', 'success')

        // Open project in new tab
        if (project.links?.project) {
          window.open(project.links.project, '_blank')
        } else {
          throw new Error('No project URL available')
        }
      } catch (error) {
        console.error('Error handling project click:', error)
        this.showNotification('Failed to copy text to clipboard', 'error')
      }
    },
    async handleQuestionClick(project) {
      try {
        // Mark button as clicked
        project.questionClicked = true

        // Check if bid_text exists and is a string
        if (!project.bid_text || typeof project.bid_text !== 'string') {
          console.error('No bid text available')
          return
        }

        // Try to parse the bid text as JSON
        let bidData
        try {
          bidData = JSON.parse(project.bid_text)
        } catch (e) {
          console.error('Failed to parse bid_text JSON:', e)
          return
        }

        // Extract and copy the question if it exists
        const question = bidData.bid_teaser?.question
        if (question) {
          await navigator.clipboard.writeText(question)
          this.showNotification('Question copied to clipboard!', 'success')
        } else {
          console.error('No question found in bid text')
          this.showNotification('No question available', 'error')
        }
      } catch (error) {
        console.error('Error copying question:', error)
        this.showNotification('Failed to copy question', 'error')
      }
    },
    toggleDescription(project) {
      project.showDescription = !project.showDescription;
      
      // Mark the expand button as clicked when expanding
      if (project.showDescription) {
        project.expandClicked = true;
      }
      
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
    handleCardClick(event, project) {
      // Prevent toggling if text is selected
      if (window.getSelection().toString()) {
        return;
      }
      
      // Proceed with toggling description
      this.toggleDescription(project);
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
      console.log('[ProjectList] Formatting spending value:', score);
      if (!score || score === 0) return 'N/A';
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
    },
    toggleSound() {
      this.isSoundEnabled = !this.isSoundEnabled;
      localStorage.setItem('soundEnabled', this.isSoundEnabled);
    },
    createAudioElement() {
      // Only create the context if it doesn't exist yet
      if (!this.audioContext) {
        try {
          // Create audio context - must be done in response to a user gesture
          const AudioContext = window.AudioContext || window.webkitAudioContext;
          this.audioContext = new AudioContext();
          
          console.log('[ProjectList] Audio context created successfully');
          this.audioInitialized = true;
        } catch (error) {
          console.error('[ProjectList] Failed to create audio context:', error);
          return;
        }
      }
      
      // Create a function to play sound that can be called on demand
      this.playSound = () => {
        try {
          if (!this.audioContext) {
            throw new Error('Audio context not available');
          }
          
          // Resume the audio context if it's suspended (browser requirement)
          if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
          }
          
          // Create a bell/ring sound
          const oscillator1 = this.audioContext.createOscillator();
          const oscillator2 = this.audioContext.createOscillator();
          const gainNode = this.audioContext.createGain();
          
          // Bell-like frequencies
          oscillator1.type = 'sine';
          oscillator1.frequency.setValueAtTime(1567.98, this.audioContext.currentTime); // G6
          
          oscillator2.type = 'sine';
          oscillator2.frequency.setValueAtTime(2349.32, this.audioContext.currentTime); // D7
          
          // Set up envelope for a bell sound
          gainNode.gain.setValueAtTime(0.1, this.audioContext.currentTime);
          gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.5);
          
          // Connect nodes
          oscillator1.connect(gainNode);
          oscillator2.connect(gainNode);
          gainNode.connect(this.audioContext.destination);
          
          // Play bell sound
          oscillator1.start();
          oscillator2.start();
          
          // Bell sound decay
          setTimeout(() => {
            oscillator1.stop();
            oscillator2.stop();
          }, 500);
          
          console.log('[ProjectList] Bell sound played using Web Audio API');
          return Promise.resolve();
        } catch (error) {
          console.error('[ProjectList] Error playing sound with Web Audio API:', error);
          return Promise.reject(error);
        }
      };
    },
    async playTestSound() {
      if (this.isSoundEnabled) {
        try {
          console.log('[ProjectList] Playing test sound');
          
          // Create audio context on first user interaction
          if (!this.audioInitialized) {
            this.createAudioElement();
          }
          
          // Play the sound
          await this.playSound();
          
          console.log('[ProjectList] Test sound played successfully');
        } catch (error) {
          console.error('Error playing test sound:', error);
          
          // Try recreating the audio context if we encountered an error
          if (!this.audioInitialized || error.message.includes('context')) {
            console.log('[ProjectList] Attempting to recreate audio context');
            this.audioContext = null;
            this.createAudioElement();
          }
        }
      }
    },
    async playNotificationSound() {
      if (this.isSoundEnabled) {
        try {
          console.log('[ProjectList] Attempting to play notification sound');
          
          // Create audio context on first user interaction
          if (!this.audioInitialized) {
            this.createAudioElement();
          }
          
          // Play the sound
          await this.playSound();
          
          console.log('[ProjectList] Sound played successfully');
        } catch (error) {
          console.error('[ProjectList] Error in playNotificationSound:', error);
          
          // Try recreating the audio context if we encountered an error
          if (!this.audioInitialized || error.message.includes('context')) {
            console.log('[ProjectList] Attempting to recreate audio context');
            this.audioContext = null;
            this.createAudioElement();
          }
        }
      } else {
        console.log('[ProjectList] Sound is disabled');
      }
    },
    handleExpandClick(project) {
      // Call the generic toggleDescription instead of duplicating logic
      this.toggleDescription(project);
    },
    getProjectEarnings(project) {
      if (!project || !project.project_details) {
        console.log('Invalid project data:', project);
        return 0;
      }
      
      console.log('Checking earnings for project:', project.project_details.title);
      
      // Check multiple potential locations for earnings data
      let earnings = null;
      
      // First check project details
      if (project.project_details.earnings) {
        earnings = project.project_details.earnings;
        console.log('Found earnings in project_details.earnings:', earnings);
      }
      
      // Then check if there's an employer_earnings_score
      if (!earnings && project.employer_earnings_score) {
        earnings = project.employer_earnings_score;
        console.log('Found earnings in employer_earnings_score:', earnings);
      }
      
      // Check if there's a reputation object with earnings
      if (!earnings && project.project_details.reputation?.earnings) {
        earnings = project.project_details.reputation.earnings;
        console.log('Found earnings in project_details.reputation.earnings:', earnings);
      }
      
      // Additional check for employer object
      if (!earnings && project.project_details.employer?.earnings) {
        earnings = project.project_details.employer.earnings;
        console.log('Found earnings in project_details.employer.earnings:', earnings);
      }
      
      // Log if no earnings were found
      if (!earnings) {
        console.log('No earnings found in any location for project:', project.project_details.title);
      }
      
      // Ensure we return a valid number or 0
      const numericEarnings = Number(earnings);
      return !isNaN(numericEarnings) && numericEarnings > 0 ? numericEarnings : 0;
    },
    async checkJsonFileExists(project) {
      try {
        const response = await fetch(`/api/check-json/${project.project_details.id}`);
        const data = await response.json();
        
        if (!data.exists) {
          this.missingFiles.add(project.project_details.id);
        } else {
          this.missingFiles.delete(project.project_details.id);
        }
      } catch (error) {
        console.error('Error checking JSON file:', error);
      }
    },
    async checkAllJsonFiles() {
      for (const project of this.projects) {
        await this.checkJsonFileExists(project);
      }
    },
    startFileChecking() {
      // Initial check
      this.checkAllJsonFiles();
      
      // Set up periodic checking every 30 seconds
      this.fileCheckInterval = setInterval(() => {
        this.checkAllJsonFiles();
      }, 30000);
    },
    stopFileChecking() {
      if (this.fileCheckInterval) {
        clearInterval(this.fileCheckInterval);
        this.fileCheckInterval = null;
      }
    }
  }
});
</script>

<style scoped>
.project-list {
  width: 100%;
  margin: 0;
  min-height: 100vh;
  background-color: #f8f5ff;
  transition: background-color 0.3s ease, color 0.3s ease;
}

.project-list.dark-theme {
  background-color: #0f1720;
  color: #ffffff;
}

/* Add global styles for body */
:global(body) {
  margin: 0;
  padding: 0;
  background-color: #f8f5ff;
  transition: background-color 0.3s ease, color 0.3s ease;
}

:global(body.dark-theme) {
  background-color: #0f1720;
  color: #ffffff;
}

.logo-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.4);
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
  background: rgba(15, 23, 32, 0.8);
}

.theme-toggle,
.sound-toggle,
.test-sound {
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

.theme-toggle:hover,
.sound-toggle:hover,
.test-sound:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.dark-theme .theme-toggle,
.dark-theme .sound-toggle,
.dark-theme .test-sound {
  color: #fff;
}

.dark-theme .theme-toggle:hover,
.dark-theme .sound-toggle:hover,
.dark-theme .test-sound:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.theme-toggle i,
.sound-toggle i,
.test-sound i {
  font-size: 1.2em;
}

.logo {
  height: 40px;
  width: auto;
  transition: filter 0.3s ease;
  filter: invert(0);
}

.logo.inverted {
  filter: invert(1);
}

.project-card {
  background: #f8f5ff;
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
  background: #172434;
  border-color: #2a3a4a;
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

/* Colored icons for metrics */
.completed-icon {
  color: #4CAF50; /* Green */
}

.rating-icon {
  color: #FFC107; /* Yellow/Gold */
}

.score-icon {
  color: #2196F3; /* Blue */
}

.earnings-icon {
  color: #009688; /* Teal */
}

.bids-icon {
  color: #9C27B0; /* Purple */
}

.avg-bid-icon {
  color: #FF9800; /* Orange */
}

.dark-theme .completed-icon {
  color: #81C784; /* Lighter Green */
}

.dark-theme .rating-icon {
  color: #FFD54F; /* Lighter Yellow */
}

.dark-theme .score-icon {
  color: #64B5F6; /* Lighter Blue */
}

.dark-theme .earnings-icon {
  color: #4DB6AC; /* Lighter Teal */
}

.dark-theme .bids-icon {
  color: #BA68C8; /* Lighter Purple */
}

.dark-theme .avg-bid-icon {
  color: #FFB74D; /* Lighter Orange */
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

.elapsed-time {
  font-size: 0.8em;
  color: #666;
  display: flex;
  align-items: center;
  gap: 4px;
}

.dark-theme .timestamp,
.dark-theme .elapsed-time {
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

.action-button.expand {
  background-color: #FFC107;
}

.action-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Clicked state for all buttons */
.action-button.clicked {
  background-color: #888888;
  transform: none;
  box-shadow: none;
  opacity: 0.7;
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
  padding: 12px 24px;
  border-radius: 4px;
  color: white;
  font-weight: 500;
  z-index: 1000;
  animation: slideIn 0.3s ease-out;
}

.notification.success {
  background-color: #4CAF50;
}

.notification.error {
  background-color: #f44336;
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

.skills-container {
  margin-bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
}

.skills-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.skill-badge {
  display: inline-block;
  background-color: #f2f2f2;
  color: #333333;
  font-size: 0.75em;
  padding: 3px 8px;
  border-radius: 12px;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.dark-theme .skill-badge {
  background-color: #2c3e50;
  color: #8ab4f8;
}

.skill-badge:hover {
  background-color: #e5e5e5;
  transform: translateY(-1px);
}

.dark-theme .skill-badge:hover {
  background-color: #34495e;
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
  gap: 10px;
  align-items: center;
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

.project-card.missing-file {
  animation: fadeToRed 2s forwards;
  pointer-events: none;
  opacity: 0.7;
}

.dark-theme .project-card.missing-file {
  animation: fadeToRedDark 2s forwards;
}

@keyframes fadeToRed {
  from {
    background-color: var(--card-bg);
  }
  to {
    background-color: rgba(255, 200, 200, 0.3);
  }
}

@keyframes fadeToRedDark {
  from {
    background-color: var(--card-bg-dark);
  }
  to {
    background-color: rgba(100, 0, 0, 0.3);
  }
}
</style>
