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
    LIMIT_HIGH_PAYING_HOURLY
)
import config
from rate_limit_manager import is_rate_limited, set_rate_limit_timeout, get_rate_limit_status

# High-paying thresholds in USD (same as bidder.py)
LIMIT_HIGH_PAYING_FIXED = 1000  # Projects with average bid >= $1000 are considered high-paying
LIMIT_HIGH_PAYING_HOURLY = 25   # Projects with average hourly rate >= $25/hr are considered high-paying

# Profile configurations (exactly same as bidder.py)
PROFILES = {
    'default': {
        'search_query': '',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'recent',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 0,  # Minimum average fixed price in USD
        'min_hourly': 0   # Minimum average hourly rate in USD
    },    
    'broad_past': {
        'search_query': 'payment, chatgpt, deepeek, api,n8n, PHP, OOP, MVC, Laravel, Composer, SQL, Javascript, Node.js, jQuery, ReactJS, plotly.js, chartJs, HTML5, SCSS, Bootstrap, Typo3, WordPress, Redaxo, Prestashop, Gambio, Linux Console, Git, Pine Script, vue, binance, Bybit, Okx, Crypto, IBKR, brokers, trading, typo3, redaxo, gambio, ccxt, scrape, blockchain, plotly, chartjs',   
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 200,
        'score_limit': 40,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 60,
        'min_hourly': 10
    },    
    'broad_recent': {
        'search_query': 'payment, chatgpt, deepseek, api, n8n, PHP, OOP, MVC, Laravel, Composer, SQL, Javascript, Node.js, jQuery, ReactJS, plotly.js, chartJs, HTML5, SCSS, Bootstrap, Typo3, WordPress, Redaxo, Prestashop, Gambio, Linux Console, Git, Pine Script, vue, binance, Bybit, Okx, Crypto, IBKR, brokers, trading, typo3, redaxo, gambio, ccxt, scrape, blockchain, plotly, chartjs',   
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 200,
        'score_limit': 40,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'recent',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 60,
        'min_hourly': 10
    },    
    'niches_past': {
        'search_query': 'n8n, vue, laravel, binance, Bybit, Okx, Crypto, IBKR, brokers, trading, typo3, redaxo, gambio, ccxt, scrape, blockchain, plotly, chartjs,',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 200,
        'score_limit': 40,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 0,
        'min_hourly': 0
    },    
    'niches_recent': {
        'search_query': 'n8n, vue, laravel, binance, Bybit, Okx, Crypto, IBKR, brokers, trading, typo3, redaxo, gambio, ccxt, scrape, blockchain, plotly, chartjs,',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 200,
        'score_limit': 40,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'recent',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 0,
        'min_hourly': 0
    },
    'high_paying_past': {
        'search_query': '',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 200,
        'score_limit': 40,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': True,
        'clear_cache': False,
        'min_fixed': 500,
        'min_hourly': 20
    },
    'high_paying_recent': {
        'search_query': '',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 200,
        'score_limit': 40,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'recent',
        'high_paying_only': True,
        'clear_cache': False,
        'min_fixed': 500,
        'min_hourly': 20
    },
    'german_past': {
        'search_query': '',
        'project_types': ['fixed','hourly'],
        'bid_limit': 200,
        'score_limit': 40,
        'country_mode': 'g',
        'german_only': True,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 50,
        'min_hourly': 10
    },
    'german_recent': {
        'search_query': '',
        'project_types': ['fixed','hourly'],
        'bid_limit': 200,
        'score_limit': 40,
        'country_mode': 'g',
        'german_only': True,
        'scan_scope': 'recent',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 50,
        'min_hourly': 10
    },
    'hourly_only_past': {
        'search_query': '',
        'project_types': ['hourly'],
        'bid_limit': 200,
        'score_limit': 40,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 0,
        'min_hourly': 5
    },
    'hourly_only_recent': {
        'search_query': '',
        'project_types': ['hourly'],
        'bid_limit': 200,
        'score_limit': 40,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'recent',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 0,
        'min_hourly': 5
    },
    'past_projects': {
        'search_query': '',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 200,
        'score_limit': 40,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 50,
        'min_hourly': 10
    },
    'delete_cache': {
        'search_query': 'z23uz23842834234k234',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': True,
        'min_fixed': 0,
        'min_hourly': 0
    }
}

# Load profile configuration
PROFILE_FILE = 'profiles/add_profile.json'
if os.path.exists(PROFILE_FILE):
    try:
        with open(PROFILE_FILE, 'r') as f:
            profile_config = json.load(f)
        profile_name = profile_config.get('profile_name', 'default')
        if profile_name in PROFILES:
            selected_profile = PROFILES[profile_name]
            print(f"✅ Loaded profile: {profile_name}")
        else:
            selected_profile = PROFILES['default']
            print(f"⚠️ Profile '{profile_name}' not found, using default")
    except Exception as e:
        print(f"⚠️ Error loading profile: {e}")
        print("Using default profile")
        selected_profile = PROFILES['default']
else:
    selected_profile = PROFILES['default']
    print("Using default profile")

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
            return None
        
        # Debug response
        try:
            data = response.json()
            print(f"📄 Raw Response: {json.dumps(data, indent=2)}")
        except:
            print(f"📄 Raw Response Text: {response.text}")
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
    if len(sys.argv) != 2:
        print("Usage: python add.py <project_id>")
        return

    project_id = sys.argv[1]
    
    # Use default profile for single project analysis
    from bidder import PROFILES
    selected_profile = PROFILES['default']
    
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