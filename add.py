#!/usr/bin/env python3
import os
import sys
import json
import time
from datetime import datetime
import requests
from typing import Dict, List, Optional, Tuple, Any
from bidder import (
    evaluate_project, 
    format_project_display,
    process_evaluated_project,
    check_project_eligibility,
    prepare_project_data,
    check_high_paying_criteria,
    check_country_criteria,
    get_user_details,
    get_user_reputation,
    ProjectRanker,
    FileCache,
    CurrencyManager,
    LIMIT_HIGH_PAYING_FIXED,
    LIMIT_HIGH_PAYING_HOURLY,
    PROFILES
)
import config
from rate_limit_manager import is_rate_limited, set_rate_limit_timeout, get_rate_limit_status

# Now using PROFILES imported from bidder.py to avoid duplication

# API Logging setup
API_LOGS_DIR = 'api_logs'
API_REQUEST_LOG = os.path.join(API_LOGS_DIR, 'freelancer_requests.log')

def setup_api_logs_directory():
    """Setup/clean the API logs directory"""
    if not os.path.exists(API_LOGS_DIR):
        os.makedirs(API_LOGS_DIR)

def log_api_request(endpoint: str, params: dict, response_status: int, response_data: dict = None):
    """Log API request details to file with comprehensive information"""
    try:
        # Ensure logs directory exists
        setup_api_logs_directory()
        
        # Create timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine if this is a Projects API request
        is_projects_api = '/projects/0.1/' in endpoint
        
        # Basic log entry
        if is_projects_api:
            # Enhanced logging for Projects API
            endpoint_type = "UNKNOWN"
            if '/projects/active' in endpoint:
                endpoint_type = "GET_ACTIVE_PROJECTS"
            elif '/projects/' in endpoint and endpoint.count('/') >= 5:
                if '/bids' in endpoint:
                    endpoint_type = "BIDS_API"
                else:
                    endpoint_type = "GET_PROJECT_DETAILS"
            elif '/users/' in endpoint:
                endpoint_type = "GET_USER_DETAILS"
            elif '/reputations/' in endpoint:
                endpoint_type = "GET_USER_REPUTATION"
            
            # Extract key parameters for projects API
            key_params = {}
            if params:
                # Common parameters
                if 'limit' in params:
                    key_params['limit'] = params['limit']
                if 'query' in params:
                    key_params['query'] = params['query']
                if 'project_types[]' in params:
                    key_params['project_types'] = params['project_types[]']
                if 'languages[]' in params:
                    key_params['languages'] = params['languages[]']
                if 'from_time' in params:
                    key_params['from_time'] = params['from_time']
                if 'offset' in params:
                    key_params['offset'] = params['offset']
                if 'full_description' in params:
                    key_params['full_description'] = params['full_description']
                if 'job_details' in params:
                    key_params['job_details'] = params['job_details']
            
            # Extract response info
            response_info = {}
            if response_data and 'result' in response_data:
                result = response_data['result']
                if 'projects' in result:
                    response_info['projects_count'] = len(result['projects'])
                if 'users' in result:
                    response_info['users_count'] = len(result['users'])
                if 'id' in result:
                    response_info['project_id'] = result['id']
                if 'title' in result:
                    response_info['project_title'] = result['title'][:50] + "..." if len(result.get('title', '')) > 50 else result.get('title', '')
            
            # Format enhanced log entry
            log_entry = f"{timestamp} | ADD.PY | {endpoint_type} | {endpoint}"
            if key_params:
                params_str = " | ".join([f"{k}={v}" for k, v in key_params.items()])
                log_entry += f" | PARAMS: {params_str}"
            if response_info:
                response_str = " | ".join([f"{k}={v}" for k, v in response_info.items()])
                log_entry += f" | RESPONSE: {response_str}"
            log_entry += f" | STATUS: {response_status}\n"
        else:
            # Standard logging for non-projects API
            log_entry = f"{timestamp} | ADD.PY | {endpoint} | STATUS: {response_status}\n"
        
        # Write to log file
        with open(API_REQUEST_LOG, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
        # Also print to console for projects API requests
        if is_projects_api:
            print(f"📝 ADD.PY API LOG: {log_entry.strip()}")
            
    except Exception as e:
        print(f"Error logging API request: {str(e)}")

def load_profile_from_json():
    """Load profile from add_profile.json file"""
    PROFILE_FILE = 'profiles/add_profile.json'
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, 'r') as f:
                profile_config = json.load(f)
            profile_name = profile_config.get('profile_name', 'default')
            if profile_name in PROFILES:
                print(f"✅ Loaded profile from JSON: {profile_name}")
                return PROFILES[profile_name]
            else:
                print(f"⚠️ Profile '{profile_name}' not found in JSON, using default")
                return PROFILES['default']
        except Exception as e:
            print(f"⚠️ Error loading profile from JSON: {e}")
            print("Using default profile")
            return PROFILES['default']
    else:
        print("⚠️ add_profile.json not found, using default profile")
        return PROFILES['default']

