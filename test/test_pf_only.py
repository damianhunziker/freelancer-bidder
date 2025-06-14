import requests
import json
import os
import time
from datetime import datetime
import random

# Configuration
FL_API_BASE_URL = "https://www.freelancer.com/api"
PROJECTS_ENDPOINT = "/projects/0.1/projects/active"
API_KEY = os.getenv("FREELANCER_API_KEY", "")

def get_projects(offset=0, limit=100):
    """
    Fetch projects from Freelancer API with pagination
    """
    endpoint = f"{FL_API_BASE_URL}{PROJECTS_ENDPOINT}"
    
    params = {
        'limit': limit,
        'offset': offset,
        'full_description': True,
        'job_details': True,
        'user_details': True,
        'users[]': ['id', 'username', 'reputation', 'country'],
        'owners[]': ['id', 'username', 'reputation', 'country'],
        'sort_field': 'time_updated',
        'sort_direction': 'desc',
        'project_statuses[]': ['active'],
        'active_only': True,
        'project_types[]': ['fixed', 'hourly'],
        'compact': True,
        'or_search_query': True,
        'user_country_details': True,
        'upgrade_details': True,
    }
    
    headers = {
        'Freelancer-OAuth-V1': API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        # Add random timeout between requests
        time.sleep(random.uniform(1.0, 2.0))
        
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching projects: {str(e)}")
        return None

def analyze_pf_only_status(projects):
    """
    Analyze PF-only status for each project
    """
    results = {
        'total_projects': len(projects),
        'pf_only_count': 0,
        'suspicious_projects': []
    }
    
    for project in projects:
        project_id = project.get('id')
        upgrades = project.get('upgrades', {})
        bid_stats = project.get('bid_stats', {})
        
        # Check if project has pf_only upgrade
        is_pf_only = upgrades.get('pf_only', False)
        
        if is_pf_only:
            results['pf_only_count'] += 1
            
            # Save suspicious projects (those marked as PF-only but with public bids)
            if bid_stats.get('bid_count', 0) > 0:
                results['suspicious_projects'].append({
                    'project_id': project_id,
                    'title': project.get('title'),
                    'bid_count': bid_stats.get('bid_count'),
                    'upgrades': upgrades,
                    'raw_response': project
                })
    
    return results

def save_results(results, batch_number):
    """
    Save analysis results to a file
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"pf_only_analysis_{timestamp}_batch_{batch_number}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    return filename

def main():
    print("Starting PF-only analysis...")
    
    total_projects = 0
    total_pf_only = 0
    batch = 1
    offset = 0
    limit = 100
    
    while True:
        print(f"\nFetching batch {batch} (offset: {offset})...")
        
        response = get_projects(offset=offset, limit=limit)
        if not response or 'result' not in response:
            print("Error: Invalid response from API")
            break
            
        projects = response['result'].get('projects', [])
        if not projects:
            print("No more projects found")
            break
            
        # Analyze this batch
        results = analyze_pf_only_status(projects)
        
        # Update totals
        total_projects += results['total_projects']
        total_pf_only += results['pf_only_count']
        
        # Print batch results
        print(f"\nBatch {batch} Results:")
        print(f"Projects analyzed: {results['total_projects']}")
        print(f"PF-only projects: {results['pf_only_count']}")
        print(f"Suspicious projects: {len(results['suspicious_projects'])}")
        
        # Save detailed results if we found suspicious projects
        if results['suspicious_projects']:
            filename = save_results(results, batch)
            print(f"\nDetailed results saved to: {filename}")
            
            # Print suspicious projects
            print("\nSuspicious Projects:")
            for proj in results['suspicious_projects']:
                print(f"\nProject ID: {proj['project_id']}")
                print(f"Title: {proj['title']}")
                print(f"Bid Count: {proj['bid_count']}")
                print(f"PF-only status: {proj['upgrades'].get('pf_only')}")
        
        # Update offset and batch number
        offset += len(projects)
        batch += 1
        
        # Print running totals
        print(f"\nRunning Totals:")
        print(f"Total projects analyzed: {total_projects}")
        print(f"Total PF-only projects: {total_pf_only}")
        print(f"PF-only percentage: {(total_pf_only/total_projects)*100:.2f}%")
        
        # Ask to continue
        if batch % 5 == 0:  # Ask every 5 batches
            response = input("\nContinue fetching? (y/n): ").lower()
            if response != 'y':
                break

if __name__ == "__main__":
    main() 