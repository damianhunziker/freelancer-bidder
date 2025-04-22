const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs').promises;
const { exec } = require('child_process');
const notifier = require('node-notifier');
const OpenAI = require('openai');
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
app.use(cors());
app.use(express.json());

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
    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
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
      const contextPath = path.join(__dirname, '..', '..', 'vyftec-context.md');
      console.log('[Debug] Reading context from:', contextPath);
      vyftec_context = await fs.readFile(contextPath, 'utf8');
      console.log('[Debug] Successfully read context file');
    } catch (error) {
      console.warn('[Debug] Could not read vyftec-context.md:', error);
    }

    // Generate bid text using OpenAI
    const openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY
    });

    const response = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [
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
    "first_paragraph": "<string, 100-250 characters>",
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

Compress the explanation text.

Third Paragraph

Translate to the job description base language. Select one of the following, based on the project category, if unsure rely on the general one, dont change the wording of the paragraphs just choose one and dont change it:

- General: "We develop financial apps, corporate websites, and powerful backends tailored to your business needs. With over 20 years of experience, we create robust, scalable, and user-friendly solutions that deliver results."
- Websites & Dashboards: "We specialize in creating impressive corporate websites and powerful dashboards tailored to your business needs. With over 20 years of experience, we build robust, scalable, and user-friendly solutions that drive results."
- Finance: "We create cutting-edge financial apps and automated trading systems. With 20+ years in web development, we deliver robust, scalable solutions for traders and businesses."

Always include these three links in the third paragraph in this order and with this new lines formatting. Don't change the wording or formatof the links, don't add brackets or anything else:
Corporate Websites: https://vyftec.com/corporate-websites
Dashboards: https://vyftec.com/dashboards
Financial Apps: https://vyftec.com/financial-apps

End the third paragraph with a contextual, humorous sign-off on a new line without asking a question, no longer than 80 signs, and sign with "Damian" on a new line.

Question

Take care not to repeat anything from the first or third paragraph in the question. A question that we ask the employer about the project. Be very specific and not general. It might ask about the clarifiation of unclear points, what we need in order to create a binding fixed-price estimation, or asking for confirmation of an approach, technologies to use, ways of working, and the like. Keep it short and concise and ask only for one thing.`
        }
      ],
      temperature: 0.7,
      max_tokens: 500
    });

    const bidText = response.choices[0].message.content;
    console.log('[Debug] OpenAI response:', bidText);

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
      console.error('[Debug] Error parsing OpenAI response:', parseError);
      res.status(500).json({ error: 'Failed to parse bid text response' });
    }
  } catch (error) {
    console.error('[Debug] Error in generate-bid endpoint:', error);
    res.status(500).json({ error: error.message });
  }
});

// Serve static files from the dist directory
app.use(express.static(path.join(__dirname, '..', 'dist')));

// Serve the Vue frontend for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'dist', 'index.html'));
});

const PORT = process.env.PORT || 5002;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
}); 