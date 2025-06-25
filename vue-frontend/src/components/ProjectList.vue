<template>
  <div class="project-list" :class="{ 'dark-theme': isDarkTheme }">

    <div class="logo-container" :class="{ 'dark-theme': isDarkTheme }">
      <img src="https://vyftec.com/wp-content/uploads/2024/10/Element-5-3.svg" alt="Vyftec Logo" class="logo" :class="{ 'inverted': isDarkTheme }">
    <div class="header-controls">
        <!-- Automatic Bidding Checkbox -->
        <div class="auto-bidding-control">
          <label class="auto-bidding-label">
            <input 
              type="checkbox" 
              v-model="automaticBiddingEnabled"
              @change="onAutomaticBiddingToggle"
              class="auto-bidding-checkbox"
            >
            <span class="checkbox-text">Automatic Bidding</span>
            <i v-if="automaticBiddingEnabled" class="fas fa-robot bidding-icon"></i>
          </label>
        </div>
        
        <!-- Recent Only Checkbox -->
        <div class="auto-bidding-control">
          <label class="auto-bidding-label">
            <input 
              type="checkbox" 
              v-model="recentOnlyEnabled"
              @change="onRecentOnlyToggle"
              class="auto-bidding-checkbox"
            >
            <span class="checkbox-text">Recent Only</span>
            <i v-if="recentOnlyEnabled" class="fas fa-clock bidding-icon"></i>
          </label>
        </div>

        <!-- Post Question Checkbox -->
        <div class="auto-bidding-control">
          <label class="auto-bidding-label">
            <input 
              type="checkbox" 
              v-model="postQuestionEnabled"
              @change="onPostQuestionToggle"
              class="auto-bidding-checkbox"
            >
            <span class="checkbox-text">Post Question</span>
            <i v-if="postQuestionEnabled" class="fas fa-question-circle bidding-icon"></i>
          </label>
        </div>

        <!-- Tag Filters -->
        <div class="tag-filters-container">
          <button 
            class="filters-toggle" 
            @click="showTagFilters = !showTagFilters"
            :class="{ 'active': showTagFilters || activeFilters.length > 0 }"
          >
            <i class="fas fa-filter"></i>
            <span>Tags</span>
            <span v-if="activeFilters.length > 0" class="filter-count">{{ activeFilters.length }}</span>
          </button>
          
          <div v-if="showTagFilters" class="tag-filters-dropdown">
            <div class="filter-section">
              <h4>Project Tags</h4>
              <div class="tag-options">
                <label v-for="tag in availableTags" :key="tag.key" class="tag-option">
                  <input 
                    type="checkbox" 
                    :value="tag.key"
                    v-model="selectedTags"
                    @change="onTagFilterChange"
                  >
                  <span class="tag-checkbox" :class="tag.cssClass"></span>
                  <span class="tag-label">{{ tag.label }}</span>
                  <span class="tag-count">({{ getTagCount(tag.key) }})</span>
                </label>
              </div>
            </div>
            
            <div class="filter-actions">
              <button @click="clearAllFilters" class="clear-filters">Clear All</button>
              <button @click="showTagFilters = false" class="close-filters">Close</button>
            </div>
          </div>
        </div>
        
        <button class="theme-toggle" @click="toggleTheme" :title="isSystemThemeMode ? 'Manual Theme Mode (Currently following system)' : 'Toggle Theme'">
          <i :class="isDarkTheme ? 'fas fa-sun' : 'fas fa-moon'"></i>
          <span v-if="isSystemThemeMode" class="system-indicator">🔄</span>
        </button>
        <button v-if="!isSystemThemeMode" class="system-theme-reset" @click="resetToSystemTheme" title="Reset to System Theme">
          <i class="fas fa-desktop"></i>
        </button>
        <div class="sound-controls">
        <button class="sound-toggle" @click="toggleSound">
          <i :class="isSoundEnabled ? 'fas fa-volume-up' : 'fas fa-volume-mute'"></i>
        </button>
          <input 
            type="range" 
            min="0" 
            max="100" 
            v-model="volumeLevel" 
            class="volume-slider"
            :class="{ 'disabled': !isSoundEnabled }"
            @input="updateVolume"
          >
        </div>
        <button class="test-sound" @click="playTestSound" :disabled="audioSystemTesting" :title="audioSystemTesting ? 'Testing audio system...' : 'Test sound'">
          <i v-if="audioSystemTesting" class="fas fa-spinner fa-spin"></i>
          <i v-else class="fas fa-music"></i>
          </button>
        <button class="debug-audio" @click="toggleAudioDebug" title="Audio Debug">
          <i class="fas fa-bug"></i>
        </button>
        <button class="simple-beep" @click="playSimpleBeep" title="Einfacher Beep-Test">
          <i class="fas fa-bell"></i>
        </button>
        <button class="auto-bid-debug" @click="toggleAutoBidDebug" title="Auto-Bidding Debug Console">
          <i class="fas fa-cog"></i>
        </button>
        <button class="test-push-notification" @click="testPushNotification" title="Test Push Notification">
          <i class="fas fa-bell"></i>
        </button>
      </div>
    </div>
    
    <!-- Audio Debug Panel -->
    <div v-if="showAudioDebug" class="audio-debug-panel" :class="{ 'dark-theme': isDarkTheme }">
      <div class="debug-header">
        <h4>Audio System Debug</h4>
        <button @click="showAudioDebug = false" class="close-debug">×</button>
      </div>
      <div class="debug-content">
        <div class="debug-section">
          <strong>Browser Support:</strong>
          <ul>
            <li>AudioContext: {{ !!window.AudioContext ? '✓' : '✗' }}</li>
            <li>webkitAudioContext: {{ !!window.webkitAudioContext ? '✓' : '✗' }}</li>
            <li>HTML5 Audio: {{ !!window.Audio ? '✓' : '✗' }}</li>
          </ul>
        </div>
        <div class="debug-section">
          <strong>Audio Context Status:</strong>
          <ul>
            <li>Exists: {{ !!audioContext ? '✓' : '✗' }}</li>
            <li>State: {{ audioContext ? audioContext.state : 'N/A' }}</li>
            <li>Gain Node: {{ !!gainNode ? '✓' : '✗' }}</li>
            <li>Sound Enabled: {{ isSoundEnabled ? '✓' : '✗' }}</li>
            <li>Volume: {{ volumeLevel }}%</li>
          </ul>
        </div>
        <div class="debug-section">
          <strong>Actions:</strong>
          <button @click="forceAudioRestart" class="debug-button">Force Restart Audio</button>
          <button @click="testAudioSystem" class="debug-button">Test Audio System</button>
          <button @click="tryAlternativeSound" class="debug-button">Try Alternative Sound</button>
        </div>
      </div>
    </div>
    
    <!-- Auto-Bidding Debug Console -->
    <div v-if="showAutoBidDebug" 
         class="auto-bid-debug-panel draggable-console resizable-console" 
         :class="{ 'dark-theme': isDarkTheme, 'dragging': isDragging }"
         :style="{ 
           position: 'fixed',
           left: consoleX + 'px',
           top: consoleY + 'px',
           width: consoleWidth + 'px',
           height: consoleHeight + 'px',
           zIndex: 1000 
         }">
      <div class="debug-header drag-handle" 
           @mousedown="startDrag"
           style="cursor: move;">
        <h4>🤖 Auto-Bidding Debug Console</h4>
        <button @click="showAutoBidDebug = false" class="close-debug">×</button>
      </div>
      <div class="debug-content">
        <div class="debug-section">
          <strong>Settings:</strong>
          <ul>
            <li>Auto-Bidding: {{ automaticBiddingEnabled ? '✅ Enabled' : '❌ Disabled' }}</li>
            <li>Filter Mode: {{ recentOnlyEnabled ? '⏰ Recent Only (≤60 min)' : '📅 Extended (≤3 days)' }}</li>
            <li>Active Projects: {{ activeBiddingProjects.size }}</li>
          </ul>
        </div>
        <div class="debug-section log-section">
          <strong>Live Log:</strong>
          <div class="log-container" ref="logContainer">
            <div v-for="(log, index) in reversedAutoBidLogs.slice(0, 200)" :key="log.id || index" 
                 class="log-entry" 
                 :class="[log.type, { 'new-log': log.isNew }]">
              <span class="log-time">{{ formatLogTimestamp(log) }}</span>
              <span class="log-source" v-if="log.source && log.source !== 'vue-frontend'">[{{ log.source }}]</span>
              <span class="log-message" v-html="formatLogMessage(log.message)"></span>
            </div>
            <div v-if="autoBidLogs.length === 0" class="log-entry info">
              <span class="log-message">Waiting for auto-bidding activity...</span>
            </div>
          </div>
          <div class="debug-buttons">
            <button @click="clearLogs" class="debug-button">Clear Logs</button>
            <button @click="showProcessingState" class="debug-button">Show State</button>
            <button @click="resetProcessingState" class="debug-button reset-button">Reset State</button>
          </div>
        </div>
      </div>
      <!-- Resize handles -->
      <div class="resize-handle resize-right" @mousedown="startResize('right', $event)"></div>
      <div class="resize-handle resize-bottom" @mousedown="startResize('bottom', $event)"></div>
      <div class="resize-handle resize-corner" @mousedown="startResize('corner', $event)"></div>
    </div>
    
    <!-- Projects list -->
    <div v-if="!loading && projects.length > 0" class="projects">
      <div v-for="project in sortedProjects" 
           :key="project.project_url" 
           :data-project-id="project.project_details.id"
           class="project-card"
           :class="{ 
             'new-project': project.isNew,
             'removed-project': project.isRemoved,
             'expanded': project.showDescription,
             'fade-in': project.isNew,
             'missing-file': missingFiles.has(project.project_details.id),
             'last-opened': lastOpenedProject === project.project_details.id,
             'recent-project': isRecentProject(project),
             'auto-bidding-active': activeBiddingProjects.has(project.project_details.id)
           }"
           :style="{ 
             backgroundColor: getProjectBackgroundColor(project), 
             ...getProjectBorderStyle(project),
             ...getProjectGlowStyle(project)
           }"
           @click="handleCardClick($event, project)">
        <!-- Bid count overlay for this project -->
        <div v-if="project.showBidOverlay" class="project-bid-overlay">
          <div class="bid-overlay-content">
            <span class="bid-overlay-number">{{ project.newBidCount }}</span>
          </div>
        </div>
        <div class="content-container">
        <div class="project-header">
          <div class="project-metrics">
            <span class="metric" :title="project.project_details.country">
              <img 
                :src="`https://flagcdn.com/24x18/${getCountryCode(project.project_details.country)}.png`"
                :srcset="`https://flagcdn.com/48x36/${getCountryCode(project.project_details.country)}.png 2x`"
                  :width="project.showDescription ? 24 : 16"
                  :height="project.showDescription ? 18 : 12"
                :alt="project.project_details.country"
                :title="project.project_details.country"
                class="country-flag"
              >
                <template v-if="project.showDescription">
              {{ project.project_details.country }}
                </template>
            </span>
            <!-- Add flag tags -->
            <span v-if="isHourlyProject(project.project_details)" class="metric flag-tag hr" title="Hourly Project">HR</span>
            <span v-if="project.project_details.employer_complete_projects && project.project_details.employer_complete_projects !== 'N/A'" class="metric" title="Completed Projects">
              <i class="fas fa-check-circle completed-icon"></i> {{ project.project_details.employer_complete_projects }}
            </span>
            <span v-if="project.project_details.employer_overall_rating && project.project_details.employer_overall_rating !== 0.0" class="metric" title="Employer Rating">
              <i class="fas fa-star rating-icon"></i> {{ project.project_details.employer_overall_rating?.toFixed(1) }}
            </span>
            <span v-if="project.ranking?.score" class="metric" title="Score">
              <i class="fas fa-chart-bar score-icon"></i> {{ project.ranking.score }}
            </span>
            <span v-if="getProjectEarnings(project) && getProjectEarnings(project) !== 0" class="metric" title="Earnings">
              <i class="fas fa-dollar-sign earnings-icon"></i> {{ formatSpending(getProjectEarnings(project)) }}
            </span>
            <span v-if="project.project_details.bid_stats && project.project_details.bid_stats.bid_count" 
                  class="metric" 
                  :class="{ 'bid-count-changed': project.bidCountChanged }"
                  title="Bids">
              <i class="fas fa-gavel bids-icon"></i> <strong>{{ project.project_details.bid_stats.bid_count }}</strong>
            </span>
            <span v-if="project.project_details.bid_stats && getAvgBidValue(project.project_details.bid_stats)" class="metric" title="Avg Bid" :class="{ 'hourly-price': isHourlyProject(project.project_details) }">
              <i class="fas fa-coins avg-bid-icon"></i> {{ getCurrencySymbol(project.project_details) }}<strong>{{ getAvgBidValue(project.project_details.bid_stats).toFixed(0) }}</strong>
              <i v-if="isHourlyProject(project.project_details)" class="fas fa-clock hourly-icon"></i>
            </span>
            <span v-if="project.project_details.flags?.is_high_paying" class="metric flag-tag pay" title="High Paying">PAY</span>
            <span v-if="project.project_details.flags?.is_urgent" class="metric flag-tag urg" title="Urgent">URG</span>
            <span v-if="project.project_details.flags?.is_authentic" class="metric flag-tag auth" title="Authentic">AUTH</span>
            <span v-if="project.project_details.flags?.is_german" class="metric flag-tag germ" title="German">GER</span>
            <span v-if="project.project_details.flags?.is_enterprise" class="metric flag-tag corp" title="Enterprise">CORP</span>
            <span v-if="project.project_details.flags?.is_corr" class="metric flag-tag corr" title="High Correlation">CORR</span>
            <span v-if="project.project_details.flags?.is_rep" class="metric flag-tag rep" title="Good Reputation">REP</span>
            <span v-if="isQualifiedForAutoBidding(project)" class="metric flag-tag qual" title="Qualifies for Automatic Bidding">QUAL</span>
            <span v-if="project.project_details.llm_recog_language" class="metric flag-tag lang" :title="`LLM Detected Language: ${project.project_details.llm_recog_language.toUpperCase()}`">{{ project.project_details.llm_recog_language.toUpperCase() }}</span>
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
            <button                     class="action-button generate"
                    :class="{ 
                      'clicked': project.buttonStates?.generateClicked, 
                      'disabled': project.ranking?.bid_teaser?.first_paragraph,
                      'error': project.buttonStates?.generationFailed 
                    }"
                    :title="getGenerateButtonTitle(project)"
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
                    @click.stop="handleQuestionClick(project)"
                    title="Frage kopieren">
              <i class="fas fa-question-circle"></i>
            </button>
            <button v-if="project.ranking?.bid_teaser?.question"
                    class="action-button send-question"
                    :class="{ 
                      'clicked': project.buttonStates?.questionSent,
                      'loading': project.buttonStates?.sendingQuestion,
                      'disabled': project.buttonStates?.questionSent 
                    }"
                    @click.stop="handleSendQuestionClick(project)"
                    :disabled="project.buttonStates?.questionSent || project.buttonStates?.sendingQuestion"
                    :title="getQuestionButtonTitle(project)">
              <i v-if="project.buttonStates?.sendingQuestion" class="fas fa-spinner fa-spin"></i>
              <i v-else-if="project.buttonStates?.questionSent" class="fas fa-check"></i>
              <i v-else class="fas fa-rocket"></i>
            </button>
            <button v-if="project.ranking?.bid_teaser?.first_paragraph"
                    class="action-button send-application"
                    :class="{ 
                      'clicked': project.buttonStates?.bidSubmitted,
                      'manual-required': project.buttonStates?.manualSubmissionRequired,
                      'disabled': project.buttonStates?.bidSubmitted 
                    }"
                    @click.stop="handleSendApplication(project)"
                    :disabled="project.buttonStates?.bidSubmitted"
                    :title="getApplicationButtonTitle(project)">
              <i v-if="loadingProject === project.project_details.id" class="fas fa-spinner fa-spin"></i>
              <i v-else-if="project.buttonStates?.bidSubmitted" class="fas fa-check"></i>
              <i v-else-if="project.buttonStates?.manualSubmissionRequired" class="fas fa-exclamation-triangle"></i>
              <i v-else class="fas fa-paper-plane"></i>
            </button>
          </div>
        </div>
        </div>
      </div>
    </div>

    <!-- No projects state -->
    <div v-if="!loading && projects.length === 0" class="no-projects">
      No projects found
    </div>
</template>

<script>
import { defineComponent } from 'vue';
import { API_BASE_URL } from '../config';
import { formatBidText } from '@/utils/formatBidText'

