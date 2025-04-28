const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs').promises;
const { exec } = require('child_process');
const notifier = require('node-notifier');
const OpenAI = require('openai');
const config = require('../config-loader');
const { getDomainReferences } = require('./database');
require('dotenv').config();
const app = express();

// Keep track of previously seen files
let previousFiles = new Set();

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
  allowedHeaders: ['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Cache-Control', 'Pragma']
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
  console.log('[Server] /api/jobs aufgerufen');

  // Add cache control headers
  res.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
  res.set('Pragma', 'no-cache');
  res.set('Expires', '0');

  try {
    // Use absolute path to jobs directory
    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
    console.log('Debug: Current directory:', __dirname);
    console.log('Debug: Jobs directory path:', jobsDir);
    
    // Check if directory exists
    try {
      await fs.access(jobsDir);
      console.log('Debug: Jobs directory exists');
    } catch (error) {
      console.error('Debug: Jobs directory does not exist:', error);
      return res.status(500).json({ error: 'Jobs directory not found' });
    }
    
    const files = await fs.readdir(jobsDir);
    console.log('Debug: All files in jobs directory:', files);
    
    // Filter for job_*.json files
    const jobFiles = files.filter(file => file.startsWith('job_') && file.endsWith('.json'));
    console.log('Debug: Filtered job files:', jobFiles);
    
    // Check for new files and play sound if found
    checkForNewFiles(jobFiles);
    
    // Read all job files and return their contents
    const jobs = await Promise.all(
      jobFiles.map(async (file) => {
        const filePath = path.join(jobsDir, file);
        const content = await fs.readFile(filePath, 'utf8');
          return JSON.parse(content);
        })
    );
    
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
    console.log('Checking for project ID:', projectId);
    console.log('Available files:', files);
    
    // Find any file that starts with job_ and contains the project ID
    const projectFile = files.find(file => {
      const match = file.match(/^job_(\d+)_/);
      return match && match[1] === projectId;
    });
    
    if (projectFile) {
      console.log('Found matching file:', projectFile);
      res.json({ exists: true, filename: projectFile });
    } else {
      console.log('No matching file found for project ID:', projectId);
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

// Add this function before generateAIMessages
async function generateReferenceMessages(jobData) {
  // Get domain references from database
  console.log('[Debug] Fetching domain references from database...');
  const domainRefs = await getDomainReferences();
  console.log('[Debug] Found domain references:', JSON.stringify(domainRefs, null, 2));
  
  // Create domain context string
  console.log('[Debug] Creating domain context string...');
  const domainContext = domainRefs.references.domains.map(ref => {
    const tags = ref.tags.join(', ');
    const subtags = ref.subtags.join(', ');
    return `Domain: ${ref.domain}\nTitle: ${ref.title}\nDescription: ${ref.description}\nTags: ${tags}\nSubtags: ${subtags}`;
  }).join('\n\n');
  console.log('[Debug] Generated domain context:\n', domainContext);

  // Ensure skills exists and is an array, otherwise use empty array
  const skills = jobData?.project_details?.jobs?.map(job => job.name) || [];
  console.log('[Debug] Extracted project skills:', skills);
  
  const messages = [
    {
      "role": "system",
      "content": "You are an AI assistant that analyzes software projects and finds relevant reference projects and the projects subtags or tags from our portfolio."
    },
    {
      "role": "user",
      "content": `Project Title: ${jobData?.project_details?.title || ''}\nProject Description:\n${jobData?.project_details?.description || ''}\nProject Skills: ${skills.join(', ')}`
    },
    {
      "role": "user",
      "content": `Here are our reference domains and their subtags or tags:\n\n${domainContext}`
    },
    {
      "role": "user",
      "content": `Please analyze the project and find the most relevant reference domains and the subtags or tags of these domains that match best with the project. Return your response in this JSON format:
{
  "references": {
    "domains": [
      {
        "domain": "<domain from our portfolio>",
        "relevance_score": <number between 0 and 1>,
        "tags": [
          {
            "name": "<tag or subtag from our portfolio>",
            "relevance_score": <number between 0 and 1>,
          }
        ]
      }
    ]
  }
}

Important:
1. Only include domains and their fitting subtags or tags from our portfolio (provided above)
2. Return maximum 2 - 5 most relevant domains
3. Return maximum 2 - 5 most relevant subtags or tags
4. Ensure relevance_score accurately reflects how well the domain/tag/subtag matches the project`
    }
  ];

  console.log('[Debug] Final messages for AI:', JSON.stringify(messages, null, 2));
  return messages;
}

// Add this function before the app.post route
function generateAIMessages(vyftec_context, score, explanation, jobData) {
  return [
    {
      "role": "system",
      "content": "You are an AI assistant that generates bid proposals for software projects."
    },
    {
      "role": "user",
      "content": `Company Context:\n${vyftec_context}`
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
    "first_paragraph": "<string, 150-400 characters>",
    "second_paragraph": "<string, 70-180 characters>",
    "third_paragraph": "<string>",
    "question": "<string, 50-100 characters>"
  }
}

First Paragraph

This text is most important as it's the first thing the employer sees. Don't ask questions. The goal is to catch the employers attention by a highly job-context related answer, at best we provide the solution in the first sentence. So the client sees we read the description and employ with the project. Go trough this list and apply the points in this order, only continue to the next point if the previous can not be applied, keeping the answers short and concise:

1. Answer direct questions or tasks given by the client like that the first word is an identifier.
2. Is there a simple solution to the clients job that can be answered in one sentence then do it.
3. Think about, what does the client wants to hear? Can we satisfy his needs and express it in a simple sentence?
3. Outline the approach and technologies that we envision to fulfill the requirements. Try not to repeat technologies mentoined by the client.
4. If there is still space or the other points can't be applied, explain the correlation according the explanation text.

Terminology: Don't ask questions. Make sense, be logical, follow the thread, and keep the flow. Make it easily readable and formulate fluently, cool, and funny, but in a very professional, project management, CEO way. Don't ask questions. Don't use words like experience, expertise, specialization. Don't repeat wordings given by the client too much, instead try to variate and use synonyms in a natural way.

Second Paragraph

Don't generate a second paragraph just use "" as placeholder.

Third Paragraph

Write a contextual, humorous sign-off without asking a question, no longer than 80 signs.

Question

Take care not to repeat anything from the first or third paragraph in the question. A question that we ask the employer about the project. Be very specific and not general. It might ask about the clarifiation of unclear points, what we need in order to create a binding fixed-price estimation, or asking for confirmation of an approach, technologies to use, ways of working, and the like. Keep it short and concise and ask only for one thing.`
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
      projectFile = files.find(file => file.startsWith(`job_${projectId}_`));
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

    // Read vyftec-context.md
    let vyftec_context = '';
    try {
      const contextPath = path.join(__dirname, '..', '..', 'vyftec-context.md');
      vyftec_context = await fs.readFile(contextPath, 'utf8');
      console.log('[Debug] Successfully read context file');
    } catch (error) {
      console.error('[Debug] Error reading context file:', error);
      return res.status(500).json({ error: 'Failed to read context file' });
    }

    try {
      const aiProvider = config.AI_PROVIDER;
      console.log('[Debug] Selected AI provider:', aiProvider);
      
      // First AI request - Generate bid text
      const bidMessages = generateAIMessages(vyftec_context, score, explanation, jobData);
      
      if (aiProvider === 'chatgpt') {
        const openai = new OpenAI({
          apiKey: process.env.OPENAI_API_KEY
        });

        // Generate bid text
        const bidResponse = await openai.chat.completions.create({
          model: process.env.OPENAI_MODEL || "gpt-3.5-turbo",
          messages: bidMessages,
          temperature: 0.7,
          max_tokens: 1000
        });
        
        const aiResponse = bidResponse.choices[0].message.content;
        console.log('[Debug] Raw AI response:', aiResponse);
        
        // Clean and parse the AI response
        const cleanResponse = aiResponse.replace(/```json\s*|\s*```/g, '').trim();
        let parsedResponse;
        try {
          parsedResponse = JSON.parse(cleanResponse);
          console.log('[Debug] Parsed response:', parsedResponse);
        } catch (error) {
          console.error('[Debug] Failed to parse AI response:', error);
          throw new Error('Failed to parse AI response');
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

        // Second AI request - Generate references
        console.log('[Debug] Generating references...');
        const refMessages = await generateReferenceMessages(jobData);
        const refResponse = await openai.chat.completions.create({
          model: process.env.OPENAI_MODEL || "gpt-3.5-turbo",
          messages: refMessages,
          temperature: 0.7,
          max_tokens: 1000
        });

        const refAiResponse = refResponse.choices[0].message.content;
        console.log('[Debug] Raw reference response:', refAiResponse);

        // Parse reference response
        let references;
        try {
          const cleanRefResponse = refAiResponse.replace(/```json\s*|\s*```/g, '').trim();
          references = JSON.parse(cleanRefResponse);
          console.log('[Debug] Parsed references:', references);
        } catch (error) {
          console.error('[Debug] Failed to parse reference response:', error);
          // Set default empty references if parsing fails
          references = { references: { domains: [] } };
        }

        // Construct the second paragraph from references
        let secondParagraph = "Fitting reference projects:";
        if (references?.references?.domains && references.references.domains.length > 0) {
          references.references.domains.forEach(domainRef => {
            // Ensure domain starts with http:// or https://, default to https://
            let domainUrl = domainRef.domain;
            if (!domainUrl.startsWith('http://') && !domainUrl.startsWith('https://')) {
              domainUrl = 'https://' + domainUrl;
            }
            const tagNames = domainRef.tags?.map(tag => tag.name).join(', ') || 'No relevant tags';
            secondParagraph += `\n${domainUrl}, ${tagNames}`;
          });
        } else {
          secondParagraph = "-"; // Fallback if no references found or parsing failed
        }

        // Update the finalBidText with the generated second paragraph
        if (finalBidText?.bid_teaser) {
          finalBidText.bid_teaser.second_paragraph = secondParagraph;
          console.log('[Debug] Updated second paragraph:', finalBidText.bid_teaser.second_paragraph);
        }

        // Update the job file
        if (projectFile) {
          const filePath = path.join(jobsDir, projectFile);
          
          // Ensure ranking object exists
          if (!jobData.ranking) {
            jobData.ranking = {};
          }
          
          // Update bid text and references
          jobData.ranking.bid_text = finalBidText;
          jobData.ranking.references = references.references;
          
          // Write the updated data back to the file
          const updatedContent = JSON.stringify(jobData, null, 2);
          await fs.writeFile(filePath, updatedContent, 'utf8');
          console.log('[Debug] Successfully updated JSON file');
        }

        // Return the bid text and references
        res.json({
          bid_text: finalBidText,
          references: references.references
        });

      } else if (aiProvider === 'deepseek') {
        if (!config.DEEPSEEK_API_BASE || !config.DEEPSEEK_API_KEY) {
          throw new Error('DeepSeek configuration is incomplete');
        }

        const deepseekUrl = `${config.DEEPSEEK_API_BASE}/chat/completions`;
        console.log('[Debug] DeepSeek API URL:', deepseekUrl);

        // Generate bid text
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
        
        // Clean and parse the AI response
        const cleanResponse = aiResponse.replace(/```json\s*|\s*```/g, '').trim();
        let parsedResponse;
        try {
          parsedResponse = JSON.parse(cleanResponse);
          console.log('[Debug] Parsed response:', parsedResponse);
        } catch (error) {
          console.error('[Debug] Failed to parse AI response:', error);
          throw new Error('Failed to parse AI response');
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

        // Second AI request - Generate references
        console.log('[Debug] Generating references...');
        const refMessages = await generateReferenceMessages(jobData);
        const refResponse = await fetch(deepseekUrl, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${config.DEEPSEEK_API_KEY}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            model: config.DEEPSEEK_MODEL,
            messages: refMessages,
            temperature: 0.7,
            max_tokens: 1000
          })
        });

        if (!refResponse.ok) {
          const errorText = await refResponse.text();
          console.error('[Debug] DeepSeek API error response:', {
            status: refResponse.status,
            statusText: refResponse.statusText,
            errorText
          });
          throw new Error(`DeepSeek API error: ${refResponse.status} - ${refResponse.statusText}. Details: ${errorText}`);
        }

        const refData = await refResponse.json();
        const refAiResponse = refData.choices[0].message.content;
        console.log('[Debug] Raw reference response:', refAiResponse);
        
        // Parse reference response
        let references;
        try {
          const cleanRefResponse = refAiResponse.replace(/```json\s*|\s*```/g, '').trim();
          references = JSON.parse(cleanRefResponse);
          console.log('[Debug] Parsed references:', references);
        } catch (error) {
          console.error('[Debug] Failed to parse reference response:', error);
          // Set default empty references if parsing fails
          references = { references: { domains: [] } };
        }

        // Construct the second paragraph from references
        let secondParagraph = "Relevant portfolio projects";
        if (references?.references?.domains && references.references.domains.length > 0) {
          references.references.domains.forEach(domainRef => {
             // Ensure domain starts with http:// or https://, default to https://
            let domainUrl = domainRef.domain;
            if (!domainUrl.startsWith('http://') && !domainUrl.startsWith('https://')) {
              domainUrl = 'https://' + domainUrl;
            }
            const tagNames = domainRef.tags?.map(tag => tag.name).join(', ') || 'No relevant tags';
            secondParagraph += `\n${domainUrl} (${tagNames})`;
          });
        } else {
           secondParagraph = "-"; // Fallback if no references found or parsing failed
        }

        // Update the finalBidText with the generated second paragraph
        if (finalBidText?.bid_teaser) {
          finalBidText.bid_teaser.second_paragraph = secondParagraph;
          console.log('[Debug] Updated second paragraph:', finalBidText.bid_teaser.second_paragraph);
        }

        // Update the job file
        if (projectFile) {
          const filePath = path.join(jobsDir, projectFile);
          
          // Ensure ranking object exists
          if (!jobData.ranking) {
            jobData.ranking = {};
          }
          
          // Update bid text and references
          jobData.ranking.bid_text = finalBidText;
          jobData.ranking.references = references.references;
          
          // Write the updated data back to the file
          const updatedContent = JSON.stringify(jobData, null, 2);
          await fs.writeFile(filePath, updatedContent, 'utf8');
          console.log('[Debug] Successfully updated JSON file');
        }

        // Return the bid text and references
        res.json({
          bid_text: finalBidText,
          references: references.references
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
    
    // Find the file that starts with job_ and contains the project ID
    const projectFile = files.find(file => {
      const match = file.match(/^job_(\d+)_/);
      return match && match[1] === projectId;
    });
    
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

// Remove static file serving - API server only
const PORT = process.env.PORT || 5002;
app.listen(PORT, () => {
  console.log(`API Server running on port ${PORT}`);
}); 