const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs').promises;
const { exec } = require('child_process');
const notifier = require('node-notifier');
const OpenAI = require('openai');
const config = require('../config-loader');
const { 
  getDomainReferences,
  getAllEmployment,
  getEmploymentById,
  createEmployment,
  updateEmployment,
  deleteEmployment,
  getAllEducation,
  getEducationById,
  createEducation,
  updateEducation,
  deleteEducation,
  getAllTags,
  createTag,
  updateTag,
  deleteTag,
  getAllDomains,
  getDomainById,
  removeDomainTag,
  removeDomainSubtag
} = require('./database');
require('dotenv').config();
const app = express();

// Keep track of previously seen files
let previousFiles = new Set();

// Add new constants for bid monitoring
const BID_CHECK_INTERVAL = 20000; // 20 seconds
const MAX_BIDS = 200; // Maximum number of bids before removing project
const BATCH_SIZE = 20; // Maximum number of projects to query at once

// Function to play notification sound
function playNotificationSound() {
  notifier.notify({
    title: 'New Project Found!',
    message: 'A new project has been detected',
    sound: true
  });
}

// Function to check for new files
function checkForNewFiles(currentFiles) {
  const newFiles = currentFiles.filter(file => !previousFiles.has(file));
  if (newFiles.length > 0) {
    playNotificationSound();
  }
  previousFiles = new Set(currentFiles);
}

// Enable CORS for all routes
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Cache-Control', 'Pragma', 'Expires', 'If-Modified-Since', 'Authorization'],
  exposedHeaders: ['Content-Length', 'Content-Type', 'Cache-Control', 'Last-Modified', 'ETag']
}));
app.use(express.json());

// Add OPTIONS handling for preflight requests
app.options('*', cors());

// Function to check if test.py is running
function checkTestPyRunning() {
  return new Promise((resolve) => {
    exec('ps aux | grep "[t]est.py"', (error, stdout) => {
      if (error) {
        console.error('Error checking process:', error);
        resolve({ running: false });
        return;
      }
      resolve({ running: stdout.trim().length > 0 });
    });
  });
}

