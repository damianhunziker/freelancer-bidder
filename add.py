#!/usr/bin/env python3
import sys
import json
import requests
from bidder import ProjectRanker, FileCache, save_job_to_json, get_our_skills, has_matching_skill
import config

def get_project_details(project_id):
    """Get project details from Freelancer API"""
    try:
        endpoint = f'{config.FL_API_BASE_URL}/projects/0.1/projects/{project_id}/'
        params = {
            'job_details': True,
            'jobs': True,
            'full_description': True
        }
        headers = {
            'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching project details: {e}")
        return None

def extract_skills_from_text(text):
    """Extract potential skills from text"""
    if not text:
        return []
    
    # Common skill keywords to look for
    skill_keywords = [
        'wordpress', 'php', 'javascript', 'python', 'laravel', 'react', 'vue',
        'node.js', 'mysql', 'mongodb', 'api', 'web development', 'frontend',
        'backend', 'full stack', 'mobile app', 'ios', 'android', 'flutter',
        'react native', 'aws', 'cloud', 'devops', 'docker', 'kubernetes'
    ]
    
    text_lower = text.lower()
    found_skills = []
    
    for skill in skill_keywords:
        if skill in text_lower:
            found_skills.append(skill)
    
    return found_skills

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
    
    print(f"\n🔍 Fetching details for project {project_id}...")
    
    project_data = get_project_details(project_id)
    if not project_data or 'result' not in project_data:
        print("Failed to fetch project data")
        sys.exit(1)
    
    project = project_data['result']
    
    # Debug: Print raw project data
    print("\n📄 Raw project data:")
    print(json.dumps(project, indent=2))
    
    # Extract project skills
    project_skills = []
    if project.get('jobs'):
        for job in project['jobs']:
            if isinstance(job, dict) and 'name' in job:
                project_skills.append(job['name'])
                print(f"Found skill: {job['name']}")

    print(f"\n📋 Project skills found: {', '.join(project_skills) if project_skills else 'None'}")

    # Get our skills for comparison
    our_skills = get_our_skills()
    print(f"\n🛠️ Our skills loaded: {len(our_skills)} skills")
    print("Our skills list:")
    for skill in our_skills:
        print(f"  • {skill['name']} (ID: {skill['id']})")

    # Check if project has any matching skills
    print("\n🔍 Comparing skills...")
    matches_found = False
    for our_skill in our_skills:
        for project_skill in project_skills:
            if our_skill['name'].lower() == project_skill.lower():
                print(f"✅ Match found: {our_skill['name']} matches {project_skill}")
                matches_found = True

    if not matches_found:
        print("❌ No matching skills found for this project")
        sys.exit(0)

    print("\n✅ Project has matching skills, proceeding with ranking...")
    
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