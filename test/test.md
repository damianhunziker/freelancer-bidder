# Test Documentation - Freelancer Bidder System

## Overview
This document outlines all testing procedures, workflows, and validation steps for the Freelancer Bidder System.

## System Components

### Core Scripts
- `bidder.py` - Main bidding system with AI ranking and automated bidding
- `add.py` - Single project analysis and evaluation
- `get_skills.py` - Skills data fetching and caching system
- `freelancer-websocket-reader.py` - Real-time project monitoring via WebSocket

### Frontend System
- `vue-frontend/` - Vue.js web interface for project management and bidding
- `vue-frontend/server/index.js` - Node.js backend API server

## Testing Procedures

### 1. Configuration Testing

#### Test Config Files
```bash
# Verify config.py exists and has required settings
python -c "import config; print('✅ Config loaded successfully')"

# Check API keys are set
python -c "import config; assert config.FREELANCER_API_KEY, 'API key missing'"
```

#### Required Config Variables
- `FREELANCER_API_KEY` - Freelancer.com API authentication
- `OPENAI_API_KEY` or `DEEPSEEK_API_KEY` - AI text generation
- `FREELANCER_USER_ID` - User ID for bidding
- `AI_PROVIDER` - 'openai' or 'deepseek'

### 2. Skills System Testing

#### Test Skills Update
```bash
# Test skills fetching
python get_skills.py

# Verify skills.json was created
ls -la skills/skills.json

# Test skills loading in bidder
python -c "from bidder import get_our_skills; print(f'Loaded {len(get_our_skills())} skills')"
```

#### Expected Results
- Skills file created in `skills/skills.json`
- Timestamp file `.skills_update_timestamp` updated
- Skills loaded successfully in bidder system

### 3. Single Project Analysis Testing

#### Test add.py with Project ID
```bash
# Test with a real project ID (replace with actual ID)
python add.py 123456789

# Expected output:
# - Project details fetched
# - User reputation analyzed
# - Project scored and evaluated
# - Results saved to jobs/ directory
```

#### Validation Steps
- Check project data is fetched correctly
- Verify user reputation is retrieved
- Confirm scoring algorithm works
- Validate JSON output format

### 4. Main Bidder System Testing

#### Test Different Profiles
```bash
# Test with default profile
python bidder.py

# Test specific profiles
python bidder.py --profile broad_recent
python bidder.py --profile high_paying_past
python bidder.py --profile german_recent
```

#### Profile Testing Matrix
| Profile | Search Query | Project Types | Min Fixed | Min Hourly | Country Mode |
|---------|-------------|---------------|-----------|------------|--------------|
| default | '' | fixed,hourly | 0 | 0 | y |
| broad_recent | 'payment,chatgpt,api...' | fixed,hourly | 60 | 10 | y |
| high_paying_past | '' | fixed,hourly | 500 | 20 | y |
| german_recent | '' | fixed,hourly | 50 | 10 | g |

### 5. WebSocket Monitoring Testing

#### Test Freelancer WebSocket Reader
```bash
# Start WebSocket monitoring
python freelancer-websocket-reader.py

# Expected behavior:
# - Opens browser for manual login
# - Monitors WebSocket streams
# - Extracts job IDs automatically
# - Executes add.py for new projects
# - Runs continuously until Ctrl+C
```

#### Validation Points
- Browser opens correctly
- WebSocket connection established
- Job IDs extracted from streams
- add.py executed for each new job
- No duplicate processing

### 6. Frontend System Testing

#### Start Frontend Development Server
```bash
cd vue-frontend
npm install
npm run serve

# Backend API server
node server/index.js
```

#### Frontend Test Cases

##### Project List Display
- [ ] Projects load correctly from jobs/ directory
- [ ] Project details display properly
- [ ] Ranking scores show with color coding
- [ ] Filter and search functionality works

##### Bid Text Generation
- [ ] Generate bid text button works
- [ ] AI text generation completes successfully
- [ ] Generated text displays in interface
- [ ] Text can be copied to clipboard

##### Automatic Bidding
- [ ] Auto-bid toggle functions
- [ ] Projects are processed automatically
- [ ] Bid submission works correctly
- [ ] Error handling displays properly

### 7. API Integration Testing

#### Freelancer API Tests
```bash
# Test API connectivity
python -c "
import requests
import config
response = requests.get(
    f'{config.FL_API_BASE_URL}/projects/0.1/projects/active',
    headers={'Freelancer-OAuth-V1': config.FREELANCER_API_KEY}
)
print(f'API Status: {response.status_code}')
"
```

#### AI API Tests
```bash
# Test OpenAI API
python -c "
import openai
import config
client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
response = client.chat.completions.create(
    model='gpt-3.5-turbo',
    messages=[{'role': 'user', 'content': 'Test'}],
    max_tokens=10
)
print('✅ OpenAI API working')
"

# Test DeepSeek API
python -c "
import requests
import config
response = requests.post(
    'https://api.deepseek.com/v1/chat/completions',
    headers={'Authorization': f'Bearer {config.DEEPSEEK_API_KEY}'},
    json={
        'model': 'deepseek-chat',
        'messages': [{'role': 'user', 'content': 'Test'}],
        'max_tokens': 10
    }
)
print(f'DeepSeek API Status: {response.status_code}')
"
```

### 8. Cache System Testing

#### Test Cache Functionality
```bash
# Clear cache
python -c "
from bidder import FileCache
cache = FileCache()
cache.clear()
print('✅ Cache cleared')
"

# Test cache operations
python -c "
from bidder import FileCache
cache = FileCache()
cache.set('test', 'key1', {'data': 'test'})
result = cache.get('test', 'key1')
assert result['data'] == 'test'
print('✅ Cache operations working')
"
```

