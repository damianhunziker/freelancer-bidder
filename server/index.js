const express = require('express');
const fs = require('fs').promises;
const path = require('path');
const cors = require('cors');
const { exec } = require('child_process');
const notifier = require('node-notifier');
const OpenAI = require('openai');
const axios = require('axios');
require('dotenv').config();

const app = express();

// Middleware für JSON-Parsing
app.use(express.json());

// Enable CORS for all routes
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  next();
});

// Log all requests
app.use((req, res, next) => {
  console.log(`${req.method} ${req.path}`);
  next();
});

// Handle OPTIONS requests
app.options('*', (req, res) => {
  res.status(200).end();
});

// Load Python config
async function loadPythonConfig() {
  try {
    const configPath = path.join(__dirname, '..', 'config.py');
    const configContent = await fs.readFile(configPath, 'utf8');
    
    // Extract values using regex
    const aiProvider = configContent.match(/AI_PROVIDER\s*=\s*'([^']+)'/)[1];
    const openaiApiKey = configContent.match(/OPENAI_API_KEY\s*=\s*'([^']+)'/)[1];
    const openaiModel = configContent.match(/OPENAI_MODEL\s*=\s*'([^']+)'/)[1];
    const openaiTemp = parseFloat(configContent.match(/OPENAI_TEMPERATURE\s*=\s*([\d.]+)/)[1]);
    const openaiMaxTokens = parseInt(configContent.match(/OPENAI_MAX_TOKENS\s*=\s*(\d+)/)[1]);
    
    const deepseekApiKey = configContent.match(/DEEPSEEK_API_KEY\s*=\s*'([^']+)'/)[1];
    const deepseekApiBase = configContent.match(/DEEPSEEK_API_BASE\s*=\s*"([^"]+)"/)[1];
    const deepseekModel = configContent.match(/DEEPSEEK_MODEL\s*=\s*"([^"]+)"/)[1];
    const deepseekTemp = parseFloat(configContent.match(/DEEPSEEK_TEMPERATURE\s*=\s*([\d.]+)/)[1]);
    const deepseekMaxTokens = parseInt(configContent.match(/DEEPSEEK_MAX_TOKENS\s*=\s*(\d+)/)[1]);

    return {
      aiProvider,
      openai: {
        apiKey: openaiApiKey,
        model: openaiModel,
        temperature: openaiTemp,
        maxTokens: openaiMaxTokens
      },
      deepseek: {
        apiKey: deepseekApiKey,
        apiBase: deepseekApiBase,
        model: deepseekModel,
        temperature: deepseekTemp,
        maxTokens: deepseekMaxTokens
      }
    };
  } catch (error) {
    console.error('Error loading Python config:', error);
    throw error;
  }
}

// Initialize config
let config;
(async () => {
  config = await loadPythonConfig();
  console.log('AI Provider:', config.aiProvider);
})();

// AI request function that handles both providers
async function makeAIRequest(messages) {
  if (!config) {
    throw new Error('Configuration not loaded');
  }

  if (config.aiProvider === 'chatgpt') {
    const openai = new OpenAI({
      apiKey: config.openai.apiKey
    });

    const response = await openai.chat.completions.create({
      model: config.openai.model,
      messages: messages,
      temperature: config.openai.temperature,
      max_tokens: config.openai.maxTokens
    });

    return response.choices[0].message.content;
  } else if (config.aiProvider === 'deepseek') {
    const response = await axios.post(
      `${config.deepseek.apiBase}/chat/completions`,
      {
        model: config.deepseek.model,
        messages: messages,
        temperature: config.deepseek.temperature,
        max_tokens: config.deepseek.maxTokens
      },
      {
        headers: {
          'Authorization': `Bearer ${config.deepseek.apiKey}`,
          'Content-Type': 'application/json'
        }
      }
    );

    return response.data.choices[0].message.content;
  } else {
    throw new Error(`Unsupported AI provider: ${config.aiProvider}`);
  }
}

// Endpoint to list all projects from the jobs folder
app.get('/api/jobs', async (req, res) => {
  try {
    const jobsDir = path.join(__dirname, '..', 'jobs');
    const files = await fs.readdir(jobsDir);
    
    // Filter for job_*.json files
    const jobFiles = files.filter(file => file.startsWith('job_') && file.endsWith('.json'));
    
    // Read and parse all job files
    const jobs = await Promise.all(jobFiles.map(async (filename) => {
      const filePath = path.join(jobsDir, filename);
      const content = await fs.readFile(filePath, 'utf8');
      return JSON.parse(content);
    }));
    
    res.json(jobs);
  } catch (error) {
    console.error('Error reading jobs directory:', error);
    res.status(500).json({ error: error.message });
  }
});

