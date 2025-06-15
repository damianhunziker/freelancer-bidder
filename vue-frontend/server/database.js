const knex = require('knex')({
  client: 'mysql2',
  connection: {
    host: 'localhost',
    user: 'root',
    password: 'dCTKBq@CV9$a50ZtpzSr@D7*7Q',
    database: 'domain_analysis'
  },
  pool: { min: 0, max: 7 }
});

// Create a separate connection for the domain_analysis database
const domainAnalysisDb = require('knex')({
  client: 'mysql2',
  connection: {
    host: 'localhost',
    user: 'root',
    password: 'dCTKBq@CV9$a50ZtpzSr@D7*7Q',
    database: 'domain_analysis'
  },
  pool: { min: 0, max: 7 }
});

/**
 * Get domain references with their associated tags and subtags
 * Uses the domain_analysis database structure with proper joins
 */
async function getDomainReferences() {
  try {
    console.log('[Debug] Fetching domains from domain_analysis database...');
    
    // Get all domains
    const domains = await domainAnalysisDb('domains')
      .select('id', 'domain_name as domain', 'title', 'description')
      .orderBy('id', 'desc');
    
    console.log(`[Debug] Found ${domains.length} domains`);
    
    // For each domain, get their associated tags through the join table
    const domainsWithData = await Promise.all(domains.map(async (domain) => {
      // Get tags for this domain
      const tagRecords = await domainAnalysisDb('domain_tags')
        .join('tags', 'domain_tags.tag_id', 'tags.id')
        .where('domain_tags.domain_id', domain.id)
        .select('tags.tag_name');
      
      // Get subtags for this domain
      const subtagRecords = await domainAnalysisDb('domain_subtags')
        .join('subtags', 'domain_subtags.subtag_id', 'subtags.id')
        .where('domain_subtags.domain_id', domain.id)
        .select('subtags.subtag_name');
      
      // Extract tag and subtag names to arrays
      const tags = tagRecords.map(record => record.tag_name);
      const subtags = subtagRecords.map(record => record.subtag_name);
      
      // Return the domain with its tags and subtags
      return {
        domain: domain.domain,
        description: domain.description || '', // Ensure description is never null
        tags: tags,
        subtags: subtags
      };
    }));
    
    console.log(`[Debug] Processed ${domainsWithData.length} domains with their tags and subtags`);
    
    return {
      references: {
        domains: domainsWithData
      }
    };
  } catch (error) {
    console.error('Error fetching domain references:', error);
    return { references: { domains: [] } };
  }
}

/**
 * Get employment history data from the database
 * Ordered by start date (newest first)
 */
async function getEmploymentHistory() {
  try {
    console.log('[Debug] Fetching employment history from database...');
    
    const employment = await domainAnalysisDb('employment')
      .select('*')
      .orderByRaw("STR_TO_DATE(CONCAT(start_date, ' 01'), '%M %Y %d') DESC, start_date DESC");
    
    console.log(`[Debug] Found ${employment.length} employment records`);
    
    return {
      employment: employment
    };
  } catch (error) {
    console.error('Error fetching employment history:', error);
    return { employment: [] };
  }
}

/**
 * Get education/training history data from the database with associated tags
 * Ordered by start date (newest first)
 */
async function getEducationHistory() {
  try {
    console.log('[Debug] Fetching education history from database...');
    
    // Get all education records
    const education = await domainAnalysisDb('education')
      .select('*')
      .orderByRaw("STR_TO_DATE(CONCAT(start_date, ' 01'), '%M %Y %d') DESC, start_date DESC");
    
    console.log(`[Debug] Found ${education.length} education records`);
    
    // For each education record, get associated tags
    const educationWithTags = await Promise.all(education.map(async (edu) => {
      const tagRecords = await domainAnalysisDb('education_tags')
        .join('tags', 'education_tags.tag_id', 'tags.id')
        .where('education_tags.education_id', edu.id)
        .select('tags.tag_name', 'tags.id');
      
      const tags = tagRecords.map(record => ({
        id: record.id,
        name: record.tag_name
      }));
      
      return {
        ...edu,
        tags: tags
      };
    }));
    
    console.log(`[Debug] Processed ${educationWithTags.length} education records with their tags`);
    
    return {
      education: educationWithTags
    };
  } catch (error) {
    console.error('Error fetching education history:', error);
    return { education: [] };
  }
}

// ========== EMPLOYMENT CRUD ==========

async function getAllEmployment() {
  try {
    const employment = await domainAnalysisDb('employment')
      .select('*')
      .orderByRaw("STR_TO_DATE(CONCAT(start_date, ' 01'), '%M %Y %d') DESC, start_date DESC");
    return employment;
  } catch (error) {
    console.error('Error fetching employment:', error);
    throw error;
  }
}

async function getEmploymentById(id) {
  try {
    const employment = await domainAnalysisDb('employment')
      .where('id', id)
      .first();
    return employment;
  } catch (error) {
    console.error('Error fetching employment by id:', error);
    throw error;
  }
}

