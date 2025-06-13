<template>
  <div class="database-admin">
    <div class="admin-header">
      <h1>🔧 Database Administration</h1>
      <p>Manage Employment, Education, Tags and Domain Data</p>
    </div>

    <!-- Navigation Tabs -->
    <div class="admin-tabs">
      <button 
        v-for="tab in tabs" 
        :key="tab.id"
        :class="['tab-button', { active: activeTab === tab.id }]"
        @click="setActiveTab(tab.id)"
      >
        {{ tab.icon }} {{ tab.label }}
        <span v-if="tab.count !== undefined" class="count-badge">{{ tab.count }}</span>
      </button>
    </div>

    <!-- Content Sections -->
    <div class="admin-content">
      
      <!-- Employment Section -->
      <div v-if="activeTab === 'employment'" class="content-section">
        <div class="section-header">
          <h2>👔 Employment Management</h2>
          <button @click="showCreateEmploymentForm" class="btn-primary">
            ➕ Add Employment
          </button>
        </div>

        <div class="data-table">
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Position</th>
                <th>Period</th>
                <th>Location</th>
                <th>Self-employed</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in employment" :key="item.id">
                <td>{{ item.company_name }}</td>
                <td>{{ item.position }}</td>
                <td>{{ item.start_date }} - {{ item.end_date || 'Present' }}</td>
                <td>{{ item.location || '-' }}</td>
                <td>
                  <span :class="item.is_self_employed ? 'badge-yes' : 'badge-no'">
                    {{ item.is_self_employed ? 'Yes' : 'No' }}
                  </span>
                </td>
                <td class="actions">
                  <button @click="editEmployment(item)" class="btn-edit">✏️</button>
                  <button @click="deleteEmploymentItem(item)" class="btn-delete">🗑️</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Education Section -->
      <div v-if="activeTab === 'education'" class="content-section">
        <div class="section-header">
          <h2>🎓 Education Management</h2>
          <button @click="showCreateEducationForm" class="btn-primary">
            ➕ Add Education
          </button>
        </div>

        <div class="data-table">
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Institution</th>
                <th>Period</th>
                <th>Type</th>
                <th>Tags</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in education" :key="item.id">
                <td>{{ item.title }}</td>
                <td>{{ item.institution || '-' }}</td>
                <td>{{ item.start_date }} - {{ item.end_date || 'Present' }}</td>
                <td>{{ item.type }}</td>
                <td>
                  <div class="tags">
                    <span v-for="tag in item.tags" :key="tag.id" class="tag">
                      {{ tag.name }}
                    </span>
                  </div>
                </td>
                <td class="actions">
                  <button @click="editEducation(item)" class="btn-edit">✏️</button>
                  <button @click="deleteEducationItem(item)" class="btn-delete">🗑️</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tags Section -->
      <div v-if="activeTab === 'tags'" class="content-section">
        <div class="section-header">
          <h2>🏷️ Tags Management</h2>
          <button @click="showCreateTagForm" class="btn-primary">
            ➕ Add Tag
          </button>
        </div>

        <div class="data-table">
          <table>
            <thead>
              <tr>
                <th>Tag Name</th>
                <th>Education Usage</th>
                <th>Domain Usage</th>
                <th>Total Usage</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tag in tags" :key="tag.id">
                <td><strong>{{ tag.tag_name }}</strong></td>
                <td>{{ tag.education_count }}</td>
                <td>{{ tag.domain_count }}</td>
                <td>{{ tag.education_count + tag.domain_count }}</td>
                <td class="actions">
                  <button @click="editTag(tag)" class="btn-edit">✏️</button>
                  <button 
                    @click="deleteTagItem(tag)" 
                    class="btn-delete"
                    :disabled="tag.education_count + tag.domain_count > 0"
                  >
                    🗑️
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Domains Section -->
      <div v-if="activeTab === 'domains'" class="content-section">
        <div class="section-header">
          <h2>🌐 Domains Management</h2>
          <div class="header-actions">
            <p class="note">Click ✏️ to edit domain details or ✕ to remove tags/subtags</p>
            <button @click="showCreateDomainForm" class="btn-primary">
              ➕ Add Domain
            </button>
          </div>
        </div>

        <div class="data-table">
          <table>
            <thead>
              <tr>
                <th>Domain</th>
                <th>Title</th>
                <th>Description</th>
                <th>Tags</th>
                <th>Subtags</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="domain in domains" :key="domain.id">
                <td><strong>{{ domain.domain_name }}</strong></td>
                <td>{{ domain.title || '-' }}</td>
                <td class="description-cell">
                  {{ domain.description ? (domain.description.length > 100 ? domain.description.substring(0, 100) + '...' : domain.description) : '-' }}
                </td>
                <td>
                  <div class="tags">
                    <span v-for="tag in domain.tags" :key="tag.id" class="tag removable">
                      {{ tag.name }}
                      <button @click="removeDomainTag(domain.id, tag.id)" class="remove-tag-btn" title="Remove tag">✕</button>
                    </span>
                    <div class="tag-input-container">
                      <input 
                        v-model="tagInputs[domain.id]"
                        @input="onTagInput(domain.id, $event.target.value)"
                        @keydown.enter="addTagToDomain(domain.id, $event.target.value)"
                        @focus="showTagSuggestions[domain.id] = true"
                        @blur="hideTagSuggestions(domain.id)"
                        class="tag-input"
                        placeholder="Add tag..."
                        type="text"
                      />
                      <div v-if="showTagSuggestions[domain.id] && tagSuggestions[domain.id] && tagSuggestions[domain.id].length" class="suggestions-dropdown">
                        <div 
                          v-for="suggestion in tagSuggestions[domain.id]" 
                          :key="suggestion.id"
                          @mousedown="addTagToDomain(domain.id, suggestion.tag_name)"
                          class="suggestion-item"
                        >
                          {{ suggestion.tag_name }}
                        </div>
                      </div>
                    </div>
                  </div>
                </td>
                <td>
                  <div class="tags">
                    <span v-for="subtag in domain.subtags" :key="subtag.id" class="tag subtag removable">
                      {{ subtag.name }}
                      <button @click="removeDomainSubtag(domain.id, subtag.id)" class="remove-tag-btn" title="Remove subtag">✕</button>
                    </span>
                    <div class="tag-input-container">
                      <input 
                        v-model="subtagInputs[domain.id]"
                        @input="onSubtagInput(domain.id, $event.target.value)"
                        @keydown.enter="addSubtagToDomain(domain.id, $event.target.value)"
                        @focus="showSubtagSuggestions[domain.id] = true"
                        @blur="hideSubtagSuggestions(domain.id)"
                        class="tag-input"
                        placeholder="Add subtag..."
                        type="text"
                      />
                      <div v-if="showSubtagSuggestions[domain.id] && subtagSuggestions[domain.id] && subtagSuggestions[domain.id].length" class="suggestions-dropdown">
                        <div 
                          v-for="suggestion in subtagSuggestions[domain.id]" 
                          :key="suggestion.id"
                          @mousedown="addSubtagToDomain(domain.id, suggestion.subtag_name)"
                          class="suggestion-item"
                        >
                          {{ suggestion.subtag_name }}
                        </div>
                      </div>
                    </div>
                  </div>
                </td>
                <td class="actions">
                  <button @click="editDomain(domain)" class="btn-edit">✏️</button>
                  <button @click="deleteDomainItem(domain)" class="btn-delete">🗑️</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Modal Forms -->
    
    <!-- Employment Form Modal -->
    <div v-if="showEmploymentModal" class="modal-overlay" @click="closeModals">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ editingEmployment ? 'Edit' : 'Create' }} Employment</h3>
          <button @click="closeModals" class="btn-close">✕</button>
        </div>
        <form @submit.prevent="saveEmployment" class="modal-form">
          <div class="form-row">
            <div class="form-group">
              <label>Company Name *</label>
              <input v-model="employmentForm.company_name" type="text" required>
            </div>
            <div class="form-group">
              <label>Position *</label>
              <input v-model="employmentForm.position" type="text" required>
            </div>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label>Start Date *</label>
              <input v-model="employmentForm.start_date" type="text" placeholder="e.g. März 2021" required>
            </div>
            <div class="form-group">
              <label>End Date</label>
              <input v-model="employmentForm.end_date" type="text" placeholder="e.g. Juli 2024 or leave empty">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Location</label>
              <input v-model="employmentForm.location" type="text" placeholder="e.g. Schweiz">
            </div>
            <div class="form-group">
              <label>
                <input v-model="employmentForm.is_self_employed" type="checkbox">
                Self-employed
              </label>
            </div>
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea v-model="employmentForm.description" rows="3"></textarea>
          </div>

          <div class="form-group">
            <label>Technologies</label>
            <textarea v-model="employmentForm.technologies" rows="2" placeholder="Separate with semicolons"></textarea>
          </div>

          <div class="form-group">
            <label>Achievements</label>
            <textarea v-model="employmentForm.achievements" rows="2" placeholder="Separate with semicolons"></textarea>
          </div>

          <div class="modal-actions">
            <button type="button" @click="closeModals" class="btn-secondary">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Education Form Modal -->
    <div v-if="showEducationModal" class="modal-overlay" @click="closeModals">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ editingEducation ? 'Edit' : 'Create' }} Education</h3>
          <button @click="closeModals" class="btn-close">✕</button>
        </div>
        <form @submit.prevent="saveEducation" class="modal-form">
          <div class="form-row">
            <div class="form-group">
              <label>Title *</label>
              <input v-model="educationForm.title" type="text" required>
            </div>
            <div class="form-group">
              <label>Institution</label>
              <input v-model="educationForm.institution" type="text">
            </div>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label>Start Date *</label>
              <input v-model="educationForm.start_date" type="text" placeholder="e.g. Feb 2020" required>
            </div>
            <div class="form-group">
              <label>End Date</label>
              <input v-model="educationForm.end_date" type="text" placeholder="e.g. Apr 2020">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Type</label>
              <select v-model="educationForm.type">
                <option value="course">Course</option>
                <option value="training">Training</option>
                <option value="workshop">Workshop</option>
                <option value="certification">Certification</option>
              </select>
            </div>
            <div class="form-group">
              <label>Duration</label>
              <input v-model="educationForm.duration" type="text" placeholder="e.g. 28 Stunden">
            </div>
          </div>

          <div class="form-group">
            <label>Location</label>
            <input v-model="educationForm.location" type="text" placeholder="e.g. Zürich">
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea v-model="educationForm.description" rows="4"></textarea>
          </div>

          <div class="form-group">
            <label>Tags</label>
            <div class="tags-selector">
              <div v-for="tag in tags" :key="tag.id" class="tag-option">
                <label>
                  <input 
                    type="checkbox" 
                    :value="tag.id" 
                    v-model="educationForm.tag_ids"
                  >
                  {{ tag.tag_name }}
                </label>
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button type="button" @click="closeModals" class="btn-secondary">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Tag Form Modal -->
    <div v-if="showTagModal" class="modal-overlay" @click="closeModals">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ editingTag ? 'Edit' : 'Create' }} Tag</h3>
          <button @click="closeModals" class="btn-close">✕</button>
        </div>
        <form @submit.prevent="saveTag" class="modal-form">
          <div class="form-group">
            <label>Tag Name *</label>
            <input v-model="tagForm.tag_name" type="text" required placeholder="e.g. Web Development">
          </div>

          <div class="modal-actions">
            <button type="button" @click="closeModals" class="btn-secondary">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Domain Form Modal -->
    <div v-if="showDomainModal" class="modal-overlay" @click="closeModals">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ editingDomain ? 'Edit' : 'Create' }} Domain</h3>
          <button @click="closeModals" class="btn-close">✕</button>
        </div>
        <form @submit.prevent="saveDomain" class="modal-form">
          <div class="form-row">
            <div class="form-group">
              <label>Domain Name *</label>
              <input v-model="domainForm.domain_name" type="text" required>
            </div>
            <div class="form-group">
              <label>Title</label>
              <input v-model="domainForm.title" type="text">
            </div>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label>Description</label>
              <textarea v-model="domainForm.description" rows="3"></textarea>
            </div>
          </div>

          <div class="form-group">
            <label>Tags</label>
            <div class="tags-selector">
              <div v-for="tag in tags" :key="tag.id" class="tag-option">
                <label>
                  <input 
                    type="checkbox" 
                    :value="tag.id" 
                    v-model="domainForm.tag_ids"
                  >
                  {{ tag.tag_name }}
                </label>
              </div>
            </div>
          </div>

          <div class="form-group">
            <label>Subtags</label>
            <div class="tags-selector">
              <div v-for="tag in tags" :key="tag.id" class="tag-option">
                <label>
                  <input 
                    type="checkbox" 
                    :value="tag.id" 
                    v-model="domainForm.subtag_ids"
                  >
                  {{ tag.tag_name }}
                </label>
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button type="button" @click="closeModals" class="btn-secondary">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'DatabaseAdmin',
  data() {
    return {
      activeTab: 'employment',
      loading: false,
      saving: false,
      
      // Data arrays
      employment: [],
      education: [],
      tags: [],
      domains: [],
      
      // Modal states
      showEmploymentModal: false,
      showEducationModal: false,
      showTagModal: false,
      showDomainModal: false,
      
      // Edit flags
      editingEmployment: null,
      editingEducation: null,
      editingTag: null,
      editingDomain: null,
      
      // Form data
      employmentForm: {
        company_name: '',
        position: '',
        start_date: '',
        end_date: '',
        description: '',
        is_self_employed: false,
        location: '',
        technologies: '',
        achievements: ''
      },
      
      educationForm: {
        title: '',
        institution: '',
        start_date: '',
        end_date: '',
        duration: '',
        description: '',
        location: '',
        type: 'course',
        tag_ids: []
      },
      
      tagForm: {
        tag_name: ''
      },
      
      domainForm: {
        domain_name: '',
        title: '',
        description: '',
        tag_ids: [],
        subtag_ids: []
      },

      tagInputs: {},
      showTagSuggestions: {},
      tagSuggestions: {},
      subtagInputs: {},
      showSubtagSuggestions: {},
      subtagSuggestions: {}
    }
  },
  
  computed: {
    tabs() {
      return [
        { id: 'employment', label: 'Employment', icon: '👔', count: this.employment.length },
        { id: 'education', label: 'Education', icon: '🎓', count: this.education.length },
        { id: 'tags', label: 'Tags', icon: '🏷️', count: this.tags.length },
        { id: 'domains', label: 'Domains', icon: '🌐', count: this.domains.length }
      ]
    }
  },
  
  async mounted() {
    await this.loadAllData()
  },
  
  methods: {
    setActiveTab(tabId) {
      this.activeTab = tabId
    },
    
    async loadAllData() {
      this.loading = true
      try {
        await Promise.all([
          this.loadEmployment(),
          this.loadEducation(), 
          this.loadTags(),
          this.loadDomains()
        ])
      } catch (error) {
        console.error('Error loading data:', error)
        alert('Error loading data: ' + error.message)
      } finally {
        this.loading = false
      }
    },
    
    async loadEmployment() {
      const response = await axios.get('/api/admin/employment')
      this.employment = response.data
    },
    
    async loadEducation() {
      const response = await axios.get('/api/admin/education')
      this.education = response.data
    },
    
    async loadTags() {
      const response = await axios.get('/api/admin/tags')
      this.tags = response.data
    },
    
    async loadDomains() {
      const response = await axios.get('/api/admin/domains')
      this.domains = response.data
    },
    
    // Employment methods
    showCreateEmploymentForm() {
      this.editingEmployment = null
      this.employmentForm = {
        company_name: '',
        position: '',
        start_date: '',
        end_date: '',
        description: '',
        is_self_employed: false,
        location: '',
        technologies: '',
        achievements: ''
      }
      this.showEmploymentModal = true
    },
    
    editEmployment(item) {
      this.editingEmployment = item
      this.employmentForm = { ...item }
      this.showEmploymentModal = true
    },
    
    async saveEmployment() {
      this.saving = true
      try {
        if (this.editingEmployment) {
          await axios.put(`/api/admin/employment/${this.editingEmployment.id}`, this.employmentForm)
        } else {
          await axios.post('/api/admin/employment', this.employmentForm)
        }
        await this.loadEmployment()
        this.closeModals()
      } catch (error) {
        console.error('Error saving employment:', error)
        alert('Error saving employment: ' + error.message)
      } finally {
        this.saving = false
      }
    },
    
    async deleteEmploymentItem(item) {
      if (confirm(`Delete employment at ${item.company_name}?`)) {
        try {
          await axios.delete(`/api/admin/employment/${item.id}`)
          await this.loadEmployment()
        } catch (error) {
          console.error('Error deleting employment:', error)
          alert('Error deleting employment: ' + error.message)
        }
      }
    },
    
    // Education methods
    showCreateEducationForm() {
      this.editingEducation = null
      this.educationForm = {
        title: '',
        institution: '',
        start_date: '',
        end_date: '',
        duration: '',
        description: '',
        location: '',
        type: 'course',
        tag_ids: []
      }
      this.showEducationModal = true
    },
    
    editEducation(item) {
      this.editingEducation = item
      this.educationForm = { 
        ...item,
        tag_ids: item.tags ? item.tags.map(tag => tag.id) : []
      }
      this.showEducationModal = true
    },
    
    async saveEducation() {
      this.saving = true
      try {
        if (this.editingEducation) {
          await axios.put(`/api/admin/education/${this.editingEducation.id}`, this.educationForm)
        } else {
          await axios.post('/api/admin/education', this.educationForm)
        }
        await this.loadEducation()
        this.closeModals()
      } catch (error) {
        console.error('Error saving education:', error)
        alert('Error saving education: ' + error.message)
      } finally {
        this.saving = false
      }
    },
    
    async deleteEducationItem(item) {
      if (confirm(`Delete education "${item.title}"?`)) {
        try {
          await axios.delete(`/api/admin/education/${item.id}`)
          await this.loadEducation()
        } catch (error) {
          console.error('Error deleting education:', error)
          alert('Error deleting education: ' + error.message)
        }
      }
    },
    
    // Tag methods
    showCreateTagForm() {
      this.editingTag = null
      this.tagForm = { tag_name: '' }
      this.showTagModal = true
    },
    
    editTag(item) {
      this.editingTag = item
      this.tagForm = { ...item }
      this.showTagModal = true
    },
    
    async saveTag() {
      this.saving = true
      try {
        if (this.editingTag) {
          await axios.put(`/api/admin/tags/${this.editingTag.id}`, this.tagForm)
        } else {
          await axios.post('/api/admin/tags', this.tagForm)
        }
        await this.loadTags()
        await this.loadEducation() // Reload to update tag counts
        this.closeModals()
      } catch (error) {
        console.error('Error saving tag:', error)
        alert('Error saving tag: ' + error.message)
      } finally {
        this.saving = false
      }
    },
    
    async deleteTagItem(item) {
      if (confirm(`Delete tag "${item.tag_name}"? This will remove it from all associated records.`)) {
        try {
          await axios.delete(`/api/admin/tags/${item.id}`)
          await this.loadTags()
          await this.loadEducation() // Reload to reflect changes
        } catch (error) {
          console.error('Error deleting tag:', error)
          alert('Error deleting tag: ' + error.message)
        }
      }
    },
    
    closeModals() {
      this.showEmploymentModal = false
      this.showEducationModal = false
      this.showTagModal = false
      this.showDomainModal = false
      this.editingEmployment = null
      this.editingEducation = null
      this.editingTag = null
      this.editingDomain = null
    },

    // Domain methods
    showCreateDomainForm() {
      this.editingDomain = null
      this.domainForm = {
        domain_name: '',
        title: '',
        description: '',
        tag_ids: [],
        subtag_ids: []
      }
      this.showDomainModal = true
    },
    
    editDomain(item) {
      this.editingDomain = item
      this.domainForm = { 
        ...item,
        tag_ids: item.tags ? item.tags.map(tag => tag.id) : [],
        subtag_ids: item.subtags ? item.subtags.map(subtag => subtag.id) : []
      }
      this.showDomainModal = true
    },
    
    async saveDomain() {
      this.saving = true
      try {
        if (this.editingDomain) {
          await axios.put(`/api/admin/domains/${this.editingDomain.id}`, this.domainForm)
        } else {
          await axios.post('/api/admin/domains', this.domainForm)
        }
        await this.loadDomains()
        this.closeModals()
      } catch (error) {
        console.error('Error saving domain:', error)
        alert('Error saving domain: ' + error.message)
      } finally {
        this.saving = false
      }
    },
    
    async deleteDomainItem(item) {
      if (confirm(`Delete domain "${item.domain_name}"?`)) {
        try {
          await axios.delete(`/api/admin/domains/${item.id}`)
          await this.loadDomains()
        } catch (error) {
          console.error('Error deleting domain:', error)
          alert('Error deleting domain: ' + error.message)
        }
      }
    },

    // New methods for domain management
    removeDomainTag(domainId, tagId) {
      if (confirm('Are you sure you want to remove this tag from the domain?')) {
        this.saving = true
        fetch(`/api/admin/domains/${domainId}/tags/${tagId}`, {
          method: 'DELETE'
        })
        .then(response => {
          if (!response.ok) {
            throw new Error('Failed to remove tag')
          }
          return response.json()
        })
        .then(() => {
          this.loadDomains() // Refresh the domains list
        })
        .catch(error => {
          console.error('Error removing tag:', error)
          alert('Error removing tag: ' + error.message)
        })
        .finally(() => {
          this.saving = false
        })
      }
    },

    removeDomainSubtag(domainId, subtagId) {
      if (confirm('Are you sure you want to remove this subtag from the domain?')) {
        this.saving = true
        fetch(`/api/admin/domains/${domainId}/subtags/${subtagId}`, {
          method: 'DELETE'
        })
        .then(response => {
          if (!response.ok) {
            throw new Error('Failed to remove subtag')
          }
          return response.json()
        })
        .then(() => {
          this.loadDomains() // Refresh the domains list
        })
        .catch(error => {
          console.error('Error removing subtag:', error)
          alert('Error removing subtag: ' + error.message)
        })
        .finally(() => {
          this.saving = false
        })
      }
    },

    async onTagInput(domainId, input) {
      if (input.length > 0) {
        try {
          const response = await axios.get(`/api/admin/tags/search?q=${encodeURIComponent(input)}`);
          this.tagSuggestions[domainId] = response.data;
        } catch (error) {
          console.error('Error searching tags:', error);
          this.tagSuggestions[domainId] = [];
        }
      } else {
        this.tagSuggestions[domainId] = [];
      }
    },

    async onSubtagInput(domainId, input) {
      if (input.length > 0) {
        try {
          const response = await axios.get(`/api/admin/subtags/search?q=${encodeURIComponent(input)}`);
          this.subtagSuggestions[domainId] = response.data;
        } catch (error) {
          console.error('Error searching subtags:', error);
          this.subtagSuggestions[domainId] = [];
        }
      } else {
        this.subtagSuggestions[domainId] = [];
      }
    },

    async addTagToDomain(domainId, tagName) {
      if (!tagName || tagName.trim() === '') return;
      
      try {
        const response = await axios.post(`/api/admin/domains/${domainId}/tags`, {
          tag_name: tagName.trim()
        });
        
        if (response.data.success) {
          // Clear input
          this.tagInputs[domainId] = '';
          this.showTagSuggestions[domainId] = false;
          
          // Refresh domains list
          await this.loadDomains();
        }
      } catch (error) {
        console.error('Error adding tag to domain:', error);
        alert('Error adding tag: ' + error.message);
      }
    },

    async addSubtagToDomain(domainId, subtagName) {
      if (!subtagName || subtagName.trim() === '') return;
      
      try {
        const response = await axios.post(`/api/admin/domains/${domainId}/subtags`, {
          subtag_name: subtagName.trim()
        });
        
        if (response.data.success) {
          // Clear input
          this.subtagInputs[domainId] = '';
          this.showSubtagSuggestions[domainId] = false;
          
          // Refresh domains list
          await this.loadDomains();
        }
      } catch (error) {
        console.error('Error adding subtag to domain:', error);
        alert('Error adding subtag: ' + error.message);
      }
    },

    hideTagSuggestions(domainId) {
      setTimeout(() => {
        this.showTagSuggestions[domainId] = false;
      }, 200); // Delay to allow click events on suggestions
    },

    hideSubtagSuggestions(domainId) {
      setTimeout(() => {
        this.showSubtagSuggestions[domainId] = false;
      }, 200); // Delay to allow click events on suggestions
    }
  }
}
</script>

