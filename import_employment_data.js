const fs = require('fs').promises;
const path = require('path');
const mysql = require('mysql2/promise');

// Database configuration
const dbConfig = {
  host: 'localhost',
  user: 'root',
  password: 'dCTKBq@CV9$a50ZtpzSr@D7*7Q',
  database: 'domain_analysis'
};

// Helper function to parse a single employment entry
function parseEmploymentEntry(companyLine, dateLine, contentLines) {
  let companyName = companyLine;
  let location = null;
  
  if (companyLine.includes(',')) {
    const parts = companyLine.split(',');
    companyName = parts[0].trim();
    location = parts.slice(1).join(',').trim();
  }
  
  // Extract date range
  let startDate = null;
  let endDate = null;
  
  // Parse date patterns like "März 2021 – Juli 2024", "Ab Juli 2024", or "Dez 2011 – Ok 2017"
  const dateMatch = dateLine.match(/([A-Za-zä-ü]+\s+\d{4})\s*[–-]\s*([A-Za-zä-ü]+\s+\d{4})/);
  const abDateMatch = dateLine.match(/Ab\s+([A-Za-zä-ü]+\s+\d{4})/);
  
  if (dateMatch) {
    startDate = dateMatch[1];
    endDate = dateMatch[2];
  } else if (abDateMatch) {
    startDate = abDateMatch[1];
    endDate = null; // Still working there
  } else {
    // Try other date patterns like "2009 - Nov 2011"
    const yearRangeMatch = dateLine.match(/(\d{4})\s*[–-]\s*(\w+\s+\d{4})/);
    if (yearRangeMatch) {
      startDate = yearRangeMatch[1];
      endDate = yearRangeMatch[2];
    }
  }
  
  // Check if self-employed
  let isSelftEmployed = false;
  if (companyLine.includes('(selbstständig)') || 
      companyLine.includes('selbstständig') ||
      companyLine.includes('IK, Lettland')) {
    isSelftEmployed = true;
    companyName = companyName.replace('(selbstständig)', '').trim();
  }
  
  let position = 'Webentwickler'; // Default position
  let description = '';
  let technologies = [];
  let achievements = [];
  
  // Process content lines
  for (const line of contentLines) {
    const trimmedLine = line.trim();
    
    if (trimmedLine.startsWith('-')) {
      const bulletPoint = trimmedLine.substring(1).trim();
      
      // Categorize bullet points
      if (bulletPoint.includes('PHP') || bulletPoint.includes('JavaScript') || 
          bulletPoint.includes('Laravel') || bulletPoint.includes('SQL') ||
          bulletPoint.includes('HTML') || bulletPoint.includes('CSS') ||
          bulletPoint.includes('React') || bulletPoint.includes('Vue') ||
          bulletPoint.includes('TYPO3') || bulletPoint.includes('Docker') ||
          bulletPoint.includes('Git') || bulletPoint.includes('API') ||
          bulletPoint.includes('nginx') || bulletPoint.includes('Linux') ||
          bulletPoint.includes('Bootstrap') || bulletPoint.includes('jQuery') ||
          bulletPoint.includes('Composer') || bulletPoint.includes('Webpack') ||
          bulletPoint.includes('NPM') || bulletPoint.includes('Magento') ||
          bulletPoint.includes('Joomla') || bulletPoint.includes('WordPress') ||
          bulletPoint.includes('Prestashop') || bulletPoint.includes('REST') ||
          bulletPoint.includes('XML') || bulletPoint.includes('JSON') ||
          bulletPoint.includes('tt_news') || bulletPoint.includes('Contenido') ||
          bulletPoint.includes('CCXT') || bulletPoint.includes('AI') ||
          bulletPoint.includes('Quantitative') || bulletPoint.includes('DMX')) {
        technologies.push(bulletPoint);
      } else if (bulletPoint.includes('Entwicklung') || bulletPoint.includes('Umsetzung') ||
                 bulletPoint.includes('Implementation') || bulletPoint.includes('Integration') ||
                 bulletPoint.includes('Vermittelt') || bulletPoint.includes('Betreuung') ||
                 bulletPoint.includes('Weiterentwicklung') || bulletPoint.includes('Erarbeitung') ||
                 bulletPoint.includes('Geschäftsleitung') || bulletPoint.includes('Lead Developer') ||
                 bulletPoint.includes('Fokus')) {
        achievements.push(bulletPoint);
      } else {
        description += (description ? ' ' : '') + bulletPoint;
      }
    } else if (trimmedLine && !trimmedLine.startsWith('#')) {
      // Check if it's a position line
      if (trimmedLine.includes('Anstellung als')) {
        const positionMatch = trimmedLine.match(/Anstellung als ([^,.-]+)/);
        if (positionMatch) {
          position = positionMatch[1].trim();
        }
      } else {
        description += (description ? ' ' : '') + trimmedLine;
      }
    }
  }
  
  // Extract position from description or use default
  if (description.includes('Anstellung als')) {
    const positionMatch = description.match(/Anstellung als ([^,.-]+)/);
    if (positionMatch) {
      position = positionMatch[1].trim();
      // Remove the position from description to avoid duplication
      description = description.replace(/Anstellung als [^,.-]+[,.-]?\s*/, '').trim();
    }
  } else if (isSelftEmployed) {
    position = 'Selbstständiger Webentwickler';
  }
  
  // Special handling for Lead Developer
  if (achievements.some(a => a.includes('Lead Developer'))) {
    position = 'Geschäftsleitung, Lead Developer';
  }
  
  // Clean up description
  description = description.replace(/\s+/g, ' ').trim();
  
  // Only return if we have valid data
  if (companyName && startDate) {
    return {
      company_name: companyName,
      position: position,
      start_date: startDate,
      end_date: endDate,
      description: description,
      is_self_employed: isSelftEmployed,
      location: location,
      technologies: technologies.length > 0 ? technologies.join('; ') : null,
      achievements: achievements.length > 0 ? achievements.join('; ') : null
    };
  }
  
  return null;
}