export default defineComponent({
  name: 'ProjectList',
  data() {
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
    isSystemThemeMode: true, // Track if we're following system theme
      systemThemeQuery: null,
      isSoundEnabled: true,
      volumeLevel: 50,
      audioContext: null,
      gainNode: null,
      oscillators: [],
      audioQueue: [],
      isPlayingAudio: false,
      audioSystemTesting: false,
      showAudioDebug: false,
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
      },
      projectPollingInterval: null,
      automaticBiddingEnabled: false,
      recentOnlyEnabled: true,
      postQuestionEnabled: false,
      showAutoBidDebug: false,
      autoBidLogs: [],
      autoBidLogPollingInterval: null,
      activeBiddingProjects: new Set(),
      // Track projects currently being processed for auto-bidding
      processingProjectIds: new Set(),
      // Track projects that have already been processed to prevent re-processing
      processedProjectIds: new Set(),
      // Track question posting to prevent duplicates
      questionPostingProjectIds: new Set(),
      // Tag filtering
      showTagFilters: false,
      selectedTags: [],
      availableTags: [
        { key: 'hourly', label: 'HR', cssClass: 'hr', description: 'Hourly Projects' },
        { key: 'high_paying', label: 'PAY', cssClass: 'pay', description: 'High Paying' },
        { key: 'urgent', label: 'URG', cssClass: 'urg', description: 'Urgent' },
        { key: 'authentic', label: 'AUTH', cssClass: 'auth', description: 'Authentic' },
        { key: 'german', label: 'GER', cssClass: 'germ', description: 'German' },
        { key: 'enterprise', label: 'CORP', cssClass: 'corp', description: 'Enterprise' },
        { key: 'correlation', label: 'CORR', cssClass: 'corr', description: 'High Correlation' },
        { key: 'reputation', label: 'REP', cssClass: 'rep', description: 'Good Reputation' },
        { key: 'qualified', label: 'QUAL', cssClass: 'qual', description: 'Auto-Bid Qualified' }
      ],
      // Drag functionality for auto-bidding console
      isDragging: false,
      dragStartX: 0,
      dragStartY: 0,
      consoleX: 100,
      consoleY: 100,
      consoleWidth: 500,
      consoleHeight: 400,
      // Resize functionality
      isResizing: false,
      resizeStartX: 0,
      resizeStartY: 0,
      resizeStartWidth: 0,
      resizeStartHeight: 0,
      resizeHandle: null,
              isPageHidden: false,
        windowHasFocus: true,
        backgroundKeepAliveInterval: null,
        rafId: null,
        wakeLock: null,
    }
  },
  beforeCreate() {
    // Lifecycle hook - no logging needed
  },
  created() {

    // Initialize system theme query first
    this.systemThemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Initialize theme based on system preference or saved setting
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      this.isDarkTheme = savedTheme === 'dark';
      this.isSystemThemeMode = false; // User has manually set a preference
    } else {
      // Use system preference
      this.isDarkTheme = this.systemThemeQuery.matches;
      this.isSystemThemeMode = true; // Following system theme
    }
    
    // Always add listener for system theme changes
    this.systemThemeQuery.addEventListener('change', this.handleSystemThemeChange);
    this.applyTheme();
    
    // Initialize sound preference
    const soundEnabled = localStorage.getItem('soundEnabled');
    if (soundEnabled !== null) {
      this.isSoundEnabled = soundEnabled === 'true';
    }
    
    // Initialize volume level
    const savedVolume = localStorage.getItem('volumeLevel');
    if (savedVolume !== null) {
      this.volumeLevel = parseInt(savedVolume);
    }
    
    // Initialize console position
    this.initializeConsolePosition();
    
    // Start loading projects immediately
    this.loadProjects().catch(error => {
      console.error('[ProjectList] Error in initial loadProjects:', error);
      this.loading = false;
      this.error = error.message;
    });
  },
  beforeMount() {
    // Lifecycle hook - no logging needed
  },
      async mounted() {
      console.log('[ProjectList] Component mounted, loading projects...');
      
      // Initialize background execution features first
      console.log('[BackgroundExecution] Initializing background execution features...');
      this.setupVisibilityHandling();
      await this.setupWakeLockIfSupported();
      this.setupBackgroundKeepAlive();
      
      // Load persistent auto-bid logs before starting other processes
      this.loadPersistentAutoBidLogs();
      
      // Start time tracking and load projects
      this.startTimeTracking();
      await this.loadProjects();
      this.startPolling();
      
      // Add animation delay to project cards
      this.$nextTick(() => {
        // Use document.querySelectorAll instead of this.$el.querySelectorAll
        const cards = document.querySelectorAll('.project-card');
        cards.forEach((card, index) => {
          card.style.animationDelay = `${index * 0.05}s`;
        });
      });
      
      // Start all background tasks asynchronously to not block project display
      setTimeout(() => {
        try {
          // Start file checking
          this.startFileChecking();

          // Start glow update interval
          this.startGlowUpdateInterval();
          
          // Initialize audio context (delayed and non-blocking)
          setTimeout(() => {
            this.initializeAudio().catch(error => {
              console.warn('[Audio] Failed to initialize audio context:', error);
            });
          }, 2000); // Further delay audio initialization
          
        } catch (error) {
          console.error('[ProjectList] Error in background tasks:', error);
        }
      }, 100); // Small delay to ensure projects are loaded first
      
      // Add event listener for closing tag filters dropdown
      document.addEventListener('click', this.handleClickOutside);
      
      console.log('[BackgroundExecution] ✅ All background execution features initialized');
    },

    startFileChecking() {
      // File checking is now handled by the main polling system
      // This function is kept for compatibility but does nothing
      console.log('[ProjectList] File checking integrated into main polling system');
    },

    startGlowUpdateInterval() {
      // Start glow update interval
      setInterval(this.updateProjectGlowIntensity, 30000);
    },
      beforeUnmount() {
      console.log('[ProjectList] Component unmounting, cleaning up...');
      this.stopPolling();
      this.stopTimeTracking();
      this.stopFileWatching();
      this.cleanupVisibilityHandling();
      this.releaseWakeLock();
      this.cleanupBackgroundKeepAlive();
      this.stopAutoBidLogPolling();
      
      // Cleanup system theme listener
      if (this.systemThemeQuery) {
        this.systemThemeQuery.removeEventListener('change', this.handleSystemThemeChange);
      }
    },

  unmounted() {
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
      return this.sortProjects(this.filteredProjects);
    },
    filteredProjects() {
      if (this.selectedTags.length === 0) {
        return this.projects;
      }
      
      return this.projects.filter(project => {
        return this.selectedTags.some(tagKey => this.projectHasTag(project, tagKey));
      });
    },
    activeFilters() {
      return this.selectedTags;
    },
    reversedAutoBidLogs() {
      // Return logs in newest-first order (they're already sorted this way from backend)
      // No need to reverse since we sort by timestamp descending in loadBackendAutoBidLogs
      return this.autoBidLogs.slice();
    },
    getProjectBorderStyle() {
      return (project) => {
        const flags = project.project_details?.flags || {};
        const flagCount = Object.values(flags).filter(Boolean).length;
        
        // Check if project has required tag combination
        const hasQualityFlag = flags.is_corr || flags.is_authentic;
        const hasUrgencyFlag = flags.is_high_paying || flags.is_urgent || flags.is_german || this.isHourlyProject(project.project_details) || flags.is_rep || flags.is_enterprise;
        
        // Only show border if both conditions are met
        if (!hasQualityFlag || !hasUrgencyFlag) {
          return { border: 'none' };
        }

        const colors = [];
        
        // Add RGB colors for each active tag (same as background)
        if (flags.is_high_paying) {
          colors.push([255, 215, 0]); // Yellow for PAY
        }
        if (flags.is_urgent) {
          colors.push([244, 67, 54]); // Red for URG
        }
        if (flags.is_authentic) {
          colors.push([0, 188, 212]); // Cyan for AUTH
        }
        if (flags.is_german) {
          colors.push([255, 152, 0]); // Orange for GER
        }
        if (flags.is_enterprise) {
          colors.push([139, 69, 19]); // Brown for CORP
        }
        if (flags.is_corr) {
          colors.push([0, 206, 209]); // Turquoise for CORR
        }
        if (flags.is_rep) {
          colors.push([128, 0, 128]); // Purple for REP
        }
        if (this.isHourlyProject(project.project_details)) {
          colors.push([156, 39, 176]); // Purple for HR
        }

        // Calculate average RGB values
        const mixedColor = colors.reduce((acc, color) => {
          return [
            acc[0] + color[0],
            acc[1] + color[1],
            acc[2] + color[2]
          ];
        }, [0, 0, 0]).map(component => Math.round(component / colors.length));

        // Make border color darker by reducing each component by 30%
        const darkerColor = mixedColor.map(component => Math.round(component * 0.7));
        
        // Set border opacity based on flag count
        const borderOpacity = flagCount === 1 ? 0.4 : 0.8;  // Lower opacity for single flag

        return {
          border: `2px solid rgba(${darkerColor[0]}, ${darkerColor[1]}, ${darkerColor[2]}, ${borderOpacity})`
        };
      };
    },

    getProjectGlowStyle() {
      return (project) => {
        const ageInMinutes = this.getProjectAgeInMinutes(project);
        
        if (ageInMinutes > 60) {
          return {}; // No glow for projects older than 1 hour
        }
        
        // Calculate glow intensity (1.0 for brand new, 0.0 for 1 hour old)
        const glowIntensity = Math.max(0, 1 - (ageInMinutes / 60));
        
        // Create orange-red glow with varying intensity
        const glowColor = `255, ${Math.floor(165 * (1 - glowIntensity * 0.3))}, 0`; // Orange to red
        const shadowSize = Math.floor(8 + (glowIntensity * 12)); // 8px to 20px
        const shadowOpacity = 0.3 + (glowIntensity * 0.5); // 0.3 to 0.8
        
        return {
          boxShadow: `0 0 ${shadowSize}px rgba(${glowColor}, ${shadowOpacity}), 
                      0 0 ${shadowSize * 2}px rgba(${glowColor}, ${shadowOpacity * 0.5})`
        };
      };
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
    getProjectBackgroundColor(project) {
      const colors = [];
      const flags = project.project_details?.flags || {};
      const flagCount = Object.values(flags).filter(Boolean).length;
      
      // Debug log for new projects
      if (project.isNew) {
        console.log('[ColorMix] Calculating background for new project:', {
          projectId: project.project_details.id,
          title: project.project_details.title,
          flags: flags,
          flagCount: flagCount,
          isDarkTheme: this.isDarkTheme
        });
      }
      
      // Add RGB colors for each active tag
      if (flags.is_high_paying) {
        colors.push([255, 215, 0]); // Yellow for PAY
      }
      if (flags.is_urgent) {
        colors.push([244, 67, 54]); // Red for URG
      }
      if (flags.is_authentic) {
        colors.push([0, 188, 212]); // Cyan for AUTH
      }
      if (flags.is_german) {
        colors.push([255, 152, 0]); // Orange for GER
      }
      if (flags.is_enterprise) {
        colors.push([139, 69, 19]); // Brown for CORP
      }
      if (flags.is_corr) {
        colors.push([0, 206, 209]); // Turquoise for CORR
      }
      if (flags.is_rep) {
        colors.push([128, 0, 128]); // Purple for REP
      }
      if (this.isHourlyProject(project.project_details)) {
        colors.push([156, 39, 176]); // Purple for HR
      }

      // If no colors, return default background
      if (colors.length === 0) {
        return this.isDarkTheme ? '#1a1a1a' : 'white';
      }

      // Calculate average RGB values
      const mixedColor = colors.reduce((acc, color) => {
        return [
          acc[0] + color[0],
          acc[1] + color[1],
          acc[2] + color[2]
        ];
      }, [0, 0, 0]).map(component => Math.round(component / colors.length));

      // Set opacity based on flag count
      const baseOpacity = this.isDarkTheme ? 0.3 : 0.2;
      const opacity = flagCount === 1 ? baseOpacity * 0.5 : baseOpacity;  // 50% less opacity for single flag

      const finalColor = `rgba(${mixedColor[0]}, ${mixedColor[1]}, ${mixedColor[2]}, ${opacity})`;
      
      // Debug log for new projects
      if (project.isNew) {
        console.log('[ColorMix] Final color for new project:', {
          projectId: project.project_details.id,
          finalColor: finalColor,
          mixedColor: mixedColor,
          opacity: opacity,
          colors: colors
        });
      }

      return finalColor;
    },
    applyTheme() {
      document.body.classList.toggle('dark-theme', this.isDarkTheme);
      document.documentElement.classList.toggle('dark-theme', this.isDarkTheme);
    },
    toggleTheme() {
      this.isDarkTheme = !this.isDarkTheme;
      this.isSystemThemeMode = false; // User manually toggled, stop following system
      // Save user preference
      localStorage.setItem('theme', this.isDarkTheme ? 'dark' : 'light');
      this.applyTheme();
    },
    resetToSystemTheme() {
      // Reset to follow system theme
      this.isSystemThemeMode = true;
      this.isDarkTheme = this.systemThemeQuery.matches;
      localStorage.removeItem('theme'); // Remove saved preference
      this.applyTheme();
      console.log('[Theme] Reset to system theme mode:', this.isDarkTheme ? 'dark' : 'light');
    },
    handleSystemThemeChange(e) {
      // Always update if we're in system theme mode
      if (this.isSystemThemeMode) {
        console.log('[Theme] System theme changed to:', e.matches ? 'dark' : 'light');
        this.isDarkTheme = e.matches;
        this.applyTheme();
      } else {
        console.log('[Theme] System theme changed but user has manual preference, ignoring');
      }
    },
    initMasonry() {
      // Remove old masonry initialization
    },
    startPolling() {
      // Clear any existing interval
      if (this.projectPollingInterval) {
        clearInterval(this.projectPollingInterval);
      }
      
      // Poll every 20 seconds
      this.projectPollingInterval = setInterval(() => {
        this.loadProjects();
      }, 20000);
    },
    stopPolling() {
      if (this.projectPollingInterval) {
        clearInterval(this.projectPollingInterval);
        this.projectPollingInterval = null;
      }
    },
    
    startTimeTracking() {
      // Start timer to update elapsed times
      this.timeUpdateInterval = setInterval(() => {
        this.forceUpdate();
      }, 1000);
    },

    stopTimeTracking() {
      if (this.timeUpdateInterval) {
        clearInterval(this.timeUpdateInterval);
        this.timeUpdateInterval = null;
      }
    },

    stopFileWatching() {
      if (this.fileCheckInterval) {
        clearInterval(this.fileCheckInterval);
        this.fileCheckInterval = null;
      }
    },
    
    async checkForNewProjects() {
      // Checking for new projects - reduced logging

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

        // REMOVED: Auto-bidding logic moved to loadProjects() to prevent duplication

      } catch (error) {
        console.error('[ProjectList] Error checking for new projects:', error);
      }
    },
    async loadProjects() {
      try {
        // Starting bid count check - reduced logging
        
        // Add cache-busting parameters and headers to force fresh data
        const timestamp = Date.now();
        const cacheBuster = Math.random().toString(36).substring(7);
        const url = `${API_BASE_URL}/api/jobs?t=${timestamp}&cb=${cacheBuster}`;
        
                  // Fetching projects - reduced logging
        
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache'
          }
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch projects');
        }
        
        const newProjects = await response.json();
        console.log('[BidTracker] Fetched', newProjects.length, 'projects from JSON files');
        console.log('[BidTracker] Sample project structure:', newProjects[0] ? Object.keys(newProjects[0]) : 'No projects');
        console.log('[BidTracker] Response headers:', {
          'cache-control': response.headers.get('cache-control'),
          'last-modified': response.headers.get('last-modified'),
          'etag': response.headers.get('etag'),
          'expires': response.headers.get('expires')
        });
        
        // Log a sample of the fetched data to verify it's fresh
        if (newProjects.length > 0) {
          console.log('[BidTracker] Sample project data from API:', {
            id: newProjects[0].project_details.id,
            title: newProjects[0].project_details.title,
            bidCount: newProjects[0].project_details.bid_stats?.bid_count,
            timestamp: new Date().toISOString()
          });
        }
        
        // Log initial state
        console.log('[BidTracker] Current frontend state:', {
          totalProjects: this.projects.length,
          projectIds: this.projects.map(p => p.project_details.id),
          projectBids: this.projects.map(p => ({
            id: p.project_details.id,
            title: p.project_details.title,
            bidCount: p.project_details.bid_stats?.bid_count
          }))
        });
        
        // Store old projects for bid count comparison
        const oldProjects = [...this.projects];
        console.log('[BidTracker] Stored old projects for comparison:', oldProjects.length);
        
        // Check for new projects by comparing project IDs
        const oldProjectIds = new Set(oldProjects.map(p => p.project_details.id));
        const newlyAddedProjects = newProjects.filter(p => !oldProjectIds.has(p.project_details.id));
        
        if (newlyAddedProjects.length > 0) {
          console.log('[BidTracker] 🆕 New projects detected:', {
            count: newlyAddedProjects.length,
            projectIds: newlyAddedProjects.map(p => p.project_details.id),
            titles: newlyAddedProjects.map(p => p.project_details.title),
            timestamp: new Date().toISOString()
          });
          
          // Play notification sound for new projects if enabled (don't await to not block UI)
          if (this.isSoundEnabled && this.audioContext) {
            console.log('[BidTracker] Playing notification sound for new projects:', {
              timestamp: new Date().toISOString(),
              soundEnabled: this.isSoundEnabled,
              volume: this.volumeLevel,
              projectCount: newlyAddedProjects.length
            });
            
            // Get the highest score among new projects, default to 50 if no score
            const highestScore = Math.max(...newlyAddedProjects.map(project => project.ranking?.score || 50));
            
            // Play sound asynchronously without blocking
            this.playNotificationSound(highestScore).catch(error => {
              console.warn('[BidTracker] Notification sound failed:', error);
            });
          }
          
          // Mark new projects with fade-in animation
          newlyAddedProjects.forEach(project => {
            project.isNew = true;
            console.log('[BidTracker] Marked project as new:', {
              projectId: project.project_details.id,
              title: project.project_details.title,
              isNew: project.isNew
            });
            
            // Remove the fade-in effect after animation
            setTimeout(() => {
              project.isNew = false;
              console.log('[BidTracker] Removed new project status:', {
                projectId: project.project_details.id,
                isNew: project.isNew
              });
            }, 10000); // 10 seconds fade-in effect
          });
          
          // 🤖 SINGLE AUTO-BIDDING POINT: Check for automatic bidding on new projects
          if (this.automaticBiddingEnabled) {
            console.log(`[AutoBid] 🎯 SINGLE EXECUTION: Checking ${newlyAddedProjects.length} new projects for automatic bidding...`);
            
            // Add small delay before checking for automatic bidding to ensure UI has updated
            setTimeout(async () => {
              console.log(`[AutoBid] 🔄 Processing ${newlyAddedProjects.length} new projects for auto-bidding...`);
              
              for (const project of newlyAddedProjects) {
                const projectId = project.project_details.id;
                
                // 🚫 DUPLICATE PROTECTION: Ensure project isn't already being processed
                if (this.processingProjectIds.has(projectId)) {
                  console.log(`[AutoBid] ⚠️ SKIP: Project ${projectId} already being processed`);
                  continue;
                }
                
                if (this.processedProjectIds.has(projectId)) {
                  console.log(`[AutoBid] ⚠️ SKIP: Project ${projectId} already processed`);
                  continue;
                }
                
                if (this.shouldAutomaticallyBid(project)) {
                  console.log(`[AutoBid] ✅ New project ${projectId} qualifies for automatic bidding`);
                  await this.performAutomaticBid(project);
                  
                  // Add delay between bids to avoid overwhelming the API
                  await new Promise(resolve => setTimeout(resolve, 3000));
                } else {
                  console.log(`[AutoBid] ❌ Project ${projectId} does not qualify for automatic bidding`);
                }
              }
              
              console.log(`[AutoBid] ✅ Completed processing ${newlyAddedProjects.length} new projects`);
            }, 1000); // 1 second delay
          }
        }
        
        // Check for bid count changes before updating
        newProjects.forEach(newProject => {
          const existingProject = oldProjects.find(
            p => p.project_details.id === newProject.project_details.id
          );
          
          if (existingProject) {
            const oldBidCount = existingProject.project_details.bid_stats?.bid_count;
            const newBidCount = newProject.project_details.bid_stats?.bid_count;
            
            // Log detailed bid count comparison
            console.log(`[BidTracker] Comparing bid counts for project ${newProject.project_details.id}:`, {
              title: newProject.project_details.title,
              oldBidCount: oldBidCount,
              newBidCount: newBidCount,
              hasChanged: oldBidCount !== newBidCount,
              difference: newBidCount - oldBidCount,
              timestamp: new Date().toISOString()
            });
            
            if (oldBidCount !== newBidCount) {
              console.log(`[BidTracker] 🎯 Bid count changed - Starting animation sequence:`, {
                projectId: newProject.project_details.id,
                title: newProject.project_details.title,
                oldCount: oldBidCount,
                newCount: newBidCount,
                difference: newBidCount - oldBidCount,
                timestamp: new Date().toISOString()
              });
              
              // Show bid count overlay on this specific project
              newProject.newBidCount = newBidCount; // Show the new total bid count
              newProject.showBidOverlay = true;
              console.log('[BidTracker] Showing bid overlay:', {
                timestamp: new Date().toISOString(),
                projectId: newProject.project_details.id,
                bidDifference: newProject.newBidCount,
                overlayVisible: newProject.showBidOverlay
              });
              
              
              // Hide overlay after animation
              setTimeout(() => {
                newProject.showBidOverlay = false;
                console.log('[BidTracker] Animation sequence completed:', {
                  timestamp: new Date().toISOString(),
                  projectId: newProject.project_details.id,
                  duration: '2000ms',
                  overlayVisible: newProject.showBidOverlay
                });
              }, 2000);
              
              // Mark project for animation
              newProject.bidCountChanged = true;
              console.log('[BidTracker] Bid count animation triggered:', {
                timestamp: new Date().toISOString(),
                projectId: newProject.project_details.id,
                animationState: newProject.bidCountChanged
              });
              
              setTimeout(() => {
                newProject.bidCountChanged = false;
                console.log('[BidTracker] Bid count animation reset:', {
                  timestamp: new Date().toISOString(),
                  projectId: newProject.project_details.id,
                  animationState: newProject.bidCountChanged
                });
              }, 500);
            }
          }
        });
        
        // Preserve UI state from old projects
        const preservedStates = new Map();
        oldProjects.forEach(oldProject => {
          if (oldProject.buttonStates || oldProject.showDescription || oldProject.isNew) {
            preservedStates.set(oldProject.project_details.id, {
              buttonStates: oldProject.buttonStates,
              showDescription: oldProject.showDescription,
              isNew: oldProject.isNew
            });
          }
        });
        
        // Replace projects array with fresh data and preserved UI state
        console.log('[BidTracker] About to update this.projects with', newProjects.length, 'new projects');
        console.log('[BidTracker] Current this.projects.length before update:', this.projects.length);
        
        this.projects = newProjects.map(newProject => {
          const preserved = preservedStates.get(newProject.project_details.id);
          
          // Load button states from project data (including persistent error states)
          this.loadButtonStatesFromProject(newProject);
          
          if (preserved) {
            return {
              ...newProject,
              ...preserved
            };
          }
          return newProject;
        });
        
        console.log('[BidTracker] Projects array updated with', this.projects.length, 'projects');
        console.log('[BidTracker] First project after update:', this.projects[0] ? this.projects[0].project_details?.title : 'No projects');
        
        // Force Vue reactivity update to ensure colors are applied
        this.$forceUpdate();
        
        // Additional trigger for color recalculation
        this.$nextTick(() => {
          console.log('[BidTracker] ✅ Vue reactivity update completed, colors should be visible');
        });
        
        // Log final state
        console.log('[BidTracker] Project load check completed:', {
          totalProjects: this.projects.length,
          projectIds: this.projects.map(p => p.project_details.id),
          timestamp: new Date().toISOString(),
          projectBids: this.projects.map(p => ({
            id: p.project_details.id,
            title: p.project_details.title,
            bidCount: p.project_details.bid_stats?.bid_count
          }))
        });
        
        // Ensure loading is set to false so projects are displayed
        this.loading = false;
        console.log('[BidTracker] Loading set to false, projects should now be visible');
      } catch (error) {
        console.error('[BidTracker] Error loading projects:', error);
        this.error = error.message;
        this.loading = false;
      }
    },
    formatDate(timestamp) {
      return new Date(timestamp).toLocaleString();
    },
    
    formatLogTimestamp(log) {
      // Handle different timestamp formats from logs
      if (!log) return 'N/A';
      
      // PRIORITY 1: Use fullTimestamp (ISO string) like in auto_bidding.log
      if (log.fullTimestamp) {
        try {
          const date = new Date(log.fullTimestamp);
          if (!isNaN(date.getTime())) {
            // Format like auto_bidding.log: just show time portion nicely
            return date.toLocaleString('de-DE', {
              year: '2-digit',
              month: '2-digit', 
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            });
          }
        } catch (error) {
          // Try to show the raw ISO string if parsing fails
          if (typeof log.fullTimestamp === 'string') {
            return log.fullTimestamp.replace('T', ' ').replace('Z', '').substring(0, 19);
          }
        }
      }
      
      // PRIORITY 2: Use the already formatted timestamp if it exists and looks like time
      if (log.timestamp && typeof log.timestamp === 'string' && /^\d{1,2}:\d{2}:\d{2}/.test(log.timestamp)) {
        return log.timestamp;
      }
      
      // PRIORITY 3: Try to parse timestamp as date
      if (log.timestamp) {
        try {
          const date = new Date(log.timestamp);
          if (!isNaN(date.getTime())) {
            return date.toLocaleString('de-DE', {
              year: '2-digit',
              month: '2-digit', 
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            });
          }
        } catch (error) {
          // Silent failure
        }
      }
      
      // PRIORITY 4: Return the raw timestamp if all else fails
      if (log.timestamp) {
        return String(log.timestamp);
      }
      
      // Final fallback
      return 'No timestamp';
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
      
      // Format the time parts with zero-padding for seconds
      const parts = [];
      if (days > 0) parts.push(`${days}d`);
      if (hours > 0 || days > 0) parts.push(`${hours.toString().padStart(2, '0')}h`);
      if (minutes > 0 || hours > 0 || days > 0) parts.push(`${minutes.toString().padStart(2, '0')}m`);
      if (days === 0) parts.push(`${seconds.toString().padStart(2, '0')}s`); // Always show seconds with 2 digits
      
      return parts.join(' ');
    },
    
    forceUpdate() {
      // This will trigger a reactivity update for all components
      this.$forceUpdate();
    },
    
    showNotification(message, type = 'success') {
      // Create in-browser notification (existing functionality)
      const notification = document.createElement('div')
      notification.className = `notification ${type}`
      notification.textContent = message
      document.body.appendChild(notification)
      
      // Remove notification after 3 seconds
      setTimeout(() => {
        notification.remove()
      }, 3000)
      
      // Send push notification to mobile devices (new functionality)
      this.sendPushNotification(message, type);
    },
    
    async sendPushNotification(message, type = 'success') {
      // Check if browser supports notifications
      if (!('Notification' in window)) {
        console.log('[PushNotification] Browser does not support notifications');
        return;
      }
      
      // Register service worker if not already registered
      await this.registerServiceWorker();
      
      // Check if we have permission
      if (Notification.permission === 'granted') {
        try {
          // Determine icon and title based on type
          let icon = '/favicon.ico';
          let title = 'Freelancer Bidder';
          
          switch (type) {
            case 'success':
              title = '✅ Auto-Bid Success';
              icon = '/favicon.ico';
              break;
            case 'error':
              title = '❌ Auto-Bid Error';
              icon = '/favicon.ico';
              break;
            case 'warning':
              title = '⚠️ Auto-Bid Warning';
              icon = '/favicon.ico';
              break;
            default:
              title = '📋 Auto-Bid Info';
              break;
          }
          
          // Try to use service worker registration for better mobile support
          if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            try {
              const registration = await navigator.serviceWorker.ready;
              await registration.showNotification(title, {
                body: message,
                icon: icon,
                tag: `auto-bid-${type}-${Date.now()}`,
                badge: icon,
                requireInteraction: type === 'error',
                silent: false,
                vibrate: type === 'success' ? [200, 100, 200] : type === 'error' ? [300, 100, 300, 100, 300] : [100],
                data: {
                  type: type,
                  timestamp: new Date().toISOString(),
                  url: window.location.href
                }
              });
              console.log(`[PushNotification] ✅ Service Worker notification sent: ${title} - ${message}`);
              return;
            } catch (swError) {
              console.warn('[PushNotification] Service Worker notification failed, falling back to regular notification:', swError);
            }
          }
          
          // Fallback to regular notification
          const pushNotification = new Notification(title, {
            body: message,
            icon: icon,
            tag: `auto-bid-${type}-${Date.now()}`,
            badge: icon,
            requireInteraction: type === 'error',
            silent: false,
            vibrate: type === 'success' ? [200, 100, 200] : type === 'error' ? [300, 100, 300, 100, 300] : [100],
            data: {
              type: type,
              timestamp: new Date().toISOString(),
              url: window.location.href
            }
          });
          
          // Handle notification click (open app)
          pushNotification.onclick = function(event) {
            event.preventDefault();
            window.focus();
            pushNotification.close();
          };
          
          // Auto-close success notifications after 5 seconds
          if (type === 'success' || type === 'info') {
            setTimeout(() => {
              pushNotification.close();
            }, 5000);
          }
          
          console.log(`[PushNotification] ✅ Regular notification sent: ${title} - ${message}`);
          
        } catch (error) {
          console.warn('[PushNotification] Failed to send push notification:', error);
        }
      } else if (Notification.permission === 'default') {
        // Request permission if not yet granted
        console.log('[PushNotification] Requesting notification permission...');
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
          // Retry sending notification
          this.sendPushNotification(message, type);
        }
      } else {
        console.log('[PushNotification] Notification permission denied');
      }
    },

    async registerServiceWorker() {
      if ('serviceWorker' in navigator) {
        try {
          // Check if already registered
          const registrations = await navigator.serviceWorker.getRegistrations();
          const existingRegistration = registrations.find(reg => 
            reg.scope.includes(window.location.origin)
          );
          
          if (existingRegistration) {
            console.log('[ServiceWorker] Already registered:', existingRegistration.scope);
            return existingRegistration;
          }
          
          // Register new service worker
          const registration = await navigator.serviceWorker.register('/sw.js', {
            scope: '/'
          });
          
          console.log('[ServiceWorker] Registration successful:', registration.scope);
          
          // Wait for service worker to be ready
          await navigator.serviceWorker.ready;
          console.log('[ServiceWorker] Service worker is ready');
          
          return registration;
        } catch (error) {
          console.warn('[ServiceWorker] Registration failed:', error);
          return null;
        }
      }
      return null;
    },
    
    async handleProjectClick(project) {
      console.log('[BidTeaser] Project clicked:', project.project_details.id);

      // ✅ CRITICAL CHECK: Never regenerate if bid texts already exist
      if (project.ranking?.bid_teaser?.first_paragraph) {
        console.log('[BidTeaser] ✅ BID TEXTS ALREADY EXIST - ABSOLUTELY NO REGENERATION');
        console.log('[BidTeaser] Existing bid teaser:', {
          first_paragraph: project.ranking.bid_teaser.first_paragraph ? 'EXISTS' : 'MISSING',
          second_paragraph: project.ranking.bid_teaser.second_paragraph ? 'EXISTS' : 'MISSING', 
          third_paragraph: project.ranking.bid_teaser.third_paragraph ? 'EXISTS' : 'MISSING',
          question: project.ranking.bid_teaser.question ? 'EXISTS' : 'MISSING'
        });
        this.showNotification('Bid texts already exist - no regeneration needed', 'info');
        return;
      }

      // ✅ PREVENT DUPLICATE GENERATION: Check if already generating
      if (project.buttonStates?.generating) {
        console.log('[BidTeaser] ⚠️ ALREADY GENERATING - Preventing duplicate generation for project:', project.project_details.id);
        this.showNotification('Bid generation already in progress - please wait', 'warning');
        return;
      }

      // ✅ PREVENT DUPLICATE GENERATION: Check if generation failed recently
      if (project.buttonStates?.generationFailed && project.buttonStates?.lastGenerationAttempt) {
        const timeSinceLastAttempt = Date.now() - new Date(project.buttonStates.lastGenerationAttempt).getTime();
        const cooldownMinutes = 2; // 2 minutes cooldown
        if (timeSinceLastAttempt < cooldownMinutes * 60 * 1000) {
          const remainingTime = Math.ceil((cooldownMinutes * 60 * 1000 - timeSinceLastAttempt) / 1000);
          this.showNotification(`Generation failed recently. Please wait ${remainingTime}s before retrying`, 'warning');
          return;
        }
      }

      // Initialize buttonStates if not exists
      if (!project.buttonStates) {
        project.buttonStates = {};
      }

      // Set generating flag to prevent duplicates
      project.buttonStates.generating = true;
      project.buttonStates.lastGenerationAttempt = new Date().toISOString();
      project.buttonStates.generateClicked = true;
      
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

        // Generate bid text (final bid will be submitted after generation)
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

        // Clear generating flag on success
        project.buttonStates.generating = false;
        project.buttonStates.generationFailed = false;

        // Show success notification
        this.showNotification('Bid text generated successfully', 'success');

      } catch (error) {
        console.error('[BidTeaser] Error:', error);
        
        // Mark generation as failed with error details
        project.buttonStates.generating = false;
        project.buttonStates.generationFailed = true;
        project.buttonStates.generationError = error.message;
        project.buttonStates.errorTimestamp = new Date().toISOString();
        
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
    async handleSendQuestionClick(project) {
      try {
        if (!project.ranking?.bid_teaser?.question) {
          this.showNotification('No question available for this project', 'error');
          return;
        }

        // Prevent multiple simultaneous requests
        if (project.buttonStates?.sendingQuestion || project.buttonStates?.questionSent) {
          return;
        }

        // Set loading state
        project.buttonStates = project.buttonStates || {};
        project.buttonStates.sendingQuestion = true;
        await this.updateButtonState(project, 'sendingQuestion');

        this.showNotification('Sending question to project...', 'info');

        // Call the backend API to send question via Selenium
        const response = await this.sendQuestionToProject(project.project_details.id);

        if (response.success) {
          project.buttonStates.questionSent = true;
          project.buttonStates.sendingQuestion = false;
          await this.updateButtonState(project, 'questionSent');
          this.showNotification('Question successfully sent to project!', 'success');
        } else {
          throw new Error(response.error || 'Failed to send question');
        }

      } catch (error) {
        console.error('Error sending question:', error);
        
        // Reset states on error
        if (project.buttonStates) {
          project.buttonStates.sendingQuestion = false;
          delete project.buttonStates.questionSent;
        }
        
        this.showNotification(error.message || 'Failed to send question to project', 'error');
      }
    },
    async sendQuestionToProject(projectId) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/post-question/${projectId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();

      } catch (error) {
        console.error('Error calling send question API:', error);
        throw error;
      }
    },
    getQuestionButtonTitle(project) {
      if (!project.ranking?.bid_teaser?.question) {
        return 'No question available';
      }
      
      if (project.buttonStates?.sendingQuestion) {
        return 'Sending question...';
      }
      
      if (project.buttonStates?.questionSent) {
        return 'Question already sent';
      }
      
      return 'Send question to project';
    },
    toggleDescription(project) {
      project.showDescription = !project.showDescription;
      
      // Mark the expand button as clicked when expanding
      if (project.showDescription) {
        project.buttonStates.expandClicked = true;
      }
      
      this.$nextTick(() => {
        // Use document.querySelector instead of this.$el.querySelector
        const card = document.querySelector(`[data-project-url="${project.project_url}"]`);
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
    getAvgBidValue(bidStats) {
      if (!bidStats) return null;
      
      // Priority order: bid_avg (most reliable) -> bid_avg_usd -> bid_avg_calculated -> bid_avg_original
      if (bidStats.bid_avg && bidStats.bid_avg > 0) {
        return bidStats.bid_avg;
      }
      
      if (bidStats.bid_avg_usd && bidStats.bid_avg_usd > 0) {
        return bidStats.bid_avg_usd;
      }
      
      if (bidStats.bid_avg_calculated && bidStats.bid_avg_calculated > 0) {
        return bidStats.bid_avg_calculated;
      }
      
      if (bidStats.bid_avg_original && bidStats.bid_avg_original > 0) {
        return bidStats.bid_avg_original;
      }
      
      return null;
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
    async toggleSound() {
      console.log('[Audio Debug] toggleSound called, current state:', this.isSoundEnabled);
      this.isSoundEnabled = !this.isSoundEnabled;
      localStorage.setItem('soundEnabled', this.isSoundEnabled);
      console.log('[Audio Debug] New sound state:', this.isSoundEnabled);
      
      if (this.isSoundEnabled) {
        console.log('[Audio Debug] Sound enabled, initializing audio...');
        // Initialize audio context if needed
        await this.initializeAudio();
        // Restore previous volume
        if (this.gainNode) {
          this.gainNode.gain.value = this.volumeLevel / 100;
          console.log('[Audio Debug] Volume restored to:', this.volumeLevel);
        } else {
          console.error('[Audio Debug] No gain node available after initialization!');
        }
      } else {
        console.log('[Audio Debug] Sound disabled, muting...');
        // Mute audio without changing volume level
        if (this.gainNode) {
          this.gainNode.gain.value = 0;
          console.log('[Audio Debug] Audio muted');
        } else {
          console.warn('[Audio Debug] No gain node to mute');
        }
      }
    },
    checkBrowserAudioSupport() {
      console.log('[Audio Support] Checking browser audio support...');
      
      const support = {
        AudioContext: !!window.AudioContext,
        webkitAudioContext: !!window.webkitAudioContext,
        HTMLAudio: !!window.Audio,
        userAgent: navigator.userAgent,
        platform: navigator.platform
      };
      
      console.log('[Audio Support] Browser support:', support);
      
      if (!support.AudioContext && !support.webkitAudioContext) {
        console.error('[Audio Support] No AudioContext support detected!');
        alert('Warnung: Ihr Browser unterstützt möglicherweise keine Audio-Benachrichtigungen. Bitte verwenden Sie einen modernen Browser wie Chrome, Firefox oder Safari.');
        return false;
      }
      
      if (!support.HTMLAudio) {
        console.warn('[Audio Support] No HTML5 Audio support detected!');
      }
      
      return true;
    },

    async ensureUserInteraction() {
      console.log('[Audio Interaction] Ensuring user interaction...');
      
      return new Promise((resolve) => {
        // Check if we already have user interaction
        if (document.visibilityState === 'visible') {
          // Try to create and trigger a user interaction event
          const interactionEvent = new MouseEvent('click', {
            view: window,
            bubbles: true,
            cancelable: true
          });
          
          // Dispatch the event on the document
          document.dispatchEvent(interactionEvent);
          
          console.log('[Audio Interaction] User interaction simulated');
          resolve();
        } else {
          console.log('[Audio Interaction] Document not visible, skipping interaction');
          resolve();
        }
      });
    },

    async initializeAudio() {
      console.log('[Audio Debug] initializeAudio called');
      
      // Check browser support first
      if (!this.checkBrowserAudioSupport()) {
        console.error('[Audio Debug] Browser does not support audio');
        return;
      }
      
      console.log('[Audio Debug] Browser support check:', {
        AudioContext: !!window.AudioContext,
        webkitAudioContext: !!window.webkitAudioContext,
        userAgent: navigator.userAgent
      });

      // Clean up any existing audio context first
      if (this.audioContext && this.audioContext.state !== 'closed') {
        console.log('[Audio Debug] Cleaning up existing context, state:', this.audioContext.state);
        try {
          await this.audioContext.close();
          console.log('[Audio Debug] Existing context closed');
        } catch (e) {
          console.warn('[Audio Debug] Error closing existing context:', e);
        }
      }
      
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) {
          throw new Error('AudioContext not supported in this browser');
        }
        
        console.log('[Audio Debug] Creating new AudioContext...');
        this.audioContext = new AudioContext();
        console.log('[Audio Debug] AudioContext created, initial state:', this.audioContext.state);
        console.log('[Audio Debug] AudioContext details:', {
          sampleRate: this.audioContext.sampleRate,
          currentTime: this.audioContext.currentTime,
          destination: !!this.audioContext.destination
        });
        
        // Create main gain node with saved volume level
        console.log('[Audio Debug] Creating gain node...');
        this.gainNode = this.audioContext.createGain();
        const gainValue = this.isSoundEnabled ? (this.volumeLevel / 100) : 0;
        this.gainNode.gain.value = gainValue;
        this.gainNode.connect(this.audioContext.destination);
        
        console.log('[Audio Debug] Gain node created and connected, value:', gainValue);
        console.log('[Audio Debug] Volume level:', this.volumeLevel, 'Sound enabled:', this.isSoundEnabled);
        
        // Resume audio context if it's suspended (needed for some browsers)
        if (this.audioContext.state === 'suspended') {
          console.log('[Audio Debug] AudioContext is suspended, attempting to resume...');
          await this.audioContext.resume();
          console.log('[Audio Debug] AudioContext resumed, new state:', this.audioContext.state);
        }

        // Add event listeners for audio context state changes
        this.audioContext.addEventListener('statechange', () => {
          console.log('[Audio Debug] Audio context state changed to:', this.audioContext.state);
          if (this.audioContext.state === 'suspended') {
            console.warn('[Audio Debug] Audio context was suspended, attempting to resume...');
            this.audioContext.resume().catch(error => {
              console.error('[Audio Debug] Failed to resume suspended context:', error);
            });
          }
        });

        console.log('[Audio Debug] Audio initialization completed successfully');
        console.log('[Audio Debug] Final state:', {
          contextState: this.audioContext.state,
          gainNodeExists: !!this.gainNode,
          gainValue: this.gainNode ? this.gainNode.gain.value : 'N/A'
        });

      } catch (error) {
        console.error('[Audio Debug] Failed to initialize audio context:', error);
        console.error('[Audio Debug] Error details:', {
          name: error.name,
          message: error.message,
          stack: error.stack
        });
      }
    },
    cleanupAudio() {
      console.log('[Audio] Cleaning up audio resources');
      
      // Stop and clean up all oscillators
      if (this.oscillators && this.oscillators.length > 0) {
        this.oscillators.forEach(osc => {
          try {
            if (osc.stop) osc.stop();
            if (osc.disconnect) osc.disconnect();
          } catch (e) {
            // Ignore errors during cleanup
          }
        });
        this.oscillators = [];
      }
      
      // Clean up gain node
      if (this.gainNode) {
        try {
          this.gainNode.disconnect();
        } catch (e) {
          // Ignore errors during cleanup
        }
        this.gainNode = null;
      }
      
      // Clean up audio context
      if (this.audioContext) {
        try {
          this.audioContext.close();
        } catch (e) {
          // Ignore errors during cleanup
        }
        this.audioContext = null;
      }
    },
    async testAudioSystem() {
      console.log('[Audio Test] Testing audio system...');
      console.log('[Audio Test] Browser info:', {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        audioContext: !!window.AudioContext,
        webkitAudioContext: !!window.webkitAudioContext
      });
      
      try {
        // Test if we can create a basic oscillator and play it briefly
        if (!this.audioContext || this.audioContext.state !== 'running' || !this.gainNode) {
          console.log('[Audio Test] Audio system not ready:', {
            contextExists: !!this.audioContext,
            contextState: this.audioContext ? this.audioContext.state : 'N/A',
            gainNodeExists: !!this.gainNode
          });
          return false;
        }
        
        // Create a very brief test oscillator
        const testOsc = this.audioContext.createOscillator();
        const testGain = this.audioContext.createGain();
        
        testOsc.type = 'sine';
        testOsc.frequency.setValueAtTime(440, this.audioContext.currentTime);
        testGain.gain.setValueAtTime(0.001, this.audioContext.currentTime); // Very quiet
        
        testOsc.connect(testGain);
        testGain.connect(this.gainNode);
        
        testOsc.start();
        testOsc.stop(this.audioContext.currentTime + 0.01); // 10ms test
        
        console.log('[Audio Test] Audio system test passed');
        return true;
      } catch (error) {
        console.error('[Audio Test] Audio system test failed:', error);
        return false;
      }
    },

    async tryAlternativeSound() {
      console.log('[Audio Alternative] Trying Safari-compatible methods...');
      
      // Method 1: Try HTML5 Audio with a proper WAV file first (Safari prefers this)
      try {
        console.log('[Audio Alternative] Trying HTML5 Audio method...');
        
        // Create a longer, more audible beep sound
        const sampleRate = 44100;
        const duration = 0.5; // 500ms
        const frequency = 800; // 800Hz
        const volume = this.volumeLevel / 100;
        
        // Generate WAV data
        const samples = Math.floor(sampleRate * duration);
        const buffer = new ArrayBuffer(44 + samples * 2);
        const view = new DataView(buffer);
        
        // WAV header
        const writeString = (offset, string) => {
          for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
          }
        };
        
        writeString(0, 'RIFF');
        view.setUint32(4, 36 + samples * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, samples * 2, true);
        
        // Generate sine wave
        for (let i = 0; i < samples; i++) {
          const sample = Math.sin(2 * Math.PI * frequency * i / sampleRate) * volume * 0x7FFF;
          view.setInt16(44 + i * 2, sample, true);
        }
        
        // Create blob and audio element
        const blob = new Blob([buffer], { type: 'audio/wav' });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        
        // Set volume and play
        audio.volume = volume;
        
        console.log('[Audio Alternative] Playing HTML5 Audio...');
        await audio.play();
        
        // Clean up
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        
        console.log('[Audio Alternative] HTML5 Audio method succeeded!');
        return true;
        
      } catch (htmlError) {
        console.error('[Audio Alternative] HTML5 Audio method failed:', htmlError);
      }
      
      // Method 2: Try Web Audio API with immediate user interaction
      try {
        console.log('[Audio Alternative] Trying Web Audio API with user interaction...');
        
        // Create a fresh AudioContext
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Ensure context is running
        if (audioContext.state === 'suspended') {
          await audioContext.resume();
        }
        
        console.log('[Audio Alternative] AudioContext state:', audioContext.state);
        
        if (audioContext.state !== 'running') {
          throw new Error('AudioContext not running');
        }
        
        // Create oscillator with higher volume
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        oscillator.type = 'sine';
        
        // Make it louder and longer
        const volume = (this.volumeLevel / 100) * 0.5; // 50% of user volume
        gainNode.gain.setValueAtTime(0, audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(volume, audioContext.currentTime + 0.05);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.8);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.8);
        
        console.log('[Audio Alternative] Web Audio API method executed');
        
        // Clean up after sound finishes
        setTimeout(() => {
          try {
            audioContext.close();
          } catch (e) {
            // Ignore cleanup errors
          }
        }, 1000);
        
        return true;
        
      } catch (webAudioError) {
        console.error('[Audio Alternative] Web Audio API method failed:', webAudioError);
      }
      
      // Method 3: Simple notification sound
      try {
        console.log('[Audio Alternative] Trying system notification...');
        
        // Try to use the system notification sound (if available)
        if ('Notification' in window) {
          const notification = new Notification('Sound Test', {
            body: 'Audio system test',
            silent: false,
            tag: 'audio-test'
          });
          
          // Close notification immediately
          setTimeout(() => notification.close(), 100);
          
          console.log('[Audio Alternative] System notification method executed');
          return true;
        }
        
      } catch (notificationError) {
        console.error('[Audio Alternative] System notification method failed:', notificationError);
      }
      
      console.error('[Audio Alternative] All alternative methods failed');
      return false;
    },

    async forceAudioRestart() {
      console.log('[Audio Recovery] Force restarting audio system...');
      
      // Set testing flag to indicate system restart
      this.audioSystemTesting = true;
      
      try {
        // Complete cleanup
        this.cleanupAudio();
        
        // Wait a moment for cleanup to complete
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Force user interaction if needed (for browsers that require it)
        await this.ensureUserInteraction();
        
        // Reinitialize audio
        await this.initializeAudio();
        
        // Test the system
        const testResult = await this.testAudioSystem();
        console.log('[Audio Recovery] Audio restart result:', testResult);
        
        return testResult;
      } catch (error) {
        console.error('[Audio Recovery] Failed to restart audio system:', error);
        return false;
      } finally {
        // Always clear testing flag
        this.audioSystemTesting = false;
      }
    },

    async ensureAudioContext() {
      console.log('[Audio Debug] ensureAudioContext called');
      console.log('[Audio Debug] Current audio context state:', {
        exists: !!this.audioContext,
        state: this.audioContext ? this.audioContext.state : 'N/A',
        gainNodeExists: !!this.gainNode
      });

      // First, test if the current audio system is working
      if (this.audioContext && this.gainNode) {
        const testPassed = await this.testAudioSystem();
        if (testPassed) {
          console.log('[Audio Debug] Audio system test passed, using existing context');
          return true;
        }
        console.log('[Audio Debug] Audio system test failed, will restart');
      }

      // Check if audio context exists and is in a good state
      if (!this.audioContext || this.audioContext.state === 'closed') {
        console.log('[Audio Debug] Audio context missing or closed, reinitializing...');
        await this.initializeAudio();
      } else if (this.audioContext.state === 'suspended') {
        console.log('[Audio Debug] Audio context suspended, attempting to resume...');
        try {
          await this.audioContext.resume();
          console.log('[Audio Debug] Audio context resumed, state:', this.audioContext.state);
        } catch (error) {
          console.error('[Audio Debug] Failed to resume audio context:', error);
          // If resume fails, try force restart
          console.log('[Audio Debug] Resume failed, force restarting...');
          const restartSuccess = await this.forceAudioRestart();
          if (!restartSuccess) {
            console.error('[Audio Debug] Force restart also failed');
            return false;
          }
        }
      }
      
      // Verify gain node exists
      if (!this.gainNode && this.audioContext) {
        console.log('[Audio Debug] Gain node missing, recreating...');
        this.gainNode = this.audioContext.createGain();
        this.gainNode.gain.value = this.isSoundEnabled ? (this.volumeLevel / 100) : 0;
        this.gainNode.connect(this.audioContext.destination);
        console.log('[Audio Debug] Gain node recreated');
      }
      
      // Final test
      const finalTest = await this.testAudioSystem();
      console.log('[Audio Debug] Final audio system test:', finalTest);
      
      if (!finalTest) {
        console.log('[Audio Debug] Final test failed, attempting force restart...');
        const restartSuccess = await this.forceAudioRestart();
        return restartSuccess;
      }
      
      const isReady = this.audioContext && this.audioContext.state === 'running' && this.gainNode;
      console.log('[Audio Debug] Audio context ready:', isReady);
      console.log('[Audio Debug] Final check:', {
        contextExists: !!this.audioContext,
        contextState: this.audioContext ? this.audioContext.state : 'N/A',
        gainNodeExists: !!this.gainNode,
        soundEnabled: this.isSoundEnabled
      });
      
      return isReady;
    },
    async playTestSound() {
      console.log('[Audio Debug] ===== PLAY TEST SOUND CALLED =====');
      console.log('[Audio Debug] Initial state check:', {
        soundEnabled: this.isSoundEnabled,
        volumeLevel: this.volumeLevel,
        contextExists: !!this.audioContext,
        gainNodeExists: !!this.gainNode
      });

      // Set testing flag to show spinner
      this.audioSystemTesting = true;

      // For Safari: Try the alternative method first since it's more reliable
      if (navigator.userAgent.includes('Safari') && !navigator.userAgent.includes('Chrome')) {
        console.log('[Audio Debug] Safari detected, trying alternative method first...');
        const alternativeSuccess = await this.tryAlternativeSound();
        if (alternativeSuccess) {
          console.log('[Audio Debug] Safari alternative method succeeded!');
          this.audioSystemTesting = false;
          return;
        }
        console.log('[Audio Debug] Safari alternative method failed, trying standard method...');
      }

      // Retry mechanism for sound playback
      let retryCount = 0;
      const maxRetries = 3;

      while (retryCount < maxRetries) {
        try {
          console.log(`[Audio Debug] Attempt ${retryCount + 1}/${maxRetries} - Ensuring audio context...`);
          const contextReady = await this.ensureAudioContext();
          
          if (!contextReady) {
            throw new Error('Audio context not available or not running');
          }
          
          console.log('[Audio Debug] Audio context ready, state:', this.audioContext.state);
          console.log('[Audio Debug] Gain node value:', this.gainNode.gain.value);
          
          // Additional verification before creating oscillators
          if (!this.audioContext || this.audioContext.state !== 'running') {
            throw new Error('Audio context not in running state');
          }
          
          if (!this.gainNode) {
            throw new Error('Gain node not available');
          }
          
          // Create oscillators for a more complex sound
          console.log('[Audio Debug] Creating oscillators...');
          const osc1 = this.audioContext.createOscillator();
          const osc2 = this.audioContext.createOscillator();
          const oscGain = this.audioContext.createGain();
          
          console.log('[Audio Debug] Oscillators created');
          
          // Configure oscillators with lower frequencies
          osc1.type = 'sine';
          osc1.frequency.setValueAtTime(440, this.audioContext.currentTime); // A4 note
          
          osc2.type = 'sine';
          osc2.frequency.setValueAtTime(554.37, this.audioContext.currentTime); // C#5 note
          
          console.log('[Audio Debug] Oscillator frequencies set:', {
            osc1: 440,
            osc2: 554.37,
            currentTime: this.audioContext.currentTime
          });
          
          // Configure envelope with longer duration
          oscGain.gain.setValueAtTime(0, this.audioContext.currentTime);
          oscGain.gain.linearRampToValueAtTime(0.5, this.audioContext.currentTime + 0.1);
          oscGain.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 2.0);
          
          console.log('[Audio Debug] Envelope configured');
          
          // Connect nodes
          console.log('[Audio Debug] Connecting audio nodes...');
          osc1.connect(oscGain);
          osc2.connect(oscGain);
          oscGain.connect(this.gainNode);
          
          console.log('[Audio Debug] Audio nodes connected');
          
          // Add error handlers
          osc1.addEventListener('ended', () => {
            console.log('[Audio Debug] Oscillator 1 ended');
          });
          osc2.addEventListener('ended', () => {
            console.log('[Audio Debug] Oscillator 2 ended');
          });
          
          // Start sound
          console.log('[Audio Debug] Starting oscillators...');
          osc1.start();
          osc2.start();
          
          console.log('[Audio Debug] ===== SOUND SHOULD BE PLAYING NOW =====');
          console.log('[Audio Debug] Audio graph:', {
            osc1Connected: true,
            osc2Connected: true,
            oscGainConnected: true,
            gainNodeConnected: true,
            destinationConnected: true
          });
          
          // Stop sound after envelope completes and clean up immediately
          setTimeout(() => {
            console.log('[Audio Debug] Stopping and cleaning up oscillators...');
            try {
              osc1.stop();
              osc2.stop();
              osc1.disconnect();
              osc2.disconnect();
              oscGain.disconnect();
              console.log('[Audio Debug] Sound stopped and cleaned up successfully');
            } catch (error) {
              console.error('[Audio Debug] Error cleaning up oscillators:', error);
            }
          }, 2100); // Slightly longer than envelope to ensure completion
          
          console.log('[Audio Debug] Test sound setup completed successfully');
          
          // If we reach here, the sound played successfully
          this.audioSystemTesting = false;
          return;
          
        } catch (error) {
          console.error(`[Audio Debug] ===== ERROR ON ATTEMPT ${retryCount + 1} =====`);
          console.error('[Audio Debug] Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
          });
          
          retryCount++;
          
          if (retryCount < maxRetries) {
            console.log(`[Audio Debug] Retrying... (${retryCount}/${maxRetries})`);
            // Force restart audio system before retry
            await this.forceAudioRestart();
            // Wait a bit before retry
            await new Promise(resolve => setTimeout(resolve, 200));
          } else {
            console.error('[Audio Debug] ===== ALL RETRY ATTEMPTS FAILED =====');
            console.log('[Audio Debug] Trying alternative sound method...');
            
            // Try alternative sound method as last resort
            const alternativeSuccess = await this.tryAlternativeSound();
            if (alternativeSuccess) {
              console.log('[Audio Debug] Alternative sound method succeeded!');
              this.audioSystemTesting = false;
              return;
            }
            
            // Final attempt to reinitialize for future calls
            this.cleanupAudio();
            await this.initializeAudio();
            
            // Show user message about sound issues
            this.showSoundTroubleshootingMessage();
          }
        }
      }
      
      // Always clear testing flag
      this.audioSystemTesting = false;
    },

    showSoundTroubleshootingMessage() {
      const isSafari = navigator.userAgent.includes('Safari') && !navigator.userAgent.includes('Chrome');
      
      let message = 'Sound konnte nicht abgespielt werden.\n\n';
      
      if (isSafari) {
        message += 'Safari-spezifische Lösungen:\n';
        message += '• Überprüfen Sie die Safari-Einstellungen unter "Websites" > "Auto-Play"\n';
        message += '• Stellen Sie sicher, dass Auto-Play für diese Website erlaubt ist\n';
        message += '• Versuchen Sie, die Seite neu zu laden und sofort auf den Sound-Test zu klicken\n';
        message += '• Überprüfen Sie die Systemlautstärke und Safari-Lautstärke\n\n';
      }
      
      message += 'Allgemeine Lösungen:\n';
      message += '• Überprüfen Sie die Systemlautstärke\n';
      message += '• Überprüfen Sie die Browser-Lautstärke (Tab-Symbol)\n';
      message += '• Stellen Sie sicher, dass der Browser Audio-Berechtigungen hat\n';
      message += '• Versuchen Sie einen anderen Browser (Chrome, Firefox)\n';
      message += '• Laden Sie die Seite neu und versuchen Sie es erneut';
      
      alert(message);
      
      console.log('[Audio Debug] Troubleshooting message shown to user');
    },

    toggleAudioDebug() {
      this.showAudioDebug = !this.showAudioDebug;
      console.log('[Audio Debug] Debug panel toggled:', this.showAudioDebug);
    },

    async playSimpleBeep() {
      console.log('[Simple Beep] Starting simple beep test...');
      
      try {
        // Method 1: Very simple HTML5 Audio
        const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT');
        audio.volume = 0.5;
        await audio.play();
        console.log('[Simple Beep] HTML5 Audio beep played successfully');
        return;
      } catch (error) {
        console.error('[Simple Beep] HTML5 Audio failed:', error);
      }
      
      try {
        // Method 2: Very simple Web Audio API
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        if (audioContext.state === 'suspended') {
          await audioContext.resume();
        }
        
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.3;
        
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.2);
        
        console.log('[Simple Beep] Web Audio API beep played successfully');
        
        setTimeout(() => {
          try {
            audioContext.close();
          } catch (e) {
            // Ignore
          }
        }, 500);
        
      } catch (error) {
        console.error('[Simple Beep] Web Audio API failed:', error);
        alert('Einfacher Sound-Test fehlgeschlagen. Bitte überprüfen Sie Ihre Browser-Einstellungen und Systemlautstärke.');
      }
    },
    async playNotificationSound(score = 50) {
      if (!this.isSoundEnabled) {
        console.log('[Audio] Sound disabled, skipping notification');
        return;
      }
      
      console.log('[Audio] ===== PLAY NOTIFICATION SOUND CALLED =====');
      console.log('[Audio] Score:', score, 'Sound enabled:', this.isSoundEnabled);
      
      // Retry mechanism for notification sound
      let retryCount = 0;
      const maxRetries = 3;

      while (retryCount < maxRetries) {
        try {
          console.log(`[Audio] Notification attempt ${retryCount + 1}/${maxRetries} - Ensuring audio context...`);
          const contextReady = await this.ensureAudioContext();
          
          if (!contextReady) {
            throw new Error('Audio context not available or not running');
          }
          
          console.log('[Audio] Playing notification with score:', score);
          console.log('[Audio] Audio context state:', this.audioContext.state);
          
          // Additional verification before creating oscillators
          if (!this.audioContext || this.audioContext.state !== 'running') {
            throw new Error('Audio context not in running state');
          }
          
          if (!this.gainNode) {
            throw new Error('Gain node not available');
          }
          
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
          oscGain.connect(this.gainNode);
          osc1.connect(oscGain);
          osc2.connect(oscGain);
          
          // Add error handlers
          osc1.addEventListener('ended', () => {
            console.log('[Audio] Notification oscillator 1 ended');
          });
          osc2.addEventListener('ended', () => {
            console.log('[Audio] Notification oscillator 2 ended');
          });
          
          // Start sound
          osc1.start();
          osc2.start();
          
          console.log('[Audio] ===== NOTIFICATION SOUND SHOULD BE PLAYING NOW =====');
          
          // Stop sound after envelope completes and clean up immediately
          setTimeout(() => {
            try {
              osc1.stop();
              osc2.stop();
              osc1.disconnect();
              osc2.disconnect();
              oscGain.disconnect();
              console.log('[Audio] Notification sound cleaned up');
            } catch (error) {
              console.error('[Audio] Error cleaning up notification sound:', error);
            }
          }, 2100); // Slightly longer than envelope to ensure completion
          
          console.log('[Audio] Notification sound played successfully');
          
          // If we reach here, the sound played successfully
          return;
          
        } catch (error) {
          console.error(`[Audio] ===== NOTIFICATION ERROR ON ATTEMPT ${retryCount + 1} =====`);
          console.error('[Audio] Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
          });
          
          retryCount++;
          
          if (retryCount < maxRetries) {
            console.log(`[Audio] Retrying notification... (${retryCount}/${maxRetries})`);
            // Force restart audio system before retry
            await this.forceAudioRestart();
            // Wait a bit before retry
            await new Promise(resolve => setTimeout(resolve, 200));
          } else {
            console.error('[Audio] ===== ALL NOTIFICATION RETRY ATTEMPTS FAILED =====');
            console.log('[Audio] Trying alternative notification sound method...');
            
            // Try alternative sound method as last resort
            const alternativeSuccess = await this.tryAlternativeSound();
            if (alternativeSuccess) {
              console.log('[Audio] Alternative notification sound method succeeded!');
              return;
            }
            
            // Final attempt to reinitialize for future calls
            this.cleanupAudio();
            await this.initializeAudio();
          }
        }
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
      if (!project.ranking?.bid_teaser) return '';
      return formatBidText(project.ranking.bid_teaser);
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
    updateVolume() {
      if (this.gainNode && this.isSoundEnabled) {
        // Convert 0-100 range to 0-1 range for audio gain
        this.gainNode.gain.value = this.volumeLevel / 100;
        // Save volume preference
        localStorage.setItem('volumeLevel', this.volumeLevel);
        console.log('[Audio] Volume updated to:', this.volumeLevel);
      } else if (this.gainNode && !this.isSoundEnabled) {
        this.gainNode.gain.value = 0;
      }
    },
    updateProjectGlowIntensity() {
      this.projects.forEach(project => {
        if (project.isNew) {
          const submissionTime = new Date(project.project_details.time_submitted).getTime();
          const now = new Date().getTime();
          const ageInMinutes = (now - submissionTime) / (1000 * 60);
          
          if (ageInMinutes <= 10) {
            // Calculate opacity based on age (1.0 to 0.0 over 10 minutes)
            const opacity = Math.max(0, 1 - (ageInMinutes / 10));
            const projectElement = document.querySelector(`[data-project-id="${project.project_details.id}"]`);
            if (projectElement) {
              projectElement.style.setProperty('--glow-opacity', opacity);
            }
          } else {
            // Remove new project status after 10 minutes
            project.isNew = false;
          }
        }
      });
    },
    startGlowUpdateInterval() {
      // Update glow intensity every 30 seconds
      setInterval(this.updateProjectGlowIntensity, 30000);
    },
    
    isRecentProject(project) {
      const ageInMinutes = this.getProjectAgeInMinutes(project);
      return ageInMinutes <= 60; // Less than or equal to 1 hour
    },
    
    getProjectAgeInMinutes(project) {
      if (!project.project_details?.time_submitted) return Infinity;
      
      const timestampMs = typeof project.project_details.time_submitted === 'number' 
        ? project.project_details.time_submitted * 1000 
        : new Date(project.project_details.time_submitted).getTime();
      
      if (isNaN(timestampMs)) return Infinity;
      
      const now = Date.now();
      const ageInMs = now - timestampMs;
      return Math.floor(ageInMs / (1000 * 60)); // Convert to minutes
    },
    async handleSendApplication(project) {
      try {
        if (!project.ranking?.bid_teaser) {
          this.showNotification('No bid text available yet', 'error');
          return;
        }

        // ✅ PREVENT DUPLICATE SUBMISSION: Check if bid already submitted
        if (project.buttonStates?.bidSubmitted) {
          console.log('[BidSubmission] ✅ BID ALREADY SUBMITTED - Preventing duplicate submission for project:', project.project_details.id);
          this.showNotification('Bid already submitted for this project', 'info');
          return;
        }

        // ✅ PREVENT DUPLICATE SUBMISSION: Check if already submitting
        if (project.buttonStates?.submitting) {
          console.log('[BidSubmission] ⚠️ ALREADY SUBMITTING - Preventing duplicate submission for project:', project.project_details.id);
          this.showNotification('Bid submission already in progress - please wait', 'warning');
          return;
        }

        // ✅ PREVENT DUPLICATE SUBMISSION: Check if submission failed recently
        if (project.buttonStates?.submissionFailed && project.buttonStates?.lastSubmissionAttempt) {
          const timeSinceLastAttempt = Date.now() - new Date(project.buttonStates.lastSubmissionAttempt).getTime();
          const cooldownMinutes = 3; // 3 minutes cooldown for submission
          if (timeSinceLastAttempt < cooldownMinutes * 60 * 1000) {
            const remainingTime = Math.ceil((cooldownMinutes * 60 * 1000 - timeSinceLastAttempt) / 1000);
            this.showNotification(`Submission failed recently. Please wait ${remainingTime}s before retrying`, 'warning');
            return;
          }
        }

        // Initialize buttonStates if not exists
        if (!project.buttonStates) {
          project.buttonStates = {};
        }

        // Set submitting flag to prevent duplicates
        project.buttonStates.submitting = true;
        project.buttonStates.lastSubmissionAttempt = new Date().toISOString();

        // Show loading state
        this.loadingProject = project.project_details.id;

        // Call the server endpoint to format and submit the bid
        const response = await fetch(`${API_BASE_URL}/api/send-application/${project.project_details.id}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            bidLimit: 200 // Default bid limit, can be made configurable
          })
        });

        if (!response.ok) {
          throw new Error(`Failed to process bid: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('[Debug] Bid processing response:', data);

        // Update last opened project
        this.lastOpenedProject = project.project_details.id;

        if (data.success && data.bid_submitted) {
          // Successful API submission
          console.log('[Debug] Bid successfully submitted via API');
          
          // Update button state for successful submission
          project.buttonStates.submitting = false;
          project.buttonStates.bidSubmitted = true;
          project.buttonStates.submissionFailed = false;
          project.bidSubmittedAt = data.freelancer_response?.result?.time_submitted;
          project.bidAmount = data.bid_data?.amount;
          project.bidPeriod = data.bid_data?.period;

          this.showNotification(`✅ Bid successfully submitted! Amount: $${data.bid_data?.amount}, Period: ${data.bid_data?.period} days`, 'success');

          // Don't automatically open project - let user decide
          // if (data.project_url) {
          //   window.open(data.project_url, '_blank', 'noopener,noreferrer');
          // }

        } else if (data.api_error || !data.success) {
          // API submission failed, fallback to manual submission
          console.log('[Debug] API submission failed, falling back to manual submission');
          
          // Copy the formatted text to clipboard for manual submission
          if (data.formatted_text) {
            try {
              await navigator.clipboard.writeText(data.formatted_text);
              console.log('Bid text copied to clipboard for manual submission');
            } catch (clipboardError) {
              console.warn('Direct clipboard access failed, trying fallback method:', clipboardError);
              
              // Fallback method using textarea
              const textArea = document.createElement('textarea');
              textArea.value = data.formatted_text;
              document.body.appendChild(textArea);
              textArea.select();
              
              try {
                document.execCommand('copy');
                console.log('Bid text copied to clipboard (fallback method)');
              } catch (fallbackError) {
                console.error('Fallback copy failed:', fallbackError);
                throw new Error('Failed to copy bid text to clipboard');
              } finally {
                document.body.removeChild(textArea);
              }
            }
          }

          // Don't automatically open project for manual submission
          // User can click the button to open manually if needed
          // if (data.project_url) {
          //   window.open(data.project_url, '_blank', 'noopener,noreferrer');
          // }

          // Update button state for manual submission
          project.buttonStates.submitting = false;
          project.buttonStates.submissionFailed = true;
          project.buttonStates.manualSubmissionRequired = true;
          project.buttonStates.errorMessage = data.error_message || 'Auto-submission failed';
          project.buttonStates.errorTimestamp = new Date().toISOString();
          
          // Set specific error type based on response
          if (data.bid_count_exceeded) {
            project.buttonStates.errorType = 'bid_count_exceeded';
          } else if (data.error_message?.includes('Freelancer API error')) {
            project.buttonStates.errorType = 'freelancer_api_error';
          } else if (data.error_message?.includes('API call failed')) {
            project.buttonStates.errorType = 'api_call_exception';
          } else if (data.error_message?.includes('bid count')) {
            project.buttonStates.errorType = 'bid_count_check_failed';
          } else {
            project.buttonStates.errorType = 'general_error';
          }

          // Show error message with details
          let errorMsg;
          if (data.bid_count_exceeded) {
            errorMsg = `❌ Too many bids (${data.current_bid_count}/${data.bid_limit}) - Automatic bidding cancelled`;
          } else {
            errorMsg = data.error_message ? 
              `⚠️ Auto-submission failed: ${data.error_message}. Bid text copied for manual submission.` :
              '⚠️ Auto-submission failed. Bid text copied for manual submission.';
          }
          
          this.showNotification(errorMsg, 'error');
        }

      } catch (error) {
        console.error('Error processing bid submission:', error);
        
        // Mark submission as failed with error details
        if (!project.buttonStates) {
          project.buttonStates = {};
        }
        project.buttonStates.submitting = false;
        project.buttonStates.submissionFailed = true;
        project.buttonStates.errorMessage = error.message || 'Failed to process bid submission';
        project.buttonStates.errorTimestamp = new Date().toISOString();
        
        this.showNotification(error.message || 'Failed to process bid submission', 'error');
      } finally {
        // Clear loading state and ensure submitting flag is cleared
        this.loadingProject = null;
        if (project.buttonStates) {
          project.buttonStates.submitting = false;
        }
      }
    },
    getGenerateButtonTitle(project) {
      if (project.ranking?.bid_teaser?.first_paragraph) {
        return 'Bid text already generated';
      } else if (project.buttonStates?.generating) {
        return 'Generating bid text... Please wait';
      } else if (project.buttonStates?.generationFailed) {
        const errorMsg = project.buttonStates?.generationError;
        const timestamp = project.buttonStates?.errorTimestamp;
        const timeStr = timestamp ? new Date(timestamp).toLocaleDateString() + ' ' + new Date(timestamp).toLocaleTimeString() : '';
        
        let tooltip = `❌ BID GENERATION FAILED\n\n`;
        tooltip += `Error: ${errorMsg || 'Unknown error'}\n\n`;
        tooltip += `📅 ${timeStr ? `Time: ${timeStr}` : 'Time: Unknown'}\n\n`;
        tooltip += `💡 Click to retry bid generation`;
        
        return tooltip;
      } else {
        return 'Generate bid text';
      }
    },
    getApplicationButtonTitle(project) {
      if (project.buttonStates?.bidSubmitted) {
        return 'Bid submitted';
      } else if (project.buttonStates?.submitting) {
        return 'Submitting bid... Please wait';
      } else if (project.buttonStates?.manualSubmissionRequired) {
        const errorMsg = project.buttonStates?.errorMessage;
        const timestamp = project.buttonStates?.errorTimestamp;
        const errorType = project.buttonStates?.errorType;
        
        if (errorMsg) {
          const timeStr = timestamp ? new Date(timestamp).toLocaleDateString() + ' ' + new Date(timestamp).toLocaleTimeString() : '';
          
          // Create detailed tooltip based on error type
          let tooltip = `Manual submission required\n\n`;
          
          // Add specific error information based on type
          if (errorType === 'bid_count_exceeded') {
            tooltip += `❌ TOO MANY BIDS\n`;
            tooltip += `Error: ${errorMsg}\n\n`;
            tooltip += `The project has too many competing bids.\n`;
            tooltip += `Automatic bidding was cancelled to avoid\n`;
            tooltip += `wasting time on over-competitive projects.\n\n`;
          } else if (errorType === 'freelancer_api_error') {
            tooltip += `❌ FREELANCER API ERROR\n`;
            tooltip += `Error: ${errorMsg}\n\n`;
            tooltip += `The Freelancer.com API returned an error.\n`;
            tooltip += `This could be due to rate limiting,\n`;
            tooltip += `authentication issues, or server problems.\n\n`;
          } else if (errorType === 'api_call_exception') {
            tooltip += `❌ CONNECTION ERROR\n`;
            tooltip += `Error: ${errorMsg}\n\n`;
            tooltip += `Network connection failed or timeout occurred.\n`;
            tooltip += `Check your internet connection and try again.\n\n`;
          } else if (errorType === 'bid_count_check_failed') {
            tooltip += `❌ BID COUNT CHECK FAILED\n`;
            tooltip += `Error: ${errorMsg}\n\n`;
            tooltip += `Could not verify current bid count before submission.\n`;
            tooltip += `Manual verification recommended.\n\n`;
          } else if (errorType === 'missing_bid_text') {
            tooltip += `❌ NO BID TEXT\n`;
            tooltip += `Error: ${errorMsg}\n\n`;
            tooltip += `Generate bid text first before submitting.\n\n`;
          } else {
            tooltip += `❌ SUBMISSION ERROR\n`;
            tooltip += `Error: ${errorMsg}\n\n`;
          }
          
          tooltip += `📅 ${timeStr ? `Time: ${timeStr}` : 'Time: Unknown'}\n\n`;
          tooltip += `💡 Click to open project for manual submission`;
          
          return tooltip;
        } else {
          return 'Manual submission required - Click to open project for manual bidding';
        }
      } else {
        return 'Send Application';
      }
    },
    onAutomaticBiddingToggle() {
      console.log('Automatic Bidding toggled:', this.automaticBiddingEnabled);
      
      if (this.automaticBiddingEnabled) {
        // DISABLED: Removed immediate project checking to prevent duplicates
        // Auto-bidding will be triggered naturally by new project detection in loadProjects()
        this.showNotification(
          '✅ Automatic Bidding enabled - will process new qualifying projects automatically', 
          'success'
        );
      } else {
        this.showNotification(
          '❌ Automatic Bidding disabled', 
          'info'
        );
      }
    },
    
    // Check if a project should be automatically bid on (eingerahmt = has both quality and urgency flags)
    shouldAutomaticallyBid(project) {
      const projectId = project.project_details?.id || 'unknown';
      
      if (!this.automaticBiddingEnabled) {
        console.log(`[AutoBid] Project ${projectId}: Automatic bidding disabled`);
        return false;
      }
      
      // 🚫 CRITICAL: Check if project is currently being processed
      if (this.processingProjectIds.has(projectId)) {
        console.log(`[AutoBid] Project ${projectId}: ⚠️ ALREADY BEING PROCESSED - SKIPPING to prevent duplicates`);
        return false;
      }
      
      // 🚫 CRITICAL: Check if project has already been processed
      if (this.processedProjectIds.has(projectId)) {
        console.log(`[AutoBid] Project ${projectId}: ⚠️ ALREADY PROCESSED - SKIPPING to prevent duplicates`);
        return false;
      }
      
      // Don't bid if already bid on this project
      if (project.buttonStates?.bidSubmitted || project.buttonStates?.applicationSent) {
        console.log(`[AutoBid] Project ${projectId}: Already bid on this project`);
        // Mark as processed since it's already handled
        this.processedProjectIds.add(projectId);
        return false;
      }
      
      // Don't bid if manual submission is required (error state)
      if (project.buttonStates?.manualSubmissionRequired) {
        console.log(`[AutoBid] Project ${projectId}: Manual submission required (error state present)`);
        return false;
      }
      
      // Check Recent Only filter
      if (this.recentOnlyEnabled && !this.isRecentProject(project)) {
        console.log(`[AutoBid] Project ${projectId}: Not recent (${this.getProjectAgeInMinutes(project)} minutes old, required: ≤60 minutes)`);
        return false;
      }
      
      const shouldBid = this.isQualifiedForAutoBidding(project);
      
      if (shouldBid) {
        console.log(`[AutoBid] ✅ Project ${projectId} qualifies for automatic bidding (age: ${this.getProjectAgeInMinutes(project)} minutes)`);
      } else {
        console.log(`[AutoBid] ❌ Project ${projectId} does not qualify: needs both quality AND urgency flags`);
      }
      
      return shouldBid;
    },
    
    // Check if project qualifies for automatic bidding based on flags only (for QUAL tag display)
    isQualifiedForAutoBidding(project) {
      const flags = project.project_details?.flags || {};
      
      // Check if project has required tag combination
      const hasQualityFlag = flags.is_corr || flags.is_authentic;
      const hasUrgencyFlag = flags.is_high_paying || flags.is_urgent || flags.is_german || this.isHourlyProject(project.project_details) || flags.is_rep || flags.is_enterprise;
      
      // Only qualified if both conditions are met (project is "eingerahmt")
      return hasQualityFlag && hasUrgencyFlag;
    },
    
    // Check all projects for automatic bidding
    async checkProjectsForAutomaticBidding() {
      if (!this.automaticBiddingEnabled) return;
      
      const mode = (this.isPageHidden || !this.windowHasFocus) ? 'BACKGROUND' : 'FOREGROUND';
      console.log(`[AutoBid-${mode}] Checking projects for automatic bidding...`);
      console.log(`[AutoBid-${mode}] Total projects: ${this.projects.length}`);
      console.log(`[AutoBid-${mode}] Recent Only enabled: ${this.recentOnlyEnabled}`);
      console.log(`[AutoBid-${mode}] Automatic Bidding enabled: ${this.automaticBiddingEnabled}`);
      console.log(`[AutoBid-${mode}] Page hidden: ${this.isPageHidden}, Window focus: ${this.windowHasFocus}`);
      
      let qualifyingProjects = 0;
      let skippedProjects = 0;
      
      for (const project of this.projects) {
        const projectId = project.project_details?.id || 'unknown';
        const projectTitle = project.project_details?.title || 'Unknown Title';
        
        console.log(`[AutoBid-${mode}] Analyzing project ${projectId}: "${projectTitle}"`);
        
        // Debug project flags
        const flags = project.project_details?.flags || {};
        console.log(`[AutoBid-${mode}] Project ${projectId} flags:`, flags);
        console.log(`[AutoBid-${mode}] Project ${projectId} age: ${this.getProjectAgeInMinutes(project)} minutes`);
        console.log(`[AutoBid-${mode}] Project ${projectId} is recent: ${this.isRecentProject(project)}`);
        console.log(`[AutoBid-${mode}] Project ${projectId} button states:`, project.buttonStates);
        console.log(`[AutoBid-${mode}] Project ${projectId} has bid teaser: ${!!project.ranking?.bid_teaser}`);
        
        if (this.shouldAutomaticallyBid(project)) {
          console.log(`[AutoBid-${mode}] ✅ Project ${projectId} qualifies for automatic bidding`);
          qualifyingProjects++;
          
          try {
            await this.performAutomaticBid(project);
            console.log(`[AutoBid-${mode}] ✅ Successfully processed automatic bid for project ${projectId}`);
          } catch (error) {
            console.error(`[AutoBid-${mode}] ❌ Failed to process automatic bid for project ${projectId}:`, error);
          }
          
          // Add delay between bids to avoid overwhelming the API
          await new Promise(resolve => setTimeout(resolve, 3000));
        } else {
          console.log(`[AutoBid-${mode}] ❌ Project ${projectId} does not qualify for automatic bidding`);
          skippedProjects++;
        }
      }
      
      console.log(`[AutoBid-${mode}] Summary: ${qualifyingProjects} qualifying projects, ${skippedProjects} skipped projects`);
      
      // Cleanup old processed projects periodically
      this.cleanupProcessedProjects();
      
      // Log background execution status
      if (mode === 'BACKGROUND') {
        console.log(`[AutoBid-BACKGROUND] ✅ Background auto-bidding check completed successfully`);
        
        // Show notification if we processed bids in background
        if (qualifyingProjects > 0) {
          try {
            new Notification(`Auto-Bidding: ${qualifyingProjects} bid(s) processed in background`, {
              icon: '/favicon.ico',
              tag: 'auto-bidding-background'
            });
          } catch (error) {
            console.warn('[AutoBid-BACKGROUND] Could not show notification:', error);
          }
        }
      }
    },
    
    // Save error information to project JSON for persistence
    async saveErrorToProject(project, errorMessage, errorContext = 'auto-bidding') {
      const projectId = project.project_details?.id;
      if (!projectId) return;
      
      try {
        const errorData = {
          error: {
            message: errorMessage,
            context: errorContext,
            timestamp: new Date().toISOString(),
            type: 'manual_submission_required'
          }
        };
        
        const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/error`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(errorData)
        });
        
        if (!response.ok) {
          console.error(`Failed to save error to project ${projectId}:`, response.statusText);
        } else {
          console.log(`Error saved to project ${projectId}:`, errorMessage);
        }
      } catch (error) {
        console.error(`Error saving error to project ${projectId}:`, error);
      }
    },
    
    // Load button states from project data (including error states)
    loadButtonStatesFromProject(project) {
      if (!project.buttonStates) {
        project.buttonStates = {};
      }
      
      // Check if project has error state
      if (project.ranking?.error) {
        project.buttonStates.manualSubmissionRequired = true;
        project.buttonStates.errorMessage = project.ranking.error.message;
        project.buttonStates.errorTimestamp = project.ranking.error.timestamp;
      }
      
      return project.buttonStates;
    },
    
    // Post question to project using Selenium automation
    async postQuestionToProject(projectId) {
      // 🚫 CRITICAL: Check if question is already being posted for this project
      if (this.questionPostingProjectIds.has(projectId)) {
        console.log(`[PostQuestion] ⚠️ DUPLICATE PROTECTION: Question already being posted for project ${projectId} - ABORTING`);
        throw new Error('Question posting already in progress for this project');
      }
      
      try {
        // 🔒 LOCK: Mark project as having question being posted
        this.questionPostingProjectIds.add(projectId);
        console.log(`[PostQuestion] 🔒 LOCKED: Project ${projectId} marked as posting question. Question posting count: ${this.questionPostingProjectIds.size}`);
        
        console.log(`[PostQuestion] Posting question for project ${projectId}`);
        
        // Call the Python script to post the question
        const response = await fetch(`${API_BASE_URL}/api/post-question/${projectId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            projectId: projectId
          })
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
          console.log(`[PostQuestion] ✅ Question posted successfully for project ${projectId}`);
          return result;
        } else {
          throw new Error(result.error || 'Unknown error posting question');
        }
        
      } catch (error) {
        console.error(`[PostQuestion] ❌ Error posting question for project ${projectId}:`, error);
        throw error;
      } finally {
        // 🔓 UNLOCK: Remove from question posting tracking
        this.questionPostingProjectIds.delete(projectId);
        console.log(`[PostQuestion] 🔓 UNLOCKED: Project ${projectId} removed from question posting. Question posting count: ${this.questionPostingProjectIds.size}`);
      }
    },

    // Perform automatic bid on a project using the same functions as manual buttons
    async performAutomaticBid(project) {
      const projectId = project.project_details?.id || 'unknown';
      const projectTitle = project.project_details?.title || 'Unknown Title';
      
      // 🚫 CRITICAL DUPLICATE PROTECTION
      if (this.processingProjectIds.has(projectId)) {
        console.log(`[AutoBid] ⚠️ DUPLICATE PROTECTION: Project ${projectId} is already being processed - ABORTING`);
        this.logAutoBidding(`⚠️ DUPLICATE PROTECTION: Project ${projectId} already being processed - ABORTING`, 'warning');
        return;
      }
      
      if (this.processedProjectIds.has(projectId)) {
        console.log(`[AutoBid] ⚠️ DUPLICATE PROTECTION: Project ${projectId} has already been processed - ABORTING`);
        this.logAutoBidding(`⚠️ DUPLICATE PROTECTION: Project ${projectId} already processed - ABORTING`, 'warning');
        return;
      }
      
      try {
        // 🔒 LOCK: Mark project as being processed
        this.processingProjectIds.add(projectId);
        console.log(`[AutoBid] 🔒 LOCKED: Project ${projectId} marked as processing. Processing count: ${this.processingProjectIds.size}`);
        
        this.logAutoBidding(`🚀 Starting automatic bid for project ${projectId}: "${projectTitle}"`, 'info');
        
        // Add to active bidding projects for UI feedback (pink border)
        this.activeBiddingProjects.add(projectId);
        console.log(`[AutoBid] Added project ${projectId} to active bidding projects. Active count: ${this.activeBiddingProjects.size}`);
        
        // ✅ PREVENT CONCURRENT GENERATION: Check if already generating
        if (project.buttonStates?.generating) {
          this.logAutoBidding(`⚠️ ALREADY GENERATING: Bid generation already in progress for project ${projectId} - skipping`, 'warning');
          return;
        }
        
        // ✅ CRITICAL PROTECTION: Check if bid texts already exist before any generation
        if (project.ranking?.bid_teaser?.first_paragraph) {
          this.logAutoBidding(`📄 ✅ PROTECTION: Bid texts already exist for project ${projectId} - NEVER regenerating`, 'info');
          console.log('[AutoBid] ✅ PROTECTION: Existing bid teaser found:', {
            first_paragraph: project.ranking.bid_teaser.first_paragraph ? 'EXISTS' : 'MISSING',
            second_paragraph: project.ranking.bid_teaser.second_paragraph ? 'EXISTS' : 'MISSING',
            third_paragraph: project.ranking.bid_teaser.third_paragraph ? 'EXISTS' : 'MISSING',
            question: project.ranking.bid_teaser.question ? 'EXISTS' : 'MISSING'
          });
        } else if (project.ranking?.bid_teaser && Object.keys(project.ranking.bid_teaser).length > 0) {
          // ✅ ADDITIONAL PROTECTION: Check for any bid_teaser content
          const hasAnyContent = Object.values(project.ranking.bid_teaser).some(value => 
            value && typeof value === 'string' && value.trim().length > 0
          );
          
          if (hasAnyContent) {
            this.logAutoBidding(`📄 ✅ ADDITIONAL PROTECTION: Bid teaser has content for project ${projectId} - NEVER regenerating`, 'info');
            console.log('[AutoBid] ✅ ADDITIONAL PROTECTION: Bid teaser has content, keys:', Object.keys(project.ranking.bid_teaser));
          } else {
            // Only generate if absolutely no content exists
            this.logAutoBidding(`📝 No existing bid texts found for project ${projectId} - proceeding with generation`, 'info');
            
            // Generate bid text (this function has its own protection checks)
            await this.handleProjectClick(project);
            
            // Verify generation was successful
            if (!project.ranking?.bid_teaser?.first_paragraph) {
              const errorMsg = 'Failed to generate bid text';
              await this.saveErrorToProject(project, errorMsg, 'bid-text-generation');
              throw new Error(errorMsg);
            }
            
            this.logAutoBidding(`✅ Bid text generated for project ${projectId}`, 'success');
          }
        } else {
          // No bid_teaser object exists at all - safe to generate
          this.logAutoBidding(`📝 No bid teaser object found for project ${projectId} - proceeding with generation`, 'info');
          
          // Generate bid text (this function has its own protection checks)
          await this.handleProjectClick(project);
          
          // Verify generation was successful
          if (!project.ranking?.bid_teaser?.first_paragraph) {
            const errorMsg = 'Failed to generate bid text';
            await this.saveErrorToProject(project, errorMsg, 'bid-text-generation');
            throw new Error(errorMsg);
          }
          
          this.logAutoBidding(`✅ Bid text generated for project ${projectId}`, 'success');
        }
        
        // Step 2: Automatically submit the bid (client-side callback)
        this.logAutoBidding(`📤 Automatically submitting bid for project ${projectId}...`, 'info');
        
        try {
          // Use the same send application function as manual bidding
          await this.handleSendApplication(project);
          
          this.logAutoBidding(`✅ Automatic bidding completed for project ${projectId} - bid submitted successfully!`, 'success');
          
          // Post question if enabled
          if (this.postQuestionEnabled) {
            this.logAutoBidding(`📝 Posting question for project ${projectId}...`, 'info');
            
            try {
              await this.postQuestionToProject(projectId);
              this.logAutoBidding(`✅ Question posted successfully for project ${projectId}`, 'success');
            } catch (questionError) {
              this.logAutoBidding(`⚠️ Failed to post question for project ${projectId}: ${questionError.message}`, 'warning');
              // Don't fail the entire process if question posting fails
            }
          }
          
          // Show success notification
          this.showNotification(
            `✅ Auto-bid successful: "${projectTitle.substring(0, 40)}..."${this.postQuestionEnabled ? ' (+ question posted)' : ''}`, 
            'success'
          );
          
        } catch (submitError) {
          // If bid submission fails, log it but don't fail the whole process
          this.logAutoBidding(`⚠️ Bid submission failed for project ${projectId}: ${submitError.message}`, 'error');
          
          // Mark as manual submission required
          if (!project.buttonStates) {
            project.buttonStates = {};
          }
          project.buttonStates.manualSubmissionRequired = true;
          project.buttonStates.errorMessage = `Auto-submission failed: ${submitError.message}`;
          project.buttonStates.errorTimestamp = new Date().toISOString();
          
          this.showNotification(
            `⚠️ Auto-bid generated text but submission failed for "${projectTitle.substring(0, 30)}..." - check manually`, 
            'warning'
          );
        }
        
      } catch (error) {
        const errorMsg = `Auto-bidding failed: ${error.message}`;
        
        // Save error to project JSON for persistence
        await this.saveErrorToProject(project, errorMsg, 'auto-bidding');
        
        // Set button state for UI
        if (!project.buttonStates) {
          project.buttonStates = {};
        }
        project.buttonStates.manualSubmissionRequired = true;
        project.buttonStates.errorMessage = errorMsg;
        project.buttonStates.errorTimestamp = new Date().toISOString();
        
        this.logAutoBidding(`❌ Error during automatic bidding for project ${projectId}: ${error.message}`, 'error');
        
        this.showNotification(
          `❌ Automatic bid error for "${projectTitle}": ${error.message}`, 
          'error'
        );
      } finally {
        // 🔓 UNLOCK: Remove from processing and mark as processed
        this.processingProjectIds.delete(projectId);
        this.processedProjectIds.add(projectId);
        console.log(`[AutoBid] 🔓 UNLOCKED: Project ${projectId} removed from processing and marked as processed`);
        console.log(`[AutoBid] Processing count: ${this.processingProjectIds.size}, Processed count: ${this.processedProjectIds.size}`);
        
        // Remove from active bidding projects (remove pink border)
        this.activeBiddingProjects.delete(projectId);
        console.log(`[AutoBid] Removed project ${projectId} from active bidding projects. Active count: ${this.activeBiddingProjects.size}`);
      }
    },
    onRecentOnlyToggle() {
      console.log('Recent Only toggled:', this.recentOnlyEnabled);
    },
    
    onPostQuestionToggle() {
      console.log('Post Question toggled:', this.postQuestionEnabled);
      
      if (this.postQuestionEnabled) {
        this.showNotification(
          '✅ Post Question enabled - Questions will be posted automatically when auto-bidding', 
          'info'
        );
      } else {
        this.showNotification(
          '📋 Post Question disabled - Auto-bidding will not post questions', 
          'info'
        );
      }
    },
    
    // Cleanup function to remove old processed project IDs (prevents memory leaks)
    cleanupProcessedProjects() {
      // Keep only the last 1000 processed projects to prevent memory issues
      if (this.processedProjectIds.size > 1000) {
        const processedArray = Array.from(this.processedProjectIds);
        const toKeep = processedArray.slice(-500); // Keep last 500
        this.processedProjectIds.clear();
        toKeep.forEach(id => this.processedProjectIds.add(id));
        console.log(`[AutoBid] 🧹 Cleaned up processed projects. Kept ${toKeep.length} recent entries.`);
      }
    },
    
    // Debug function to show current processing state
    showProcessingState() {
      console.log(`[AutoBid] 📊 Processing State:`, {
        processing: Array.from(this.processingProjectIds),
        processed: Array.from(this.processedProjectIds),
        questionPosting: Array.from(this.questionPostingProjectIds),
        activeBidding: Array.from(this.activeBiddingProjects)
      });
    },
    
    // Reset processing state (for debugging)
    resetProcessingState() {
      this.processingProjectIds.clear();
      this.processedProjectIds.clear();
      this.questionPostingProjectIds.clear();
      console.log(`[AutoBid] 🔄 Processing state manually reset`);
      this.logAutoBidding('Processing state manually reset', 'info');
    },
    toggleAutoBidDebug() {
      this.showAutoBidDebug = !this.showAutoBidDebug;
    },
    logAutoBidding(message, type = 'info') {
      const now = new Date();
      const timestamp = now.toLocaleTimeString();
      const fullTimestamp = now.toISOString();
      
      const logEntry = {
        id: Date.now() + Math.random(), // Unique ID for key
        timestamp,
        fullTimestamp,
        message,
        type,
        source: 'vue-frontend',
        isNew: true // Mark as new for highlighting
      };
      
      // Always add to autoBidLogs array at the beginning (newest first)
      this.autoBidLogs.unshift(logEntry);
      
      // Keep only last 200 logs to prevent memory issues
      if (this.autoBidLogs.length > 200) {
        this.autoBidLogs = this.autoBidLogs.slice(0, 200);
      }
      
      // Always log to browser console (regardless of console visibility)
      console.log(`[AutoBid] ${message}`);
      
      // Store persistent logs in localStorage (even when console is closed)
      this.storePersistentAutoBidLog(logEntry);
      
      // Send log to backend for server-side logging (even when console is closed)
      this.sendAutoBidLogToBackend(logEntry);
      
      // Send important auto-bid logs as push notifications to mobile
      this.sendAutoBidPushNotification(message, type);
      
      // Auto-scroll to newest log if console is open
      this.scrollToNewestLog();
    },
    clearLogs() {
      this.autoBidLogs = [];
      this.logAutoBidding('Logs cleared', 'info');
    },
    
    scrollToNewestLog() {
      // Auto-scroll to top (newest logs) when new entries are added
      this.$nextTick(() => {
        const logContainer = this.$refs.logContainer;
        if (logContainer && this.showAutoBidDebug) {
          logContainer.scrollTop = 0; // Scroll to top since newest logs are first
        }
      });
    },
    
    async sendAutoBidPushNotification(message, type) {
      // Only send push notifications for important auto-bid events
      const importantKeywords = [
        '✅ Automatic bidding completed',
        '✅ Auto-bid successful',
        '❌ Auto-bidding failed',
        '❌ Automatic bid error',
        '⚠️ Auto-bid generated text but submission failed',
        '🚀 Starting automatic bid',
        'bid submitted successfully'
      ];
      
      // Check if this is an important auto-bid message
      const isImportant = importantKeywords.some(keyword => 
        message.toLowerCase().includes(keyword.toLowerCase())
      );
      
      if (isImportant && Notification.permission === 'granted') {
        try {
          let title = '🤖 Auto-Bidding';
          let icon = '/favicon.ico';
          
          // Determine title and vibration based on message content
          if (message.includes('✅') || message.includes('successful')) {
            title = '✅ Auto-Bid Success';
          } else if (message.includes('❌') || message.includes('failed') || message.includes('error')) {
            title = '❌ Auto-Bid Error';
          } else if (message.includes('⚠️') || message.includes('warning')) {
            title = '⚠️ Auto-Bid Warning';
          } else if (message.includes('🚀') || message.includes('Starting')) {
            title = '🚀 Auto-Bid Started';
          }
          
          const pushNotification = new Notification(title, {
            body: message,
            icon: icon,
            tag: `auto-bid-log-${Date.now()}`,
            badge: icon,
            requireInteraction: type === 'error',
            silent: false,
            vibrate: type === 'success' ? [200, 100, 200] : type === 'error' ? [300, 100, 300, 100, 300] : [100],
            data: {
              type: 'auto-bid-log',
              logType: type,
              timestamp: new Date().toISOString()
            }
          });
          
          // Auto-close after 4 seconds for non-error notifications
          if (type !== 'error') {
            setTimeout(() => {
              pushNotification.close();
            }, 4000);
          }
          
          console.log(`[AutoBidPush] ✅ Auto-bid push notification sent: ${title}`);
          
        } catch (error) {
          console.warn('[AutoBidPush] Failed to send auto-bid push notification:', error);
        }
      }
    },
    
    storePersistentAutoBidLog(logEntry) {
      try {
        // Get existing persistent logs from localStorage
        const existingLogs = JSON.parse(localStorage.getItem('autoBidPersistentLogs') || '[]');
        
        // Add new log entry
        existingLogs.push(logEntry);
        
        // Keep only last 500 persistent logs to prevent localStorage from getting too large
        const trimmedLogs = existingLogs.slice(-500);
        
        // Save back to localStorage
        localStorage.setItem('autoBidPersistentLogs', JSON.stringify(trimmedLogs));
        
        console.log(`[AutoBid] Stored persistent log entry (${trimmedLogs.length} total)`);
      } catch (error) {
        console.warn('[AutoBid] Failed to store persistent log:', error);
      }
    },
    
    sendAutoBidLogToBackend(logEntry) {
      // Send auto-bid log to backend for server-side logging (fire and forget)
      fetch('/api/auto-bid-log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          timestamp: logEntry.fullTimestamp,
          message: logEntry.message,
          type: logEntry.type,
          source: 'vue-frontend'
        })
      }).catch(error => {
        // Silent failure - we don't want logging failures to disrupt auto-bidding
        console.warn('[AutoBid] Failed to send log to backend:', error);
      });
    },
    
    async loadPersistentAutoBidLogs() {
      try {
        // Load logs from backend API first
        await this.loadBackendAutoBidLogs();
        
        // Then load from localStorage as fallback/supplement
        const persistentLogs = JSON.parse(localStorage.getItem('autoBidPersistentLogs') || '[]');
        
        // Merge persistent logs with current logs (avoiding duplicates)
        const currentLogIds = new Set(this.autoBidLogs.map(log => log.id));
        const newPersistentLogs = persistentLogs.filter(log => !currentLogIds.has(log.id));
        
        // Add persistent logs to current logs
        this.autoBidLogs = [...newPersistentLogs, ...this.autoBidLogs];
        
        // Keep only last 200 logs for display
        if (this.autoBidLogs.length > 200) {
          this.autoBidLogs = this.autoBidLogs.slice(-200);
        }
        
        console.log(`[AutoBid] Loaded ${newPersistentLogs.length} persistent logs from localStorage`);
        
        // Start polling for new logs
        this.startAutoBidLogPolling();
      } catch (error) {
        console.warn('[AutoBid] Failed to load persistent logs:', error);
      }
    },
    
    async loadBackendAutoBidLogs() {
      try {
        const response = await fetch('/api/auto-bid-logs?limit=200&includeFile=true');
        if (response.ok) {
          const data = await response.json();
          const backendLogs = data.logs || [];
          
          // Convert backend logs to frontend format
          const formattedLogs = backendLogs.map(log => ({
            id: `backend-${log.timestamp}-${Math.random()}`,
            timestamp: new Date(log.timestamp).toLocaleTimeString(),
            fullTimestamp: log.timestamp,
            message: log.message,
            type: log.type,
            source: log.source || 'backend',
            isNew: this.isLogNew(log.timestamp)
          }));
          
          // Merge with existing logs (avoiding duplicates)
          const existingMessages = new Set(this.autoBidLogs.map(log => `${log.fullTimestamp}-${log.message}`));
          const newBackendLogs = formattedLogs.filter(log => 
            !existingMessages.has(`${log.fullTimestamp}-${log.message}`)
          );
          
          // Add new backend logs to the beginning of the array (newest first)
          this.autoBidLogs = [...newBackendLogs, ...this.autoBidLogs];
          
          // Sort by timestamp (newest first) to maintain proper order
          this.autoBidLogs.sort((a, b) => new Date(b.fullTimestamp) - new Date(a.fullTimestamp));
          
          // Keep only last 200 logs
          if (this.autoBidLogs.length > 200) {
            this.autoBidLogs = this.autoBidLogs.slice(0, 200);
          }
          
          console.log(`[AutoBid] Loaded ${newBackendLogs.length} new logs from backend`);
          
          // Auto-scroll to newest logs if new logs were loaded
          if (newBackendLogs.length > 0) {
            this.scrollToNewestLog();
          }
        }
      } catch (error) {
        console.warn('[AutoBid] Failed to load backend logs:', error);
      }
    },
    
    isLogNew(timestamp) {
      // Consider logs from the last 30 seconds as "new"
      const logTime = new Date(timestamp).getTime();
      const now = Date.now();
      const thirtySecondsAgo = now - (30 * 1000);
      return logTime > thirtySecondsAgo;
    },
    
    startAutoBidLogPolling() {
      // Poll for new logs every 10 seconds
      if (this.autoBidLogPollingInterval) {
        clearInterval(this.autoBidLogPollingInterval);
      }
      
      this.autoBidLogPollingInterval = setInterval(async () => {
        await this.loadBackendAutoBidLogs();
        
        // Update "isNew" status for existing logs
        this.autoBidLogs.forEach(log => {
          if (log.isNew && !this.isLogNew(log.fullTimestamp)) {
            log.isNew = false;
          }
        });
      }, 10000); // Poll every 10 seconds
    },
    
    stopAutoBidLogPolling() {
      if (this.autoBidLogPollingInterval) {
        clearInterval(this.autoBidLogPollingInterval);
        this.autoBidLogPollingInterval = null;
      }
    },
    startDrag(event) {
      this.isDragging = true;
      this.dragStartX = event.clientX - this.consoleX;
      this.dragStartY = event.clientY - this.consoleY;
      
      // Add global mouse event listeners
      document.addEventListener('mousemove', this.drag);
      document.addEventListener('mouseup', this.stopDrag);
      
      // Prevent text selection while dragging
      event.preventDefault();
    },
    drag(event) {
      if (this.isDragging) {
        this.consoleX = event.clientX - this.dragStartX;
        this.consoleY = event.clientY - this.dragStartY;
        
        // Keep console within viewport bounds
        const maxX = window.innerWidth - 400; // console width
        const maxY = window.innerHeight - 300; // estimated console height
        
        this.consoleX = Math.max(0, Math.min(this.consoleX, maxX));
        this.consoleY = Math.max(0, Math.min(this.consoleY, maxY));
      }
    },
    stopDrag() {
      this.isDragging = false;
      
      // Remove global mouse event listeners
      document.removeEventListener('mousemove', this.drag);
      document.removeEventListener('mouseup', this.stopDrag);
      
      // Save position to localStorage
      this.saveConsolePosition();
    },
    getStoredConsolePosition() {
      const stored = localStorage.getItem('autoBidConsolePosition');
      if (stored) {
        try {
          const position = JSON.parse(stored);
          return {
            x: Math.max(0, Math.min(position.x || 100, window.innerWidth - 300)),
            y: Math.max(0, Math.min(position.y || 100, window.innerHeight - 200)),
            width: Math.max(300, Math.min(position.width || 500, window.innerWidth - 100)),
            height: Math.max(200, Math.min(position.height || 400, window.innerHeight - 100))
          };
        } catch (e) {
          console.warn('Invalid console position in localStorage:', e);
        }
      }
      // Default position and size
      return { x: 100, y: 100, width: 500, height: 400 };
    },
    saveConsolePosition() {
      const position = {
        x: this.consoleX,
        y: this.consoleY,
        width: this.consoleWidth,
        height: this.consoleHeight
      };
      localStorage.setItem('autoBidConsolePosition', JSON.stringify(position));
    },
    initializeConsolePosition() {
      const position = this.getStoredConsolePosition();
      this.consoleX = position.x;
      this.consoleY = position.y;
      this.consoleWidth = position.width;
      this.consoleHeight = position.height;
    },
    startResize(handle, event) {
      this.isResizing = true;
      this.resizeStartX = event.clientX;
      this.resizeStartY = event.clientY;
      this.resizeStartWidth = this.consoleWidth;
      this.resizeStartHeight = this.consoleHeight;
      this.resizeHandle = handle;
      
      // Add global mouse event listeners
      document.addEventListener('mousemove', this.resize);
      document.addEventListener('mouseup', this.stopResize);
      
      event.preventDefault();
    },
    resize(event) {
      if (this.isResizing) {
        const deltaX = event.clientX - this.resizeStartX;
        const deltaY = event.clientY - this.resizeStartY;
        
        if (this.resizeHandle === 'right' || this.resizeHandle === 'corner') {
          this.consoleWidth = Math.max(300, this.resizeStartWidth + deltaX);
        }
        
        if (this.resizeHandle === 'bottom' || this.resizeHandle === 'corner') {
          this.consoleHeight = Math.max(200, this.resizeStartHeight + deltaY);
        }
      }
    },
    stopResize() {
      this.isResizing = false;
      
      // Remove global mouse event listeners
      document.removeEventListener('mousemove', this.resize);
      document.removeEventListener('mouseup', this.stopResize);
      
      this.saveConsolePosition();
    },
    formatLogMessage(message) {
      // Format project IDs as links and handle line breaks
      return message
        .replace(/project (\d+)/gi, '<a href="https://www.freelancer.com/projects/$1" target="_blank" class="project-link">project $1</a>')
        .replace(/Project (\d+)/gi, '<a href="https://www.freelancer.com/projects/$1" target="_blank" class="project-link">Project $1</a>')
        .replace(/\n/g, '<br>');
    },
    
    // Tag filtering methods
    projectHasTag(project, tagKey) {
      const flags = project.project_details?.flags || {};
      
      switch (tagKey) {
        case 'hourly':
          return this.isHourlyProject(project.project_details);
        case 'high_paying':
          return flags.is_high_paying;
        case 'urgent':
          return flags.is_urgent;
        case 'authentic':
          return flags.is_authentic;
        case 'german':
          return flags.is_german;
        case 'enterprise':
          return flags.is_enterprise;
        case 'correlation':
          return flags.is_corr;
        case 'reputation':
          return flags.is_rep;
        case 'qualified':
          return this.isQualifiedForAutoBidding(project);
        default:
          return false;
      }
    },
    
    getTagCount(tagKey) {
      return this.projects.filter(project => this.projectHasTag(project, tagKey)).length;
    },
    
    onTagFilterChange() {
      console.log('Selected tags:', this.selectedTags);
      // Force re-computation of filtered projects
      this.$forceUpdate();
    },
    
    clearAllFilters() {
      this.selectedTags = [];
      this.onTagFilterChange();
    },
    
    // Close tag filter dropdown when clicking outside
    handleClickOutside(event) {
      // Use document.querySelector instead of this.$el.querySelector
      const tagFiltersContainer = document.querySelector('.tag-filters-container');
      if (tagFiltersContainer && !tagFiltersContainer.contains(event.target)) {
        this.showTagFilters = false;
      }
    },

    setupVisibilityHandling() {
      console.log('[BackgroundExecution] Setting up page visibility handling...');
      
      // Store original functions to preserve them
      this.originalCheckForNewProjects = this.checkForNewProjects;
      this.originalLoadProjects = this.loadProjects;
      
      // Handle page visibility changes
      this.handleVisibilityChange = () => {
        if (document.hidden) {
          console.log('[BackgroundExecution] 🔒 Page hidden (system locked/background) - maintaining auto-bidding');
          this.isPageHidden = true;
          
          // Switch to aggressive background mode
          this.switchToBackgroundMode();
        } else {
          console.log('[BackgroundExecution] 👀 Page visible (system unlocked/foreground) - resuming normal mode');
          this.isPageHidden = false;
          
          // Resume normal mode
          this.switchToForegroundMode();
        }
      };
      
      // Listen for visibility changes (when Mac is locked/unlocked)
      document.addEventListener('visibilitychange', this.handleVisibilityChange);
      
      // Also listen for focus/blur events as backup
      this.handleFocusChange = (event) => {
        if (event.type === 'blur') {
          console.log('[BackgroundExecution] 🔒 Window lost focus - preparing for background execution');
          this.windowHasFocus = false;
        } else if (event.type === 'focus') {
          console.log('[BackgroundExecution] 👀 Window gained focus - resuming active execution');
          this.windowHasFocus = true;
        }
      };
      
      window.addEventListener('focus', this.handleFocusChange);
      window.addEventListener('blur', this.handleFocusChange);
      
      // Initialize states
      this.isPageHidden = document.hidden;
      this.windowHasFocus = document.hasFocus();
      
      console.log('[BackgroundExecution] Initial states:', {
        isPageHidden: this.isPageHidden,
        windowHasFocus: this.windowHasFocus
      });
    },

    cleanupVisibilityHandling() {
      if (this.handleVisibilityChange) {
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
      }
      if (this.handleFocusChange) {
        window.removeEventListener('focus', this.handleFocusChange);
        window.removeEventListener('blur', this.handleFocusChange);
      }
    },

    async setupWakeLockIfSupported() {
      if ('wakeLock' in navigator) {
        try {
          console.log('[BackgroundExecution] Screen Wake Lock API supported - requesting wake lock');
          
          // Request a screen wake lock to keep the system active
          this.wakeLock = await navigator.wakeLock.request('screen');
          
          console.log('[BackgroundExecution] ✅ Screen wake lock acquired successfully');
          
          // Listen for wake lock release
          this.wakeLock.addEventListener('release', () => {
            console.log('[BackgroundExecution] 🔓 Screen wake lock released');
          });
          
        } catch (error) {
          console.warn('[BackgroundExecution] Failed to acquire screen wake lock:', error);
        }
      } else {
        console.log('[BackgroundExecution] Screen Wake Lock API not supported');
      }
      
      // Request notification permissions for background auto-bidding alerts
      await this.requestNotificationPermission();
    },

    async requestNotificationPermission() {
      if ('Notification' in window) {
        try {
          const permission = await Notification.requestPermission();
          if (permission === 'granted') {
            console.log('[BackgroundExecution] ✅ Notification permission granted - background alerts enabled');
          } else {
            console.log('[BackgroundExecution] ⚠️ Notification permission denied - background alerts disabled');
          }
        } catch (error) {
          console.warn('[BackgroundExecution] Error requesting notification permission:', error);
        }
      } else {
        console.log('[BackgroundExecution] Notifications not supported in this browser');
      }
    },

    releaseWakeLock() {
      if (this.wakeLock) {
        this.wakeLock.release();
        this.wakeLock = null;
        console.log('[BackgroundExecution] Wake lock released');
      }
    },

    setupBackgroundKeepAlive() {
      console.log('[BackgroundExecution] Setting up background keep-alive mechanisms...');
      
      // Use high-frequency keep-alive to prevent browser throttling
      this.backgroundKeepAliveInterval = setInterval(() => {
        if (this.isPageHidden || !this.windowHasFocus) {
          console.log('[BackgroundExecution] 🔄 Keep-alive ping (background mode active)');
          
          // Force garbage collection to prevent memory issues in background
          if (window.gc) {
            window.gc();
          }
          
                     // DISABLED: Auto-bidding moved to new project detection in loadProjects() to prevent duplicates
           // Background auto-bidding is handled automatically when new projects are detected
        }
      }, 5000); // Every 5 seconds in background
      
      // Use requestAnimationFrame as backup (more reliable for background execution)
      this.rafKeepAlive = () => {
        if (this.isPageHidden || !this.windowHasFocus) {
          // Continue the loop even in background
          this.rafId = requestAnimationFrame(this.rafKeepAlive);
        } else {
          // Slow down in foreground to save resources
          setTimeout(() => {
            this.rafId = requestAnimationFrame(this.rafKeepAlive);
          }, 1000);
        }
      };
      
      this.rafId = requestAnimationFrame(this.rafKeepAlive);
    },

    cleanupBackgroundKeepAlive() {
      if (this.backgroundKeepAliveInterval) {
        clearInterval(this.backgroundKeepAliveInterval);
        this.backgroundKeepAliveInterval = null;
      }
      
      if (this.rafId) {
        cancelAnimationFrame(this.rafId);
        this.rafId = null;
      }
    },

    switchToBackgroundMode() {
      console.log('[BackgroundExecution] 🔄 Switching to BACKGROUND mode (aggressive auto-bidding)');
      
      // Clear existing polling interval
      if (this.projectPollingInterval) {
        clearInterval(this.projectPollingInterval);
      }
      
      // Set up more frequent polling for background mode (every 10 seconds)
      this.projectPollingInterval = setInterval(() => {
        console.log('[BackgroundExecution] 🔍 Background polling check...');
        this.loadProjects().catch(error => {
          console.error('[BackgroundExecution] Background polling failed:', error);
        });
      }, 10000); // 10 seconds for aggressive background checking
      
      // DISABLED: Removed immediate auto-bidding check to prevent duplicates
      // Auto-bidding will be triggered naturally by new project detection in loadProjects()
    },

    switchToForegroundMode() {
      console.log('[BackgroundExecution] 👀 Switching to FOREGROUND mode (normal polling)');
      
      // Clear background polling interval
      if (this.projectPollingInterval) {
        clearInterval(this.projectPollingInterval);
      }
      
      // Resume normal polling (every 20 seconds)
      this.projectPollingInterval = setInterval(() => {
        this.loadProjects().catch(error => {
          console.error('[ProjectList] Foreground polling failed:', error);
        });
      }, 20000); // Back to normal 20 seconds
      
      // Trigger immediate refresh when coming back to foreground
      console.log('[BackgroundExecution] 🔄 Immediate refresh after foreground mode switch');
      this.loadProjects().catch(error => {
        console.error('[BackgroundExecution] Immediate foreground refresh failed:', error);
      });
    },

    testPushNotification() {
      // Implement the logic for testing push notifications
      console.log('Test push notification triggered');
      this.showNotification('This is a test push notification', 'info');
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

.header-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 40px; /* Fixed height for consistent alignment */
}