### 9. Currency Conversion Testing

#### Test Currency Manager
```bash
python -c "
from bidder import CurrencyManager
cm = CurrencyManager()
usd_amount = cm.convert_to_usd(100, 'EUR')
print(f'100 EUR = {usd_amount} USD')
assert usd_amount is not None
print('✅ Currency conversion working')
"
```

### 10. Error Handling Testing

#### Test Invalid Inputs
```bash
# Test with invalid project ID
python add.py invalid_id

# Test with missing config
mv config.py config.py.backup
python bidder.py  # Should show config error
mv config.py.backup config.py
```

#### Test Network Failures
- Disconnect internet and test API calls
- Test rate limiting scenarios
- Verify graceful degradation

### 11. Performance Testing

#### Load Testing
```bash
# Test with multiple projects
python -c "
from bidder import get_active_projects
projects = get_active_projects(limit=50)
print(f'Fetched {len(projects.get(\"result\", {}).get(\"projects\", []))} projects')
"
```

#### Memory Usage
```bash
# Monitor memory usage during operation
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

### 12. Integration Testing

#### End-to-End Workflow Test
1. Start with clean cache and no existing jobs
2. Run `python get_skills.py` to update skills
3. Run `python bidder.py` with a test profile
4. Verify projects are fetched, analyzed, and scored
5. Check that high-scoring projects are processed
6. Validate JSON files are created correctly
7. Test frontend displays projects correctly
8. Test bid generation and submission

#### Automated Test Script
```bash
#!/bin/bash
# test_workflow.sh

echo "🧪 Starting Freelancer Bidder System Tests"

# Test 1: Configuration
echo "📋 Testing configuration..."
python -c "import config; print('✅ Config OK')" || exit 1

# Test 2: Skills system
echo "🎯 Testing skills system..."
python get_skills.py || exit 1

# Test 3: Single project analysis
echo "🔍 Testing project analysis..."
# Note: Replace with actual project ID for testing
# python add.py 123456789

# Test 4: Main bidder (dry run)
echo "🤖 Testing main bidder..."
python -c "
from bidder import get_active_projects, ProjectRanker
projects = get_active_projects(limit=5)
ranker = ProjectRanker()
print(f'✅ Fetched {len(projects.get(\"result\", {}).get(\"projects\", []))} projects')
"

# Test 5: Frontend build
echo "🌐 Testing frontend..."
cd vue-frontend
npm run build || exit 1
cd ..

echo "✅ All tests completed successfully!"
```

### 13. Debugging and Troubleshooting

#### Common Issues and Solutions

##### API Rate Limiting
- Check rate limit headers in responses
- Implement exponential backoff
- Monitor API usage quotas

##### WebSocket Connection Issues
- Verify browser automation setup
- Check network connectivity
- Validate WebSocket message format

##### AI API Failures
- Test API keys and quotas
- Verify model availability
- Check request format and parameters

##### Cache Corruption
- Clear cache directory: `rm -rf cache/`
- Restart with fresh cache
- Verify file permissions

#### Debug Mode
```bash
# Run with debug output
python bidder.py debug

# Enable verbose logging
export DEBUG=1
python bidder.py
```

### 14. Test Data Management

#### Test Project IDs
- Use sandbox/test project IDs when available
- Create test projects for validation
- Document known good/bad project examples

#### Mock Data
- Create mock API responses for testing
- Use test fixtures for consistent results
- Implement offline testing mode

### 15. Continuous Integration

#### Automated Testing Pipeline
```yaml
# .github/workflows/test.yml
name: Test Freelancer Bidder
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run tests
      run: ./test_workflow.sh
```

## Test Checklist

### Pre-deployment Testing
- [ ] All configuration files present and valid
- [ ] API keys working and have sufficient quotas
- [ ] Skills system functioning correctly
- [ ] Project analysis working for sample projects
- [ ] Frontend builds and runs without errors
- [ ] WebSocket monitoring connects successfully
- [ ] Cache system operational
- [ ] Currency conversion accurate
- [ ] Error handling graceful

### Post-deployment Monitoring
- [ ] Monitor API usage and rate limits
- [ ] Check bid success rates
- [ ] Verify project scoring accuracy
- [ ] Monitor system performance
- [ ] Track error rates and types
- [ ] Validate bid text quality

## Maintenance Testing

### Weekly Tests
- Verify API connectivity
- Check skills data freshness
- Test sample project analysis
- Monitor cache performance

### Monthly Tests
- Full system integration test
- Performance benchmarking
- Security audit
- Dependency updates

---

**Note**: Replace placeholder project IDs and API keys with actual test values. Always test in a safe environment before production deployment. 

## Quick Test Commands

### Basic System Check
```bash
# Test all core components
python -c "import config; print('Config OK')"
python get_skills.py
python -c "from bidder import get_our_skills; print(f'{len(get_our_skills())} skills loaded')"
```

### Frontend Quick Test
```bash
cd vue-frontend
npm run build
node server/index.js &
curl http://localhost:3000/api/jobs
```

### WebSocket Test
```bash
# Start monitoring (requires manual browser login)
python freelancer-websocket-reader.py
```

## Troubleshooting

### Common Issues
1. **API Rate Limiting** - Check rate limit headers, implement backoff
2. **WebSocket Connection** - Verify browser automation, check network
3. **AI API Failures** - Test API keys, verify model availability
4. **Cache Corruption** - Clear cache directory: `rm -rf cache/`

### Debug Mode
```bash
python bidder.py debug
export DEBUG=1
python bidder.py
``` 