async function createEmployment(data) {
  try {
    const [id] = await domainAnalysisDb('employment').insert(data);
    return id;
  } catch (error) {
    console.error('Error creating employment:', error);
    throw error;
  }
}

async function updateEmployment(id, data) {
  try {
    await domainAnalysisDb('employment')
      .where('id', id)
      .update(data);
    return true;
  } catch (error) {
    console.error('Error updating employment:', error);
    throw error;
  }
}

async function deleteEmployment(id) {
  try {
    await domainAnalysisDb('employment')
      .where('id', id)
      .del();
    return true;
  } catch (error) {
    console.error('Error deleting employment:', error);
    throw error;
  }
}

// ========== EDUCATION CRUD ==========

async function getAllEducation() {
  try {
    const education = await domainAnalysisDb('education')
      .select('*')
      .orderByRaw("STR_TO_DATE(CONCAT(start_date, ' 01'), '%M %Y %d') DESC, start_date DESC");
    
    // Get tags for each education record
    const educationWithTags = await Promise.all(education.map(async (edu) => {
      const tagRecords = await domainAnalysisDb('education_tags')
        .join('tags', 'education_tags.tag_id', 'tags.id')
        .where('education_tags.education_id', edu.id)
        .select('tags.tag_name', 'tags.id');
      
      const tags = tagRecords.map(record => ({
        id: record.id,
        name: record.tag_name
      }));
      
      return {
        ...edu,
        tags: tags
      };
    }));
    
    return educationWithTags;
  } catch (error) {
    console.error('Error fetching education:', error);
    throw error;
  }
}

async function getEducationById(id) {
  try {
    const education = await domainAnalysisDb('education')
      .where('id', id)
      .first();
    
    if (education) {
      const tagRecords = await domainAnalysisDb('education_tags')
        .join('tags', 'education_tags.tag_id', 'tags.id')
        .where('education_tags.education_id', id)
        .select('tags.tag_name', 'tags.id');
      
      const tags = tagRecords.map(record => ({
        id: record.id,
        name: record.tag_name
      }));
      
      return {
        ...education,
        tags: tags,
        tag_ids: tags.map(tag => tag.id)
      };
    }
    
    return education;
  } catch (error) {
    console.error('Error fetching education by id:', error);
    throw error;
  }
}

async function createEducation(data) {
  const trx = await domainAnalysisDb.transaction();
  try {
    const { tag_ids, ...educationData } = data;
    
    // Insert education record
    const [educationId] = await trx('education').insert(educationData);
    
    // Insert tag relations if provided
    if (tag_ids && tag_ids.length > 0) {
      const tagRelations = tag_ids.map(tagId => ({
        education_id: educationId,
        tag_id: tagId
      }));
      await trx('education_tags').insert(tagRelations);
    }
    
    await trx.commit();
    return educationId;
  } catch (error) {
    await trx.rollback();
    console.error('Error creating education:', error);
    throw error;
  }
}

async function updateEducation(id, data) {
  const trx = await domainAnalysisDb.transaction();
  try {
    const { tag_ids, ...educationData } = data;
    
    // Update education record
    await trx('education')
      .where('id', id)
      .update(educationData);
    
    // Delete existing tag relations
    await trx('education_tags')
      .where('education_id', id)
      .del();
    
    // Insert new tag relations if provided
    if (tag_ids && tag_ids.length > 0) {
      const tagRelations = tag_ids.map(tagId => ({
        education_id: id,
        tag_id: tagId
      }));
      await trx('education_tags').insert(tagRelations);
    }
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error updating education:', error);
    throw error;
  }
}

async function deleteEducation(id) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Delete tag relations first
    await trx('education_tags')
      .where('education_id', id)
      .del();
    
    // Delete education record
    await trx('education')
      .where('id', id)
      .del();
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error deleting education:', error);
    throw error;
  }
}

// ========== TAGS CRUD ==========

async function getAllTags() {
  try {
    const tags = await domainAnalysisDb('tags')
      .select('*')
      .orderBy('tag_name');
    
    // Add usage counts
    const tagsWithCounts = await Promise.all(tags.map(async (tag) => {
      const [educationCount] = await domainAnalysisDb('education_tags')
        .where('tag_id', tag.id)
        .count('* as count');
      
      const [domainCount] = await domainAnalysisDb('domain_tags')
        .where('tag_id', tag.id)
        .count('* as count');
      
      return {
        ...tag,
        education_count: educationCount.count,
        domain_count: domainCount.count
      };
    }));
    
    return tagsWithCounts;
  } catch (error) {
    console.error('Error fetching tags:', error);
    throw error;
  }
}

async function createTag(data) {
  try {
    const [id] = await domainAnalysisDb('tags').insert(data);
    return id;
  } catch (error) {
    console.error('Error creating tag:', error);
    throw error;
  }
}

async function updateTag(id, data) {
  try {
    await domainAnalysisDb('tags')
      .where('id', id)
      .update(data);
    return true;
  } catch (error) {
    console.error('Error updating tag:', error);
    throw error;
  }
}

