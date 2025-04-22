const path = require('path');
const fs = require('fs');

// Read the main config file
const configPath = path.resolve(__dirname, '../config.js');
let config = {};

try {
  if (fs.existsSync(configPath)) {
    config = require(configPath);
    console.log('Successfully loaded configuration from:', configPath);
  } else {
    console.warn('Config file not found at:', configPath);
  }
} catch (error) {
  console.error('Error loading configuration:', error);
}

// Export the configuration with default values
module.exports = {
  FRONTEND_PORT: config.FRONTEND_PORT || 8080,
  FRONTEND_API_URL: config.FRONTEND_API_URL || 'http://localhost:5002'
}; 