require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs').promises;
const { exec } = require('child_process');
const notifier = require('node-notifier');
const OpenAI = require('openai');
const app = express();

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// Store active conversations
const activeConversations = new Map();

// Function to generate a unique conversation ID
function generateConversationId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

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

// Parse JSON bodies
app.use(express.json());

// Add the new route for handling questions
app.post('/api/ask-question', async (req, res) => {
  try {
    const { project_details, bid_text, question, conversation_id } = req.body;
    
    if (!project_details || !bid_text || !question) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Read the vyftec-context.md file from the project root directory
    const contextPath = path.join(__dirname, '..', '..', 'vyftec-context.md');
    let context;
    try {
      context = await fs.readFile(contextPath, 'utf8');
    } catch (error) {
      console.error('Error reading context file:', error);
      return res.status(500).json({ error: 'Failed to read context file' });
    }

    // Get or create conversation
    let conversation = activeConversations.get(conversation_id);
    if (!conversation) {
      // Generate a new conversation ID if none provided
      const newConversationId = generateConversationId();
      conversation = {
        messages: [
          {
            role: "system",
            content: `You are a helpful assistant that provides detailed answers about projects based on the provided context. 
            You should maintain context from previous questions and provide natural, conversational responses.
            If the user's response is short (like "yes" or "ok"), ask for more specific details about what they'd like to know.
            Always provide relevant information from the project details and context.
            
            Context about Vyftec:
            ${context}
            
            Project Details:
            Title: ${project_details.title}
            Description: ${project_details.description}
            Budget: ${project_details.budget || 'Not specified'}
            Country: ${project_details.country || 'Not specified'}
            Project Type: ${project_details.project_type || 'Not specified'}
            
            AI Evaluation:
            ${bid_text}`
          }
        ]
      };
      activeConversations.set(newConversationId, conversation);
      return res.json({ 
        response: "I understand you're interested in this project. To provide a more detailed and accurate response, I would need to know more about your specific concerns or requirements. Could you please provide more context about what aspects of the project you'd like to discuss?",
        conversation_id: newConversationId 
      });
    }

    // Add the user's question to the conversation
    conversation.messages.push({
      role: "user",
      content: question
    });

    // Call OpenAI API with the full conversation history
    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: conversation.messages,
      temperature: 0.7,
      max_tokens: 500
    });

    const response = completion.choices[0].message.content;
    
    // Add the assistant's response to the conversation
    conversation.messages.push({
      role: "assistant",
      content: response
    });

    // Clean up old conversations (keep only the last 100 messages)
    if (conversation.messages.length > 100) {
      conversation.messages = [
        conversation.messages[0], // Keep the system message
        ...conversation.messages.slice(-99) // Keep the last 99 messages
      ];
    }

    res.json({ 
      response,
      conversation_id 
    });
  } catch (error) {
    console.error('Error processing question:', error);
    res.status(500).json({ 
      error: 'Failed to process question',
      details: error.message 
    });
  }
});

// Add a route to get conversation history
app.get('/api/conversation/:conversation_id', (req, res) => {
  const conversation = activeConversations.get(req.params.conversation_id);
  if (!conversation) {
    return res.status(404).json({ error: 'Conversation not found' });
  }
  res.json(conversation);
});

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

// Serve static files from the dist directory
app.use(express.static(path.join(__dirname, '..', 'dist')));

// Serve the Vue frontend for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'dist', 'index.html'));
});

const PORT = 8080;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
}); 