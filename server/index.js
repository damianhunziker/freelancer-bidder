const express = require('express');
const fs = require('fs').promises;
const path = require('path');
const app = express();

// Middleware für JSON-Parsing
app.use(express.json());

// Enable CORS for all routes
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
  next();
});

// Endpoint to list all projects from the jobs folder
app.get('/jobs', async (req, res) => {
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

// Endpoint to get a specific job file
app.get('/jobs/:filename', async (req, res) => {
  try {
    const jobsDir = path.join(__dirname, '..', 'jobs');
    const filePath = path.join(jobsDir, req.params.filename);
    
    // Validate filename to prevent directory traversal
    if (!req.params.filename.startsWith('job_') || !req.params.filename.endsWith('.json')) {
      return res.status(400).json({ error: 'Invalid filename' });
    }
    
    const content = await fs.readFile(filePath, 'utf8');
    res.json(JSON.parse(content));
  } catch (error) {
    console.error('Error reading job file:', error);
    res.status(500).json({ error: error.message });
  }
});

const PORT = 5002;
app.listen(PORT, () => {
  console.log(`Server läuft auf Port ${PORT}`);
}); 