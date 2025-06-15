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

      <!-- Projects Section -->
      <div v-if="activeTab === 'projects'" class="content-section">
        <div class="section-header">
          <h2>📋 Projects Management</h2>
          <button @click="showCreateProjectForm" class="btn-primary">
            ➕ Add Project
          </button>
        </div>

        <div class="data-table">
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Status</th>
                <th>Type</th>
                <th>Budget</th>
                <th>Country</th>
                <th>Files</th>
                <th>Tags</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="project in projects" :key="project.id">
                <td><strong>{{ project.title }}</strong></td>
                <td>
                  <span :class="'badge-' + project.status">
                    {{ project.status }}
                  </span>
                </td>
                <td>{{ project.project_type }}</td>
                <td>
                  <span v-if="project.budget_min || project.budget_max">
                    {{ project.budget_min ? '$' + project.budget_min : '' }}
                    {{ project.budget_min && project.budget_max ? ' - ' : '' }}
                    {{ project.budget_max ? '$' + project.budget_max : '' }}
                    {{ project.currency_code }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td>{{ project.country || '-' }}</td>
                <td>
                  <span class="files-count">{{ project.files ? project.files.length : 0 }}</span>
                </td>
                <td>
                  <div class="tags">
                    <span v-for="tag in project.tags" :key="tag.id" class="tag">
                      {{ tag.name }}
                    </span>
                  </div>
                </td>
                <td class="actions">
                  <button @click="editProject(project)" class="btn-edit">✏️</button>
                  <button @click="showProjectFiles(project)" class="btn-secondary">📁</button>
                  <button @click="deleteProjectItem(project)" class="btn-delete">🗑️</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
              </div>
      </div>

      <!-- Customers Section -->
      <div v-if="activeTab === 'customers'" class="content-section">
        <div class="section-header">
          <h2>👥 Customer Management</h2>
          <button @click="showCreateCustomerForm" class="btn-primary">
            ➕ Add Customer
          </button>
        </div>

        <div class="data-table">
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Contact Person</th>
                <th>Email</th>
                <th>Phone</th>
                <th>City</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="customer in customers" :key="customer.id">
                <td><strong>{{ customer.company_name }}</strong></td>
                <td>{{ customer.contact_person || '-' }}</td>
                <td>{{ customer.email || '-' }}</td>
                <td>{{ customer.phone || '-' }}</td>
                <td>{{ customer.city || '-' }}</td>
                <td>
                  <span :class="`badge-${customer.status}`">
                    {{ customer.status }}
                  </span>
                </td>
                <td class="actions">
                  <button @click="editCustomer(customer)" class="btn-edit">✏️</button>
                  <button @click="showCustomerProjects(customer)" class="btn-secondary">📋</button>
                  <button @click="deleteCustomerItem(customer)" class="btn-delete">🗑️</button>
                </td>
              </tr>
            </tbody>
          </table>
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

    <!-- Project Form Modal -->
    <div v-if="showProjectModal" class="modal-overlay" @click="closeModals">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ editingProject ? 'Edit' : 'Create' }} Project</h3>
          <button @click="closeModals" class="btn-close">✕</button>
        </div>
        <form @submit.prevent="saveProject" class="modal-form">
          <div class="form-row">
            <div class="form-group">
              <label>Title *</label>
              <input v-model="projectForm.title" type="text" required>
            </div>
            <div class="form-group">
              <label>Status</label>
              <select v-model="projectForm.status">
                <option value="planning">Planning</option>
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="on_hold">On Hold</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label>Project Type</label>
              <select v-model="projectForm.project_type">
                <option value="hourly">Hourly</option>
                <option value="fixed">Fixed Price</option>
              </select>
            </div>
            <div class="form-group">
              <label>Customer</label>
              <select v-model="projectForm.customer_id">
                <option value="">No Customer</option>
                <option v-for="customer in customers" :key="customer.id" :value="customer.id">
                  {{ customer.company_name }}
                </option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>Country</label>
            <input v-model="projectForm.country" type="text">
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Budget Min</label>
              <input v-model="projectForm.budget_min" type="number" step="0.01">
            </div>
            <div class="form-group">
              <label>Budget Max</label>
              <input v-model="projectForm.budget_max" type="number" step="0.01">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Currency</label>
              <select v-model="projectForm.currency_code">
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
                <option value="CHF">CHF</option>
              </select>
            </div>
            <div class="form-group">
              <label>Start Date</label>
              <input v-model="projectForm.start_date" type="date">
            </div>
          </div>

          <div class="form-group">
            <label>End Date</label>
            <input v-model="projectForm.end_date" type="date">
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea v-model="projectForm.description" rows="4"></textarea>
          </div>

          <div class="form-group">
            <label>Internal Notes</label>
            <textarea v-model="projectForm.internal_notes" rows="3" placeholder="Internal notes for project management"></textarea>
          </div>

          <div class="form-group">
            <label>Tags</label>
            <div class="tags-selector">
              <div v-for="tag in tags" :key="tag.id" class="tag-option">
                <label>
                  <input 
                    type="checkbox" 
                    :value="tag.id" 
                    v-model="projectForm.tag_ids"
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

    <!-- Project File Modal -->
    <div v-if="showProjectFileModal" class="modal-overlay" @click="closeModals">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ editingProjectFile ? 'Edit' : 'Add' }} Project File</h3>
          <button @click="closeModals" class="btn-close">✕</button>
        </div>
        <form @submit.prevent="saveProjectFile" class="modal-form">
          <div class="form-row">
            <div class="form-group">
              <label>File Name *</label>
              <input v-model="projectFileForm.file_name" type="text" required>
            </div>
            <div class="form-group">
              <label>File Type</label>
              <input v-model="projectFileForm.file_type" type="text" placeholder="e.g. PDF, DOCX, etc.">
            </div>
          </div>
          
          <div class="form-group">
            <label>File Path</label>
            <input v-model="projectFileForm.file_path" type="text" placeholder="Path to file">
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea v-model="projectFileForm.description" rows="3"></textarea>
          </div>

          <div class="form-group">
            <label>
              <input v-model="projectFileForm.is_communication" type="checkbox">
              Communication File
            </label>
          </div>

          <div class="form-group">
            <label>Tags</label>
            <div class="tags-selector">
              <div v-for="tag in tags" :key="tag.id" class="tag-option">
                <label>
                  <input 
                    type="checkbox" 
                    :value="tag.id" 
                    v-model="projectFileForm.tag_ids"
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

    <!-- Customer Form Modal -->
    <div v-if="showCustomerModal" class="modal-overlay" @click="closeModals">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ editingCustomer ? 'Edit' : 'Create' }} Customer</h3>
          <button @click="closeModals" class="btn-close">✕</button>
        </div>
        <form @submit.prevent="saveCustomer" class="modal-form">
          <div class="form-row">
            <div class="form-group">
              <label>Company Name *</label>
              <input v-model="customerForm.company_name" type="text" required>
            </div>
            <div class="form-group">
              <label>Contact Person</label>
              <input v-model="customerForm.contact_person" type="text">
            </div>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label>Email</label>
              <input v-model="customerForm.email" type="email">
            </div>
            <div class="form-group">
              <label>Phone</label>
              <input v-model="customerForm.phone" type="tel">
            </div>
          </div>

          <div class="form-group">
            <label>Address Line 1</label>
            <input v-model="customerForm.address_line1" type="text">
          </div>

          <div class="form-group">
            <label>Address Line 2</label>
            <input v-model="customerForm.address_line2" type="text">
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>City</label>
              <input v-model="customerForm.city" type="text">
            </div>
            <div class="form-group">
              <label>State</label>
              <input v-model="customerForm.state" type="text">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Postal Code</label>
              <input v-model="customerForm.postal_code" type="text">
            </div>
            <div class="form-group">
              <label>Country</label>
              <input v-model="customerForm.country" type="text">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Tax ID</label>
              <input v-model="customerForm.tax_id" type="text">
            </div>
            <div class="form-group">
              <label>Website</label>
              <input v-model="customerForm.website" type="url">
            </div>
          </div>

          <div class="form-group">
            <label>Status</label>
            <select v-model="customerForm.status">
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="potential">Potential</option>
            </select>
          </div>

          <div class="form-group">
            <label>Notes</label>
            <textarea v-model="customerForm.notes" rows="4"></textarea>
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

    <!-- Customer Projects Modal -->
    <div v-if="showCustomerProjectsModal" class="modal-overlay" @click="closeModals">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h3>Projects for {{ selectedCustomer?.company_name }}</h3>
          <button @click="closeModals" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <div v-if="customerProjects.length === 0" class="empty-state">
            <p>No projects found for this customer.</p>
          </div>
          <div v-else class="data-table">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Type</th>
                  <th>Budget</th>
                  <th>Files</th>
                  <th>Tags</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="project in customerProjects" :key="project.id">
                  <td><strong>{{ project.title }}</strong></td>
                  <td>
                    <span :class="`badge-${project.status}`">
                      {{ project.status }}
                    </span>
                  </td>
                  <td>{{ project.project_type }}</td>
                  <td>
                    <span v-if="project.budget_min || project.budget_max">
                      {{ project.budget_min }}-{{ project.budget_max }} {{ project.currency_code }}
                    </span>
                    <span v-else>-</span>
                  </td>
                  <td>
                    <span class="files-count">{{ project.file_count }}</span>
                  </td>
                  <td>
                    <div class="tags">
                      <span v-for="tag in project.tags" :key="tag.id" class="tag">
                        {{ tag.name }}
                      </span>
                    </div>
                  </td>
                  <td>{{ new Date(project.created_at).toLocaleDateString() }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
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
      projects: [],
      customers: [],
      
      // Modal states
      showEmploymentModal: false,
      showEducationModal: false,
      showTagModal: false,
      showDomainModal: false,
      showProjectModal: false,
      showProjectFileModal: false,
      showCustomerModal: false,
      showCustomerProjectsModal: false,
      
      // Edit flags
      editingEmployment: null,
      editingEducation: null,
      editingTag: null,
      editingDomain: null,
      editingProject: null,
      editingProjectFile: null,
      editingCustomer: null,
      selectedProject: null,
      selectedCustomer: null,
      customerProjects: [],
      
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
      
      projectForm: {
        title: '',
        description: '',
        status: 'planning',
        project_type: 'hourly',
        budget_min: '',
        budget_max: '',
        currency_code: 'USD',
        country: '',
        internal_notes: '',
        start_date: '',
        end_date: '',
        customer_id: '',
        tag_ids: []
      },
      
      projectFileForm: {
        file_name: '',
        file_path: '',
        file_type: '',
        description: '',
        is_communication: false,
        tag_ids: []
      },
      
      customerForm: {
        company_name: '',
        contact_person: '',
        email: '',
        phone: '',
        address_line1: '',
        address_line2: '',
        city: '',
        state: '',
        postal_code: '',
        country: '',
        tax_id: '',
        website: '',
        notes: '',
        status: 'active'
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
        { id: 'domains', label: 'Domains', icon: '🌐', count: this.domains.length },
        { id: 'projects', label: 'Projects', icon: '📋', count: this.projects.length },
        { id: 'customers', label: 'Customers', icon: '👥', count: this.customers.length }
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
          this.loadDomains(),
          this.loadProjects(),
          this.loadCustomers()
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
      this.showProjectModal = false
      this.showProjectFileModal = false
      this.showCustomerModal = false
      this.showCustomerProjectsModal = false
      this.editingEmployment = null
      this.editingEducation = null
      this.editingTag = null
      this.editingDomain = null
      this.editingProject = null
      this.editingProjectFile = null
      this.editingCustomer = null
      this.selectedProject = null
      this.selectedCustomer = null
      this.customerProjects = []
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
    },

    // Projects methods
    async loadProjects() {
      const response = await axios.get('/api/admin/projects');
      this.projects = response.data;
    },

    showCreateProjectForm() {
      this.editingProject = null;
      this.projectForm = {
        title: '',
        description: '',
        status: 'planning',
        project_type: 'hourly',
        budget_min: '',
        budget_max: '',
        currency_code: 'USD',
        country: '',
        internal_notes: '',
        start_date: '',
        end_date: '',
        customer_id: '',
        tag_ids: []
      };
      this.showProjectModal = true;
    },

    editProject(project) {
      this.editingProject = project;
      this.projectForm = {
        title: project.title,
        description: project.description,
        status: project.status,
        project_type: project.project_type,
        budget_min: project.budget_min,
        budget_max: project.budget_max,
        currency_code: project.currency_code,
        country: project.country,
        internal_notes: project.internal_notes,
        start_date: project.start_date,
        end_date: project.end_date,
        customer_id: project.customer_id || '',
        tag_ids: project.tags ? project.tags.map(tag => tag.id) : []
      };
      this.showProjectModal = true;
    },

    async saveProject() {
      this.saving = true;
      try {
        if (this.editingProject) {
          await axios.put(`/api/admin/projects/${this.editingProject.id}`, this.projectForm);
        } else {
          await axios.post('/api/admin/projects', this.projectForm);
        }
        await this.loadProjects();
        this.closeModals();
      } catch (error) {
        console.error('Error saving project:', error);
        alert('Error saving project: ' + error.message);
      } finally {
        this.saving = false;
      }
    },

    async deleteProjectItem(project) {
      if (confirm(`Delete project "${project.title}"?`)) {
        try {
          await axios.delete(`/api/admin/projects/${project.id}`);
          await this.loadProjects();
        } catch (error) {
          console.error('Error deleting project:', error);
          alert('Error deleting project: ' + error.message);
        }
      }
    },

    showProjectFiles(project) {
      this.selectedProject = project;
      // Could open a file management view here
      alert(`Project "${project.title}" has ${project.files ? project.files.length : 0} files`);
    },

    showCreateProjectFileForm(project) {
      this.selectedProject = project;
      this.editingProjectFile = null;
      this.projectFileForm = {
        file_name: '',
        file_path: '',
        file_type: '',
        description: '',
        is_communication: false,
        tag_ids: []
      };
      this.showProjectFileModal = true;
    },

    async saveProjectFile() {
      this.saving = true;
      try {
        if (this.editingProjectFile) {
          await axios.put(`/api/admin/projects/files/${this.editingProjectFile.id}`, this.projectFileForm);
        } else {
          await axios.post(`/api/admin/projects/${this.selectedProject.id}/files`, this.projectFileForm);
        }
        await this.loadProjects();
        this.closeModals();
      } catch (error) {
        console.error('Error saving project file:', error);
        alert('Error saving project file: ' + error.message);
      } finally {
        this.saving = false;
      }
    },

    // Customer methods
    async loadCustomers() {
      const response = await axios.get('/api/admin/customers');
      this.customers = response.data;
    },

    showCreateCustomerForm() {
      this.editingCustomer = null;
      this.customerForm = {
        company_name: '',
        contact_person: '',
        email: '',
        phone: '',
        address_line1: '',
        address_line2: '',
        city: '',
        state: '',
        postal_code: '',
        country: '',
        tax_id: '',
        website: '',
        notes: '',
        status: 'active'
      };
      this.showCustomerModal = true;
    },

    editCustomer(customer) {
      this.editingCustomer = customer;
      this.customerForm = { ...customer };
      this.showCustomerModal = true;
    },

    async saveCustomer() {
      this.saving = true;
      try {
        if (this.editingCustomer) {
          await axios.put(`/api/admin/customers/${this.editingCustomer.id}`, this.customerForm);
        } else {
          await axios.post('/api/admin/customers', this.customerForm);
        }
        await this.loadCustomers();
        this.closeModals();
      } catch (error) {
        console.error('Error saving customer:', error);
        alert('Error saving customer: ' + error.message);
      } finally {
        this.saving = false;
      }
    },

    async deleteCustomerItem(customer) {
      if (confirm(`Delete customer "${customer.company_name}"? This will remove the customer association from all projects but won't delete the projects themselves.`)) {
        try {
          await axios.delete(`/api/admin/customers/${customer.id}`);
          await this.loadCustomers();
        } catch (error) {
          console.error('Error deleting customer:', error);
          alert('Error deleting customer: ' + error.message);
        }
      }
    },

    async showCustomerProjects(customer) {
      this.selectedCustomer = customer;
      try {
        const response = await axios.get(`/api/admin/customers/${customer.id}/projects`);
        this.customerProjects = response.data;
        this.showCustomerProjectsModal = true;
      } catch (error) {
        console.error('Error loading customer projects:', error);
        alert('Error loading customer projects: ' + error.message);
      }
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

.badge-planning {
  background: #fff3cd;
  color: #856404;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.badge-active {
  background: #d4edda;
  color: #155724;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.badge-completed {
  background: #cce5ff;
  color: #004085;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.badge-on_hold {
  background: #e2e3e5;
  color: #383d41;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.badge-cancelled {
  background: #f8d7da;
  color: #721c24;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.files-count {
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: bold;
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