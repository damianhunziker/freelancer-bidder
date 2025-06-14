import requests
import json
import os
import time
from datetime import datetime
import sys
from collections import OrderedDict

# Configuration
FL_API_BASE_URL = "https://www.freelancer.com/api"
PROJECTS_ENDPOINT = "/projects/0.1/projects/active"
API_KEY = os.getenv("FREELANCER_API_KEY", "")
TEST_DURATION = 300  # 5 minutes per test
LOG_FILE = "rate_limit_test.log"

def log_test_result(delay, limit, duration, total_requests, failed_requests, rate_limits_hit, error_messages):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        log_entry = (
            f"\n=== Test Results ===\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Delay between requests: {delay} seconds\n"
            f"Project limit per request: {limit}\n"
            f"Test duration: {duration} seconds\n"
            f"Total requests made: {total_requests}\n"
            f"Failed requests: {failed_requests}\n"
            f"Rate limits hit: {rate_limits_hit}\n"
            f"Average requests per minute: {(total_requests / (duration/60)):.2f}\n"
            f"Error messages:\n{error_messages}\n"
            f"{'='*50}\n"
        )
        f.write(log_entry)
        print(log_entry)

def get_recent_projects(limit=10):
    """Fetch most recent projects from Freelancer API"""
    endpoint = f"{FL_API_BASE_URL}{PROJECTS_ENDPOINT}"
    
    params = {
        'limit': limit,
        'full_description': True,
        'job_details': True,
        'sort_field': 'time_updated',
        'sort_direction': 'desc',
        'project_statuses[]': ['active'],
        'active_only': True,
        'project_types[]': ['fixed', 'hourly'],
        'compact': True,
        'timeframe': 'last_24_hours'
    }
    
    headers = {
        'Freelancer-OAuth-V1': API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response_data = response.json()
        
        # Check if we have a valid result set
        if 'result' in response_data and 'projects' in response_data['result']:
            projects = response_data['result']['projects']
            return True, len(projects), None
            
        # Check for rate limit in response
        if response.status_code == 429 or (
            'error' in response_data and 
            isinstance(response_data['error'], dict) and 
            'message' in response_data['error'] and 
            'rate limit' in response_data['error']['message'].lower()
        ):
            return False, 0, "Rate limit exceeded"
            
        return False, 0, f"Invalid response: {response.status_code}"
        
    except Exception as e:
        return False, 0, str(e)

def test_rate_limit(delay, limit):
    print(f"\nStarting test with delay={delay}s and limit={limit}")
    start_time = time.time()
    total_requests = 0
    successful_requests = 0
    rate_limits_hit = 0
    last_success_time = None
    
    try:
        while time.time() - start_time < TEST_DURATION:
            success, num_projects, error = get_recent_projects(limit=limit)
            total_requests += 1
            
            current_time = time.time()
            
            if success:
                successful_requests += 1
                if last_success_time:
                    time_since_last = current_time - last_success_time
                    print(f"\nTime between successful requests: {time_since_last:.1f}s")
                last_success_time = current_time
                
                sys.stdout.write(f"\rRequests: {total_requests} | Success: {successful_requests} | Rate Limits: {rate_limits_hit} | Last batch: {num_projects} projects")
                sys.stdout.flush()
            else:
                if "rate limit" in error.lower():
                    rate_limits_hit += 1
                    print(f"\nRate limit hit at {datetime.now().strftime('%H:%M:%S')} - Waiting 15 minutes...")
                    time.sleep(900)  # 15 minutes
                else:
                    print(f"\nError: {error}")
            
            time.sleep(delay)
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    
    duration = time.time() - start_time
    requests_per_minute = total_requests / (duration/60)
    success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0
    
    print(f"\n\nTest Results:")
    print(f"Duration: {duration:.1f}s")
    print(f"Requests per minute: {requests_per_minute:.1f}")
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Rate limits hit: {rate_limits_hit}")
    
    return rate_limits_hit == 0

def main():
    # Test configurations
    configurations = [
        {'delay': 10, 'limit': 12},  # More aggressive first test
        {'delay': 8, 'limit': 15},   # Pushing boundaries
        {'delay': 6, 'limit': 20}    # Most aggressive test
    ]
    
    print("Starting rate limit testing...")
    print("Each test will run for 300 seconds")
    print("Starting with conservative delays to avoid existing rate limits")
    print("\nWaiting 15 minutes before starting tests to ensure rate limit window is reset...")
    time.sleep(900)  # Wait 15 minutes before starting
    
    for config in configurations:
        print(f"\nTesting configuration: delay={config['delay']}s, limit={config['limit']}")
        success = test_rate_limit(config['delay'], config['limit'])
        
        if not success:
            print(f"\nRate limit hit with delay={config['delay']}s. Stopping tests.")
            break
        
        # Wait between tests
        if not config == configurations[-1]:
            print("\nWaiting 5 minutes before next test...")
            time.sleep(300)

if __name__ == "__main__":
    main() 