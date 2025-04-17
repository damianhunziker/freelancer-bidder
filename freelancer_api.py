import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
from pprint import pprint
import config
import openai
import time
from concurrent.futures import ThreadPoolExecutor
import tqdm
import sys
from io import StringIO
import os
import pickle
import hashlib
from pathlib import Path

class FreelancerAPI:
    def __init__(self, api_key: str, cache_expiry: int = 3600):
        self.api_key = api_key
        self.base_url = config.BASE_URL
        self.headers = {
            'Freelancer-OAuth-V1': api_key,
            'Content-Type': 'application/json'
        }
        # Initialize file-based cache
        self.cache = FileCache(cache_dir='cache', expiry=cache_expiry)
        # Ensure jobs directory exists
        self.jobs_dir = Path('jobs')
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def get_active_projects(self, limit: int = config.DEFAULT_PROJECT_LIMIT, 
                            job_ids: List[int] = None, skills: List[str] = None,
                            country_codes: List[str] = None,
                            progress_bar=None) -> Dict:
        """
        Get active projects from Freelancer API with optional filtering.
        
        Args:
            limit: Maximum number of projects to return (default: 20)
            job_ids: List of job category IDs to filter by
            skills: List of skill names to filter by
            country_codes: List of country codes to filter by
            progress_bar: Optional progress bar for status updates
            
        Returns:
            Dict containing the API response with project data
        """
        endpoint = f'{self.base_url}{config.PROJECTS_ENDPOINT}'
        
        # Optimize parameters for speed
        params = {
            'limit': limit,
            'full_description': True,
            'job_details': True,
            'user_details': True,
            'users[]': ['id', 'username', 'reputation', 'country', 'hourly_rate', 'earnings'],
            'owners[]': ['id', 'username', 'reputation', 'country', 'hourly_rate', 'earnings'],
            'sort_field': 'time_updated',
            'sort_direction': 'desc',
            'project_statuses[]': ['active'],
            'active_only': True,
            'project_types[]': ['fixed', 'hourly'],  # Include both fixed and hourly projects
            'compact': True,
            'timeframe': 'last_24_hours',
            'or_search_query': True,
            'user_country_details': True,
            'min_employer_rating': 4.0  # Filter out low-rated employers
        }
        
        # Add job IDs filter if provided
        if job_ids and len(job_ids) > 0:
            params['jobs[]'] = job_ids
        
        # Add skills as space-separated search query if provided
        if skills and len(skills) > 0:
            # Limit to most important skills to reduce query size
            important_skills = skills[:5]  # Use only top 5 skills
            skills_query = " ".join(important_skills)
            params['query'] = skills_query
        
        # Add country codes filter if provided
        if country_codes and len(country_codes) > 0:
            # Prioritize high-value countries
            priority_countries = ['ch', 'us', 'de', 'gb', 'au']  # Top priority countries
            params['countries[]'] = priority_countries
        
        # Always fetch from API, never from cache
        if progress_bar:
            progress_bar.set_description_str("🌐 API: Fetching new projects")
        
        # Make request without any delays or retries
        response = requests.get(endpoint, headers=self.headers, params=params)
        
        if response.status_code == 429:
            raise requests.exceptions.HTTPError("Rate limit exceeded")
            
        response.raise_for_status()
        
        # Still cache individual projects for later reference
        result = response.json()
        if 'result' in result and 'projects' in result['result']:
            for project in result['result']['projects']:
                if 'id' in project:
                    project_id = project['id']
                    self.cache.set('project_details', f"id_{project_id}", project)
        
        return result

    def get_project_by_id(self, project_id: int) -> Dict:
        """Get a single project by ID, using cache if available."""
        # Check cache first
        cached_project = self.cache.get('projects', project_id)
        if cached_project:
            return {'result': {'projects': {str(project_id): cached_project}}}
        
        # If not in cache, fetch from API
        endpoint = f'{self.base_url}{config.PROJECTS_ENDPOINT}/{project_id}/'
        response = requests.get(endpoint, headers=self.headers)
        response.raise_for_status()
        result = response.json()
        
        # Cache the project
        if 'result' in result:
            self.cache.set('projects', project_id, result['result'])
        
        return result

    def get_user_details(self, user_id: int, progress_bar=None) -> Dict:
        """Get user details, using cache if available."""
        # Check cache first
        cached_user = self.cache.get('users', user_id)
        if cached_user:
            if progress_bar:
                progress_bar.set_description_str(f"💾 CACHE: Loading user {user_id} details")
            return cached_user
        
        # If not in cache, fetch from API
        if progress_bar:
            progress_bar.set_description_str(f"🌐 API: Fetching user {user_id} details")
        
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
            response = requests.get(endpoint, headers=self.headers, params=params)
            
            if response.status_code != 200:
                return {}
            
            data = response.json()
            
            if 'result' not in data:
                return {}
            
            # Cache the user data
            self.cache.set('users', user_id, data)
            
            return data
            
        except Exception:
            return {}

    def get_user_reputation(self, user_id: int, progress_bar=None) -> Dict:
        """Get user reputation, using cache if available."""
        # Check cache first
        cached_reputation = self.cache.get('reputations', user_id)
        if cached_reputation:
            if progress_bar:
                progress_bar.set_description_str(f"💾 CACHE: Loading reputation for user {user_id}")
            return cached_reputation
        
        # If not in cache, fetch from API
        if progress_bar:
            progress_bar.set_description_str(f"🌐 API: Fetching reputation for user {user_id}")
        
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
        result = response.json()
        
        # Cache the reputation data
        self.cache.set('reputations', user_id, result)
        
        return result

    def clear_cache(self) -> None:
        """Clear all caches."""
        self.cache.clear()

    def get_cache_stats(self) -> Dict:
        """Get statistics about the cache."""
        return self.cache.get_stats()

    def get_project_details(self, project_id: int) -> Dict:
        """Holt detaillierte Projektdaten mit Cache-Unterstützung"""
        # Prüfe zuerst den Cache
        cached_project = self.cache.get('project_details', project_id)
        if cached_project:
            return cached_project
        
        # Wenn nicht im Cache, hole Projektdetails aus der API
        endpoint = f'{self.base_url}{config.PROJECTS_ENDPOINT}/{project_id}'
        response = requests.get(endpoint, headers=self.headers)
        response.raise_for_status()
        result = response.json()
        
        if 'result' in result:
            # Cache das Ergebnis
            self.cache.set('project_details', project_id, result['result'])
            return result['result']
        
        return {}

    def _clean_filename(self, text):
        """Bereinigt Text für die Verwendung in Dateinamen"""
        if not text:
            return "unknown"
        # Entferne oder ersetze ungültige Zeichen
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']:
            text = text.replace(char, '_')
        return text.lower()

    def save_project_as_json(self, project_data):
        """Save project data as JSON in the json_projects directory."""
        project_id = project_data.get('id', 'unknown')
        file_path = self.json_projects_dir / f"{project_id}.json"
        with open(file_path, 'w') as file:
            json.dump(project_data, file, indent=4)
        print(f"Saved project {project_id} to JSON.")

    def process_project(self, project):
        """Process and optionally save project details based on certain criteria."""
        # Example criterion: project bid count over a limit
        if project.get('bid_stats', {}).get('bid_count', 0) > 50:
            self.save_project_as_json(project)

    def save_job_to_json(self, project_data: Dict, ranking_data: Dict) -> None:
        """
        Save complete job data including project details and ranking to a JSON file
        """
        try:
            project_id = project_data.get('id', 'unknown')
            print(f"\nDebug: Attempting to save job {project_id} to JSON...")
            
            # Generate project URL using the template from config
            project_url = config.PROJECT_URL_TEMPLATE.format(project_id)
            
            # Get employer earnings from project data
            employer_earnings = 0
            if 'owner' in project_data and 'earnings' in project_data['owner']:
                employer_earnings = project_data['owner']['earnings']
            
            # Combine all relevant data
            job_data = {
                'project_details': {
                    **project_data,
                    'employer_earnings_score': employer_earnings
                },
                'ranking': ranking_data,
                'timestamp': datetime.now().isoformat(),
                'bid_score': ranking_data.get('score', 0),
                'bid_text': ranking_data.get('explanation', ''),
                'project_url': project_url,
                'links': {
                    'project': project_url,
                    'employer': config.USER_URL_TEMPLATE.format(project_data.get('owner_username', project_data.get('owner_id', 'unknown')))
                }
            }

            # Create filename with timestamp and project ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"job_{project_id}_{timestamp}.json"
            file_path = self.jobs_dir / filename

            print(f"Debug: Saving to file: {file_path}")
            
            # Save to JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(job_data, f, indent=4, ensure_ascii=False)
            
            print(f"✅ Saved job data for project {project_id} to {filename}")
            
        except Exception as e:
            print(f"❌ Error saving job data for project {project_id}: {str(e)}")
            print(f"Debug: Full error traceback:")
            import traceback
            print(traceback.format_exc())

    def process_ranked_project(self, project_data: Dict, ranking_data: Dict) -> None:
        """
        Process a ranked project and save it if it meets the criteria
        """
        # Add debug logging
        print(f"\nDebug: Processing ranked project...")
        print(f"Debug: Project ID: {project_data.get('id', 'unknown')}")
        print(f"Debug: Score: {ranking_data.get('score', 0)}")
        print(f"Debug: Bid count: {project_data.get('bid_stats', {}).get('bid_count', 0)}")
        print(f"Debug: Has bid text: {bool(ranking_data.get('explanation', '').strip())}")
        
        # Get the score from ranking data
        score = ranking_data.get('score', 0)
        
        # Check if project meets criteria (you can modify these criteria)
        bid_count = project_data.get('bid_stats', {}).get('bid_count', 0)
        has_bid_text = bool(ranking_data.get('explanation', '').strip())
        
        # Define your criteria here
        meets_criteria = (
            score >= config.bidscoreLimit and  # Score is above threshold
            bid_count < 40 and                 # Not too many bids
            has_bid_text                       # Has generated bid text
        )
        
        print(f"Debug: Meets criteria: {meets_criteria}")
        
        if meets_criteria:
            print(f"Debug: Saving job to JSON...")
            self.save_job_to_json(project_data, ranking_data)
        else:
            print(f"Debug: Project did not meet criteria:")
            print(f"  - Score >= {config.bidscoreLimit}: {score >= config.bidscoreLimit}")
            print(f"  - Bid count < 40: {bid_count < 40}")
            print(f"  - Has bid text: {has_bid_text}")

