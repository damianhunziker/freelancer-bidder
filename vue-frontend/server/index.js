const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs').promises;
const { exec } = require('child_process');
// Removed notifier to reduce dependencies
const OpenAI = require('openai');
const config = require('../config-loader');
const { formatBidText } = require('../src/utils/formatBidText');

// Import fetch for Node.js (if not available globally)
let fetch;
try {
  fetch = global.fetch || require('node-fetch');
} catch (error) {
  console.warn('node-fetch not available, using built-in fetch if available');
  fetch = global.fetch;
}
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
  removeDomainSubtag,
  createDomain,
  updateDomain,
  deleteDomain,
  searchTags,
  searchSubtags,
  addTagToDomain,
  addSubtagToDomain
} = require('./database');
require('dotenv').config();
const app = express();

// Global variables removed to reduce logging

// Add new constants for bid monitoring
const BID_CHECK_INTERVAL = 20000; // 20 seconds
const MAX_BIDS = 200; // Maximum number of bids before removing project
const BATCH_SIZE = 20; // Maximum number of projects to query at once

// ===============================
// TIMEOUT CONFIGURATION CONSTANTS
// ===============================
const API_TIMEOUT_MS = 30000; // 30 seconds timeout for all API calls
const MAX_API_RETRIES = 3; // Maximum number of retries for failed API calls
const RATE_LIMIT_RETRY_DELAY = 60; // Default retry delay for rate limiting (seconds)
const NETWORK_ERROR_RETRY_DELAY = 3000; // Base delay for network errors (milliseconds)
const TIMEOUT_ERROR_RETRY_DELAY = 5000; // Base delay for timeout errors (milliseconds)

// Rate limiting configuration
const RATE_LIMIT_BAN_TIMEOUT_MINUTES = config.RATE_LIMIT_BAN_TIMEOUT_MINUTES || 30;

// Auto-bidding debug logs for frontend
let autoBiddingLogs = [];

console.log(`[Timeout System] Initialized with configuration:
- API Timeout: ${API_TIMEOUT_MS}ms
- Max Retries: ${MAX_API_RETRIES}
- Rate Limit Delay: ${RATE_LIMIT_RETRY_DELAY}s
- Network Error Delay: ${NETWORK_ERROR_RETRY_DELAY}ms
- Timeout Error Delay: ${TIMEOUT_ERROR_RETRY_DELAY}ms`);

// Enhanced rate limiting and timeout handling function for Freelancer API calls
async function handleRateLimit(response, context = 'API call') {
  if (response.status === 429) {
    const banTimeoutSeconds = RATE_LIMIT_BAN_TIMEOUT_MINUTES * 60;
    console.error(`🚫 Rate Limiting erkannt in ${context}! Warte ${RATE_LIMIT_BAN_TIMEOUT_MINUTES} Minuten...`);
    logAutoBiddingServer(`Rate Limiting erkannt in ${context}! Warte ${RATE_LIMIT_BAN_TIMEOUT_MINUTES} Minuten...`, 'error');
    
    // Wait for the ban timeout
    await new Promise(resolve => setTimeout(resolve, banTimeoutSeconds * 1000));
    
    throw new Error(`Rate limit exceeded in ${context}. Waited ${RATE_LIMIT_BAN_TIMEOUT_MINUTES} minutes.`);
  }
  return response;
}

// Centralized API call function with timeout and retry logic
async function makeAPICallWithTimeout(url, options = {}, retryCount = 0) {
  const maxRetries = 3;
  const timeoutMs = 30000; // 30 seconds timeout
  const context = options.context || 'API call';
  
  try {
    // Create timeout controller
    const timeoutController = new AbortController();
    const timeoutId = setTimeout(() => {
      timeoutController.abort();
    }, timeoutMs);

    // Merge default options with provided options
    const apiOptions = {
      ...options,
      signal: timeoutController.signal
    };
    delete apiOptions.context; // Remove context from API options

    const response = await fetch(url, apiOptions);

    // Clear timeout if request completes
    clearTimeout(timeoutId);

    // Handle rate limiting - wait 30 minutes for 429 errors
    if (response.status === 429) {
      const banTimeoutSeconds = 30 * 60; // 30 minutes
      console.error(`🚫 Rate Limiting erkannt in ${context}! Warte 30 Minuten...`);
      logAutoBiddingServer(`Rate Limiting erkannt in ${context}! Warte 30 Minuten...`, 'error');
      
      // Wait for the full 30 minutes
      await new Promise(resolve => setTimeout(resolve, banTimeoutSeconds * 1000));
      
      // After waiting, throw error to stop further processing
      throw new Error(`Rate limit exceeded in ${context}. Waited 30 minutes.`);
    }

    // Handle other HTTP errors
    if (!response.ok) {
      if (retryCount < maxRetries) {
        logAutoBiddingServer(`HTTP error ${response.status} in ${context}, retrying ${retryCount + 2}/${maxRetries + 1}`, 'warning');
        await new Promise(resolve => setTimeout(resolve, 2000 * (retryCount + 1))); // Exponential backoff
        return makeAPICallWithTimeout(url, options, retryCount + 1);
      } else {
        throw new Error(`HTTP request failed with status ${response.status} in ${context} after ${maxRetries + 1} attempts`);
      }
    }

    return response;

  } catch (error) {
    // Handle timeout and network errors with retry logic
    if (error.name === 'AbortError') {
      if (retryCount < maxRetries) {
        logAutoBiddingServer(`Request timeout in ${context}, retrying ${retryCount + 2}/${maxRetries + 1}`, 'warning');
        await new Promise(resolve => setTimeout(resolve, 5000 * (retryCount + 1))); // Longer delay for timeouts
        return makeAPICallWithTimeout(url, options, retryCount + 1);
      } else {
        const timeoutError = new Error(`Request timed out in ${context} after ${maxRetries + 1} attempts`);
        logAutoBiddingServer(`Request timed out in ${context} after ${maxRetries + 1} attempts`, 'error');
        throw timeoutError;
      }
    } else if (error.code === 'ECONNRESET' || error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
      if (retryCount < maxRetries) {
        logAutoBiddingServer(`Network error in ${context}: ${error.message}, retrying ${retryCount + 2}/${maxRetries + 1}`, 'warning');
        await new Promise(resolve => setTimeout(resolve, 3000 * (retryCount + 1))); // Progressive delay
        return makeAPICallWithTimeout(url, options, retryCount + 1);
      } else {
        const networkError = new Error(`Network error in ${context} after ${maxRetries + 1} attempts: ${error.message}`);
        logAutoBiddingServer(`Network error in ${context} after ${maxRetries + 1} attempts: ${error.message}`, 'error');
        throw networkError;
      }
    } else {
      logAutoBiddingServer(`Unexpected error in ${context}: ${error.message}`, 'error');
      throw error;
    }
  }
}

// Function to log auto-bidding activities
function logAutoBiddingServer(message, type = 'info', projectId = null) {
  const timestamp = new Date().toLocaleTimeString();
  const logEntry = {
    timestamp,
    message,
    type,
    projectId,
    id: Date.now() + Math.random()
  };
  
  // Add to logs array
  autoBiddingLogs.push(logEntry);
  
  // Keep only last 200 logs
  if (autoBiddingLogs.length > 200) {
    autoBiddingLogs = autoBiddingLogs.slice(-200);
  }
  
  // Also log to console with prefix
  const consoleMsg = `[AutoBid Server] ${message}`;
  switch (type) {
    case 'error':
      console.error(consoleMsg);
      break;
    case 'warning':
      console.warn(consoleMsg);
      break;
    case 'success':
      console.log(`${consoleMsg}`);
      break;
    default:
      console.log(consoleMsg);
  }
}

