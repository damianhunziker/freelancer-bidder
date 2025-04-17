from freelancersdk.session import Session
from freelancersdk.resources.projects import search_projects, get_project_by_id
from freelancersdk.resources.projects.exceptions import ProjectsNotFoundException
from freelancersdk.resources.projects.helpers import create_search_projects_filter
import json
import openai
from pprint import pprint
import config

# Replace the API key assignments with config imports
FREELANCER_API_KEY = config.FREELANCER_API_KEY
OPENAI_API_KEY = config.OPENAI_API_KEY

# Initialize the APIs
openai.api_key = OPENAI_API_KEY
session = Session(
    oauth_token=FREELANCER_API_KEY,
    url='https://www.freelancer-sandbox.com'
)

# Define your bidding style and approach
BID_STYLE_PROMPT = """You are an expert freelance developer specializing in web development, trading bots, and cryptocurrency integration.
Your task is to write compelling project bid proposals. Follow these guidelines:

1. Be professional and confident, but not arrogant
2. Always mention relevant experience specific to the project
3. Address the project requirements directly
4. Include a brief implementation plan
5. Highlight your reliability and communication skills
6. Keep the tone friendly and collaborative
7. Mention your expertise with the specific technologies required
8. Offer a brief timeline estimate if possible
9. End with a call to action

Remember: The goal is to stand out while being genuine and professional."""

def generate_bid_text(project_title, project_description, required_skills, budget_range):
    """Generate a customized bid using GPT-4"""
    prompt = f"""Based on the following project details, write a compelling bid proposal:

Project Title: {project_title}
Description: {project_description or 'No description provided'}
Required Skills: {', '.join(required_skills)}
Budget Range: {budget_range}

Write a bid that demonstrates expertise in these technologies and addresses the project needs specifically."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": BID_STYLE_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating bid: {str(e)}")
        return None

# Define the skills you want to filter by
skills = ['Laravel', 'TradingView', 'Binance']

# Define minimum budget in USD
MIN_BUDGET_USD = 500

try:
    # Get list of active projects
    print("\n=== Fetching Active Project List ===")
    
    total_projects = 0
    offset = 0
    batch_size = 10  # We only want 10 projects
    all_projects = []
    
    search_filter = create_search_projects_filter(
        sort_field='time_updated',
        project_types=['fixed', 'hourly']
    )
    
    result = search_projects(
        session,
        query='',  # Broad search
        search_filter=search_filter,
        limit=batch_size,
        offset=offset,
        project_details={
            'id': True,
            'title': True,
            'description': True,
            'full_description': True,
            'jobs': True,
            'upgrade_details': True,
            'status': True
        }
    )
    
    if not result or 'projects' not in result:
        print("No projects found.")
        exit()
    
    projects = result['projects']
    # Filter for active projects after fetching
    active_projects = [p for p in projects if p.get('status') == 'active']
    all_projects.extend(active_projects)
    total_projects = len(active_projects)
    
    print(f"Fetched {total_projects} active projects.")
    
    # Print details of all active projects
    for project in all_projects:
        title = project.get('title', 'No Title')
        preview_description = project.get('preview_description', 'No preview description available')
        full_description = project.get('full_description', 'No full description available')
        print(f"\nTitle: {title}")
        print(f"Preview Description: {preview_description}")
        print(f"Full Description: {full_description}")
        print("-" * 80)

except Exception as e:
    print(f"Error: {str(e)}")
    print("Type of error:", type(e).__name__)
    import traceback
    print("Traceback:", traceback.format_exc())