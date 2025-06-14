import requests
import json
import os
import logging
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProjectFetcher:
    def __init__(self):
        self.base_url = "https://www.freelancer.com/api/projects/0.1/projects/active"
        self.headers = {
            "Content-Type": "application/json",
            "freelancer-oauth-v1": os.getenv("FREELANCER_API_KEY", "")
        }
        self.country_codes = ["ch"]  # India's country code

    def fetch_projects(self) -> Dict:
        """Fetch active projects with country filter."""
        try:
            params = {
                "limit": 50,  # Fetch 50 projects at once
                "full_description": True,
                "job_details": True,
                "user_details": True
            }
            
            # Add country codes as separate parameters
            for i, code in enumerate(self.country_codes):
                params[f"countries[{i}]"] = code

            print(params)
            
            logger.info(f"Fetching projects for countries: {self.country_codes}")
            
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    projects = data.get("result", {}).get("projects", [])
                    logger.info(f"Successfully fetched {len(projects)} projects")
                    return projects
                else:
                    logger.error(f"API returned error status: {data.get('status')}")
            else:
                logger.error(f"Failed to fetch projects. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
            
            return []
        except Exception as e:
            logger.error(f"Error fetching projects: {str(e)}")
            return []

    def display_projects(self, projects: List[Dict]):
        """Display project details in the console."""
        if not projects:
            print("\nNo projects found.")
            return

        print(f"\nFound {len(projects)} projects:")
        print("-" * 80)
        
        for i, project in enumerate(projects, 1):
            print(f"\nProject {i}:")
            print(f"Title: {project.get('title', 'N/A')}")
            print(f"Description: {project.get('description', 'N/A')[:200]}...")
            print(f"Budget: {project.get('budget', {}).get('minimum', 'N/A')} - {project.get('budget', {}).get('maximum', 'N/A')}")
            print(f"Owner: {project.get('owner', {}).get('username', 'N/A')}")
            print(f"Country: {project.get('owner', {}).get('location', {}).get('country', {}).get('name', 'N/A')}")
            print("-" * 80)

def main():
    fetcher = ProjectFetcher()
    projects = fetcher.fetch_projects()
    fetcher.display_projects(projects)

if __name__ == "__main__":
    main() 