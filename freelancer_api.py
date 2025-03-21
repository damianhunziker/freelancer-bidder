import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
from pprint import pprint
import config

class FreelancerAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = config.BASE_URL
        self.headers = {
            'Freelancer-OAuth-V1': api_key,
            'Content-Type': 'application/json'
        }

    def get_active_projects(self, limit: int = config.DEFAULT_PROJECT_LIMIT) -> Dict:
        endpoint = f'{self.base_url}{config.PROJECTS_ENDPOINT}'
        params = {
            'limit': limit,
            'full_description': True,
            'job_details': True,
            'user_details': True,
            'users[]': ['id', 'username', 'reputation', 'country', 'hourly_rate', 'earnings'],
            'owners[]': ['id', 'username', 'reputation', 'country', 'hourly_rate', 'earnings']
        }
        
        response = requests.get(endpoint, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_user_details(self, user_id: int) -> Dict:
        endpoint = f'{self.base_url}/users/0.1/users/{user_id}/'
        params = {
            'user_details': True,
            'user_country_details': True,
            'user_profile_description': True,
            'user_reputation': True,
            'user_employer_reputation': True,
            'users[]': ['id', 'username', 'reputation', 'registration_date', 'location']
        }
        
        try:
            print(f"\nDEBUG - User API Request:")
            print(f"Endpoint: {endpoint}")
            print("Headers:", json.dumps(self.headers, indent=2))
            print("Parameters:", json.dumps(params, indent=2))
            
            response = requests.get(endpoint, headers=self.headers, params=params)
            print(f"Response Status: {response.status_code}")
            print(f"Response URL: {response.url}")
            
            if response.status_code != 200:
                print(f"Error Response: {response.text}")
                return {}
            
            data = response.json()
            print("\nDEBUG - API Response:")
            pprint(data)
            
            if 'result' not in data:
                print("No 'result' key in response")
                return {}
            
            return data
            
        except requests.RequestException as e:
            print(f"Request Error: {str(e)}")
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {str(e)}")
            print("Raw Response:", response.text)
            return {}
        except Exception as e:
            print(f"Unexpected Error: {str(e)}")
            return {}

    def get_user_reputation(self, user_id: int) -> Dict:
        endpoint = f'{self.base_url}{config.REPUTATIONS_ENDPOINT}'
        params = {
            'users[]': [user_id],
            'role': 'employer',
            'reputation_extra_details': True,
            'reputation_history': True,
            'jobs_history': True,
            'feedbacks_history': True,
            'profile_description': True
        }
        
        response = requests.get(endpoint, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

def format_time_since(timestamp):
    if not timestamp:
        return "Unknown"
    posted_time = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    delta = now - posted_time
    
    if delta.days > 0:
        return f"{delta.days} days ago"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours} hours ago"
    minutes = (delta.seconds % 3600) // 60
    return f"{minutes} minutes ago"

def get_star_rating(rating):
    if not rating:
        return "No rating"
    full_stars = int(rating)
    stars = "★" * full_stars + "☆" * (5 - full_stars)
    return f"{stars} ({rating:.1f})"

def format_money(amount: float) -> str:
    return f"${amount:,.2f}" if amount else "$0.00"

def format_timestamp(timestamp):
    if not timestamp:
        return "Unknown"
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def main():
    api = FreelancerAPI(config.FREELANCER_API_KEY)
    
    try:
        found_projects = 0
        offset = 0
        
        while found_projects < config.PROJECTS_TO_FIND:
            result = api.get_active_projects(limit=config.DEFAULT_PROJECT_LIMIT)
            
            if 'result' not in result or 'projects' not in result['result']:
                break
                
            projects = result['result']['projects']
            if not projects:
                break
                
            for project in projects:
                owner_id = project.get('owner_id')
                project_id = project.get('id')
                if not owner_id or not project_id:
                    continue
                
                reputation_data = api.get_user_reputation(owner_id)
                if 'result' in reputation_data:
                    rep_result = reputation_data['result']
                    user_rep = rep_result.get(str(owner_id), {})
                    earnings_score = user_rep.get('earnings_score', 0)
                    
                    if earnings_score > config.REQUIRED_EARNINGS_SCORE:
                        found_projects += 1
                        print(f"\n{'='*80}")
                        print(f"Project {found_projects}:")
                        print(f"Title: {project.get('title', 'No Title')}")
                        
                        # URLs
                        print(f"\nLinks:")
                        print(f"Project URL: {config.PROJECT_URL_TEMPLATE.format(project_id)}")
                        print(f"Employer URL: {config.USER_URL_TEMPLATE.format(project.get('owner_username', owner_id))}")
                        
                        # Project Age and Bids
                        print(f"\nPosted: {format_time_since(project.get('submitdate'))}")
                        bid_stats = project.get('bid_stats', {})
                        print(f"Bids: {bid_stats.get('bid_count', 0)}")
                        
                        # Skills
                        skills = project.get('jobs', [])
                        if skills:
                            print("\nRequired Skills:")
                            for skill in skills:
                                print(f"- {skill.get('name', 'Unknown')}")
                        
                        # Employer Stats
                        print("\nEmployer Metrics:")
                        print(f"Earnings Score: {earnings_score:.1f}")
                        entire_history = user_rep.get('entire_history', {})
                        if entire_history:
                            print(f"Overall Rating: {entire_history.get('overall', 0):.1f}")
                            print(f"Complete Projects: {entire_history.get('complete', 0)}")
                            print(f"Total Projects: {entire_history.get('all', 0)}")
                        
                        # Project Description
                        print("\nDescription:")
                        print(project.get('description', 'No description available'))
                        
                        print(f"\n{'='*80}")
                        
                        if found_projects >= config.PROJECTS_TO_FIND:
                            break
            
            if found_projects >= config.PROJECTS_TO_FIND:
                break
                
            offset += config.DEFAULT_PROJECT_LIMIT
            
        print(f"\nFound {found_projects} projects with earnings score > {config.REQUIRED_EARNINGS_SCORE}")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 