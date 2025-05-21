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
             'missing-file': missingFiles.has(project.project_details.id),
             'last-opened': lastOpenedProject === project.project_details.id,
             'high-paying': project.project_details.flags?.is_high_paying,
             'german': project.project_details.flags?.is_german,
             'urgent': project.project_details.flags?.is_urgent,
             'enterprise': project.project_details.flags?.is_enterprise
           }"
           @click="handleCardClick($event, project)">
        <div class="content-container">
        <div class="project-header">
          <div class="project-metrics">
            <span class="metric" title="Country">
              <img 
                :src="`https://flagcdn.com/24x18/${getCountryCode(project.project_details.country)}.png`"
                :srcset="`https://flagcdn.com/48x36/${getCountryCode(project.project_details.country)}.png 2x`"
                  :width="project.showDescription ? 24 : 16"
                  :height="project.showDescription ? 18 : 12"
                :alt="project.project_details.country"
                class="country-flag"
              >
                <template v-if="project.showDescription">
              {{ project.project_details.country }}
                </template>
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
            <span v-if="project.project_details.bid_stats && project.project_details.bid_stats.bid_avg" class="metric" title="Avg Bid" :class="{ 'hourly-price': isHourlyProject(project.project_details) }">
              <i class="fas fa-coins avg-bid-icon"></i> {{ getCurrencySymbol(project.project_details) }}{{ project.project_details.bid_stats.bid_avg.toFixed(0) }}
              <i v-if="isHourlyProject(project.project_details)" class="fas fa-clock hourly-icon"></i>
            </span>
            <span class="metric" title="Time since posting">
              <i class="fas fa-clock"></i> {{ getElapsedTime(project.project_details.time_submitted) }}
            </span>
          </div>
            <h3 class="project-title" :title="project.project_details.title">
              {{ project.project_details.title }}
            </h3>
        </div>
        
        <div class="project-info">
          <div class="description-container">
              <div v-if="project.project_details.jobs && project.project_details.jobs.length > 0 && project.showDescription" class="skills-container">
              <div class="skills-badges">
                <span v-for="skill in project.project_details.jobs" :key="skill.id" class="skill-badge">
                  {{ skill.name }}
                </span>
              </div>
            </div>
              <p class="description" v-html="nl2br(project.project_details.description)">
              </p>
              <!-- Explanation text after description -->
              <div v-if="project.ranking?.explanation" class="explanation-section">
                <h4>Projekt-Analyse:</h4>
                <p class="explanation">{{ project.ranking.explanation }}</p>
            </div>
            
            <!-- Project links section - only visible when expanded -->
            <div v-if="project.showDescription" class="project-links" @click.stop>
              <a :href="project.project_url" target="_blank" class="project-link" @click.stop>
                <i class="fas fa-external-link-alt"></i> Project
              </a>
                <a v-if="project.links?.employer && !project.links.employer.endsWith('/unknown')" 
                   :href="project.links.employer" 
                   target="_blank" 
                   class="employer-link" 
                   @click.stop>
                <i class="fas fa-user"></i> Employer
              </a>
              </div>
              <!-- Project flags in expanded view -->
              <div v-if="project.showDescription && project.project_details.flags" class="project-flags">
                <span v-if="project.project_details.flags.is_high_paying" class="flag-badge high-paying">💰 High Paying</span>
                <span v-if="project.project_details.flags.is_german" class="flag-badge german">🇩🇪 German</span>
                <span v-if="project.project_details.flags.is_urgent" class="flag-badge urgent">⚡ Urgent</span>
                <span v-if="project.project_details.flags.is_enterprise" class="flag-badge enterprise">🏢 Enterprise</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="project-footer">
          <div class="footer-left">
            <button class="action-button project-link" 
                    :class="{ 'clicked': project.buttonStates?.projectLinkClicked }"
                    @click.stop="openProject(project)" 
                    title="View Project">
              <i class="fas fa-external-link-alt"></i>
            </button>
            <button v-if="project.links?.employer && !project.links.employer.endsWith('/unknown')"
                    class="action-button employer-link" 
                    :class="{ 'clicked': project.buttonStates?.employerLinkClicked }"
                    @click.stop="openEmployerProfile(project)" 
                    title="View Employer">
              <i class="fas fa-user"></i>
            </button>
          </div>
          <div class="footer-right">
            <button class="action-button expand" 
                    :class="{ 'clicked': project.buttonStates?.expandClicked }"
                    @click.stop="handleExpandClick(project)">
              <i class="fas fa-expand-alt"></i>
            </button>
            <button class="action-button generate"
                    :class="{ 'clicked': project.buttonStates?.generateClicked, 'disabled': project.ranking?.bid_teaser?.first_paragraph }"
                    @click.stop="handleProjectClick(project)">
              <i v-if="loadingProject === project.project_details.id" class="fas fa-spinner fa-spin"></i>
              <i v-else class="fas fa-robot"></i>
            </button>
            <button v-if="project.ranking?.bid_teaser?.first_paragraph"
                    class="action-button copy-and-open"
                    :class="{ 'active': project.ranking?.bid_teaser?.first_paragraph, 'clicked': project.buttonStates?.copyClicked }"
                    @click.stop="handleClipboardAndProjectOpen(project)">
              <i class="fas fa-copy"></i>
            </button>
            <button v-if="project.ranking?.bid_teaser?.first_paragraph"
                    class="action-button question"
                    :class="{ 'clicked': project.buttonStates?.questionClicked }"
                    @click.stop="handleQuestionClick(project)">
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
      gainNode: null,
      oscillators: [],
      audioQueue: [],
      isPlayingAudio: false,
      timeUpdateInterval: null,
      missingFiles: new Set(),
      fileCheckInterval: null,
      loadingProject: null,
      lastOpenedProject: null,
      currencySymbols: {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'AUD': 'A$',
        'CAD': 'C$',
        'INR': '₹',
        'JPY': '¥',
        'CNY': '¥',
        'CHF': 'CHF'
      }
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
  async mounted() {
    console.log('[ProjectList] mounted aufgerufen');
    console.log('[ProjectList] DOM Element:', this.$el);
    
    // Add animation delay to project cards
    this.$nextTick(() => {
      const cards = this.$el.querySelectorAll('.project-card');
      cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.05}s`;
      });
    });
    
    // Start polling for new projects
    this.startPolling();
    
    // Start timer to update elapsed times
    this.timeUpdateInterval = setInterval(() => {
      this.forceUpdate();
    }, 1000);

    // Start file checking
    this.startFileChecking();

    // Initialize audio context (but don't wait for it)
    this.initializeAudio().catch(error => {
      console.warn('[Audio] Failed to initialize audio context:', error);
    });
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
    this.cleanupAudio();
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
      return this.sortProjects(this.projects);
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
    sortProjects(projects) {
      return [...projects].sort((a, b) => {
        // Convert timestamps to milliseconds for comparison
        const getTimestamp = (project) => {
          const timestamp = project.project_details?.time_submitted || project.timestamp;
          return typeof timestamp === 'number' ? timestamp * 1000 : new Date(timestamp).getTime();
        };
        
        const timestampA = getTimestamp(a);
        const timestampB = getTimestamp(b);
        
        // Handle invalid dates by putting them at the end
        if (isNaN(timestampA)) return 1;
        if (isNaN(timestampB)) return -1;
        if (isNaN(timestampA) && isNaN(timestampB)) return 0;
        
        // Sort in descending order (newest first)
        return timestampB - timestampA;
      });
    },
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
          method: 'GET',
          mode: 'cors',
          headers: {
            'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
            'Pragma': 'no-cache',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
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
        
        // Play sound if there are new projects and audio is ready
        if (newProjects.length > 0 && this.audioContext) {
          // Get the highest score among new projects
          const highestScore = Math.max(...newProjects.map(project => project.bid_score || 0));
          // Play the notification sound with the highest score
          await this.playNotificationSound(highestScore);
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
          method: 'GET',
          mode: 'cors',
          headers: {
            'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
            'Pragma': 'no-cache',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
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
              questionClicked: false,
              projectLinkClicked: false,
              employerLinkClicked: false
            };
          }
        });
        
        // Update projects array
        this.projects = data;
        
        // Create a Set of current project URLs
        const currentProjectUrls = new Set(data.map(job => job.project_url));
        console.log('[ProjectList] Current project URLs:', currentProjectUrls);
        
        // Find new projects by comparing with lastKnownProjects
        const newProjects = data.filter(job => !this.lastKnownProjects.has(job.project_url));
        console.log('[ProjectList] New projects:', newProjects);
        
        // Update lastKnownProjects with current project URLs
        this.lastKnownProjects = currentProjectUrls;
        
        // Play sound if there are new projects on initial load and audio is ready
        if (newProjects.length > 0 && this.audioContext) {
          // Get the highest score among new projects
          const highestScore = Math.max(...newProjects.map(project => project.bid_score || 0));
          // Play the notification sound with the highest score
          await this.playNotificationSound(highestScore);
        }

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
      
      // Convert Unix timestamp to milliseconds if it's in seconds
      const timestampMs = typeof timestamp === 'number' ? timestamp * 1000 : new Date(timestamp).getTime();
      const now = Date.now(); // Use Date.now() for better performance
      
      // Check for invalid dates or future dates
      if (isNaN(timestampMs)) return 'Invalid date';
      if (timestampMs > now) return 'Future date';
      
      const diffMs = now - timestampMs;
      
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
      if (days === 0) parts.push(`${seconds}s`); // Only show seconds if less than a day old
      
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
        console.log('[BidTeaser] Bid teaser texts already present, skipping generation');
          return;
        }

      // Set loading state for this project
      this.loadingProject = project.project_details.id;
      console.log('[BidTeaser] Loading state set for project:', project.project_details.id);

      try {
        // Initialize buttonStates if not exists
        if (!project.buttonStates) {
          project.buttonStates = {};
        }
        project.buttonStates.generateClicked = true;

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
          // First parse the outer JSON string
          let parsedOuter = JSON.parse(responseText);
          
          // Check if the result is still a string (double encoded)
          if (typeof parsedOuter === 'string') {
            // Parse the inner JSON string
            data = JSON.parse(parsedOuter);
            console.log('[BidTeaser] Parsed double-encoded JSON:', data);
          } else {
            // Assume it was single-encoded JSON
            data = parsedOuter;
            console.log('[BidTeaser] Parsed single-encoded JSON:', data);
          }
          
        } catch (parseError) {
          console.error('[BidTeaser] JSON parse error:', parseError);
          throw new Error('Invalid response format from server');
        }

        // Access the bid_teaser correctly nested within bid_text
        if (!data.bid_text || !data.bid_text.bid_teaser) {
          console.error('[BidTeaser] Missing bid_text or bid_teaser in parsed data:', data);
          throw new Error('Missing bid_text or bid_teaser in response structure');
        }

        // Update the project with the correctly extracted bid teaser texts
        project.ranking.bid_teaser = data.bid_text.bid_teaser;
        console.log('[BidTeaser] Project updated with new bid teaser texts:', project.ranking.bid_teaser);

        // Verify the JSON file was updated by checking the project again
        try {
          const verifyResponse = await fetch(`${API_BASE_URL}/api/jobs`);
          if (!verifyResponse.ok) {
            console.warn('[BidTeaser] Warning: Could not verify JSON update, but bid text was generated successfully');
          } else {
            const projects = await verifyResponse.json();
            const updatedProject = projects.find(p => p.project_details.id === project.project_details.id);
            
            if (!updatedProject?.ranking?.bid_teaser?.first_paragraph) {
              console.warn('[BidTeaser] Warning: JSON file verification shows missing bid text, but local update was successful');
            }
          }
        } catch (verifyError) {
          console.warn('[BidTeaser] Warning: Error during JSON verification, but bid text was generated successfully:', verifyError);
        }

        // Show success notification
        this.showNotification('Bid text generated successfully', 'success');

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
            projectId: project.project_details.id,
            buttonType,
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
      project.buttonStates.expandClicked = true;
      this.updateButtonState(project, 'expandClicked');
      this.toggleDescription(project);
    },
    async handleClipboardAndProjectOpen(project) {
      try {
        if (!project.ranking?.bid_teaser) {
          this.showNotification('No bid text available yet', 'error');
          return;
        }

        // Update last opened project
        this.lastOpenedProject = project.project_details.id;

        // Format the bid text
        const formattedText = this.formatBidText(project);
        
        // Try to write to clipboard
        try {
          await navigator.clipboard.writeText(formattedText);
          console.log('Text copied to clipboard');
        } catch (clipboardError) {
          console.warn('Direct clipboard access failed, trying fallback method:', clipboardError);
          
          // Fallback method using textarea
          const textArea = document.createElement('textarea');
          textArea.value = formattedText;
          document.body.appendChild(textArea);
          textArea.select();
          
          try {
            document.execCommand('copy');
            console.log('Text copied to clipboard (fallback method)');
          } catch (fallbackError) {
            console.error('Fallback copy failed:', fallbackError);
            throw new Error('Failed to copy text to clipboard');
          } finally {
            document.body.removeChild(textArea);
          }
        }

        // Ensure the URL is properly formatted
        let projectUrl = project.project_url;
        if (!projectUrl || !projectUrl.startsWith('http')) {
          projectUrl = `https://www.freelancer.com/projects/${project.project_details.id}`;
        }

        // Open the project in a new tab
        window.open(projectUrl, '_blank', 'noopener,noreferrer');

        // Update button state only after successful clipboard and window open operations
        await this.updateButtonState(project, 'copyClicked');

      } catch (error) {
        console.error('Error handling clipboard and project open:', error);
        this.showNotification(error.message || 'Failed to copy text and open project', 'error');
      }
    },
    openProject(project) {
      if (!project.buttonStates) {
        project.buttonStates = {};
      }
      project.buttonStates.projectLinkClicked = true;
      this.updateButtonState(project, 'projectLinkClicked');
      window.open(project.project_url, '_blank', 'noopener,noreferrer');
    },
    async handleQuestionClick(project) {
      try {
        if (!project.ranking?.bid_teaser?.question) {
          this.showNotification('No question available for this project', 'error');
          return;
        }

        const text = project.ranking.bid_teaser.question;
        
        // Try to write to clipboard
        try {
          await navigator.clipboard.writeText(text);
          console.log('Question copied to clipboard');
        } catch (clipboardError) {
          console.warn('Direct clipboard access failed, trying fallback method:', clipboardError);
          
          // Fallback method using textarea
          const textArea = document.createElement('textarea');
          textArea.value = text;
          document.body.appendChild(textArea);
          textArea.select();
          
          try {
            document.execCommand('copy');
            console.log('Question copied to clipboard (fallback method)');
          } catch (fallbackError) {
            console.error('Fallback copy failed:', fallbackError);
            throw new Error('Failed to copy question to clipboard');
          } finally {
            document.body.removeChild(textArea);
          }
        }

        // Update button state only after successful clipboard operation
        await this.updateButtonState(project, 'questionClicked');

      } catch (error) {
        console.error('Error handling question click:', error);
        this.showNotification(error.message || 'Failed to copy question', 'error');
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
      // Prevent toggling if clicking on buttons or if text is selected
      if (event.target.closest('.project-actions') || 
          event.target.closest('.project-links') ||
          window.getSelection().toString() ||
          event.target.closest('.action-button') ||
          event.target.closest('.copy-and-open') ||
          event.target.closest('.question')) {
        event.stopPropagation();
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
    getCurrencySymbol(projectDetails) {
      if (!projectDetails) return '$';
      
      // Try to find currency in different possible locations
      let currency = 'USD';
      
      // First check the new structured location we added in bidder.py
      if (projectDetails.bid_stats && projectDetails.bid_stats.currency) {
        currency = projectDetails.bid_stats.currency;
      }
      
      return this.currencySymbols[currency] || '$';
    },
    
    isHourlyProject(projectDetails) {
      if (!projectDetails) return false;
      
      // First check the dedicated project_type field we added in bidder.py
      if (projectDetails.project_type === 'hourly') {
        return true;
      }

      
      return false;
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
      if (this.audioContext) {
        // If context exists but is suspended, try to resume it
        if (this.audioContext.state === 'suspended') {
          try {
            await this.audioContext.resume();
            console.log('[Audio] Resumed existing audio context, state:', this.audioContext.state);
          } catch (error) {
            console.error('[Audio] Failed to resume audio context:', error);
            // If we can't resume, create a new context
            this.cleanupAudio();
          }
        }
        return;
      }
      
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.audioContext = new AudioContext();
        
        // Create main gain node
        this.gainNode = this.audioContext.createGain();
        this.gainNode.gain.value = 0.5; // 50% volume
        this.gainNode.connect(this.audioContext.destination);
        
        console.log('[Audio] Context initialized successfully, state:', this.audioContext.state);
        
        // Resume audio context if it's suspended (needed for some browsers)
        if (this.audioContext.state === 'suspended') {
          await this.audioContext.resume();
          console.log('[Audio] Audio context resumed, new state:', this.audioContext.state);
        }
      } catch (error) {
        console.error('[Audio] Failed to initialize audio context:', error);
      }
    },
    cleanupAudio() {
      console.log('[Audio] Cleaning up audio resources');
      if (this.oscillators.length > 0) {
        this.oscillators.forEach(osc => {
          try {
            osc.stop();
            osc.disconnect();
          } catch (e) {
            // Ignore errors during cleanup
          }
        });
        this.oscillators = [];
      }
      
      if (this.gainNode) {
        try {
          this.gainNode.disconnect();
        } catch (e) {
          // Ignore errors during cleanup
        }
        this.gainNode = null;
      }
      
      if (this.audioContext) {
        try {
          this.audioContext.close();
        } catch (e) {
          // Ignore errors during cleanup
        }
        this.audioContext = null;
      }
    },
    async ensureAudioContext() {
      if (!this.audioContext || this.audioContext.state === 'closed') {
        await this.initializeAudio();
      } else if (this.audioContext.state === 'suspended') {
        try {
          await this.audioContext.resume();
          console.log('[Audio] Audio context resumed, state:', this.audioContext.state);
        } catch (error) {
          console.error('[Audio] Failed to resume audio context:', error);
          // If resume fails, try reinitializing
          this.cleanupAudio();
          await this.initializeAudio();
        }
      }
      return this.audioContext && this.audioContext.state === 'running';
    },
    async playTestSound() {
      try {
        console.log('[Audio] Playing test sound');
        if (!await this.ensureAudioContext()) {
          throw new Error('Audio context not available or not running');
        }
        
        console.log('[Audio] Audio context state before playing:', this.audioContext.state);
        
        // Create oscillators for a more complex sound
        const osc1 = this.audioContext.createOscillator();
        const osc2 = this.audioContext.createOscillator();
        const oscGain = this.audioContext.createGain();
        
        // Configure oscillators with lower frequencies
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(440, this.audioContext.currentTime); // A4 note
        
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(554.37, this.audioContext.currentTime); // C#5 note
        
        // Configure envelope with longer duration
        oscGain.gain.setValueAtTime(0, this.audioContext.currentTime);
        oscGain.gain.linearRampToValueAtTime(0.5, this.audioContext.currentTime + 0.1);
        oscGain.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 2.0);
        
        // Connect nodes
        osc1.connect(oscGain);
        osc2.connect(oscGain);
        oscGain.connect(this.gainNode);
        
        // Start sound
        osc1.start();
        osc2.start();
        
        console.log('[Audio] Sound started playing');
        
        // Stop sound after envelope completes
        setTimeout(() => {
          try {
            osc1.stop();
            osc2.stop();
            osc1.disconnect();
            osc2.disconnect();
            oscGain.disconnect();
            console.log('[Audio] Sound stopped and cleaned up');
          } catch (error) {
            console.error('[Audio] Error cleaning up oscillators:', error);
          }
        }, 2000);
        
        console.log('[Audio] Test sound played successfully');
      } catch (error) {
        console.error('[Audio] Error playing test sound:', error);
        // Try to reinitialize audio on error
        this.cleanupAudio();
        await this.initializeAudio();
      }
    },
    async playNotificationSound(score = 50) {
      if (!this.isSoundEnabled) return;
      
      try {
        if (!await this.ensureAudioContext()) {
          throw new Error('Audio context not available or not running');
        }
        
        console.log('[Audio] Playing notification with score:', score);
        console.log('[Audio] Audio context state:', this.audioContext.state);
        
        // Calculate frequency based on score, but keep it in a more audible range
        let baseFreq = 440; // A4 note
        if (score <= 30) {
          baseFreq = 220; // A3 - lower pitch for low scores
        } else if (score >= 70) {
          baseFreq = 554.37; // C#5 - higher pitch but not too high
        }
        
        // Create oscillators
        const osc1 = this.audioContext.createOscillator();
        const osc2 = this.audioContext.createOscillator();
        const oscGain = this.audioContext.createGain();
        
        // Configure oscillators
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(baseFreq, this.audioContext.currentTime);
        
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(baseFreq * 1.25, this.audioContext.currentTime); // Perfect third
        
        // Configure envelope with longer duration
        oscGain.gain.setValueAtTime(0, this.audioContext.currentTime);
        oscGain.gain.linearRampToValueAtTime(0.4, this.audioContext.currentTime + 0.1);
        oscGain.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 2.0);
        
        // Connect nodes
        osc1.connect(oscGain);
        osc2.connect(oscGain);
        oscGain.connect(this.gainNode);
        
        // Start sound
        osc1.start();
        osc2.start();
        
        // Store oscillators for cleanup
        this.oscillators.push(osc1, osc2);
        
        console.log('[Audio] Notification sound started');
        
        // Stop sound after envelope completes
        setTimeout(() => {
          try {
            osc1.stop();
            osc2.stop();
            osc1.disconnect();
            osc2.disconnect();
            oscGain.disconnect();
            
            // Remove from oscillators array
            this.oscillators = this.oscillators.filter(o => o !== osc1 && o !== osc2);
            console.log('[Audio] Notification sound cleaned up');
          } catch (error) {
            console.error('[Audio] Error cleaning up notification sound:', error);
          }
        }, 2000);
        
        console.log('[Audio] Notification sound played successfully');
      } catch (error) {
        console.error('[Audio] Error playing notification:', error);
        // Try to reinitialize audio on error
        this.cleanupAudio();
        await this.initializeAudio();
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
    formatBidText(project) {
      if (!project.ranking.bid_teaser) return '';
      
      // Format the bid text with proper line breaks and spacing
      let formattedText = '';

      if (project.ranking.bid_teaser.third_paragraph) {
        formattedText += project.ranking.bid_teaser.third_paragraph + '\n\n';
      }
      
      if (project.ranking.bid_teaser.first_paragraph) {
        formattedText += project.ranking.bid_teaser.first_paragraph + '\n\n';
      }

      if (project.ranking.explanation) {
        formattedText += project.ranking.explanation + '\n\n';
      }
 
      if (project.ranking.bid_teaser.second_paragraph) {
        formattedText += project.ranking.bid_teaser.second_paragraph + '\n\n';
      }
      
      formattedText += 'Best Regards,\nDamian';

      // Replace — with ...
      formattedText = formattedText.replace('—', '... ');
      
      return formattedText.trim();
    },
    getPreviewDescription(description) {
      // Remove this method as it's no longer needed
      return description;
    },
    openEmployerProfile(project) {
      if (project.links?.employer) {
        if (!project.buttonStates) {
          project.buttonStates = {};
        }
        project.buttonStates.employerLinkClicked = true;
        this.updateButtonState(project, 'employerLinkClicked');
        window.open(project.links.employer, '_blank', 'noopener,noreferrer');
      }
    },
  }
});
</script>