class ProjectRanker:
    def __init__(self, api_key: str, cache_expiry: int = 3600, max_retries: int = 3, retry_delay: int = 5):
        self.client = openai.OpenAI(api_key=api_key)
        self.conversation_id = "chatcmpl-BDpJQA3iphEQ1bVrfRin9e55MjyV4"
        # Initialize file-based cache for OpenAI queries
        self.cache = FileCache(cache_dir='cache', expiry=cache_expiry)
        # Retry settings
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    def rank_project(self, project_data: Dict, progress_bar=None) -> Dict:
        # Extract Projekt-ID
        project_id = project_data.get('project_id', None)
        if project_id is None:
            project_id = project_data.get('id', 'unknown_id')
        
        # Create cache key
        cache_key = f"project_id_{project_id}"
        
        # Check cache first
        cached_ranking = self.cache.get('openai', cache_key)
        if cached_ranking:
            # Don't use cached failed rankings
            if cached_ranking.get('score', 0) == 0 and "failed" in cached_ranking.get('explanation', '').lower():
                if progress_bar:
                    progress_bar.set_description_str(f"🔄 Retrying previously failed ranking for project ID {project_id}")
            else:
                if progress_bar:
                    progress_bar.set_description_str(f"💾 CACHE: Loading AI ranking for project ID {project_id}")
                return cached_ranking
        
        # Implement retry logic
        for attempt in range(1, self.max_retries + 1):
            try:
                if progress_bar:
                    project_title = project_data.get('title', 'Untitled Project')
                    if attempt > 1:
                        progress_bar.set_description_str(f"🔄 Retry #{attempt} - Generating ranking for project ID {project_id}")
                    else:
                        progress_bar.set_description_str(f"🤖 AI: Generating ranking for project ID {project_id}")
                
                prompt = self._create_ranking_prompt(project_data)
                
                # Read the vyftec-context.md content
                with open('vyftec-context.md', 'r') as file:
                    vyftec_context = file.read()
                
                # Use the OpenAI API with a timeout
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": f"""