// Endpoint to check if a job file exists
app.get('/api/check-json/:jobId', async (req, res) => {
  try {
    const jobsDir = path.join(__dirname, '..', 'jobs');
    const files = await fs.readdir(jobsDir);
    const jobFile = files.find(file => file.startsWith(`job_${req.params.jobId}_`));
    res.json({ exists: !!jobFile });
  } catch (error) {
    console.error('Error checking job file:', error);
    res.status(500).json({ error: error.message });
  }
});

// Endpoint to update button states for a job
app.post('/api/jobs/:jobId/update', async (req, res) => {
  try {
    const jobId = req.params.jobId;
    const buttonStates = req.body.buttonStates;
    
    console.log('Update request received:');
    console.log('Job ID:', jobId);
    console.log('Button states:', buttonStates);
    
    if (!buttonStates) {
      console.log('Error: buttonStates is missing');
      return res.status(400).json({ error: 'buttonStates is required' });
    }

    const jobsDir = path.join(__dirname, '..', 'jobs');
    console.log('Jobs directory:', jobsDir);
    
    // List all files in the jobs directory
    const files = await fs.readdir(jobsDir);
    console.log('All files in jobs directory:', files);
    
    // Find the job file with more detailed logging
    const jobPattern = `job_${jobId}_`;
    console.log('Looking for files matching pattern:', jobPattern);
    
    const jobFile = files.find(file => {
      const matches = file.startsWith(jobPattern);
      console.log(`Checking file ${file}: ${matches ? 'matches' : 'does not match'}`);
      return matches;
    });
    
    console.log('Found job file:', jobFile);

    if (!jobFile) {
      console.log('Error: Job file not found for ID:', jobId);
      console.log('Available job IDs:', files
        .filter(f => f.startsWith('job_') && f.endsWith('.json'))
        .map(f => f.split('_')[1])
        .join(', '));
      return res.status(404).json({ 
        error: 'Job file not found',
        jobId: jobId,
        availableFiles: files.filter(f => f.startsWith('job_') && f.endsWith('.json'))
      });
    }

    const filePath = path.join(jobsDir, jobFile);
    console.log('Reading file:', filePath);
    
    // Read and update the job file
    const content = await fs.readFile(filePath, 'utf8');
    let jobData;
    try {
      jobData = JSON.parse(content);
    } catch (parseError) {
      console.error('Error parsing job data:', parseError);
      return res.status(500).json({ error: 'Invalid job data format' });
    }

    // Initialize buttonStates if it doesn't exist
    if (!jobData.buttonStates) {
      jobData.buttonStates = {};
    }

    // Update button states
    jobData.buttonStates = {
      ...jobData.buttonStates,
      ...buttonStates
    };

    console.log('Updated job data:', JSON.stringify(jobData, null, 2));

    // Write back to file
    await fs.writeFile(filePath, JSON.stringify(jobData, null, 2));
    console.log('File updated successfully');

    res.json({ 
      success: true, 
      message: 'Button states updated successfully',
      jobId,
      buttonStates: jobData.buttonStates
    });
  } catch (error) {
    console.error('Error updating button states:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add new endpoint for generating bid text
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

    // Check if bid teaser texts already exist in the JSON file
    const jobsDir = path.join(__dirname, '..', 'jobs');
    console.log('[Debug] Looking for jobs in directory:', jobsDir);
    let projectFile = null;
    let jobData = null;

    try {
      const files = await fs.readdir(jobsDir);
      console.log('[Debug] Found files:', files);
      projectFile = files.find(file => file.startsWith(`job_${projectId}_`));
      console.log('[Debug] Found project file:', projectFile);
      
      if (projectFile) {
        const filePath = path.join(jobsDir, projectFile);
        console.log('[Debug] Reading file:', filePath);
        const content = await fs.readFile(filePath, 'utf8');
        jobData = JSON.parse(content);
        
        // Check if bid teaser texts already exist
        if (jobData.ranking?.bid_teaser?.first_paragraph) {
          console.log('[Debug] Bid teaser texts already exist in JSON file');
          return res.json({ bid_teaser: jobData.ranking.bid_teaser });
        }
      }
    } catch (error) {
      console.warn('[Debug] Error reading jobs directory or file:', error);
      // Continue with bid generation if file doesn't exist
    }

    // Read vyftec-context.md
    let vyftec_context = '';
    try {
      const contextPath = path.join(__dirname, '..', 'vyftec-context.md');
      console.log('[Debug] Reading context from:', contextPath);
      vyftec_context = await fs.readFile(contextPath, 'utf8');
      console.log('[Debug] Successfully read context file');
    } catch (error) {
      console.warn('[Debug] Could not read vyftec-context.md:', error);
    }

    // Generate bid text using the configured AI provider
    const messages = [
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

This text is most important as it's the first thing the employer sees. The goal is to catch the employers attention by a highly job-context related answer, at best we provide the solution in the first sentence. So the client sees we read the description and employ with the project. Go trough this list and apply the points in this order, keeping the answers short and concise:

1. Answer direct questions or tasks given by the client like that the first word is an identifier.
2. Is there a simple solution to the clients job that can be answered in one sentence then do it.
3. Think about, what does the client wants to hear? Can we satisfy his needs and express it in a simple sentence?
3. Outline the approach and technologies that we envision to fulfill the requirements. Try not to repeat technologies mentoined by the client.
4. If there is still space or the other points can't be applied, explain the correlation according the explanation text.

Terminology: Make sense, be logical, follow the thread, and keep the flow. Make it easily readable and formulate fluently, cool, and funny, but in a very professional, project management, CEO way. Don't ask questions. Don't use words like experience, expertise, specialization. Don't repeat wordings given by the client too much, instead try to variate and use synonyms in a natural way.

Second Paragraph

Don't generate a second paragraph just use "-" as placeholder.

Third Paragraph

Always include these three links in the third paragraph in this order and with this new lines formatting. Don't change the wording or format of the links, don't add brackets or anything else:
Corporate Websites: https://vyftec.com/corporate-websites
Dashboards: https://vyftec.com/dashboards
Financial Apps: https://vyftec.com/financial-apps

End the third paragraph with a contextual, humorous sign-off on a new line without asking a question, no longer than 80 signs, and sign with "Damian" on a new line.

Question

Take care not to repeat anything from the first or third paragraph in the question. A question that we ask the employer about the project. Be very specific and not general. It might ask about the clarifiation of unclear points, what we need in order to create a binding fixed-price estimation, or asking for confirmation of an approach, technologies to use, ways of working, and the like. Keep it short and concise and ask only for one thing.`
      }
    ];

    const bidText = await makeAIRequest(messages);
    console.log('[Debug] AI response:', bidText);

    try {
      const bidData = JSON.parse(bidText);
      console.log('[Debug] Parsed bid data:', bidData);

      // Write the bid teaser texts to the JSON file if it exists
      if (projectFile) {
        const filePath = path.join(jobsDir, projectFile);
        console.log('[Debug] Writing to file:', filePath);
        console.log('[Debug] Current jobData:', jobData);
        
        // Ensure jobs directory exists
        try {
          await fs.access(jobsDir);
        } catch (error) {
          console.log('[Debug] Jobs directory does not exist, creating it');
          await fs.mkdir(jobsDir, { recursive: true });
        }
        
        // Ensure ranking object exists
        if (!jobData.ranking) {
          console.log('[Debug] Creating new ranking object');
          jobData.ranking = {};
        }
        
        // Update the bid teaser
        console.log('[Debug] Updating bid teaser with:', bidData.bid_teaser);
        jobData.ranking.bid_teaser = bidData.bid_teaser;
        
        // Write the updated data back to the file
        const updatedContent = JSON.stringify(jobData, null, 2);
        console.log('[Debug] Writing updated content:', updatedContent);
        
        await fs.writeFile(filePath, updatedContent, 'utf8');
        console.log('[Debug] Successfully updated JSON file with bid teaser texts');
      } else {
        console.log('[Debug] No project file found, skipping JSON update');
      }

      res.json(bidData);
    } catch (parseError) {
      console.error('[Debug] Error parsing AI response:', parseError);
      res.status(500).json({ error: 'Failed to parse bid text response' });
    }
  } catch (error) {
    console.error('[Debug] Error in generate-bid endpoint:', error);
    res.status(500).json({ error: error.message });
  }
});

// Handle 404 for any other routes
app.use((req, res) => {
  console.log('404 Not Found:', req.method, req.path);
  res.status(404).json({ error: 'Not found' });
});

const PORT = 5002;
app.listen(PORT, () => {
  console.log(`API Server läuft auf Port ${PORT}`);
}); 