<style scoped>
.project-list {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  box-sizing: border-box;
  padding: 0;
  margin: 0;
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
  min-height: 100vh;
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
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin: 0;
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
  margin: 0 auto;
}

.logo.inverted {
  filter: invert(1);
}

.project-card {
  background: white;
  border-radius: 2px; /* Reduziert von 4px */
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.1); /* Noch subtilerer Schatten */
  transition: all 0.2s ease;
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  margin: 0;
  padding: 0;
  transform-origin: center;
  display: flex;
  flex-direction: column;
}

.project-card:not(.expanded) {
  .content-container {
    height: 170px;
    overflow: hidden;
    position: relative;
    padding: 6px 10px;
    display: flex;
    flex-direction: column;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
  }

  .project-header {
    width: 100%;
    box-sizing: border-box;
  }

  .project-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 6px;
    width: 100%;
    box-sizing: border-box;
    align-items: center;

    .metric {
      display: flex;
      align-items: center;
      gap: 3px;
      font-size: 0.7em;
      color: #666;
      white-space: nowrap;
      padding: 2px 4px;
      border-radius: 4px;
      background: rgba(0, 0, 0, 0.03);
      
      i {
        font-size: 0.9em;
        opacity: 0.8;
      }
      
      &:hover {
        background: rgba(0, 0, 0, 0.05);
      }
    }
  }

  .project-title {
    font-size: 0.75em;
    padding: 0;
    margin: 0 0 8px 0;
    max-width: 100%;
    white-space: normal;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .project-info {
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    position: relative;
    height: 100%;
    overflow: hidden;
  }

  .description {
    padding: 15px;
    margin: 0;
    word-wrap: break-word;
    overflow-wrap: break-word;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    text-align: left;
    line-height: 1.4;
    white-space: pre-wrap;
    font-size: 0.7em;
    height: 100%;
    overflow-x: hidden;
    overflow-y: auto;
    hyphens: auto;
  }

  .project-footer {
    padding: 4px 8px;
    height: 28px;
    
    .footer-left, .footer-right {
      gap: 4px;
    }
    
    .action-button {
      width: 20px;
      height: 20px;
      border-radius: 3px;
      
      i {
        font-size: 0.7rem;
      }
      
      &:hover {
        transform: translateY(-1px);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      }
    }
  }
}

