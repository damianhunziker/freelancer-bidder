# Global Rate Limiting System

This system implements a global rate limiting for all Freelancer API calls throughout the project.

## Overview

When a 429 rate limiting response is detected from the Freelancer API, a 30-minute timeout is automatically set for **all** API clients. The system uses a shared `.rate_limit_timestamp` file that is read by all components.

## Affected Files

### Python Files
- `bidder.py` - Main bidding engine
- `add.py` - Single project analysis
- `rate_limit_manager.py` - Python implementation of rate limit functions

### Node.js/JavaScript Files
- `vue-frontend/server/index.js` - Vue.js backend server
- `vue-frontend/server/rateLimitManager.js` - JavaScript implementation of rate limit functions

## How It Works

### 1. Rate Limit Detection
When one of the files receives a 429 response from the Freelancer API:
```python
# Python
if response.status_code == 429:
    set_rate_limit_timeout()
```

```javascript
// JavaScript
if (response.status === 429) {
    handleRateLimitResponse(context);
}
```

### 2. Global Timeout
- Current time + 30 minutes is stored in `.rate_limit_timestamp`
- All other clients check this file before making any API calls

### 3. API Call Check
Before making any Freelancer API calls:
```python
# Python
if is_rate_limited():
    print("🚫 Global rate limit active - skipping API call")
    return
```

```javascript
// JavaScript
if (!shouldProceedWithApiCall(context)) {
    throw new Error('Rate limit active - skipping API call');
}
```

## Exceptions

### Bid Text Generation
AI-based bid generation is exempt from rate limiting and works even during a timeout:

```javascript
// Bid generation is always allowed
const response = await makeAPICallWithTimeout(url, {
    context: 'Bid Generation',
    allowBidGeneration: true
});
```

## Files and Functions

### Python (`rate_limit_manager.py`)
```python
# Main functions
is_rate_limited()           # Checks active rate limit status
set_rate_limit_timeout()    # Sets 30-minute timeout
get_rate_limit_status()     # Returns detailed status info
clear_rate_limit_timeout()  # Clears the timeout manually
```

### JavaScript (`vue-frontend/server/rateLimitManager.js`)
```javascript
// Main functions
isRateLimited()                              // Checks active rate limit status
setRateLimitTimeout()                        // Sets 30-minute timeout
shouldProceedWithApiCall(context)             // Wrapper for API call check
handleRateLimitResponse(context)             // Handles 429 responses
```

## Configuration

### Rate Limit File
- **File**: `.rate_limit_timeout`
- **Format**: Unix timestamp (milliseconds for JS, seconds for Python)
- **Location**: Project root directory

### Timeout Duration
- **Default**: 30 minutes (1800 seconds)
- **Configurable**: Can be adjusted in the manager files

## Usage

### Adding New API Calls

**Python:**
```python
from rate_limit_manager import is_rate_limited, set_rate_limit_timeout

def my_api_call():
    if is_rate_limited():
        print("🚫 Rate limit active - skipping API call")
        return None
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 429:
        set_rate_limit_timeout()
        return None
    
    return response.json()
```

**JavaScript:**
```javascript
const { shouldProceedWithApiCall, handleRateLimitResponse } = require('./rateLimitManager');

async function myApiCall() {
    if (!shouldProceedWithApiCall('My API Call')) {
        throw new Error('Rate limit active');
    }
    
    const response = await fetch(url, options);
    
    if (response.status === 429) {
        handleRateLimitResponse('My API Call');
        throw new Error('Rate limit detected');
    }
    
    return response.json();
}
```

## Status Monitoring

### Python
```python
from rate_limit_manager import get_rate_limit_status

status = get_rate_limit_status()
print(f"Rate limited: {status['is_rate_limited']}")
print(f"Remaining time: {status['remaining_seconds']} seconds")
print(f"Timeout until: {status['timeout_until']}")
```

### JavaScript
```javascript
const { getRateLimitStatus } = require('./rateLimitManager');

const status = getRateLimitStatus();
console.log(`Rate limited: ${status.isRateLimited}`);
console.log(`Remaining time: ${status.remainingMs / 1000} seconds`);
console.log(`Timeout until: ${status.timeoutUntil}`);
```

## Testing

### Python
```bash
python rate_limit_manager.py
```

### JavaScript
```bash
node vue-frontend/server/rateLimitManager.js
```

## Logs and Debugging

The system outputs detailed logs:
- `🚫` Rate limit detected/active
- `⏳` Display remaining time
- `✅` Rate limit lifted

## Backup and Recovery

- The `.rate_limit_timestamp` file can be manually deleted to reset rate limiting
- The system cleans up expired timeouts automatically
- In case of filesystem errors, the system errs on the conservative side (no rate limit assumed)

## Rate Limit Timestamp File

The `.rate_limit_timestamp` file contains a single Unix timestamp in **seconds** (not milliseconds) representing when the rate limit timeout expires.

### Timestamp Format

All timestamps are stored as Unix timestamps in **seconds** across all components:
- Python: Uses `time.time()` which returns seconds since epoch
- JavaScript: Uses `Math.floor(Date.now() / 1000)` to convert milliseconds to seconds

This ensures consistency when the timestamp file is read by different components.