async function deleteTag(id) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Delete all relations first
    await trx('education_tags').where('tag_id', id).del();
    await trx('domain_tags').where('tag_id', id).del();
    
    // Delete tag
    await trx('tags').where('id', id).del();
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error deleting tag:', error);
    throw error;
  }
}

// ========== DOMAINS CRUD ==========

async function getAllDomains() {
  try {
    const domains = await domainAnalysisDb('domains')
      .select('*')
      .orderBy('domain_name');
    
    // Get tags and subtags for each domain
    const domainsWithData = await Promise.all(domains.map(async (domain) => {
      const tagRecords = await domainAnalysisDb('domain_tags')
        .join('tags', 'domain_tags.tag_id', 'tags.id')
        .where('domain_tags.domain_id', domain.id)
        .select('tags.tag_name', 'tags.id');
      
      const subtagRecords = await domainAnalysisDb('domain_subtags')
        .join('subtags', 'domain_subtags.subtag_id', 'subtags.id')
        .where('domain_subtags.domain_id', domain.id)
        .select('subtags.subtag_name', 'subtags.id');
      
      const tags = tagRecords.map(record => ({
        id: record.id,
        name: record.tag_name
      }));
      
      const subtags = subtagRecords.map(record => ({
        id: record.id,
        name: record.subtag_name
      }));
      
      return {
        ...domain,
        tags: tags,
        subtags: subtags
      };
    }));
    
    return domainsWithData;
  } catch (error) {
    console.error('Error fetching domains:', error);
    throw error;
  }
}

async function getDomainById(id) {
  try {
    const domain = await domainAnalysisDb('domains')
      .where('id', id)
      .first();
    
    if (domain) {
      const tagRecords = await domainAnalysisDb('domain_tags')
        .join('tags', 'domain_tags.tag_id', 'tags.id')
        .where('domain_tags.domain_id', id)
        .select('tags.tag_name', 'tags.id');
      
      const subtagRecords = await domainAnalysisDb('domain_subtags')
        .join('subtags', 'domain_subtags.subtag_id', 'subtags.id')
        .where('domain_subtags.domain_id', id)
        .select('subtags.subtag_name', 'subtags.id');
      
      const tags = tagRecords.map(record => ({
        id: record.id,
        name: record.tag_name
      }));
      
      const subtags = subtagRecords.map(record => ({
        id: record.id,
        name: record.subtag_name
      }));
      
      return {
        ...domain,
        tags: tags,
        subtags: subtags,
        tag_ids: tags.map(tag => tag.id),
        subtag_ids: subtags.map(subtag => subtag.id)
      };
    }
    
    return domain;
  } catch (error) {
    console.error('Error fetching domain by id:', error);
    throw error;
  }
}

// Remove tag from domain
async function removeDomainTag(domainId, tagId) {
  try {
    await domainAnalysisDb('domain_tags')
      .where({
        domain_id: domainId,
        tag_id: tagId
      })
      .del();
    return true;
  } catch (error) {
    console.error('Error removing domain tag:', error);
    throw error;
  }
}

// Remove subtag from domain
async function removeDomainSubtag(domainId, subtagId) {
  try {
    await domainAnalysisDb('domain_subtags')
      .where({
        domain_id: domainId,
        subtag_id: subtagId
      })
      .del();
    return true;
  } catch (error) {
    console.error('Error removing domain subtag:', error);
    throw error;
  }
}

// Create new domain
async function createDomain(data) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Extract tag and subtag IDs from data
    const { tag_ids = [], subtag_ids = [], ...domainData } = data;
    
    // Insert domain
    const [domainId] = await trx('domains').insert(domainData);
    
    // Insert tag associations
    if (tag_ids.length > 0) {
      const tagInserts = tag_ids.map(tagId => ({
        domain_id: domainId,
        tag_id: tagId
      }));
      await trx('domain_tags').insert(tagInserts);
    }
    
    // Insert subtag associations
    if (subtag_ids.length > 0) {
      const subtagInserts = subtag_ids.map(subtagId => ({
        domain_id: domainId,
        subtag_id: subtagId
      }));
      await trx('domain_subtags').insert(subtagInserts);
    }
    
    await trx.commit();
    return domainId;
  } catch (error) {
    await trx.rollback();
    console.error('Error creating domain:', error);
    throw error;
  }
}

// Update domain
async function updateDomain(id, data) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Extract tag and subtag IDs from data
    const { tag_ids = [], subtag_ids = [], ...domainData } = data;
    
    // Update domain
    await trx('domains')
      .where('id', id)
      .update(domainData);
    
    // Remove existing tag associations
    await trx('domain_tags').where('domain_id', id).del();
    
    // Remove existing subtag associations
    await trx('domain_subtags').where('domain_id', id).del();
    
    // Insert new tag associations
    if (tag_ids.length > 0) {
      const tagInserts = tag_ids.map(tagId => ({
        domain_id: id,
        tag_id: tagId
      }));
      await trx('domain_tags').insert(tagInserts);
    }
    
    // Insert new subtag associations
    if (subtag_ids.length > 0) {
      const subtagInserts = subtag_ids.map(subtagId => ({
        domain_id: id,
        subtag_id: subtagId
      }));
      await trx('domain_subtags').insert(subtagInserts);
    }
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error updating domain:', error);
    throw error;
  }
}

