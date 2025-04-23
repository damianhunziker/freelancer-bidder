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
    
    <!-- Loading overlay -->
    <div v-if="loadingProject" class="loading-overlay">
      <div class="loading-spinner"></div>
      <div class="loading-text">Generating bid text...</div>
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
                    :class="{ 'clicked': project.buttonStates?.expandClicked }"
                    @click="handleExpandClick(project)">
              <i class="fas fa-expand-alt"></i>
            </button>
            <button class="action-button generate"
                    :class="{ 'clicked': project.buttonStates?.generateClicked, 'disabled': project.ranking?.bid_teaser?.first_paragraph }"
                    @click="handleProjectClick(project)">
              <i v-if="loadingProject === project.project_details.id" class="fas fa-spinner fa-spin"></i>
              <i v-else class="fas fa-robot"></i>
            </button>
            <button class="action-button copy-and-open"
                    :class="{ 'active': project.ranking?.bid_teaser?.first_paragraph, 'clicked': project.buttonStates?.copyClicked }"
                    @click="handleClipboardAndProjectOpen(project)">
              <i class="fas fa-external-link-alt"></i>
            </button>
            <button class="action-button question"
                    :class="{ 'clicked': project.buttonStates?.questionClicked }"
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
import { API_BASE_URL } from '../config';

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
      fileCheckInterval: null,
      loadingProject: null, // Track which project is being loaded
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

    // Initialize theme based on system preference or saved setting
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      this.isDarkTheme = savedTheme === 'dark';
    } else {
      // Use system preference
      this.systemThemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
      this.isDarkTheme = this.systemThemeQuery.matches;
      
      // Add listener for system theme changes
      this.systemThemeQuery.addEventListener('change', this.handleSystemThemeChange);
    }
    this.applyTheme();
    
    // Initialize sound preference
    const soundEnabled = localStorage.getItem('soundEnabled');
    if (soundEnabled !== null) {
      this.isSoundEnabled = soundEnabled === 'true';
    }
    
    // Start loading projects immediately
    this.loadProjects();
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
      // Save user preference
      localStorage.setItem('theme', this.isDarkTheme ? 'dark' : 'light');
      this.applyTheme();
    },
    handleSystemThemeChange(e) {
      // Only update if user hasn't manually set a preference
      if (!localStorage.getItem('theme')) {
        this.isDarkTheme = e.matches;
        this.applyTheme();
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
        const response = await fetch(`${API_BASE_URL}/api/jobs`, {
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
        const response = await fetch(`${API_BASE_URL}/api/jobs`, {
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
        
        // Initialize buttonStates for each project if not exists
        data.forEach(project => {
          if (!project.buttonStates) {
            project.buttonStates = {
              expandClicked: false,
              copyClicked: false,
              questionClicked: false
            };
          }
        });
        
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
          
          setTimeout(() => {
            project.isNew = false;
          }, 1000);
        }
        
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
      console.log('[BidTeaser] Project clicked:', project.project_details.id);

      // Check if bid teaser texts are already present
      if (project.ranking?.bid_teaser?.first_paragraph) {
        console.log('[BidTeaser] Bid teaser texts already present, proceeding with clipboard and project opening');
        await this.handleClipboardAndProjectOpen(project);
        return;
      }

      // Set loading state for this project
      this.loadingProject = project.project_details.id;
      console.log('[BidTeaser] Loading state set for project:', project.project_details.id);

      try {
        // If no score is available, fetch initial ranking first
        if (!project.ranking?.score) {
          console.log('[BidTeaser] No score available, fetching initial ranking');
          const rankingResponse = await fetch(`${API_BASE_URL}/api/rank-project/${project.project_details.id}`);
          if (!rankingResponse.ok) {
            throw new Error('Failed to fetch initial ranking');
          }
          const rankingData = await rankingResponse.json();
          project.ranking = rankingData;
          console.log('[BidTeaser] Initial ranking fetched:', rankingData);
        }

        // Generate bid text
        console.log('[BidTeaser] Generating bid text for project:', project.project_details.id);
        const response = await fetch(`${API_BASE_URL}/api/generate-bid/${project.project_details.id}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            score: project.ranking.score,
            explanation: project.ranking.explanation
          })
        });

        if (!response.ok) {
          throw new Error(`Failed to generate bid text: ${response.statusText}`);
        }

        const responseText = await response.text();
        console.log('[BidTeaser] Raw response:', responseText);

        let data;
        try {
          data = JSON.parse(responseText);
        } catch (parseError) {
          console.error('[BidTeaser] JSON parse error:', parseError);
          throw new Error('Invalid response format from server');
        }

        if (!data.bid_teaser) {
          throw new Error('Missing bid_teaser in response');
        }

        // Update the project with the new bid teaser texts
        project.ranking.bid_teaser = data.bid_teaser;
        console.log('[BidTeaser] Project updated with new bid teaser texts');

      } catch (error) {
        console.error('[BidTeaser] Error:', error);
        this.showNotification('Failed to generate bid text: ' + error.message, 'error');
      } finally {
        // Clear loading state
        this.loadingProject = null;
        console.log('[BidTeaser] Loading state cleared for project:', project.project_details.id);
      }
    },
    async updateButtonState(project, buttonType) {
      try {
        console.log('Updating button state:', { 
          projectId: project.project_details.id, 
          buttonType, 
          state: true 
        });
        
        const response = await fetch(`${API_BASE_URL}/api/update-button-state`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            projectId: project.project_details.id.toString(), // Ensure ID is a string
            buttonType: buttonType,
            state: true
          })
        });

        if (!response.ok) {
          throw new Error('Failed to update button state');
        }

        // Update local state after successful API call
        if (!project.buttonStates) {
          project.buttonStates = {};
        }
        project.buttonStates[buttonType] = true;
        
      } catch (error) {
        console.error('Error updating button state:', error);
        this.$emit('error', 'Failed to update button state');
      }
    },
    handleExpandClick(project) {
      if (!project.buttonStates) {
        project.buttonStates = {};
      }
      project.buttonStates.expandClicked = !project.buttonStates.expandClicked;
      this.updateButtonState(project, 'expandClicked');
      this.toggleDescription(project);
    },
    async handleClipboardAndProjectOpen(project) {
      try {
        // Format the bid text
        const bidText = this.formatBidText(project.ranking.bid_teaser, project.project_details.description);

        // Try to write to clipboard directly
        try {
          await navigator.clipboard.writeText(bidText);
          console.log('Bid text copied to clipboard');
        } catch (error) {
          console.error('Failed to write to clipboard:', error);
          
          // If clipboard API fails, try the fallback method
          const textArea = document.createElement('textarea');
          textArea.value = bidText;
          document.body.appendChild(textArea);
          textArea.select();
          
          try {
            document.execCommand('copy');
            console.log('Bid text copied to clipboard (fallback method)');
          } catch (fallbackError) {
            console.error('Fallback copy failed:', fallbackError);
            this.$emit('error', 'Failed to copy text to clipboard. Please try again.');
            return;
          } finally {
            document.body.removeChild(textArea);
          }
        }

        // Ensure the URL is properly formatted
        let projectUrl = `https://www.freelancer.com/projects/${project.project_details.id}`;
        
        // Open project in new tab
        window.open(projectUrl, '_blank', 'noopener,noreferrer');
      } catch (error) {
        console.error('Error in handleClipboardAndProjectOpen:', error);
        this.$emit('error', 'An error occurred while processing the project. Please try again.');
      }
    },
    openProject(project) {
      console.log('[BidTeaser] Opening project:', project.project_details.id);
      window.open(`https://www.freelancer.com/projects/${project.project_details.id}`, '_blank');
    },
    async handleQuestionClick(project) {
      try {
        if (!project.buttonStates) {
          project.buttonStates = {};
        }
        project.buttonStates.questionClicked = true;

        // Check if bid_teaser exists
        if (!project.ranking?.bid_teaser) {
          console.error('No bid teaser available');
          return;
        }

        // Extract and copy the question if it exists
        const question = project.ranking.bid_teaser.question;
        if (question) {
          await navigator.clipboard.writeText(question);
          this.showNotification('Question copied to clipboard!', 'success');
        } else {
          console.error('No question found in bid teaser');
          this.showNotification('No question available', 'error');
        }

        await this.updateButtonState(project, 'questionClicked');
      } catch (error) {
        console.error('Error copying question:', error);
        this.showNotification('Failed to copy question', 'error');
      }
    },
    toggleDescription(project) {
      project.showDescription = !project.showDescription;
      
      // Mark the expand button as clicked when expanding
      if (project.showDescription) {
        project.buttonStates.expandClicked = true;
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
        'Andorra': 'ad',
        'Qatar': 'qa',
        'United Arab Emirates': 'ae',
        'Saudi Arabia': 'sa',
        'Kuwait': 'kw',
        'Bahrain': 'bh',
        'Oman': 'om',
        'Hong Kong': 'hk',
        'Taiwan': 'tw',
        'Macau': 'mo',
        'Brunei': 'bn',
        'Malaysia': 'my',
        'Thailand': 'th',
        'Vietnam': 'vn',
        'Indonesia': 'id',
        'Philippines': 'ph',
        'Mexico': 'mx',
        'Chile': 'cl',
        'Argentina': 'ar',
        'Uruguay': 'uy',
        'Costa Rica': 'cr',
        'Panama': 'pa',
        'Colombia': 'co',
        'Peru': 'pe',
        'Ecuador': 'ec',
        'South Africa': 'za',
        'Mauritius': 'mu',
        'Seychelles': 'sc',
        'Turkey': 'tr',
        'Ukraine': 'ua',
        'Kazakhstan': 'kz',
        'Azerbaijan': 'az',
        'Georgia': 'ge',
        'Armenia': 'am',
        'Moldova': 'md',
        'Belarus': 'by',
        'Serbia': 'rs',
        'Montenegro': 'me',
        'North Macedonia': 'mk',
        'Albania': 'al',
        'Bosnia and Herzegovina': 'ba',
        'Kosovo': 'xk'
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
    async initializeAudio() {
      if (this.audioInitialized) return;
      
      try {
        // Create audio context
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.audioContext = new AudioContext();
        
        // Create a gain node for volume control
        this.gainNode = this.audioContext.createGain();
        this.gainNode.gain.value = 0.5; // Set volume to 50%
        this.gainNode.connect(this.audioContext.destination);
        
        console.log('[ProjectList] Audio context created successfully');
        this.audioInitialized = true;
      } catch (error) {
        console.error('[ProjectList] Failed to create audio context:', error);
      }
    },
    async playTestSound() {
      try {
        console.log('[ProjectList] Playing test sound');
        
        // Initialize audio if needed
        await this.initializeAudio();
        
        if (!this.audioInitialized) {
          throw new Error('Audio initialization failed');
        }
        
        // Create oscillators for a bell sound
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
        gainNode.connect(this.gainNode);
        
        // Play bell sound
        oscillator1.start();
        oscillator2.start();
        
        // Bell sound decay
        setTimeout(() => {
          oscillator1.stop();
          oscillator2.stop();
          oscillator1.disconnect();
          oscillator2.disconnect();
          gainNode.disconnect();
        }, 500);
        
        console.log('[ProjectList] Test sound played successfully');
      } catch (error) {
        console.error('Error playing test sound:', error);
      }
    },
    async playNotificationSound() {
      try {
        if (!this.isSoundEnabled) return;
        
        console.log('[ProjectList] Attempting to play notification sound');
        
        // Initialize audio if needed
        await this.initializeAudio();
        
        if (!this.audioInitialized) {
          throw new Error('Audio initialization failed');
        }
        
        // Create oscillators for a bell sound
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
        gainNode.connect(this.gainNode);
        
        // Play bell sound
        oscillator1.start();
        oscillator2.start();
        
        // Bell sound decay
        setTimeout(() => {
          oscillator1.stop();
          oscillator2.stop();
          oscillator1.disconnect();
          oscillator2.disconnect();
          gainNode.disconnect();
        }, 500);
        
        console.log('[ProjectList] Sound played successfully');
      } catch (error) {
        console.error('[ProjectList] Error in playNotificationSound:', error);
      }
    },
    getProjectEarnings(project) {
      if (!project || !project.project_details) {
        console.log('Invalid project data:', project);
        return 0;
      }
      
      //console.log('Checking earnings for project:', project.project_details.title);
      
      // Check multiple potential locations for earnings data
      let earnings = null;
      
      // First check project details
      if (project.project_details.earnings) {
        earnings = project.project_details.earnings;
        //console.log('Found earnings in project_details.earnings:', earnings);
      }
      
      // Then check if there's an employer_earnings_score
      if (!earnings && project.employer_earnings_score) {
        earnings = project.employer_earnings_score;
        //console.log('Found earnings in employer_earnings_score:', earnings);
      }
      
      // Check if there's a reputation object with earnings
      if (!earnings && project.project_details.reputation?.earnings) {
        earnings = project.project_details.reputation.earnings;
        //console.log('Found earnings in project_details.reputation.earnings:', earnings);
      }
      
      // Additional check for employer object
      if (!earnings && project.project_details.employer?.earnings) {
        earnings = project.project_details.employer.earnings;
        //console.log('Found earnings in project_details.employer.earnings:', earnings);
      }
      
      // Log if no earnings were found
      if (!earnings) {
        //console.log('No earnings found in any location for project:', project.project_details.title);
      }
      
      // Ensure we return a valid number or 0
      const numericEarnings = Number(earnings);
      return !isNaN(numericEarnings) && numericEarnings > 0 ? numericEarnings : 0;
    },
    async checkJsonFileExists(project) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/check-json/${project.project_details.id}`);
        const data = await response.json();
        
        if (!data.exists) {
          this.missingFiles.add(project.project_details.id);
          // Remove the project from the projects array
          const index = this.projects.findIndex(p => p.project_details.id === project.project_details.id);
          if (index !== -1) {
            this.projects.splice(index, 1);
          }
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
    },
    formatBidText(bidTeaser, description) {
      if (!bidTeaser) return '';
      
      // Format the bid text with proper line breaks and spacing
      let formattedText = '';
      
      if (bidTeaser.first_paragraph) {
        formattedText += bidTeaser.first_paragraph + '\n\n';
      }
      
      if (bidTeaser.second_paragraph && description.length > 1000) {
        formattedText += bidTeaser.second_paragraph + '\n\n';
      }
      
      if (bidTeaser.third_paragraph) {
        formattedText += bidTeaser.third_paragraph + '\n\n';
      }
      
      return formattedText.trim();
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
  display: none; /* Completely hide the card instead of showing it with reduced opacity */
}

/* Remove the fadeToRed and fadeToRedDark animations since we're hiding the cards completely */
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

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 5px solid #f3f3f3;
  border-top: 5px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-text {
  color: white;
  margin-top: 20px;
  font-size: 1.2em;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.dark-theme .loading-overlay {
  background-color: rgba(0, 0, 0, 0.7);
}

.dark-theme .loading-spinner {
  border-color: #2c3e50;
  border-top-color: #3498db;
}

.dark-theme .loading-text {
  color: #ecf0f1;
}

.action-button.generate {
  background-color: #2196F3;
}

.action-button.generate.disabled {
  background-color: #999;
  cursor: not-allowed;
  pointer-events: none;
}

.action-button.generate:hover {
  background-color: #1976D2;
}

.action-button.copy-and-open {
  background-color: #999;
  transition: background-color 0.3s ease;
}

.action-button.copy-and-open.active {
  background-color: #f44336;
}

.action-button.copy-and-open:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.action-button.copy-and-open.active:hover {
  background-color: #d32f2f;
}

/* Add clicked state for copy-and-open button */
.action-button.copy-and-open.clicked {
  background-color: #888888;
  transform: none;
  box-shadow: none;
  opacity: 0.7;
}
</style>
