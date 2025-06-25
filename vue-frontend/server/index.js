const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs').promises;
const { exec } = require('child_process');
// Removed notifier to reduce dependencies
const OpenAI = require('openai');
const config = require('../config-loader');
const { formatBidText } = require('../src/utils/formatBidText');
const { shouldProceedWithApiCall, handleRateLimitResponse } = require('./rateLimitManager');

// Heartbeat functionality for Node.js
const heartbeatFile = path.join(__dirname, '..', '..', 'heartbeat_status.json');

function sendHeartbeat(processName, additionalData = {}) {
  try {
    // Read current data
    let data = { last_updated: Date.now() / 1000, processes: {} };
    try {
      if (require('fs').existsSync(heartbeatFile)) {
        data = JSON.parse(require('fs').readFileSync(heartbeatFile, 'utf8'));
      }
    } catch (e) {
      console.warn('Could not read heartbeat file, creating new one');
    }
    
    // Update process heartbeat
    const processData = {
      last_heartbeat: Date.now() / 1000,
      last_heartbeat_formatted: new Date().toLocaleString(),
      pid: process.pid,
      status: 'alive',
      ...additionalData
    };
    
    data.processes[processName] = processData;
    data.last_updated = Date.now() / 1000;
    
    // Write back to file
    require('fs').writeFileSync(heartbeatFile, JSON.stringify(data, null, 2));
  } catch (error) {
    console.error(`Error sending heartbeat for ${processName}:`, error);
  }
}

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
  addSubtagToDomain,
  // Projects
  getAllProjects,
  getProjectById,
  createProject,
  updateProject,
  deleteProject,
  addProjectFile,
  updateProjectFile,
  deleteProjectFile,
  linkJobToProject,
  createProjectFromJob,
  addTagToProject,
  removeProjectTag,
  // Contacts
  getAllContacts,
  getContactById,
  createContact,
  updateContact,
  deleteContact,
  addPhoneNumber,
  updatePhoneNumber,
  deletePhoneNumber,
  // Customers  
  getAllCustomers,
  getCustomerById,
  createCustomer,
  updateCustomer,
  deleteCustomer,
  getCustomerProjects
} = require('./database');
require('dotenv').config();
const app = express();

// Global variables removed to reduce logging

// Add new constants for bid monitoring
const BID_CHECK_ENABLED = false; // Set to false to disable bid monitoring entirely
const BID_CHECK_INTERVAL = 30000; // 30 seconds (increased from 10 seconds)
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

// Global question posting lock system - prevent duplicate submissions
const questionPostingLocks = new Set();

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

// Enhanced API logging functions  
function logInternalAPIRequest(req, res, responseData = null) {
  try {
    const timestamp = new Date().toLocaleString();
    const method = req.method;
    const endpoint = req.originalUrl || req.url;
    const ip = req.ip || req.connection.remoteAddress || 'Unknown';
    
    // Determine if this is a project-related API request
    const isProjectAPI = endpoint.includes('/api/') && (
      endpoint.includes('project') || 
      endpoint.includes('job') || 
      endpoint.includes('bid') || 
      endpoint.includes('generate-bid') ||
      endpoint.includes('send-application') ||
      endpoint.includes('button-state')
    );
    
    if (isProjectAPI) {
      let endpointType = "UNKNOWN";
      let projectId = null;
      
      // Extract endpoint type and project ID
      if (endpoint.includes('/api/jobs')) {
        endpointType = "GET_JOBS";
        // Skip logging GET_JOBS requests as they are too frequent
        return;
      } else if (endpoint.includes('/api/check-json/')) {
        endpointType = "CHECK_JSON";
        projectId = endpoint.split('/api/check-json/')[1]?.split('/')[0];
      } else if (endpoint.includes('/api/generate-bid/')) {
        endpointType = "GENERATE_BID";
        projectId = endpoint.split('/api/generate-bid/')[1]?.split('/')[0];
      } else if (endpoint.includes('/api/send-application/')) {
        endpointType = "SEND_APPLICATION";
        projectId = endpoint.split('/api/send-application/')[1]?.split('/')[0];
      } else if (endpoint.includes('/api/update-button-state')) {
        endpointType = "UPDATE_BUTTON_STATE";
        projectId = req.body?.projectId;
      } else if (endpoint.includes('/api/test-freelancer-auth')) {
        endpointType = "TEST_FREELANCER_AUTH";
      } else if (endpoint.includes('/api/test-price-validation/')) {
        endpointType = "TEST_PRICE_VALIDATION";
        projectId = endpoint.split('/api/test-price-validation/')[1]?.split('/')[0];
      } else if (endpoint.includes('/api/projects/') && endpoint.includes('/error')) {
        endpointType = "SAVE_PROJECT_ERROR";
        projectId = endpoint.split('/api/projects/')[1]?.split('/')[0];
      } else if (endpoint.includes('/api/auto-bidding-logs')) {
        endpointType = "GET_AUTO_BIDDING_LOGS";
      } else if (endpoint.includes('/api/indexer/status')) {
        endpointType = "GET_INDEXER_STATUS";
      }
      
      // Extract request info
      let requestInfo = {};
      if (req.body && Object.keys(req.body).length > 0) {
        // Log relevant request body fields
        if (req.body.score) requestInfo.score = req.body.score;
        if (req.body.explanation) requestInfo.explanation_length = req.body.explanation?.length || 0;
        if (req.body.buttonType) requestInfo.button_type = req.body.buttonType;
        if (req.body.state !== undefined) requestInfo.state = req.body.state;
        if (req.body.error) requestInfo.error_type = req.body.error.type;
      }
      
      // Extract query parameters
      if (req.query && Object.keys(req.query).length > 0) {
        if (req.query.limit) requestInfo.limit = req.query.limit;
        if (req.query.filename) requestInfo.filename = req.query.filename;
      }
      
      // Extract response info if available
      let responseInfo = {};
      if (responseData) {
        if (responseData.success !== undefined) responseInfo.success = responseData.success;
        if (responseData.bid_submitted !== undefined) responseInfo.bid_submitted = responseData.bid_submitted;
        if (responseData.error) responseInfo.error = responseData.error;
        if (responseData.jobs) responseInfo.jobs_count = responseData.jobs.length;
        if (responseData.logs) responseInfo.logs_count = responseData.logs.length;
        if (responseData.exists !== undefined) responseInfo.file_exists = responseData.exists;
        if (responseData.running !== undefined) responseInfo.indexer_running = responseData.running;
        if (responseData.bid_text) responseInfo.bid_generated = true;
        if (responseData.freelancer_response) responseInfo.freelancer_api_success = true;
      }
      
      // Format log entry
      let logEntry = `${timestamp} | VUE-INTERNAL | ${endpointType} | ${method} | ${endpoint}`;
      
      if (projectId) {
        logEntry += ` | project_id=${projectId}`;
      }
      
      if (Object.keys(requestInfo).length > 0) {
        const requestStr = Object.entries(requestInfo).map(([k, v]) => `${k}=${v}`).join(' | ');
        logEntry += ` | REQUEST: ${requestStr}`;
      }
      
      if (Object.keys(responseInfo).length > 0) {
        const responseStr = Object.entries(responseInfo).map(([k, v]) => `${k}=${v}`).join(' | ');
        logEntry += ` | RESPONSE: ${responseStr}`;
      }
      
      logEntry += ` | STATUS: ${res.statusCode} | IP: ${ip}\n`;
      
      // Write to log file
      const fs = require('fs').promises;
      const logPath = path.join(__dirname, '..', '..', 'api_logs', 'freelancer_requests.log');
      fs.appendFile(logPath, logEntry).catch(err => {
        console.error('Error writing to internal API log:', err);
      });
    }
  } catch (error) {
    console.error('Error logging internal API request:', error);
  }
}