// Delete domain
async function deleteDomain(id) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Delete all tag associations
    await trx('domain_tags').where('domain_id', id).del();
    
    // Delete all subtag associations
    await trx('domain_subtags').where('domain_id', id).del();
    
    // Delete domain
    await trx('domains').where('id', id).del();
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error deleting domain:', error);
    throw error;
  }
}

// Search tags for autocomplete
async function searchTags(query) {
  try {
    if (!query || query.length < 1) {
      // Return all tags if no query
      const tags = await domainAnalysisDb('tags')
        .select('id', 'tag_name')
        .orderBy('tag_name')
        .limit(20);
      return tags;
    }
    
    const tags = await domainAnalysisDb('tags')
      .select('id', 'tag_name')
      .where('tag_name', 'like', `%${query}%`)
      .orderBy('tag_name')
      .limit(10);
    return tags;
  } catch (error) {
    console.error('Error searching tags:', error);
    throw error;
  }
}

// Search subtags for autocomplete
async function searchSubtags(query) {
  try {
    if (!query || query.length < 1) {
      // Return all subtags if no query
      const subtags = await domainAnalysisDb('subtags')
        .select('id', 'subtag_name')
        .orderBy('subtag_name')
        .limit(20);
      return subtags;
    }
    
    const subtags = await domainAnalysisDb('subtags')
      .select('id', 'subtag_name')
      .where('subtag_name', 'like', `%${query}%`)
      .orderBy('subtag_name')
      .limit(10);
    return subtags;
  } catch (error) {
    console.error('Error searching subtags:', error);
    throw error;
  }
}

// Add tag to domain (create tag if it doesn't exist)
async function addTagToDomain(domainId, tagName) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Check if tag exists
    let tag = await trx('tags')
      .where('tag_name', tagName)
      .first();
    
    // Create tag if it doesn't exist
    if (!tag) {
      const [tagId] = await trx('tags').insert({ tag_name: tagName });
      tag = { id: tagId, tag_name: tagName };
    }
    
    // Check if association already exists
    const existingAssociation = await trx('domain_tags')
      .where({
        domain_id: domainId,
        tag_id: tag.id
      })
      .first();
    
    if (!existingAssociation) {
      // Add association
      await trx('domain_tags').insert({
        domain_id: domainId,
        tag_id: tag.id
      });
    }
    
    await trx.commit();
    return { 
      success: true, 
      tag: tag,
      message: existingAssociation ? 'Tag already assigned' : 'Tag added successfully'
    };
  } catch (error) {
    await trx.rollback();
    console.error('Error adding tag to domain:', error);
    throw error;
  }
}

// Add subtag to domain (create subtag if it doesn't exist)
async function addSubtagToDomain(domainId, subtagName) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Check if subtag exists
    let subtag = await trx('subtags')
      .where('subtag_name', subtagName)
      .first();
    
    // Create subtag if it doesn't exist
    if (!subtag) {
      const [subtagId] = await trx('subtags').insert({ subtag_name: subtagName });
      subtag = { id: subtagId, subtag_name: subtagName };
    }
    
    // Check if association already exists
    const existingAssociation = await trx('domain_subtags')
      .where({
        domain_id: domainId,
        subtag_id: subtag.id
      })
      .first();
    
    if (!existingAssociation) {
      // Add association
      await trx('domain_subtags').insert({
        domain_id: domainId,
        subtag_id: subtag.id
      });
    }
    
    await trx.commit();
    return { 
      success: true, 
      subtag: subtag,
      message: existingAssociation ? 'Subtag already assigned' : 'Subtag added successfully'
    };
  } catch (error) {
    await trx.rollback();
    console.error('Error adding subtag to domain:', error);
    throw error;
  }
}

// ========== PROJECTS CRUD ==========

async function getAllProjects() {
  try {
    const projects = await domainAnalysisDb('projects')
      .select('*')
      .orderBy('created_at', 'desc');
    
    // For each project, get associated tags and files
    const projectsWithData = await Promise.all(projects.map(async (project) => {
      // Get tags for this project
      const tagRecords = await domainAnalysisDb('project_tags')
        .join('tags', 'project_tags.tag_id', 'tags.id')
        .where('project_tags.project_id', project.id)
        .select('tags.id', 'tags.tag_name as name');
      
      // Get files for this project
      const files = await domainAnalysisDb('project_files')
        .where('project_id', project.id)
        .select('*')
        .orderBy('created_at', 'desc');
      
      // For each file, get its tags
      const filesWithTags = await Promise.all(files.map(async (file) => {
        const fileTagRecords = await domainAnalysisDb('project_file_tags')
          .join('tags', 'project_file_tags.tag_id', 'tags.id')
          .where('project_file_tags.file_id', file.id)
          .select('tags.id', 'tags.tag_name as name');
        
        return {
          ...file,
          tags: fileTagRecords
        };
      }));
      
      return {
        ...project,
        tags: tagRecords,
        files: filesWithTags
      };
    }));
    
    return projectsWithData;
  } catch (error) {
    console.error('Error fetching projects:', error);
    throw error;
  }
}