// Removed notification functions to reduce logging

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
  try {
    // Disable caching
    res.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    res.set('Pragma', 'no-cache');
    res.set('Expires', '0');

    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
    
    try {
      const jobFiles = await fs.readdir(jobsDir);
      
      const jobs = [];
      
      for (const filename of jobFiles) {
        if (filename.endsWith('.json')) {
          try {
            const filePath = path.join(jobsDir, filename);
            const content = await fs.readFile(filePath, 'utf8');
            const parsed = JSON.parse(content);
            
            // Only log if there are issues
            if (!parsed.project_details) {
              console.log('[Server] ⚠️ Missing project_details in:', filename);
            }
            
            jobs.push(parsed);
          } catch (parseError) {
            console.error('[Server] ❌ Error parsing file', filename, ':', parseError.message);
          }
        }
      }
      
      res.json(jobs);
    } catch (error) {
      console.error('[Server] ❌ Error reading jobs directory:', error);
      res.status(500).json({ error: 'Failed to read jobs directory' });
    }
  } catch (error) {
    console.error('[Server] ❌ Error in /api/jobs:', error);
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
        const index = aiResponse.indexOf(prefix);
        if (index !== -1) {
          const afterPrefix = aiResponse.substring(index + prefix.length).trim();
          const jsonMatch = afterPrefix.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            return JSON.parse(jsonMatch[0]);
          }
        }
      }
      throw new Error('No JSON found after prefixes');
    }
  ];

  // Try each strategy
  for (let i = 0; i < strategies.length; i++) {
    try {
      const result = strategies[i]();
      // Only log successful parsing for debugging when needed
      return result;
    } catch (error) {
      // Only log the final failure
      if (i === strategies.length - 1) {
        console.error(`[Debug] ❌ All parsing strategies failed for ${responseType}:`, error.message);
        console.error(`[Debug] Raw response:`, aiResponse);
      }
    }
  }
  
  throw new Error(`Failed to parse ${responseType} response as JSON`);
}

// Add this function before generateCorrelationAnalysis
async function generateCorrelationAnalysis(jobData) {
  // Get all data from database - reduced logging
  const [domainRefs, employmentData, educationData] = await Promise.all([
    getDomainReferences(),
    getAllEmployment(),
    getAllEducation()
  ]);
  
  // Create domain context string
  const domainContext = domainRefs.references.domains.map(ref => {
    const tags = ref.tags.join(', ');
    const subtags = ref.subtags.join(', ');
    const title = ref.title || ref.domain || 'Untitled Project';
    const description = ref.description || 'No description available';
    return `Domain: ${ref.domain}\nTitle: ${title}\nDescription: ${description}\nTags: ${tags}\nSubtags: ${subtags}`;
  }).join('\n\n');

  // Create employment context string
  const employmentContext = employmentData.map(emp => {
    const position = emp.position || 'Position not specified';
    const description = emp.description || 'No description available';
    return `Company: ${emp.company_name}\nPosition: ${position}\nDescription: ${description}\nTags: ${emp.tags ? emp.tags.join(', ') : 'No tags'}`;
  }).join('\n\n');

  // Create education context string
  const educationContext = educationData.map(edu => {
    const title = edu.title || 'Title not specified';
    const description = edu.description || 'No description available';
    return `Institution: ${edu.institution || 'Unknown'}\nTitle: ${title}\nDescription: ${description}\nTags: ${edu.tags ? edu.tags.join(', ') : 'No tags'}`;
  }).join('\n\n');

  // Ensure skills exists and is an array, otherwise use empty array
  const skills = jobData?.project_details?.jobs?.map(job => job.name) || [];
  
  const messages = [
    {
      "role": "system",
      "content": "You are a project manager of the Vyftec Webagency, that finds correlations between our experience and job descriptions in order to improve our pitching process."
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
        "title": "<education title>",
        "relevance_score": <number between 0 and 1>,
        "description": "<brief description why relevant>"
      }
    ]
  }
}

CRITICAL INSTRUCTIONS:
1. Only include items from our portfolio/background (provided above) that are actually relevant
2. Return maximum 3-5 most relevant items per category
3. If no relevant items are found for a category, return an empty array for that category
4. Ensure relevance_score accurately reflects how well the item matches the project
5. For employment and education, provide a brief description why it's relevant to this project
6. **NEVER use "undefined" as a title - always use the exact title provided in the data above**
7. **For domains: use the exact "Title:" value from the domain data provided**
8. **For employment: use the exact "Position:" value from the employment data provided**
9. **For education: use the exact "Title:" value from the education data provided**
10. **If a title is missing in the source data, use the domain name, company name, or institution name as the title**`
    }
  ];

  return messages;
}

// Function to generate final paragraph composition prompt with conversation context
function generateFinalCompositionMessages(bid_teaser, jobData, conversationContext = null) {
  // Assemble the generated paragraphs
  let assembledText = '';
  
  if (bid_teaser.greeting) {
    assembledText += bid_teaser.greeting + '\n\n';
  }
  
  if (bid_teaser.first_paragraph) {
    assembledText += bid_teaser.first_paragraph + '\n\n';
  }
  
  if (bid_teaser.second_paragraph) {
    assembledText += bid_teaser.second_paragraph + '\n\n';
  }
  
  if (bid_teaser.third_paragraph) {
    assembledText += bid_teaser.third_paragraph + '\n\n';
  }
  
  if (bid_teaser.fourth_paragraph) {
    assembledText += bid_teaser.fourth_paragraph + '\n\n';
  }
  
  if (bid_teaser.closing) {
    assembledText += bid_teaser.closing + '\n\n';
  }

  // Get conversation context from the last conversation
  let contextPrompt = '';
  if (conversationContext) {
    contextPrompt = `Previous Conversation Context:\n${conversationContext}\n\n`;
  } else {
    // Default context based on project specifics
    contextPrompt = `Conversation Context:
This is following up on our previous discussion about generating high-quality bid texts for Vyftec. 
We've now generated the individual paragraphs and need to create a cohesive, final proposal text.
The goal is to maintain consistency with our previous conversation approach while creating a compelling bid.

`;
  }

  return [
    {
      "role": "system", 
      "content": "You are a project manager writing an appealing bid text for a job offer. You are continuing our previous conversation about generating bid texts for Vyftec. You should now create a final, cohesive bid text that combines all paragraphs in a fluent, catchy, convincing, logical, professional way and adds appropriate context from our previous discussion."
    },
    {
      "role": "user",
      "content": `${contextPrompt}Project Title: ${jobData.project_details.title}

Generated Paragraphs:
${assembledText}

