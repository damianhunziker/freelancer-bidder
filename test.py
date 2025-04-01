import requests
import json
from datetime import datetime
import config
import time
import openai
import os
import pickle
from pathlib import Path
import tqdm
import random

def format_timestamp(timestamp):
    if not timestamp:
        return "Unknown"
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

class FileCache:
    """File-based caching system for API responses with human-readable filenames"""
    
    def __init__(self, cache_dir='cache', expiry=3600):
        self.cache_dir = cache_dir
        self.expiry = expiry
        self._ensure_cache_dirs()
    
    def _ensure_cache_dirs(self):
        """Create cache directories if they don't exist"""
        Path(self.cache_dir).mkdir(exist_ok=True)
        for subdir in ['projects', 'users', 'reputations', 'openai', 'project_details']:
            Path(f"{self.cache_dir}/{subdir}").mkdir(exist_ok=True)
    
    def _get_cache_path(self, cache_type, key):
        if isinstance(key, (int, float)):
            readable_key = f"id_{key}"
        else:
            key_str = str(key)
            for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']:
                key_str = key_str.replace(char, '_')
            if len(key_str) > 100:
                readable_key = f"{key_str[:50]}____{key_str[-45:]}"
            else:
                readable_key = key_str
        return f"{self.cache_dir}/{cache_type}/{readable_key}.pkl"
    
    def get(self, cache_type, key):
        try:
            cache_path = self._get_cache_path(cache_type, key)
            if not os.path.exists(cache_path):
                return None
            file_age = time.time() - os.path.getmtime(cache_path)
            if file_age > self.expiry:
                os.remove(cache_path)
                return None
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
                if isinstance(data, dict):
                    data['_from_cache'] = True
                    data['_cache_age'] = int(file_age)
                    data['_cache_type'] = cache_type
                    data['_cache_key'] = str(key)
                return data
        except Exception as e:
            return None
    
    def set(self, cache_type, key, data):
        cache_path = self._get_cache_path(cache_type, key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except (pickle.PickleError, IOError) as e:
            print(f"Cache write error: {str(e)}")
    
    def clear(self, cache_type=None):
        if cache_type:
            cache_dir = f"{self.cache_dir}/{cache_type}"
            if os.path.exists(cache_dir):
                for file in os.listdir(cache_dir):
                    if file.endswith('.pkl'):
                        os.remove(f"{cache_dir}/{file}")
        else:
            for subdir in ['projects', 'users', 'reputations', 'openai', 'project_details']:
                self.clear(subdir)
    
    def get_stats(self):
        stats = {}
        for cache_type in ['projects', 'users', 'reputations', 'openai']:
            cache_dir = f"{self.cache_dir}/{cache_type}"
            total = 0
            valid = 0
            if os.path.exists(cache_dir):
                files = [f for f in os.listdir(cache_dir) if f.endswith('.pkl')]
                total = len(files)
                for file in files:
                    file_path = f"{cache_dir}/{file}"
                    file_age = time.time() - os.path.getmtime(file_path)
                    if file_age <= self.expiry:
                        valid += 1
            stats[cache_type] = {'total': total, 'valid': valid}
        return stats

class ProjectRanker:
    def __init__(self, api_key: str, cache_expiry: int = 3600):
        self.client = openai.OpenAI(api_key=api_key)
        self.conversation_id = "chatcmpl-BDpJQA3iphEQ1bVrfRin9e55MjyV4"
        self.cache = FileCache(cache_dir='cache', expiry=cache_expiry)
        self.max_retries = 3
        self.retry_delay = 5

    def rank_project(self, project_data: dict, progress_bar=None) -> dict:
        project_id = project_data.get('project_id', None) or project_data.get('id', 'unknown_id')
        cache_key = f"project_id_{project_id}"
        
        cached_ranking = self.cache.get('openai', cache_key)
        if cached_ranking:
            if cached_ranking.get('score', 0) == 0 and "failed" in cached_ranking.get('explanation', '').lower():
                if progress_bar:
                    progress_bar.set_description_str(f"🔄 Retrying previously failed ranking for project ID {project_id}")
            else:
                if progress_bar:
                    progress_bar.set_description_str(f"💾 CACHE: Loading AI ranking for project ID {project_id}")
                return cached_ranking
        
        for attempt in range(1, self.max_retries + 1):
            try:
                if progress_bar:
                    project_title = project_data.get('title', 'Untitled Project')
                    if attempt > 1:
                        progress_bar.set_description_str(f"🔄 Retry #{attempt} - Generating ranking for project ID {project_id}")
                    else:
                        progress_bar.set_description_str(f"🤖 AI: Generating ranking for project ID {project_id}")
                
                prompt = self._create_ranking_prompt(project_data)
                
                with open('vyftec-context.md', 'r') as file:
                    vyftec_context = file.read()
                
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": f"""Your task is to return a score indicating how well a project fits Vyftec's expertise. We will provide project titles and descriptions. Your response should include:

A score (0-100) indicating the project's fit.

A score explanation summarizing the key correlations.

A bid teaser text (if the score exceeds {config.bidscoreLimit}), structured in three paragraphs and a question. The focus is on meaningful, context-related and pragmatic communication in the first paragraph and the question. During the generation process please always keep that in mind when you encounter important points that can be mentoined in the question or the first paragraph.Dont forget the question! 

Response Format (JSON)

Return the response in JSON format:

{{
  "score": <int>,
  "explanation": "<string>",
  "bid_teaser": {{
    "first_paragraph": "<string>",
    "second_paragraph": "<string>",
    "third_paragraph": "<string>",
    "question": "<string>"
  }}
}}

If the score is below {config.bidscoreLimit}, omit the bid_teaser field.

Score Calculation

Evaluate the project based on:

Technology Match: Compare required technologies with Vyftec's expertise (e.g., Laravel, PHP, API integrations, Pine Script, TradingView, etc.).

Experience Level: Assess if the project suits junior, mid-level, or senior developers.

Regional Fit: Preferably German-speaking projects, with Switzerland as the best match, followed by English-speaking projects.

Industry Fit: Determine alignment with Vyftec's focus areas (e.g., web development, trading, API integrations).

Project Complexity: Favor larger, but highlight particularly well-fitting smaller ones.

Ensure a realistic evaluation: Do not artificially increase scores. Many projects may not be a good fit, and a low score is acceptable.

Do not consider the project required skills, only the project technologies and skills mentioned in the description and title. Do also not consider
the price of the project as it can be misleading.

Score Output

Return a score between 0 and 100, ensuring that single, exchangeable technologies do not overly impact the score. For example, PHP is necessary, but knowledge of a specific API is not, as Vyftec excels at API integrations.
                        
Score Explanation

Provide a concise explanation (100-250 characters) detailing the alignment between the project requirements and Vyftec's expertise.

Bid Teaser Text

If the score exceeds {config.bidscoreLimit}, generate a 3-paragraph bid teaser text:

First Paragraph: Outline the proposed technologies and approach to solving the problem or fulfilling the project requirements. (100-250 characters)

Second Paragraph: Highlight the correlation between the project's requirements and Vyftec's expertise. (70-180 characters)

Third Paragraph: Select one of the following, based on the project category:

Finance: "We create cutting-edge financial apps and automated trading systems. With 20+ years in web development, we deliver robust, scalable solutions for traders and businesses."

Websites & Dashboards: "We specialize in creating impressive corporate websites and powerful dashboards tailored to your business needs. With over 20 years of experience, we build robust, scalable, and user-friendly solutions that drive results."

General: "We develop financial apps, corporate websites, and powerful backends tailored to business needs. With over 20 years of experience, we create robust, scalable, and user-friendly solutions that deliver results."

Always include these links in the third paragraph:

Financial Apps: https://vyftec.com/financial-apps

Corporate Websites: https://vyftec.com/corporate-websites

Dashboards: https://vyftec.com/dashboards

End the third paragraph with a contextual, humorous sign-off, and sign with "Damian."

In the question comes a question that we ask the employer about the project. It might ask about the clarifiation of 
unclear points, what we all need in order to create a binding fixed-price estimation, or asking for confirmation of an 
approach, technologies to use, ways of working, and the like.

Here is the context from vyftec-context.md:

                        {vyftec_context}"""},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500,
                    timeout=60
                )
                
                result = {
                    'score': self._extract_score(response.choices[0].message.content),
                    'explanation': response.choices[0].message.content,
                    'success': True
                }
                
                self.cache.set('openai', cache_key, result)
                return result
                
            except Exception as e:
                if progress_bar:
                    progress_bar.set_description_str(f"❌ Error (attempt {attempt}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                else:
                    return {
                        'score': 0,
                        'explanation': f"Ranking failed: {str(e)}",
                        'success': False
                    }

    def _create_ranking_prompt(self, project_data: dict) -> str:
        return f"""Please evaluate this Freelancer.com project for Vyftec:

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

Evaluate this project for Vyftec with a score from 0-100 and detailed explanation."""

    def _extract_score(self, response_text: str) -> int:
        try:
            import re
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
            
            scores = re.findall(r'\b([0-9]{1,3})\b', response_text)
            for score in scores:
                score = int(score)
                if 0 <= score <= 100:
                    return score
                    
            return 0
            
        except Exception as e:
            return 0

def get_active_projects(limit: int = 20) -> dict:
    """
    Get active projects from Freelancer API with optional filtering.
    """
    endpoint = f'{config.BASE_URL}{config.PROJECTS_ENDPOINT}'
    
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
        'project_types[]': ['fixed'],
        'compact': True,
        'timeframe': 'last_24_hours',
        'or_search_query': True,
        'user_country_details': True,
        'min_budget': 100,
        'max_budget': 10000,
        'min_employer_earnings': 1000,
        'min_employer_rating': 4.0
    }
    
    headers = {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        # Add random timeout between 0.5 and 2 seconds
        timeout = random.uniform(0.5, 2.0)
        time.sleep(timeout)
        
        response = requests.get(endpoint, headers=headers, params=params)
        
        if response.status_code != 200:
            response.raise_for_status()
        
        data = response.json()
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        return {'result': {'projects': []}}
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return {'result': {'projects': []}}
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {'result': {'projects': []}}

def get_user_details(user_id: int, cache: FileCache, progress_bar=None, failed_users=None) -> dict:
    # Check if we've already failed to fetch this user
    if failed_users and user_id in failed_users:
        if progress_bar:
            progress_bar.set_description_str(f"⏭️ Skipping previously failed user {user_id}")
        return {
            'result': {
                'id': user_id,
                'username': None,
                'reputation': None,
                'registration_date': None,
                'location': {
                    'city': None,
                    'country': {
                        'name': None
                    }
                }
            }
        }
    
    # Create default response structure
    default_response = {
        'result': {
            'id': user_id,
            'username': None,
            'reputation': None,
            'registration_date': None,
            'location': {
                'city': None,
                'country': {
                    'name': None
                }
            }
        }
    }
    
    # Check cache first
    cached_user = cache.get('users', user_id)
    if cached_user:
        if progress_bar:
            progress_bar.set_description_str(f"💾 CACHE: Loading user {user_id} details")
        return cached_user
    
    # If cache miss, try to fetch from API once
    if progress_bar:
        progress_bar.set_description_str(f"🌐 API: Fetching user {user_id} details")
    
    endpoint = f'{config.BASE_URL}/users/0.1/users/{user_id}/'
    params = {
        'user_details': True,
        'user_country_details': True,
        'user_profile_description': True,
        'user_reputation': True,
        'user_employer_reputation': True,
        'users[]': ['id', 'username', 'reputation', 'registration_date', 'location']
    }
    
    headers = {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        
        # If request fails, cache and return default response
        if response.status_code != 200:
            if failed_users is not None:
                failed_users.add(user_id)
            cache.set('users', user_id, default_response)
            return default_response
        
        data = response.json()
        if 'result' not in data:
            if failed_users is not None:
                failed_users.add(user_id)
            cache.set('users', user_id, default_response)
            return default_response
        
        # Cache successful response
        cache.set('users', user_id, data)
        return data
        
    except Exception:
        # Cache and return default response on any exception
        if failed_users is not None:
            failed_users.add(user_id)
        cache.set('users', user_id, default_response)
        return default_response

def get_user_reputation(user_id: int, cache: FileCache, progress_bar=None) -> dict:
    cached_reputation = cache.get('reputations', user_id)
    if cached_reputation:
        if progress_bar:
            progress_bar.set_description_str(f"💾 CACHE: Loading reputation for user {user_id}")
        return cached_reputation
    
    if progress_bar:
        progress_bar.set_description_str(f"🌐 API: Fetching reputation for user {user_id}")
    
    endpoint = f'{config.BASE_URL}{config.REPUTATIONS_ENDPOINT}'
    params = {
        'users[]': [user_id],
        'role': 'employer',
        'reputation_extra_details': True,
        'reputation_history': True,
        'jobs_history': True,
        'feedbacks_history': True,
        'profile_description': True
    }
    
    headers = {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            # Add a small delay between requests to avoid rate limiting
            if attempt > 0:
                time.sleep(retry_delay * attempt)
            
            response = requests.get(endpoint, headers=headers, params=params)
            
            if response.status_code == 429:  # Rate limit exceeded
                if progress_bar:
                    progress_bar.set_description_str(f"⏳ Rate limited, waiting {retry_delay * (attempt + 1)} seconds...")
                continue
                
            if response.status_code != 200:
                if progress_bar:
                    progress_bar.set_description_str(f"⚠️ API error (attempt {attempt + 1}/{max_retries}): {response.status_code}")
                if attempt < max_retries - 1:
                    continue
                return {
                    'result': {
                        str(user_id): {
                            'earnings_score': 0,
                            'entire_history': {
                                'complete': 0,
                                'overall': 0
                            }
                        }
                    }
                }
            
            result = response.json()
            cache.set('reputations', user_id, result)
            return result
            
        except Exception as e:
            if progress_bar:
                progress_bar.set_description_str(f"❌ Error (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                continue
            return {
                'result': {
                    str(user_id): {
                        'earnings_score': 0,
                        'entire_history': {
                            'complete': 0,
                            'overall': 0
                        }
                    }
                }
            }
    
    # If we get here, all retries failed
    return {
        'result': {
            str(user_id): {
                'earnings_score': 0,
                'entire_history': {
                    'complete': 0,
                    'overall': 0
                }
            }
        }
    }

def save_job_to_json(project_data: dict, ranking_data: dict) -> None:
    try:
        project_id = project_data.get('id', 'unknown')
        print(f"\nDebug: Attempting to save job {project_id} to JSON...")
        
        project_url = config.PROJECT_URL_TEMPLATE.format(project_id)
        employer_earnings = 0
        if 'owner' in project_data and 'earnings' in project_data['owner']:
            employer_earnings = project_data['owner']['earnings']
        
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

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"job_{project_id}_{timestamp}.json"
        jobs_dir = Path('jobs')
        jobs_dir.mkdir(parents=True, exist_ok=True)
        file_path = jobs_dir / filename

        print(f"Debug: Saving to file: {file_path}")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=4, ensure_ascii=False)
        
        print(f"✅ Saved job data for project {project_id} to {filename}")
        
    except Exception as e:
        print(f"❌ Error saving job data for project {project_id}: {str(e)}")
        print(f"Debug: Full error traceback:")
        import traceback
        print(traceback.format_exc())

def process_ranked_project(project_data: dict, ranking_data: dict, bid_limit: int = 40, score_limit: int = 50) -> None:
    print(f"\nDebug: Processing ranked project...")
    print(f"Debug: Project ID: {project_data.get('id', 'unknown')}")
    print(f"Debug: Score: {ranking_data.get('score', 0)}")
    print(f"Debug: Bid count: {project_data.get('bid_stats', {}).get('bid_count', 0)}")
    print(f"Debug: Has bid text: {bool(ranking_data.get('explanation', '').strip())}")
    
    score = ranking_data.get('score', 0)
    bid_count = project_data.get('bid_stats', {}).get('bid_count', 0)
    has_bid_text = bool(ranking_data.get('explanation', '').strip())
    
    meets_criteria = (
        score >= score_limit and
        bid_count < bid_limit and
        has_bid_text
    )
    
    print(f"Debug: Meets criteria: {meets_criteria}")
    
    if meets_criteria:
        print(f"Debug: Saving job to JSON...")
        save_job_to_json(project_data, ranking_data)
    else:
        print(f"Debug: Project did not meet criteria:")
        print(f"  - Score >= {score_limit}: {score >= score_limit}")
        print(f"  - Bid count < {bid_limit}: {bid_count < bid_limit}")
        print(f"  - Has bid text: {has_bid_text}")

def format_score_with_ascii_art(score):
    def get_color_for_score(score):
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

        number_str = str(number)
        lines = [""] * 5
        
        for digit in number_str:
            if digit in ascii_digits:
                for i in range(5):
                    lines[i] += ascii_digits[digit][i]
        
        return lines

    color_code = get_color_for_score(score)
    reset_code = "\033[0m"
    
    ascii_art = generate_ascii_art_number(score)
    colored_ascii_art = [f"{color_code}{line}{reset_code}" for line in ascii_art]
    
    return "\n".join(colored_ascii_art)

def draw_box(content, min_width=80, max_width=150):
    lines = content.split('\n')
    content_width = max(len(line) for line in lines)
    box_width = max(min_width, min(content_width + 8, max_width))
    horizontal_line = "─" * (box_width - 2)
    empty_line = f"│{' ' * (box_width - 2)}│"
    box = [f"┌{horizontal_line}┐", empty_line]
    
    for line in lines:
        remaining = line
        while remaining:
            chunk_size = box_width - 8
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

def main():
    # Get user input for configuration
    print("\n=== Configuration ===")
    bid_limit = int(input("Enter bid limit (default: 40): ").strip() or "40")
    score_limit = int(input("Enter score limit (default: 50): ").strip() or "50")
    country_check = input("Enable country check? (y/n, default: y): ").strip().lower() != "n"
    
    # Clear cache option at startup
    clear_cache_response = input("Cache löschen vor Start? (j/n): ").strip().lower()
    
    print("Starting project list test...")
    seen_projects = set()  # Track all projects we've seen
    failed_users = set()  # Track users we've failed to fetch
    cache = FileCache(cache_dir='cache', expiry=3600)
    ranker = ProjectRanker(config.OPENAI_API_KEY)
    
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
    
    # Process the user's choice to clear cache
    if clear_cache_response in ['j', 'ja', 'y', 'yes']:
        print("🧹 Lösche alle Cache-Dateien...")
        cache.clear()
        print("✅ Cache wurde vollständig geleert.")
    else:
        print("ℹ️ Cache bleibt erhalten.")
    
    try:
        while True:
            result = get_active_projects(limit=20)
            
            if 'result' not in result or 'projects' not in result['result']:
                print("\nNo projects in response, waiting 1 second...")
                time.sleep(1)
                continue
                
            projects = result['result']['projects']
            if not projects:
                print("\nEmpty projects list, waiting 1 second...")
                time.sleep(1)
                continue
            
            # Create a single progress bar for the entire process
            with tqdm.tqdm(total=len(projects), desc="Processing projects", unit="project", leave=True) as pbar:
                new_projects_found = 0
                
                # Process all projects
                for project in projects:
                    project_id = project.get('id')
                    if not project_id:
                        pbar.update(1)
                        continue
                    
                    # Skip if we've already seen this project
                    if project_id in seen_projects:
                        pbar.update(1)
                        continue
                    
                    # Check bid count first
                    bid_count = project.get('bid_stats', {}).get('bid_count', 0)
                    if bid_count >= bid_limit:
                        print(f"\n⏭️ Skipped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {project.get('title', 'No Title')}")
                        print(f"   Reason: Too many bids ({bid_count} >= {bid_limit})")
                        seen_projects.add(project_id)
                        pbar.update(1)
                        continue
                    
                    # Check country if enabled
                    if country_check:
                        # First check project's country code
                        country_code = project.get('country', '')
                        if country_code:
                            if country_code not in ['CH', 'DE', 'AT', 'US', 'GB', 'CA', 'AU']:
                                print(f"\n⏭️ Skipped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {project.get('title', 'No Title')}")
                                print(f"   Reason: Country code {country_code} not in target list")
                                seen_projects.add(project_id)
                                pbar.update(1)
                                continue
                        else:
                            print(f"\nDebug: No country code found for project: {project.get('title', 'No Title')}")
                    
                    # Check if project is already cached
                    cached_project = cache.get('project_details', f"id_{project_id}")
                    is_new_project = cached_project is None
                    
                    if is_new_project:
                        # Get user details first to check country
                        owner_id = project.get('owner_id')
                        user_details = get_user_details(owner_id, cache, pbar, failed_users)
                        
                        country = "Unknown"
                        city = "Unknown"
                        
                        if 'result' in user_details:
                            user_data = user_details['result']
                            location = user_data.get('location', {})
                            if location and 'city' in location:
                                city = location.get('city', 'Unknown')
                            if location and 'country' in location:
                                country = location['country'].get('name', 'Unknown')
                                print(f"\nDebug: Found country {country} for project: {project.get('title', 'No Title')}")
                        
                        # Skip projects from non-target countries only if country check is enabled
                        if country_check and country not in target_countries:
                            print(f"\n⏭️ Skipped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {project.get('title', 'No Title')}")
                            print(f"   Reason: Country {country} not in target list")
                            seen_projects.add(project_id)
                            pbar.update(1)
                            continue
                        
                        new_projects_found += 1
                        
                        # Get user reputation
                        reputation_data = get_user_reputation(owner_id, cache, pbar)
                        
                        if 'result' not in reputation_data:
                            print(f"\n⏭️ Skipped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {project.get('title', 'No Title')}")
                            print(f"   Reason: Failed to fetch reputation data")
                            seen_projects.add(project_id)
                            pbar.update(1)
                            continue
                            
                        rep_result = reputation_data['result']
                        user_rep = rep_result.get(str(owner_id), {})
                        earnings_score = user_rep.get('earnings_score', 0)
                        
                        # Prepare project data for ranking
                        entire_history = user_rep.get('entire_history', {})
                        project_data = {
                            'title': project.get('title', 'No Title'),
                            'description': project.get('description', 'No description available'),
                            'jobs': project.get('jobs', []),
                            'bid_stats': project.get('bid_stats', {}),
                            'employer_earnings_score': earnings_score,
                            'employer_complete_projects': entire_history.get('complete', 0),
                            'employer_overall_rating': entire_history.get('overall', 0),
                            'country': country,
                            'id': project_id
                        }
                        
                        # Get project ranking
                        ranking = ranker.rank_project(project_data, pbar)
                        
                        if not ranking.get('success', True):
                            print(f"\n⏭️ Skipped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {project.get('title', 'No Title')}")
                            print(f"   Reason: Failed to generate ranking")
                            seen_projects.add(project_id)
                            pbar.update(1)
                            continue
                        
                        score = ranking['score']
                        
                        # Generate colored ASCII art score
                        score_ascii_art = format_score_with_ascii_art(score)
                        
                        # Create project details for display
                        project_details = f"""
📌 {project.get('title', 'No Title')}

┌────────────────────────────────┬────────────────────────────────┬────────────────────────────────┬────────────────────────────────┐
│ 🤖 SCORE:                       │ 🔧 PROJEKT-FÄHIGKEITEN:         │ 💼 ARBEITGEBER:                 │ 🤖 KI-KONTEXT:                 │
│ {score_ascii_art}               │                                │                                │   • Konversation: {ranker.conversation_id} │
│ 💰 BUDGET: ${project.get('budget', {}).get('minimum', 0)} - ${project.get('budget', {}).get('maximum', 0)} │                                │                                │ 🔗 LINKS:                      │
│                                │                                │                                │   • Projekt: {config.PROJECT_URL_TEMPLATE.format(project_id)} │
│                                │                                │                                │   • Arbeitgeber: {config.USER_URL_TEMPLATE.format(project.get('owner_username', owner_id))} │
├────────────────────────────────┼────────────────────────────────┼────────────────────────────────┼────────────────────────────────┤
│ 🔢 GEBOTE: {str(project.get('bid_stats', {}).get('bid_count', 0)).ljust(20)} │                                │ 🌍 STANDORT: {f"{city}, {country}"[:20].ljust(20)} │                                │
"""
                        
                        # Add skills
                        skills_text = ""
                        for skill in project.get('jobs', []):
                            skills_text += f"│                                │   • {skill.get('name', 'Unknown')[:24].ljust(24)}  │                                │                                │\n"
                        
                        project_details += skills_text
                        project_details += f"""└────────────────────────────────┴────────────────────────────────┴────────────────────────────────┴────────────────────────────────┘

📋 BESCHREIBUNG:
{project.get('description', 'Keine Beschreibung verfügbar')}

🤖 KI-BEWERTUNG:
{ranking['explanation']}
"""
                        
                        # Display the box
                        print(draw_box(project_details))
                        
                        # Process and save ranked projects
                        if score >= score_limit:
                            print(f"\n✅ New Project: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {project.get('title', 'No Title')}")
                            print(f"   Score: {score}")
                            print(f"   Location: {city}, {country}")
                            process_ranked_project(project_data, ranking, bid_limit, score_limit)
                        else:
                            print(f"\n⏭️ Skipped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {project.get('title', 'No Title')}")
                            print(f"   Reason: Score {score} below threshold {score_limit}")
                        
                        seen_projects.add(project_id)
                        pbar.update(1)
                        continue
                    
                    # Update progress bar for cached projects
                    pbar.update(1)
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 