// API Logging function for vue-frontend
function logFreelancerAPIRequest(url, options, response, responseData = null) {
  try {
    const timestamp = new Date().toLocaleString();
    const method = options.method || 'GET';

    // Determine if this is a Projects API request
    const isProjectsAPI = url.includes('/projects/0.1/');
    
    if (isProjectsAPI) {
      let endpointType = "UNKNOWN";
      if (url.includes('/projects/active')) {
        endpointType = "GET_ACTIVE_PROJECTS";
      } else if (url.includes('/bids/') && method === 'POST') {
        endpointType = "CREATE_BID";
      } else if (url.includes('/bids/') && method === 'PUT') {
        endpointType = "UPDATE_BID";
      } else if (url.includes('/bids/') && method === 'GET') {
        endpointType = "GET_BIDS";
      } else if (url.includes('/projects/') && url.split('/').length >= 6) {
        endpointType = "GET_PROJECT_DETAILS";
      }
      
      // Extract response info
      let responseInfo = {};
      if (responseData) {
        if (responseData.result) {
          if (responseData.result.projects) {
            responseInfo.projects_count = responseData.result.projects.length;
          }
          if (responseData.result.id) {
            responseInfo.project_id = responseData.result.id;
          }
          if (responseData.result.bidder_id) {
            responseInfo.bidder_id = responseData.result.bidder_id;
          }
          if (responseData.result.amount) {
            responseInfo.bid_amount = responseData.result.amount;
          }
        }
      }
      
      // Format log entry
      let logEntry = `${timestamp} | VUE-FRONTEND | ${endpointType} | ${method} | ${url}`;
      if (Object.keys(responseInfo).length > 0) {
        const responseStr = Object.entries(responseInfo).map(([k, v]) => `${k}=${v}`).join(' | ');
        logEntry += ` | RESPONSE: ${responseStr}`;
      }
      logEntry += ` | STATUS: ${response.status}\n`;
      
      // Write to log file
      const fs = require('fs').promises;
      const logPath = path.join(__dirname, '..', '..', 'api_logs', 'freelancer_requests.log');
      fs.appendFile(logPath, logEntry).catch(err => {
        console.error('Error writing to API log:', err);
      });
    }
  } catch (error) {
    console.error('Error logging Freelancer API request:', error);
  }
}