// Function to parse employment data from lebenslauf.md
function parseEmploymentData(content) {
  const employmentData = [];
  
  // Find the Beruflicher Werdegang section - more robust approach
  const berufMatch = content.match(/## Beruflicher Werdegang\s*([\s\S]*?)(?=## Weiterbildungen|$)/);
  if (!berufMatch) {
    console.log('No Beruflicher Werdegang section found');
    return employmentData;
  }
  
  const berufSection = berufMatch[1];
  console.log('Found Beruflicher Werdegang section, length:', berufSection.length);
  console.log('First 300 chars:', berufSection.substring(0, 300));
  
  // Split content by sections based on ### headers
  const sections = berufSection.split('###').slice(1); // Remove the first empty element
  console.log(`Found ${sections.length} employment sections after split`);
  
  // Debug: show what we found after split
  sections.forEach((section, index) => {
    const firstLine = section.trim().split('\n')[0];
    console.log(`Section ${index + 1}: ${firstLine}`);
  });
  
  for (const section of sections) {
    const lines = section.trim().split('\n').filter(line => line.trim());
    if (lines.length === 0) continue;
    
    const companyLine = lines[0].trim();
    console.log(`Processing section: ${companyLine}`);
    
    // Skip non-employment sections (these should be in Weiterbildungen)
    if (companyLine.includes('Project Management Grundlagen') || 
        companyLine.includes('Webapplikationen mit React') || 
        companyLine.includes('Front-End JavaScript') ||
        companyLine.includes('Typo3 Barcamp') ||
        companyLine.includes('Bachelor of Multimedia') ||
        companyLine.includes('Creative Media Producer') ||
        companyLine.includes('Introduction to Trading')) {
      console.log(`Skipping non-employment section: ${companyLine}`);
      continue;
    }
    
    // Get date line
    const dateLine = lines.length > 1 ? lines[1].trim() : '';
    
    // Get content lines (skip company and date)
    const contentLines = lines.slice(2);
    
    // Parse the entry
    const entry = parseEmploymentEntry(companyLine, dateLine, contentLines);
    if (entry) {
      employmentData.push(entry);
      console.log(`Added employment entry: ${entry.company_name} (${entry.start_date} - ${entry.end_date || 'Present'})`);
    } else {
      console.log(`Failed to parse entry: ${companyLine}`);
    }
  }
  
  // Sort by start date (newest first)
  employmentData.sort((a, b) => {
    // Simple sorting by year for now
    const yearA = parseInt(a.start_date.match(/\d{4}/)?.[0] || '0');
    const yearB = parseInt(b.start_date.match(/\d{4}/)?.[0] || '0');
    return yearB - yearA;
  });
  
  return employmentData;
}

// Function to insert employment data into database
async function insertEmploymentData(employmentData) {
  const connection = await mysql.createConnection(dbConfig);
  
  try {
    // Clear existing data
    await connection.execute('DELETE FROM employment');
    console.log('Cleared existing employment data');
    
    // Insert new data
    const insertQuery = `
      INSERT INTO employment 
      (company_name, position, start_date, end_date, description, is_self_employed, location, technologies, achievements)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;
    
    for (const employment of employmentData) {
      await connection.execute(insertQuery, [
        employment.company_name,
        employment.position,
        employment.start_date,
        employment.end_date,
        employment.description,
        employment.is_self_employed,
        employment.location,
        employment.technologies,
        employment.achievements
      ]);
      
      console.log(`Inserted: ${employment.company_name} (${employment.start_date} - ${employment.end_date || 'Present'})`);
    }
    
    console.log(`Successfully imported ${employmentData.length} employment records`);
    
  } catch (error) {
    console.error('Error inserting employment data:', error);
    throw error;
  } finally {
    await connection.end();
  }
}

// Main function
async function main() {
  try {
    console.log('Reading lebenslauf.md file...');
    const lebenslaufPath = path.join(__dirname, 'lebenslauf.md');
    const content = await fs.readFile(lebenslaufPath, 'utf8');
    
    console.log('Parsing employment data...');
    const employmentData = parseEmploymentData(content);
    
    console.log(`Found ${employmentData.length} employment entries:`);
    employmentData.forEach((emp, index) => {
      console.log(`${index + 1}. ${emp.company_name} - ${emp.position} (${emp.start_date} - ${emp.end_date || 'Present'}) [Self-employed: ${emp.is_self_employed}]`);
      if (emp.technologies) {
        console.log(`   Technologies: ${emp.technologies.substring(0, 100)}...`);
      }
      if (emp.achievements) {
        console.log(`   Achievements: ${emp.achievements.substring(0, 100)}...`);
      }
    });
    
    console.log('\nInserting data into database...');
    await insertEmploymentData(employmentData);
    
    console.log('Employment data import completed successfully!');
    
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

// Run the script
if (require.main === module) {
  main();
}

module.exports = { parseEmploymentData, insertEmploymentData }; 