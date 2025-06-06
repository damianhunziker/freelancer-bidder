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
      .select('id', 'domain_name as domain')
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
  removeDomainSubtag
}; 