async function getProjectById(id) {
  try {
    const project = await domainAnalysisDb('projects')
      .where('id', id)
      .first();
    
    if (!project) return null;
    
    // Get associated tags
    const tagRecords = await domainAnalysisDb('project_tags')
      .join('tags', 'project_tags.tag_id', 'tags.id')
      .where('project_tags.project_id', project.id)
      .select('tags.id', 'tags.tag_name as name');
    
    // Get files
    const files = await domainAnalysisDb('project_files')
      .where('project_id', project.id)
      .select('*')
      .orderBy('created_at', 'desc');
    
    // For each file, get its tags
    const filesWithTags = await Promise.all(files.map(async (file) => {
      const fileTagRecords = await domainAnalysisDb('project_file_tags')
        .join('tags', 'project_file_tags.tag_id', 'tags.id')
        .where('project_file_tags.file_id', file.id)
        .select('tags.id', 'tags.tag_name as name');
      
      return {
        ...file,
        tags: fileTagRecords
      };
    }));
    
    return {
      ...project,
      tags: tagRecords,
      files: filesWithTags
    };
  } catch (error) {
    console.error('Error fetching project by id:', error);
    throw error;
  }
}

async function createProject(data) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Extract tag_ids from data
    const { tag_ids, ...projectData } = data;
    
    // Clean up data - convert empty strings to null for dates and numbers
    const cleanedData = {};
    for (const [key, value] of Object.entries(projectData)) {
      if ((key === 'start_date' || key === 'end_date') && value === '') {
        cleanedData[key] = null;
      } else if ((key === 'budget_min' || key === 'budget_max') && (value === '' || value === null)) {
        cleanedData[key] = null;
      } else {
        cleanedData[key] = value;
      }
    }
    
    // Create project
    const [projectId] = await trx('projects').insert({
      ...cleanedData,
      created_at: new Date(),
      updated_at: new Date()
    });
    
    // Add tags if provided
    if (tag_ids && tag_ids.length > 0) {
      const tagAssociations = tag_ids.map(tagId => ({
        project_id: projectId,
        tag_id: tagId
      }));
      await trx('project_tags').insert(tagAssociations);
    }
    
    await trx.commit();
    return projectId;
  } catch (error) {
    await trx.rollback();
    console.error('Error creating project:', error);
    throw error;
  }
}

async function updateProject(id, data) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Extract tag_ids from data
    const { tag_ids, ...projectData } = data;
    
    // Clean up data - convert empty strings to null for dates and numbers
    const cleanedData = {};
    for (const [key, value] of Object.entries(projectData)) {
      if ((key === 'start_date' || key === 'end_date') && value === '') {
        cleanedData[key] = null;
      } else if ((key === 'budget_min' || key === 'budget_max') && (value === '' || value === null)) {
        cleanedData[key] = null;
      } else {
        cleanedData[key] = value;
      }
    }
    
    // Update project
    await trx('projects')
      .where('id', id)
      .update({
        ...cleanedData,
        updated_at: new Date()
      });
    
    // Handle tags if provided
    if (tag_ids !== undefined) {
      // Remove existing tag associations
      await trx('project_tags').where('project_id', id).del();
      
      // Add new tag associations
      if (tag_ids && tag_ids.length > 0) {
        const tagAssociations = tag_ids.map(tagId => ({
          project_id: id,
          tag_id: tagId
        }));
        await trx('project_tags').insert(tagAssociations);
      }
    }
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error updating project:', error);
    throw error;
  }
}

async function deleteProject(id) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Delete project file tags
    const files = await trx('project_files').where('project_id', id).select('id');
    for (const file of files) {
      await trx('project_file_tags').where('file_id', file.id).del();
    }
    
    // Delete project files
    await trx('project_files').where('project_id', id).del();
    
    // Delete project tags
    await trx('project_tags').where('project_id', id).del();
    
    // Delete project
    await trx('projects').where('id', id).del();
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error deleting project:', error);
    throw error;
  }
}

// ========== PROJECT FILES CRUD ==========

async function addProjectFile(projectId, fileData) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Extract tag_ids from fileData
    const { tag_ids, ...fileRecord } = fileData;
    
    // Create file record
    const [fileId] = await trx('project_files').insert({
      project_id: projectId,
      ...fileRecord,
      created_at: new Date(),
      updated_at: new Date()
    });
    
    // Add tags if provided
    if (tag_ids && tag_ids.length > 0) {
      const tagAssociations = tag_ids.map(tagId => ({
        file_id: fileId,
        tag_id: tagId
      }));
      await trx('project_file_tags').insert(tagAssociations);
    }
    
    await trx.commit();
    return fileId;
  } catch (error) {
    await trx.rollback();
    console.error('Error adding project file:', error);
    throw error;
  }
}