.project-card.expanded {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100vw;
  height: 100vh;
  margin: 0;
  padding: 20px;
  z-index: 1000;
  background: white;
  overflow-y: auto;
  border-radius: 0;
  box-shadow: none;

  .content-container {
    height: auto;
    overflow: visible;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    box-sizing: border-box;
  }

  .project-header {
    margin-bottom: 20px;
  }

  .project-metrics {
    margin-bottom: 15px;
    font-size: 1.2em;
    display: flex;
    flex-wrap: wrap;
    gap: 16px; /* Increased from default gap */
    
    .metric {
      display: flex;
      align-items: center;
      gap: 8px; /* Increased space between icon and text */
      padding: 4px 8px; /* Added some padding around each metric */
      
      i {
        font-size: 1.1em; /* Slightly larger icons in expanded view */
      }
    }
  }

  .project-title {
    font-size: 1.8em;
    margin: 0 0 20px 0;
    line-height: 1.4;
  }

  .project-info {
    margin-bottom: 30px;
  }

  .description {
    font-size: 1.2em;
    line-height: 1.6;
    white-space: pre-line;
  }

  .project-links {
    margin: 20px 0;
    display: flex;
    gap: 15px;
    
    a {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 20px;
      border-radius: 6px;
      text-decoration: none;
      font-size: 1.1em;
      transition: all 0.2s ease;
      
      &.project-link {
        background: #2196F3;
        color: white;
        
        &:hover {
          background: #1976D2;
        }
      }
      
      &.employer-link {
        background: #9C27B0;
        color: white;
        
        &:hover {
          background: #7B1FA2;
        }
      }
      
      i {
        font-size: 1.2em;
      }
    }
  }

  .project-flags {
    margin: 20px 0;
    
    .flag-badge {
      font-size: 1.1em;
      padding: 8px 16px;
    }
  }

  .project-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: white;
    padding: 15px 20px;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    z-index: 1001;
    
    .project-actions {
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      
      .action-button {
        width: 44px;
        height: 44px;
        font-size: 1.2em;
        
        &:hover {
          transform: translateY(-2px);
        }
      }
    }
  }
}

