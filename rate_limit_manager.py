#!/usr/bin/env python3
"""
Global Rate Limit Manager

This module manages a shared rate limit timestamp across all Freelancer API clients.
When rate limiting is detected, all API requests are paused for 30 minutes.
"""

import os
import time
from datetime import datetime, timedelta

# Path to the rate limit timestamp file
RATE_LIMIT_FILE = '.rate_limit_timestamp'

def set_rate_limit_timeout():
    """
    Set a rate limit timeout for 30 minutes from now.
    This should be called when a 429 rate limit response is detected.
    """
    timeout_time = time.time() + (30 * 60)  # Current time + 30 minutes
    
    try:
        with open(RATE_LIMIT_FILE, 'w') as f:
            f.write(str(timeout_time))
        
        timeout_datetime = datetime.fromtimestamp(timeout_time)
        print(f"🚫 Rate limit timeout set until: {timeout_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        return timeout_time
    except Exception as e:
        print(f"❌ Error setting rate limit timeout: {e}")
        return None

def get_rate_limit_timeout():
    """
    Get the current rate limit timeout timestamp.
    Returns None if no timeout is set or if the file doesn't exist.
    """
    try:
        if not os.path.exists(RATE_LIMIT_FILE):
            return None
            
        with open(RATE_LIMIT_FILE, 'r') as f:
            timeout_str = f.read().strip()
            
        if not timeout_str:
            return None
            
        return float(timeout_str)
    except Exception as e:
        print(f"❌ Error reading rate limit timeout: {e}")
        return None

def is_rate_limited():
    """
    Check if we are currently in a rate limit timeout period.
    Returns True if we should NOT make API requests, False if it's safe to proceed.
    """
    timeout_timestamp = get_rate_limit_timeout()
    
    if timeout_timestamp is None:
        return False
    
    current_time = time.time()
    
    if current_time < timeout_timestamp:
        remaining_seconds = int(timeout_timestamp - current_time)
        remaining_minutes = remaining_seconds // 60
        print(f"⏳ Rate limit active. Remaining time: {remaining_minutes} minutes, {remaining_seconds % 60} seconds")
        return True
    else:
        # Timeout has expired, clean up the file
        clear_rate_limit_timeout()
        return False

def clear_rate_limit_timeout():
    """
    Clear the rate limit timeout (remove the timestamp file).
    """
    try:
        if os.path.exists(RATE_LIMIT_FILE):
            os.remove(RATE_LIMIT_FILE)
            print("✅ Rate limit timeout cleared")
    except Exception as e:
        print(f"❌ Error clearing rate limit timeout: {e}")

def get_rate_limit_status():
    """
    Get detailed status information about the rate limit.
    Returns a dictionary with status information.
    """
    timeout_timestamp = get_rate_limit_timeout()
    current_time = time.time()
    
    if timeout_timestamp is None:
        return {
            'is_rate_limited': False,
            'timeout_timestamp': None,
            'remaining_seconds': 0,
            'timeout_until': None
        }
    
    remaining_seconds = max(0, int(timeout_timestamp - current_time))
    is_active = current_time < timeout_timestamp
    
    return {
        'is_rate_limited': is_active,
        'timeout_timestamp': timeout_timestamp,
        'remaining_seconds': remaining_seconds,
        'timeout_until': datetime.fromtimestamp(timeout_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    }

# Test function
if __name__ == '__main__':
    print("Testing Rate Limit Manager...")
    
    # Test setting timeout
    print("\n1. Setting rate limit timeout...")
    set_rate_limit_timeout()
    
    # Test checking status
    print("\n2. Checking rate limit status...")
    status = get_rate_limit_status()
    print(f"Status: {status}")
    
    # Test is_rate_limited
    print("\n3. Testing is_rate_limited()...")
    if is_rate_limited():
        print("✅ Rate limit is active")
    else:
        print("❌ Rate limit is not active")
    
    # Clear timeout for testing
    print("\n4. Clearing rate limit timeout...")
    clear_rate_limit_timeout()
    
    print("\n5. Final status check...")
    if is_rate_limited():
        print("❌ Rate limit should be cleared")
    else:
        print("✅ Rate limit successfully cleared") 