async function updateProjectFile(fileId, fileData) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Extract tag_ids from fileData
    const { tag_ids, ...fileRecord } = fileData;
    
    // Update file
    await trx('project_files')
      .where('id', fileId)
      .update({
        ...fileRecord,
        updated_at: new Date()
      });
    
    // Handle tags if provided
    if (tag_ids !== undefined) {
      // Remove existing tag associations
      await trx('project_file_tags').where('file_id', fileId).del();
      
      // Add new tag associations
      if (tag_ids && tag_ids.length > 0) {
        const tagAssociations = tag_ids.map(tagId => ({
          file_id: fileId,
          tag_id: tagId
        }));
        await trx('project_file_tags').insert(tagAssociations);
      }
    }
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error updating project file:', error);
    throw error;
  }
}

async function deleteProjectFile(fileId) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Delete file tags
    await trx('project_file_tags').where('file_id', fileId).del();
    
    // Delete file
    await trx('project_files').where('id', fileId).del();
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error deleting project file:', error);
    throw error;
  }
}

// ========== PROJECT UTILITIES ==========

async function linkJobToProject(jobId, projectId) {
  try {
    await domainAnalysisDb('projects')
      .where('id', projectId)
      .update({
        linked_job_id: jobId,
        updated_at: new Date()
      });
    return true;
  } catch (error) {
    console.error('Error linking job to project:', error);
    throw error;
  }
}

async function createProjectFromJob(jobData) {
  try {
    const projectData = {
      title: jobData.title,
      description: jobData.description,
      status: 'active', // or 'planning' 
      project_type: jobData.project_type || 'hourly',
      budget_min: jobData.budget?.minimum || null,
      budget_max: jobData.budget?.maximum || null,
      currency_code: jobData.currency?.code || 'USD',
      country: jobData.country,
      linked_job_id: jobData.id,
      internal_notes: `Created from job #${jobData.id}`,
      created_at: new Date(),
      updated_at: new Date()
    };
    
    const [projectId] = await domainAnalysisDb('projects').insert(projectData);
    return projectId;
  } catch (error) {
    console.error('Error creating project from job:', error);
    throw error;
  }
}

async function addTagToProject(projectId, tagName) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Check if tag exists
    let tag = await trx('tags')
      .where('tag_name', tagName)
      .first();
    
    // Create tag if it doesn't exist
    if (!tag) {
      const [tagId] = await trx('tags').insert({ tag_name: tagName });
      tag = { id: tagId, tag_name: tagName };
    }
    
    // Check if association already exists
    const existingAssociation = await trx('project_tags')
      .where({
        project_id: projectId,
        tag_id: tag.id
      })
      .first();
    
    if (!existingAssociation) {
      // Add association
      await trx('project_tags').insert({
        project_id: projectId,
        tag_id: tag.id
      });
    }
    
    await trx.commit();
    return { 
      success: true, 
      tag: tag,
      message: existingAssociation ? 'Tag already assigned' : 'Tag added successfully'
    };
  } catch (error) {
    await trx.rollback();
    console.error('Error adding tag to project:', error);
    throw error;
  }
}

async function removeProjectTag(projectId, tagId) {
  try {
    await domainAnalysisDb('project_tags')
      .where({
        project_id: projectId,
        tag_id: tagId
      })
      .del();
    return true;
  } catch (error) {
    console.error('Error removing project tag:', error);
    throw error;
  }
}

// ========== CONTACTS CRUD ==========

async function getAllContacts() {
  try {
    const contacts = await domainAnalysisDb('contacts')
      .select('*')
      .orderBy('last_name', 'asc')
      .orderBy('first_name', 'asc');
    
    // Get phone numbers for each contact
    const contactsWithPhones = await Promise.all(contacts.map(async (contact) => {
      const phoneNumbers = await domainAnalysisDb('contact_phone_numbers')
        .where('contact_id', contact.id)
        .select('*')
        .orderBy('is_primary', 'desc')
        .orderBy('phone_type', 'asc');
      
      return {
        ...contact,
        phone_numbers: phoneNumbers
      };
    }));
    
    return contactsWithPhones;
  } catch (error) {
    console.error('Error fetching contacts:', error);
    throw error;
  }
}

async function getContactById(id) {
  try {
    const contact = await domainAnalysisDb('contacts')
      .where('id', id)
      .first();
    
    if (contact) {
      const phoneNumbers = await domainAnalysisDb('contact_phone_numbers')
        .where('contact_id', id)
        .select('*')
        .orderBy('is_primary', 'desc')
        .orderBy('phone_type', 'asc');
      
      return {
        ...contact,
        phone_numbers: phoneNumbers
      };
    }
    
    return contact;
  } catch (error) {
    console.error('Error fetching contact by id:', error);
    throw error;
  }
}

