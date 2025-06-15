/**
 * Global Rate Limit Manager for Node.js
 * 
 * This module manages a shared rate limit timestamp across all Freelancer API clients.
 * When rate limiting is detected, all API requests are paused for 30 minutes.
 */

const fs = require('fs');
const path = require('path');

// Path to the rate limit timestamp file (in project root)
const RATE_LIMIT_FILE = path.join(__dirname, '..', '..', '.rate_limit_timestamp');

/**
 * Set a rate limit timeout for 30 minutes from now.
 * This should be called when a 429 rate limit response is detected.
 */
function setRateLimitTimeout() {
    const timeoutTime = Math.floor(Date.now() / 1000) + (30 * 60); // Current time in seconds + 30 minutes
    
    try {
        fs.writeFileSync(RATE_LIMIT_FILE, timeoutTime.toString());
        
        const timeoutDate = new Date(timeoutTime * 1000);
        console.log(`🚫 Rate limit timeout set until: ${timeoutDate.toLocaleString()}`);
        return timeoutTime;
    } catch (error) {
        console.error(`❌ Error setting rate limit timeout: ${error.message}`);
        return null;
    }
}

/**
 * Get the current rate limit timeout timestamp.
 * Returns null if no timeout is set or if the file doesn't exist.
 */
function getRateLimitTimeout() {
    try {
        if (!fs.existsSync(RATE_LIMIT_FILE)) {
            return null;
        }
        
        const timeoutStr = fs.readFileSync(RATE_LIMIT_FILE, 'utf8').trim();
        
        if (!timeoutStr) {
            return null;
        }
        
        return parseFloat(timeoutStr); // Use parseFloat for seconds with decimals
    } catch (error) {
        console.error(`❌ Error reading rate limit timeout: ${error.message}`);
        return null;
    }
}

/**
 * Check if we are currently in a rate limit timeout period.
 * Returns true if we should NOT make API requests, false if it's safe to proceed.
 */
function isRateLimited() {
    const timeoutTimestamp = getRateLimitTimeout();
    
    if (timeoutTimestamp === null) {
        return false;
    }
    
    const currentTime = Math.floor(Date.now() / 1000); // Current time in seconds
    
    if (currentTime < timeoutTimestamp) {
        const remainingSeconds = timeoutTimestamp - currentTime;
        const remainingMinutes = Math.floor(remainingSeconds / 60);
        const remainingSecondsDisplay = remainingSeconds % 60;
        console.log(`⏳ Rate limit active. Remaining time: ${remainingMinutes} minutes, ${remainingSecondsDisplay} seconds`);
        return true;
    } else {
        // Timeout has expired, clean up the file
        clearRateLimitTimeout();
        return false;
    }
}

/**
 * Clear the rate limit timeout (remove the timestamp file).
 */
function clearRateLimitTimeout() {
    try {
        if (fs.existsSync(RATE_LIMIT_FILE)) {
            fs.unlinkSync(RATE_LIMIT_FILE);
            console.log('✅ Rate limit timeout cleared');
        }
    } catch (error) {
        console.error(`❌ Error clearing rate limit timeout: ${error.message}`);
    }
}

/**
 * Get detailed status information about the rate limit.
 * Returns an object with status information.
 */
function getRateLimitStatus() {
    const timeoutTimestamp = getRateLimitTimeout();
    const currentTime = Math.floor(Date.now() / 1000); // Current time in seconds
    
    if (timeoutTimestamp === null) {
        return {
            isRateLimited: false,
            timeoutTimestamp: null,
            remainingSeconds: 0,
            timeoutUntil: null
        };
    }
    
    const remainingSeconds = Math.max(0, timeoutTimestamp - currentTime);
    const isActive = currentTime < timeoutTimestamp;
    
    return {
        isRateLimited: isActive,
        timeoutTimestamp: timeoutTimestamp,
        remainingSeconds: remainingSeconds,
        timeoutUntil: new Date(timeoutTimestamp * 1000).toLocaleString()
    };
}

/**
 * Wrapper function to check rate limit before making API calls.
 * Returns true if the API call should proceed, false if it should be skipped.
 */
function shouldProceedWithApiCall(context = 'API call', allowBidGeneration = false) {
    // Allow bid text generation even during rate limiting
    if (allowBidGeneration) {
        return true;
    }
    
    if (isRateLimited()) {
        console.log(`🚫 Skipping ${context} due to rate limiting`);
        return false;
    }
    
    return true;
}

/**
 * Handle a rate limit response (429 status code).
 * Sets the timeout and logs the event.
 */
function handleRateLimitResponse(context = 'API call') {
    console.error(`🚫 Rate limiting detected in ${context}! Setting 30-minute timeout...`);
    setRateLimitTimeout();
}

module.exports = {
    setRateLimitTimeout,
    getRateLimitTimeout,
    isRateLimited,
    clearRateLimitTimeout,
    getRateLimitStatus,
    shouldProceedWithApiCall,
    handleRateLimitResponse
};

// Test function (only runs when executed directly)
if (require.main === module) {
    console.log('Testing Rate Limit Manager...');
    
    // Test setting timeout
    console.log('\n1. Setting rate limit timeout...');
    setRateLimitTimeout();
    
    // Test checking status
    console.log('\n2. Checking rate limit status...');
    const status = getRateLimitStatus();
    console.log('Status:', status);
    
    // Test isRateLimited
    console.log('\n3. Testing isRateLimited()...');
    if (isRateLimited()) {
        console.log('✅ Rate limit is active');
    } else {
        console.log('❌ Rate limit is not active');
    }
    
    // Test shouldProceedWithApiCall
    console.log('\n4. Testing shouldProceedWithApiCall()...');
    console.log('Normal API call:', shouldProceedWithApiCall('test API call'));
    console.log('Bid generation:', shouldProceedWithApiCall('bid generation', true));
    
    // Clear timeout for testing
    console.log('\n5. Clearing rate limit timeout...');
    clearRateLimitTimeout();
    
    console.log('\n6. Final status check...');
    if (isRateLimited()) {
        console.log('❌ Rate limit should be cleared');
    } else {
        console.log('✅ Rate limit successfully cleared');
    }
} 