<style scoped>
.database-admin {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.admin-header {
  text-align: center;
  margin-bottom: 30px;
}

.admin-header h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
  color: #2c3e50;
}

.admin-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 30px;
  border-bottom: 2px solid #eee;
}

.tab-button {
  padding: 12px 20px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 1rem;
  border-bottom: 3px solid transparent;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab-button:hover {
  background: #f8f9fa;
}

.tab-button.active {
  border-bottom-color: #007bff;
  background: #f8f9fa;
  font-weight: bold;
}

.count-badge {
  background: #007bff;
  color: white;
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 0.8rem;
  font-weight: bold;
}

.content-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}

.section-header h2 {
  margin: 0;
  color: #2c3e50;
}

.header-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.header-actions .note {
  margin: 0;
  color: #6c757d;
  font-style: italic;
  font-size: 0.9rem;
}

.description-cell {
  max-width: 300px;
  word-wrap: break-word;
}

.data-table {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #dee2e6;
}

th {
  background: #f8f9fa;
  font-weight: bold;
  color: #495057;
}

tbody tr:hover {
  background: #f8f9fa;
}

.actions {
  white-space: nowrap;
}

.btn-primary {
  background: #007bff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-secondary:hover {
  background: #545b62;
}

.btn-edit {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  margin-right: 4px;
  border-radius: 4px;
  font-size: 1.2rem;
}