async function createContact(data) {
  const trx = await domainAnalysisDb.transaction();
  try {
    const { phone_numbers, ...contactData } = data;
    
    // Insert contact record
    const [contactId] = await trx('contacts').insert({
      ...contactData,
      created_at: new Date(),
      updated_at: new Date()
    });
    
    // Insert phone numbers if provided
    if (phone_numbers && phone_numbers.length > 0) {
      const phoneNumbersData = phone_numbers.map(phone => ({
        contact_id: contactId,
        phone_number: phone.phone_number,
        phone_type: phone.phone_type || 'mobile',
        is_primary: phone.is_primary || false
      }));
      await trx('contact_phone_numbers').insert(phoneNumbersData);
    }
    
    await trx.commit();
    return contactId;
  } catch (error) {
    await trx.rollback();
    console.error('Error creating contact:', error);
    throw error;
  }
}

async function updateContact(id, data) {
  const trx = await domainAnalysisDb.transaction();
  try {
    const { phone_numbers, ...contactData } = data;
    
    // Update contact record
    await trx('contacts')
      .where('id', id)
      .update({
        ...contactData,
        updated_at: new Date()
      });
    
    // Delete existing phone numbers
    await trx('contact_phone_numbers')
      .where('contact_id', id)
      .del();
    
    // Insert new phone numbers if provided
    if (phone_numbers && phone_numbers.length > 0) {
      const phoneNumbersData = phone_numbers.map(phone => ({
        contact_id: id,
        phone_number: phone.phone_number,
        phone_type: phone.phone_type || 'mobile',
        is_primary: phone.is_primary || false
      }));
      await trx('contact_phone_numbers').insert(phoneNumbersData);
    }
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error updating contact:', error);
    throw error;
  }
}

async function deleteContact(id) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Check if contact is used by any customers
    const customersUsingContact = await trx('customers')
      .where('primary_contact_id', id)
      .count('id as count')
      .first();
    
    if (customersUsingContact.count > 0) {
      throw new Error('Contact cannot be deleted because it is used by customers');
    }
    
    // Delete phone numbers first
    await trx('contact_phone_numbers')
      .where('contact_id', id)
      .del();
    
    // Delete contact record
    await trx('contacts')
      .where('id', id)
      .del();
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error deleting contact:', error);
    throw error;
  }
}

// ========== PHONE NUMBERS CRUD ==========

async function addPhoneNumber(contactId, phoneData) {
  try {
    const [id] = await domainAnalysisDb('contact_phone_numbers').insert({
      contact_id: contactId,
      phone_number: phoneData.phone_number,
      phone_type: phoneData.phone_type || 'mobile',
      is_primary: phoneData.is_primary || false
    });
    return id;
  } catch (error) {
    console.error('Error adding phone number:', error);
    throw error;
  }
}

async function updatePhoneNumber(phoneId, phoneData) {
  try {
    await domainAnalysisDb('contact_phone_numbers')
      .where('id', phoneId)
      .update({
        phone_number: phoneData.phone_number,
        phone_type: phoneData.phone_type,
        is_primary: phoneData.is_primary
      });
    return true;
  } catch (error) {
    console.error('Error updating phone number:', error);
    throw error;
  }
}

async function deletePhoneNumber(phoneId) {
  try {
    await domainAnalysisDb('contact_phone_numbers')
      .where('id', phoneId)
      .del();
    return true;
  } catch (error) {
    console.error('Error deleting phone number:', error);
    throw error;
  }
}

// ========== CUSTOMERS CRUD ==========

async function getAllCustomers() {
  try {
    const customers = await domainAnalysisDb('customers')
      .leftJoin('contacts', 'customers.primary_contact_id', 'contacts.id')
      .select(
        'customers.*',
        'contacts.first_name as contact_first_name',
        'contacts.last_name as contact_last_name',
        'contacts.email as contact_email'
      )
      .orderBy('customers.company_name', 'asc');
    
    // Get primary phone number for each customer's contact
    const customersWithPhones = await Promise.all(customers.map(async (customer) => {
      if (customer.primary_contact_id) {
        const primaryPhone = await domainAnalysisDb('contact_phone_numbers')
          .where('contact_id', customer.primary_contact_id)
          .where('is_primary', true)
          .first();
        
        if (!primaryPhone) {
          // If no primary phone, get the first phone number
          const firstPhone = await domainAnalysisDb('contact_phone_numbers')
            .where('contact_id', customer.primary_contact_id)
            .first();
          customer.contact_phone = firstPhone ? firstPhone.phone_number : null;
        } else {
          customer.contact_phone = primaryPhone.phone_number;
        }
      }
      
      return customer;
    }));
    
    return customersWithPhones;
  } catch (error) {
    console.error('Error fetching customers:', error);
    throw error;
  }
}

