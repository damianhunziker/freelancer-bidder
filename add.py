import sys
from bidder import ProjectRanker, FileCache, save_job_to_json
import requests
import config
import json

def get_project_details(project_id):
    """Fetch project details from Freelancer API."""
    endpoint = f'{config.FL_API_BASE_URL}/projects/0.1/projects/{project_id}/'
    
    params = {
        'full_description': True,
        'job_details': True,
        'user_details': True,
        'users[]': ['id', 'username', 'reputation', 'country', 'hourly_rate', 'earnings'],
        'owners[]': ['id', 'username', 'reputation', 'country', 'hourly_rate', 'earnings']
    }
    
    headers = {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching project details: {str(e)}")
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python add.py <project_id>")
        print("Example: python add.py 39360013")
        sys.exit(1)
    
    try:
        project_id = int(sys.argv[1])
    except ValueError:
        print("Error: Project ID must be a number")
        sys.exit(1)
    
    print(f"🔍 Fetching project {project_id}...")
    
    # Get project details
    project_data = get_project_details(project_id)
    if not project_data or 'result' not in project_data:
        print("Error: Could not fetch project details")
        sys.exit(1)
    
    project = project_data['result']
    
    # Prepare project data for ranking
    owner_id = project.get('owner_id')
    
    prepared_project = {
        'title': project.get('title', 'No Title'),
        'description': project.get('description', 'No description available'),
        'jobs': project.get('jobs', []),
        'bid_stats': project.get('bid_stats', {}),
        'employer_earnings_score': 0,  # Default values since we're not checking
        'employer_complete_projects': 0,
        'employer_overall_rating': 0,
        'country': project.get('country', 'Unknown'),
        'id': project_id,
        'owner_id': owner_id,
        'owner_username': project.get('owner', {}).get('username', str(owner_id))
    }
    
    # Initialize ranker and rank project
    print("🤖 Ranking project...")
    ranker = ProjectRanker()
    ranking = ranker.rank_project(prepared_project)
    
    if not ranking.get('success', True):
        print("Error: Failed to generate ranking")
        sys.exit(1)
    
    # Save project to JSON
    print("💾 Saving project data...")
    save_job_to_json(prepared_project, ranking)
    
    print(f"\n✅ Project processed successfully!")
    print(f"Score: {ranking.get('score', 0)}")
    print(f"Explanation: {ranking.get('explanation', 'No explanation available')}")

if __name__ == "__main__":
    main() 