Create the final polished bid text. Stick to the wording of the paragraphs, only change it where indicated:
1. **Ensure the direct response to customer questions, tasks, or application requirements is fully answered** and placed in the opening section. Rephrase if necessary—you may use lists. Please include domains, education, and employment where relevant. Describe solutions using conjunctive or indicative (can or could).
2. In total the text should include 1-2 enumerations, lists to loosen things up (e.g., projects, education, employment, timeline breakdown, solution structure, client demands, etc.).
3. Take care at least 2 reference domains are mentioned.
3. **Rearrange sentences or paragraphs to make the text more compelling and persuasive**.
4. Remove unnecessary clichés and vague statements. Stay factual and mention only essentials.
5. Stay below the client's word count if possible. Keep it concise—never exceed 3 paragraphs or 1000 characters, even for detailed job descriptions.
6. **Ensure nothing is repeated.**
7. **Combine all paragraphs naturally with smooth flow.**
8. Add connecting phrases and transitions where needed.
9. Ensure all paragraphs and sentences form one cohesive proposal.
10. **Don't mention price.** If asked for budget reference to those specified in the bid. 
11. Add at least the greeting, decide if closing is appropriate and finish with my name "Damian Hunziker".
12. **Ensure the paragraphs and lists** are properly divided by new line signs.

Return your response in this JSON format:
{
  "final_bid_text": "<complete assembled bid text>"
}`
    }
  ];
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
        correlationContext += `- ${edu.title} in ${edu.institution} - ${edu.description}\n`;
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

## Project Scope / Tech Stack
We are a full-service web agency, so we provide the full chain of the production and execution of a web project containing, planning and project management, design, development, testing, deployment, support and maintenance. We will rely on partners to fill any gap, **dont mentoin that we would not be able to do things or would not be proficient in a certain area**. Dont't propose only our preferred tech stack, but **research and propose the best fitting stack for the client needs** leaning towards our preferred stack. Low-code and AI agents enable us to cover a wide range of requirements.

## Terminology
Write in professional project management and executive language. Adapt to the client's tone, politeness, and formality. Be sympathetic, relaxed, objective and professional, above the things. **Make sense, be logical, pragmatic** follow the thread, and keep the flow. Make it easily readable and formulate fluently, cool, and funny. Don't ask questions. Don't use words like experience, expertise, specialization. Don't repeat wordings given by the client too much, instead try to variate and use synonyms in a natural way. Keep the answers short and concise. Don't ask questions.

## Offer Length / Number of Paragraphs / Paragraphs to omit
Before starting decide about the word count of the complete offer and the amount of paragraphs to use **based on the length and detail level of the job description of the client, decide how long our texts should be and how many paragraphs to use**. 
- **Let the length of the clients job description determine the length of our overall bid text.** While we stay below the client's wordcount, we try to not to overuse paragraphs. Example: When the description is 400 signs we could max. open one paragraph as they are 200-300 characters.
- The first paragraph is mandatory. 
-**In many cases you will only use the first paragraph**, when the description is short and not detailed and machine written. 
- **Only if the job description has a reasonably high level of detail and length, you will use more paragraphs.**
- **You can omit entire paragraphs (except first_paragraph)**, decide which paragraphs are relevant for this job posting. 
- If you decide to omit a paragraph, just use **an empty variable in the json**. 
- When you don't have much valuable to say in a paragraph omit it. 
- **Stay slightly below the client's word count but don't exceed our paragraph limits**. 

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
   - If job post contains direct technical/process questions/tasks (e.g., "How would you solve X?" or "List similar projects):  
     → Research → Answer concisely in 1 sentence.  
   - **Write the solution in the first sentence.**  
   - *Example: "For PDF conversion, I recommend Python's PyMuPDF library for its batch processing capabilities."*

2. **Application Requirements Alignment**  
   - Mirror client's requested structure/format:  
     • If client uses bullet points → Use bullet points  
     • If numbered list → Use numbered list  
     • If plain text → Use plain text  
   - → Cover ALL explicit requirements from "How to apply" section.  
   - **Answer the requirements in the first sentence.**  
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
   - **Don't rely only on our preferred stack but the best fitting for the job.**
   - Propose high-level approach, using conjunctive or indicative (can or could) instead of present continuous or future tense (will do):  
     → Phasing (e.g., "First prototype → Feedback → Scaling")  
     → Tech stack (e.g., "Laravel/Vue for real-time updates")  
     → Risk mitigation (e.g., "Test-driven development")  
   - → Keep to 1 actionable sentence.  

### Output Rules
- **Seamless integration:** Connect points with transition words (e.g., "Moreover," "Specifically," "Building on this")
- **No markdown:** Plain English only
- **Authority tone:** Confident but humble
- **Character limit:** Strictly 200-600 characters

### Portfolio integration
Try to involve in the texts relevant experience and portfolio projects with links provided above to strengthen your proposal where applicable.

## Second Paragraph (Introduction Text)
Brief introduction of Vyftec and our capabilities relevant to this project. Keep it concise and focused on what matters for this specific requirements. Use references to portfolio projects, education, employment, and other relevant information to strengthen the message.

## Third Paragraph (Correlation Text)
Explain the correlation between our skills/background and the project requirements. Use the explanation text provided to show why we're a good fit.

## Fourth Paragraph (Portfolio Projects, Education, Employment)
Include relevant portfolio projects, education, and employment history based on the correlation analysis provided. Format as a concise overview of our relevant background.

## Closing
Write a professional but relaxed closing that matches the tone of the greeting. Include a call to action or invitation for further discussion. **Keep it very short and concise.**

## Question
Take care not to repeat anything from other paragraphs in the question. A question that we ask the employer about the project, the goal is it to provide an accurate estimation. Be very specific and not general. It might ask about the clarification of unclear points, what we need in order to create a binding fixed-price estimation, or asking for confirmation of an approach, technologies to use, ways of working, and the like. Keep it short and concise and ask only for one thing. And do not forget to translate the whole bid texts to the projects description texts language. **No security related questions, if not explicitly asked or necessary.**

## Estimated Price
Calculate an estimated price around the average price found in the project data. Use the following rules:
- Currency: Consider the currency of the project data and calculate the price in the same currency.
- Consider project complexity: Factor in the technical requirements and scope
- Stay competitive: Keep the price attractive while ensuring profitability
- Output: Provide the final estimated price as a number (without currency symbols)

## Estimated Days
Calculate the estimated days needed for project completion using the same logic as the price estimation:
- Base calculation: Estimate realistic timeframe based on project scope and complexity
- Buffer time: Include reasonable buffer for testing, revisions, and deployment
- Output: Provide the estimated days as a number

## Overall length of the complete bid text
- The overall length of the complete bid text containing all paragraphs **should be  below the length of the job description in characters**. In could be approx. 30% below the job description length.

## Important
- **dont mention that we would not be able to do things or would not be proficient in a certain area, or something would not be within our area of expertise.**
- you can mention that we can create feasibility studies and prototypes, when it is appropriate.
`
    }
  ];
}