.dark-theme .project-card.expanded {
  background: #0f1720;
  
  .project-footer {
    background: #0f1720;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.3);
  }
}

/* Close button for expanded view */
.project-card.expanded::before {
  content: '×';
  position: fixed;
  top: 20px;
  right: 20px;
  width: 40px;
  height: 40px;
  background: rgba(0, 0, 0, 0.1);
  color: #333;
  font-size: 32px;
  line-height: 40px;
  text-align: center;
  border-radius: 50%;
  cursor: pointer;
  z-index: 1002;
  transition: all 0.3s ease;
}

.dark-theme .project-card.expanded::before {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.project-card.expanded::before:hover {
  background: rgba(0, 0, 0, 0.2);
  transform: scale(1.1);
}

/* Add overlay for non-expanded cards */
.project-card.expanded ~ .project-card {
  display: none;
}

.project-card:not(.expanded) {
  transform: scale(0.96); /* Von 0.98 auf 0.96 - etwas kleiner im Normalzustand */
  opacity: 1;
  transition: all 0.3s ease;
}

.project-card:not(.expanded):hover {
  transform: scale(1.04); /* Von 1.02 auf 1.04 - etwas größer beim Hover */
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.project-card:not(.expanded) .project-title {
  font-size: 0.9em;
  padding: 8px 0;
}

.project-card:not(.expanded) .metric {
  font-size: 0.7em;
}

.project-card:not(.expanded) .action-button {
  width: 24px;
  height: 24px;
  font-size: 0.9rem;
}

.project-card:not(.expanded) .skill-badge {
  font-size: 0.65em;
  padding: 2px 6px;
}

.project-card:not(.expanded) .description {
  font-size: 0.8em;
}

.project-card.expanded .description {
  font-size: 1.4em;
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto;
}

.project-card.expanded .project-title {
  font-size: 2em;
  padding: 20px 0;
}

.project-card.expanded .metric {
  font-size: 1.2em;
}

.project-card.expanded .action-button {
  width: 50px;
  height: 50px;
  font-size: 1.5rem;
}

.project-card.expanded .skill-badge {
  font-size: 1.2em;
  padding: 6px 12px;
}

/* Add smooth transition for all elements */
.project-card * {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Media queries for responsive layout */
@media (max-width: 2000px) {
  .projects {
    grid-template-columns: repeat(10, 1fr);
    gap: 1px;
    padding: 1px;
  }
}

@media (max-width: 1800px) {
  .projects {
    grid-template-columns: repeat(8, 1fr);
    gap: 1px;
    padding: 1px;
  }
}

@media (max-width: 1600px) {
  .projects {
    grid-template-columns: repeat(6, 1fr);
    gap: 1px;
    padding: 1px;
  }
}

@media (max-width: 1200px) {
  .projects {
    grid-template-columns: repeat(5, 1fr);
    gap: 1px;
    padding: 1px;
  }
}

@media (max-width: 900px) {
  .projects {
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    padding: 1px;
  }
}

@media (max-width: 600px) {
  .projects {
    grid-template-columns: 1fr;
    gap: 1px;
    padding: 1px;
  }
}

/* Base colors for different flags */
.project-card.high-paying {
  background: #fff3cd;
  border: 1px solid #ffeeba;
}

.project-card.german {
  background: #d4edda;
  border: 1px solid #c3e6cb;
}

.project-card.urgent {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
}

.project-card.enterprise {
  background: #cce5ff;
  border: 1px solid #b8daff;
}

/* Dark theme adjustments */
.dark-theme .project-card.high-paying {
  background: #2c2c00;
  border-color: #4d4d00;
}

.dark-theme .project-card.german {
  background: #1a3d1a;
  border-color: #3d5d3d;
}

.dark-theme .project-card.urgent {
  background: #3d1a1a;
  border-color: #5d3d3d;
}

.dark-theme .project-card.enterprise {
  background: #1a1a3d;
  border-color: #3d3d5d;
}

/* Remove shimmer effect */
.project-card::before {
  display: none;
}

/* Remove animation keyframes */
@keyframes shimmer {
  0%, 50%, 100% {
    opacity: 0;
  }
}

/* Remove mix-blend-mode effects */
.project-card.high-paying.german {
  background: #fff3cd;
}

.project-card.high-paying.urgent {
  background: #fff3cd;
}

.project-card.german.urgent {
  background: #d4edda;
}

.project-card.enterprise.technical {
  background: #cce5ff;
}

/* Dark theme mix-blend-mode removals */
.dark-theme .project-card.high-paying.german {
  background: #2c2c00;
}

.dark-theme .project-card.high-paying.urgent {
  background: #2c2c00;
}

.dark-theme .project-card.german.urgent {
  background: #1a3d1a;
}

.dark-theme .project-card.enterprise.technical {
  background: #1a1a3d;
}

/* Ensure text remains readable */
.project-card {
  color: #333;
}

.dark-theme .project-card {
  color: #fff;
}

/* Simplify transitions */
.project-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.project-card:hover {
  transform: translateY(-1px); /* Reduced lift effect from -2px */
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Reduced shadow from 0 4px 8px */
}

.dark-theme .project-card:hover {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2); /* Reduced shadow */
}

.project-header {
  box-sizing: border-box;
  width: 100%;
  flex-shrink: 0;

  .elapsed-time {
    font-size: 0.7em;
    color: #666;
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 4px;

    i {
      font-size: 0.9em;
      opacity: 0.8;
    }
  }
}

.project-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
  width: 100%;
  box-sizing: border-box;
  align-items: center;

  .metric {
    display: flex;
    align-items: center;
    gap: 3px;
    font-size: 0.7em;
    color: #666;
    white-space: nowrap;
    padding: 2px 4px;
    border-radius: 4px;
    background: rgba(0, 0, 0, 0.03);
    
    i {
      font-size: 0.9em;
      opacity: 0.8;
    }
    
    &:hover {
      background: rgba(0, 0, 0, 0.05);
    }
  }
}

.dark-theme {
  .project-metrics .metric {
    color: #aaa;
    background: rgba(255, 255, 255, 0.05);
    
    &:hover {
      background: rgba(255, 255, 255, 0.08);
    }
  }
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

.fa-clock {
  color: #607D8B; /* Blue Grey */
}

.dark-theme {
  .completed-icon { color: #81C784; }
  .rating-icon { color: #FFD54F; }
  .score-icon { color: #64B5F6; }
  .earnings-icon { color: #4DB6AC; }
  .bids-icon { color: #BA68C8; }
  .avg-bid-icon { color: #FFB74D; }
  .fa-clock { color: #90A4AE; }
}

.country-flag {
  border-radius: 2px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.project-title {
  margin: 0;
  padding: 15px 0;
  word-break: break-word;
  width: 100%;
  box-sizing: border-box;
  font-size: 1.4em;
  line-height: 1.4;
  text-align: center;
  font-weight: 600;
}

.project-card:not(.expanded) .project-title {
  font-size: 0.75em;
  padding: 4px 0;
  max-width: 100%;
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  height: 2.8em;
}

.project-card.expanded .project-title {
  white-space: normal;
  font-size: 1.5em;
  padding: 10px 0;
  -webkit-line-clamp: unset;
  height: auto;
}

.dark-theme .project-title {
  color: #fff;
}

.project-info {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  position: relative;
  height: 100%;
  overflow: hidden;
}

.description-container {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  height: 100%;
  overflow: hidden;
}

.description {
  padding: 15px;
  margin: 0;
  word-wrap: break-word;
  overflow-wrap: break-word;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  text-align: left;
  line-height: 1.4;
  white-space: pre-wrap;
  font-size: 0.7em;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  hyphens: auto;
}

.project-card:not(.expanded) {
  .description {
    font-size: 0.55em;
    padding: 0;
    text-overflow: ellipsis;
    display: block;
    overflow: hidden;
    width: 100%;
    max-width: 100%;
    height: 100%; /* Volle Höhe in der Listenansicht */
  }
}

.project-card.expanded {
  .description {
    font-size: 1.1em;
    padding: 30px;
    max-width: 800px;
    width: 100%;
    margin: 0 auto;
    line-height: 1.6;
    overflow-y: auto;
    white-space: pre-wrap;
    height: initial; /* Automatische Höhe im Detail-View */
  }
}

.dark-theme .description {
  color: #aaa;
}

.project-card.expanded .description {
  font-size: 1.1em;
  padding: 15px;
  line-height: 1.6;
}

.project-card.expanded .description {
  font-size: 1.1em;
  padding: 15px;
  line-height: 1.6;
}

.project-card.expanded .explanation {
  font-size: 1.2em;
  padding: 15px;
  line-height: 1.6;
}

.project-card.expanded .explanation {
  font-size: 1.2em;
  padding: 15px;
  line-height: 1.6;
}

.project-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  box-sizing: border-box;
  border-top: 1px solid #eee;
  flex-shrink: 0;

  .footer-left, .footer-right {
    display: flex;
    align-items: center;
  }

  .action-button {
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
    color: white;
  display: flex;
  align-items: center;
    justify-content: center;
    padding: 0;

    &.project-link {
      background-color: #2196F3;
      &:hover { background-color: #1976D2; }
    }

    &.employer-link {
      background-color: #9C27B0;
      &:hover { background-color: #7B1FA2; }
    }

    &.expand {
      background-color: #FFC107;
    }

    &.generate {
      background-color: #4CAF50;
    }

    &.copy-and-open {
      background-color: #f44336;
    }

    &.question {
      background-color: #FF9800;
    }

    &.clicked {
      background-color: #888888;
      transform: none !important;
      box-shadow: none !important;
      opacity: 0.7;
    }

    &.disabled {
      background-color: #999;
      cursor: not-allowed;
      pointer-events: none;
    }
  }
}

.dark-theme {
  .elapsed-time {
    color: #aaa;
  }
}

.action-button.view {
  background-color: #4CAF50;
}

.action-button.question {
  background-color: #FF9800; /* Orange color */
}

.action-button.question:hover {
  background-color: #F57C00; /* Darker orange on hover */
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
  margin-top: 20px;
  padding: 20px;
  border-top: 1px solid #eee;
  max-width: 800px;
  width: 100%;
  margin-left: auto;
  margin-right: auto;
  box-sizing: border-box;
}

.dark-theme .explanation-section {
  border-top-color: #3a4b5c;
}

.explanation-section h4 {
  color: #333;
  margin-bottom: 15px;
  font-size: 1.2em;
  font-weight: 600;
}

.dark-theme .explanation-section h4 {
  color: #fff;
}

.explanation {
  font-size: 1em;
  line-height: 1.5;
  color: #666;
  white-space: pre-wrap;
  text-align: left;
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin: 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.dark-theme .explanation {
  background-color: #3a4b5c;
  color: #aaa;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.project-card.expanded .explanation {
  font-size: 1.2em;
  line-height: 1.6;
}

/* Project links styles */
.project-links {
  display: flex;
  gap: 15px;
  margin: 10px 15px;
  padding-top: 10px;
  border-top: 1px solid #eee;
}

.dark-theme .project-links {
  border-top-color: #3a4b5c;
}

.project-link, .employer-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #2196F3;
  text-decoration: none;
  font-size: 0.85em;
  padding: 5px 10px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.employer-link {
  color: #9C27B0;
}

.project-link:hover, .employer-link:hover {
  background-color: rgba(0, 0, 0, 0.05);
  transform: translateY(-1px);
}

.dark-theme .project-link, .dark-theme .employer-link {
  color: #64B5F6;
}

.dark-theme .employer-link {
  color: #BA68C8;
}

.dark-theme .project-link:hover, .dark-theme .employer-link:hover {
  background-color: rgba(255, 255, 255, 0.1);
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
  grid-template-columns: repeat(12, 1fr);
  gap: 1px; /* Minimaler Abstand zwischen den Karten */
  padding: 1px; /* Minimaler äußerer Abstand */
  width: 100%;
  max-width: 2400px;
  margin: 0 auto;
  box-sizing: border-box;
  margin-top: 60px;
}

@media (max-width: 2000px) {
  .projects {
    grid-template-columns: repeat(10, 1fr);
    gap: 1px;
    padding: 1px;
  }
}
@media (max-width: 1800px) {
  .projects {
    grid-template-columns: repeat(8, 1fr);
    gap: 1px;
    padding: 1px;
  }
}
@media (max-width: 1600px) {
  .projects {
    grid-template-columns: repeat(6, 1fr);
    gap: 1px;
    padding: 1px;
  }
}
@media (max-width: 1200px) {
  .projects {
    grid-template-columns: repeat(5, 1fr);
    gap: 1px;
    padding: 1px;
  }
  }
@media (max-width: 900px) {
  .projects {
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    padding: 1px;
  }
}
@media (max-width: 600px) {
  .projects {
    grid-template-columns: 1fr;
    gap: 1px;
    padding: 1px;
  }
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

.action-button.generate .fa-spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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

.project-card.last-opened {
  background-color: rgba(76, 175, 80, 0.1);  /* Light green background */
  transition: background-color 0.3s ease;
}

.dark-theme .project-card.last-opened {
  background-color: rgba(76, 175, 80, 0.2);  /* Slightly darker green for dark theme */
}

/* Add CSS for hourly project indicator */
.metric.project-type {
  font-weight: 500;
}

.metric.project-type.hourly-project {
  background-color: #00c853;
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: bold;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.dark-theme .metric.project-type.hourly-project {
  background-color: #00e676;
  color: #000;
}

/* Remove the project-type styles and replace with hourly price indicator */
.metric.hourly-price {
  background-color: #00e676; /* Brighter green */
  color: #000; /* Black text for better contrast */
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: bold;
  box-shadow: 0 2px 8px rgba(0, 230, 118, 0.4); /* Green glow */
  transition: all 0.2s ease;
  animation: pulse 2s infinite; /* Subtle pulse animation */
}

.dark-theme .metric.hourly-price {
  background-color: #00e676; /* Keep the same bright green for dark theme */
  color: #000; /* Black text for contrast */
  box-shadow: 0 2px 8px rgba(0, 230, 118, 0.6); /* Stronger glow for dark theme */
}

/* Pulse animation for hourly prices */
@keyframes pulse {
  0% {
    box-shadow: 0 2px 8px rgba(0, 230, 118, 0.4);
  }
  50% {
    box-shadow: 0 2px 12px rgba(0, 230, 118, 0.7);
  }
  100% {
    box-shadow: 0 2px 8px rgba(0, 230, 118, 0.4);
  }
}

.hourly-icon {
  margin-left: 4px;
  font-size: 0.9em;
}

.project-card.high-paying {
  background-color: #fff3cd;  /* Light yellow background */
  border-color: #ffeeba;
}

.project-card.german {
  background-color: #d4edda;  /* Light green background */
  border-color: #c3e6cb;
}

/* If both classes are present, high-paying takes precedence */
.project-card.high-paying.german {
  background-color: #fff3cd;
  border-color: #ffeeba;
}

.project-card.expanded .project-header {
  max-width: 900px;
  width: 100%;
  margin: 32px auto 0 auto;
  padding: 10px 24px 10px 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 2;
  border-radius: 12px;
  box-sizing: border-box;
}

.project-card.expanded .project-title {
  white-space: normal;
  font-size: 1.5em;
  padding: 10px 0;
}

@media (max-width: 950px) {
  .project-card.expanded .project-header {
    max-width: 100vw;
    padding: 10px 8px;
    margin: 16px 0 0 0;
    border-radius: 0;
  }
  .project-card.expanded .project-title {
    font-size: 1.1em;
    padding: 6px 0;
  }
}

.dark-theme .project-card.expanded .project-header {
  background: rgba(15, 23, 32, 0.9);
}

.project-card.expanded .description {
  font-size: 1.4em;
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto;
}

.project-card.expanded .metric {
  font-size: 1.2em;
}

.project-card.expanded .action-button {
  width: 50px;
  height: 50px;
  font-size: 1.5rem;
}

.project-card.expanded .skill-badge {
  font-size: 1.2em;
  padding: 6px 12px;
}

.project-card.expanded .project-footer {
  position: sticky;
  bottom: 0;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: 20px;
  z-index: 2;
}

.dark-theme .project-card.expanded .project-footer {
  background: rgba(15, 23, 32, 0.9);
}

/* Add close button for expanded view */
.project-card.expanded::before {
  content: '×';
  position: fixed;
  top: 20px;
  right: 20px;
  width: 40px;
  height: 40px;
  background: rgba(0, 0, 0, 0.1);
  color: #333;
  font-size: 32px;
  line-height: 40px;
  text-align: center;
  border-radius: 50%;
  cursor: pointer;
  z-index: 1001;
  transition: all 0.3s ease;
}

.dark-theme .project-card.expanded::before {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.project-card.expanded::before:hover {
  background: rgba(0, 0, 0, 0.2);
}

.dark-theme .project-card.expanded::before:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Add overlay for non-expanded cards */
.projects:has(.project-card.expanded) {
  position: relative;
}

/* Remove overlay for expanded view */
.projects:has(.project-card.expanded)::after {
  display: none !important;
}

/* Center expanded card content and limit width */
.project-card.expanded {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  overflow-y: auto;
}

.project-card.expanded > * {
  max-width: 900px;
  width: 100%;
  margin-left: auto;
  margin-right: auto;
}

/* Hide country name and reduce flag size in collapsed view */
.project-card:not(.expanded) .metric .country-flag {
  width: 16px !important;
  height: 12px !important;
}
.project-card:not(.expanded) .metric {
  font-size: 0.6em;
}
.project-card:not(.expanded) .metric {
  /* Hide country name text, only show flag */
}
.project-card:not(.expanded) .metric {
  /* Hide the country name next to the flag */
}
.project-card:not(.expanded) .metric {
  /* We'll hide the country name in the template below */
}
.project-card:not(.expanded) .project-title {
  font-size: 0.75em;
  padding: 4px 0;
  max-width: 100%;
}
.project-card:not(.expanded) .skill-badge {
  font-size: 0.55em;
  padding: 1px 4px;
}
.project-card:not(.expanded) .description {
  font-size: 0.65em;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* Add styles for project flags */
.project-flags {
  display: flex;
  gap: 8px;
  margin: 10px 15px 0 15px;
  flex-wrap: wrap;
}
.flag-badge {
  display: inline-flex;
  align-items: center;
  font-size: 0.95em;
  padding: 3px 10px;
  border-radius: 12px;
  background: #f2f2f2;
  color: #333;
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.flag-badge.high-paying { background: #fff3cd; color: #b8860b; }
.flag-badge.german { background: #d4edda; color: #155724; }
.flag-badge.urgent { background: #f8d7da; color: #721c24; }
.flag-badge.enterprise { background: #cce5ff; color: #004085; }
.dark-theme .flag-badge { background: #222; color: #eee; }

/* Add styles for the explanation details */
.explanation-details {
  margin-top: 15px;
  font-size: 1em;
  line-height: 1.5;
  color: #666;
  white-space: pre-wrap;
  text-align: left;
  background-color: #f4f4f4;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.dark-theme .explanation-details {
  background-color: #2a3b4c;
  color: #aaa;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.project-card.expanded .explanation-details {
  font-size: 1.1em;
  line-height: 1.6;
}
</style>