def select_profile_interactively():
    """Allow user to select profile interactively"""
    print("\n=== Profile Selection ===")
    print("\nAvailable profiles:")
    profile_list = list(PROFILES.keys())
    for idx, profile_name in enumerate(profile_list, 1):
        print(f"{idx}. {profile_name}")
    
    # Ask for profile selection by number
    profile_input = input("\nSelect a profile number (or press Enter for default): ").strip()
    
    # Handle profile selection
    if profile_input.isdigit() and 1 <= int(profile_input) <= len(profile_list):
        profile_name = profile_list[int(profile_input) - 1]
        selected_profile = PROFILES[profile_name]
        print(f"\n✅ Selected profile: {profile_name}")
        return selected_profile
    else:
        print("\n✅ Using default profile")
        return PROFILES['default']

def get_project_details(project_id: str) -> dict:
    """Fetch complete project details including all metadata"""
    try:
        url = f"{config.FL_API_BASE_URL}/projects/0.1/projects/{project_id}"

        params = {
            'full_description': True,
            'job_details': True,
            'user_details': True,
            'bid_details': True,
            'user_country_details': True,
            'upgrade_details': True,
            'attachment_details': True,
            'employer_reputation': True,
            'profile_description': True,
            'compact': True
        }
        
        headers = {
            'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        # Check global rate limit before making API call
        if is_rate_limited():
            print("🚫 Global rate limit active - skipping Freelancer API call")
            return None
        
        print(f"\n🌐 API: Fetching project details for {project_id}")
        print(f"🔗 URL: {url}")
        print(f"📝 Parameters: {params}")
        
        response = requests.get(url, params=params, headers=headers)
        
        print(f"📊 Response Status: {response.status_code}")
        
        # Handle rate limiting
        if response.status_code == 429:
            print(f"🚫 Rate Limiting erkannt! Setze globalen Timeout für 30 Minuten...")
            set_rate_limit_timeout()
            # Log the API request even when rate limited
            log_api_request(url, params, response.status_code)
            return None
        
        # Debug response
        try:
            data = response.json()
            print(f"📄 Raw Response: {json.dumps(data, indent=2)}")
            # Log the API request with response data
            log_api_request(url, params, response.status_code, data)
        except:
            print(f"📄 Raw Response Text: {response.text}")
            # Log the API request without response data
            log_api_request(url, params, response.status_code)
            response.raise_for_status()
            return None
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            response.raise_for_status()
            return None
        
        if 'result' not in data:
            print(f"❌ No 'result' key in response")
            return None
        
        # For single project queries, the project is directly in 'result'
        result = data['result']
        
        # Check if project is valid
        if not result or 'id' not in result:
            print(f"❌ Invalid project data")
            return None
        
        def format_timestamp(timestamp):
            if timestamp:
                return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            return 'N/A'
        
        print(f"\n=== Project Details ===")
        print(f"Project: {result.get('title')}")
        print(f"Status: {result.get('status')}")
        print(f"Type: {result.get('type')}")
        print(f"Owner: {result.get('owner_id')}")
        
        # Parse time_submitted (Unix timestamp)
        time_submitted = result.get('time_submitted')
        if time_submitted:
            final_time_submitted = time_submitted
        else:
            final_time_submitted = time.time()
        
        print(f"Final timestamp: {final_time_submitted} ({format_timestamp(final_time_submitted)})")
        
        print("\n=== Other Project Data ===")
        print(f"Project ID: {result.get('id')}")
        print(f"Title: {result.get('title')}")
        print(f"Project Type: {result.get('type')}")
        print(f"Country: {result.get('country', 'Unknown')}")
        print(f"Is German: {result.get('country', '').lower() in config.GERMAN_SPEAKING_COUNTRIES}")
        print(f"Bid Count: {result.get('bid_stats', {}).get('bid_count', 0)}")
        print(f"Jobs/Skills: {[job.get('name') for job in result.get('jobs', [])]}")
        
        return result
        
    except Exception as e:
        print(f"Error fetching project details: {str(e)}")
        return None



def main():
    # Check if script is called with or without parameters
    if len(sys.argv) == 1:
        # Interactive mode: no parameters - show profile selection
        print("🔧 Interactive mode: Select profile")
        selected_profile = select_profile_interactively()
        
        # Ask for project ID
        project_id = input("\nEnter project ID to analyze: ").strip()
        if not project_id:
            print("❌ No project ID provided")
            return
            
    elif len(sys.argv) == 2:
        # Automatic mode: called with project_id parameter (from freelancer-websocket-reader)
        project_id = sys.argv[1]
        print(f"🤖 Automatic mode: Using profile from add_profile.json for project {project_id}")
        selected_profile = load_profile_from_json()
        
    else:
        print("Usage:")
        print("  python add.py                    # Interactive mode with profile selection")
        print("  python add.py <project_id>       # Automatic mode using add_profile.json")
        return
    
    # Initialize cache and ranker (same as bidder.py)
    cache = FileCache(cache_dir='cache', expiry=3600)
    ranker = ProjectRanker()
    seen_projects = set()
    failed_users = set()
    
    # Get project details
    project = get_project_details(project_id)
    if not project:
        print("❌ Failed to get project details")
        return
        
    # Check project eligibility (same as bidder.py)
    is_eligible, reason = check_project_eligibility(
        project,
        project_id,
        selected_profile,
        seen_projects
    )
    
    if not is_eligible:
        print(f"⏭️ Skipped: {reason}")
        return
        
    # Get user details (same as bidder.py)
    owner_id = project.get('owner_id')
    user_details = get_user_details(owner_id, cache, failed_users)
    
    country = "Unknown"
    if user_details and 'result' in user_details and user_details['result']:
        user_data = user_details['result']
        location = user_data.get('location', {})
        if location and 'country' in location:
            country = location['country'].get('name', 'Unknown')
    
    # Check country criteria (same as bidder.py)
    is_valid_country, reason = check_country_criteria(project, country, selected_profile)
    if not is_valid_country:
        print(f"🌍 Skipped: {reason}")
        return
    
    # Get user reputation (same as bidder.py)
    reputation_data = get_user_reputation(owner_id, cache)
    if not reputation_data:
        print(f"👤 Warning: Failed to fetch reputation data, continuing with empty reputation")
        reputation_data = {'result': {}}
        
    # Prepare project data (same as bidder.py)
    project_data = prepare_project_data(
        project,
        project_id,
        reputation_data.get('result', {}),
        country
    )
    
    # Evaluate the project (same as bidder.py)
    evaluation = evaluate_project(project_data, selected_profile)
    
    # Process the evaluated project (same as bidder.py)
    result = process_evaluated_project(project, project_id, evaluation, ranker, selected_profile)
    if result:
        print("✅ Project processed successfully")
    else:
        print("⏭️ Project did not meet criteria")

if __name__ == "__main__":
    main() 