.sound-controls {
  position: relative;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 4px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
  transition: all 0.3s ease;
}

.sound-controls:hover {
  background: rgba(255, 255, 255, 0.15);
}

.dark-theme .sound-controls {
  background: rgba(0, 0, 0, 0.2);
}

.dark-theme .sound-controls:hover {
  background: rgba(0, 0, 0, 0.3);
}

.theme-toggle,
.sound-toggle,
.test-sound,
.debug-audio,
.simple-beep,
.system-theme-reset {
  background: transparent;
  border: none;
  color: #666;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 24px;
  width: 24px;
  position: relative;
}

/* Standalone buttons (outside sound-controls) get background */
.header-controls > .theme-toggle {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
  padding: 8px;
  border-radius: 8px;
  height: 32px;
  width: 32px;
}

.theme-toggle:hover,
.sound-toggle:hover,
.test-sound:hover,
.debug-audio:hover,
.simple-beep:hover,
.system-theme-reset:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Standalone theme toggle hover */
.header-controls > .theme-toggle:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
}

.dark-theme .theme-toggle,
.dark-theme .sound-toggle,
.dark-theme .test-sound,
.dark-theme .debug-audio,
.dark-theme .simple-beep,
.dark-theme .system-theme-reset {
  color: #fff;
  background: transparent;
}