async function getCustomerById(id) {
  try {
    const customer = await domainAnalysisDb('customers')
      .leftJoin('contacts', 'customers.primary_contact_id', 'contacts.id')
      .where('customers.id', id)
      .select(
        'customers.*',
        'contacts.first_name as contact_first_name',
        'contacts.last_name as contact_last_name',
        'contacts.email as contact_email',
        'contacts.notes as contact_notes'
      )
      .first();
    
    if (customer && customer.primary_contact_id) {
      // Get all phone numbers for the contact
      const phoneNumbers = await domainAnalysisDb('contact_phone_numbers')
        .where('contact_id', customer.primary_contact_id)
        .select('*')
        .orderBy('is_primary', 'desc')
        .orderBy('phone_type', 'asc');
      
      customer.contact_phone_numbers = phoneNumbers;
    }
    
    return customer;
  } catch (error) {
    console.error('Error fetching customer by id:', error);
    throw error;
  }
}

async function createCustomer(data) {
  try {
    const [id] = await domainAnalysisDb('customers').insert({
      ...data,
      created_at: new Date(),
      updated_at: new Date()
    });
    return id;
  } catch (error) {
    console.error('Error creating customer:', error);
    throw error;
  }
}

async function updateCustomer(id, data) {
  try {
    await domainAnalysisDb('customers')
      .where('id', id)
      .update({
        ...data,
        updated_at: new Date()
      });
    return true;
  } catch (error) {
    console.error('Error updating customer:', error);
    throw error;
  }
}

async function deleteCustomer(id) {
  const trx = await domainAnalysisDb.transaction();
  try {
    // Remove customer association from projects (don't delete projects)
    await trx('projects')
      .where('customer_id', id)
      .update({ customer_id: null });
      
    // Delete customer
    await trx('customers')
      .where('id', id)
      .del();
    
    await trx.commit();
    return true;
  } catch (error) {
    await trx.rollback();
    console.error('Error deleting customer:', error);
    throw error;
  }
}

async function getCustomerProjects(customerId) {
  try {
    const projects = await domainAnalysisDb('projects')
      .leftJoin('customers', 'projects.customer_id', 'customers.id')
      .leftJoin('contacts', 'customers.primary_contact_id', 'contacts.id')
      .where('projects.customer_id', customerId)
      .select(
        'projects.*',
        'customers.company_name as customer_company',
        'contacts.first_name as contact_first_name',
        'contacts.last_name as contact_last_name'
      )
      .orderBy('projects.created_at', 'desc');

    // Get project tags for each project
    const projectsWithTags = await Promise.all(projects.map(async (project) => {
      const tagRecords = await domainAnalysisDb('project_tags')
        .join('tags', 'project_tags.tag_id', 'tags.id')
        .where('project_tags.project_id', project.id)
        .select('tags.tag_name', 'tags.id');
      
      const tags = tagRecords.map(record => ({
        id: record.id,
        name: record.tag_name
      }));
      
      // Get file count
      const fileCount = await domainAnalysisDb('project_files')
        .where('project_id', project.id)
        .count('id as count')
        .first();
      
      return {
        ...project,
        tags: tags,
        file_count: fileCount ? fileCount.count : 0
      };
    }));
    
    return projectsWithTags;
  } catch (error) {
    console.error('Error fetching customer projects:', error);
    throw error;
  }
}

// Export the connection and helper functions
module.exports = {
  knex, // Original connection for other tables
  domainAnalysisDb, // Specific connection for domain_analysis
  getDomainReferences,
  getEmploymentHistory,
  getEducationHistory,
  
  // Employment CRUD
  getAllEmployment,
  getEmploymentById,
  createEmployment,
  updateEmployment,
  deleteEmployment,
  
  // Education CRUD
  getAllEducation,
  getEducationById,
  createEducation,
  updateEducation,
  deleteEducation,
  
  // Tags CRUD
  getAllTags,
  createTag,
  updateTag,
  deleteTag,
  
  // Domains CRUD
  getAllDomains,
  getDomainById,
  removeDomainTag,
  removeDomainSubtag,
  createDomain,
  updateDomain,
  deleteDomain,
  
  // Search tags
  searchTags,
  searchSubtags,
  addTagToDomain,
  addSubtagToDomain,
  
  // Projects CRUD
  getAllProjects,
  getProjectById,
  createProject,
  updateProject,
  deleteProject,
  
  // Project Files
  addProjectFile,
  updateProjectFile,
  deleteProjectFile,
  
  // Project Utilities
  linkJobToProject,
  createProjectFromJob,
  addTagToProject,
  removeProjectTag,
  
  // Contacts CRUD
  getAllContacts,
  getContactById,
  createContact,
  updateContact,
  deleteContact,
  
  // Phone Numbers CRUD
  addPhoneNumber,
  updatePhoneNumber,
  deletePhoneNumber,
  
  // Customers CRUD
  getAllCustomers,
  getCustomerById,
  createCustomer,
  updateCustomer,
  deleteCustomer,
  getCustomerProjects
}; 