.btn-edit:hover {
  background: #e3f2fd;
}

.btn-delete {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 1.2rem;
}

.btn-delete:hover {
  background: #ffebee;
}

.btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  color: #999;
}

.btn-close:hover {
  color: #333;
}

.badge-yes {
  background: #d4edda;
  color: #155724;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.badge-no {
  background: #f8d7da;
  color: #721c24;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag {
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  border: 1px solid #bbdefb;
  position: relative;
}

.tag.removable {
  padding-right: 25px; /* Make space for the remove button */
}

.remove-tag-btn {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 0.7rem;
  padding: 2px;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.remove-tag-btn:hover {
  background: rgba(0,0,0,0.1);
  color: #d32f2f;
}

.subtag {
  background: #fff3e0;
  color: #f57c00;
  border-color: #ffcc02;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #dee2e6;
}

.modal-header h3 {
  margin: 0;
  color: #2c3e50;
}

.modal-form {
  padding: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: #495057;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 0.9rem;
}

.form-group input[type="checkbox"] {
  width: auto;
  margin-right: 8px;
}

.tags-selector {
  max-height: 150px;
  overflow-y: auto;
  border: 1px solid #ced4da;
  border-radius: 4px;
  padding: 10px;
  background: #f8f9fa;
}

.tag-option {
  margin-bottom: 8px;
}

.tag-option label {
  display: flex;
  align-items: center;
  font-weight: normal;
  margin-bottom: 0;
  cursor: pointer;
}

.tag-option input[type="checkbox"] {
  margin-right: 8px;
  margin-bottom: 0;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 20px;
  border-top: 1px solid #dee2e6;
}

.tag-input-container {
  position: relative;
  display: inline-block;
  margin-top: 5px;
}

.tag-input {
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.8rem;
  width: 120px;
  background: #f9f9f9;
}

.tag-input:focus {
  outline: none;
  border-color: #007bff;
  background: white;
}

.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-top: none;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  z-index: 1000;
  max-height: 150px;
  overflow-y: auto;
}

.suggestion-item {
  padding: 8px 12px;
  cursor: pointer;
  font-size: 0.8rem;
  border-bottom: 1px solid #f0f0f0;
}

.suggestion-item:hover {
  background: #f8f9fa;
}

.suggestion-item:last-child {
  border-bottom: none;
}

@media (max-width: 768px) {
  .admin-tabs {
    flex-direction: column;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    width: 95%;
    margin: 10px;
  }
  
  .section-header {
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
  }
}
</style> 