// Centralized API call function with timeout and retry logic
async function makeAPICallWithTimeout(url, options = {}, retryCount = 0) {
  const maxRetries = 3;
  const timeoutMs = 30000; // 30 seconds timeout
  const context = options.context || 'API call';
  const allowBidGeneration = options.allowBidGeneration || false;
  
  // Check global rate limit before making API call
  if (!shouldProceedWithApiCall(context, allowBidGeneration)) {
    logAutoBiddingServer(`Skipping ${context} due to rate limiting`, 'warning');
    // Return a response-like object instead of throwing an error
    return {
      ok: false,
      status: 429,
      statusText: 'Rate Limited',
      rateLimited: true,
      json: async () => ({ error: 'Rate limit active', message: `Skipping ${context}` }),
      text: async () => `Rate limit active - skipping ${context}`
    };
  }
  
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
    delete apiOptions.allowBidGeneration; // Remove this custom option

    const response = await fetch(url, apiOptions);

    // Clear timeout if request completes
    clearTimeout(timeoutId);

    // Log Freelancer API requests
    try {
      if (url.includes('freelancer.com/api')) {
        let responseData = null;
        try {
          const responseText = await response.clone().text();
          responseData = JSON.parse(responseText);
        } catch (e) {
          // Response is not JSON, ignore
        }
        logFreelancerAPIRequest(url, options, response, responseData);
      }
    } catch (logError) {
      console.error('Error in API logging:', logError);
    }

    // Handle rate limiting - set global timeout
    if (response.status === 429) {
      handleRateLimitResponse(context);
      throw new Error(`Rate limit exceeded in ${context}. Global timeout set for 30 minutes.`);
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

// Add middleware to log all incoming API requests
app.use('/api/', (req, res, next) => {
  // Store original res.json and res.send to intercept responses
  const originalJson = res.json;
  const originalSend = res.send;
  
  let responseData = null;
  
  // Override res.json to capture response data
  res.json = function(data) {
    responseData = data;
    logInternalAPIRequest(req, res, responseData);
    return originalJson.call(this, data);
  };
  
  // Override res.send to capture response data (for non-JSON responses)
  res.send = function(data) {
    if (!responseData) {
      try {
        responseData = typeof data === 'string' ? JSON.parse(data) : data;
      } catch (e) {
        responseData = { raw_response: typeof data === 'string' ? data.substring(0, 100) : String(data).substring(0, 100) };
      }
      logInternalAPIRequest(req, res, responseData);
    }
    return originalSend.call(this, data);
  };
  
  next();
});

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
  // Check if we should use vector store or SQL database
  let useVectorStore = false;
  let correlationAnalysisMode = 'SQL'; // Default fallback
  
  try {
    // Try to load config from Python
    const { exec } = require('child_process');
    const util = require('util');
    const execPromise = util.promisify(exec);
    
    try {
      const { stdout } = await execPromise('python3 -c "from config import CORRELATION_ANALYSIS_MODE; print(CORRELATION_ANALYSIS_MODE)"', {
        cwd: path.join(__dirname, '..', '..')
      });
      correlationAnalysisMode = stdout.trim();
      useVectorStore = ['VECTOR_STORE', 'HYBRID'].includes(correlationAnalysisMode);
      console.log(`[Debug] Using correlation analysis mode: ${correlationAnalysisMode}`);
    } catch (configError) {
      console.log('[Debug] Could not load config.py, using default SQL mode:', configError.message);
    }
  } catch (error) {
    console.log('[Debug] Error checking correlation analysis mode, using SQL fallback:', error.message);
  }

  // If vector store is enabled, try to use Python correlation manager
  if (useVectorStore) {
    try {
      console.log('[Debug] 🚀 Using Vector Store correlation analysis...');
      
      // Call Python correlation manager
      const { exec } = require('child_process');
      const util = require('util');
      const execPromise = util.promisify(exec);
      
      // Prepare job data for Python script
      const jobDescription = `${jobData?.project_details?.title || ''}\n${jobData?.project_details?.description || ''}`;
      const skills = jobData?.project_details?.jobs?.map(job => job.name) || [];
      const jobDescriptionWithSkills = `${jobDescription}\nSkills: ${skills.join(', ')}`;
      
      // Escape quotes for shell command
      const escapedJobDescription = jobDescriptionWithSkills.replace(/"/g, '\\"').replace(/'/g, "\\'");
      
      // Run Python correlation analysis
      const pythonCommand = `python3 -c "
import json
import sys
try:
    from correlation_manager import CorrelationManager
    
    manager = CorrelationManager()
    job_description = '''${escapedJobDescription}'''
    
    result = manager.analyze_job_correlation(job_description)
    
    # Output the result as JSON for Node.js to parse
    output = {
        'success': True,
        'analysis_mode': result.analysis_mode,
        'execution_time_ms': result.execution_time_ms,
        'enhanced_analysis': result.enhanced_analysis,
        'correlation_analysis': result.correlation_analysis,
        'fallback_used': result.fallback_used,
        'error_message': result.error_message
    }
    print(json.dumps(output))
    
except Exception as e:
    print(json.dumps({
        'success': False,
        'error': str(e),
        'fallback_to_sql': True
    }))
"`;

      const { stdout, stderr } = await execPromise(pythonCommand, {
        cwd: path.join(__dirname, '..', '..'),
        timeout: 30000 // 30 second timeout
      });
      
      if (stderr) {
        console.log('[Debug] Python stderr:', stderr);
      }
      
      const pythonResult = JSON.parse(stdout.trim());
      
      if (pythonResult.success) {
        console.log(`[Debug] ✅ Vector Store analysis successful: ${pythonResult.analysis_mode} in ${pythonResult.execution_time_ms}ms`);
        
        if (pythonResult.fallback_used) {
          console.log(`[Debug] ⚠️  Fallback used: ${pythonResult.fallback_used}`);
        }
        
        // Convert Python result to AI messages format
        const correlationResults = pythonResult.correlation_analysis;
        
        // Create a simulated AI response that the existing parsing logic can handle
        const simulatedAIResponse = JSON.stringify({ correlation_analysis: correlationResults });
        
        // Return in the format expected by the rest of the system
        return [
          {
            "role": "system",
            "content": "Vector Store correlation analysis completed successfully."
          },
          {
            "role": "assistant", 
            "content": simulatedAIResponse
          }
        ];
        
      } else {
        console.log('[Debug] ⚠️  Vector Store analysis failed, falling back to SQL:', pythonResult.error);
        // Fall through to SQL analysis
      }
      
    } catch (vectorError) {
      console.log('[Debug] ⚠️  Vector Store analysis error, falling back to SQL:', vectorError.message);
      // Fall through to SQL analysis
    }
  }

  // SQL/Legacy correlation analysis (original implementation)
  console.log('[Debug] 🗄️  Using SQL-based correlation analysis...');
  
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
1. Read the job description and find out what the client expects from us for to apply to the job. **Ensure the direct response to customer questions, tasks, or application requirements is fully answered** and placed in the opening section. Rephrase if necessary—you may use lists. Please include domains, education, and employment where relevant. Describe solutions using conjunctive or indicative (can or could).
2. In total the **text should include 1-2 enumerations, but keep the amount of non-list/enum paragraphs same or higher than the amount of list/enum paragraphs**. To loosen things up (e.g., projects, education, employment, timeline breakdown, solution structure, client demands, etc.).
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

### Find out what the clients wants
Read the job description and find out what the client expects from us for to apply to the job. Often they mention a list of questions to answer to apply or there is a codeword.

### Process Flow
1. **Simple Question/Task Resolution**  
   - If job post contains direct technical/process questions/tasks (e.g., "How would you solve X?" or "List similar projects):  
     → Research → Answer concisely in 1 sentence.  
   - **Write the solution in the first sentence.**  
   - *Example: "For PDF conversion, I recommend Python's PyMuPDF library for its batch processing capabilities."*

2. **Application Requirements Alignment**  
   - Find out what the client wants by reading the job description.
   - Answer any task / requirement / item that is asked for or is necessary to be answered or demanded by the client.
   - Mirror client's requested structure/format:  
     • If client uses bullet points → Use bullet points  
     • If numbered list → Use numbered list  
     • If plain text → Use plain text  
   - → Cover ALL explicit requirements from "How to apply" section.  
   - **Answer the requirements in the first sentence.**  

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
   - **Suggest technologies according the project scope and complexity**. For example: If someone needs a simple AI agent with some basic automation suggest n8n instead of a full-fledged python laravel app.
   - Propose high-level approach, using conjunctive or indicative (can or could) instead of present continuous or future tense (will do):  
     → Phasing (e.g., "Feasibility study → First prototype → MVP → Full-scale app")  
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
Take care not to repeat anything from other paragraphs in the question. A question that we ask the employer about the project, **in order to clarify issues ** for an estimation. Be very specific and not general. Keep it short and concise and **ask only for one thing.** It might ask about the clarification of unclear points, what we need in order to create a binding estimation, or asking for confirmation of an approach, technologies to use, ways of working. **No security related questions, if not explicitly asked or necessary.**

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
- **Don't invent anything! Stick only to the objective facts that come from the company context and data.** If you can not say something to a topic leave it away.
- We provide competitive rates through an **Asia-based workforce**, AI agents and low-code production.
`
    }
  ];
}

// Then modify the app.post route to use this function
app.post('/api/generate-bid/:projectId', async (req, res) => {
  const projectId = req.params.projectId;
  const { score, explanation } = req.body;

  logAutoBiddingServer(`🔍 Generate bid request received for project ${projectId}`, 'info', projectId);

  try {
    // Find the job file
    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
    const files = await fs.readdir(jobsDir);
    const projectFile = files.find(file => file.includes(`job_${projectId}.json`));
    
    if (!projectFile) {
      console.log('[Debug] No job file found for project:', projectId);
      return res.status(404).json({ error: 'Project not found' });
    }

    // Read current job data
    let jobData;
    try {
      const filePath = path.join(jobsDir, projectFile);
      const fileContent = await fs.readFile(filePath, 'utf8');
      jobData = JSON.parse(fileContent);
      console.log('[Debug] Successfully read job data for project:', projectId);
    } catch (error) {
      console.error('[Debug] Error reading job file:', error);
      return res.status(500).json({ error: 'Failed to read job data' });
    }

    // ✅ CRITICAL CHECK #1: Never regenerate if bid texts already exist
    if (jobData.ranking?.bid_teaser?.first_paragraph) {
      console.log('[Debug] ✅ BID TEXTS ALREADY EXIST - ABSOLUTELY NO REGENERATION ALLOWED');
      console.log('[Debug] Existing bid teaser found:', {
        first_paragraph: jobData.ranking.bid_teaser.first_paragraph ? 'EXISTS' : 'MISSING',
        second_paragraph: jobData.ranking.bid_teaser.second_paragraph ? 'EXISTS' : 'MISSING',
        third_paragraph: jobData.ranking.bid_teaser.third_paragraph ? 'EXISTS' : 'MISSING',
        question: jobData.ranking.bid_teaser.question ? 'EXISTS' : 'MISSING'
      });
      
      logAutoBiddingServer(`✅ PROTECTION: Bid texts already exist for project ${projectId} - returning existing data WITHOUT regeneration`, 'info', projectId);
      
      // Return existing bid texts without regeneration
      return res.json({
        success: true,
        bid_text: { bid_teaser: jobData.ranking.bid_teaser },
        bid_teaser: jobData.ranking.bid_teaser,
        project_id: projectId,
        message: 'Using existing bid texts (PROTECTION: no regeneration performed)',
        existing_data: true,
        protection_triggered: true
      });
    }

    // ✅ CRITICAL CHECK #2: Double-check for any bid_teaser content
    if (jobData.ranking?.bid_teaser && Object.keys(jobData.ranking.bid_teaser).length > 0) {
      console.log('[Debug] ✅ BID TEASER OBJECT EXISTS - ADDITIONAL PROTECTION TRIGGERED');
      console.log('[Debug] Bid teaser keys found:', Object.keys(jobData.ranking.bid_teaser));
      
      // Check if any of the bid teaser fields have content
      const hasAnyContent = Object.values(jobData.ranking.bid_teaser).some(value => 
        value && typeof value === 'string' && value.trim().length > 0
      );
      
      if (hasAnyContent) {
        logAutoBiddingServer(`✅ ADDITIONAL PROTECTION: Bid teaser has content for project ${projectId} - returning existing data`, 'info', projectId);
        
        return res.json({
          success: true,
          bid_text: { bid_teaser: jobData.ranking.bid_teaser },
          bid_teaser: jobData.ranking.bid_teaser,
          project_id: projectId,
          message: 'Using existing bid texts (ADDITIONAL PROTECTION: no regeneration performed)',
          existing_data: true,
          additional_protection_triggered: true
        });
      }
    }

    console.log('[Debug] ✅ NO EXISTING BID TEXTS FOUND - PROCEEDING WITH GENERATION');
    logAutoBiddingServer(`📝 No existing bid texts found for project ${projectId} - proceeding with generation`, 'info', projectId);

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
        let correlationResults;
        let correlationAiResponse;
        
        // Check if we already have a vector store result
        if (correlationMessages.length === 2 && correlationMessages[1].role === 'assistant') {
          // We have a vector store result, use it directly
          correlationAiResponse = correlationMessages[1].content;
          console.log('[Debug] 🚀 Using Vector Store correlation analysis result');
          
          try {
            correlationResults = parseAIResponse(correlationAiResponse, 'correlation analysis');
          } catch (error) {
            console.error('[Debug] Failed to parse vector store correlation analysis response:', error);
            throw new Error('Failed to parse vector store correlation analysis response');
          }
        } else {
          // Use traditional AI correlation analysis
          const correlationStepMessages = [...conversationMessages, ...correlationMessages.slice(1)]; // Skip system message since we already have it
          
          const correlationResponse = await openai.chat.completions.create({
            model: process.env.OPENAI_MODEL || "gpt-3.5-turbo",
            messages: correlationStepMessages,
            temperature: 0.7,
            max_tokens: 1000
          });
          
          correlationAiResponse = correlationResponse.choices[0].message.content;
          
          // Parse the AI response using robust parsing
          try {
            correlationResults = parseAIResponse(correlationAiResponse, 'correlation analysis');
          } catch (error) {
            console.error('[Debug] Failed to parse correlation analysis response:', error);
            throw new Error('Failed to parse correlation analysis response');
          }
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
          temperature: 0.3,
          max_tokens: 2000
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
        let correlationResults;
        let correlationAiResponse;
        
        // Check if we already have a vector store result
        if (correlationMessages.length === 2 && correlationMessages[1].role === 'assistant') {
          // We have a vector store result, use it directly
          correlationAiResponse = correlationMessages[1].content;
          console.log('[Debug] 🚀 Using Vector Store correlation analysis result');
          
          try {
            correlationResults = parseAIResponse(correlationAiResponse, 'correlation analysis');
          } catch (error) {
            console.error('[Debug] Failed to parse vector store correlation analysis response:', error);
            throw new Error('Failed to parse vector store correlation analysis response');
          }
        } else {
          // Use traditional AI correlation analysis
          const correlationStepMessages = [...conversationMessages, ...correlationMessages.slice(1)]; // Skip system message since we already have it
          
          console.log('[Debug] Sending correlation analysis request to DeepSeek...');
          console.log('[Debug] Messages count:', correlationStepMessages.length);
          console.log('[Debug] Model:', config.DEEPSEEK_MODEL);
          
          const correlationResponse = await makeAPICallWithTimeout(deepseekUrl, {
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
            }),
            context: 'DeepSeek correlation analysis',
            allowBidGeneration: true
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
          correlationAiResponse = correlationData.choices[0].message.content;
          console.log('[Debug] Raw AI response:', correlationAiResponse);
          
          // Parse the AI response using robust parsing
          try {
            correlationResults = parseAIResponse(correlationAiResponse, 'correlation analysis');
          } catch (error) {
            console.error('[Debug] Failed to parse correlation analysis response:', error);
            throw new Error('Failed to parse correlation analysis response');
          }
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
        
        const bidResponse = await makeAPICallWithTimeout(deepseekUrl, {
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
          }),
          context: 'DeepSeek bid generation',
          allowBidGeneration: true
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
        
        const compositionResponse = await makeAPICallWithTimeout(deepseekUrl, {
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
          }),
          context: 'DeepSeek final composition',
          allowBidGeneration: true
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

        // Automatic bid submission is now handled client-side
        console.log('[Debug] Bid text generated - client-side will handle automatic submission');
        logAutoBiddingServer(`✅ Bid text generated for project ${projectId} - automatic submission handled by frontend`, 'info', projectId);

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

// Function to get current bid count from Freelancer API
async function getCurrentBidCount(projectId) {
  try {
    const response = await makeAPICallWithTimeout(`https://www.freelancer.com/api/projects/0.1/projects/${projectId}/?bids=true&bid_details=true`, {
      method: 'GET',
      headers: {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
        'Content-Type': 'application/json'
      },
      context: 'Get Current Bid Count'
    });

    if (!response.ok) {
      throw new Error(`Failed to get current bid count: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    console.log('[Debug] Full API response structure:', JSON.stringify(data, null, 2));
    
    // Try different response structures
    let project = null;
    let bidCount = 0;
    
    // Method 1: Check if projects is an object with projectId as key
    if (data.result?.projects?.[projectId]) {
      project = data.result.projects[projectId];
      bidCount = project.bid_stats?.bid_count || 0;
      console.log('[Debug] Found project using Method 1 (projects[projectId]):', { bidCount, status: project.status });
    }
    // Method 2: Check if projects is an array
    else if (data.result?.projects && Array.isArray(data.result.projects)) {
      project = data.result.projects.find(p => p.id == projectId);
      if (project) {
        bidCount = project.bid_stats?.bid_count || 0;
        console.log('[Debug] Found project using Method 2 (projects array):', { bidCount, status: project.status });
      }
    }
    // Method 3: Check if project is directly in result
    else if (data.result?.id == projectId) {
      project = data.result;
      bidCount = project.bid_stats?.bid_count || 0;
      console.log('[Debug] Found project using Method 3 (direct result):', { bidCount, status: project.status });
    }
    // Method 4: Check if there's a single project in result
    else if (data.result && typeof data.result === 'object' && !Array.isArray(data.result)) {
      // Sometimes the API returns the project data directly
      if (data.result.bid_stats || data.result.title) {
        project = data.result;
        bidCount = project.bid_stats?.bid_count || 0;
        console.log('[Debug] Found project using Method 4 (direct object):', { bidCount, title: project.title });
      }
    }
    
    if (!project) {
      console.error('[Debug] Project not found in any expected structure. Available keys:', Object.keys(data.result || {}));
      console.error('[Debug] Projects structure:', data.result?.projects ? Object.keys(data.result.projects) : 'No projects key');
      throw new Error(`Project ${projectId} not found in API response`);
    }

    const result = {
      bid_count: bidCount,
      project_status: project.status || 'unknown',
      project_title: project.title || 'Unknown Title'
    };
    
    console.log('[Debug] Final bid count result:', result);
    return result;
    
  } catch (error) {
    console.error('[Debug] Error getting current bid count:', error);
    throw error;
  }
}

// Function to save error to project JSON
async function saveErrorToProjectJson(projectId, error, errorType = 'bid_submission') {
  try {
    const jobsDir = path.join(__dirname, '..', '..', 'jobs');
    const projectFile = `job_${projectId}.json`;
    const filePath = path.join(jobsDir, projectFile);
    
    const content = await fs.readFile(filePath, 'utf8');
    const jobData = JSON.parse(content);
    
    // Initialize error tracking
    if (!jobData.errors) {
      jobData.errors = [];
    }
    
    // Add new error
    const errorEntry = {
      type: errorType,
      message: error.message || error,
      timestamp: new Date().toISOString(),
      context: error.context || 'Unknown'
    };
    
    jobData.errors.push(errorEntry);
    
    // Also add to buttonStates for UI display
    if (!jobData.buttonStates) {
      jobData.buttonStates = {};
    }
    
    jobData.buttonStates.manualSubmissionRequired = true;
    jobData.buttonStates.errorMessage = error.message || error;
    jobData.buttonStates.errorTimestamp = new Date().toISOString();
    jobData.buttonStates.errorType = errorType;
    
    // Write back to file
    await fs.writeFile(filePath, JSON.stringify(jobData, null, 2));
    console.log(`[Debug] Error saved to project ${projectId}:`, errorEntry);
    
    return errorEntry;
  } catch (saveError) {
    console.error('[Debug] Failed to save error to project JSON:', saveError);
    throw saveError;
  }
}

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
      const error = { message: 'No bid text available for this project', context: 'bid_text_check' };
      await saveErrorToProjectJson(projectId, error, 'missing_bid_text');
      return res.status(400).json({ error: 'No bid text available for this project' });
    }

    // ✅ CRITICAL CHECK: Get current bid count from Freelancer API before submission
    console.log('[Debug] ✅ Checking current bid count before submission...');
    let currentBidInfo;
    try {
      currentBidInfo = await getCurrentBidCount(projectId);
      console.log('[Debug] Current bid info from API:', currentBidInfo);
    } catch (bidCountError) {
      console.error('[Debug] Failed to get current bid count from API:', bidCountError);
      
      // Fallback: Use bid count from local JSON data
      const localBidCount = jobData.project_details?.bid_stats?.bid_count || 0;
      console.log(`[Debug] Using fallback bid count from local JSON: ${localBidCount}`);
      
      if (localBidCount > 0) {
        currentBidInfo = {
          bid_count: localBidCount,
          project_status: 'unknown',
          project_title: jobData.project_details?.title || 'Unknown Title',
          source: 'local_fallback'
        };
        console.log('[Debug] Using local bid count as fallback:', currentBidInfo);
      } else {
        // If both API and local data fail, allow submission with warning
        console.log('[Debug] No bid count available from API or local data - proceeding with submission');
        currentBidInfo = {
          bid_count: 0,
          project_status: 'unknown',
          project_title: jobData.project_details?.title || 'Unknown Title',
          source: 'default_fallback'
        };
      }
    }

    // Check if bid count exceeds limit (default 200, configurable)
    const bidLimit = req.body.bidLimit || 200;
    const bidSource = currentBidInfo.source || 'api';
    
    console.log(`[Debug] Bid count check: ${currentBidInfo.bid_count}/${bidLimit} (source: ${bidSource})`);
    
    if (currentBidInfo.bid_count >= bidLimit) {
      console.log(`[Debug] ❌ BID COUNT TOO HIGH: ${currentBidInfo.bid_count} >= ${bidLimit} (source: ${bidSource})`);
      
      const error = { 
        message: `Too many bids: ${currentBidInfo.bid_count} bids (limit: ${bidLimit}) [source: ${bidSource}]`, 
        context: 'bid_count_exceeded',
        current_bid_count: currentBidInfo.bid_count,
        bid_limit: bidLimit,
        project_status: currentBidInfo.project_status,
        bid_source: bidSource
      };
      await saveErrorToProjectJson(projectId, error, 'bid_count_exceeded');
      
      return res.json({
        success: false,
        bid_count_exceeded: true,
        current_bid_count: currentBidInfo.bid_count,
        bid_limit: bidLimit,
        bid_source: bidSource,
        error_message: `Project has too many bids (${currentBidInfo.bid_count}/${bidLimit}). Automatic bidding cancelled.`,
        formatted_text: formatBidText(jobData.ranking.bid_teaser),
        project_url: jobData.project_url || `https://www.freelancer.com/projects/${projectId}`,
        project_id: projectId,
        message: `Bid not submitted - too many competing bids (${currentBidInfo.bid_count}/${bidLimit}) [${bidSource}]`
      });
    }

    console.log(`[Debug] ✅ BID COUNT OK: ${currentBidInfo.bid_count}/${bidLimit} (source: ${bidSource}) - proceeding with submission`);

    // ✅ CRITICAL CHECK: Check if we already have a bid on this project BEFORE submission
    console.log(`[Debug] 🔍 Checking if bid already exists for project ${projectId}...`);
    try {
      const bidCheckResponse = await fetch(`https://www.freelancer.com/api/projects/0.1/bids/?projects[]=${projectId}&bidders[]=${numericUserId}`, {
        method: 'GET',
        headers: {
          'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
          'Content-Type': 'application/json'
        }
      });

      if (bidCheckResponse.ok) {
        const bidCheckData = await bidCheckResponse.json();
        const existingBids = bidCheckData.result?.bids || {};
        
        // Check if we have any bids for this project
        const ourBids = Object.values(existingBids).filter(bid => 
          bid.project_id == projectId && bid.bidder_id == numericUserId
        );

        if (ourBids.length > 0) {
          const existingBid = ourBids[0];
          console.log(`[Debug] 🚫 BID ALREADY EXISTS! Found existing bid:`, {
            bid_id: existingBid.id,
            amount: existingBid.amount,
            period: existingBid.period,
            submitted_time: existingBid.time_submitted,
            status: existingBid.status
          });

          // Return without attempting to submit - bid already exists
          return res.json({
            success: false,
            bid_already_exists: true,
            existing_bid: {
              bid_id: existingBid.id,
              amount: existingBid.amount,
              period: existingBid.period,
              submitted_time: existingBid.time_submitted,
              status: existingBid.status
            },
            message: `Bid already exists for this project. Bid ID: ${existingBid.id}, Amount: $${existingBid.amount}, Period: ${existingBid.period} days`,
            formatted_text: formatBidText(jobData.ranking.bid_teaser),
            project_url: jobData.project_url || `https://www.freelancer.com/projects/${projectId}`,
            project_id: projectId
          });
        } else {
          console.log(`[Debug] ✅ NO EXISTING BID found for project ${projectId} and user ${numericUserId} - proceeding with submission`);
        }
      } else {
        console.warn(`[Debug] ⚠️ Could not check existing bids (API returned ${bidCheckResponse.status}), proceeding with submission anyway`);
      }
    } catch (bidCheckError) {
      console.warn(`[Debug] ⚠️ Error checking existing bids: ${bidCheckError.message}, proceeding with submission anyway`);
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
    
    // Calculate reference price for bidding (average bid or customer price range average)
    let referencePrice = null;
    let referencePriceType = null;
    
    // Try to get average bid first, then fall back to customer price range average
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
    
    // Calculate bid amount as 10% below reference price
    let bidAmount;
    if (referencePrice && referencePrice > 0) {
      bidAmount = Math.ceil(referencePrice * 0.9); // 10% below reference price
      console.log(`[Debug] Bid amount set to 10% below ${referencePriceType}: ${referencePrice} USD * 0.9 = ${bidAmount} USD`);
    } else {
      // Fallback: use AI estimated price or minimum bid amount
      bidAmount = bidTeaser.estimated_price || minimumBidAmount;
      console.log(`[Debug] No reference price available, using fallback: ${bidAmount} USD (AI estimate: ${bidTeaser.estimated_price}, minimum: ${minimumBidAmount})`);
    }
    
    // Ensure bid amount is not below minimum
    if (bidAmount < minimumBidAmount) {
      const originalBidAmount = bidAmount;
      bidAmount = minimumBidAmount;
      console.log(`[Debug] Bid amount adjusted from ${originalBidAmount} to ${bidAmount} (minimum: ${minimumBidAmount})`);
    }
    
    // Calculate maximum allowed bid amount (for safety - should rarely be needed now)
    let maximumAllowedBid = null;
    if (referencePrice && referencePrice > 0) {
      maximumAllowedBid = Math.ceil(referencePrice * 1.8); // 80% above reference price
      console.log(`[Debug] Maximum allowed bid: ${maximumAllowedBid} USD (180% of ${referencePriceType}: ${referencePrice} USD)`);
      
      // Check if bid amount exceeds maximum allowed (should rarely happen with 10% below strategy)
      if (bidAmount > maximumAllowedBid) {
        const originalBidAmount = bidAmount;
        bidAmount = maximumAllowedBid;
        console.log(`[Debug] Bid amount adjusted from ${originalBidAmount} to ${bidAmount} (maximum allowed: ${maximumAllowedBid}, based on ${referencePriceType})`);
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
        
        // Save detailed error to JSON
        const error = {
          message: `Freelancer API error: ${freelancerResponse.status} - ${errorText}`,
          context: 'freelancer_api_error',
          api_status: freelancerResponse.status,
          api_status_text: freelancerResponse.statusText,
          api_response: errorText,
          bid_data: bidData
        };
        await saveErrorToProjectJson(projectId, error, 'freelancer_api_error');
        
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
      
      // Save detailed error to JSON
      const error = {
        message: `API call failed: ${apiError.message}`,
        context: 'api_call_exception',
        error_type: apiError.name || 'Unknown',
        error_stack: apiError.stack,
        bid_data: bidData
      };
      await saveErrorToProjectJson(projectId, error, 'api_call_exception');
      
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

// ========== PROJECTS API ENDPOINTS ==========

// Get all projects
app.get('/api/admin/projects', async (req, res) => {
  try {
    const projects = await getAllProjects();
    res.json(projects);
  } catch (error) {
    console.error('Error getting projects:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get project by ID
app.get('/api/admin/projects/:id', async (req, res) => {
  try {
    const project = await getProjectById(req.params.id);
    if (!project) {
      return res.status(404).json({ error: 'Project not found' });
    }
    res.json(project);
  } catch (error) {
    console.error('Error getting project by id:', error);
    res.status(500).json({ error: error.message });
  }
});

// Create new project
app.post('/api/admin/projects', async (req, res) => {
  try {
    const projectId = await createProject(req.body);
    res.json({ id: projectId, message: 'Project created successfully' });
  } catch (error) {
    console.error('Error creating project:', error);
    res.status(500).json({ error: error.message });
  }
});

// Update project
app.put('/api/admin/projects/:id', async (req, res) => {
  try {
    await updateProject(req.params.id, req.body);
    res.json({ message: 'Project updated successfully' });
  } catch (error) {
    console.error('Error updating project:', error);
    res.status(500).json({ error: error.message });
  }
});

// Delete project
app.delete('/api/admin/projects/:id', async (req, res) => {
  try {
    await deleteProject(req.params.id);
    res.json({ message: 'Project deleted successfully' });
  } catch (error) {
    console.error('Error deleting project:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add file to project
app.post('/api/admin/projects/:projectId/files', async (req, res) => {
  try {
    const { projectId } = req.params;
    const fileId = await addProjectFile(projectId, req.body);
    res.json({ id: fileId, message: 'File added to project successfully' });
  } catch (error) {
    console.error('Error adding file to project:', error);
    res.status(500).json({ error: error.message });
  }
});

// Update project file
app.put('/api/admin/projects/files/:fileId', async (req, res) => {
  try {
    const { fileId } = req.params;
    await updateProjectFile(fileId, req.body);
    res.json({ message: 'File updated successfully' });
  } catch (error) {
    console.error('Error updating project file:', error);
    res.status(500).json({ error: error.message });
  }
});

// Delete project file
app.delete('/api/admin/projects/files/:fileId', async (req, res) => {
  try {
    const { fileId } = req.params;
    await deleteProjectFile(fileId);
    res.json({ message: 'File deleted successfully' });
  } catch (error) {
    console.error('Error deleting project file:', error);
    res.status(500).json({ error: error.message });
  }
});

// Link job to project
app.post('/api/admin/projects/:projectId/link-job', async (req, res) => {
  try {
    const { projectId } = req.params;
    const { jobId } = req.body;
    await linkJobToProject(jobId, projectId);
    res.json({ message: 'Job linked to project successfully' });
  } catch (error) {
    console.error('Error linking job to project:', error);
    res.status(500).json({ error: error.message });
  }
});

// Create project from job
app.post('/api/admin/projects/from-job', async (req, res) => {
  try {
    const projectId = await createProjectFromJob(req.body);
    res.json({ id: projectId, message: 'Project created from job successfully' });
  } catch (error) {
    console.error('Error creating project from job:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add tag to project
app.post('/api/admin/projects/:projectId/tags', async (req, res) => {
  try {
    const { projectId } = req.params;
    const { tag_name } = req.body;
    const result = await addTagToProject(projectId, tag_name);
    res.json(result);
  } catch (error) {
    console.error('Error adding tag to project:', error);
    res.status(500).json({ error: error.message });
  }
});

// Remove tag from project
app.delete('/api/admin/projects/:projectId/tags/:tagId', async (req, res) => {
  try {
    const { projectId, tagId } = req.params;
    await removeProjectTag(projectId, tagId);
    res.json({ message: 'Tag removed from project successfully' });
  } catch (error) {
    console.error('Error removing tag from project:', error);
    res.status(500).json({ error: error.message });
  }
});

// ========== CONTACTS API ENDPOINTS ==========

// Get all contacts
app.get('/api/admin/contacts', async (req, res) => {
  try {
    const contacts = await getAllContacts();
    res.json(contacts);
  } catch (error) {
    console.error('Error fetching contacts:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get contact by ID
app.get('/api/admin/contacts/:id', async (req, res) => {
  try {
    const contact = await getContactById(req.params.id);
    if (!contact) {
      return res.status(404).json({ error: 'Contact not found' });
    }
    res.json(contact);
  } catch (error) {
    console.error('Error fetching contact:', error);
    res.status(500).json({ error: error.message });
  }
});

// Create new contact
app.post('/api/admin/contacts', async (req, res) => {
  try {
    const contactId = await createContact(req.body);
    res.json({ id: contactId, message: 'Contact created successfully' });
  } catch (error) {
    console.error('Error creating contact:', error);
    res.status(500).json({ error: error.message });
  }
});

// Update contact
app.put('/api/admin/contacts/:id', async (req, res) => {
  try {
    await updateContact(req.params.id, req.body);
    res.json({ message: 'Contact updated successfully' });
  } catch (error) {
    console.error('Error updating contact:', error);
    res.status(500).json({ error: error.message });
  }
});

// Delete contact
app.delete('/api/admin/contacts/:id', async (req, res) => {
  try {
    await deleteContact(req.params.id);
    res.json({ message: 'Contact deleted successfully' });
  } catch (error) {
    console.error('Error deleting contact:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add phone number to contact
app.post('/api/admin/contacts/:id/phone', async (req, res) => {
  try {
    const phoneId = await addPhoneNumber(req.params.id, req.body);
    res.json({ id: phoneId, message: 'Phone number added successfully' });
  } catch (error) {
    console.error('Error adding phone number:', error);
    res.status(500).json({ error: error.message });
  }
});

// Update phone number
app.put('/api/admin/contacts/phone/:phoneId', async (req, res) => {
  try {
    await updatePhoneNumber(req.params.phoneId, req.body);
    res.json({ message: 'Phone number updated successfully' });
  } catch (error) {
    console.error('Error updating phone number:', error);
    res.status(500).json({ error: error.message });
  }
});

// Delete phone number
app.delete('/api/admin/contacts/phone/:phoneId', async (req, res) => {
  try {
    await deletePhoneNumber(req.params.phoneId);
    res.json({ message: 'Phone number deleted successfully' });
  } catch (error) {
    console.error('Error deleting phone number:', error);
    res.status(500).json({ error: error.message });
  }
});

// ========== CUSTOMERS API ENDPOINTS ==========

// Get all customers
app.get('/api/admin/customers', async (req, res) => {
  try {
    const customers = await getAllCustomers();
    res.json(customers);
  } catch (error) {
    console.error('Error fetching customers:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get customer by ID
app.get('/api/admin/customers/:id', async (req, res) => {
  try {
    const customer = await getCustomerById(req.params.id);
    if (!customer) {
      return res.status(404).json({ error: 'Customer not found' });
    }
    res.json(customer);
  } catch (error) {
    console.error('Error fetching customer:', error);
    res.status(500).json({ error: error.message });
  }
});

// Create new customer
app.post('/api/admin/customers', async (req, res) => {
  try {
    const customerId = await createCustomer(req.body);
    res.json({ id: customerId, message: 'Customer created successfully' });
  } catch (error) {
    console.error('Error creating customer:', error);
    res.status(500).json({ error: error.message });
  }
});

// Update customer
app.put('/api/admin/customers/:id', async (req, res) => {
  try {
    await updateCustomer(req.params.id, req.body);
    res.json({ message: 'Customer updated successfully' });
  } catch (error) {
    console.error('Error updating customer:', error);
    res.status(500).json({ error: error.message });
  }
});

// Delete customer
app.delete('/api/admin/customers/:id', async (req, res) => {
  try {
    await deleteCustomer(req.params.id);
    res.json({ message: 'Customer deleted successfully' });
  } catch (error) {
    console.error('Error deleting customer:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get customer projects
app.get('/api/admin/customers/:id/projects', async (req, res) => {
  try {
    const projects = await getCustomerProjects(req.params.id);
    res.json(projects);
  } catch (error) {
    console.error('Error fetching customer projects:', error);
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

        // Check if the response is rate limited
        if (response.rateLimited) {
            console.log(`[Bid Check] ⏳ Skipping batch due to rate limiting`);
            return; // Skip this batch
        }

        // Check if the response is successful
        if (!response.ok) {
            throw new Error(`API call failed with status ${response.status}: ${response.statusText}`);
        }

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
            
            // Add longer delay between batches for better rate limiting
            const delay = Math.floor(Math.random() * 3000) + 10000; // 10-13 seconds between batches
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

// Start bid monitoring - only if enabled
if (BID_CHECK_ENABLED) {
    console.log(`[Bid Check] 🚀 Starting bid monitoring service (interval: ${BID_CHECK_INTERVAL/1000}s)`);

    // Run immediately on startup
    updateBidCounts().catch(error => {
        console.error('[Bid Check] ❌ Initial check failed:', error);
    });

    // Then set up the interval - no routine logging
    var bidCheckInterval = setInterval(async () => {
        try {
            await updateBidCounts();
        } catch (error) {
            console.error('[Bid Check] ❌ Interval check failed:', error);
        }
    }, BID_CHECK_INTERVAL);
} else {
    console.log(`[Bid Check] 🚫 Bid monitoring service DISABLED by BID_CHECK_ENABLED constant`);
    bidCheckInterval = null;
}

// Cleanup on server shutdown
process.on('SIGTERM', () => {
    if (BID_CHECK_ENABLED && bidCheckInterval) {
        console.log('[Bid Check] 🛑 Shutting down bid monitoring service');
        clearInterval(bidCheckInterval);
    }
});

process.on('SIGINT', () => {
    if (BID_CHECK_ENABLED && bidCheckInterval) {
        console.log('[Bid Check] 🛑 Shutting down bid monitoring service');
        clearInterval(bidCheckInterval);
    }
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
    
    // Calculate reference price for bidding (average bid or customer price range average)
    let referencePrice = null;
    let referencePriceType = null;
    
    // Try to get average bid first, then fall back to customer price range average
    if (jobData.project_details?.bid_stats?.bid_avg && jobData.project_details.bid_stats.bid_avg > 0) {
      referencePrice = jobData.project_details.bid_stats.bid_avg;
      referencePriceType = 'average bid';
      
      // Convert to USD if needed
      if (projectCurrency && projectCurrency.code !== 'USD' && projectCurrency.exchange_rate) {
        referencePrice = Math.ceil(jobData.project_details.bid_stats.bid_avg / projectCurrency.exchange_rate);
        console.log(`[Test] Average bid currency conversion: ${jobData.project_details.bid_stats.bid_avg} ${projectCurrency.code} → ${referencePrice} USD`);
      }
    } else if (projectBudget && projectBudget.minimum && projectBudget.maximum && projectBudget.minimum > 0 && projectBudget.maximum > 0) {
      // When average bid is not available, use the average of the customer's price range
      const budgetAverage = (projectBudget.minimum + projectBudget.maximum) / 2;
      referencePrice = budgetAverage;
      referencePriceType = 'customer price range average';
      
      // Convert to USD if needed
      if (projectCurrency && projectCurrency.code !== 'USD' && projectCurrency.exchange_rate) {
        referencePrice = Math.ceil(budgetAverage / projectCurrency.exchange_rate);
        console.log(`[Test] Customer price range average currency conversion: ${budgetAverage} ${projectCurrency.code} → ${referencePrice} USD`);
      }
      
      console.log(`[Test] Using customer price range average: (${projectBudget.minimum} + ${projectBudget.maximum}) / 2 = ${budgetAverage} ${projectCurrency?.code || 'USD'}`);
    }
    
    // Calculate bid amount as 10% below reference price
    let bidAmount;
    if (referencePrice && referencePrice > 0) {
      bidAmount = Math.ceil(referencePrice * 0.9); // 10% below reference price
      console.log(`[Test] Bid amount set to 10% below ${referencePriceType}: ${referencePrice} USD * 0.9 = ${bidAmount} USD`);
    } else {
      // Fallback: use AI estimated price or minimum bid amount
      bidAmount = bidTeaser.estimated_price || minimumBidAmount;
      console.log(`[Test] No reference price available, using fallback: ${bidAmount} USD (AI estimate: ${bidTeaser.estimated_price}, minimum: ${minimumBidAmount})`);
    }
    
    // TEST: Minimum price validation
    const originalBidAmount = bidAmount;
    if (bidAmount < minimumBidAmount) {
      bidAmount = minimumBidAmount;
      console.log(`[Test] Bid amount adjusted from ${originalBidAmount} to ${bidAmount} (minimum: ${minimumBidAmount})`);
    }
    
    // TEST: Maximum price validation (for safety - should rarely be needed now)
    let maximumAllowedBid = null;
    if (referencePrice && referencePrice > 0) {
      maximumAllowedBid = Math.ceil(referencePrice * 1.8); // 80% above reference price
      console.log(`[Test] Maximum allowed bid: ${maximumAllowedBid} USD (180% of ${referencePriceType}: ${referencePrice} USD)`);
      
      // Check if bid amount exceeds maximum allowed (should rarely happen with 10% below strategy)
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

// Add new endpoint for rate limit logs
app.get('/api/rate-limit-logs', (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 50;
    
    // Import rate limit functions (Node.js version)
    const { getRateLimitLogs, analyzeRateLimitPatterns, getRateLimitStatus } = require('./rateLimitManager');
    
    const logs = getRateLimitLogs(limit);
    const patterns = analyzeRateLimitPatterns();
    const status = getRateLimitStatus();
    
    res.json({ 
      logs,
      patterns,
      status,
      total_logs: logs.length 
    });
  } catch (error) {
    console.error('Error fetching rate limit logs:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add endpoint for manual rate limit management
app.post('/api/rate-limit/clear', (req, res) => {
  try {
    const { clearRateLimitTimeout } = require('./rateLimitManager');
    clearRateLimitTimeout('manual-clear-from-frontend');
    res.json({ success: true, message: 'Rate limit cleared manually' });
  } catch (error) {
    console.error('Error clearing rate limit:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/rate-limit/set', (req, res) => {
  try {
    const { setRateLimitTimeout } = require('./rateLimitManager');
    setRateLimitTimeout('manual-set-from-frontend');
    res.json({ success: true, message: 'Rate limit set manually for 30 minutes' });
  } catch (error) {
    console.error('Error setting rate limit:', error);
    res.status(500).json({ error: error.message });
  }
});

// Auto-bid logging endpoint
app.post('/api/auto-bid-log', async (req, res) => {
  try {
    const { timestamp, message, type, source } = req.body;
    
    // Create log entry with full timestamp
    const logEntry = {
      timestamp: timestamp || new Date().toISOString(),
      message: message || 'No message',
      type: type || 'info',
      source: source || 'unknown'
    };
    
    // Log to console with appropriate level
    const logLevel = type === 'error' ? 'error' : type === 'warning' ? 'warn' : 'log';
    console[logLevel](`[AutoBid-${source}] ${message}`);
    
    // Write to auto-bid log file
    const logFilePath = path.join(__dirname, '..', '..', 'api_logs', 'auto_bidding.log');
    const logLine = `${timestamp} | AUTO_BID | ${type.toUpperCase()} | source=${source} | ${message}\n`;
    
    try {
      await fs.appendFile(logFilePath, logLine);
    } catch (fileError) {
      console.warn('[AutoBid] Failed to write to log file:', fileError);
    }
    
    // Store in memory for potential API access
    autoBiddingLogs.push(logEntry);
    
    // Keep only last 200 logs in memory
    if (autoBiddingLogs.length > 200) {
      autoBiddingLogs = autoBiddingLogs.slice(-200);
    }
    
    res.json({ success: true, message: 'Auto-bid log entry recorded' });
  } catch (error) {
    console.error('Error recording auto-bid log:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get auto-bid logs endpoint
app.get('/api/auto-bid-logs', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 100;
    const includeFile = req.query.includeFile !== 'false'; // Default to true
    
    let allLogs = [];
    
    // Load logs from file if requested
    if (includeFile) {
      try {
        const logFilePath = path.join(__dirname, '..', '..', 'api_logs', 'auto_bidding.log');
        const fileContent = await fs.readFile(logFilePath, 'utf8');
        const fileLines = fileContent.trim().split('\n').filter(line => line.trim());
        
        const fileLogs = fileLines.map((line, index) => {
          try {
            // Parse log line format: TIMESTAMP | AUTO_BID | TYPE | source=SOURCE | MESSAGE
            const parts = line.split(' | ');
            if (parts.length >= 4) {
              const timestamp = parts[0];
              const type = parts[2].toLowerCase();
              const sourcePart = parts[3];
              const message = parts.slice(4).join(' | ');
              
              // Extract source from "source=SOURCE" format
              const sourceMatch = sourcePart.match(/source=(.+)/);
              const source = sourceMatch ? sourceMatch[1] : 'unknown';
              
              return {
                id: `file-${timestamp}-${index}`,
                timestamp: new Date(timestamp).toLocaleTimeString(),
                fullTimestamp: timestamp,
                message: message,
                type: type,
                source: source,
                isNew: isLogNew(timestamp)
              };
            }
          } catch (parseError) {
            console.warn('[AutoBid] Failed to parse log line:', line, parseError);
          }
          return null;
        }).filter(log => log !== null);
        
        allLogs = [...allLogs, ...fileLogs];
      } catch (fileError) {
        console.warn('[AutoBid] Failed to read log file:', fileError);
      }
    }
    
    // Add memory logs (avoiding duplicates)
    const memoryLogs = autoBiddingLogs.map(log => ({
      ...log,
      isNew: isLogNew(log.timestamp)
    }));
    
    // Merge logs and remove duplicates based on timestamp + message
    const logMap = new Map();
    [...allLogs, ...memoryLogs].forEach(log => {
      const key = `${log.fullTimestamp}-${log.message}`;
      if (!logMap.has(key)) {
        logMap.set(key, log);
      }
    });
    
    // Sort by timestamp (newest first) and limit
    const sortedLogs = Array.from(logMap.values())
      .sort((a, b) => new Date(b.fullTimestamp) - new Date(a.fullTimestamp))
      .slice(0, limit);
    
    res.json({ logs: sortedLogs, count: sortedLogs.length, fileLoaded: includeFile });
  } catch (error) {
    console.error('Error getting auto-bid logs:', error);
    res.status(500).json({ error: error.message });
  }
});

// Helper function to check if log is new (within last 30 seconds)
function isLogNew(timestamp) {
  try {
    const logTime = new Date(timestamp).getTime();
    const now = Date.now();
    const thirtySecondsAgo = now - (30 * 1000);
    return logTime > thirtySecondsAgo;
  } catch (error) {
    return false;
  }
}

// Start heartbeat for vue-frontend server
let heartbeatInterval;
function startHeartbeat() {
  // Send initial heartbeat
  sendHeartbeat('vue-frontend', {
    port: PORT,
    endpoint_count: Object.keys(app._router.stack).length
  });
  
  // Send heartbeat every 30 seconds
  heartbeatInterval = setInterval(() => {
    const { getRateLimitStatus } = require('./rateLimitManager');
    const rateLimitStatus = getRateLimitStatus();
    
    sendHeartbeat('vue-frontend', {
      port: PORT,
      uptime: process.uptime(),
      memory_usage: process.memoryUsage(),
      active_requests: Object.keys(require('cluster').workers || {}).length,
      rate_limit_status: rateLimitStatus.isRateLimited ? 'active' : 'clear',
      rate_limit_remaining: rateLimitStatus.remainingSeconds || 0
    });
  }, 30000);
}

// Cleanup on shutdown
process.on('SIGTERM', () => {
  console.log('Vue-Frontend server shutting down...');
  if (heartbeatInterval) clearInterval(heartbeatInterval);
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('Vue-Frontend server shutting down...');
  if (heartbeatInterval) clearInterval(heartbeatInterval);
  process.exit(0);
});

// Post question to project using Selenium automation (ASYNC - Fire and Forget)
app.post('/api/post-question/:projectId', async (req, res) => {
  const { projectId } = req.params;
  
  try {
    // 🚫 CRITICAL: Check if question is already being posted for this project
    if (questionPostingLocks.has(projectId)) {
      console.log(`[PostQuestion] ⚠️ DUPLICATE PROTECTION: Question already being posted for project ${projectId} - ABORTING`);
      logAutoBiddingServer(`DUPLICATE PROTECTION: Question already being posted for project ${projectId} - ABORTING`, 'warning', projectId);
      
      return res.status(409).json({
        success: false,
        error: 'Question posting already in progress for this project',
        projectId: projectId,
        status: 'duplicate_prevented'
      });
    }
    
    // 🔒 LOCK: Mark project as having question being posted
    questionPostingLocks.add(projectId);
    console.log(`[PostQuestion] 🔒 LOCKED: Project ${projectId} marked as posting question. Active locks: ${questionPostingLocks.size}`);
    logAutoBiddingServer(`Question posting started for project ${projectId}. Active locks: ${questionPostingLocks.size}`, 'info', projectId);
    
    console.log(`[PostQuestion] Starting headless question posting for project ${projectId}`);
    
    // Import required modules FIRST
    const { spawn } = require('child_process');
    const path = require('path');
    const fs = require('fs');
    
    // Check if we have an authenticated session from websocket-reader
    const authSessionPath = path.join(__dirname, '..', '..', 'freelancer_auth_session.json');
    let useHeadlessWithSession = false;
    
    try {
      if (fs.existsSync(authSessionPath)) {
        const authSession = JSON.parse(fs.readFileSync(authSessionPath, 'utf8'));
        console.log(`[PostQuestion] ✅ Found auth session from websocket-reader: ${authSession.profile_dir}`);
        useHeadlessWithSession = true;
      } else {
        console.log(`[PostQuestion] ⚠️ No auth session found - add_question.py will handle login`);
      }
    } catch (error) {
      console.log(`[PostQuestion] ⚠️ Error reading auth session: ${error.message}`);
    }
    
    // Choose script based on session availability
    let scriptPath, scriptArgs;
    
    if (useHeadlessWithSession) {
      // Use new headless-only version
      scriptPath = path.join(__dirname, '..', '..', 'add_question_headless.py');
      scriptArgs = [scriptPath, projectId];
      console.log(`[PostQuestion] 🤖 Using headless-only script with websocket-reader session`);
    } else {
      // Fallback to hybrid version
      scriptPath = path.join(__dirname, '..', '..', 'add_question.py');
      scriptArgs = [scriptPath, projectId];
      console.log(`[PostQuestion] 🔄 Using hybrid script (will handle login if needed)`);
    }
    
    // Execute the Python script with project ID (ASYNC - don't wait for result)
    const pythonProcess = spawn('python3', scriptArgs, {
      cwd: path.join(__dirname, '..', '..'),
      stdio: 'pipe',
      detached: true // Allow process to run independently
    });
    
    let processCompleted = false;
    
    // Log output but don't wait for completion
    pythonProcess.stdout.on('data', (data) => {
      console.log(`[PostQuestion-${projectId}] Stdout: ${data.toString().trim()}`);
    });
    
    pythonProcess.stderr.on('data', (data) => {
      console.log(`[PostQuestion-${projectId}] Stderr: ${data.toString().trim()}`);
    });
    
    pythonProcess.on('close', (code) => {
      processCompleted = true;
      console.log(`[PostQuestion-${projectId}] Python script finished with code ${code}`);
      
      // 🔓 UNLOCK: Remove project from question posting locks
      questionPostingLocks.delete(projectId);
      console.log(`[PostQuestion] 🔓 UNLOCKED: Project ${projectId} removed from question posting. Active locks: ${questionPostingLocks.size}`);
      
      if (code === 0) {
        console.log(`[PostQuestion-${projectId}] ✅ Question posted successfully`);
        logAutoBiddingServer(`Question posted successfully for project ${projectId}. Active locks: ${questionPostingLocks.size}`, 'success', projectId);
      } else {
        console.log(`[PostQuestion-${projectId}] ❌ Question posting failed with code ${code}`);
        logAutoBiddingServer(`Question posting failed for project ${projectId}: code ${code}. Active locks: ${questionPostingLocks.size}`, 'error', projectId);
      }
    });
    
    pythonProcess.on('error', (error) => {
      processCompleted = true;
      
      // 🔓 UNLOCK: Remove project from question posting locks on error
      questionPostingLocks.delete(projectId);
      console.log(`[PostQuestion] 🔓 UNLOCKED (ERROR): Project ${projectId} removed from question posting. Active locks: ${questionPostingLocks.size}`);
      
      console.error(`[PostQuestion-${projectId}] Error spawning Python process:`, error);
      logAutoBiddingServer(`Question posting error for project ${projectId}: ${error.message}. Active locks: ${questionPostingLocks.size}`, 'error', projectId);
    });
    
    // Optional: Set timeout to kill long-running processes (but don't wait for it)
    setTimeout(() => {
      if (!processCompleted) {
        console.log(`[PostQuestion-${projectId}] ⏰ Killing long-running process after 60 seconds`);
        try {
          pythonProcess.kill('SIGTERM');
          
          // 🔓 UNLOCK: Remove project from question posting locks on timeout
          questionPostingLocks.delete(projectId);
          console.log(`[PostQuestion] 🔓 UNLOCKED (TIMEOUT): Project ${projectId} removed from question posting. Active locks: ${questionPostingLocks.size}`);
          
          logAutoBiddingServer(`Question posting timeout for project ${projectId} (killed after 60s). Active locks: ${questionPostingLocks.size}`, 'warning', projectId);
        } catch (killError) {
          console.error(`[PostQuestion-${projectId}] Error killing process:`, killError);
        }
      }
    }, 60000); // 60 second timeout (longer since we're not waiting)
    
    // Immediately respond that the process has been started
    res.json({
      success: true,
      message: `Question posting started asynchronously for project ${projectId}`,
      status: 'started',
      projectId: projectId,
      timestamp: new Date().toISOString()
    });
    
    // Log that we've started the async process
    logAutoBiddingServer(`Question posting started asynchronously for project ${projectId}`, 'info', projectId);
    
  } catch (error) {
    // 🔓 UNLOCK: Remove project from question posting locks on main error
    questionPostingLocks.delete(projectId);
    console.log(`[PostQuestion] 🔓 UNLOCKED (MAIN ERROR): Project ${projectId} removed from question posting. Active locks: ${questionPostingLocks.size}`);
    
    console.error(`[PostQuestion] Error processing request for project ${projectId}:`, error);
    logAutoBiddingServer(`Question posting main error for project ${projectId}: ${error.message}. Active locks: ${questionPostingLocks.size}`, 'error', projectId);
    
    res.status(500).json({
      success: false,
      error: error.message,
      projectId: projectId
    });
  }
});

// Question posting locks management endpoints
app.get('/api/question-posting-locks/status', (req, res) => {
  try {
    res.json({
      success: true,
      activeLocks: Array.from(questionPostingLocks),
      lockCount: questionPostingLocks.size,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error getting question posting locks status:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/question-posting-locks/clear', (req, res) => {
  try {
    const clearedCount = questionPostingLocks.size;
    const clearedLocks = Array.from(questionPostingLocks);
    questionPostingLocks.clear();
    
    console.log(`[PostQuestion] 🧹 MANUALLY CLEARED: All ${clearedCount} question posting locks cleared`);
    logAutoBiddingServer(`Manually cleared ${clearedCount} question posting locks: ${clearedLocks.join(', ')}`, 'warning');
    
    res.json({
      success: true,
      message: `Cleared ${clearedCount} question posting locks`,
      clearedLocks: clearedLocks,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error clearing question posting locks:', error);
    res.status(500).json({ error: error.message });
  }
});

// Remove static file serving - API server only
const PORT = process.env.PORT || 5002;
app.listen(PORT, () => {
  console.log(`API Server running on port ${PORT}`);
  startHeartbeat();
}); 