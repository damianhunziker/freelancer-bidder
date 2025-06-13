const path = require('path');
const fs = require('fs');

// Read the main config file
const configPath = path.resolve(__dirname, '../config.py');
let config = {};

try {
  if (fs.existsSync(configPath)) {
    const configContent = fs.readFileSync(configPath, 'utf8');
    
    // Extract AI provider configuration
    const aiProviderMatch = configContent.match(/AI_PROVIDER\s*=\s*['"]([^'"]+)['"]/);
    const deepseekApiBaseMatch = configContent.match(/DEEPSEEK_API_BASE\s*=\s*['"]([^'"]+)['"]/);
    const deepseekApiKeyMatch = configContent.match(/DEEPSEEK_API_KEY\s*=\s*['"]([^'"]+)['"]/);
    const deepseekModelMatch = configContent.match(/DEEPSEEK_MODEL\s*=\s*['"]([^'"]+)['"]/);
    
    // Extract Freelancer API configuration
    const freelancerApiKeyMatch = configContent.match(/FREELANCER_API_KEY\s*=\s*['"]([^'"]+)['"]/);
    const freelancerUserIdMatch = configContent.match(/FREELANCER_USER_ID\s*=\s*['"]([^'"]+)['"]/);
    const flApiBaseUrlMatch = configContent.match(/FL_API_BASE_URL\s*=\s*['"]([^'"]+)['"]/);
    
    config = {
      AI_PROVIDER: aiProviderMatch ? aiProviderMatch[1] : 'chatgpt',
      DEEPSEEK_API_BASE: deepseekApiBaseMatch ? deepseekApiBaseMatch[1] : null,
      DEEPSEEK_API_KEY: deepseekApiKeyMatch ? deepseekApiKeyMatch[1] : null,
      DEEPSEEK_MODEL: deepseekModelMatch ? deepseekModelMatch[1] : 'deepseek-chat',
      FREELANCER_API_KEY: freelancerApiKeyMatch ? freelancerApiKeyMatch[1] : null,
      FREELANCER_USER_ID: freelancerUserIdMatch ? freelancerUserIdMatch[1] : null,
      FL_API_BASE_URL: flApiBaseUrlMatch ? flApiBaseUrlMatch[1] : null
    };
    
    console.log('Successfully loaded AI configuration from:', configPath);
  } else {
    console.warn('Config file not found at:', configPath);
  }
} catch (error) {
  console.error('Error loading configuration:', error);
}

// Export the configuration with default values
module.exports = {
  FRONTEND_PORT: config.FRONTEND_PORT || 8080,
  FRONTEND_API_URL: config.FRONTEND_API_URL || 'http://localhost:5002',
  AI_PROVIDER: config.AI_PROVIDER || 'chatgpt',
  DEEPSEEK_API_BASE: config.DEEPSEEK_API_BASE,
  DEEPSEEK_API_KEY: config.DEEPSEEK_API_KEY,
  DEEPSEEK_MODEL: config.DEEPSEEK_MODEL || 'deepseek-chat',
  FREELANCER_API_KEY: config.FREELANCER_API_KEY,
  FREELANCER_USER_ID: config.FREELANCER_USER_ID,
  FL_API_BASE_URL: config.FL_API_BASE_URL || 'https://www.freelancer.com/api'
}; 