Your task is to return a score indicating how well a project fits Vyftec's expertise. We will provide project titles and descriptions. Your response should include:

A score (0-100) indicating the project's fit.

A score explanation summarizing the key correlations.

A bid teaser text (if the score exceeds {config.bidscoreLimit}), structured in three paragraphs.

Response Format (JSON)

Return the response in JSON format:

{
  "score": <int>,
  "explanation": "<string>",
  "bid_teaser": {
    "first_paragraph": "<string>",
    "second_paragraph": "<string>",
    "third_paragraph": "<string>"
  }
}

If the score is below {config.bidscoreLimit}, omit the bid_teaser field.

Score Calculation

Evaluate the project based on:

Technology Match: Compare required technologies with Vyftec's expertise (e.g., Laravel, PHP, API integrations, Pine Script, TradingView, etc.).

Experience Level: Assess if the project suits junior, mid-level, or senior developers.

Regional Fit: Preferably German-speaking projects, with Switzerland as the best match, followed by English-speaking projects.

Industry Fit: Determine alignment with Vyftec's focus areas (e.g., web development, trading, API integrations).

Project Complexity: Favor larger, well-paid projects, but highlight particularly well-fitting smaller ones.

Ensure a realistic evaluation: Do not artificially increase scores. Many projects may not be a good fit, and a low score is acceptable.

Score Output

Return a score between 0 and 100, ensuring that single, exchangeable technologies do not overly impact the score. For example, PHP is necessary, but knowledge of a specific API is not, as Vyftec excels at API integrations.
                        
Score Explanation

Provide a concise explanation (up to 200-600 characters, if the score is higher than {config.bidscoreLimit}, the explanation should be longer than 400 signs) detailing the alignment between the project requirements and Vyftec's expertise. If the score is above {config.bidscoreLimit}, include a bid text linking to relevant projects.

Bid Teaser Text

If the score exceeds {config.bidscoreLimit}, generate a 3-paragraph bid teaser text:

First Paragraph: This text is highly important as its the first thing the employer sees. The focus is on answering direct questions of the employer, if there is none: Outline the solution, proposed technologies and approach to solving the problem or fulfilling the project requirements. (100-250 characters)

Second Paragraph: Outline the correlation between the project's requirements and Vyftec's expertise. (70-180 characters)

Third Paragraph: Select one of the following, based on the project category:

Finance: "We create cutting-edge financial apps and automated trading systems. With 20+ years in web development, we deliver robust, scalable solutions for traders and businesses."

Websites & Dashboards: "We specialize in creating impressive corporate websites and powerful dashboards tailored to your business needs. With over 20 years of experience, we build robust, scalable, and user-friendly solutions that drive results."

General: "We develop financial apps, corporate websites, and powerful backends tailored to business needs. With over 20 years of experience, we create robust, scalable, and user-friendly solutions that deliver results."

Always include these links in the third paragraph:

Financial Apps: https://vyftec.com/financial-apps

Corporate Websites: https://vyftec.com/corporate-websites

Dashboards: https://vyftec.com/dashboards

End the third paragraph with a contextual, humorous sign-off, and sign with "Damian."

Here is the context from vyftec-context.md:

                        {vyftec_context}
"""},



                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500,
                    timeout=60  # Set a timeout for the request
                )
                
                result = {
                    'score': self._extract_score(response.choices[0].message.content),
                    'explanation': response.choices[0].message.content,
                    'success': True  # Flag to indicate successful ranking
                }
                
                # Cache the successful result
                self.cache.set('openai', cache_key, result)
                
                return result
                
            except (openai.APITimeoutError, openai.RateLimitError) as e:
                # Handle specific OpenAI API errors
                error_msg = f"OpenAI request failed (attempt {attempt}/{self.max_retries}): {str(e)}"
                if progress_bar:
                    progress_bar.set_description_str(f"⚠️ {error_msg}")
                
                if attempt < self.max_retries:
                    # Wait before retrying (increasing delay with each attempt)
                    time.sleep(self.retry_delay * attempt)
                else:
                    # All retries failed
                    result = {
                        'score': 0,
                        'explanation': f"Ranking failed: {str(e)}",
                        'success': False  # Flag to indicate failed ranking
                    }
                    # Don't cache failed results that we want to retry later
                    return result
                    
            except Exception as e:
                # Handle other exceptions
                error_msg = f"Unexpected error (attempt {attempt}/{self.max_retries}): {str(e)}"
                if progress_bar:
                    progress_bar.set_description_str(f"❌ {error_msg}")
                
                if attempt < self.max_retries:
                    # Wait before retrying
                    time.sleep(self.retry_delay * attempt)
                else:
                    # All retries failed
                    result = {
                        'score': 0,
                        'explanation': f"Ranking failed: {str(e)}",
                        'success': False  # Flag to indicate failed ranking
                    }
                    # Don't cache failed results that we want to retry later
                    return result

    def _clean_filename(self, text):
        """Bereinigt Text für die Verwendung in Dateinamen"""
        # Entferne oder ersetze ungültige Zeichen
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']:
            text = text.replace(char, '_')
        return text.lower()

    def _create_ranking_prompt(self, project_data: Dict) -> str:
        prompt = f"""Please evaluate this Freelancer.com project for Vyftec:

Project Details:
---------------
Title: {project_data.get('title')}
Country: {project_data.get('country', 'Unknown')}
Skills Required: {', '.join(skill.get('name', '') for skill in project_data.get('jobs', []))}

