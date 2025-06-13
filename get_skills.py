import requests
import json
from typing import List, Dict
import os
from datetime import datetime
from config import FREELANCER_API_KEY

class FreelancerSkillsFetcher:
    def __init__(self):
        # Use API key from config.py
        self.api_key = FREELANCER_API_KEY
        if not self.api_key:
            raise ValueError("FREELANCER_API_KEY not found in config.py")
            
        self.base_url = "https://www.freelancer.com/api"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'freelancer-oauth-v1': self.api_key
        })
        
        # Create skills directory if it doesn't exist
        self.skills_dir = "skills"
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir)

    def get_skills(self) -> List[Dict]:
        """
        Fetch all available skills from Freelancer.com
        """
        try:
            endpoint = f"{self.base_url}/common/0.1/skills/"
            response = self.session.get(endpoint)
            response.raise_for_status()
            
            data = response.json()
            if 'result' in data and 'skills' in data['result']:
                return data['result']['skills']
            return []
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching skills: {e}")
            return []

    def save_skills_to_file(self, user_data: Dict):
        """
        Save jobs data to skills/skills.json
        """
        try:
            filepath = os.path.join(self.skills_dir, "skills.json")
            jobs_data = user_data.get('jobs', [])
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(jobs_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Jobs data saved to {filepath}")
        except Exception as e:
            print(f"❌ Error saving jobs data to file: {e}")

    def print_skills_summary(self, skills: List[Dict]):
        """
        Print a summary of the fetched skills
        """
        print("\n📊 Skills Summary:")
        print("=" * 50)
        print(f"Total skills found: {len(skills)}")
        
        # Group skills by category
        categories = {}
        for skill in skills:
            category = skill.get('category', 'Uncategorized')
            if category not in categories:
                categories[category] = []
            categories[category].append(skill.get('name', 'Unknown'))
        
        print("\n📑 Categories:")
        for category, skill_names in categories.items():
            print(f"\n{category} ({len(skill_names)} skills):")
            for name in sorted(skill_names):
                print(f"  • {name}")

    def get_user_info(self, user_id: str) -> Dict:
        """
        Fetch user information from Freelancer.com
        """
        try:
            endpoint = f"{self.base_url}/users/0.1/users/{user_id}/"
            params = {
                'jobs': 'true',
                'skills': 'true'
            }
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            if 'result' in data:
                return data['result']
            return {}
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching user info: {e}")
            return {}

    def print_user_info(self, user_data: Dict):
        """
        Print all user information as received from the API
        """
        if not user_data:
            print("❌ No user data available")
            return

        print("\n👤 Raw User Data:")
        print("=" * 50)
        print(json.dumps(user_data, indent=2, ensure_ascii=False))
        print("=" * 50)

    def get_all_skills(self) -> List[Dict]:
        """
        Fetch all available skills from Freelancer.com
        """
        try:
            endpoint = f"{self.base_url}/common/0.1/skills/"
            params = {
                'limit': 1000  # Get maximum number of skills
            }
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            if 'result' in data and 'skills' in data['result']:
                return data['result']['skills']
            return []
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching skills: {e}")
            return []

    def extract_skills_from_jobs(self, user_data: Dict) -> List[str]:
        """
        Extract unique skills from jobs data
        """
        skills = set()
        if 'jobs' in user_data:
            for job in user_data['jobs']:
                if 'skills' in job:
                    for skill in job['skills']:
                        if isinstance(skill, dict) and 'name' in skill:
                            skills.add(skill['name'])
                        elif isinstance(skill, str):
                            skills.add(skill)
        return sorted(list(skills))

def main():
    try:
        print("🚀 Starting Freelancer.com API Client...")
        fetcher = FreelancerSkillsFetcher()
        
        # Use hardcoded user ID
        user_id = "3953491"
        
        print(f"\n📥 Fetching information for user ID: {user_id}")
        user_data = fetcher.get_user_info(user_id)
        
        if user_data:
            print("✅ Successfully fetched user information")
            fetcher.print_user_info(user_data)
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"freelancer_user_{user_id}_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, ensure_ascii=False)
            print(f"\n✅ User data saved to {filename}")
            
            # Save jobs data to skills/skills.json
            print("\n📥 Saving jobs data...")
            fetcher.save_skills_to_file(user_data)
            if 'jobs' in user_data:
                print(f"📊 Total jobs found: {len(user_data['jobs'])}")
        else:
            print("❌ No user data found or error occurred")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 