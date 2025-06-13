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
    """Fetch project details from Freelancer API"""
    try:
        url = f"{config.FL_API_BASE_URL}/projects/0.1/projects/{project_id}/"
    
        params = {
            'job_details': True,
            'user_details': True,
            'user_country_details': True,
            'user_hourly_rate_details': True,
            'user_status_details': True,
            'hourly_project_info': True,
            'upgrade_details': True,
            'full_description': True,
            'reputation': True,
            'attachment_details': True,
            'employer_reputation': True,
            'bid_details': True,
            'profile_description': True,
            'sort_field': 'time_updated',
            'sort_direction': 'desc',
            'project_statuses[]': ['active'],
            'active_only': True,
            'compact': True,
            'or_search_query': True,
            'jobs': True
        }
    
        headers = {
                'freelancer-oauth-v1': config.FREELANCER_API_KEY
            }
        
        print(f"\n=== API Request Parameters ===")
        print(f"URL: {url}")
        print(f"Parameters: {json.dumps(params, indent=2)}")
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        result = response.json()['result']
        
        def format_timestamp(timestamp):
            if timestamp is None:
                return "None"
            try:
                from datetime import datetime
                return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            except:
                return str(timestamp)
        
        print("\n=== Timestamp Debug ===")
        print(f"Raw submitdate: {result.get('submitdate')}")
        print(f"Raw time_submitted: {result.get('time_submitted')}")
        print(f"Raw time_updated: {result.get('time_updated')}")
        
        # Use time_submitted if available, otherwise fall back to submitdate
        final_time_submitted = result.get('time_submitted') or result.get('submitdate')
        final_time_updated = result.get('time_updated') or final_time_submitted
        
        print("\n=== Final Timestamps ===")
        print(f"Final time_submitted: {final_time_submitted} ({format_timestamp(final_time_submitted)})")
        print(f"Final time_updated: {final_time_updated} ({format_timestamp(final_time_updated)})")
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

def get_user_details(user_id: str, cache: dict, failed_users: set) -> dict:
    """Fetch user details from Freelancer API"""
    try:
        url = f"{config.FL_API_BASE_URL}/users/0.1/users/{user_id}/"
        
        params = {
            'user_details': True,
            'user_country_details': True,
            'user_hourly_rate_details': True,
            'user_status_details': True,
            'profile_description': True
        }
        
        headers = {
            'freelancer-oauth-v1': config.FREELANCER_API_KEY
        }
        
        print(f"\n💾 CACHE: Loading user {user_id} details")
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        print(f"Error fetching user details: {str(e)}")
        return {'result': None}

def get_user_reputation(user_id: str, cache: dict) -> dict:
    """Fetch user reputation from Freelancer API"""
    try:
        url = f"{config.FL_API_BASE_URL}/users/0.1/users/{user_id}/reputation/"
        
        params = {
            'user_details': True,
            'user_country_details': True,
            'user_hourly_rate_details': True,
            'user_status_details': True,
            'profile_description': True
        }
        
        headers = {
            'freelancer-oauth-v1': config.FREELANCER_API_KEY
        }
        
        print(f"\n💾 CACHE: Loading reputation for user {user_id}")
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        print(f"Error fetching user reputation: {str(e)}")
        return {'result': None}

def calculate_project_score(project_data: dict, user_skills: List[str]) -> int:
    """Calculate a score for the project based on various factors."""
    score = 0
    
    # Budget/rate score
    if project_data['type'] == 'fixed':
        if project_data['budget']['min'] >= selected_profile['min_fixed']:
            score += 30
        if project_data['budget']['max'] >= selected_profile['min_fixed'] * 2:
            score += 20
    else:  # hourly
        if project_data['hourly_rate'] >= selected_profile['min_hourly']:
            score += 30
        if project_data['hourly_rate'] >= selected_profile['min_hourly'] * 1.5:
            score += 20
            
    # Skills match score
    project_skills = [skill.lower() for skill in project_data['skills']]
    user_skills_lower = [skill.lower() for skill in user_skills]
    matching_skills = [skill for skill in project_skills if skill in user_skills_lower]
    
    if matching_skills:
        score += min(len(matching_skills) * 10, 30)  # Up to 30 points for skills
        
    # Employer score
    if project_data['employer_earnings_score'] >= selected_profile['min_fixed']:
        score += 20
        
    # Bid count score
    if project_data['bid_count'] <= selected_profile['bid_limit']:
        score += 10
        
    return score

def save_project_to_json(project_data: dict, score: int) -> None:
    """Save the project data to a JSON file."""
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    project_id = project_data['id']
    filename = f"{output_dir}/project_{project_id}.json"
    
    data = {
        'project': project_data,
        'score': score,
        'profile': selected_profile.get('profile_name', 'unknown'),
        'timestamp': datetime.now().isoformat()
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved project data to {filename}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python add.py <project_id>")
        return

    project_id = sys.argv[1]
    
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
    if process_evaluated_project(project, project_id, evaluation, ranker, selected_profile):
        print("✅ Project processed successfully")
    else:
        print("⏭️ Project did not meet criteria")

if __name__ == "__main__":
    main() 