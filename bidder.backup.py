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
import traceback
from typing import Dict, List, Any

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
            # Clear all cache directories
            for subdir in ['projects', 'users', 'reputations', 'openai', 'project_details']:
                self.clear(subdir)
            
            # Clear jobs directory
            jobs_dir = Path('jobs')
            if jobs_dir.exists():
                for file in jobs_dir.glob('*.json'):
                    try:
                        file.unlink()
                        print(f"🗑️ Deleted job file: {file.name}")
                    except Exception as e:
                        print(f"❌ Error deleting job file {file.name}: {str(e)}")
    
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
    def __init__(self, cache_expiry: int = 3600):
        self.conversation_id = "chatcmpl-BDpJQA3iphEQ1bVrfRin9e55MjyV4"
        self.cache = FileCache(cache_dir='cache', expiry=cache_expiry)
        self.max_retries = 3
        self.retry_delay = 5
        
        # Initialize the appropriate API client based on configuration
        if config.AI_PROVIDER == 'chatgpt':
            self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        elif config.AI_PROVIDER == 'deepseek':
            self.client = None  # DeepSeek uses direct HTTP requests
        else:
            raise ValueError(f"Unsupported AI provider: {config.AI_PROVIDER}")

    def _call_ai_api(self, messages):
        """Call the configured AI API (ChatGPT or DeepSeek) and return the response."""
        if config.AI_PROVIDER == 'chatgpt':
            openai.api_key = config.OPENAI_API_KEY
            try:
                response = openai.ChatCompletion.create(
                    model=config.OPENAI_MODEL,
                    messages=messages,
                    temperature=config.OPENAI_TEMPERATURE,
                    max_tokens=config.OPENAI_MAX_TOKENS
                )
                return response.choices[0].message.content.strip()
            except openai.error.AuthenticationError as e:
                print(f"❌ OpenAI API authentication error: {str(e)}")
                raise Exception("OpenAI API authentication failed. Please check your API key.")
            except openai.error.RateLimitError as e:
                print(f"❌ OpenAI API rate limit exceeded: {str(e)}")
                raise Exception("OpenAI API rate limit exceeded. Please try again later.")
            except openai.error.APIError as e:
                print(f"❌ OpenAI API error: {str(e)}")
                raise Exception(f"OpenAI API error: {str(e)}")
            except Exception as e:
                print(f"❌ Unexpected error with OpenAI API: {str(e)}")
                raise Exception(f"Unexpected error with OpenAI API: {str(e)}")

        elif config.AI_PROVIDER == 'deepseek':
            headers = {
                "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": config.DEEPSEEK_MODEL,
                "messages": messages,
                "temperature": config.DEEPSEEK_TEMPERATURE,
                "max_tokens": config.DEEPSEEK_MAX_TOKENS
            }
            
            try:
                response = requests.post(
                    f"{config.DEEPSEEK_API_BASE}/chat/completions",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                
                try:
                    return result["choices"][0]["message"]["content"].strip()
                except (KeyError, IndexError) as e:
                    print(f"Response data: {json.dumps(result, indent=2)}")
                    raise Exception(f"DeepSeek API response missing required field: {str(e)}")
            except requests.exceptions.HTTPError as e:
                print(f"❌ DeepSeek API HTTP error: {str(e)}")
                raise Exception(f"DeepSeek API HTTP error: {str(e)}")
            except requests.exceptions.ConnectionError as e:
                print(f"❌ DeepSeek API connection error: {str(e)}")
                raise Exception("Failed to connect to DeepSeek API. Please check your internet connection.")
            except requests.exceptions.Timeout as e:
                print(f"❌ DeepSeek API timeout error: {str(e)}")
                raise Exception("DeepSeek API request timed out. Please try again.")
            except Exception as e:
                print(f"❌ Unexpected error with DeepSeek API: {str(e)}")
                raise Exception(f"Unexpected error with DeepSeek API: {str(e)}")
        
        else:
            raise ValueError(f"Invalid AI provider configured: {config.AI_PROVIDER}. Must be 'chatgpt' or 'deepseek'.")

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
        
        # Read vyftec-context.md
        try:
            with open('vyftec-context.md', 'r') as file:
                vyftec_context = file.read()
        except Exception as e:
            print(f"Warning: Could not read vyftec-context.md: {str(e)}")
            vyftec_context = ""
        
        # Step 1: Generate score and explanation
        for attempt in range(1, self.max_retries + 1):
            try:
                if progress_bar:
                    project_title = project_data.get('title', 'Untitled Project')
                    if attempt > 1:
                        progress_bar.set_description_str(f"🔄 Retry #{attempt} - Generating score for project ID {project_id}")
                    else:
                        progress_bar.set_description_str(f"🤖 AI: Generating score for project ID {project_id}")
                
                prompt = self._create_ranking_prompt(project_data)
                
                messages = [
                    {
                        "role": "system",
                        "content": """You are an project managere for the web-agency Vyftec that scores software projects for Vyftec based on how well they match the company's expertise."""
                    },
                    {
                        "role": "user",
                        "content": f"""Company Context:\n{vyftec_context}"""
                    },
                    {
                        "role": "user",
                        "content": f"""Project Information:\n{prompt}"""
                    },
                    {
                        "role": "user",
                        "content": """Please return your response in this JSON format:
{
  "score": <int between 0-100>,
  "explanation": <string, 400-800 characters>
}

We will provide project titles, skills required, and descriptions, data about the employer. Your response should include:
- A score (0-100) indicating the project's fit. 
- A score explanation summarizing the key correlations.

Score Calculation

Evaluate the project based on:
Technology Match: Compare required technologies with Vyftec's expertise. Dont consider the selected skills of the employer in the job only the description and title of the project.
Experience Level: Assess if the project suits junior, mid-level, or senior developers.
Regional Fit: Preferably German-speaking projects, with Switzerland as the best match, followed by English-speaking projects.
Industry Fit: Don't consider industries, we provide services to all businesses and industries.

Ensure a realistic evaluation: Do not artificially increase scores. Many projects may not be a good fit, and a low score is acceptable.
Do not consider the project required skills, only the project technologies and skills mentioned in the description and title. Do also not consider
the price of the project as it can be misleading.
Everything that is dashboard, ERP, CRM, etc. is a very good fit also if some technologies dont match."""
                    }
                ]
                
                response_text = self._call_ai_api(messages)
                
                # Parse the response
                try:
                    if not response_text:
                        raise ValueError("Empty response from AI")
                    
                    # Clean the response text by removing any markdown code block indicators
                    response_text = response_text.replace('```json', '').replace('```', '').strip()
                    
                    result = json.loads(response_text)
                    score = result.get('score', 0)
                    explanation = result.get('explanation', '')
                    
                    if not isinstance(score, int) or not 0 <= score <= 100:
                        raise ValueError(f"Invalid score format: {score}")
                    
                    if not explanation or len(explanation) < 100:
                        raise ValueError(f"Invalid explanation format: {explanation[:100]}...")
                    
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error parsing AI response: {str(e)}")
                    print(f"Raw response: {response_text}")
                    raise ValueError(f"Invalid response format: {str(e)}")
                
                result['success'] = True
                result['bid_teaser'] = {}  # Initialize empty bid teaser
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
                        'success': False,
                        'bid_teaser': {}
                    }

    def generate_bid_text(self, project_data: dict, score: int, explanation: str, progress_bar=None) -> dict:
        project_id = project_data.get('project_id', None) or project_data.get('id', 'unknown_id')
        cache_key = f"bid_text_{project_id}"
        
        # Check cache first
        cached_bid = self.cache.get('openai', cache_key)
        if cached_bid:
            if progress_bar:
                progress_bar.set_description_str(f"💾 CACHE: Loading bid text for project ID {project_id}")
            return cached_bid
        
        # Read vyftec-context.md
        try:
            with open('vyftec-context.md', 'r') as file:
                vyftec_context = file.read()
        except Exception as e:
            print(f"Warning: Could not read vyftec-context.md: {str(e)}")
            vyftec_context = ""
        
        if progress_bar:
            progress_bar.set_description_str(f"🤖 AI ({config.AI_PROVIDER}): Generating bid text for project ID {project_id}")
        
        messages = [
            {"role": "system", "content": f"""You are an AI assistant for Vyftec, helping to write high-quality bid teasers for software development projects. You MUST respond in valid JSON format."""},
            {"role": "user", "content": f"""Company Context:\n{vyftec_context}"""},
            {"role": "user", "content": f"""Project Title:\n{project_data.get('title', 'Untitled Project')}"""},
            {"role": "user", "content": f"""Project Description:\n{project_data.get('description', 'No description')}"""},
            {"role": "user", "content": f"""Matching Score: {score}\nMatching Explanation:\n{explanation}"""},
            {"role": "user", "content": """You MUST return your response in this EXACT JSON format, with no additional text before or after:
{
  "bid_teaser": {
    "first_paragraph": "<string, 100-250 characters>",
    "second_paragraph": "<string, 70-180 characters>",
    "third_paragraph": "<string>",
    "question": "<string>"
  }
}

Instructions:
- First Paragraph: Focus on answering direct questions or outlining the solution. Keep it short, logical, and engaging.
- Second Paragraph: Compress the explanation text to 70-180 characters.
- Third Paragraph: Use one of these templates based on project category:
  General: "We develop financial apps, corporate websites, and powerful backends tailored to business needs. ..."
  Websites & Dashboards: "We specialize in creating impressive corporate websites and powerful dashboards ..."
  Finance: "We create cutting-edge financial apps and automated trading systems. ..."
- Question: Ask one clear, contextual question about the project.

Include relevant links in the third paragraph:
Corporate Websites: https://vyftec.com/corporate-websites
Dashboards: https://vyftec.com/dashboards
Financial Apps: https://vyftec.com/financial-apps

IMPORTANT: Your response must be a valid JSON object and nothing else. No markdown, no explanations, just the JSON."""}
        ]
        
        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt > 1:
                    print(f"\n🔄 Retry #{attempt} for generating bid text")
                    if progress_bar:
                        progress_bar.set_description_str(f"🔄 Retry #{attempt} - Generating bid text for project ID {project_id}")
                
                print(f"\n🔍 Debug: Generating bid text with {config.AI_PROVIDER}")
                bid_text = self._call_ai_api(messages)
                
                if not bid_text:
                    raise ValueError(f"Empty bid response from {config.AI_PROVIDER}")
                
                print("\n📝 Raw response from AI:")
                print(bid_text)
                
                # Clean the response text by removing any markdown code block indicators
                bid_text = bid_text.replace('```json', '').replace('```', '').strip()
                
                print("\n🧹 Cleaned response:")
                print(bid_text)
                
                try:
                    bid_result = json.loads(bid_text)
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON Parse Error at position {e.pos}:")
                    print(f"Error message: {str(e)}")
                    # Print the problematic part of the text
                    if e.pos > 20:
                        print(f"Text around error (position {e.pos}):")
                        print(bid_text[e.pos-20:e.pos+20])
                    raise
                
                print("\n🔍 Parsed JSON structure:")
                print(json.dumps(bid_result, indent=2))
                
                # Validate the response structure
                if 'bid_teaser' not in bid_result:
                    raise ValueError("Missing 'bid_teaser' in response")
                
                teaser = bid_result['bid_teaser']
                required_fields = ['first_paragraph', 'second_paragraph', 'third_paragraph', 'question']
                
                print("\n✅ Checking required fields...")
                for field in required_fields:
                    if field not in teaser:
                        raise ValueError(f"Missing required field '{field}' in bid_teaser")
                    if not isinstance(teaser[field], str):
                        raise ValueError(f"Field '{field}' must be a string")
                    if not teaser[field].strip():
                        raise ValueError(f"Field '{field}' cannot be empty")
                    print(f"  ✓ {field}: {len(teaser[field])} characters")
                
                # Validate paragraph lengths
                if not (100 <= len(teaser['first_paragraph']) <= 250):
                    print(f"⚠️ Warning: first_paragraph length ({len(teaser['first_paragraph'])}) outside expected range (100-250)")
                
                if not (70 <= len(teaser['second_paragraph']) <= 180):
                    print(f"⚠️ Warning: second_paragraph length ({len(teaser['second_paragraph'])}) outside expected range (70-180)")
                
                result = {'bid_teaser': teaser}
                self.cache.set('openai', cache_key, result)
                print(f"✅ Successfully generated bid text for project {project_id}")
                return result
                
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in {config.AI_PROVIDER} response: {str(e)}")
                print(f"Raw response: {bid_text}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    continue
                return {'bid_teaser': {}}
                
            except ValueError as e:
                print(f"❌ Validation error: {str(e)}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    continue
                return {'bid_teaser': {}}
                
            except Exception as e:
                print(f"❌ Unexpected error generating bid text: {str(e)}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    continue
                return {'bid_teaser': {}}
        
        return {'bid_teaser': {}}

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

def get_active_projects(limit: int = 20, params=None) -> dict:
    """
    Get active projects from Freelancer API with optional filtering.
    """
    endpoint = f'{config.FL_API_BASE_URL}{config.PROJECTS_ENDPOINT}'
    
    if params is None:
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
            'or_search_query': True,
            'user_country_details': True,
            'languages[]': ['de'],
            'min_employer_rating': 4.0,  # Filter out low-rated employers
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
        print(traceback.format_exc())
        return {'result': {'projects': []}}

def get_user_details(user_id: int, cache: FileCache, failed_users=None) -> dict:
    # Check if we've already failed to fetch this user
    if failed_users and user_id in failed_users:
        print(f"⏭️ Skipping previously failed user {user_id}")
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
        print(f"💾 CACHE: Loading user {user_id} details")
        return cached_user
    
    # If cache miss, try to fetch from API once
    endpoint = f"{config.FL_API_BASE_URL}/users/0.1/users/{user_id}/"
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

def get_user_reputation(user_id: int, cache: FileCache) -> dict:
    cached_reputation = cache.get('reputations', user_id)
    if cached_reputation:
        print(f"💾 CACHE: Loading reputation for user {user_id}")
        return cached_reputation
    
    print(f"🌐 API: Fetching reputation for user {user_id}")
    
    endpoint = f'{config.FL_API_BASE_URL}{config.REPUTATIONS_ENDPOINT}'
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
                print(f"⏳ Rate limited, waiting {retry_delay * (attempt + 1)} seconds...")
                continue
                
            if response.status_code != 200:
                print(f"⚠️ API error (attempt {attempt + 1}/{max_retries}): {response.status_code}")
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
            print(f"❌ Error (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                continue
    
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
    try:
        # Get user input for configuration
        print("\n=== Configuration ===")
        bid_limit = int(input("Enter bid limit (default: 40): ").strip() or "40")
        score_limit = int(input("Enter score limit (default: 50): ").strip() or "50")
        country_check = input("Enable country check? (y/n, default: y): ").strip().lower() != "n"
        scan_scope = input("Scan scope (recent/past, default: recent): ").strip().lower() or "recent"
        
        # Clear cache option at startup
        clear_cache_response = input("Cache löschen vor Start? (j/n): ").strip().lower()
        
        print("Starting project list test...")
        seen_projects = set()  # Track all projects we've seen
        failed_users = set()  # Track users we've failed to fetch
        cache = FileCache(cache_dir='cache', expiry=3600)
        ranker = ProjectRanker()
        
        # Define our expertise/skills with their corresponding job IDs
        our_skills = [
            # Web Development
            {'name': 'PHP', 'id': 3},
            {'name': 'Python', 'id': None},
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
        
        # Process the user's choice to clear cache
        if clear_cache_response in ['j', 'ja', 'y', 'yes']:
            print("🧹 Lösche alle Cache-Dateien...")
            cache.clear()
            print("✅ Cache wurde vollständig geleert.")
        else:
            print("ℹ️ Cache bleibt erhalten.")
        
        try:
            while True:
                # Adjust API parameters based on scan scope
                params = {
                    'limit': 50,
                    'full_description': True,
                    'job_details': True,
                    'user_details': True,
                    'users[]': ['id', 'username', 'reputation', 'country', 'hourly_rate', 'earnings'],
                    'owners[]': ['id', 'username', 'reputation', 'country', 'hourly_rate', 'earnings'],
                    'sort_field': 'time_updated',
                    'sort_direction': 'desc',
                    'project_statuses[]': ['active'],
                    'active_only': True,
                    'project_types[]': ['fixed', 'hourly'],
                    'compact': True,
                    'or_search_query': True,
                    'user_country_details': True,
                    'min_employer_rating': 4.0
                }
                
                # Add timeframe parameter only for recent jobs
                if scan_scope == 'recent':
                    params['timeframe'] = 'last_24_hours'
                
                result = get_active_projects(limit=20, params=params)
                
                if 'result' not in result or 'projects' not in result['result']:
                    print("\nNo projects in response, waiting 1 second...")
                    time.sleep(1)
                    continue
                
                projects = result['result']['projects']
                if not projects:
                    print("\nEmpty projects list, waiting 1 second...")
                    time.sleep(1)
                    continue
                
                new_projects_found = 0
                total_projects = len(projects)
                current_project = 0
                
                # Process all projects
                for project in projects:
                    current_project += 1
                    project_id = project.get('id')
                    if not project_id:
                        continue
                    
                    # Skip if we've already seen this project
                    if project_id in seen_projects:
                        continue
                    
                    print(f"\nProcessing project {current_project}/{total_projects}: {project.get('title', 'No Title')} ({config.PROJECT_URL_TEMPLATE.format(project_id)})")
                    
                    # Check bid count first
                    bid_count = project.get('bid_stats', {}).get('bid_count', 0)
                    if bid_count >= bid_limit:
                        print(f"\033[91m⏭️\033[0m Skipped: Too many bids ({bid_count} >= {bid_limit})")
                        seen_projects.add(project_id)
                        continue
                    
                    # Check country if enabled
                    if country_check:
                        # First check project's country code
                        country_code = project.get('country', '')
                        country = "Unknown"
                        
                        if country_code:
                            if country_code not in config.RICH_COUNTRIES:
                                print(f"\033[93m🌍\033[0m Skipped: Country code {country_code} not in target list")
                                seen_projects.add(project_id)
                                continue
                        else:
                            # No country code found, silently continue to check user details
                            pass
                    
                    # Check if project is already cached
                    cached_project = cache.get('project_details', f"id_{project_id}")
                    is_new_project = cached_project is None
                    
                    if is_new_project:
                        # Get user details first to check country
                        owner_id = project.get('owner_id')
                        user_details = get_user_details(owner_id, cache, failed_users)
                        
                        city = "Unknown"
                        
                        if 'result' in user_details:
                            user_data = user_details['result']
                            location = user_data.get('location', {})
                            if location and 'city' in location:
                                city = location.get('city', 'Unknown')
                            if location and 'country' in location:
                                country = location['country'].get('name', 'Unknown')
                        
                        # Only skip if we have a valid country and it's not in the target list
                        if country_check and country != "Unknown" and country not in config.RICH_COUNTRIES_FULL.values():
                            print(f"\033[93m🌍\033[0m Skipped: Country {country} not in target list")
                            seen_projects.add(project_id)
                            continue

                        # Check if at least one skill matches our skills
                        project_skills = [skill.get('name', '').lower() for skill in project.get('jobs', [])]
                        
                        # Normalize skill names for better matching
                        def normalize_skill(skill):
                            return skill.lower().replace('-', ' ').replace('_', ' ').strip()
                        
                        normalized_project_skills = [normalize_skill(skill) for skill in project_skills]
                        normalized_our_skills = [normalize_skill(skill) for skill in skill_names_lower]
                        
                        # Check for exact matches
                        exact_matches = set(normalized_project_skills) & set(normalized_our_skills)
                        if exact_matches:
                            has_matching_skill = True
                        else:
                            # Check for partial matches (e.g., "javascript" in "javascript developer")
                            has_matching_skill = False
                            for project_skill in normalized_project_skills:
                                for our_skill in normalized_our_skills:
                                    if our_skill in project_skill or project_skill in our_skill:
                                        has_matching_skill = True
                                        break
                                if has_matching_skill:
                                    break
                        
                        if not has_matching_skill:
                            print(f"\033[94m🔧\033[0m Skipped: No matching skills found")
                            seen_projects.add(project_id)
                            continue
                        
                        new_projects_found += 1
                        
                        # Get user reputation
                        reputation_data = get_user_reputation(owner_id, cache)
                        
                        if 'result' not in reputation_data:
                            print(f"\033[95m👤\033[0m Skipped: Failed to fetch reputation data")
                            seen_projects.add(project_id)
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
                        ranking = ranker.rank_project(project_data)
                        
                        if not ranking.get('success', True):
                            print(f"\033[96m🤖\033[0m Skipped: Failed to generate ranking")
                            seen_projects.add(project_id)
                            continue
                        
                        score = ranking['score']
                        
                        # Generate colored ASCII art score
                        score_ascii_art = format_score_with_ascii_art(score)
                        
                        # Create project details for display
                        project_details = f"""
📌 {project.get('title', 'No Title')}
🔗 {config.PROJECT_URL_TEMPLATE.format(project_id)}

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
                            print(f"✅ New Project")
                            print(f"   Score: {score}")
                            print(f"   Location: {city}, {country}")
                            process_ranked_project(project_data, ranking, bid_limit, score_limit)
                        else:
                            print(f"⏭️ Skipped: Score {score} below threshold {score_limit}")
                        
                        seen_projects.add(project_id)
                        continue
                    
                    # Remove the "Project already processed" message
                    continue
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
        except Exception as e:
            print(f"\nError: {str(e)}")
            print(traceback.format_exc())

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 