// Then modify the app.post route to use this function
app.post('/api/generate-bid/:projectId', async (req, res) => {
  try {
    console.log('[Debug] ===== GENERATE BID ENDPOINT CALLED =====');
    console.log('[Debug] Generate bid request received:', {
      projectId: req.params.projectId,
      body: req.body,
      headers: req.headers
    });

    logAutoBiddingServer(`🎯 Bid generation request received for project ${req.params.projectId}`, 'info', req.params.projectId);

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
      projectFile = files.find(file => file === `job_${projectId}.json`);
      
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

    // Skip placeholder bid - only submit final bid after text generation
    console.log('[Debug] Skipping placeholder bid, will submit final bid after text generation');

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

        // Create or reuse a conversation context for this project
        let conversationId = jobData.ranking?.conversation_id;
        let conversationMessages = [];
        
        if (!conversationId) {
          // Create new conversation with Vyftec context
          conversationId = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          
          // Initialize conversation with Vyftec context
          conversationMessages = [
            {
              role: "system",
              content: "You are an AI assistant helping Vyftec create high-quality bid proposals. This is a multi-step conversation where we will analyze correlations, generate bid text, and compose the final proposal."
            },
            {
              role: "user", 
              content: `Company Context for this conversation:\n${vyftec_context}\n\nProject: ${jobData.project_details.title}\n\nWe will now proceed with correlation analysis, bid generation, and final composition in sequence.`
            },
            {
              role: "assistant",
              content: "I understand. I have the Vyftec company context and project details. I'm ready to help with the three-step process: correlation analysis, bid text generation, and final composition. Let's begin with the correlation analysis."
            }
          ];
          
          console.log('[Debug] Created new conversation:', conversationId);
        } else {
          // Load existing conversation context (simplified - in production you'd load from database)
          conversationMessages = [
            {
              role: "system",
              content: "You are continuing our previous conversation about creating bid proposals for Vyftec."
            },
            {
              role: "user",
              content: "Continuing our conversation for this project bid generation process."
            }
          ];
          console.log('[Debug] Continuing existing conversation:', conversationId);
        }

        // STEP 1: Generate correlation analysis (add to conversation)
        const correlationStepMessages = [...conversationMessages, ...correlationMessages.slice(1)]; // Skip system message since we already have it
        
        const correlationResponse = await openai.chat.completions.create({
          model: process.env.OPENAI_MODEL || "gpt-3.5-turbo",
          messages: correlationStepMessages,
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

        // Add correlation result to conversation
        conversationMessages.push({
          role: "assistant",
          content: `Correlation analysis completed: ${JSON.stringify(correlationResults)}`
        });

        // STEP 2: Generate bid text (continue conversation)
        console.log('[Debug] Generating bid text...');
        const bidContextMessages = generateAIMessages('', score, explanation, jobData, correlationResults); // Empty vyftec_context since it's already in conversation
        const bidStepMessages = [...conversationMessages, ...bidContextMessages.slice(2)]; // Skip system and context messages
        
        const bidResponse = await openai.chat.completions.create({
          model: process.env.OPENAI_MODEL || "gpt-3.5-turbo",
          messages: bidStepMessages,
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

        // Apply final formatting using the same function as manual bidding
        const formattedBidDescription = formatBidText(finalBidText.bid_teaser);

        // Add bid generation result to conversation
        conversationMessages.push({
          role: "assistant", 
          content: `Bid text generated: ${JSON.stringify(finalBidText.bid_teaser)}`
        });

        // STEP 3: Final paragraph composition (continue conversation)
        console.log('[Debug] Generating final composed bid text...');
        const compositionContextMessages = generateFinalCompositionMessages(finalBidText.bid_teaser, jobData, 'Continuing our conversation from correlation analysis and bid generation.');
        const compositionStepMessages = [...conversationMessages, ...compositionContextMessages.slice(1)]; // Skip system message
        
        const compositionResponse = await openai.chat.completions.create({
          model: process.env.OPENAI_MODEL || "gpt-3.5-turbo",
          messages: compositionStepMessages,
          temperature: 0.7,
          max_tokens: 800
        });
        
        const compositionAiResponse = compositionResponse.choices[0].message.content;
        console.log('[Debug] Raw composition AI response:', compositionAiResponse);
        
        // Parse the composition response
        let compositionResults;
        try {
          compositionResults = parseAIResponse(compositionAiResponse, 'final composition');
          // Add the final composed text to our bid data
          if (compositionResults.final_bid_text) {
            finalBidText.final_composed_text = compositionResults.final_bid_text;
            finalBidText.composition_improvements = compositionResults.improvements_made;
            // Also add to bid_teaser for formatBidText function access
            finalBidText.bid_teaser.final_composed_text = compositionResults.final_bid_text;
            console.log('[Debug] Final composed text created successfully');
          }
        } catch (error) {
          console.error('[Debug] Failed to parse composition response, using original:', error);
          // If composition fails, continue with original formatted text
        }

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
          // Store the formatted description for consistency with manual process
          jobData.ranking.formatted_description = formattedBidDescription;
          // Store the final composed text if available
          if (finalBidText.final_composed_text) {
            jobData.ranking.final_composed_text = finalBidText.final_composed_text;
            jobData.ranking.composition_improvements = finalBidText.composition_improvements;
          }
          
          console.log('[Debug] Final bid_teaser being saved to ranking:', JSON.stringify(finalBidText.bid_teaser, null, 2));
          console.log('[Debug] ranking.bid_teaser after assignment:', JSON.stringify(jobData.ranking.bid_teaser, null, 2));
          console.log('[Debug] Formatted description preview:', formattedBidDescription.substring(0, 200) + '...');
          
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
          formatted_description: formattedBidDescription,
          correlation_analysis: correlationResults,
          final_composed_text: finalBidText.final_composed_text || null,
          composition_improvements: finalBidText.composition_improvements || null,
          project_id: projectId,
          message: 'Bid text generated successfully'
        });

      } else if (aiProvider === 'deepseek') {
        if (!config.DEEPSEEK_API_BASE || !config.DEEPSEEK_API_KEY) {
          throw new Error('DeepSeek configuration is incomplete');
        }

        const deepseekUrl = `${config.DEEPSEEK_API_BASE}/chat/completions`;
        console.log('[Debug] DeepSeek API URL:', deepseekUrl);

        // Create or reuse a conversation context for this project (DeepSeek)
        let conversationId = jobData.ranking?.conversation_id;
        let conversationMessages = [];
        
        if (!conversationId) {
          // Create new conversation with Vyftec context
          conversationId = `conv_deepseek_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          
          // Initialize conversation with Vyftec context
          conversationMessages = [
            {
              role: "system",
              content: "You are an AI assistant helping Vyftec create high-quality bid proposals. This is a multi-step conversation where we will analyze correlations, generate bid text, and compose the final proposal."
            },
            {
              role: "user", 
              content: `Company Context for this conversation:\n${vyftec_context}\n\nProject: ${jobData.project_details.title}\n\nWe will now proceed with correlation analysis, bid generation, and final composition in sequence.`
            },
            {
              role: "assistant",
              content: "I understand. I have the Vyftec company context and project details. I'm ready to help with the three-step process: correlation analysis, bid text generation, and final composition. Let's begin with the correlation analysis."
            }
          ];
          
          console.log('[Debug] Created new DeepSeek conversation:', conversationId);
        } else {
          // Load existing conversation context
          conversationMessages = [
            {
              role: "system",
              content: "You are continuing our previous conversation about creating bid proposals for Vyftec."
            },
            {
              role: "user",
              content: "Continuing our conversation for this project bid generation process."
            }
          ];
          console.log('[Debug] Continuing existing DeepSeek conversation:', conversationId);
        }

        // STEP 1: Generate correlation analysis (add to conversation)
        const correlationStepMessages = [...conversationMessages, ...correlationMessages.slice(1)]; // Skip system message since we already have it
        
        const correlationResponse = await fetch(deepseekUrl, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${config.DEEPSEEK_API_KEY}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            model: config.DEEPSEEK_MODEL,
            messages: correlationStepMessages,
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

        // Add correlation result to conversation
        conversationMessages.push({
          role: "assistant",
          content: `Correlation analysis completed: ${JSON.stringify(correlationResults)}`
        });

        // STEP 2: Generate bid text (continue conversation)
        console.log('[Debug] Generating bid text...');
        const bidContextMessages = generateAIMessages('', score, explanation, jobData, correlationResults); // Empty vyftec_context since it's already in conversation
        const bidStepMessages = [...conversationMessages, ...bidContextMessages.slice(2)]; // Skip system and context messages
        
        const bidResponse = await fetch(deepseekUrl, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${config.DEEPSEEK_API_KEY}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            model: config.DEEPSEEK_MODEL,
            messages: bidStepMessages,
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

        // Apply final formatting using the same function as manual bidding
        const formattedBidDescription = formatBidText(finalBidText.bid_teaser);

        // Add bid generation result to conversation
        conversationMessages.push({
          role: "assistant", 
          content: `Bid text generated: ${JSON.stringify(finalBidText.bid_teaser)}`
        });

        // STEP 3: Final paragraph composition (continue conversation)
        console.log('[Debug] Generating final composed bid text with DeepSeek...');
        const compositionContextMessages = generateFinalCompositionMessages(finalBidText.bid_teaser, jobData, 'Continuing our conversation from correlation analysis and bid generation.');
        const compositionStepMessages = [...conversationMessages, ...compositionContextMessages.slice(1)]; // Skip system message
        
        const compositionResponse = await fetch(deepseekUrl, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${config.DEEPSEEK_API_KEY}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            model: config.DEEPSEEK_MODEL,
            messages: compositionStepMessages,
            temperature: 0.7,
            max_tokens: 800
          })
        });

        if (!compositionResponse.ok) {
          const errorText = await compositionResponse.text();
          console.error('[Debug] DeepSeek composition API error response:', {
            status: compositionResponse.status,
            statusText: compositionResponse.statusText,
            errorText
          });
          // Continue without composition if it fails
          console.warn('[Debug] Composition failed, continuing with original bid text');
        } else {
          const compositionData = await compositionResponse.json();
          const compositionAiResponse = compositionData.choices[0].message.content;
          console.log('[Debug] Raw composition AI response:', compositionAiResponse);
          
          // Parse the composition response
          let compositionResults;
          try {
            compositionResults = parseAIResponse(compositionAiResponse, 'final composition');
            // Add the final composed text to our bid data
            if (compositionResults.final_bid_text) {
              finalBidText.final_composed_text = compositionResults.final_bid_text;
              finalBidText.composition_improvements = compositionResults.improvements_made;
              // Also add to bid_teaser for formatBidText function access
              finalBidText.bid_teaser.final_composed_text = compositionResults.final_bid_text;
              console.log('[Debug] Final composed text created successfully with DeepSeek');
            }
          } catch (error) {
            console.error('[Debug] Failed to parse DeepSeek composition response, using original:', error);
            // If composition fails, continue with original formatted text
          }
        }

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
          // Store the formatted description for consistency with manual process
          jobData.ranking.formatted_description = formattedBidDescription;
          // Store the final composed text if available
          if (finalBidText.final_composed_text) {
            jobData.ranking.final_composed_text = finalBidText.final_composed_text;
            jobData.ranking.composition_improvements = finalBidText.composition_improvements;
          }
          
          // Store conversation ID for future reuse (DeepSeek)
          jobData.ranking.conversation_id = conversationId;
          
          console.log('[Debug] Final bid_teaser being saved to ranking:', JSON.stringify(finalBidText.bid_teaser, null, 2));
          console.log('[Debug] ranking.bid_teaser after assignment:', JSON.stringify(jobData.ranking.bid_teaser, null, 2));
          console.log('[Debug] DeepSeek Conversation ID saved:', conversationId);
          console.log('[Debug] Formatted description preview:', formattedBidDescription.substring(0, 200) + '...');
          
          // Write the updated data back to the file
          const updatedContent = JSON.stringify(jobData, null, 2);
          await fs.writeFile(filePath, updatedContent, 'utf8');
          console.log('[Debug] Successfully updated JSON file');
        }

        // Submit final bid after text generation
        console.log('[Debug] Submitting final bid with generated text');
        logAutoBiddingServer(`🎯 Submitting final bid for project ${projectId}`, 'info', projectId);
        
        const finalBidResult = await submitFinalBid(projectId, jobData.project_details, finalBidText);
        if (finalBidResult.success) {
          logAutoBiddingServer(`✅ Final bid submitted successfully for project ${projectId}`, 'success', projectId);
        } else {
          logAutoBiddingServer(`❌ Final bid failed for project ${projectId}: ${finalBidResult.error}`, 'error', projectId);
        }

        // Return the bid text and correlation results
        res.json({
          success: true,
          bid_text: finalBidText,
          bid_teaser: finalBidText.bid_teaser,
          formatted_description: formattedBidDescription,
          correlation_analysis: correlationResults,
          final_composed_text: finalBidText.final_composed_text || null,
          composition_improvements: finalBidText.composition_improvements || null,
          conversation_id: conversationId,
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
    
    // Handle rate limiting
    await handleRateLimit(testResponse, 'Freelancer API test');
    
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
      projectFile = files.find(file => file === `job_${projectId}.json`);
      
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

    // Format the bid description using the shared utility function
    const bidTeaser = jobData.ranking.bid_teaser;
    
    // Add final_composed_text to bid_teaser if available for formatBidText function access
    if (jobData.ranking.final_composed_text && !bidTeaser.final_composed_text) {
      bidTeaser.final_composed_text = jobData.ranking.final_composed_text;
    }
    
    const bidDescription = formatBidText(bidTeaser);

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
    
    // Calculate maximum allowed bid amount (80% above max/average price)
    let maximumAllowedBid = null;
    let referencePrice = null;
    let referencePriceType = null;
    
    // Try to get  average bid, then fall back to maximum budget
    if (jobData.project_details?.bid_stats?.bid_avg && jobData.project_details.bid_stats.bid_avg > 0) {
      referencePrice = jobData.project_details.bid_stats.bid_avg;
      referencePriceType = 'average bid';
      
      // Convert to USD if needed
      if (projectCurrency && projectCurrency.code !== 'USD' && projectCurrency.exchange_rate) {
        referencePrice = Math.ceil(jobData.project_details.bid_stats.bid_avg / projectCurrency.exchange_rate);
        console.log(`[Debug] Average bid currency conversion: ${jobData.project_details.bid_stats.bid_avg} ${projectCurrency.code} → ${referencePrice} USD`);
      }
    } else if (projectBudget && projectBudget.minimum && projectBudget.maximum && projectBudget.minimum > 0 && projectBudget.maximum > 0) {
      // When average bid is not available, use the average of the customer's price range
      const budgetAverage = (projectBudget.minimum + projectBudget.maximum) / 2;
      referencePrice = budgetAverage;
      referencePriceType = 'customer price range average';
      
      // Convert to USD if needed
      if (projectCurrency && projectCurrency.code !== 'USD' && projectCurrency.exchange_rate) {
        referencePrice = Math.ceil(budgetAverage / projectCurrency.exchange_rate);
        console.log(`[Debug] Customer price range average currency conversion: ${budgetAverage} ${projectCurrency.code} → ${referencePrice} USD`);
      }
      
      console.log(`[Debug] Using customer price range average: (${projectBudget.minimum} + ${projectBudget.maximum}) / 2 = ${budgetAverage} ${projectCurrency?.code || 'USD'}`);
    }
    
    // Apply maximum bid limit if we have a reference price
    if (referencePrice && referencePrice > 0) {
      maximumAllowedBid = Math.ceil(referencePrice * 1.8); // 80% above reference price
      console.log(`[Debug] Maximum allowed bid: ${maximumAllowedBid} USD (180% of ${referencePriceType}: ${referencePrice} USD)`);
      
      // Check if bid amount exceeds maximum allowed
      if (bidAmount > maximumAllowedBid) {
        bidAmount = maximumAllowedBid;
        console.log(`[Debug] Bid amount adjusted from ${bidTeaser.estimated_price} to ${bidAmount} (maximum allowed: ${maximumAllowedBid}, based on ${referencePriceType})`);
      }
    } else {
      console.log(`[Debug] No reference price available for maximum bid validation (max budget: ${projectBudget?.maximum}, avg bid: ${jobData.project_details?.bid_stats?.bid_avg})`);
    }
    
    console.log(`[Debug] Final bid amount: ${bidAmount} USD (estimated: ${bidTeaser.estimated_price}, minimum: ${minimumBidAmount}, maximum allowed: ${maximumAllowedBid || 'no limit'})`);

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

    // Submit bid to Freelancer API using centralized timeout function
    try {
      const freelancerResponse = await makeAPICallWithTimeout('https://www.freelancer.com/api/projects/0.1/bids/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Freelancer-OAuth-V1': config.FREELANCER_API_KEY
        },
        body: JSON.stringify(bidData),
        context: 'Bid Submission'
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

// Create new domain
app.post('/api/admin/domains', async (req, res) => {
  try {
    const id = await createDomain(req.body);
    res.json({ id, message: 'Domain created successfully' });
  } catch (error) {
    console.error('Error creating domain:', error);
    res.status(500).json({ error: error.message });
  }
});

// Update domain
app.put('/api/admin/domains/:id', async (req, res) => {
  try {
    await updateDomain(req.params.id, req.body);
    res.json({ message: 'Domain updated successfully' });
  } catch (error) {
    console.error('Error updating domain:', error);
    res.status(500).json({ error: error.message });
  }
});

// Delete domain
app.delete('/api/admin/domains/:id', async (req, res) => {
  try {
    await deleteDomain(req.params.id);
    res.json({ message: 'Domain deleted successfully' });
  } catch (error) {
    console.error('Error deleting domain:', error);
    res.status(500).json({ error: error.message });
  }
});

// Search tags for autocomplete
app.get('/api/admin/tags/search', async (req, res) => {
  try {
    const { q } = req.query;
    const tags = await searchTags(q);
    res.json(tags);
  } catch (error) {
    console.error('Error searching tags:', error);
    res.status(500).json({ error: error.message });
  }
});

// Search subtags for autocomplete
app.get('/api/admin/subtags/search', async (req, res) => {
  try {
    const { q } = req.query;
    const subtags = await searchSubtags(q);
    res.json(subtags);
  } catch (error) {
    console.error('Error searching subtags:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add tag to domain
app.post('/api/admin/domains/:domainId/tags', async (req, res) => {
  try {
    const { domainId } = req.params;
    const { tag_name } = req.body;
    const result = await addTagToDomain(domainId, tag_name);
    res.json(result);
  } catch (error) {
    console.error('Error adding tag to domain:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add subtag to domain
app.post('/api/admin/domains/:domainId/subtags', async (req, res) => {
  try {
    const { domainId } = req.params;
    const { subtag_name } = req.body;
    const result = await addSubtagToDomain(domainId, subtag_name);
    res.json(result);
  } catch (error) {
    console.error('Error adding subtag to domain:', error);
    res.status(500).json({ error: error.message });
  }
});

// Function to get all project IDs from jobs folder
async function getProjectIdsFromJobs() {
    try {
        const jobsDir = path.join(__dirname, '..', '..', 'jobs');
        // Reading jobs directory - reduced logging
        
        const files = await fs.readdir(jobsDir);
        console.log(`[Bid Check] Found ${files.length} files`);
        
        const projectIds = files
            .filter(file => file.startsWith('job_') && file.endsWith('.json'))
            .map(file => file.replace('job_', '').replace('.json', ''))
            .map(Number);
            
        console.log(`[Bid Check] Extracted ${projectIds.length} project IDs`);
        return projectIds;
    } catch (error) {
        console.error('[Bid Check] Error reading jobs directory:', error);
        return [];
    }
}

async function processBatch(projectIds) {
    const endpoint = 'https://www.freelancer.com/api/projects/0.1/projects';
    
    // Create proper array format for API
    const projectParams = projectIds.map(id => `projects[]=${id}`).join('&');
    const params = `${projectParams}&job_details=true&bid_details=true&compact=true`;

    try {
        const response = await makeAPICallWithTimeout(`${endpoint}?${params}`, {
            headers: {
                'Freelancer-OAuth-V1': config.FREELANCER_API_KEY
            },
            context: 'Bid Check - Project Batch'
        });

        const data = await response.json();
        const projects = data.result.projects;

        for (const project of projects) {
            const projectId = project.id;
            const bidCount = project.bid_stats?.bid_count || 0;
            
            const jobFile = path.join(__dirname, '..', '..', 'jobs', `job_${projectId}.json`);

            try {
                const jobData = JSON.parse(await fs.readFile(jobFile, 'utf8'));
                
                // Ensure project_details and bid_stats exist
                if (!jobData.project_details) jobData.project_details = {};
                if (!jobData.project_details.bid_stats) jobData.project_details.bid_stats = {};
                
                const oldBidCount = jobData.project_details.bid_stats.bid_count || 0;
                jobData.project_details.bid_stats.bid_count = bidCount;
                
                if (bidCount >= MAX_BIDS) {
                    console.log(`[Bid Check] 🗑️ Removing project ${projectId} - exceeded max bids (${bidCount} >= ${MAX_BIDS})`);
                    await fs.unlink(jobFile);
                } else {
                    // Only log when bid count actually changes
                    if (bidCount !== oldBidCount) {
                        console.log(`[Bid Check] 📊 Project ${projectId} bid count: ${oldBidCount} → ${bidCount}`);
                    }
                    await fs.writeFile(jobFile, JSON.stringify(jobData, null, 2));
                }
            } catch (error) {
                if (error.code !== 'ENOENT') {
                    console.error(`[Bid Check] ❌ Error processing project ${projectId}:`, error);
                }
            }
        }
    } catch (error) {
        console.error('[Bid Check] ❌ Error in processBatch:', error);
        logAutoBiddingServer(`Error in processBatch: ${error.message}`, 'error');
        throw error;
    }
}

// Function to update bid counts and remove high-bid projects
async function updateBidCounts() {
    try {
        const projectIds = await getProjectIdsFromJobs();
        
        if (projectIds.length === 0) {
            return; // Silent when no projects
        }

        // Process projects in batches
        for (let i = 0; i < projectIds.length; i += BATCH_SIZE) {
            const batch = projectIds.slice(i, i + BATCH_SIZE);
            
            // Add random delay between batches for rate limiting
            const delay = Math.floor(Math.random() * 2000) + 1000;
            await new Promise(resolve => setTimeout(resolve, delay));
            
            try {
                await processBatch(batch);
            } catch (error) {
                console.error('[Bid Check] ❌ Error processing batch:', error.message);
            }
        }
    } catch (error) {
        console.error('[Bid Check] ❌ Error in updateBidCounts:', error);
    }
}

// Start bid monitoring - only log startup
console.log(`[Bid Check] 🚀 Starting bid monitoring service (interval: ${BID_CHECK_INTERVAL/1000}s)`);

// Run immediately on startup
updateBidCounts().catch(error => {
    console.error('[Bid Check] ❌ Initial check failed:', error);
});

// Then set up the interval - no routine logging
const bidCheckInterval = setInterval(async () => {
    try {
        await updateBidCounts();
    } catch (error) {
        console.error('[Bid Check] ❌ Interval check failed:', error);
    }
}, BID_CHECK_INTERVAL);

// Cleanup on server shutdown
process.on('SIGTERM', () => {
    console.log('[Bid Check] 🛑 Shutting down bid monitoring service');
    clearInterval(bidCheckInterval);
});

process.on('SIGINT', () => {
    console.log('[Bid Check] 🛑 Shutting down bid monitoring service');
    clearInterval(bidCheckInterval);
});

// Add new endpoint for auto-bidding logs
app.get('/api/auto-bidding-logs', (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 50;
    const logs = autoBiddingLogs.slice(-limit);
    res.json({ logs });
  } catch (error) {
    console.error('Error fetching auto-bidding logs:', error);
    res.status(500).json({ error: error.message });
  }
});

// Save error information to project JSON for auto-bidding persistence
app.post('/api/projects/:projectId/error', async (req, res) => {
  try {
    const projectId = req.params.projectId;
    const { error } = req.body;
    
    console.log(`[Error] Saving error for project ${projectId}:`, error);
    
    const jobFile = path.join(__dirname, '..', '..', 'jobs', `job_${projectId}.json`);
    
    // Check if job file exists
    try {
      const data = await fs.readFile(jobFile, 'utf8');
      const jobData = JSON.parse(data);
      
      // Add error information to ranking section
      if (!jobData.ranking) {
        jobData.ranking = {};
      }
      
      jobData.ranking.error = {
        message: error.message,
        context: error.context,
        timestamp: error.timestamp,
        type: error.type
      };
      
      // Write updated data back to file
      await fs.writeFile(jobFile, JSON.stringify(jobData, null, 2));
      
      console.log(`[Error] Successfully saved error to project ${projectId}`);
      res.json({ message: 'Error saved successfully' });
      
    } catch (fileError) {
      if (fileError.code === 'ENOENT') {
        console.error(`[Error] Job file not found for project ${projectId}`);
        res.status(404).json({ error: 'Project not found' });
      } else {
        throw fileError;
      }
    }
    
  } catch (error) {
    console.error('Error saving error to project:', error);
    res.status(500).json({ error: error.message });
  }
});

// Test endpoint for price validation logic
app.post('/api/test-price-validation/:projectId', async (req, res) => {
  try {
    const projectId = req.params.projectId;
    console.log(`[Test] Testing price validation for project ${projectId}`);
    
    // Find the job file for this project
    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
    const files = await fs.readdir(jobsDir);
    const projectFile = files.find(file => file === `job_${projectId}.json`);
    
    if (!projectFile) {
      return res.status(404).json({ error: 'Project not found' });
    }
    
    // Read project data
    const filePath = path.join(jobsDir, projectFile);
    const jobData = JSON.parse(await fs.readFile(filePath, 'utf8'));
    
    // Get bid teaser
    const bidTeaser = jobData.ranking?.bid_teaser || {};
    if (!bidTeaser.estimated_price) {
      return res.status(400).json({ error: 'No estimated price found. Generate bid text first.' });
    }
    
    // Extract project budget and currency info
    const projectBudget = jobData.project_details?.budget;
    const projectCurrency = jobData.project_details?.currency;
    
    console.log(`[Test] Project budget info - Min: ${projectBudget?.minimum}, Max: ${projectBudget?.maximum}, Currency: ${projectCurrency?.code}`);
    console.log(`[Test] AI estimated price: ${bidTeaser.estimated_price}`);
    
    // Calculate minimum allowed bid amount
    let minimumBidAmount = 100; // Default fallback
    if (projectBudget && projectBudget.minimum) {
      minimumBidAmount = projectBudget.minimum;
      
      // If project currency is not USD, convert to USD for API submission
      if (projectCurrency && projectCurrency.code !== 'USD' && projectCurrency.exchange_rate) {
        const originalAmount = minimumBidAmount;
        minimumBidAmount = Math.ceil(projectBudget.minimum / projectCurrency.exchange_rate);
        console.log(`[Test] Currency conversion: ${originalAmount} ${projectCurrency.code} → ${minimumBidAmount} USD (rate: ${projectCurrency.exchange_rate})`);
      }
    }
    
    // Get the AI estimated price or use fallback
    let bidAmount = bidTeaser.estimated_price || minimumBidAmount;
    
    // TEST: Minimum price validation
    const originalBidAmount = bidAmount;
    if (bidAmount < minimumBidAmount) {
      bidAmount = minimumBidAmount;
      console.log(`[Test] Bid amount adjusted from ${bidTeaser.estimated_price} to ${bidAmount} (minimum: ${minimumBidAmount})`);
    }
    
    // TEST: Maximum price validation (NEW FEATURE!)
    let maximumAllowedBid = null;
    let referencePrice = null;
    let referencePriceType = null;
    
    // Try to get average bid first then fall back tomaximum budget
    if (jobData.project_details?.bid_stats?.bid_avg && jobData.project_details.bid_stats.bid_avg > 0) {
      referencePrice = jobData.project_details.bid_stats.bid_avg;
      referencePriceType = 'average bid';
      
      // Convert to USD if needed
      if (projectCurrency && projectCurrency.code !== 'USD' && projectCurrency.exchange_rate) {
        referencePrice = Math.ceil(jobData.project_details.bid_stats.bid_avg / projectCurrency.exchange_rate);
        console.log(`[Debug] Average bid currency conversion: ${jobData.project_details.bid_stats.bid_avg} ${projectCurrency.code} → ${referencePrice} USD`);
      }
    } else if (projectBudget && projectBudget.minimum && projectBudget.maximum && projectBudget.minimum > 0 && projectBudget.maximum > 0) {
      // When average bid is not available, use the average of the customer's price range
      const budgetAverage = (projectBudget.minimum + projectBudget.maximum) / 2;
      referencePrice = budgetAverage;
      referencePriceType = 'customer price range average';
      
      // Convert to USD if needed
      if (projectCurrency && projectCurrency.code !== 'USD' && projectCurrency.exchange_rate) {
        referencePrice = Math.ceil(budgetAverage / projectCurrency.exchange_rate);
        console.log(`[Debug] Customer price range average currency conversion: ${budgetAverage} ${projectCurrency.code} → ${referencePrice} USD`);
      }
      
      console.log(`[Debug] Using customer price range average: (${projectBudget.minimum} + ${projectBudget.maximum}) / 2 = ${budgetAverage} ${projectCurrency?.code || 'USD'}`);
    }
    
    // Apply maximum bid limit if we have a reference price
    if (referencePrice && referencePrice > 0) {
      maximumAllowedBid = Math.ceil(referencePrice * 1.8); // 80% above reference price
      console.log(`[Test] Maximum allowed bid: ${maximumAllowedBid} USD (180% of ${referencePriceType}: ${referencePrice} USD)`);
      
      // Check if bid amount exceeds maximum allowed
      if (bidAmount > maximumAllowedBid) {
        const previousAmount = bidAmount;
        bidAmount = maximumAllowedBid;
        console.log(`[Test] Bid amount adjusted from ${previousAmount} to ${bidAmount} (maximum allowed: ${maximumAllowedBid}, based on ${referencePriceType})`);
      }
    } else {
      console.log(`[Test] No reference price available for maximum bid validation (max budget: ${projectBudget?.maximum}, avg bid: ${jobData.project_details?.bid_stats?.bid_avg})`);
    }
    
    console.log(`[Test] Final bid amount: ${bidAmount} USD (estimated: ${bidTeaser.estimated_price}, minimum: ${minimumBidAmount}, maximum allowed: ${maximumAllowedBid || 'no limit'})`);
    
    // Return test results
    res.json({
      success: true,
      test_results: {
        project_id: projectId,
        project_budget: projectBudget,
        ai_estimated_price: bidTeaser.estimated_price,
        minimum_bid: minimumBidAmount,
        maximum_allowed_bid: maximumAllowedBid,
        reference_price: referencePrice,
        reference_price_type: referencePriceType,
        final_bid_amount: bidAmount,
        adjustments: {
          minimum_adjustment: bidAmount !== originalBidAmount && bidAmount === minimumBidAmount,
          maximum_adjustment: bidAmount !== originalBidAmount && bidAmount === maximumAllowedBid,
          total_adjustment: originalBidAmount !== bidAmount,
          adjustment_amount: originalBidAmount - bidAmount
        }
      }
    });
    
  } catch (error) {
    console.error('[Test] Error in price validation test:', error);
    res.status(500).json({ error: error.message });
  }
});

// Remove static file serving - API server only
const PORT = process.env.PORT || 5002;
app.listen(PORT, () => {
  console.log(`API Server running on port ${PORT}`);
}); 



async function submitFinalBid(projectId, projectData, bidContent) {
  try {
    console.log(`[FinalBid] Submitting final bid for project ${projectId}`);
    
    // Build final bid text from generated content
    const teaser = bidContent.bid_teaser || {};

    const finalText = `${teaser.final_composed_text || ''}`;
    
    // Get numeric user ID from username (same logic as placeholder bid)
    let numericUserId = config.FREELANCER_USER_ID;
    
    if (config.FREELANCER_USER_ID === "webskillssl") {
      numericUserId = 3953491;
    } else if (typeof config.FREELANCER_USER_ID === 'string' && isNaN(config.FREELANCER_USER_ID)) {
      try {
        const userResponse = await fetch(`https://www.freelancer.com/api/users/0.1/users?usernames[]=${config.FREELANCER_USER_ID}`, {
          method: 'GET',
          headers: {
            'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
            'Content-Type': 'application/json'
          }
        });
        
        if (userResponse.ok) {
          const userData = await userResponse.json();
          const userEntries = Object.entries(userData.result?.users || {});
          if (userEntries.length > 0) {
            const [userId] = userEntries[0];
            numericUserId = parseInt(userId);
          } else {
            throw new Error(`User '${config.FREELANCER_USER_ID}' not found`);
          }
        } else {
          throw new Error(`Failed to get user ID: ${userResponse.status}`);
        }
      } catch (userError) {
        console.log(`[FinalBid] ❌ Failed to get user ID: ${userError.message}`);
        return { success: false, error: userError.message };
      }
    }

    // Calculate bid amount (same logic as placeholder bid)
    const projectBudget = projectData.budget;
    const projectCurrency = projectData.currency;
    
    let minimumBidAmount = 100; // Default fallback
    if (projectBudget && projectBudget.minimum) {
      minimumBidAmount = projectBudget.minimum;
      
      if (projectCurrency && projectCurrency.code !== 'USD' && projectCurrency.exchange_rate) {
        minimumBidAmount = Math.ceil(projectBudget.minimum / projectCurrency.exchange_rate);
      }
    }

    // Prepare bid data for Freelancer API
    const bidData = {
      project_id: parseInt(projectId),
      bidder_id: parseInt(numericUserId),
      amount: minimumBidAmount,
      period: 7, // 7 days delivery time
      milestone_percentage: 100,
      description: finalText
    };

    // Check if bid already exists and update it, or create new one
    let freelancerResponse;
    
    try {
      // First try to get existing bids
      const getBidsResponse = await makeAPICallWithTimeout(`https://www.freelancer.com/api/projects/0.1/projects/${projectId}/bids/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Freelancer-OAuth-V1': config.FREELANCER_API_KEY
        },
        context: 'Get Existing Bids for Final'
      });

      if (getBidsResponse.ok) {
        const bidsData = await getBidsResponse.json();
        const userBids = (bidsData.result?.bids || []).filter(bid => 
          bid.bidder_id === numericUserId
        );

        if (userBids.length > 0) {
          // Update existing bid
          const bidId = userBids[0].id;
          console.log(`[FinalBid] Updating existing bid ${bidId} for project ${projectId}`);
          
          freelancerResponse = await makeAPICallWithTimeout(`https://www.freelancer.com/api/projects/0.1/bids/${bidId}/`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Freelancer-OAuth-V1': config.FREELANCER_API_KEY
            },
            body: JSON.stringify(bidData),
            context: 'Update Final Bid'
          });
        } else {
          // Create new bid
          console.log(`[FinalBid] Creating new bid for project ${projectId}`);
          
          freelancerResponse = await makeAPICallWithTimeout('https://www.freelancer.com/api/projects/0.1/bids/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Freelancer-OAuth-V1': config.FREELANCER_API_KEY
            },
            body: JSON.stringify(bidData),
            context: 'Create Final Bid'
          });
        }
      } else {
        // If can't get existing bids, try to create new one
        console.log(`[FinalBid] Could not get existing bids, creating new bid for project ${projectId}`);
        
        freelancerResponse = await makeAPICallWithTimeout('https://www.freelancer.com/api/projects/0.1/bids/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Freelancer-OAuth-V1': config.FREELANCER_API_KEY
          },
          body: JSON.stringify(bidData),
          context: 'Create Final Bid'
        });
      }
    } catch (error) {
      console.log(`[FinalBid] ❌ Error during bid submission: ${error.message}`);
      return { success: false, error: error.message };
    }

    if (!freelancerResponse.ok) {
      const errorText = await freelancerResponse.text();
      console.log(`[FinalBid] ❌ API error: ${freelancerResponse.status} - ${errorText}`);
      return { success: false, error: `${freelancerResponse.status} - ${errorText}` };
    }

    const freelancerData = await freelancerResponse.json();
    console.log(`[FinalBid] ✅ Final bid submitted successfully for project ${projectId}`);
    
    return { 
      success: true, 
      freelancer_response: freelancerData,
      bid_data: bidData
    };

  } catch (error) {
    console.log(`[FinalBid] ❌ Error submitting final bid: ${error.message}`);
    return { success: false, error: error.message };
  }
} 