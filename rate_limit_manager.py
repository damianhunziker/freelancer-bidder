#!/usr/bin/env python3
"""
Global Rate Limit Manager

This module manages a shared rate limit timestamp across all Freelancer API clients.
When rate limiting is detected, all API requests are paused for 30 minutes.
Includes comprehensive logging for rate limit activities.
"""

import os
import time
from datetime import datetime, timedelta

# Path to the rate limit timestamp file
RATE_LIMIT_FILE = '.rate_limit_timestamp'

# Rate limit logging
RATE_LIMIT_LOG_DIR = 'api_logs'
RATE_LIMIT_LOG_FILE = os.path.join(RATE_LIMIT_LOG_DIR, 'rate_limit.log')

def setup_rate_limit_logs_directory():
    """Setup/clean the rate limit logs directory"""
    if not os.path.exists(RATE_LIMIT_LOG_DIR):
        os.makedirs(RATE_LIMIT_LOG_DIR)

def log_rate_limit_activity(event_type, details=None, context=None):
    """Log rate limit activities to file and console"""
    try:
        # Ensure logs directory exists
        setup_rate_limit_logs_directory()
        
        # Create timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Format log entry
        log_entry = f"{timestamp} | RATE_LIMIT | {event_type}"
        
        if context:
            log_entry += f" | context={context}"
        
        if details:
            if isinstance(details, dict):
                detail_str = " | ".join([f"{k}={v}" for k, v in details.items()])
                log_entry += f" | {detail_str}"
            else:
                log_entry += f" | details={details}"
        
        log_entry += "\n"
        
        # Write to log file
        with open(RATE_LIMIT_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # Also print to console
        print(f"🚫 RATE LIMIT LOG: {log_entry.strip()}")
            
    except Exception as e:
        print(f"Error logging rate limit activity: {str(e)}")

def set_rate_limit_timeout(context=None):
    """
    Set a rate limit timeout for 30 minutes from now.
    This should be called when a 429 rate limit response is detected.
    """
    timeout_time = time.time() + (30 * 60)  # Current time + 30 minutes
    
    try:
        with open(RATE_LIMIT_FILE, 'w') as f:
            f.write(str(timeout_time))
        
        timeout_datetime = datetime.fromtimestamp(timeout_time)
        
        # Log the rate limit activation
        log_details = {
            'timeout_until': timeout_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'timeout_duration_minutes': 30,
            'timeout_timestamp': timeout_time
        }
        log_rate_limit_activity('ACTIVATED', log_details, context)
        
        print(f"🚫 Rate limit timeout set until: {timeout_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        return timeout_time
    except Exception as e:
        error_msg = f"Error setting rate limit timeout: {e}"
        log_rate_limit_activity('ACTIVATION_ERROR', {'error': str(e)}, context)
        print(f"❌ {error_msg}")
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
        log_rate_limit_activity('READ_ERROR', {'error': str(e)})
        print(f"❌ Error reading rate limit timeout: {e}")
        return None

def is_rate_limited(context=None):
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
        
        # Log the rate limit check (only every 60 seconds to avoid spam)
        last_check_key = f"last_check_{context or 'default'}"
        last_check_time = getattr(is_rate_limited, last_check_key, 0)
        
        if current_time - last_check_time > 60:  # Log only every 60 seconds
            log_details = {
                'remaining_minutes': remaining_minutes,
                'remaining_seconds': remaining_seconds % 60,
                'timeout_until': datetime.fromtimestamp(timeout_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            }
            log_rate_limit_activity('STILL_ACTIVE', log_details, context)
            setattr(is_rate_limited, last_check_key, current_time)
        
        print(f"⏳ Rate limit active. Remaining time: {remaining_minutes} minutes, {remaining_seconds % 60} seconds")
        return True
    else:
        # Timeout has expired, clean up the file
        clear_rate_limit_timeout(context)
        return False

def clear_rate_limit_timeout(context=None):
    """
    Clear the rate limit timeout (remove the timestamp file).
    """
    try:
        if os.path.exists(RATE_LIMIT_FILE):
            # Log before clearing
            timeout_timestamp = get_rate_limit_timeout()
            if timeout_timestamp:
                log_details = {
                    'was_timeout_until': datetime.fromtimestamp(timeout_timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                    'cleared_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                log_rate_limit_activity('CLEARED', log_details, context)
            
            os.remove(RATE_LIMIT_FILE)
            print("✅ Rate limit timeout cleared")
    except Exception as e:
        error_msg = f"Error clearing rate limit timeout: {e}"
        log_rate_limit_activity('CLEAR_ERROR', {'error': str(e)}, context)
        print(f"❌ {error_msg}")

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

def get_rate_limit_logs(lines=50):
    """
    Get the last N lines from the rate limit log file.
    Returns a list of log entries.
    """
    try:
        if not os.path.exists(RATE_LIMIT_LOG_FILE):
            return []
        
        with open(RATE_LIMIT_LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # Return the last N lines
        return [line.strip() for line in all_lines[-lines:]]
    except Exception as e:
        print(f"Error reading rate limit logs: {e}")
        return []

def analyze_rate_limit_patterns():
    """
    Analyze rate limit patterns from the log file.
    Returns statistics about rate limiting.
    """
    try:
        logs = get_rate_limit_logs(1000)  # Analyze last 1000 entries
        
        activations = [log for log in logs if 'ACTIVATED' in log]
        clears = [log for log in logs if 'CLEARED' in log]
        errors = [log for log in logs if 'ERROR' in log]
        
        # Extract contexts
        contexts = {}
        for log in logs:
            if '| context=' in log:
                context = log.split('| context=')[1].split(' |')[0].split('\n')[0]
                contexts[context] = contexts.get(context, 0) + 1
        
        return {
            'total_events': len(logs),
            'activations': len(activations),
            'clears': len(clears),
            'errors': len(errors),
            'contexts': contexts,
            'last_activation': activations[-1] if activations else None,
            'last_clear': clears[-1] if clears else None
        }
    except Exception as e:
        print(f"Error analyzing rate limit patterns: {e}")
        return {}

# Test function
if __name__ == '__main__':
    print("Testing Rate Limit Manager with Logging...")
    
    # Test setting timeout
    print("\n1. Setting rate limit timeout...")
    set_rate_limit_timeout("test_context")
    
    # Test checking status
    print("\n2. Checking rate limit status...")
    status = get_rate_limit_status()
    print(f"Status: {status}")
    
    # Test is_rate_limited
    print("\n3. Testing is_rate_limited()...")
    if is_rate_limited("test_context"):
        print("✅ Rate limit is active")
    else:
        print("❌ Rate limit is not active")
    
    # Test log analysis
    print("\n4. Analyzing rate limit patterns...")
    patterns = analyze_rate_limit_patterns()
    print(f"Patterns: {patterns}")
    
    # Show recent logs
    print("\n5. Recent rate limit logs:")
    recent_logs = get_rate_limit_logs(5)
    for log in recent_logs:
        print(f"   {log}")
    
    # Clear timeout for testing
    print("\n6. Clearing rate limit timeout...")
    clear_rate_limit_timeout("test_context")
    
    print("\n7. Final status check...")
    if is_rate_limited("test_context"):
        print("❌ Rate limit should be cleared")
    else:
        print("✅ Rate limit successfully cleared") 