// API Routes - These must come before the static file serving
app.get('/api/indexer/status', async (req, res) => {
  try {
    const status = await checkTestPyRunning();
    res.json(status);
  } catch (error) {
    console.error('Error checking indexer status:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/jobs', async (req, res) => {
  console.log('[Server] /api/jobs called with query params:', req.query);

  // Add stronger cache control headers
  res.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0');
  res.set('Pragma', 'no-cache');
  res.set('Expires', '0');
  res.set('Last-Modified', new Date().toUTCString());
  res.set('ETag', `"${Date.now()}-${Math.random()}"`);
  
  console.log('[Server] Cache headers set:', {
    'cache-control': res.get('Cache-Control'),
    'last-modified': res.get('Last-Modified'),
    'etag': res.get('ETag')
  });

  try {
    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
    
    // Check if directory exists
    try {
      await fs.access(jobsDir);
    } catch (error) {
      return res.status(500).json({ error: 'Jobs directory not found' });
    }
    
    const files = await fs.readdir(jobsDir);
    const jobFiles = files.filter(file => file.startsWith('job_') && file.endsWith('.json'));
    
    console.log('[Server] Found job files:', jobFiles.length);
    
    // Check for new files and play sound if found
    checkForNewFiles(jobFiles);
    
    // Read and parse all job files
    const jobs = await Promise.all(jobFiles.map(async (filename) => {
      const filePath = path.join(jobsDir, filename);
      console.log('[Server] Reading file:', filename);
      
      // Get file stats to check modification time
      const stats = await fs.stat(filePath);
      console.log('[Server] File stats for', filename, ':', {
        modified: stats.mtime.toISOString(),
        size: stats.size
      });
      
      const content = await fs.readFile(filePath, 'utf8');
      const parsed = JSON.parse(content);
      
      // Log bid count for debugging
      console.log('[Server] File', filename, 'bid count:', parsed.project_details?.bid_stats?.bid_count);
      
      return parsed;
    }));
    
    res.json(jobs);
  } catch (error) {
    console.error('Error reading jobs directory:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/jobs/:filename', async (req, res) => {
  try {
    // Use absolute path to jobs directory
    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
    const filePath = path.join(jobsDir, req.params.filename);
    
    console.log('Debug: Current directory:', __dirname);
    console.log('Debug: Jobs directory path:', jobsDir);
    console.log('Debug: Requested file path:', filePath);
    
    // Validate filename to prevent directory traversal
    if (!req.params.filename.startsWith('job_') || !req.params.filename.endsWith('.json')) {
      return res.status(400).json({ error: 'Invalid filename' });
    }
    
    // Check if file exists
    try {
      await fs.access(filePath);
      console.log('Debug: File exists');
    } catch (error) {
      console.error('Debug: File does not exist:', error);
      return res.status(404).json({ error: 'File not found' });
    }
    
    const content = await fs.readFile(filePath, 'utf8');
    res.json(JSON.parse(content));
  } catch (error) {
    console.error('Error reading job file:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/check-json/:projectId', async (req, res) => {
  try {
    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
    
    // Validate project ID format
    const projectId = req.params.projectId;
    if (!projectId || !/^\d+$/.test(projectId)) {
      console.log('Invalid project ID format:', projectId);
      return res.status(400).json({ 
        exists: false, 
        error: 'Invalid project ID format' 
      });
    }
    
    // Ensure jobs directory exists
    try {
      await fs.access(jobsDir);
    } catch (error) {
      console.log('Jobs directory not found:', jobsDir);
      return res.json({ exists: false });
    }
    
    // Read directory contents
    const files = await fs.readdir(jobsDir);
    console.log(`Files in jobs directory: ${files.length}`);
    
    // Look for the exact file name with the new format
    const projectFile = files.find(file => file === `job_${projectId}.json`);
    
    if (projectFile) {
      res.json({ exists: true, filename: projectFile });
    } else {
      res.json({ exists: false });
    }
  } catch (error) {
    console.error('Error checking JSON file:', error);
    res.status(500).json({ 
      exists: false, 
      error: 'Internal server error checking JSON file' 
    });
  }
});

// Add this robust JSON parsing function before generateCorrelationAnalysis
function parseAIResponse(aiResponse, responseType = 'unknown') {
  console.log(`[Debug] Parsing ${responseType} AI response:`, aiResponse);
  
  // Try different strategies to extract JSON
  const strategies = [
    // Strategy 1: Direct JSON parsing (if response is clean JSON)
    () => JSON.parse(aiResponse.trim()),
    
    // Strategy 2: Remove common markdown formatting
    () => {
      const cleaned = aiResponse.replace(/```json\s*|\s*```/g, '').trim();
      return JSON.parse(cleaned);
    },
    
    // Strategy 3: Extract JSON from anywhere in the text
    () => {
      // Find JSON-like content between { and }
      const jsonMatch = aiResponse.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      }
      throw new Error('No JSON found');
    },
    
    // Strategy 4: Find JSON after common prefixes
    () => {
      const prefixes = [
        'Here is the JSON:',
        'Response:',
        'Result:',
        'JSON:',
        '```json',
        '```'
      ];
      
      for (const prefix of prefixes) {
        const index = aiResponse.toLowerCase().indexOf(prefix.toLowerCase());
        if (index !== -1) {
          const afterPrefix = aiResponse.substring(index + prefix.length).trim();
          const cleaned = afterPrefix.replace(/```\s*$/, '').trim();
          const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            return JSON.parse(jsonMatch[0]);
          }
        }
      }
      throw new Error('No JSON found after prefixes');
    },
    
    // Strategy 5: Extract multiple JSON objects and take the first valid one
    () => {
      // Find potential JSON objects by counting braces
      let braceCount = 0;
      let startIndex = -1;
      let jsonObjects = [];
      
      for (let i = 0; i < aiResponse.length; i++) {
        if (aiResponse[i] === '{') {
          if (braceCount === 0) {
            startIndex = i;
          }
          braceCount++;
        } else if (aiResponse[i] === '}') {
          braceCount--;
          if (braceCount === 0 && startIndex !== -1) {
            const jsonCandidate = aiResponse.substring(startIndex, i + 1);
            jsonObjects.push(jsonCandidate);
            startIndex = -1;
          }
        }
      }
      
      // Try to parse each extracted JSON object
      for (const jsonObj of jsonObjects) {
        try {
          return JSON.parse(jsonObj);
        } catch (e) {
          continue;
        }
      }
      throw new Error('No valid JSON objects found with brace counting');
    }
  ];
  
  // Try each strategy
  for (let i = 0; i < strategies.length; i++) {
    try {
      const result = strategies[i]();
      console.log(`[Debug] Successfully parsed ${responseType} with strategy ${i + 1}:`, result);
      return result;
    } catch (error) {
      console.log(`[Debug] Strategy ${i + 1} failed for ${responseType}:`, error.message);
      continue;
    }
  }
  
  // If all strategies fail, throw an error with the original response for debugging
  console.error(`[Debug] All parsing strategies failed for ${responseType}. Original response:`, aiResponse);
  throw new Error(`Failed to parse ${responseType} AI response: No valid JSON found`);
}

// Add this function before generateCorrelationAnalysis
async function generateCorrelationAnalysis(jobData) {
  // Get all data from database
  console.log('[Debug] Fetching correlation data from database...');
  const [domainRefs, employmentData, educationData] = await Promise.all([
    getDomainReferences(),
    getAllEmployment(),
    getAllEducation()
  ]);
  
  console.log('[Debug] Found data:', {
    domains: domainRefs.references.domains.length,
    employment: employmentData.length,
    education: educationData.length
  });
  
  // Create domain context string
  const domainContext = domainRefs.references.domains.map(ref => {
    const tags = ref.tags.join(', ');
    const subtags = ref.subtags.join(', ');
    return `Domain: ${ref.domain}\nTitle: ${ref.title}\nDescription: ${ref.description}\nTags: ${tags}\nSubtags: ${subtags}`;
  }).join('\n\n');

  // Create employment context string
  const employmentContext = employmentData.map(emp => {
    return `Company: ${emp.company}\nPosition: ${emp.position}\nDescription: ${emp.description}\nTags: ${emp.tags ? emp.tags.join(', ') : 'No tags'}`;
  }).join('\n\n');

  // Create education context string
  const educationContext = educationData.map(edu => {
    return `Institution: ${edu.institution}\nDegree: ${edu.degree}\nField: ${edu.field_of_study}\nDescription: ${edu.description || 'No description'}\nTags: ${edu.tags ? edu.tags.join(', ') : 'No tags'}`;
  }).join('\n\n');

  // Ensure skills exists and is an array, otherwise use empty array
  const skills = jobData?.project_details?.jobs?.map(job => job.name) || [];
  console.log('[Debug] Extracted project skills:', skills);
  
  const messages = [
    {
      "role": "system",
      "content": "You are an AI assistant that analyzes software projects and finds relevant reference projects, employment history, and education from our portfolio and background."
    },
    {
      "role": "user",
      "content": `Project Title: ${jobData?.project_details?.title || ''}\nProject Description:\n${jobData?.project_details?.description || ''}\nProject Skills: ${skills.join(', ')}`
    },
    {
      "role": "user",
      "content": `Here are our reference domains and their tags/subtags:\n\n${domainContext}`
    },
    {
      "role": "user",
      "content": `Here is our employment history:\n\n${employmentContext}`
    },
    {
      "role": "user",
      "content": `Here is our education background:\n\n${educationContext}`
    },
    {
      "role": "user",
      "content": `Please analyze the project and find the most relevant references from our portfolio, employment history, and education that match best with the project. Return your response in this JSON format:
{
  "correlation_analysis": {
    "domains": [
      {
        "domain": "<domain from our portfolio>",
        "title": "<domain title>",
        "relevance_score": <number between 0 and 1>,
        "tags": [
          {
            "name": "<tag or subtag from our portfolio>",
            "relevance_score": <number between 0 and 1>
          }
        ]
      }
    ],
    "employment": [
      {
        "company": "<company name>",
        "position": "<position title>",
        "relevance_score": <number between 0 and 1>,
        "description": "<brief description why relevant>"
      }
    ],
    "education": [
      {
        "institution": "<institution name>",
        "degree": "<degree title>",
        "field_of_study": "<field of study>",
        "relevance_score": <number between 0 and 1>,
        "description": "<brief description why relevant>"
      }
    ]
  }
}

Important:
1. Only include items from our portfolio/background (provided above) that are actually relevant
2. Return maximum 3-5 most relevant items per category
3. If no relevant items are found for a category, return an empty array for that category
4. Ensure relevance_score accurately reflects how well the item matches the project
5. For employment and education, provide a brief description why it's relevant to this project`
    }
  ];

  console.log('[Debug] Final correlation analysis messages for AI:', JSON.stringify(messages, null, 2));
  return messages;
}

// Then modify the generateAIMessages function to accept correlation results
function generateAIMessages(vyftec_context, score, explanation, jobData, correlationResults) {
  // Create context string from correlation results
  let correlationContext = '';
  
  if (correlationResults?.correlation_analysis) {
    const analysis = correlationResults.correlation_analysis;
    
    // Add relevant domains
    if (analysis.domains && analysis.domains.length > 0) {
      correlationContext += 'Relevant Portfolio Projects:\n';
      analysis.domains.forEach(domain => {
        const tags = domain.tags?.map(tag => tag.name).join(', ') || '';
        correlationContext += `- ${domain.domain} (${domain.title}) - Tags: ${tags}\n`;
      });
      correlationContext += '\n';
    }
    
    // Add relevant employment
    if (analysis.employment && analysis.employment.length > 0) {
      correlationContext += 'Relevant Employment Experience:\n';
      analysis.employment.forEach(emp => {
        correlationContext += `- ${emp.position} at ${emp.company} - ${emp.description}\n`;
      });
      correlationContext += '\n';
    }
    
    // Add relevant education
    if (analysis.education && analysis.education.length > 0) {
      correlationContext += 'Relevant Education:\n';
      analysis.education.forEach(edu => {
        correlationContext += `- ${edu.degree} in ${edu.field_of_study} from ${edu.institution} - ${edu.description}\n`;
      });
      correlationContext += '\n';
    }
  }

  return [
    {
      "role": "system",
      "content": "You are a project manager at the Vyftec web agency, responsible for pitching to job offers. Your goal is to craft high-quality proposals that win us new contracts."
    },
    {
      "role": "user",
      "content": `Company Context:\n${vyftec_context}`
    },
    {
      "role": "user",
      "content": `Relevant Experience and Portfolio:\n${correlationContext}`
    },
    {
      "role": "user",
      "content": `Project Score: ${score}\nProject Explanation:\n${explanation}`
    },
    {
      "role": "user",
      "content": `Project Title: ${jobData.project_details.title}\nProject Description:\n${jobData.project_details.description}`
    },
    {
      "role": "user",
      "content": `Please generate a bid text in the following JSON format:
{
  "bid_teaser": {
    "greeting": "<string>",
    "first_paragraph": "<string, 200-300 characters>",
    "second_paragraph": "<string, 200-300 characters>",
    "third_paragraph": "<string, 200-300 characters>",
    "fourth_paragraph": "<string, 200-300 characters>",
    "closing": "<string>",
    "question": "<string, 50-100 characters>",
    "estimated_price": "<number>",
    "estimated_days": "<number>"
  }
}

## Goal
**The goal is to write high-quality bid texts so the client initiates a conversation with us** and we ultimately win the project.

## Terminology
Write in professional project management and executive language. Adapt to the client's tone, politeness, and formality. Be sympathetic. Make sense, be logical, follow the thread, and keep the flow. Make it easily readable and formulate fluently, cool, and funny. Don't ask questions. Don't use words like experience, expertise, specialization. Don't repeat wordings given by the client too much, instead try to variate and use synonyms in a natural way. Keep the answers short and concise. Don't ask questions.

## Offer Length / Number of Paragraphs / Paragraphs to omit
Before starting decide about the wordcound of the complete offer and the amount of paragraphs to use **based on the length and detail level of the job description of the client, decide how long our texts should be and how many paragraphs to use**. 
- **Let the length of the clients job decription determine the length of our overall bid text.** While we stay below the client's wordcount, we try to not to overuse paragraphs. Example: When the description is 400 signs we could max. open one paragraph as they are 200-300 characters.
- The first paragraph is mandatory. 
-**In many cases you will only use the first paragraph**, when the description is short and not detailed and machine written. 
- **Only if the job description has a reasonably high level of detail and length, you will use more paragraphs.**
- **You can omit entire paragraphs (except first_paragraph)**, decide which paragraphs are relevant for this job posting. 
- If you decide to omit a paragraph, just use **an empty variable in the json**. 
- When you don't have much valuable to say in a paragraph omit it. 
- **Stay slightly below the client's wordcount but don't exceed our paragraph limits**. 

## Translation
Determine the language of the project and translate the bid text to the language of the project description text.

## Greeting / Closing
- Create sympathetic, casual greeting that matches the style of the offer
- Mirror the client's formality, tone, and politeness, but make it slightly more relaxed and funny if possible
- If client mentions names in description, use name as greeting
- Closing and farewell follow the same rules

## Elements / Paragraphs
- **Greeting** (Opening)
- **First Paragraph** (Solution text - MANDATORY)
- **Second Paragraph** (Introduction text)
- **Third Paragraph** (Correlation text)
- **Fourth Paragraph** (Portfolio projects, education, employment)
- **Closing** (Farewell)

## Greeting
Create a sympathetic, casual greeting that matches the style of the offer. Mirror the client's formality, tone, and politeness, but make it slightly more relaxed and funny if possible. If the client mentions names in the description, use the name as a greeting. Don't formalte anything else than the greeting with the name if available.

## First Paragraph (MANDATORY)

### Objective
Generate the FIRST PARAGRAPH of a freelance job application. Address the following points sequentially in ONE cohesive paragraph (max 600 characters). If a point can't be fulfilled or space remains after addressing a point, proceed to the next without gaps.

### Process Flow
1. **Simple Question/Task Resolution**  
   - If job post contains direct technical/process questions (e.g., "How would you solve X?"):  
     → Research → Answer concisely in 1 sentence.  
   - *Example: "For PDF conversion, I recommend Python's PyMuPDF library for its batch processing capabilities."*

2. **Application Requirements Alignment**  
   - Mirror client's requested structure/format:  
     • If client uses bullet points → Use bullet points  
     • If numbered list → Use numbered list  
     • If plain text → Use plain text  
   - → Cover ALL explicit requirements from "How to apply" section.  
   - *Example: "Per your requirements: (1) Laravel expertise (2) React integration (3+ years experience - confirmed in my 5-year track record."*

3. **Unspoken Needs Response**  
   - Read between lines for:  
     • Urgency → Highlight availability/rapid deployment  
     • Previous failures → Emphasize reliability  
     • Complexity → Show specialized expertise  
   - → Respond to implied needs in 1 sentence.  
   - *Example: "Having rescued 10+ stalled projects, I ensure seamless handover with documented workflows."*

4. **Relevant Experience Match**  
   - Cross-reference project tags with our metadata:  
     → Extract 1-2 domain/task-specific references.  
     → Format: "At [Company](URL), I [Task] using [Tech] for [Similar Outcome]."  
   - *Example: "For BlueMouse AG, I built Laravel/JS dashboards optimizing Reishauer's manufacturing analytics."*

5. **Solution Blueprint**  
   - Propose high-level approach:  
     → Phasing (e.g., "First prototype → Feedback → Scaling")  
     → Tech stack (e.g., "Laravel/Vue for real-time updates")  
     → Risk mitigation (e.g., "Test-driven development")  
   - → Keep to 1 actionable sentence.  

### Output Rules
- **Seamless integration:** Connect points with transition words (e.g., "Moreover," "Specifically," "Building on this")
- **No markdown:** Plain English only
- **Authority tone:** Confident but humble
- **Character limit:** Strictly 200-600 characters

Use the relevant experience and portfolio information provided above to strengthen your proposal where applicable.

## Second Paragraph (Introduction Text)
Brief introduction of Vyftec and our capabilities relevant to this project. Keep it concise and focused on what matters for this specific project.

## Third Paragraph (Correlation Text)
Explain the correlation between our skills/background and the project requirements. Use the explanation text provided to show why we're a good fit.

## Fourth Paragraph (Portfolio Projects, Education, Employment)
Include relevant portfolio projects, education, and employment history based on the correlation analysis provided. Format as a concise overview of our relevant background.

## Closing
Write a professional but relaxed closing that matches the tone of the greeting. Include a call to action or invitation for further discussion. **Keep it very short and concise.**

## Question
Take care not to repeat anything from other paragraphs in the question. A question that we ask the employer about the project, the goal is it to provide an accurate estimation. Be very specific and not general. It might ask about the clarification of unclear points, what we need in order to create a binding fixed-price estimation, or asking for confirmation of an approach, technologies to use, ways of working, and the like. Keep it short and concise and ask only for one thing. And do not forget to translate the whole bid texts to the projects description texts language.

## Estimated Price
Calculate an estimated price around the average price found in the project data. Use the following rules:
- Currency: Consider the currency of the project data and calculate the price in the same currency.
- Base calculation: Start with the project's average bid price
- Adjust upward: Don't move farer away than 30% from the average price. If the average price is too low (below reasonable market rates), increase it moderately
- Adjust downward: Don't move farer away than 30% from the average price. If the average price is too high (above reasonable market rates), decrease it slightly
- Consider project complexity: Factor in the technical requirements and scope
- Stay competitive: Keep the price attractive while ensuring profitability
- Output: Provide the final estimated price as a number (without currency symbols)

## Estimated Days
Calculate the estimated days needed for project completion using the same logic as the price estimation:
- Base calculation: Estimate realistic timeframe based on project scope and complexity
- Consider average patterns: If similar projects typically take certain timeframes, use that as reference
- Adjust for efficiency: Account for our team's capabilities and workflow
- Buffer time: Include reasonable buffer for testing, revisions, and deployment
- Output: Provide the estimated days as a number`
    }
  ];
}

// Then modify the app.post route to use this function
app.post('/api/generate-bid/:projectId', async (req, res) => {
  try {
    console.log('[Debug] Generate bid request received:', {
      projectId: req.params.projectId,
      body: req.body,
      headers: req.headers
    });

    // Disable caching
    res.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    res.set('Pragma', 'no-cache');
    res.set('Expires', '0');

    const { score, explanation } = req.body;
    const projectId = req.params.projectId;

    if (!score || !explanation) {
      console.log('[Debug] Missing parameters:', { score, explanation });
      return res.status(400).json({ error: 'Missing required parameters: score and explanation' });
    }

    // Get job data from file
    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
    console.log('[Debug] Looking for jobs in directory:', jobsDir);
    let projectFile = null;
    let jobData = null;

    try {
      const files = await fs.readdir(jobsDir);
      console.log('[Debug] Found files:', files);
      projectFile = files.find(file => file === `job_${projectId}.json`);
      console.log('[Debug] Found project file:', projectFile);
      
      if (!projectFile) {
        return res.status(404).json({ error: 'Project not found' });
      }

      const filePath = path.join(jobsDir, projectFile);
      console.log('[Debug] Reading file:', filePath);
      const content = await fs.readFile(filePath, 'utf8');
      jobData = JSON.parse(content);
    } catch (error) {
      console.error('[Debug] Error reading job file:', error);
      return res.status(500).json({ error: 'Failed to read job data' });
    }

    // Read vyftec-context.md and lebenslauf.md
    let vyftec_context = '';
    try {
      const contextPath = path.join(__dirname, '..', '..', 'vyftec-context.md');
      vyftec_context = await fs.readFile(contextPath, 'utf8');
      console.log('[Debug] Successfully read context file');
      
      // Read and append lebenslauf.md
      try {
        const lebenslaufPath = path.join(__dirname, '..', '..', 'lebenslauf.md');
        const lebenslaufContent = await fs.readFile(lebenslaufPath, 'utf8');
        vyftec_context += '\n\n' + lebenslaufContent;
        console.log('[Debug] Successfully read and appended lebenslauf file');
      } catch (error) {
        console.log('[Debug] Warning: Could not read lebenslauf.md:', error.message);
      }
    } catch (error) {
      console.error('[Debug] Error reading context file:', error);
      return res.status(500).json({ error: 'Failed to read context file' });
    }

    try {
      const aiProvider = config.AI_PROVIDER;
      console.log('[Debug] Selected AI provider:', aiProvider);
      
      // First AI request - Generate correlation analysis
      const correlationMessages = await generateCorrelationAnalysis(jobData);
      
      if (aiProvider === 'chatgpt') {
        const openai = new OpenAI({
          apiKey: process.env.OPENAI_API_KEY
        });

        // Generate correlation analysis
        const correlationResponse = await openai.chat.completions.create({
          model: process.env.OPENAI_MODEL || "gpt-3.5-turbo",
          messages: correlationMessages,
          temperature: 0.7,
          max_tokens: 1000
        });
        
        const correlationAiResponse = correlationResponse.choices[0].message.content;
        
        // Parse the AI response using robust parsing
        let correlationResults;
        try {
          correlationResults = parseAIResponse(correlationAiResponse, 'correlation analysis');
        } catch (error) {
          console.error('[Debug] Failed to parse correlation analysis response:', error);
          throw new Error('Failed to parse correlation analysis response');
        }

        // Second AI request - Generate bid text
        console.log('[Debug] Generating bid text...');
        const bidMessages = generateAIMessages(vyftec_context, score, explanation, jobData, correlationResults);
        
        const bidResponse = await openai.chat.completions.create({
          model: process.env.OPENAI_MODEL || "gpt-3.5-turbo",
          messages: bidMessages,
          temperature: 0.7,
          max_tokens: 1000
        });
        
        const aiResponse = bidResponse.choices[0].message.content;
        console.log('[Debug] Raw AI response:', aiResponse);
        
        // Parse the AI response using robust parsing
        let parsedResponse;
        try {
          parsedResponse = parseAIResponse(aiResponse, 'bid text');
        } catch (error) {
          console.error('[Debug] Failed to parse bid text response:', error);
          throw new Error('Failed to parse bid text response');
        }

        // Create a consistent bid text structure
        let finalBidText;
        if (parsedResponse.bid_text && parsedResponse.bid_text.bid_teaser) {
          // Response is already in the correct format
          finalBidText = parsedResponse.bid_text;
        } else if (parsedResponse.bid_teaser) {
          // Convert to the expected format
          finalBidText = {
            bid_teaser: parsedResponse.bid_teaser
          };
        } else {
          console.error('[Debug] Invalid response structure:', parsedResponse);
          throw new Error('Invalid AI response format: Missing bid_teaser');
        }

        // Clean up the bid_teaser strings
        Object.keys(finalBidText.bid_teaser).forEach(key => {
          if (typeof finalBidText.bid_teaser[key] === 'string') {
            finalBidText.bid_teaser[key] = finalBidText.bid_teaser[key]
              .replace(/\n/g, ' ')
              .replace(/\s+/g, ' ')
              .trim();
          }
        });

        // The AI now handles all paragraph content based on correlation analysis provided in the prompt context
        // No manual second paragraph construction needed

        // Update the job file
        if (projectFile) {
          const filePath = path.join(jobsDir, projectFile);
          
          // Ensure ranking object exists
          if (!jobData.ranking) {
            jobData.ranking = {};
          }
          
          // Update bid text and correlation results
          jobData.ranking.bid_text = finalBidText;
          jobData.ranking.bid_teaser = finalBidText.bid_teaser;
          jobData.ranking.correlation_analysis = correlationResults;
          
          console.log('[Debug] Final bid_teaser being saved to ranking:', JSON.stringify(finalBidText.bid_teaser, null, 2));
          console.log('[Debug] ranking.bid_teaser after assignment:', JSON.stringify(jobData.ranking.bid_teaser, null, 2));
          
          // Write the updated data back to the file
          const updatedContent = JSON.stringify(jobData, null, 2);
          await fs.writeFile(filePath, updatedContent, 'utf8');
          console.log('[Debug] Successfully updated JSON file');
        }

        // Return the bid text and correlation results
        res.json({
          success: true,
          bid_text: finalBidText,
          bid_teaser: finalBidText.bid_teaser,
          correlation_analysis: correlationResults,
          project_id: projectId,
          message: 'Bid text generated successfully'
        });

      } else if (aiProvider === 'deepseek') {
        if (!config.DEEPSEEK_API_BASE || !config.DEEPSEEK_API_KEY) {
          throw new Error('DeepSeek configuration is incomplete');
        }

        const deepseekUrl = `${config.DEEPSEEK_API_BASE}/chat/completions`;
        console.log('[Debug] DeepSeek API URL:', deepseekUrl);

        // Generate correlation analysis
        const correlationResponse = await fetch(deepseekUrl, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${config.DEEPSEEK_API_KEY}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            model: config.DEEPSEEK_MODEL,
            messages: correlationMessages,
            temperature: 0.7,
            max_tokens: 1000
          })
        });

        if (!correlationResponse.ok) {
          const errorText = await correlationResponse.text();
          console.error('[Debug] DeepSeek API error response:', {
            status: correlationResponse.status,
            statusText: correlationResponse.statusText,
            errorText
          });
          throw new Error(`DeepSeek API error: ${correlationResponse.status} - ${correlationResponse.statusText}. Details: ${errorText}`);
        }

        const correlationData = await correlationResponse.json();
        const correlationAiResponse = correlationData.choices[0].message.content;
        console.log('[Debug] Raw AI response:', correlationAiResponse);
        
        // Parse the AI response using robust parsing
        let correlationResults;
        try {
          correlationResults = parseAIResponse(correlationAiResponse, 'correlation analysis');
        } catch (error) {
          console.error('[Debug] Failed to parse correlation analysis response:', error);
          throw new Error('Failed to parse correlation analysis response');
        }

        // Second AI request - Generate bid text
        console.log('[Debug] Generating bid text...');
        const bidMessages = generateAIMessages(vyftec_context, score, explanation, jobData, correlationResults);
        
        const bidResponse = await fetch(deepseekUrl, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${config.DEEPSEEK_API_KEY}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            model: config.DEEPSEEK_MODEL,
            messages: bidMessages,
            temperature: 0.7,
            max_tokens: 1000
          })
        });

        if (!bidResponse.ok) {
          const errorText = await bidResponse.text();
          console.error('[Debug] DeepSeek API error response:', {
            status: bidResponse.status,
            statusText: bidResponse.statusText,
            errorText
          });
          throw new Error(`DeepSeek API error: ${bidResponse.status} - ${bidResponse.statusText}. Details: ${errorText}`);
        }

        const bidData = await bidResponse.json();
        const aiResponse = bidData.choices[0].message.content;
        console.log('[Debug] Raw AI response:', aiResponse);
        
        // Parse the AI response using robust parsing
        let parsedResponse;
        try {
          parsedResponse = parseAIResponse(aiResponse, 'bid text');
        } catch (error) {
          console.error('[Debug] Failed to parse bid text response:', error);
          throw new Error('Failed to parse bid text response');
        }

        // Create a consistent bid text structure
        let finalBidText;
        if (parsedResponse.bid_text && parsedResponse.bid_text.bid_teaser) {
          // Response is already in the correct format
          finalBidText = parsedResponse.bid_text;
        } else if (parsedResponse.bid_teaser) {
          // Convert to the expected format
          finalBidText = {
            bid_teaser: parsedResponse.bid_teaser
          };
        } else {
          console.error('[Debug] Invalid response structure:', parsedResponse);
          throw new Error('Invalid AI response format: Missing bid_teaser');
        }

        // Clean up the bid_teaser strings
        Object.keys(finalBidText.bid_teaser).forEach(key => {
          if (typeof finalBidText.bid_teaser[key] === 'string') {
            finalBidText.bid_teaser[key] = finalBidText.bid_teaser[key]
              .replace(/\n/g, ' ')
              .replace(/\s+/g, ' ')
              .trim();
          }
        });

        // The AI now handles all paragraph content based on correlation analysis provided in the prompt context
        // No manual second paragraph construction needed

        // Update the job file
        if (projectFile) {
          const filePath = path.join(jobsDir, projectFile);
          
          // Ensure ranking object exists
          if (!jobData.ranking) {
            jobData.ranking = {};
          }
          
          // Update bid text and correlation results
          jobData.ranking.bid_text = finalBidText;
          jobData.ranking.bid_teaser = finalBidText.bid_teaser;
          jobData.ranking.correlation_analysis = correlationResults;
          
          console.log('[Debug] Final bid_teaser being saved to ranking:', JSON.stringify(finalBidText.bid_teaser, null, 2));
          console.log('[Debug] ranking.bid_teaser after assignment:', JSON.stringify(jobData.ranking.bid_teaser, null, 2));
          
          // Write the updated data back to the file
          const updatedContent = JSON.stringify(jobData, null, 2);
          await fs.writeFile(filePath, updatedContent, 'utf8');
          console.log('[Debug] Successfully updated JSON file');
        }

        // Return the bid text and correlation results
        res.json({
          success: true,
          bid_text: finalBidText,
          bid_teaser: finalBidText.bid_teaser,
          correlation_analysis: correlationResults,
          project_id: projectId,
          message: 'Bid text generated successfully'
        });
      } else {
        throw new Error(`Unsupported AI provider: ${aiProvider}`);
      }
    } catch (error) {
      console.error('[Debug] Error in generate-bid endpoint:', error);
      res.status(500).json({ 
        error: error.message,
        details: 'Failed to generate or process AI response'
      });
    }
  } catch (error) {
    console.error('[Debug] Error in generate-bid endpoint:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add test endpoint for Freelancer API authentication
app.get('/api/test-freelancer-auth', async (req, res) => {
  try {
    console.log('[Debug] Testing Freelancer API authentication...');
    
    // Check if configuration is available
    if (!config.FREELANCER_API_KEY || config.FREELANCER_API_KEY === 'your_freelancer_oauth_token_here') {
      return res.json({
        success: false,
        error: 'FREELANCER_API_KEY not configured properly',
        current_key: config.FREELANCER_API_KEY ? `${config.FREELANCER_API_KEY.substring(0, 10)}...` : 'null',
        instructions: 'Please update config.py with your actual Freelancer OAuth token'
      });
    }
    
    if (!config.FREELANCER_USER_ID || config.FREELANCER_USER_ID === 'webskillssl') {
      console.log('[Debug] User ID configured as:', config.FREELANCER_USER_ID);
    }
    
    // Test API call to get user profile
    const testResponse = await fetch('https://www.freelancer.com/api/users/0.1/users/self', {
      method: 'GET',
          headers: {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY
      }
    });
    
    console.log('[Debug] Test API response status:', testResponse.status);
    
    if (!testResponse.ok) {
      const errorText = await testResponse.text();
      return res.json({
        success: false,
        error: `Freelancer API test failed: ${testResponse.status}`,
        error_details: errorText,
        configured_key: config.FREELANCER_API_KEY ? `${config.FREELANCER_API_KEY.substring(0, 10)}...` : 'null',
        configured_user_id: config.FREELANCER_USER_ID
      });
    }
    
    const userData = await testResponse.json();
    console.log('[Debug] Test API success, user data:', userData);
    
    res.json({
      success: true,
      message: 'Freelancer API authentication successful',
      user_data: userData.result,
      configured_user_id: config.FREELANCER_USER_ID,
      api_scopes_needed: ['basic', 'fln:project_manage']
    });
    
  } catch (error) {
    console.error('[Debug] Error testing Freelancer API:', error);
    res.status(500).json({
      success: false,
      error: error.message,
      configured_key: config.FREELANCER_API_KEY ? `${config.FREELANCER_API_KEY.substring(0, 10)}...` : 'null',
      configured_user_id: config.FREELANCER_USER_ID
    });
  }
});

// Add new endpoint for sending applications
app.post('/api/send-application/:projectId', async (req, res) => {
  try {
    console.log('[Debug] Send application request received:', {
      projectId: req.params.projectId,
      body: req.body,
      headers: req.headers
    });

    // Disable caching
    res.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    res.set('Pragma', 'no-cache');
    res.set('Expires', '0');

    const projectId = req.params.projectId;

    // Get job data from file
    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
    console.log('[Debug] Looking for jobs in directory:', jobsDir);
    let projectFile = null;
    let jobData = null;

    try {
      const files = await fs.readdir(jobsDir);
      console.log('[Debug] Found files:', files);
      projectFile = files.find(file => file === `job_${projectId}.json`);
      console.log('[Debug] Found project file:', projectFile);
      
      if (!projectFile) {
        return res.status(404).json({ error: 'Project not found' });
      }

      const filePath = path.join(jobsDir, projectFile);
      console.log('[Debug] Reading file:', filePath);
      const content = await fs.readFile(filePath, 'utf8');
      jobData = JSON.parse(content);
        } catch (error) {
      console.error('[Debug] Error reading job file:', error);
      return res.status(500).json({ error: 'Failed to read job data' });
    }

    // Check if bid text is available
    if (!jobData.ranking?.bid_teaser) {
      return res.status(400).json({ error: 'No bid text available for this project' });
    }

    // Format the bid description with all components
    let bidDescription = '';
    const bidTeaser = jobData.ranking.bid_teaser;

    if (bidTeaser.greeting) {
      bidDescription += bidTeaser.greeting + '\n\n';
    }
    
    if (bidTeaser.first_paragraph) {
      bidDescription += bidTeaser.first_paragraph + '\n\n';
    }

    if (bidTeaser.second_paragraph) {
      bidDescription += bidTeaser.second_paragraph + '\n\n';
    }

    if (bidTeaser.third_paragraph) {
      bidDescription += bidTeaser.third_paragraph + '\n\n';
    }

    if (bidTeaser.fourth_paragraph) {
      bidDescription += bidTeaser.fourth_paragraph + '\n\n';
    }

    if (bidTeaser.closing) {
      bidDescription += bidTeaser.closing + '\n\n';
    }

    bidDescription += 'Damian Hunziker';

    // Replace — with ...
    bidDescription = bidDescription.replace('—', '... ');

    // Get numeric user ID from username
    let numericUserId = config.FREELANCER_USER_ID;
    
    // We know that "webskillssl" maps to user ID 3953491 from our tests
    if (config.FREELANCER_USER_ID === "webskillssl") {
      numericUserId = 3953491;
      console.log('[Debug] Using known user ID for webskillssl:', numericUserId);
    } else if (typeof config.FREELANCER_USER_ID === 'string' && isNaN(config.FREELANCER_USER_ID)) {
      try {
        console.log('[Debug] Getting numeric user ID for username:', config.FREELANCER_USER_ID);
        const userResponse = await fetch(`https://www.freelancer.com/api/users/0.1/users?usernames[]=${config.FREELANCER_USER_ID}`, {
          method: 'GET',
          headers: {
            'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
            'Content-Type': 'application/json'
          }
        });
        
        if (userResponse.ok) {
          const userData = await userResponse.json();
          // The user data is keyed by user ID, not username - get the first entry
          const userEntries = Object.entries(userData.result?.users || {});
          if (userEntries.length > 0) {
            const [userId, userInfo] = userEntries[0];
            numericUserId = parseInt(userId);
            console.log('[Debug] Found numeric user ID:', numericUserId, 'for username:', userInfo.username);
        } else {
            console.error('[Debug] User not found in response:', userData);
            throw new Error(`User '${config.FREELANCER_USER_ID}' not found`);
          }
        } else {
          const errorText = await userResponse.text();
          console.error('[Debug] Failed to get user ID:', errorText);
          throw new Error(`Failed to get user ID: ${userResponse.status}`);
        }
      } catch (userError) {
        console.error('[Debug] Error getting numeric user ID:', userError);
        return res.json({
          success: false,
          api_error: true,
          error_message: `Failed to get user ID: ${userError.message}`,
          formatted_text: bidDescription.trim(),
          project_url: jobData.project_url || `https://www.freelancer.com/projects/${projectId}`,
          project_id: projectId,
          message: 'Could not resolve user ID. Please submit manually using the formatted text.'
        });
      }
    }

    // Get project budget information for minimum price validation
    const projectBudget = jobData.project_details?.budget;
    const projectCurrency = jobData.project_details?.currency;
    
    console.log(`[Debug] Project budget info - Min: ${projectBudget?.minimum}, Max: ${projectBudget?.maximum}, Currency: ${projectCurrency?.code}`);
    
    // Calculate minimum allowed bid amount
    let minimumBidAmount = 100; // Default fallback
    if (projectBudget && projectBudget.minimum) {
      minimumBidAmount = projectBudget.minimum;
      
      // If project currency is not USD, convert to USD for API submission
      if (projectCurrency && projectCurrency.code !== 'USD' && projectCurrency.exchange_rate) {
        const originalAmount = minimumBidAmount;
        // Convert to USD: project_currency_amount / exchange_rate = USD_amount
        minimumBidAmount = Math.ceil(projectBudget.minimum / projectCurrency.exchange_rate);
        console.log(`[Debug] Currency conversion: ${originalAmount} ${projectCurrency.code} → ${minimumBidAmount} USD (rate: ${projectCurrency.exchange_rate})`);
      }
    }
    
    // Get the AI estimated price or use fallback
    let bidAmount = bidTeaser.estimated_price || minimumBidAmount;
    
    // Ensure bid amount is not below minimum
    if (bidAmount < minimumBidAmount) {
      bidAmount = minimumBidAmount;
      console.log(`[Debug] Bid amount adjusted from ${bidTeaser.estimated_price} to ${bidAmount} (minimum: ${minimumBidAmount})`);
    }
    
    console.log(`[Debug] Final bid amount: ${bidAmount} USD (estimated: ${bidTeaser.estimated_price}, minimum: ${minimumBidAmount})`);

    // Prepare bid data for Freelancer API
    const bidData = {
      project_id: parseInt(projectId),
      bidder_id: parseInt(numericUserId), // Use numeric user ID
      amount: bidAmount,
      period: bidTeaser.estimated_days || 7, // Use estimated days or fallback
      milestone_percentage: 100, // Full payment on completion
      description: bidDescription.trim()
    };

    console.log('[Debug] Preparing to submit bid:', bidData);

    // Submit bid to Freelancer API
    try {
      const freelancerResponse = await fetch('https://www.freelancer.com/api/projects/0.1/bids/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Freelancer-OAuth-V1': config.FREELANCER_API_KEY
        },
        body: JSON.stringify(bidData)
      });

      console.log('[Debug] Freelancer API response status:', freelancerResponse.status);

      if (!freelancerResponse.ok) {
        const errorText = await freelancerResponse.text();
        console.error('[Debug] Freelancer API error:', {
          status: freelancerResponse.status,
          statusText: freelancerResponse.statusText,
          errorText
        });
        
        // If API call fails, return formatted text for manual submission
        return res.json({
          success: false,
          api_error: true,
          error_message: `Freelancer API error: ${freelancerResponse.status} - ${errorText}`,
          formatted_text: bidDescription.trim(),
          project_url: jobData.project_url || `https://www.freelancer.com/projects/${projectId}`,
          project_id: projectId,
          bid_data: bidData,
          message: 'API submission failed. Please submit manually using the formatted text.'
        });
      }

      const freelancerData = await freelancerResponse.json();
      console.log('[Debug] Freelancer API success response:', freelancerData);

      // Update the job file to mark bid as submitted
        if (projectFile) {
          const filePath = path.join(jobsDir, projectFile);
          
        // Ensure buttonStates object exists
        if (!jobData.buttonStates) {
          jobData.buttonStates = {};
        }
        
        // Mark bid as submitted with API data
        jobData.buttonStates.bidSubmitted = true;
        jobData.bidSubmittedAt = new Date().toISOString();
        jobData.freelancerBidData = freelancerData.result;
        jobData.bidAmount = bidData.amount;
        jobData.bidPeriod = bidData.period;
          
          // Write the updated data back to the file
          const updatedContent = JSON.stringify(jobData, null, 2);
          await fs.writeFile(filePath, updatedContent, 'utf8');
        console.log('[Debug] Successfully marked bid as submitted');
        }

      // Return success response
        res.json({
        success: true,
        bid_submitted: true,
        freelancer_response: freelancerData,
        bid_data: bidData,
        project_url: jobData.project_url || `https://www.freelancer.com/projects/${projectId}`,
        project_id: projectId,
        message: 'Bid successfully submitted to Freelancer.com!'
      });

    } catch (apiError) {
      console.error('[Debug] Error calling Freelancer API:', apiError);
      
      // If API call fails, return formatted text for manual submission
      return res.json({
        success: false,
        api_error: true,
        error_message: `API call failed: ${apiError.message}`,
        formatted_text: bidDescription.trim(),
        project_url: jobData.project_url || `https://www.freelancer.com/projects/${projectId}`,
        project_id: projectId,
        bid_data: bidData,
        message: 'Automatic submission failed. Please submit manually using the formatted text.'
      });
    }

  } catch (error) {
    console.error('[Debug] Error in send-application endpoint:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add new endpoint for button state updates
app.post('/api/update-button-state', async (req, res) => {
  try {
    const { projectId, buttonType, state } = req.body;
    console.log('Received update request:', { projectId, buttonType, state });
    
    if (!projectId || !buttonType || state === undefined) {
      return res.status(400).json({ error: 'Missing required parameters' });
    }

    // Find the job file for this project
    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
    console.log('Looking for job file in directory:', jobsDir);
    
    // Read all files in the jobs directory
    const files = await fs.readdir(jobsDir);
    console.log('Found files:', files);
    
    // Look for the exact file name with the new format
    const projectFile = files.find(file => file === `job_${projectId}.json`);
    
    if (!projectFile) {
      console.log('Project file not found for ID:', projectId);
      return res.status(404).json({ error: 'Project not found' });
    }

    console.log('Found project file:', projectFile);
    
    // Read and update the job file
    const filePath = path.join(jobsDir, projectFile);
    const jobData = JSON.parse(await fs.readFile(filePath, 'utf8'));
    
    // Initialize buttonStates if not exists
    if (!jobData.buttonStates) {
      jobData.buttonStates = {};
    }

    // Update the button state
    jobData.buttonStates[buttonType] = state;

    // Write the updated data back to the file
    await fs.writeFile(filePath, JSON.stringify(jobData, null, 2));
    console.log('Successfully updated button state');

    res.json({ success: true });
  } catch (error) {
    console.error('Error updating button state:', error);
    res.status(500).json({ error: error.message });
  }
});

// ========== ADMIN API ENDPOINTS ==========

// ========== EMPLOYMENT ENDPOINTS ==========
app.get('/api/admin/employment', async (req, res) => {
  try {
    const employment = await getAllEmployment();
    res.json(employment);
  } catch (error) {
    console.error('Error fetching employment:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/admin/employment/:id', async (req, res) => {
  try {
    const employment = await getEmploymentById(req.params.id);
    if (!employment) {
      return res.status(404).json({ error: 'Employment not found' });
    }
    res.json(employment);
  } catch (error) {
    console.error('Error fetching employment:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/admin/employment', async (req, res) => {
  try {
    const id = await createEmployment(req.body);
    res.json({ id, message: 'Employment created successfully' });
  } catch (error) {
    console.error('Error creating employment:', error);
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/admin/employment/:id', async (req, res) => {
  try {
    await updateEmployment(req.params.id, req.body);
    res.json({ message: 'Employment updated successfully' });
  } catch (error) {
    console.error('Error updating employment:', error);
    res.status(500).json({ error: error.message });
  }
});

app.delete('/api/admin/employment/:id', async (req, res) => {
  try {
    await deleteEmployment(req.params.id);
    res.json({ message: 'Employment deleted successfully' });
  } catch (error) {
    console.error('Error deleting employment:', error);
    res.status(500).json({ error: error.message });
  }
});

// ========== EDUCATION ENDPOINTS ==========
app.get('/api/admin/education', async (req, res) => {
  try {
    const education = await getAllEducation();
    res.json(education);
  } catch (error) {
    console.error('Error fetching education:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/admin/education/:id', async (req, res) => {
  try {
    const education = await getEducationById(req.params.id);
    if (!education) {
      return res.status(404).json({ error: 'Education not found' });
    }
    res.json(education);
  } catch (error) {
    console.error('Error fetching education:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/admin/education', async (req, res) => {
  try {
    const id = await createEducation(req.body);
    res.json({ id, message: 'Education created successfully' });
  } catch (error) {
    console.error('Error creating education:', error);
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/admin/education/:id', async (req, res) => {
  try {
    await updateEducation(req.params.id, req.body);
    res.json({ message: 'Education updated successfully' });
  } catch (error) {
    console.error('Error updating education:', error);
    res.status(500).json({ error: error.message });
  }
});

app.delete('/api/admin/education/:id', async (req, res) => {
  try {
    await deleteEducation(req.params.id);
    res.json({ message: 'Education deleted successfully' });
  } catch (error) {
    console.error('Error deleting education:', error);
    res.status(500).json({ error: error.message });
  }
});

// ========== TAGS ENDPOINTS ==========
app.get('/api/admin/tags', async (req, res) => {
  try {
    const tags = await getAllTags();
    res.json(tags);
  } catch (error) {
    console.error('Error fetching tags:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/admin/tags', async (req, res) => {
  try {
    const id = await createTag(req.body);
    res.json({ id, message: 'Tag created successfully' });
  } catch (error) {
    console.error('Error creating tag:', error);
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/admin/tags/:id', async (req, res) => {
  try {
    await updateTag(req.params.id, req.body);
    res.json({ message: 'Tag updated successfully' });
  } catch (error) {
    console.error('Error updating tag:', error);
    res.status(500).json({ error: error.message });
  }
});

app.delete('/api/admin/tags/:id', async (req, res) => {
  try {
    await deleteTag(req.params.id);
    res.json({ message: 'Tag deleted successfully' });
  } catch (error) {
    console.error('Error deleting tag:', error);
    res.status(500).json({ error: error.message });
  }
});

// ========== DOMAINS ENDPOINTS ==========
app.get('/api/admin/domains', async (req, res) => {
  try {
    const domains = await getAllDomains();
    res.json(domains);
  } catch (error) {
    console.error('Error fetching domains:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/admin/domains/:id', async (req, res) => {
  try {
    const domain = await getDomainById(req.params.id);
    if (!domain) {
      return res.status(404).json({ error: 'Domain not found' });
    }
    res.json(domain);
  } catch (error) {
    console.error('Error fetching domain:', error);
    res.status(500).json({ error: error.message });
  }
});

// Remove tag from domain
app.delete('/api/admin/domains/:domainId/tags/:tagId', async (req, res) => {
  try {
    await removeDomainTag(req.params.domainId, req.params.tagId);
    res.json({ message: 'Domain tag removed successfully' });
  } catch (error) {
    console.error('Error removing domain tag:', error);
    res.status(500).json({ error: error.message });
  }
});

// Remove subtag from domain
app.delete('/api/admin/domains/:domainId/subtags/:subtagId', async (req, res) => {
  try {
    await removeDomainSubtag(req.params.domainId, req.params.subtagId);
    res.json({ message: 'Domain subtag removed successfully' });
  } catch (error) {
    console.error('Error removing domain subtag:', error);
    res.status(500).json({ error: error.message });
  }
});

// Function to get all project IDs from jobs folder
async function getProjectIdsFromJobs() {
    try {
        const jobsDir = path.join(__dirname, '..', '..', 'jobs');
        console.log('[Bid Check] Reading jobs directory:', jobsDir);
        
        const files = await fs.readdir(jobsDir);
        console.log('[Bid Check] Found files:', files);
        
        const projectIds = files
            .filter(file => file.startsWith('job_') && file.endsWith('.json'))
            .map(file => file.replace('job_', '').replace('.json', ''))
            .map(Number);
            
        console.log('[Bid Check] Extracted project IDs:', projectIds);
        return projectIds;
    } catch (error) {
        console.error('[Bid Check] Error reading jobs directory:', error);
        return [];
    }
}

// Function to process projects in batches with rate limit handling
async function processBatch(projectIds) {
    console.log(`[Bid Check] Processing batch of ${projectIds.length} projects`);
    
    const endpoint = 'https://www.freelancer.com/api/projects/0.1/projects';
    
    // Create proper array format for API
    const projectParams = projectIds.map(id => `projects[]=${id}`).join('&');
    const params = `${projectParams}&job_details=true&bid_details=true&compact=true`;

    console.log(`[Bid Check] Making API request for projects: ${projectIds.join(', ')}`);

    try {
        const response = await fetch(`${endpoint}?${params}`, {
            headers: {
                'Freelancer-OAuth-V1': config.FREELANCER_API_KEY
            }
        });

        if (response.status === 429) {
            console.log('[Bid Check] Rate limit hit, waiting before retry');
            const retryAfter = parseInt(response.headers.get('Retry-After')) || 60;
            await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
            return processBatch(projectIds); // Retry the batch
        }

        if (!response.ok) {
            throw new Error(`API request failed: ${response.status}`);
        }

        const data = await response.json();
        const projects = data.result.projects;
        console.log(`[Bid Check] Received data for ${projects.length} projects`);

        for (const project of projects) {
            const projectId = project.id;
            const bidCount = project.bid_stats?.bid_count || 0;
            console.log(`[Bid Check] Project ${projectId} has ${bidCount} bids`);
            
            const jobFile = path.join(__dirname, '..', '..', 'jobs', `job_${projectId}.json`);

            try {
                const jobData = JSON.parse(await fs.readFile(jobFile, 'utf8'));
                
                // Ensure project_details and bid_stats exist
                if (!jobData.project_details) jobData.project_details = {};
                if (!jobData.project_details.bid_stats) jobData.project_details.bid_stats = {};
                
                const oldBidCount = jobData.project_details.bid_stats.bid_count || 0;
                jobData.project_details.bid_stats.bid_count = bidCount;
                
                if (bidCount >= MAX_BIDS) {
                    console.log(`[Bid Check] Removing project ${projectId} - exceeded max bids (${bidCount} >= ${MAX_BIDS})`);
                    await fs.unlink(jobFile);
                } else {
                    if (bidCount !== oldBidCount) {
                        console.log(`[Bid Check] Project ${projectId} bid count changed: ${oldBidCount} -> ${bidCount}`);
                    }
                    await fs.writeFile(jobFile, JSON.stringify(jobData, null, 2));
                }
            } catch (error) {
                if (error.code !== 'ENOENT') {
                    console.error(`[Bid Check] Error processing project ${projectId}:`, error);
                }
            }
        }
    } catch (error) {
        console.error('[Bid Check] Error in processBatch:', error);
        throw error;
    }
}

// Function to update bid counts and remove high-bid projects
async function updateBidCounts() {
    console.log('[Bid Check] Starting updateBidCounts function');
    try {
        const projectIds = await getProjectIdsFromJobs();
        console.log(`[Bid Check] Found ${projectIds.length} projects to check`);
        
        if (projectIds.length === 0) {
            console.log('[Bid Check] No projects to check');
            return;
        }

        // Process projects in batches
        for (let i = 0; i < projectIds.length; i += BATCH_SIZE) {
            const batch = projectIds.slice(i, i + BATCH_SIZE);
            console.log(`[Bid Check] Processing batch ${Math.floor(i/BATCH_SIZE) + 1} of ${Math.ceil(projectIds.length/BATCH_SIZE)}`);
            
            // Add random delay between batches for rate limiting
            const delay = Math.floor(Math.random() * 2000) + 1000;
            console.log(`[Bid Check] Waiting ${delay}ms before processing next batch`);
            await new Promise(resolve => setTimeout(resolve, delay));
            
            try {
                await processBatch(batch);
            } catch (error) {
                console.error('[Bid Check] Error processing batch:', error.message);
            }
        }
        
        console.log('[Bid Check] Completed bid check cycle');
    } catch (error) {
        console.error('[Bid Check] Error in updateBidCounts:', error);
    }
}

// Start bid monitoring
console.log(`[Bid Check] Starting bid monitoring service (interval: ${BID_CHECK_INTERVAL}ms)`);

// Run immediately on startup
updateBidCounts().catch(error => {
    console.error('[Bid Check] Initial check failed:', error);
});

// Then set up the interval
const bidCheckInterval = setInterval(async () => {
    console.log('[Bid Check] Running scheduled bid check');
    try {
        await updateBidCounts();
    } catch (error) {
        console.error('[Bid Check] Interval check failed:', error);
    }
}, BID_CHECK_INTERVAL);

// Cleanup on server shutdown
process.on('SIGTERM', () => {
    console.log('[Bid Check] Shutting down bid monitoring service');
    clearInterval(bidCheckInterval);
});

process.on('SIGINT', () => {
    console.log('[Bid Check] Shutting down bid monitoring service');
    clearInterval(bidCheckInterval);
});

// Remove static file serving - API server only
const PORT = process.env.PORT || 5002;
app.listen(PORT, () => {
  console.log(`API Server running on port ${PORT}`);
}); 