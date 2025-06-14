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

// Function to parse education data from lebenslauf.md
function parseEducationData(content) {
  const educationData = [];
  
  // Find the Weiterbildungen section
  const weiterbildungenMatch = content.match(/## Weiterbildungen([\s\S]*)/);
  if (!weiterbildungenMatch) {
    console.log('No Weiterbildungen section found');
    return educationData;
  }
  
  const weiterbildungenSection = weiterbildungenMatch[1];
  console.log('Found Weiterbildungen section:', weiterbildungenSection.substring(0, 200) + '...');
  
  // Split by "### " (with space) headers to get individual education entries
  const sections = weiterbildungenSection.split(/###\s+/).slice(1); // Remove first empty element
  console.log(`Found ${sections.length} education sections`);
  
  for (const section of sections) {
    const lines = section.trim().split('\n').filter(line => line.trim());
    if (lines.length === 0) continue;
    
    console.log(`Processing section with ${lines.length} lines`);
    console.log('First line:', lines[0]);
    
    const titleLine = lines[0].trim();
    let title = titleLine;
    let institution = null;
    let startDate = null;
    let endDate = null;
    let duration = null;
    let description = '';
    let location = null;
    let type = 'course'; // Default type
    let suggestedTags = [];
    
    // Extract date from the next line
    if (lines.length > 1) {
      const dateLine = lines[1].trim();
      console.log('Date line:', dateLine);
      
      // Parse different date patterns
      const dateRangeMatch = dateLine.match(/([A-Za-zä-ü]+)\s*[-–]\s*([A-Za-zä-ü]+\s+\d{4})/);
      const singleDateMatch = dateLine.match(/([A-Za-zä-ü]+\s+\d{4})/);
      const monthYearRangeMatch = dateLine.match(/([A-Za-zä-ü]+\s+\d{4})\s*[-–]\s*([A-Za-zä-ü]+\s+\d{4})/);
      
      if (monthYearRangeMatch) {
        startDate = monthYearRangeMatch[1];
        endDate = monthYearRangeMatch[2];
        console.log('Parsed date range:', startDate, '-', endDate);
      } else if (dateRangeMatch) {
        startDate = dateRangeMatch[1] + ' (year unknown)';
        endDate = dateRangeMatch[2];
        console.log('Parsed partial date range:', startDate, '-', endDate);
      } else if (singleDateMatch) {
        startDate = singleDateMatch[1];
        endDate = null;
        console.log('Parsed single date:', startDate);
      } else {
        // Try to extract year from the line
        const yearMatch = dateLine.match(/\d{4}/);
        if (yearMatch) {
          startDate = dateLine;
          console.log('Extracted date from line:', startDate);
        }
      }
    }
    
    // Determine type and extract information based on title/content
    if (title.includes('Barcamp')) {
      type = 'workshop';
    } else if (title.includes('Bachelor') || title.includes('Kurs')) {
      type = 'course';
    } else if (title.includes('Grundlagen')) {
      type = 'training';
    } else if (title.includes('Framework') || title.includes('entwickeln')) {
      type = 'course';
    }
    
    // Extract description and details from remaining lines
    for (let i = 2; i < lines.length; i++) {
      const line = lines[i].trim();
      
      if (line) {
        // Check for institution information
        if (line.includes('University') || line.includes('Universität') || 
            line.includes('School') || line.includes('EB Zürich') ||
            line.includes('coursera.org') || line.includes('SAE')) {
          if (!institution) {
            if (line.includes('Howard University Washington')) {
              institution = 'Howard University Washington';
            } else if (line.includes('EB Zürich')) {
              institution = 'EB Zürich';
            } else if (line.includes('coursera.org')) {
              institution = 'Hong Kong University of Science and Technology (coursera.org)';
            } else if (line.includes('School of Audio Engineering')) {
              institution = 'School of Audio Engineering, Zürich';
            }
          }
        }
        
        // Check for location
        if (line.includes('Bern') && !location) {
          location = 'Bern';
        } else if (line.includes('Zürich') && !location) {
          location = 'Zürich';
        }
        
        // Check for duration
        if (line.includes('Stündige') || line.includes('Stunden')) {
          const durationMatch = line.match(/(\d+)\s*Stündige?/);
          if (durationMatch) {
            duration = `${durationMatch[1]} Stunden`;
          }
        } else if (line.includes('Abendunterricht')) {
          if (!duration) duration = 'Abendunterricht an zwei Tagen pro Woche';
        }
        
        description += (description ? ' ' : '') + line;
      }
    }
    
    // Suggest tags based on content
    const titleAndDesc = (title + ' ' + description).toLowerCase();
    
    // Technology-related tags
    if (titleAndDesc.includes('react') || titleAndDesc.includes('javascript')) {
      suggestedTags.push('Frontend Development', 'Web Development');
    }
    if (titleAndDesc.includes('angular')) {
      suggestedTags.push('Frontend Development', 'Web Development');
    }
    if (titleAndDesc.includes('typo3')) {
      suggestedTags.push('TYPO3', 'Content Management');
    }
    if (titleAndDesc.includes('project management') || titleAndDesc.includes('projektmanagement')) {
      suggestedTags.push('Project Management');
    }
    if (titleAndDesc.includes('multimedia') || titleAndDesc.includes('media')) {
      suggestedTags.push('Web Development', 'UX/UI Design');
    }
    if (titleAndDesc.includes('photoshop') || titleAndDesc.includes('illustrator') || titleAndDesc.includes('indesign')) {
      suggestedTags.push('UX/UI Design');
    }
    if (titleAndDesc.includes('dreamweaver') || titleAndDesc.includes('web')) {
      suggestedTags.push('Web Development');
    }
    if (titleAndDesc.includes('typescript')) {
      suggestedTags.push('Frontend Development', 'TypeScript');
    }
    if (titleAndDesc.includes('webpack')) {
      suggestedTags.push('Build Tools', 'Web Development');
    }
    if (titleAndDesc.includes('testing')) {
      suggestedTags.push('Testing', 'Quality Assurance');
    }
    if (titleAndDesc.includes('seo')) {
      suggestedTags.push('SEO', 'Web Development');
    }
    
    // Trading and Finance related tags
    if (titleAndDesc.includes('trading') || titleAndDesc.includes('handel')) {
      suggestedTags.push('Trading', 'Financial Technology');
    }
    if (titleAndDesc.includes('machine learning') || titleAndDesc.includes('ml') || titleAndDesc.includes('maschinelles lernen')) {
      suggestedTags.push('Machine Learning', 'Artificial Intelligence');
    }
    if (titleAndDesc.includes('gcp') || titleAndDesc.includes('google cloud') || titleAndDesc.includes('cloud platform')) {
      suggestedTags.push('Google Cloud Platform', 'Cloud Computing');
    }
    if (titleAndDesc.includes('jupyter') || titleAndDesc.includes('notebooks')) {
      suggestedTags.push('Data Science', 'Python');
    }
    if (titleAndDesc.includes('backtesting') || titleAndDesc.includes('backtest')) {
      suggestedTags.push('Quantitative Analysis', 'Trading');
    }
    if (titleAndDesc.includes('regression') || titleAndDesc.includes('prognose') || titleAndDesc.includes('prediction')) {
      suggestedTags.push('Machine Learning', 'Data Analysis');
    }
    if (titleAndDesc.includes('volatilität') || titleAndDesc.includes('volatility') || titleAndDesc.includes('stop-loss')) {
      suggestedTags.push('Risk Management', 'Trading');
    }
    if (titleAndDesc.includes('quantitative') || titleAndDesc.includes('quant')) {
      suggestedTags.push('Quantitative Analysis', 'Financial Technology');
    }
    
    // Remove duplicates from suggested tags
    suggestedTags = [...new Set(suggestedTags)];
    
    // Clean up description
    description = description.replace(/\s+/g, ' ').trim();
    
    // Only add if we have valid data
    if (title && startDate) {
      educationData.push({
        title: title,
        institution: institution,
        start_date: startDate,
        end_date: endDate,
        duration: duration,
        description: description,
        location: location,
        type: type,
        suggested_tags: suggestedTags
      });
      
      console.log(`Added education entry: ${title} (${startDate})`);
    } else {
      console.log(`Skipped entry - missing title (${title}) or start_date (${startDate})`);
    }
  }
  
  // Sort by start date (newest first)
  educationData.sort((a, b) => {
    const yearA = parseInt(a.start_date.match(/\d{4}/)?.[0] || '0');
    const yearB = parseInt(b.start_date.match(/\d{4}/)?.[0] || '0');
    return yearB - yearA;
  });
  
  return educationData;
}

// Function to get or create tags
async function getOrCreateTags(connection, tagNames) {
  const tagIds = [];
  
  for (const tagName of tagNames) {
    // Check if tag exists
    const [existingTags] = await connection.execute(
      'SELECT id FROM tags WHERE tag_name = ?',
      [tagName]
    );
    
    if (existingTags.length > 0) {
      tagIds.push(existingTags[0].id);
    } else {
      // Create new tag
      const [result] = await connection.execute(
        'INSERT INTO tags (tag_name) VALUES (?)',
        [tagName]
      );
      tagIds.push(result.insertId);
      console.log(`Created new tag: ${tagName} (ID: ${result.insertId})`);
    }
  }
  
  return tagIds;
}

// Function to insert education data into database
async function insertEducationData(educationData) {
  const connection = await mysql.createConnection(dbConfig);
  
  try {
    // Clear existing data
    await connection.execute('DELETE FROM education_tags');
    await connection.execute('DELETE FROM education');
    console.log('Cleared existing education data');
    
    // Insert new data
    const insertQuery = `
      INSERT INTO education 
      (title, institution, start_date, end_date, duration, description, location, type)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `;
    
    for (const education of educationData) {
      // Insert education record
      const [result] = await connection.execute(insertQuery, [
        education.title,
        education.institution,
        education.start_date,
        education.end_date,
        education.duration,
        education.description,
        education.location,
        education.type
      ]);
      
      const educationId = result.insertId;
      
      console.log(`Inserted: ${education.title} (${education.start_date} - ${education.end_date || 'Present'})`);
      
      // Handle tags if any are suggested
      if (education.suggested_tags && education.suggested_tags.length > 0) {
        const tagIds = await getOrCreateTags(connection, education.suggested_tags);
        
        // Insert tag assignments
        for (const tagId of tagIds) {
          await connection.execute(
            'INSERT INTO education_tags (education_id, tag_id) VALUES (?, ?)',
            [educationId, tagId]
          );
        }
        
        console.log(`  → Assigned tags: ${education.suggested_tags.join(', ')}`);
      }
    }
    
    console.log(`Successfully imported ${educationData.length} education records`);
    
  } catch (error) {
    console.error('Error inserting education data:', error);
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
    
    console.log('Parsing education data...');
    const educationData = parseEducationData(content);
    
    console.log(`Found ${educationData.length} education entries:`);
    educationData.forEach((edu, index) => {
      console.log(`${index + 1}. ${edu.title} (${edu.start_date} - ${edu.end_date || 'Present'})`);
      console.log(`   Institution: ${edu.institution || 'Not specified'}`);
      console.log(`   Type: ${edu.type}`);
      console.log(`   Duration: ${edu.duration || 'Not specified'}`);
      console.log(`   Location: ${edu.location || 'Not specified'}`);
      if (edu.suggested_tags.length > 0) {
        console.log(`   Suggested Tags: ${edu.suggested_tags.join(', ')}`);
      }
      console.log('');
    });
    
    console.log('\nInserting data into database...');
    await insertEducationData(educationData);
    
    console.log('Education data import completed successfully!');
    
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

// Run the script
if (require.main === module) {
  main();
}

module.exports = { parseEducationData, insertEducationData }; 