/* Standalone theme toggle dark theme */
.dark-theme .header-controls > .theme-toggle {
  background: rgba(0, 0, 0, 0.3);
}

.dark-theme .theme-toggle:hover,
.dark-theme .sound-toggle:hover,
.dark-theme .test-sound:hover,
.dark-theme .debug-audio:hover,
.dark-theme .simple-beep:hover,
.dark-theme .system-theme-reset:hover {
  background: rgba(0, 0, 0, 0.3);
}

/* Standalone theme toggle dark theme hover */
.dark-theme .header-controls > .theme-toggle:hover {
  background: rgba(0, 0, 0, 0.5);
  transform: translateY(-1px);
}

.theme-toggle i,
.sound-toggle i,
.test-sound i,
.debug-audio i,
.simple-beep i,
.system-theme-reset i {
  font-size: 1.1em;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.system-indicator {
  position: absolute;
  top: -2px;
  right: -2px;
  font-size: 10px;
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.test-sound:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.test-sound:disabled:hover {
  background-color: transparent;
}

.dark-theme .test-sound:disabled:hover {
  background-color: transparent;
}

.audio-debug-panel {
  position: fixed;
  top: 80px;
  right: 20px;
  width: 350px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  font-size: 0.9em;
}

.dark-theme .audio-debug-panel {
  background: #2a2a2a;
  border-color: #444;
  color: #fff;
}

.debug-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #ddd;
  background: #f8f9fa;
  border-radius: 8px 8px 0 0;
}

.dark-theme .debug-header {
  background: #333;
  border-bottom-color: #444;
}

.debug-header h4 {
  margin: 0;
  font-size: 1em;
}

.close-debug {
  background: none;
  border: none;
  font-size: 1.5em;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dark-theme .close-debug {
  color: #ccc;
}

.debug-content {
  padding: 16px;
}

.debug-section {
  margin-bottom: 16px;
}

.debug-section:last-child {
  margin-bottom: 0;
}

.debug-section strong {
  display: block;
  margin-bottom: 8px;
  color: #333;
}

.dark-theme .debug-section strong {
  color: #fff;
}

.debug-section ul {
  margin: 0;
  padding-left: 20px;
  list-style: none;
}

.debug-section li {
  margin-bottom: 4px;
  font-family: monospace;
  font-size: 0.9em;
}

.debug-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.debug-button {
  background: #007bff;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8em;
  transition: all 0.2s ease;
}

.debug-button:hover {
  background: #0056b3;
  transform: translateY(-1px);
}

.debug-button.reset-button {
  background: #dc3545;
}

.debug-button.reset-button:hover {
  background: #c82333;
}

.logo {
  height: 40px;
  width: auto;
  margin-right: auto; /* This pushes the controls to the right */
}

.logo.inverted {
  filter: invert(1);
}

.project-card {
  background: white;
  border-radius: 2px;
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.1);
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

/* Dark theme adjustments */
.dark-theme .project-card {
  background: #1a1a1a;
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
    }
  }

  .project-title {
    font-size: 1.0em; /* Erhöht von 0.9em auf 1.0em */
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

  /* Add solid overlay background */
  &::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: white;
    z-index: -1;
  }

  .content-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    box-sizing: border-box;
    position: relative;
    z-index: 1;
    background: white; /* Ensure content container is also opaque */
  }
}

