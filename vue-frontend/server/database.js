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

// Export the connection and helper functions
module.exports = {
  knex, // Original connection for other tables
  domainAnalysisDb, // Specific connection for domain_analysis
  getDomainReferences
}; 