Employer Metrics:
---------------
Earnings Score: {project_data.get('employer_earnings_score', 0)}
Completed Projects: {project_data.get('employer_complete_projects', 0)}
Overall Rating: {project_data.get('employer_overall_rating', 0)}

Market Data:
-----------
Bid Count: {project_data.get('bid_stats', {}).get('bid_count', 0)}

Project Description:
------------------
{project_data.get('description', 'No description available')}

Evaluate this project for Vyftec with a score from 0-100 and detailed explanation in between 200 to 600 signs. If the score is higher than {config.bidscoreLimit}, the explanation should be longer than 400 signs."""

        return prompt

    def _extract_score(self, response_text: str) -> int:
        try:
            import re
            # Look for score patterns like "Score: 85" or "85/100" or "Rating: 85"
            score_patterns = [
                r'Score:\s*(\d{1,3})',
                r'(\d{1,3})/100',
                r'Rating:\s*(\d{1,3})',
                r'Bewertung:\s*(\d{1,3})'
            ]
            
            for pattern in score_patterns:
                matches = re.search(pattern, response_text)
                if matches:
                    score = int(matches.group(1))
                    if 0 <= score <= 100:
                        return score
            
            # Fallback to find any numbers
            scores = re.findall(r'\b([0-9]{1,3})\b', response_text)
            
            for score in scores:
                score = int(score)
                if 0 <= score <= 100:
                    return score
                    
            return 0
            
        except Exception as e:
            return 0

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

def draw_box(content, min_width=80, max_width=150):
    """
    Draws an ASCII frame around the given content with adaptive width and 
    ensures even line widths.
    """
    lines = content.split('\n')
    content_width = max(len(line) for line in lines)

    box_width = max(min_width, min(content_width + 8, max_width))  # +8 for padding (4 on each side)

    horizontal_line = "─" * (box_width - 2)
    empty_line = f"│{' ' * (box_width - 2)}│"

    box = [f"┌{horizontal_line}┐", empty_line]

    for line in lines:
        # Process the line in chunks that fit into the box
        remaining = line
        while remaining:
            chunk_size = box_width - 8  # 4 characters padding on each side

            if len(remaining) <= chunk_size:
                padded_chunk = remaining.ljust(chunk_size)
                box.append(f"│    {padded_chunk}    │")
                remaining = ""
            else:
                breakpoint = remaining[:chunk_size].rfind(' ')
                if breakpoint <= 0 or breakpoint < chunk_size // 2:
                    breakpoint = chunk_size

                chunk = remaining[:breakpoint]
                padded_chunk = chunk.ljust(chunk_size)
                box.append(f"│    {padded_chunk}    │")
                remaining = remaining[breakpoint:].lstrip()

    box.append(empty_line)
    box.append(f"└{horizontal_line}┘")

    return '\n'.join(box)

def get_color_for_score(score):
    """
    Returns ANSI color code based on score (0-100)
    Red (0) -> Yellow (50) -> Green (100)
    """
    if score < 20:
        return "\033[31m"  # Dark Red
    elif score < 40:
        return "\033[91m"  # Red
    elif score < 60:
        return "\033[93m"  # Yellow
    elif score < 80:
        return "\033[92m"  # Light Green
    else:
        return "\033[32m"  # Dark Green

def generate_ascii_art_number(number):
    """
    Generate ASCII art representation of a number
    """
    # Dictionary of ASCII art digits
    ascii_digits = {
        '0': [
            " ██████  ",
            "██    ██ ",
            "██    ██ ",
            "██    ██ ",
            " ██████  "
        ],
        '1': [
            " ██ ",
            "███ ",
            " ██ ",
            " ██ ",
            "████"
        ],
        '2': [
            "██████  ",
            "     ██ ",
            " █████  ",
            "██      ",
            "███████ "
        ],
        '3': [
            "██████  ",
            "     ██ ",
            " █████  ",
            "     ██ ",
            "██████  "
        ],
        '4': [
            "██   ██ ",
            "██   ██ ",
            "███████ ",
            "     ██ ",
            "     ██ "
        ],
        '5': [
            "███████ ",
            "██      ",
            "██████  ",
            "     ██ ",
            "██████  "
        ],
        '6': [
            " ██████  ",
            "██       ",
            "███████  ",
            "██    ██ ",
            " ██████  "
        ],
        '7': [
            "███████ ",
            "     ██ ",
            "    ██  ",
            "   ██   ",
            "  ██    "
        ],
        '8': [
            " ██████  ",
            "██    ██ ",
            " ██████  ",
            "██    ██ ",
            " ██████  "
        ],
        '9': [
            " ██████  ",
            "██    ██ ",
            " ███████ ",
            "      ██ ",
            " ██████  "
        ]
    }

    # Convert number to string and generate ASCII art
    number_str = str(number)
    lines = [""] * 5  # 5 lines for each ASCII art digit
    
    for digit in number_str:
        if digit in ascii_digits:
            for i in range(5):
                lines[i] += ascii_digits[digit][i]
    
    return lines

def format_score_with_ascii_art(score):
    """
    Format a score with colored ASCII art
    """
    color_code = get_color_for_score(score)
    reset_code = "\033[0m"  # Reset color
    
    ascii_art = generate_ascii_art_number(score)
    colored_ascii_art = [f"{color_code}{line}{reset_code}" for line in ascii_art]
    
    return "\n".join(colored_ascii_art)

def display_box_with_progress(content, progress_bar):
    """
    Display a box while maintaining a progress bar at the top
    """
    box = draw_box(content)
    
    # Temporarily clear the progress bar
    progress_bar.clear()
    
    # Display the box without additional print statements
    print(box)
    
    # Restore the progress bar at the top
    progress_bar.refresh()

def update_with_cache_operation(progress_bar, message):
    """
    Updates the progress bar with cache operation details instead of printing
    """
    if progress_bar:
        progress_bar.set_description_str(message)
    # If no progress bar is provided, remain silent (no print)

class FileCache:
    """File-based caching system for API responses with human-readable filenames"""
    
    def __init__(self, cache_dir='cache', expiry=3600):
        """
        Initialize the file cache
        
        Args:
            cache_dir: Directory to store cache files
            expiry: Cache expiry time in seconds
        """
        self.cache_dir = cache_dir
        self.expiry = expiry
        self._ensure_cache_dirs()
    
    def _ensure_cache_dirs(self):
        """Create cache directories if they don't exist"""
        # Create main cache directory
        Path(self.cache_dir).mkdir(exist_ok=True)
        
        # Create subdirectories for different types of data
        for subdir in ['projects', 'users', 'reputations', 'openai', 'project_details']:
            Path(f"{self.cache_dir}/{subdir}").mkdir(exist_ok=True)
    
    def _get_cache_path(self, cache_type, key):
        """Get the file path for a cache item with human-readable names"""
        # Für bessere Lesbarkeit und Debugging
        if isinstance(key, (int, float)):
            # Für numerische Schlüssel (z.B. IDs)
            readable_key = f"id_{key}"
        else:
            # Für String-Schlüssel
            key_str = str(key)
            
            # Entferne oder ersetze ungültige Dateizeichen
            for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']:
                key_str = key_str.replace(char, '_')
            
            # Kürze zu lange Schlüssel
            if len(key_str) > 100:
                # Behalte den Anfang und das Ende, aber kürze die Mitte
                readable_key = f"{key_str[:50]}____{key_str[-45:]}"
            else:
                readable_key = key_str
        
        return f"{self.cache_dir}/{cache_type}/{readable_key}.pkl"
    
    def get(self, cache_type, key):
        """
        Holt ein Element aus dem Cache
        
        Args:
            cache_type: Art des Caches ('projects', 'users', 'reputations', 'openai')
            key: Cache-Schlüssel (normalerweise eine ID)
            
        Returns:
            Das gecachte Element oder None, wenn nicht gefunden oder abgelaufen
        """
        try:
            cache_path = self._get_cache_path(cache_type, key)
            
            if not os.path.exists(cache_path):
                return None
            
            # Datei-Alter prüfen
            file_age = time.time() - os.path.getmtime(cache_path)
            if file_age > self.expiry:
                # Entferne abgelaufene Datei
                os.remove(cache_path)
                return None
            
            # Lese und gib die gecachten Daten zurück
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
                # Flag hinzufügen, dass die Daten aus dem Cache kommen
                if isinstance(data, dict):
                    data['_from_cache'] = True
                    data['_cache_age'] = int(file_age)
                    data['_cache_type'] = cache_type  # Add cache type for better messaging
                    data['_cache_key'] = str(key)     # Add cache key for better messaging
                return data
        except Exception as e:
            # Bei Fehlern Cache-Eintrag ignorieren
            return None
    
    def set(self, cache_type, key, data):
        """
        Store an item in the cache
        
        Args:
            cache_type: Type of cache ('projects', 'users', 'reputations', 'openai')
            key: Cache key (usually an ID)
            data: Data to cache
        """
        cache_path = self._get_cache_path(cache_type, key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except (pickle.PickleError, IOError) as e:
            # Log error but continue execution
            print(f"Cache write error: {str(e)}")
    
    def clear(self, cache_type=None):
        """
        Clear cache files
        
        Args:
            cache_type: Type of cache to clear, or None to clear all
        """
        if cache_type:
            cache_dir = f"{self.cache_dir}/{cache_type}"
            if os.path.exists(cache_dir):
                for file in os.listdir(cache_dir):
                    if file.endswith('.pkl'):
                        os.remove(f"{cache_dir}/{file}")
        else:
            # Add 'project_details' to the list of subdirectories to clear
            for subdir in ['projects', 'users', 'reputations', 'openai', 'project_details']:
                self.clear(subdir)
    
    def get_stats(self):
        """
        Get statistics about the cache
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {}
        
        for cache_type in ['projects', 'users', 'reputations', 'openai']:
            cache_dir = f"{self.cache_dir}/{cache_type}"
            
            # Count all files
            total = 0
            valid = 0
            
            if os.path.exists(cache_dir):
                files = [f for f in os.listdir(cache_dir) if f.endswith('.pkl')]
                total = len(files)
                
                # Count non-expired files
                for file in files:
                    file_path = f"{cache_dir}/{file}"
                    file_age = time.time() - os.path.getmtime(file_path)
                    if file_age <= self.expiry:
                        valid += 1
            
            stats[cache_type] = {
                'total': total,
                'valid': valid
            }
        
        return stats

    def check_cache_health(self):
        """Überprüft den Zustand des Caches und behebt Probleme"""
        issues_found = 0
        
        # Prüfe jedes Cache-Verzeichnis
        for cache_type in ['projects', 'users', 'reputations', 'openai', 'project_details']:
            cache_dir = f"{self.cache_dir}/{cache_type}"
            
            # Stellen Sie sicher, dass das Verzeichnis existiert
            Path(cache_dir).mkdir(exist_ok=True)
            
            if os.path.exists(cache_dir):
                # Prüfen Sie auf beschädigte Cache-Dateien
                files = [f for f in os.listdir(cache_dir) if f.endswith('.pkl')]
                
                for file in files:
                    file_path = f"{cache_dir}/{file}"
                    try:
                        # Versuche die Datei zu öffnen und zu lesen
                        with open(file_path, 'rb') as f:
                            pickle.load(f)
                    except (pickle.PickleError, IOError, EOFError):
                        # Lösche beschädigte Dateien
                        os.remove(file_path)
                        issues_found += 1
        
        return issues_found

def main():
    # Clear cache option at startup
    clear_cache_response = input("Cache löschen vor Start? (j/n): ").strip().lower()
    
    api = FreelancerAPI(config.FREELANCER_API_KEY, cache_expiry=3600)
    ranker = ProjectRanker(config.OPENAI_API_KEY)
    
    # Process the user's choice to clear cache
    if clear_cache_response in ['j', 'ja', 'y', 'yes']:
        print("🧹 Lösche alle Cache-Dateien...")
        api.clear_cache()
        print("✅ Cache wurde vollständig geleert.")
    else:
        print("ℹ️ Cache bleibt erhalten.")
    
    # Define our expertise/skills with their corresponding job IDs
    our_skills = [
        # Web Development
        {'name': 'PHP', 'id': 3},
        {'name': 'Laravel', 'id': 1315},
        {'name': 'Symfony', 'id': 292},
        {'name': 'Vue.js', 'id': 1613},
        {'name': 'React', 'id': 759},
        {'name': 'JavaScript', 'id': 7},
        {'name': 'TypeScript', 'id': 1109},
        {'name': 'HTML', 'id': 20},
        {'name': 'CSS', 'id': 10},
        {'name': 'Bootstrap', 'id': 319},
        {'name': 'Tailwind CSS', 'id': 1698},
        
        # Backend Development
        {'name': 'API Development', 'id': 1103},
        {'name': 'RESTful API', 'id': 1029},
        {'name': 'Backend Development', 'id': 1295},
        {'name': 'Web Services', 'id': 93},
        {'name': 'Database Design', 'id': 583},
        {'name': 'SQL', 'id': 30},
        {'name': 'MySQL', 'id': 13},
        {'name': 'PostgreSQL', 'id': 33},
        {'name': 'MongoDB', 'id': 527},
        
        # Financial Applications
        {'name': 'Financial Software', 'id': 1139},
        {'name': 'Accounting Software', 'id': 320},
        {'name': 'Payment Gateway Integration', 'id': 1241},
        {'name': 'Stripe', 'id': 1402},
        {'name': 'PayPal', 'id': 1050},
        {'name': 'Fintech', 'id': 1597},
        {'name': 'Banking Software', 'id': 1306},
        
        # Dashboard & Analytics
        {'name': 'Dashboard Development', 'id': 1323},
        {'name': 'Data Visualization', 'id': 701},
        {'name': 'Business Intelligence', 'id': 304},
        {'name': 'Analytics', 'id': 1111},
        
        # Corporate Websites
        {'name': 'WordPress', 'id': 17},
        {'name': 'CMS Development', 'id': 1483},
        {'name': 'Corporate Website', 'id': 1264},
        {'name': 'Responsive Design', 'id': 669},
        {'name': 'Web Design', 'id': 9},
        {'name': 'UX/UI Design', 'id': 1424}
    ]
    
    # Extract job IDs and skill names for API request
    skill_ids = [skill['id'] for skill in our_skills]
    skill_names = [skill['name'] for skill in our_skills]
    skill_names_lower = [name.lower() for name in skill_names]
    
    # Define the right countries (high-value markets)
    target_countries = [
        'Switzerland', 'United States', 'Germany', 
        'United Kingdom', 'Canada', 'Australia',
        'Netherlands', 'Sweden', 'Norway', 'Denmark', 
        'Finland', 'Singapore', 'Japan',
        
        'Luxembourg', 'Ireland', 'Austria', 'Belgium',
        'New Zealand', 'France', 'Italy', 'South Korea',
        'Israel', 'United Arab Emirates', 'Qatar', 'Hong Kong',
        'Taiwan', 'Iceland', 'Liechtenstein', 'Monaco',
        'Kuwait', 'Bahrain', 'Saudi Arabia'
    ]
    
    # Map country names to ISO country codes for API filtering
    country_codes_map = {
        'Switzerland': 'ch', 'United States': 'us', 'Germany': 'de',
        'United Kingdom': 'gb', 'Canada': 'ca', 'Australia': 'au',
        'Netherlands': 'nl', 'Sweden': 'se', 'Norway': 'no',
        'Denmark': 'dk', 'Finland': 'fi', 'Singapore': 'sg',
        'Japan': 'jp', 'Luxembourg': 'lu', 'Ireland': 'ie',
        'Austria': 'at', 'Belgium': 'be', 'New Zealand': 'nz',
        'France': 'fr', 'Italy': 'it', 'South Korea': 'kr',
        'Israel': 'il', 'United Arab Emirates': 'ae', 'Qatar': 'qa',
        'Hong Kong': 'hk', 'Taiwan': 'tw', 'Iceland': 'is',
        'Liechtenstein': 'li', 'Monaco': 'mc', 'Kuwait': 'kw',
        'Bahrain': 'bh', 'Saudi Arabia': 'sa'
    }
    
    # Get country codes for API filtering
    country_codes = [country_codes_map.get(country, '') for country in target_countries]
    country_codes = [code for code in country_codes if code]  # Remove empty strings
    
    # Reduced limit for API requests - from 1000 to 200
    batch_limit = 20  # Request only 200 projects per request
    
    try:
        # Cache-Gesundheitscheck durchführen
        cache_issues = api.cache.check_cache_health()
        if cache_issues > 0:
            print(f"🔧 Cache-Probleme behoben: {cache_issues} beschädigte Dateien entfernt")
        
        found_projects = 0
        ranked_projects = []
        seen_project_ids = set()
        total_to_process = batch_limit
        
        # Initialize displayed_projects list to track which projects have been shown
        displayed_projects = []
        
        # Tracking variables for the loop
        search_cycles = 0
        
        # Create the progress bar
        progress = tqdm.tqdm(total=total_to_process, desc="Searching projects", position=0, leave=True)
        
        # Run indefinitely until manually interrupted
        while True:
            search_cycles += 1
            projects_in_this_cycle = 0
            new_projects_in_this_cycle = 0
            
            progress.set_description_str(f"📥 Cycle {search_cycles}: Fetching newest 20 projects")
            
            # Request projects - now limited to 20
            result = api.get_active_projects(
                limit=batch_limit,
                skills=skill_names,
                country_codes=country_codes,
                progress_bar=progress
            )
            
            if 'result' not in result or 'projects' not in result['result']:
                progress.set_description_str(f"❌ No projects in API response")
                continue
                
            projects = result['result']['projects']
            if not projects:
                progress.set_description_str(f"❌ No projects returned")
                continue
            
            # Update total count and progress
            progress.total = len(projects)
            progress.set_description_str(f"🔍 Cycle {search_cycles}: Processing {len(projects)} projects")
            progress.refresh()
            progress.n = 0  # Reset progress bar position
            
            # Process projects in this batch
            for project in projects:
                progress.update(1)
                
                project_id = project.get('id')
                
                # Skip if we've already seen this project
                if project_id in seen_project_ids:
                    progress.set_description_str(f"⏩ Skipping seen project {project_id}")
                    continue
                
                seen_project_ids.add(project_id)
                projects_in_this_cycle += 1
                
                # Check if this project is already cached (directly check project cache)
                cached_project = api.cache.get('project_details', f"id_{project_id}")
                is_new_project = cached_project is None  # Project is new only if not in cache
                
                if is_new_project:
                    progress.set_description_str(f"🔎 Found new project: {project_id}")
                    new_projects_in_this_cycle += 1
                else:
                    progress.set_description_str(f"📂 Project exists in cache: {project_id}")
                    continue  # Skip processing if not new
                
                owner_id = project.get('owner_id')
                title = project.get('title', 'No Title')
                
                # Skip if missing essential project data
                if not project_id or not owner_id:
                    progress.set_description_str(f"⏩ Skipping project: Missing essential data")
                    continue
                
                # Check bid count
                bid_stats = project.get('bid_stats', {})
                bid_count = bid_stats.get('bid_count', 0)
                if bid_count >= 40:
                    progress.set_description_str(f"⏩ Skipping: Too many bids ({bid_count})")
                    continue
                
                # Check project posting time
                submitdate = project.get('submitdate')
                if not submitdate:
                    progress.set_description_str(f"⏩ Skipping: No submission date")
                    continue
                
                # Check if project has required skills
                skills = project.get('jobs', [])
                if not skills:
                    progress.set_description_str(f"⏩ Skipping: No skills specified")
                    continue
                
                # Extracting skills
                project_skill_names = [skill.get('name', 'Unknown') for skill in skills]
                
                # Get user details - update progress bar
                progress.set_description_str(f"👤 Fetching user details for '{title[:30]}...'")
                user_details = api.get_user_details(owner_id, progress_bar=progress)
                
                country = "Unknown"
                city = "Unknown"
                
                if 'result' in user_details:
                    user_data = user_details['result']
                    location = user_data.get('location', {})
                    
                    if location and 'city' in location:
                        city = location.get('city', 'Unknown')
                    
                    if location and 'country' in location:
                        country = location['country'].get('name', 'Unknown')
                
                # Get user reputation - update progress bar
                progress.set_description_str(f"⭐ Fetching reputation for '{title[:30]}...'")
                reputation_data = api.get_user_reputation(owner_id, progress_bar=progress)
                
                if 'result' not in reputation_data:
                    progress.set_description_str(f"⏩ Skipping: No reputation data")
                    continue
                    
                rep_result = reputation_data['result']
                user_rep = rep_result.get(str(owner_id), {})
                earnings_score = user_rep.get('earnings_score', 0)
                
                # Check if employer has an earnings score
                if not earnings_score:
                    progress.set_description_str(f"⏩ Skipping: No earnings score")
                    continue
                
                # Get project budget
                budget_min = project.get('budget', {}).get('minimum', 0)
                budget_max = project.get('budget', {}).get('maximum', 0)
                budget_range = f"${budget_min} - ${budget_max}" if budget_max > budget_min else f"${budget_min}"
                
                # Project passed all filters
                found_projects += 1
                progress.set_description_str(f"✅ Project #{found_projects} passed all filters")
                
                # Prepare project data for ranking
                entire_history = user_rep.get('entire_history', {})
                project_data = {
                    'title': title,
                    'description': project.get('description', 'No description available'),
                    'jobs': skills,
                    'bid_stats': bid_stats,
                    'employer_earnings_score': earnings_score,
                    'employer_complete_projects': entire_history.get('complete', 0),
                    'employer_overall_rating': entire_history.get('overall', 0),
                    'country': country,
                    'id': project_id
                }
                
                # Get project ranking - update progress
                progress.set_description_str(f"🧠 Ranking project '{title[:30]}...'")
                ranking = ranker.rank_project(project_data, progress_bar=progress)
                
                # Check if ranking was successful
                if not ranking.get('success', True):
                    progress.set_description_str(f"⏭️ Skipping project due to failed ranking, will retry later: {project_id}")
                    if project_id in seen_project_ids:
                        seen_project_ids.remove(project_id)
                    continue

                # If we got here, ranking was successful
                score = ranking['score']

                # Add this block here to process and save ranked projects
                if score >= config.bidscoreLimit:
                    progress.set_description_str(f"💾 Saving project with score {score} to jobs folder...")
                    api.process_ranked_project(project_data, ranking)

                # Generate colored ASCII art score
                score_ascii_art = format_score_with_ascii_art(score)

                # Store project with all its data
                ranked_projects.append({
                    'project': project,
                    'ranking': ranking,
                    'user_rep': user_rep,
                    'country': country,
                    'city': city,
                    'matching_skills': project_skill_names,
                    'score': score,
                    'score_ascii_art': score_ascii_art,
                    'title': title,
                    'submitdate': submitdate,
                    'budget_range': budget_range,
                    'bid_count': bid_count,
                    'project_id': project_id,
                    'employer_url': config.USER_URL_TEMPLATE.format(project.get('owner_username', owner_id)),
                    'project_url': config.PROJECT_URL_TEMPLATE.format(project_id),
                    'entire_history': entire_history,
                    'earnings_score': earnings_score,
                    'description': project.get('description', 'Keine Beschreibung verfügbar'),
                    'is_new_project': is_new_project,
                    'is_new_ranking': ranking and isinstance(ranking, dict) and not ranking.get('_from_cache'),
                    'conversation_id': ranker.conversation_id
                })
                
                # Display project box for new projects
                if is_new_project:
                    progress.set_description_str(f"✨ New project with AI ranking! Score: {score}")
                    
                    # Create project details for display
                    project_details = f"""
📌 {title}

┌────────────────────────────────┬────────────────────────────────┬────────────────────────────────┬────────────────────────────────┐
│ 🤖 SCORE:                       │ 🔧 PROJEKT-FÄHIGKEITEN:         │ 💼 ARBEITGEBER:                 │ 🤖 KI-KONTEXT:                 │
│ {score_ascii_art}               │                                │                                │   • Konversation: {ranker.conversation_id} │
│ 💰 BUDGET: {budget_range.ljust(20)} │                                │                                │ 🔗 LINKS:                      │
│                                │                                │                                │   • Projekt: {config.PROJECT_URL_TEMPLATE.format(project_id)} │
│                                │                                │                                │   • Arbeitgeber: {config.USER_URL_TEMPLATE.format(project.get('owner_username', owner_id))} │
├────────────────────────────────┼────────────────────────────────┼────────────────────────────────┼────────────────────────────────┤
│ 🔢 GEBOTE: {str(bid_count).ljust(20)} │                                │ 🌍 STANDORT: {f"{city}, {country}"[:20].ljust(20)} │                                │
"""

                    # Add skills and employer info to the second and third columns
                    skills_text = ""
                    for skill in project_skill_names:
                        skills_text += f"│                                │   • {skill[:24].ljust(24)}  │                                │                                │\n"
                        break  # Show only the first skill with rating in the same line

                    # Add remaining skills
                    for skill in project_skill_names[1:]:
                        skills_text += f"│                                │   • {skill[:24].ljust(24)}  │                                │                                │\n"

                    # Add skills to the main text
                    project_details += skills_text

                    # After adding links and before description, add the conversation ID
                    project_details += f"""└────────────────────────────────┴────────────────────────────────┴────────────────────────────────┴────────────────────────────────┘

📋 BESCHREIBUNG:
{project.get('description', 'Keine Beschreibung verfügbar')}

🤖 KI-BEWERTUNG:
{ranking['explanation']}
"""
                    # Display the box
                    progress.clear()
                    box = draw_box(project_details)
                    print(box)
                    progress.refresh()
                
                # Don't display other projects yet, just update progress
                if found_projects >= config.PROJECTS_TO_FIND:
                    progress.set_description_str(f"✅ Found {found_projects} matching projects")
                    break
            
            # Update cache stats
            cache_stats = api.get_cache_stats()
            progress.set_description_str(f"💾 Cycle {search_cycles}: {len(seen_project_ids)} projects seen, {found_projects} matches")
            
            # Optional: Add longer delay between complete cycles to respect rate limits
            if len(projects) < batch_limit:
                time.sleep(20)  # 20-second delay between full cycles
    
    except KeyboardInterrupt:
        # Handle manual interruption gracefully
        progress.close()
        print("\n\n🛑 Search interrupted by user")
        
        # Still display summary of all found projects
        print("\nAll New Projects Found (Sorted by AI Ranking):")
        
        # Filter for only new projects found in this session
        new_projects = [p for p in ranked_projects if p.get('is_new_project', False)]
        new_projects.sort(key=lambda x: x['score'], reverse=True)
        
        if not new_projects:
            print("No new projects found in this session.")
        else:
            for i, project_data in enumerate(new_projects, 1):
                # Create project details for display
                project_details = f"""
📌 {project_data['title']} - SCORE: {project_data['score']}

{project_data['score_ascii_art']}

┌───────────────────────────────────┬───────────────────────────────────┐
│ ⏱ ALTER: {format_time_since(project_data['submitdate'])} │ 🔢 GEBOTE: {project_data['bid_count']} │
├───────────────────────────────────┼───────────────────────────────────┤
│ 💰 BUDGET: {project_data['budget_range']} │ 🌍 STANDORT: {project_data['city']}, {project_data['country']} │
├───────────────────────────────────┴───────────────────────────────────┤
│ 💼 ARBEITGEBER:                                                       │ 
│   Bewertung: {get_star_rating(project_data['entire_history'].get('overall', 0))}                                         │
│   Abgeschlossene Projekte: {project_data['entire_history'].get('complete', 0)}                                    │
│   Earnings Score: {project_data['earnings_score']:.1f}                                                │
├─────────────────────────────────────────────────────────────────────┤
│ 🔧 PROJEKT-FÄHIGKEITEN:                                               │
│   {', '.join(project_data['matching_skills'])}                                 │
├─────────────────────────────────────────────────────────────────────┤
│ 🔗 LINKS:                                                             │
│   Projekt: {project_data['project_url']}                                        │
│   Arbeitgeber: {project_data['employer_url']}                                    │
├─────────────────────────────────────────────────────────────────────┤
│ 🤖 KI-KONTEXT:                                                         │
│   Konversation: {project_data['conversation_id']}                                      │
└─────────────────────────────────────────────────────────────────────┘

📋 BESCHREIBUNG:
{project_data['description']}

🤖 KI-BEWERTUNG:
{project_data['ranking']['explanation']}
"""
                # Display the box
                print(draw_box(project_details))
                print()
        
        # Bei erfolgreicher Ausführung Cache-Statistiken anzeigen
        cache_stats = api.get_cache_stats()
        print("\nCache-Status nach Abschluss:")
        print(f"- Projekte im Cache: {cache_stats['projects']['valid']}")
        print(f"- Benutzer im Cache: {cache_stats['users']['valid']}")
        print(f"- Reputationsdaten im Cache: {cache_stats['reputations']['valid']}")
        print(f"- OpenAI Bewertungen im Cache: {cache_stats['openai']['valid']}")
        print(f"- Cache-Verzeichnis: {os.path.abspath(api.cache.cache_dir)}")
        
    except Exception as e:
        # Close progress bar on error
        try:
            progress.close()
        except:
            pass
        # Replace tqdm.write with direct print
        print(f"\nError: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 