/* Dark theme adjustments */
.dark-theme .project-card.expanded {
  background: #0f1720;
}

.dark-theme .project-card.expanded::before {
  background: #0f1720;
}

.dark-theme .project-card.expanded .content-container {
  background: #0f1720;
}

/* Prevent body scrolling when card is expanded */
body:has(.project-card.expanded) {
  overflow: hidden;
}

/* Ensure the close button stays on top */
.project-card.expanded .close-button {
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

.dark-theme .project-card.expanded .close-button {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* Add overlay to body when card is expanded */
body:has(.project-card.expanded) {
  overflow: hidden;
}

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
  font-size: 1.0em; /* Erhöht von 0.9em auf 1.0em */
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

    &.hourly-price {
      background-color: #00e676 !important; /* Brighter green */
      color: #000 !important; /* Black text for better contrast */
      padding: 4px 10px !important;
      border-radius: 12px !important;
      font-weight: bold !important;
      box-shadow: 0 2px 8px rgba(0, 230, 118, 0.4) !important; /* Green glow */
      transition: all 0.2s ease !important;
      animation: pulse 2s infinite !important; /* Subtle pulse animation */
      border: none !important;
      
      i {
        color: #000 !important;
        opacity: 1;
      }
      
      &:hover {
        background-color: #00e676 !important;
        box-shadow: 0 2px 12px rgba(0, 230, 118, 0.7) !important;
      }

      .hourly-icon {
        margin-left: 2px;
        color: #000 !important;
      }
    }
  }
}

.dark-theme {
  .project-header .elapsed-time {
    color: #ffffff !important; /* Knallweiß für Zeit-Anzeige */
    
    i {
      color: #90A4AE; /* Blau-Grau für Uhr-Icon wie vorher */
      opacity: 0.8;
    }
  }

  .project-metrics .metric {
    color: #ffffff !important; /* Knallweiß für alle Metrics */
    background: rgba(255, 255, 255, 0.05);
    
    &:hover {
      background: rgba(255, 255, 255, 0.08);
    }

    &.hourly-price {
      background-color: #00e676 !important; /* Keep the same bright green for dark theme */
      color: #000 !important; /* Black text for contrast */
      box-shadow: 0 2px 8px rgba(0, 230, 118, 0.6) !important; /* Stronger glow for dark theme */
      padding: 4px 10px !important;
      border-radius: 12px !important;
      font-weight: bold !important;
      transition: all 0.2s ease !important;
      animation: pulse 2s infinite !important;
      border: none !important;
      
      i {
        color: #000 !important;
        opacity: 1;
      }
      
      &:hover {
        background-color: #00e676 !important;
        box-shadow: 0 2px 12px rgba(0, 230, 118, 0.8) !important;
      }

      .hourly-icon {
        color: #000 !important;
      }
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

/* Make bid numbers bold and prominent */
.metric:has(.bids-icon) strong,
.metric:has(.avg-bid-icon) strong {
  font-weight: 900 !important;
  font-size: 1.1em;
}

/* Alternative approach for browsers that don't support :has() */
.metric[title="Bids"] strong,
.metric[title="Avg Bid"] strong {
  font-weight: 900 !important;
  font-size: 1.1em;
}

.dark-theme {
  .completed-icon { color: #81C784; }  /* Grün für completed projects */
  .rating-icon { color: #FFD54F; }     /* Gelb für Rating */
  .score-icon { color: #64B5F6; }      /* Blau für Score */
  .earnings-icon { color: #4DB6AC; }   /* Teal für Earnings */
  .bids-icon { color: #BA68C8; }       /* Purple für Bids */
  .avg-bid-icon { color: #FFB74D; }    /* Orange für Avg Bid */
  .fa-clock { color: #90A4AE; }        /* Blau-Grau für Uhr */
}

.country-flag {
  border-radius: 2px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.project-title {
  margin: 0;
  word-break: break-word;
  width: 100%;
  box-sizing: border-box;
  font-size: 1.4em;
  line-height: 1.4;
  text-align: center;
  font-weight: 600;
}

.project-card:not(.expanded) .project-title {
  font-size: 1.0em; /* Erhöht von 0.9em auf 1.0em */
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
    background-color: #BBBBBB; /* Default gray for all buttons */

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      background-color: #666666; /* Slightly darker gray on hover */
    }

    /* Project link button is gray by default */
    &.project-link {
      background-color: #BBBBBB;
      &:hover { background-color: #666666; }
      &.clicked {
        background-color: #2196F3;
        &:hover { background-color: #1976D2; }
      }
    }

    &.employer-link {
      background-color: #9C27B0;
      &:hover { background-color: #7B1FA2; }
    }

    /* Expand and generate buttons are gray by default */
    &.expand {
      background-color: #BBBBBB;
      &:hover { background-color: #666666; }
      &.clicked {
        background-color: #FFC107;
        &:hover { background-color: #FFA000; }
      }
    }

    /* Generate button logic */
    &.generate {
      background-color: #BBBBBB;
      &:hover { background-color: #666666; }
      &.clicked {
        background-color: #4CAF50;
        &:hover { background-color: #388E3C; }
      }
      &.disabled {
        background-color: #4CAF50;
      }
    }

    /* When copy-and-open or question buttons exist, generate button should be colored */
    .project-footer:has(.copy-and-open), 
    .project-footer:has(.question) {
      .generate {
        background-color: #4CAF50;
        &:hover { background-color: #388E3C; }
      }
    }

    /* Copy-and-open button is gray by default */
    &.copy-and-open {
      background-color: #BBBBBB;
      &:hover { background-color: #666666; }
      &.clicked {
        background-color: #f44336;
        &:hover { background-color: #d32f2f; }
      }
      &.active {
        background-color: #BBBBBB; /* Keep gray even when active */
        &.clicked {
          background-color: #f44336;
          &:hover { background-color: #d32f2f; }
        }
      }
    }

    /* Question button is gray by default */
    &.question {
      background-color: #BBBBBB;
      &:hover { background-color: #666666; }
      &.clicked {
        background-color: #FF9800;
        &:hover { background-color: #F57C00; }
      }
    }

    &.disabled {
      background-color: #999;
      cursor: not-allowed;
      pointer-events: none;
    }
  }
}

/* Dark theme adjustments */
.dark-theme .action-button {
  &.project-link:not(.clicked),
  &.expand:not(.clicked),
  &.copy-and-open:not(.clicked),
  &.question:not(.clicked) {
    background-color: #666666;
    &:hover {
      background-color: #777777;
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
  font-size: 1.0em; /* Increased from 0.9em to 1.0em */
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

.sound-controls {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.volume-slider {
  width: 60px;
  height: 3px;
  -webkit-appearance: none;
  appearance: none;
  background: #ddd;
  outline: none;
  border-radius: 2px;
  cursor: pointer;
  margin: 0;
  padding: 0;
  vertical-align: middle;
}

.volume-slider.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dark-theme .volume-slider {
  background: #444;
}

.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 10px;
  height: 10px;
  background: #666;
  border-radius: 50%;
  cursor: pointer;
}

.dark-theme .volume-slider::-webkit-slider-thumb {
  background: #fff;
}

.volume-slider::-moz-range-thumb {
  width: 10px;
  height: 10px;
  background: #666;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.dark-theme .volume-slider::-moz-range-thumb {
  background: #fff;
}

.volume-slider.disabled::-webkit-slider-thumb {
  background: #999;
  cursor: not-allowed;
}

.dark-theme .volume-slider.disabled::-webkit-slider-thumb {
  background: #666;
}

.volume-slider.disabled::-moz-range-thumb {
  background: #999;
  cursor: not-allowed;
}

.dark-theme .volume-slider.disabled::-moz-range-thumb {
  background: #666;
}

.volume-slider:hover {
  opacity: 1;
}

.volume-slider::-webkit-slider-thumb:hover {
  background: #444;
}

.dark-theme .volume-slider::-webkit-slider-thumb:hover {
  background: #ddd;
}

.volume-slider::-moz-range-thumb:hover {
  background: #444;
}

.dark-theme .volume-slider::-moz-range-thumb:hover {
  background: #ddd;
}

.project-card.fade-in {
  animation: fadeInRedBorder 10s cubic-bezier(0.4, 0, 0.2, 1) forwards, fadeInRedBackground 2s ease-out forwards;
  border: 2px solid transparent;
}

@keyframes fadeInRedBorder {
  0% {
    border-color: rgba(255, 0, 0, 1);
  }
  20% {
    border-color: rgba(255, 0, 0, 0.9);
  }
  40% {
    border-color: rgba(255, 0, 0, 0.7);
  }
  60% {
    border-color: rgba(255, 0, 0, 0.5);
  }
  80% {
    border-color: rgba(255, 0, 0, 0.3);
  }
  100% {
    border-color: transparent;
  }
}

@keyframes fadeInRedBackground {
  0% {
    background-color: rgba(255, 0, 0, 0.2);
  }
  100% {
    background-color: white;
  }
}

.dark-theme .project-card.fade-in {
  animation: fadeInRedBorder 10s cubic-bezier(0.4, 0, 0.2, 1) forwards, fadeInRedBackgroundDark 2s ease-out forwards;
}

@keyframes fadeInRedBackgroundDark {
  0% {
    background-color: rgba(255, 0, 0, 0.2);
  }
  100% {
    background-color: #0f1720;
  }
}

/* Ensure animations work with other card states */
.project-card.fade-in.high-paying,
.project-card.fade-in.german,
.project-card.fade-in.urgent,
.project-card.fade-in.enterprise {
  animation: fadeInRedBorder 10s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.dark-theme .project-card.fade-in.high-paying,
.dark-theme .project-card.fade-in.german,
.dark-theme .project-card.fade-in.urgent,
.dark-theme .project-card.fade-in.enterprise {
  animation: fadeInRedBorder 10s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

/* Flag tag styles */
.metric.flag-tag {
  font-weight: bold;
  padding: 2px 8px;
  border-radius: 12px;
  border: none;
  color: white !important;

  &.hr {
    background-color: #9c27b0 !important; /* Purple */
    color: white !important;
  }

  &.pay {
    background-color: #ffd700 !important; /* Yellow */
    color: white !important; /* Better contrast for yellow */
  }

  &.urg {
    background-color: #f44336 !important; /* Red */
    color: white !important;
  }

  &.auth {
    background-color: #00bcd4 !important; /* Cyan */
    color: white !important;
  }

  &.germ {
    background-color: #ff9800 !important; /* Orange */
    color: white !important;
  }

  &.corp {
    background-color: #8B4513 !important; /* Brown */
    color: white !important;
  }

  &.corr {
    background-color: #00CED1 !important; /* Turquoise */
    color: white !important;
  }

  &.rep {
    background-color: #800080 !important; /* Purple */
    color: white !important;
  }

  &.qual {
    background-color: #2E7D32 !important; /* Dark green for QUAL */
    border: 2px solid #1B5E20 !important;
    font-weight: bold !important;
    color: white !important;
  }

  &.lang {
    background-color: #667eea !important; /* Blue-purple gradient start */
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: white !important;
    font-weight: bold !important;
    font-size: 0.75em !important;
  }
}

.dark-theme .project-card {
  /* Dark theme base colors with higher opacity */
  &.high-paying {
    background-color: rgba(255, 215, 0, 0.3) !important;
  }
  
  &.urgent {
    background-color: rgba(244, 67, 54, 0.3) !important;
  }
  
  &.authentic {
    background-color: rgba(0, 188, 212, 0.3) !important;
  }
  
  &.german {
    background-color: rgba(255, 152, 0, 0.3) !important;
  }
  
  &.enterprise {
    background-color: rgba(139, 69, 19, 0.3) !important; /* Brown */
  }

  &.hourly-project {
    background-color: rgba(156, 39, 176, 0.3) !important;
  }
}

/* Add keyframes for the glow animation */
@keyframes newProjectGlow {
  0% {
    box-shadow: 0 0 10px rgba(255, 215, 0, 0.7), 0 0 20px rgba(255, 67, 54, 0.5);
  }
  50% {
    box-shadow: 0 0 20px rgba(255, 215, 0, 0.9), 0 0 30px rgba(255, 67, 54, 0.7);
  }
  100% {
    box-shadow: 0 0 10px rgba(255, 215, 0, 0.7), 0 0 20px rgba(255, 67, 54, 0.5);
  }
}

@keyframes bidCountChange {
  0% {
    transform: scale(1);
    color: inherit;
  }
  50% {
    transform: scale(1.3);
    color: #f44336;
    font-weight: 900;
    text-shadow: 0 0 4px rgba(244, 67, 54, 0.5);
  }
  100% {
    transform: scale(1);
    color: inherit;
  }
}

.bid-count-changed {
  animation: bidCountChange 0.5s ease-in-out;
}

/* Recent project glow effect */
.project-card.recent-project {
  transition: box-shadow 0.3s ease-in-out;
}

/* Project card background colors */
.project-card {
  /* Base tag colors with reduced opacity for mixing */
  &.high-paying {
    background-color: rgba(255, 215, 0, 0.2) !important; /* Yellow for PAY */
  }
  
  &.urgent {
    background-color: rgba(244, 67, 54, 0.2) !important; /* Red for URG */
  }
  
  &.authentic {
    background-color: rgba(0, 188, 212, 0.2) !important; /* Cyan for AUTH */
  }
  
  &.german {
    background-color: rgba(255, 152, 0, 0.2) !important; /* Orange for GER */
  }
  
  &.enterprise {
    background-color: rgba(0, 0, 139, 0.2) !important; /* Dark Blue for CORP */
  }

  &.hourly-project {
    background-color: rgba(156, 39, 176, 0.2) !important; /* Purple for HR */
  }

  &.new-project {
    position: relative;
    
    &::before {
      content: '';
      position: absolute;
      top: -3px;
      left: -3px;
      right: -3px;
      bottom: -3px;
      border-radius: 4px;
      z-index: -1;
      animation: newProjectGlow 2s ease-in-out infinite;
      opacity: var(--glow-opacity, 1);
      transition: opacity 1s ease-out;
    }
  }
}

/* Dark theme adjustments - All tags with bright white text */
.dark-theme .metric.flag-tag {
  color: #ffffff !important; /* Knallweiß für alle Tags */
  
  &.hr {
    background-color: #9c27b0 !important; /* Purple */
    color: #ffffff !important;
  }

  &.pay {
    background-color: #ffd700 !important; /* Yellow */
    color: #ffffff !important; /* Knallweiß statt schwarz */
  }

  &.urg {
    background-color: #f44336 !important; /* Red */
    color: #ffffff !important;
  }

  &.auth {
    background-color: #00bcd4 !important; /* Cyan */
    color: #ffffff !important;
  }

  &.germ {
    background-color: #ff9800 !important; /* Orange */
    color: #ffffff !important;
  }

  &.corp {
    background-color: #8B4513 !important; /* Brown */
    color: #ffffff !important;
  }

  &.corr {
    background-color: #00CED1 !important; /* Turquoise */
    color: #ffffff !important;
  }

  &.rep {
    background-color: #800080 !important; /* Purple */
    color: #ffffff !important;
  }

  &.qual {
    background-color: #2E7D32 !important; /* Dark green for QUAL */
    border: 2px solid #1B5E20 !important;
    font-weight: bold !important;
    color: #ffffff !important;
  }

  &.lang {
    background-color: #667eea !important; /* Blue-purple gradient start */
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: #ffffff !important;
    font-weight: bold !important;
    font-size: 0.75em !important;
  }
}

/* Project-specific bid count overlay styles */
.project-bid-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: transparent;
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10;
  border-radius: 2px;
  pointer-events: none;
}

.bid-overlay-content {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
}

.bid-overlay-number {
  font-size: 3rem;
  font-weight: 900;
  color: #132e49;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), 0 0 8px rgba(255, 255, 255, 0.5);
  padding: 8px 16px;
  border-radius: 8px;
  animation: bidNumberFadeOut 2s ease-in-out forwards;
  letter-spacing: 1px;
}

.dark-theme .bid-overlay-number {
  background-color: rgba(26, 26, 26, 0.9);
  color: #ff6666;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), 0 0 8px rgba(255, 102, 102, 0.6);
}

@keyframes bidNumberFadeOut {
  0% { 
    transform: scale(1.3); 
    opacity: 1;
  }
  30% { 
    transform: scale(1.1); 
    opacity: 1;
  }
  70% { 
    transform: scale(1); 
    opacity: 0.8;
  }
  100% { 
    transform: scale(0.9); 
    opacity: 0;
  }
}

/* Update existing bid count change animation */
.bid-count-changed {
  animation: bidCountChange 0.5s ease-in-out;
}

@keyframes bidCountChange {
  0% {
    transform: scale(1);
    color: inherit;
  }
  50% {
    transform: scale(1.3);
    color: #f44336;
    font-weight: 900;
    text-shadow: 0 0 4px rgba(244, 67, 54, 0.5);
  }
  100% {
    transform: scale(1);
    color: inherit;
  }
}

.action-button.question {
  background-color: #9c27b0;
}

.action-button.question:hover {
  background-color: #7b1fa2;
}

.action-button.send-application {
  background-color: #4caf50;
}

.action-button.send-application:hover {
  background-color: #45a049;
}

.action-button.send-application.clicked {
  background-color: #388e3c;
  border: 2px solid #2e7d32;
}

.dark-theme .action-button.send-application {
  background-color: #66bb6a;
  color: #1b5e20;
}

.dark-theme .action-button.send-application:hover {
  background-color: #4caf50;
}

.dark-theme .action-button.send-application.clicked {
  background-color: #388e3c;
  border: 2px solid #2e7d32;
}

.action-button.send-application.manual-required {
  background-color: #ff9800;
  color: white;
}

.action-button.send-application.manual-required:hover {
  background-color: #f57c00;
}

.action-button.send-application.disabled {
  background-color: #4caf50;
  opacity: 0.8;
  cursor: default;
  pointer-events: none;
}

.action-button.send-application.disabled:hover {
  background-color: #4caf50;
  transform: none;
  box-shadow: none;
}

.dark-theme .action-button.send-application {
  background-color: #66bb6a;
  color: #1b5e20;
}

.dark-theme .action-button.send-application:hover {
  background-color: #4caf50;
}

.dark-theme .action-button.send-application.clicked {
  background-color: #388e3c;
  border: 2px solid #2e7d32;
}

.dark-theme .action-button.send-application.manual-required {
  background-color: #ff9800;
  color: white;
}

.dark-theme .action-button.send-application.manual-required:hover {
  background-color: #f57c00;
}

.dark-theme .action-button.send-application.disabled {
  background-color: #4caf50;
  opacity: 0.8;
}

/* Send Question Button Styles */
.action-button.send-question {
  background-color: #757575;
}

.action-button.send-question:hover {
  background-color: #616161;
}

.action-button.send-question.clicked {
  background-color: #4caf50;
  border: 2px solid #388e3c;
}

.action-button.send-question.loading {
  opacity: 0.7;
  cursor: default;
  pointer-events: none;
}

.action-button.send-question.loading:hover {
  background-color: #757575;
  transform: none;
  box-shadow: none;
}

.action-button.send-question.disabled {
  background-color: #4caf50;
  opacity: 0.8;
  cursor: default;
  pointer-events: none;
}

.action-button.send-question.disabled:hover {
  background-color: #4caf50;
  transform: none;
  box-shadow: none;
}

/* Dark theme styles for send-question */
.dark-theme .action-button.send-question {
  background-color: #616161;
  color: #fff;
}

.dark-theme .action-button.send-question:hover {
  background-color: #757575;
}

.dark-theme .action-button.send-question.clicked {
  background-color: #4caf50;
  border: 2px solid #388e3c;
}

.dark-theme .action-button.send-question.loading {
  background-color: #616161;
  opacity: 0.7;
}

.dark-theme .action-button.send-question.disabled {
  background-color: #4caf50;
  opacity: 0.8;
}

/* Automatic Bidding Checkbox Styles */
.auto-bidding-control {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 16px;
  height: 32px; /* Fixed height for consistent alignment */
  padding: 4px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
  transition: all 0.3s ease;
}

.auto-bidding-control:hover {
  background: rgba(255, 255, 255, 0.15);
}

.dark-theme .auto-bidding-control {
  background: rgba(0, 0, 0, 0.2);
}

.dark-theme .auto-bidding-control:hover {
  background: rgba(0, 0, 0, 0.3);
}

.auto-bidding-checkbox {
  appearance: none;
  width: 20px;
  height: 20px;
  border: 2px solid #ccc;
  border-radius: 4px;
  background-color: #fff;
  cursor: pointer;
  position: relative;
  transition: all 0.3s ease;
}

.auto-bidding-checkbox:checked {
  background-color: #4caf50;
  border-color: #4caf50;
}

.auto-bidding-checkbox:checked::after {
  content: '✓';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 14px;
  font-weight: bold;
}

.checkbox-text {
  font-size: 0.9em;
  color: #333;
  font-weight: 500;
  user-select: none;
  cursor: pointer;
  line-height: 1.2;
  white-space: nowrap;
}

.auto-bidding-label {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 100%;
  cursor: pointer;
}

.bidding-icon {
  font-size: 1.1em;
  color: #4caf50;
  animation: pulse 2s infinite;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.6; }
  100% { opacity: 1; }
}

/* Dark theme styles for automatic bidding */
.dark-theme .auto-bidding-checkbox {
  border-color: #555;
  background-color: #2a2a2a;
}

.dark-theme .auto-bidding-checkbox:checked {
  background-color: #4caf50;
  border-color: #4caf50;
}

.dark-theme .checkbox-text {
  color: #e0e0e0;
}

/* Tag Filters Styles */
.tag-filters-container {
  position: relative;
  display: inline-block;
  margin-right: 16px;
}

.filters-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.9em;
  color: #333;
}

.filters-toggle:hover {
  background: #e8e8e8;
  border-color: #bbb;
}

.filters-toggle.active {
  background: #4caf50;
  color: white;
  border-color: #45a049;
}

.filter-count {
  background: rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 10px;
  padding: 2px 6px;
  font-size: 0.8em;
  font-weight: bold;
  min-width: 18px;
  text-align: center;
}

.tag-filters-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 280px;
  max-width: 400px;
  margin-top: 4px;
}

.filter-section {
  padding: 16px;
  border-bottom: 1px solid #eee;
}

.filter-section h4 {
  margin: 0 0 12px 0;
  color: #333;
  font-size: 1em;
  font-weight: 600;
}

.tag-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.tag-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  font-size: 0.85em;
}

.tag-option:hover {
  background: #f8f9fa;
}

.tag-option input[type="checkbox"] {
  display: none;
}

.tag-checkbox {
  width: 16px;
  height: 16px;
  border: 2px solid #ddd;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 10px;
  color: white;
  font-weight: bold;
}

.tag-option input[type="checkbox"]:checked + .tag-checkbox {
  border-color: transparent;
}

/* Tag-specific colors for checkboxes */
.tag-checkbox.hr {
  background-color: #9c27b0;
}

.tag-checkbox.pay {
  background-color: #ffd700;
  color: black;
}

.tag-checkbox.urg {
  background-color: #f44336;
}

.tag-checkbox.auth {
  background-color: #00bcd4;
}

.tag-checkbox.germ {
  background-color: #ff9800;
}

.tag-checkbox.corp {
  background-color: #2196f3;
}

.tag-checkbox.corr {
  background-color: #00CED1;
}

.tag-checkbox.rep {
  background-color: #87CEFA;
}

.tag-checkbox.qual {
  background-color: #2E7D32;
}

.tag-option input[type="checkbox"]:checked + .tag-checkbox::after {
  content: '✓';
}

.tag-label {
  font-weight: 500;
  color: #333;
  flex: 1;
}

.tag-count {
  font-size: 0.8em;
  color: #666;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
}

.filter-actions {
  padding: 12px 16px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.clear-filters, .close-filters {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 0.85em;
  transition: all 0.2s ease;
}

.clear-filters {
  color: #f44336;
  border-color: #f44336;
}

.clear-filters:hover {
  background: #f44336;
  color: white;
}

.close-filters {
  color: #666;
}

.close-filters:hover {
  background: #f0f0f0;
}

/* Dark theme support for tag filters */
.dark-theme .filters-toggle {
  background: #2a2a2a;
  border-color: #444;
  color: #e0e0e0;
}

.dark-theme .filters-toggle:hover {
  background: #333;
  border-color: #555;
}

.dark-theme .tag-filters-dropdown {
  background: #2a2a2a;
  border-color: #444;
}

.dark-theme .filter-section {
  border-bottom-color: #444;
}

.dark-theme .filter-section h4 {
  color: #e0e0e0;
}

.dark-theme .tag-option:hover {
  background: #333;
}

.dark-theme .tag-label {
  color: #e0e0e0;
}

.dark-theme .tag-count {
  background: #333;
  color: #ccc;
}

.dark-theme .clear-filters,
.dark-theme .close-filters {
  background: #2a2a2a;
  border-color: #444;
  color: #e0e0e0;
}

.dark-theme .clear-filters {
  border-color: #f44336;
  color: #f44336;
}

.dark-theme .clear-filters:hover {
  background: #f44336;
  color: white;
}

.dark-theme .close-filters:hover {
  background: #333;
}

/* Auto-bidding active state - pink border for projects being processed */
.project-card.auto-bidding-active {
  border: 3px solid #e91e63 !important; /* Pink border */
  box-shadow: 0 0 15px rgba(233, 30, 99, 0.5) !important;
  animation: autoBiddingPulse 2s ease-in-out infinite !important;
  position: relative;
  z-index: 10; /* Ensure it's above other elements */
}

.dark-theme .project-card.auto-bidding-active {
  border: 3px solid #e91e63 !important; /* Pink border */
  box-shadow: 0 0 15px rgba(233, 30, 99, 0.7) !important;
  animation: autoBiddingPulse 2s ease-in-out infinite !important;
}

@keyframes autoBiddingPulse {
  0% {
    box-shadow: 0 0 15px rgba(233, 30, 99, 0.5);
    border-color: #e91e63;
  }
  50% {
    box-shadow: 0 0 25px rgba(233, 30, 99, 0.9);
    border-color: #ff4081;
  }
  100% {
    box-shadow: 0 0 15px rgba(233, 30, 99, 0.5);
    border-color: #e91e63;
  }
}

/* Special case for dark theme */
.dark-theme .project-card.auto-bidding-active {
  animation: autoBiddingPulseDark 2s ease-in-out infinite !important;
}

@keyframes autoBiddingPulseDark {
  0% {
    box-shadow: 0 0 15px rgba(233, 30, 99, 0.7);
    border-color: #e91e63;
  }
  50% {
    box-shadow: 0 0 30px rgba(233, 30, 99, 1.0);
    border-color: #ff4081;
  }
  100% {
    box-shadow: 0 0 15px rgba(233, 30, 99, 0.7);
    border-color: #e91e63;
  }
}

.auto-bid-debug {
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
  height: 32px;
  width: 32px;
}

.auto-bid-debug:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.dark-theme .auto-bid-debug {
  color: #fff;
}

.dark-theme .auto-bid-debug:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.auto-bid-debug-panel {
  position: fixed;
  top: 80px;
  left: 20px;
  width: 400px;
  max-height: 60vh;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  font-size: 0.9em;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dark-theme .auto-bid-debug-panel {
  background: #2a2a2a;
  border-color: #444;
  color: #fff;
}

.debug-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.debug-section {
  padding: 8px 12px;
  border-bottom: 1px solid #e0e0e0;
}

.debug-section.log-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-bottom: none;
}

.dark-theme .debug-section {
  border-bottom-color: #444;
}

.log-container {
  flex: 1;
  overflow-y: auto;
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 8px;
  margin: 8px 0;
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  min-height: 100px;
  max-height: calc(100vh - 200px); /* Prevent console from getting too tall */
  scrollbar-width: thin;
  scrollbar-color: #ccc #f8f9fa;
}

/* Custom scrollbar for WebKit browsers */
.log-container::-webkit-scrollbar {
  width: 8px;
}

.log-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: #999;
}

.dark-theme .log-container {
  background: #1a1a1a;
  border-color: #444;
  color: #e0e0e0;
  scrollbar-color: #666 #1a1a1a;
}

/* Dark theme scrollbar for WebKit browsers */
.dark-theme .log-container::-webkit-scrollbar-track {
  background: #2a2a2a;
}

.dark-theme .log-container::-webkit-scrollbar-thumb {
  background: #666;
}

.dark-theme .log-container::-webkit-scrollbar-thumb:hover {
  background: #888;
}

.project-link {
  color: #007bff;
  text-decoration: none;
  font-weight: bold;
}

.project-link:hover {
  text-decoration: underline;
}

.dark-theme .project-link {
  color: #66b3ff;
}

.resizable-console {
  position: relative;
  min-width: 300px;
  min-height: 200px;
}

.resize-handle {
  position: absolute;
  opacity: 0.6;
  transition: opacity 0.2s ease;
}

.resize-handle:hover {
  opacity: 1;
}

.resize-handle.resize-right {
  right: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: ew-resize;
  background: linear-gradient(to right, transparent, #ccc);
}

.resize-handle.resize-bottom {
  bottom: 0;
  left: 0;
  right: 0;
  height: 4px;
  cursor: ns-resize;
  background: linear-gradient(to bottom, transparent, #ccc);
}

.resize-handle.resize-corner {
  right: 0;
  bottom: 0;
  width: 12px;
  height: 12px;
  cursor: nw-resize;
  background: linear-gradient(135deg, transparent 30%, #ccc 30%, #ccc 70%, transparent 70%);
}

.dark-theme .resize-handle.resize-right {
  background: linear-gradient(to right, transparent, #666);
}

.dark-theme .resize-handle.resize-bottom {
  background: linear-gradient(to bottom, transparent, #666);
}

.dark-theme .resize-handle.resize-corner {
  background: linear-gradient(135deg, transparent 30%, #666 30%, #666 70%, transparent 70%);
}

.dark-theme .resize-handle.resize-corner {
  background: linear-gradient(135deg, transparent 30%, #666 30%, #666 70%, transparent 70%);
}

.log-entry {
  padding: 2px 0;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.dark-theme .log-entry {
  border-bottom-color: #333;
}

.log-time {
  color: #666;
  font-size: 0.8em;
  white-space: nowrap;
  min-width: 60px;
}

.dark-theme .log-time {
  color: #999;
}

.log-message {
  flex: 1;
  word-wrap: break-word;
}

.log-entry.info .log-message {
  color: #0066cc;
}

.log-entry.success .log-message {
  color: #00aa00;
}

.log-entry.warning .log-message {
  color: #ff8800;
}

.log-entry.error .log-message {
  color: #cc0000;
}

.dark-theme .log-entry.info .log-message {
  color: #3399ff;
}

.dark-theme .log-entry.success .log-message {
  color: #00cc00;
}

.dark-theme .log-entry.warning .log-message {
  color: #ffaa00;
}

.dark-theme .log-entry.error .log-message {
  color: #ff3333;
}

/* New log highlighting */
.log-entry.new-log {
  background-color: rgba(144, 238, 144, 0.2); /* Light green background */
  border-left: 3px solid #90ee90;
  animation: newLogPulse 2s ease-in-out;
}

.dark-theme .log-entry.new-log {
  background-color: rgba(144, 238, 144, 0.15); /* Slightly darker green for dark theme */
  border-left-color: #90ee90;
}

@keyframes newLogPulse {
  0% {
    background-color: rgba(144, 238, 144, 0.4);
  }
  100% {
    background-color: rgba(144, 238, 144, 0.2);
  }
}

.dark-theme @keyframes newLogPulse {
  0% {
    background-color: rgba(144, 238, 144, 0.3);
  }
  100% {
    background-color: rgba(144, 238, 144, 0.15);
  }
}

/* Log source styling */
.log-source {
  color: #666;
  font-size: 0.75em;
  font-weight: bold;
  background-color: #f0f0f0;
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
}

.dark-theme .log-source {
  color: #aaa;
  background-color: #333;
}

/* Draggable console styles */
.draggable-console {
  user-select: none;
  transition: box-shadow 0.2s ease;
}

.draggable-console.dragging {
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
  cursor: move;
}

.drag-handle {
  user-select: none;
  cursor: move;
}

.drag-handle:active {
  cursor: move;
}
</style>