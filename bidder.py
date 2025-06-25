import requests
import json
from datetime import datetime, timedelta
import config
import time
import openai
import os
import pickle
from pathlib import Path
import tqdm
from tqdm import tqdm as tqdm_bar
import random
import traceback
from typing import Dict, List, Any, Optional, Tuple
import shutil
import subprocess
from rate_limit_manager import is_rate_limited, set_rate_limit_timeout, get_rate_limit_status
from heartbeat_manager import send_heartbeat

SKILLS_CACHE_FILE = '.skills_update_timestamp'
SKILLS_UPDATE_INTERVAL_DAYS = 30
SKILLS_JSON_PATH = os.path.join('skills', 'skills.json')

# Project evaluation logging
def setup_project_evaluation_logs():
    """Setup directory structure for project evaluation logs"""
    api_logs_dir = Path('api_logs')
    api_logs_dir.mkdir(exist_ok=True)
    return api_logs_dir

def log_project_evaluation(project_id: str, project_title: str, status: str, reason: str = "", additional_data: dict = None):
    """Log project evaluation result to JSON file in api_logs folder"""
    try:
        logs_dir = setup_project_evaluation_logs()
        
        # Create filename with current date
        current_date = datetime.now().strftime('%Y%m%d')
        log_file = logs_dir / f'project_evaluations_{current_date}.json'
        
        # Prepare log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'project_id': project_id,
            'project_title': project_title,
            'status': status,  # 'accepted', 'rejected', 'error'
            'reason': reason,
            'additional_data': additional_data or {}
        }
        
        # Read existing logs or create new list
        existing_logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_logs = []
        
        # Append new log entry
        existing_logs.append(log_entry)
        
        # Write back to file
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(existing_logs, f, indent=2, ensure_ascii=False)
            
        print(f"📝 Logged project evaluation: {project_id} - {status}")
        
    except Exception as e:
        print(f"❌ Error logging project evaluation: {str(e)}")

def should_update_skills():
    if not os.path.exists(SKILLS_CACHE_FILE):
        return True
    try:
        with open(SKILLS_CACHE_FILE, 'r') as f:
            last_run = float(f.read().strip())
        last_run_dt = datetime.fromtimestamp(last_run)
        if datetime.now() - last_run_dt > timedelta(days=SKILLS_UPDATE_INTERVAL_DAYS):
            return True
    except Exception:
        return True
    return False

def update_skills():
    print('🔄 Running get_skills.py to update skills...')
    subprocess.run(['python', 'get_skills.py'])
    with open(SKILLS_CACHE_FILE, 'w') as f:
        f.write(str(time.time()))

def ensure_skills_are_updated():
    if should_update_skills():
        update_skills()
    else:
        print('✅ Skills are up to date.')

def load_skills_from_json():
    """Load skills from skills.json and format them for our_skills array"""
    try:
        if not os.path.exists(SKILLS_JSON_PATH):
            print(f"❌ Skills file not found at {SKILLS_JSON_PATH}")
            return []
            
        with open(SKILLS_JSON_PATH, 'r', encoding='utf-8') as f:
            skills_data = json.load(f)
            
        our_skills = []
        for skill in skills_data:
            if isinstance(skill, dict) and 'name' in skill:
                skill_entry = {
                    'name': skill['name'],
                    'id': skill.get('id')  # id might be None, that's okay
                }
                our_skills.append(skill_entry)
                
        print(f"✅ Loaded {len(our_skills)} skills from {SKILLS_JSON_PATH}")
        return our_skills
        
    except Exception as e:
        print(f"❌ Error loading skills from JSON: {str(e)}")
        return []

def get_our_skills():
    """Get our skills array, loading from JSON if not already loaded"""
    global our_skills
    if not our_skills:
        our_skills = load_skills_from_json()
    return our_skills

def has_matching_skill(project_skills):
    """Check if any of the project skills match our skills"""
    if not project_skills:
        return False
        
    our_skills = get_our_skills()
    if not our_skills:
        return False
        
    # Convert project skills to lowercase for case-insensitive comparison
    project_skills_lower = [skill.lower() for skill in project_skills]
    
    # Check if any of our skills match the project skills
    for our_skill in our_skills:
        if our_skill['name'].lower() in project_skills_lower:
            return True
            
    return False

# Ensure skills are updated before proceeding
ensure_skills_are_updated()

# Initialize our_skills as empty, will be loaded when needed
our_skills = []

def sleep_with_progress(duration: float, description: str = "Warten"):
    """Sleep with a tqdm progress bar showing the countdown and heartbeat support"""
    if duration <= 0:
        return
    
    start_time = time.time()
    last_heartbeat = start_time
    
    # Use tqdm to show progress over the sleep duration
    with tqdm_bar(
        total=int(duration * 10),  # Use 0.1 second intervals for smooth progress
        desc=f"⏳ {description}",
        unit="",
        ncols=80,
        bar_format="{l_bar}{bar}| {remaining}s verbleibend"
    ) as pbar:
        for i in range(int(duration * 10)):
            time.sleep(0.1)
            pbar.update(1)
            
            # Send heartbeat every 60 seconds during sleep
            current_time = time.time()
            if current_time - last_heartbeat >= 60:
                try:
                    send_heartbeat('bidder', {
                        'status': 'sleeping',
                        'sleep_description': description,
                        'sleep_duration': duration,
                        'sleep_elapsed': current_time - start_time,
                        'sleep_remaining': duration - (current_time - start_time),
                        'rate_limit_status': 'active' if is_rate_limited() else 'clear'
                    })
                    last_heartbeat = current_time
                except Exception as e:
                    # Don't let heartbeat errors interrupt sleep
                    pass
        
        # Handle any remaining fractional seconds
        remaining = duration - (duration // 0.1) * 0.1
        if remaining > 0:
            time.sleep(remaining)

# High-paying thresholds in USD
LIMIT_HIGH_PAYING_FIXED = 1000  # Projects with average bid >= $1000 are considered high-paying
LIMIT_HIGH_PAYING_HOURLY = 25   # Projects with average hourly rate >= $25/hr are considered high-paying

# Profile configurations
PROFILES = {
    'default': {
        'search_query': '',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'recent',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 0,  # Minimum average fixed price in USD
        'min_hourly': 0   # Minimum average hourly rate in USD
    },    
    'broad_past': {
        'search_query': 'payment, chatgpt, deepeek, api,n8n, PHP, OOP, MVC, Laravel, Composer, SQL, Javascript, Node.js, jQuery, ReactJS, plotly.js, chartJs, HTML5, SCSS, Bootstrap, Typo3, WordPress, Redaxo, Prestashop, Gambio, Linux Console, Git, Pine Script, vue, binance, Bybit, Okx, Crypto, IBKR, brokers, trading, typo3, redaxo, gambio, ccxt, scrape, blockchain, plotly, chartjs',   
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 60,
        'min_hourly': 10
    },    
    'broad_recent': {
        'search_query': 'payment, chatgpt, deepseek, api, n8n, PHP, OOP, MVC, Laravel, Composer, SQL, Javascript, Node.js, jQuery, ReactJS, plotly.js, chartJs, HTML5, SCSS, Bootstrap, Typo3, WordPress, Redaxo, Prestashop, Gambio, Linux Console, Git, Pine Script, vue, binance, Bybit, Okx, Crypto, IBKR, brokers, trading, typo3, redaxo, gambio, ccxt, scrape, blockchain, plotly, chartjs',   
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'recent',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 60,
        'min_hourly': 10
    },    
    'niches_past': {
        'search_query': 'n8n, vue, laravel, binance, Bybit, Okx, Crypto, IBKR, brokers, trading, typo3, redaxo, gambio, ccxt, scrape, blockchain, plotly, chartjs,',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 0,
        'min_hourly': 0
    },    
    'niches_recent': {
        'search_query': 'n8n, vue, laravel, binance, Bybit, Okx, Crypto, IBKR, brokers, trading, typo3, redaxo, gambio, ccxt, scrape, blockchain, plotly, chartjs,',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'recent',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 0,
        'min_hourly': 0
    },
    'high_paying_past': {
        'search_query': '',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': True,
        'clear_cache': False,
        'min_fixed': 500,
        'min_hourly': 20
    },
    'high_paying_recent': {
        'search_query': '',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'recent',
        'high_paying_only': True,
        'clear_cache': False,
        'min_fixed': 500,
        'min_hourly': 20
    },
    'german_past': {
        'search_query': '',
        'project_types': ['fixed','hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': True,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 50,
        'min_hourly': 10
    },
    'german_recent': {
        'search_query': '',
        'project_types': ['fixed','hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': True,
        'scan_scope': 'recent',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 50,
        'min_hourly': 10
    },
    'dach_past': {
        'search_query': '',
        'project_types': ['fixed','hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'g',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 50,
        'min_hourly': 10
    },
    'dach_recent': {
        'search_query': '',
        'project_types': ['fixed','hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'g',
        'german_only': False,
        'scan_scope': 'recent',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 50,
        'min_hourly': 10
    },
    'hourly_only_past': {
        'search_query': '',
        'project_types': ['hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 0,
        'min_hourly': 5
    },
    'hourly_only_recent': {
        'search_query': '',
        'project_types': ['hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'recent',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 0,
        'min_hourly': 5
    },
    'past_projects': {
        'search_query': '',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': False,
        'min_fixed': 50,
        'min_hourly': 10
    },
    'delete_cache': {
        'search_query': 'z23uz23842834234k234',
        'project_types': ['fixed', 'hourly'],
        'bid_limit': 100,
        'score_limit': 50,
        'country_mode': 'y',
        'german_only': False,
        'scan_scope': 'past',
        'high_paying_only': False,
        'clear_cache': True,
        'min_fixed': 0,
        'min_hourly': 0
    }
}

class CurrencyManager:
    def __init__(self, cache_duration: int = 3600):
        self.cache_duration = cache_duration
        self.last_update = None
        self.rates = {
            'USD': 1.0,  # Base currency
            'EUR': 1.08,
            'GBP': 1.27,
            'AUD': 0.66,
            'INR': 0.012,
            'CAD': 0.74,
            'NZD': 0.61,
            'SGD': 0.75,
            'HKD': 0.13,
            'PHP': 0.018
        }
        self.backup_rates = self.rates.copy()
        self.update_rates()

    def update_rates(self) -> Tuple[bool, str]:
        """Update currency rates from API with error handling and backup rates
        Returns: (success: bool, message: str)
        """
        current_time = time.time()
        
        # Skip update if cache is still valid
        if self.last_update and (current_time - self.last_update) < self.cache_duration:
            return True, "Using cached rates"

        try:
            print("\n=== Updating Currency Rates ===")
            response = requests.get('https://open.er-api.com/v6/latest/USD', timeout=10)
        
            if response.status_code == 200:
                data = response.json()
                rates = data.get('rates', {})
                        
                # Verify received rates before updating
                for currency in self.rates.keys():
                    rate = rates.get(currency)
                    if rate and rate > 0:
                        self.rates[currency] = rate
                
                self.last_update = current_time
                self.backup_rates = self.rates.copy()  # Update backup rates
                
                print("Current exchange rates (to USD):")
                for currency, rate in self.rates.items():
                    print(f"{currency}: {rate:.4f}")
                return True, "✅ Currency rates updated successfully"
                    
            return False, f"⚠️ API Error (HTTP {response.status_code}), using previous rates"
            
        except requests.exceptions.Timeout:
            return False, "⚠️ API timeout, using previous rates"
        except requests.exceptions.RequestException as e:
            return False, f"⚠️ API request failed: {str(e)}, using previous rates"
        except Exception as e:
            return False, f"⚠️ Unexpected error: {str(e)}, using previous rates"

    def convert_to_usd(self, amount: float, currency: str, debug: bool = False) -> Optional[float]:
        """Convert amount from given currency to USD with detailed debugging
        Returns: Converted amount or None if conversion fails
        """
        if not amount:
            return 0.0
        
        if currency == 'USD':
            return amount
            
        rate = self.rates.get(currency)
        if rate is None:
            print(f"⚠️ Warning: Unsupported currency {currency}")
            return None
        
        converted = amount * rate
        
        if debug:
            print(f"""
Currency Conversion Details:
  Amount: {amount:.2f} {currency}
  Rate: 1 {currency} = {rate:.4f} USD
  Result: {converted:.2f} USD
  Last Rate Update: {datetime.fromtimestamp(self.last_update).strftime('%Y-%m-%d %H:%M:%S') if self.last_update else 'Never'}
""")
        
        return converted

    def get_rate(self, currency: str) -> Optional[float]:
        """Get current exchange rate for a currency"""
        return self.rates.get(currency)

# Initialize global currency manager
currency_manager = CurrencyManager()

def format_timestamp(timestamp):
    if not timestamp:
        return "Unknown"
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def get_country_code_from_name(country_name: str) -> str:
    """Convert full country name to 2-letter country code"""
    if not country_name:
        return ''
    
    # Create reverse mapping from full names to codes
    name_to_code = {
        'Switzerland': 'ch',
        'Germany': 'de', 
        'Austria': 'at',
        'Liechtenstein': 'li',
        'United States': 'us',
        'United Kingdom': 'gb',
        'France': 'fr',
        'Spain': 'es',
        'Italy': 'it',
        'Netherlands': 'nl',
        'Canada': 'ca',
        'Australia': 'au',
        'India': 'in',
        'Pakistan': 'pk',
        'Bangladesh': 'bd',
        'Ukraine': 'ua',
        'Poland': 'pl',
        'Romania': 'ro',
        'Brazil': 'br',
        'Mexico': 'mx',
        'Argentina': 'ar',
        'Chile': 'cl',
        'Colombia': 'co',
        'Peru': 'pe',
        'South Africa': 'za',
        'Nigeria': 'ng',
        'Egypt': 'eg',
        'Kenya': 'ke',
        'China': 'cn',
        'Japan': 'jp',
        'South Korea': 'kr',
        'Singapore': 'sg',
        'Thailand': 'th',
        'Vietnam': 'vn',
        'Indonesia': 'id',
        'Philippines': 'ph',
        'Malaysia': 'my',
        'Turkey': 'tr',
        'Israel': 'il',
        'United Arab Emirates': 'ae',
        'Saudi Arabia': 'sa',
        'Russia': 'ru',
        'Belarus': 'by',
        'Czech Republic': 'cz',
        'Slovakia': 'sk',
        'Hungary': 'hu',
        'Croatia': 'hr',
        'Serbia': 'rs',
        'Bulgaria': 'bg',
        'Slovenia': 'si',
        'Lithuania': 'lt',
        'Latvia': 'lv',
        'Estonia': 'ee',
        'Finland': 'fi',
        'Sweden': 'se',
        'Norway': 'no',
        'Denmark': 'dk',
        'Iceland': 'is',
        'Ireland': 'ie',
        'Belgium': 'be',
        'Luxembourg': 'lu',
        'Portugal': 'pt',
        'Greece': 'gr',
        'Cyprus': 'cy',
        'Malta': 'mt',
        'New Zealand': 'nz'
    }
    
    return name_to_code.get(country_name, '').lower()

def extract_country_from_project(project: dict) -> tuple[str, str]:
    """
    Extract country information from project data using multiple fallback methods
    Returns: (country_name, country_code)
    """
    try:
        print(f"🔍 Analyzing project data for country information...")
        
        # Method 1: Try owner.location.country from project data (with location_details=true)
        if 'owner' in project and project['owner']:
            owner = project['owner']
            print(f"🔍 Method 1: Checking owner.location...")
            if 'location' in owner and owner['location']:
                location = owner['location']
                if 'country' in location and location['country'] and location['country'].get('name'):
                    country_name = location['country']['name']
                    country_code_raw = location['country'].get('code', '')
                    country_code = country_code_raw.lower() if country_code_raw else ''
                    print(f"🌍 Method 1 - SUCCESS: {country_name} ({country_code})")
                    return country_name, country_code
                else:
                    print(f"🔍 Method 1: owner.location.country is null or empty")
            else:
                print(f"🔍 Method 1: owner.location is null or empty")
        else:
            print(f"🔍 Method 1: owner is null or empty")
        
        # Method 2: Try project.location.country (direct project location)
        print(f"🔍 Method 2: Checking project.location...")
        if 'location' in project and project['location']:
            location = project['location']
            if 'country' in location and location['country'] and location['country'].get('name'):
                country_name = location['country']['name']
                country_code_raw = location['country'].get('code', '')
                country_code = country_code_raw.lower() if country_code_raw else ''
                print(f"🌍 Method 2 - SUCCESS: {country_name} ({country_code})")
                return country_name, country_code
            else:
                print(f"🔍 Method 2: project.location.country is null or empty")
        else:
            print(f"🔍 Method 2: project.location is null or empty")
        
        # Method 3: Try true_location.country (true location if different from display location)
        print(f"🔍 Method 3: Checking true_location...")
        if 'true_location' in project and project['true_location']:
            location = project['true_location']
            if 'country' in location and location['country'] and location['country'].get('name'):
                country_name = location['country']['name']
                country_code_raw = location['country'].get('code', '')
                country_code = country_code_raw.lower() if country_code_raw else ''
                print(f"🌍 Method 3 - SUCCESS: {country_name} ({country_code})")
                return country_name, country_code
            else:
                print(f"🔍 Method 3: true_location.country is null or empty")
        else:
            print(f"🔍 Method 3: true_location is null or empty")
        
        # Method 4: Try direct country field
        print(f"🔍 Method 4: Checking direct country field...")
        if 'country' in project and project['country']:
            if isinstance(project['country'], dict):
                country_name = project['country'].get('name', 'Unknown')
                country_code_raw = project['country'].get('code', '')
                country_code = country_code_raw.lower() if country_code_raw else ''
                if country_name != 'Unknown':
                    print(f"🌍 Method 4 - SUCCESS: {country_name} ({country_code})")
                    return country_name, country_code
            elif isinstance(project['country'], str):
                country_name = project['country']
                country_code = get_country_code_from_name(country_name)
                print(f"🌍 Method 4 - SUCCESS: {country_name} ({country_code})")
                return country_name, country_code
        else:
            print(f"🔍 Method 4: direct country field is null or empty")
        
        print(f"⚠️ All methods failed - no country found in project data")
        return "Unknown", ""
        
    except Exception as e:
        print(f"⚠️ Error extracting country from project: {str(e)}")
        return "Unknown", ""

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

    def detect_authenticity(self, project_data: dict) -> dict:
        """
        Analyze project description to detect if it's authentically written by a human.
        Returns dict with authenticity data.
        """
        print("\n=== Authenticity Detection Debug ===")
        try:
            print("Creating authenticity detection messages...")
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert at detecting AI-generated vs human-written project descriptions on Freelancer.com. 
                    
Key indicators of freelancer.com AI-generated job description:
1. Generic, templated structure with bullet points
2. The first sentence is often more human written.
3. Overly formal and standardized sections like "Key Requirements:" and "Ideal Skills:"
4. Very broad, non-specific requirements
5. Lack of personal context or specific project details
6. Missing technical specifics or implementation details
7. No mention of existing systems, current problems, or specific business context
8. Reads like a generic job posting template
9. Perfect grammar and spelling

Key indicators of authentic human-written content:
1. Contains specific technical details and requirements
2. Mentions existing systems, code, or infrastructure
3. Describes specific business problems or use cases
4. Includes personal context or company-specific information
5. Has natural language variations and potentially typos
6. Contains specific implementation preferences or constraints
7. May include examples of current issues or desired features
8. Often more conversational in tone
9. May include budget discussions or timeline specifics
10. References to specific APIs, libraries, or tools they use
11. Can be short
12. A good sign are grammar and spelling mistakes

Rate the authenticity of project descriptions on a scale of 0-100, where:
0-30: Clearly AI-generated with minimal human input
31-60: Partially AI-generated with some human customization
61-100: Primarily human-written with authentic details

Return your response in this JSON format:
{
  "is_authentic": true/false,
  "authenticity_score": <0-100>,
  "explanation": "Brief explanation of the rating"
}"""
                },
                {
                    "role": "user",
                    "content": f"""Please analyze this project description for authenticity:

Title: {project_data.get('title', '')}

Description:
{project_data.get('description', '')}"""
                }
            ]
            
            print("Calling AI API for authenticity detection...")
            authenticity_response = self._call_ai_api(messages)
            print(f"Raw AI Response: {authenticity_response}")
            
            # Clean the response text by removing markdown code block indicators
            cleaned_response = authenticity_response.replace('```json', '').replace('```', '').strip()
            print(f"Cleaned response: {cleaned_response}")
            
            authenticity_data = json.loads(cleaned_response)
            print(f"Parsed authenticity data: {authenticity_data}")
            
            is_authentic = authenticity_data.get('authenticity_score') >= 65
            authenticity_score = authenticity_data.get('authenticity_score', 0)
            authenticity_explanation = authenticity_data.get('explanation', '')
            
            print(f"\nAuthenticity Analysis Results:")
            print(f"Score: {authenticity_score}")
            print(f"Is Authentic: {is_authentic}")
            print(f"Explanation: {authenticity_explanation}")
            
            return {
                'is_authentic': is_authentic,
                'score': authenticity_score,
                'explanation': authenticity_explanation
            }
            
        except Exception as e:
            print(f"Error in authenticity detection: {str(e)}")
            print(f"Full error traceback:")
            print(traceback.format_exc())
            return {
                'is_authentic': False,
                'score': 0,
                'explanation': f"Failed to analyze authenticity: {str(e)}"
            }

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
        
        # Read vyftec-context.md and lebenslauf.md
        try:
            vyftec_context = ""
            
            # Read vyftec-context.md
            with open('vyftec-context.md', 'r') as file:
                vyftec_context = file.read()
            
            # Read and append lebenslauf.md
            try:
                with open('lebenslauf.md', 'r') as file:
                    lebenslauf_content = file.read()
                    vyftec_context += "\n\n" + lebenslauf_content
            except Exception as e:
                print(f"Warning: Could not read lebenslauf.md: {str(e)}")
                
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
                        "content": """You are a project manager for the web-agency Vyftec that scores software projects based on how well they match the company's expertise."""
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
  "explanation": <string, 400-800 characters>,
  "llm_recog_language": <string, ISO 639-1 language code: "de", "en", "fr", "es", "it", etc.>
}

We provide project titles, skills required, and descriptions, data about the employer and the Vyftec context. Your response should include:
- A score (0-100) indicating the project's fit. 
- A score explanation summarizing the key correlations.
- The detected language of the project description as ISO 639-1 code (e.g., "de" for German, "en" for English, "fr" for French).

# Language Detection

Analyze the project title and description to determine the primary language. Return the ISO 639-1 language code:
- "de" for German (Deutsch)
- "en" for English
- "fr" for French (Français)
- "es" for Spanish (Español)
- "it" for Italian (Italiano)
- "pt" for Portuguese
- "nl" for Dutch
- etc.

# Translation

The explanation text should be in the language of the project description text.

# Score Calculation

Evaluate the project based on:
Technology Match: Compare required technologies, skills and tasks with Vyftec's competencies. Dont consider the selected skills of the employer in the job only the description and title of the project.
Experience Level: Assess if the project suits junior, mid-level, or senior developers.
Regional Fit: Preferably German-speaking projects, with Switzerland as the best match, followed by English-speaking projects.

# Scope 
 
Do not consider the project required skills, only the project technologies and skills mentioned in the description and title. Do also not consider the price of the project as it can be misleading.
Everything that is Website, API, Automation, eCommerce, CMS, web technology, JavaScript, SQL, CSS, WordPress, PHP, Dashboard, ERP, CRM, etc. is a very good fit also if some technologies don't match.

"""
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
                    llm_recog_language = result.get('llm_recog_language', 'unknown')
                    
                    if not isinstance(score, int) or not 0 <= score <= 100:
                        raise ValueError(f"Invalid score format: {score}")
                    
                    if not explanation or len(explanation) < 100:
                        raise ValueError(f"Invalid explanation format: {explanation[:100]}...")
                    
                    if not llm_recog_language or not isinstance(llm_recog_language, str):
                        raise ValueError(f"Invalid language format: {llm_recog_language}")
                    
                    # Normalize language code to lowercase
                    llm_recog_language = llm_recog_language.lower().strip()
                    
                    print(f"🌍 LLM detected language: '{llm_recog_language}' for project {project_data.get('id', 'unknown')}")
                    
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error parsing AI response: {str(e)}")
                    print(f"Raw response: {response_text}")
                    raise ValueError(f"Invalid response format: {str(e)}")
                
                result['success'] = True
                result['bid_teaser'] = {}  # Initialize empty bid teaser
                result['llm_recog_language'] = llm_recog_language
                self.cache.set('openai', cache_key, result)
                return result
                
            except Exception as e:
                if progress_bar:
                    progress_bar.set_description_str(f"❌ Error (attempt {attempt}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries:
                    sleep_with_progress(self.retry_delay * attempt, f"Retry {attempt} nach Fehler")
                else:
                    return {
                        'score': 0,
                        'explanation': f"Ranking failed: {str(e)}",
                        'success': False,
                        'bid_teaser': {}
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

# Initialize global project ranker after class definitions
ranker = ProjectRanker()

def evaluate_project(project_data: dict, selected_profile: dict = None) -> dict:
    """
    Evaluate a single project and return the evaluation results.
    This function can be called from both bidder.py and app.py.
    
    Args:
        project_data (dict): The project data to evaluate
        selected_profile (dict, optional): The profile to use for evaluation. If None, uses default values.
    
    Returns:
        dict: A dictionary containing the evaluation results with the following keys:
            - success (bool): Whether the evaluation was successful
            - score (int): The project score (0-100)
            - ranking_data (dict): The full ranking data including explanation and bid teaser
            - project_data (dict): The processed project data
            - meets_criteria (bool): Whether the project meets all criteria
            - reason (str): If meets_criteria is False, explains why
    """
    try:
        if selected_profile is None:
            selected_profile = {
                'bid_limit': 100,
                'min_fixed': 0,
                'min_hourly': 0,
                'high_paying_only': False
            }

        # Get project ranking
        ranking = ranker.rank_project(project_data)
        
        if not ranking.get('success', True):
            return {
                'success': False,
                'reason': 'Failed to generate ranking'
            }
        
        score = ranking['score']
        project_id = project_data.get('id')
        
        # Check bid count
        bid_count = project_data.get('bid_stats', {}).get('bid_count', 0)
        if bid_count >= selected_profile['bid_limit']:
            return {
                'success': True,
                'score': score,
                'ranking_data': ranking,
                'project_data': project_data,
                'meets_criteria': False,
                'reason': f'Too many bids ({bid_count} >= {selected_profile["bid_limit"]})'
            }
        
        # Check average bid price
        project_type = project_data.get('type', 'fixed')
        currency_info = project_data.get('currency', {'code': 'USD', 'sign': '$'})
        currency_code = currency_info.get('code', 'USD')
        bid_stats = project_data.get('bid_stats', {})
        
        if project_type == 'fixed':
            avg_bid = bid_stats.get('bid_avg', 0)
            avg_bid_usd = currency_manager.convert_to_usd(avg_bid, currency_code)
            min_required = selected_profile['min_fixed']
            
            # If no average bid available, use budget average instead
            if avg_bid == 0:
                budget = project_data.get('budget', {})
                budget_min = budget.get('minimum', 0)
                budget_max = budget.get('maximum', 0)
                if budget_min > 0:
                    if budget_max > 0:
                        # Both min and max available - use average
                        budget_avg = (budget_min + budget_max) / 2
                        budget_avg_usd = currency_manager.convert_to_usd(budget_avg, currency_code)
                        comparison_value = budget_avg_usd
                        comparison_label = f"Budget average (${budget_avg:.2f} {currency_code})"
                    else:
                        # Only minimum available - use minimum
                        budget_min_usd = currency_manager.convert_to_usd(budget_min, currency_code)
                        comparison_value = budget_min_usd
                        comparison_label = f"Budget minimum (${budget_min:.2f} {currency_code})"
                else:
                    comparison_value = 0
                    comparison_label = "No bid data or budget available"
            else:
                comparison_value = avg_bid_usd
                comparison_label = f"Average bid (${avg_bid:.2f} {currency_code})"
            
            if comparison_value < min_required:
                return {
                    'success': True,
                    'score': score,
                    'ranking_data': ranking,
                    'project_data': project_data,
                    'meets_criteria': False,
                    'reason': f'{comparison_label} too low (${comparison_value:.2f} USD < ${min_required} USD)'
                }
        else:  # hourly
            hourly_rate = project_data.get('hourly_rate', 0)
            hourly_rate_usd = currency_manager.convert_to_usd(hourly_rate, currency_code)
            min_required = selected_profile['min_hourly']
            
            # If no hourly rate available, use budget average instead
            if hourly_rate == 0:
                budget = project_data.get('budget', {})
                budget_min = budget.get('minimum', 0)
                budget_max = budget.get('maximum', 0)
                if budget_min > 0:
                    if budget_max > 0:
                        # Both min and max available - use average
                        budget_avg = (budget_min + budget_max) / 2
                        budget_avg_usd = currency_manager.convert_to_usd(budget_avg, currency_code)
                        comparison_value = budget_avg_usd
                        comparison_label = f"Budget average (${budget_avg:.2f} {currency_code}/hr)"
                    else:
                        # Only minimum available - use minimum
                        budget_min_usd = currency_manager.convert_to_usd(budget_min, currency_code)
                        comparison_value = budget_min_usd
                        comparison_label = f"Budget minimum (${budget_min:.2f} {currency_code}/hr)"
                else:
                    comparison_value = 0
                    comparison_label = "No hourly rate or budget available"
            else:
                comparison_value = hourly_rate_usd
                comparison_label = f"Hourly rate (${hourly_rate:.2f} {currency_code}/hr)"
            
            if comparison_value < min_required:
                return {
                    'success': True,
                    'score': score,
                    'ranking_data': ranking,
                    'project_data': project_data,
                    'meets_criteria': False,
                    'reason': f'{comparison_label} too low (${comparison_value:.2f} USD/hr < ${min_required} USD/hr)'
                }
        
        # Check for high-paying jobs if enabled
        if selected_profile['high_paying_only']:
            if project_type == 'fixed':
                budget_min = project_data.get('budget', {}).get('minimum', 0)
                budget_max = project_data.get('budget', {}).get('maximum', 0)
                budget_min_usd = currency_manager.convert_to_usd(budget_min, currency_code)
                budget_max_usd = currency_manager.convert_to_usd(budget_max, currency_code)
                
                if budget_max_usd < LIMIT_HIGH_PAYING_FIXED:
                    return {
                        'success': True,
                        'score': score,
                        'ranking_data': ranking,
                        'project_data': project_data,
                        'meets_criteria': False,
                        'reason': f'Budget too low (${budget_max_usd:.2f} USD < ${LIMIT_HIGH_PAYING_FIXED})'
                    }
            else:  # hourly
                hourly_rate = project_data.get('hourly_rate', 0)
                hourly_rate_usd = currency_manager.convert_to_usd(hourly_rate, currency_code)
                
                if hourly_rate_usd < LIMIT_HIGH_PAYING_HOURLY:
                    return {
                        'success': True,
                        'score': score,
                        'ranking_data': ranking,
                        'project_data': project_data,
                        'meets_criteria': False,
                        'reason': f'Hourly rate too low (${hourly_rate_usd:.2f} USD/hr < ${LIMIT_HIGH_PAYING_HOURLY})'
                    }
        
        # If we get here, the project meets all criteria
        return {
            'success': True,
            'score': score,
            'ranking_data': ranking,
            'project_data': project_data,
            'meets_criteria': True,
            'reason': 'Project meets all criteria'
        }
        
    except Exception as e:
        print(f"❌ Error evaluating project: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'reason': f'Error evaluating project: {str(e)}'
        }

def process_ranked_project(project_data: dict, ranking_data: dict, bid_limit: int = 40, score_limit: int = 50) -> None:
    """Process and display a ranked project with enhanced currency debugging"""
    try:
        project_type = project_data.get('type', 'unknown')
        currency_info = project_data.get('currency', {})
        currency_code = currency_info.get('code', 'USD') if isinstance(currency_info, dict) else 'USD'
        
        # Get bid statistics with currency conversion
        bid_stats = project_data.get('bid_stats', {})
        avg_bid = bid_stats.get('bid_avg', 0)
        avg_bid_usd = currency_manager.convert_to_usd(avg_bid, currency_code)
        
        if project_type == 'fixed':
            budget = project_data.get('budget', {})
            budget_min = budget.get('minimum', 0)
            budget_max = budget.get('maximum', 0)
            
            budget_min_usd = currency_manager.convert_to_usd(budget_min, currency_code)
            budget_max_usd = currency_manager.convert_to_usd(budget_max, currency_code)
        else:  # hourly
            hourly_rate = project_data.get('hourly_rate', 0)
            hourly_rate_usd = currency_manager.convert_to_usd(hourly_rate, currency_code)
        
        # Check if currency conversion was successful
        if any(val is None for val in [avg_bid_usd, budget_min_usd if project_type == 'fixed' else hourly_rate_usd]):
            print(f"⚠️ Warning: Currency conversion failed for some values ({currency_code})")
            return

        # Save the project data to JSON
        save_job_to_json(project_data, ranking_data)

    except Exception as e:
        print(f"❌ Error processing ranked project: {str(e)}")
        print(traceback.format_exc())

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

def draw_box(content, min_width=80, max_width=150, is_high_paying=False, is_german=False, is_corr=False, is_rep=False):
    # ANSI color codes
    colors = {
        'reset': '\033[0m',
        'high_paying': '\033[38;5;208m',  # Orange
        'german': '\033[38;5;34m',        # Green
        'corr': '\033[38;5;196m',         # Red
        'rep': '\033[38;5;129m',          # Purple
        'qual': '\033[38;5;208m',         # Orange
        'pay': '\033[38;5;34m',           # Green
        'get': '\033[38;5;196m',          # Red
        'urg': '\033[38;5;208m'           # Orange
    }
    
    # Background colors
    bg_colors = {
        'high_paying': '\033[48;5;208m',  # Orange background
        'german': '\033[48;5;34m',        # Green background
        'corr': '\033[48;5;196m',         # Red background
        'rep': '\033[48;5;129m',          # Purple background
        'qual': '\033[48;5;208m',         # Orange background
        'pay': '\033[48;5;34m',           # Green background
        'get': '\033[48;5;196m',          # Red background
        'urg': '\033[48;5;208m'           # Orange background
    }
    
    # Create tags
    tags = []
    if is_high_paying:
        tags.append(f"{bg_colors['high_paying']}🤖 HIGH PAYING{colors['reset']}")
    if is_german:
        tags.append(f"{bg_colors['german']}🇩🇪 GERMAN{colors['reset']}")
    if is_corr:
        tags.append(f"{bg_colors['corr']}📝 CORR{colors['reset']}")
    if is_rep:
        tags.append(f"{bg_colors['rep']}👥 REP{colors['reset']}")
    
    # Add automatic bidding tags
    tags.extend([
        f"{bg_colors['qual']}🎯 QUAL{colors['reset']}",
        f"{bg_colors['pay']}💰 PAY{colors['reset']}",
        f"{bg_colors['get']}🎯 GET{colors['reset']}",
        f"{bg_colors['urg']}⚡ URG{colors['reset']}"
    ])
    
    # Join tags with spaces
    tag_line = " ".join(tags)
    
    # Calculate box width
    content_width = max(len(line) for line in content.split('\n'))
    box_width = max(min_width, min(max_width, content_width + 4))
    
    # Create box
    box = []
    box.append("┌" + "─" * (box_width - 2) + "┐")
    
    # Add content lines
    for line in content.split('\n'):
        padding = box_width - len(line) - 2
        box.append("│ " + line + " " * padding + "│")
    
    box.append("└" + "─" * (box_width - 2) + "┘")
    
    # Add tag line
    box.append(tag_line)
    
    return "\n".join(box)

# Add new constants at the top of the file after other constants
RECENT_PROJECTS_DIR = "recent_projects"
RECENT_PROJECTS_LOG = os.path.join(RECENT_PROJECTS_DIR, "latest_projects.log")

# Add new constants at the top of the file after other constants
API_LOGS_DIR = "api_logs"
API_REQUEST_LOG = os.path.join(API_LOGS_DIR, "freelancer_requests.log")

# Constants for project flags
LIMIT_CORRELATION_SCORE = 74  # Minimum correlation score for CORR flag
LIMIT_EMPLOYER_RATING = 4.0   # Minimum employer rating for REP flag
LIMIT_EMPLOYER_REVIEWS = 1    # Minimum number of employer reviews for REP flag

def setup_recent_projects_directory():
    """Setup/clean the recent projects directory"""
    # Remove old directory if it exists
    if os.path.exists(RECENT_PROJECTS_DIR):
        shutil.rmtree(RECENT_PROJECTS_DIR)
    
    # Create fresh directory
    os.makedirs(RECENT_PROJECTS_DIR)

def update_recent_projects_log(projects):
    """Update the log file with recent projects"""
    try:
        # Sort projects by submission date (newest first)
        sorted_projects = sorted(
            projects,
            key=lambda x: x.get('time_submitted', 0) or x.get('submitdate', 0),
            reverse=True
        )
        
        # Create log content
        log_content = [
            "=" * 180,
            f"Latest Projects Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total Projects: {len(projects)}",
            "=" * 180,
            "SUBMIT TIME          | TYPE   | BIDS | COUNTRY       | ID       | TITLE",
            "-" * 180
        ]
        
        # Add each project to the log in a single line
        for project in sorted_projects:
            submit_time = project.get('time_submitted', 0) or project.get('submitdate', 0)
            submit_datetime = datetime.fromtimestamp(submit_time)
            bid_count = project.get('bid_stats', {}).get('bid_count', 0)
            project_type = project.get('type', 'unk1nown').upper()[:6]  # Limit to 6 chars
            country = project.get('country', 'Unknown')[:12]  # Limit to 12 chars
            project_id = str(project.get('id', 'Unknown'))[:8]  # Limit to 8 chars
            title = project.get('title', 'No Title')
            
            # Format each field with fixed width
            line = (
                f"{submit_datetime.strftime('%Y-%m-%d %H:%M')} | "  # 17 chars
                f"{project_type:<6} | "                             # 8 chars
                f"{bid_count:>4} | "                               # 7 chars
                f"{country:<12} | "                                # 14 chars
                f"{project_id:<8} | "                              # 10 chars
                f"{title}"                                         # rest of line
            )
            
            log_content.append(line)
        
        # Write to log file
        with open(RECENT_PROJECTS_LOG, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_content))
            
    except Exception as e:
        print(f"Error updating recent projects log: {str(e)}")

def setup_api_logs_directory():
    """Setup/clean the API logs directory"""
    # Create logs directory if it doesn't exist
    if not os.path.exists(API_LOGS_DIR):
        os.makedirs(API_LOGS_DIR)

def log_api_request(endpoint: str, params: dict, response_status: int, response_data: dict = None):
    """Log API request details to file with comprehensive information"""
    try:
        # Create timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine if this is a Projects API request
        is_projects_api = '/projects/0.1/' in endpoint
        
        # Basic log entry
        if is_projects_api:
            # Enhanced logging for Projects API
            endpoint_type = "UNKNOWN"
            if '/projects/active' in endpoint:
                endpoint_type = "GET_ACTIVE_PROJECTS"
            elif '/projects/' in endpoint and endpoint.count('/') >= 5:
                if '/bids' in endpoint:
                    endpoint_type = "BIDS_API"
                else:
                    endpoint_type = "GET_PROJECT_DETAILS"
            elif '/users/' in endpoint:
                endpoint_type = "GET_USER_DETAILS"
            elif '/reputations/' in endpoint:
                endpoint_type = "GET_USER_REPUTATION"
            
            # Extract key parameters for projects API
            key_params = {}
            if params:
                # Common parameters
                if 'limit' in params:
                    key_params['limit'] = params['limit']
                if 'query' in params:
                    key_params['query'] = params['query']
                if 'project_types[]' in params:
                    key_params['project_types'] = params['project_types[]']
                if 'languages[]' in params:
                    key_params['languages'] = params['languages[]']
                if 'from_time' in params:
                    key_params['from_time'] = params['from_time']
                if 'offset' in params:
                    key_params['offset'] = params['offset']
            
            # Extract response info
            response_info = {}
            if response_data and 'result' in response_data:
                result = response_data['result']
                if 'projects' in result:
                    response_info['projects_count'] = len(result['projects'])
                if 'users' in result:
                    response_info['users_count'] = len(result['users'])
                if 'id' in result:
                    response_info['project_id'] = result['id']
            
            # Format enhanced log entry
            log_entry = f"{timestamp} | {endpoint_type} | {endpoint}"
            if key_params:
                params_str = " | ".join([f"{k}={v}" for k, v in key_params.items()])
                log_entry += f" | PARAMS: {params_str}"
            if response_info:
                response_str = " | ".join([f"{k}={v}" for k, v in response_info.items()])
                log_entry += f" | RESPONSE: {response_str}"
            log_entry += f" | STATUS: {response_status}\n"
        else:
            # Standard logging for non-projects API
            log_entry = f"{timestamp} | {endpoint} | STATUS: {response_status}\n"
        
        # Write to log file
        with open(API_REQUEST_LOG, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
        # Also print to console for projects API requests
        if is_projects_api:
            print(f"📝 API LOG: {log_entry.strip()}")
            
    except Exception as e:
        print(f"Error logging API request: {str(e)}")

def get_active_projects(limit: int = 20, params=None, offset: int = 0, german_only: bool = False, search_query: str = None, project_types=None, scan_scope: str = 'recent') -> dict:
    """Get active projects from Freelancer API"""
    try:
        # Setup API logs directory at first call
        if not os.path.exists(API_LOGS_DIR):
            setup_api_logs_directory()
        
        # Setup recent projects directory at first call
        if not os.path.exists(RECENT_PROJECTS_DIR):
            setup_recent_projects_directory()
        
        endpoint = f'{config.FL_API_BASE_URL}{config.PROJECTS_ENDPOINT}'
        
        if params is None:
            params = {}

        # Base parameters
        base_params = {
            'limit': limit,
            'job_details': True,
            'user_details': True,
            'user_country_details': True,
            'location_details': True,
            'user_hourly_rate_details': True,
            'user_status_details': True,
            'hourly_project_info': True,
            'upgrade_details': True,
            'full_description': True,
            'reputation': True,
            'attachment_details': True,
            'employer_reputation': True,
            'bid_details': True,
            'profile_description': True,
            'sort_field': 'time_updated',
            'sort_direction': 'desc',
            'project_statuses[]': ['active'],
            'active_only': True,
            'compact': True,
            'or_search_query': True
        }
        params.update(base_params)

        # Add from_time parameter for recent mode to get only projects from last hour
        if scan_scope == 'recent':
            one_hour_ago = int(time.time()) - 3600  # Current time minus 1 hour in seconds
            params['from_time'] = one_hour_ago
            print(f"\nDebug: Filtering projects from last hour (from_time: {one_hour_ago})")
        else:
            params['offset'] = offset
    
        # Set project types based on user selection
        if project_types:
            params['project_types[]'] = project_types
        else:
            params['project_types[]'] = ['fixed', 'hourly']
        
        # Add search query if provided
        if search_query and search_query.strip():
            params['query'] = search_query.strip()
        
        # Add German language filter if german_only mode is enabled
        if german_only:
            params['languages[]'] = ['de']
        
        # Check global rate limit before making API call
        if is_rate_limited("bidder-get-user-reputation"):
            print("🚫 Global rate limit active - skipping Freelancer API call")
            return {'result': {'projects': []}}
        
        headers = {
            'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
            'Content-Type': 'application/json'
        }
    
        # Add fixed timeout of 12 seconds between requests
        sleep_with_progress(6, "API Rate Limiting - Warte auf nächsten Request")

        response = requests.get(endpoint, headers=headers, params=params)
        
        # Log the API request
        try:
            response_data = response.json() if response.status_code == 200 else None
            log_api_request(endpoint, params, response.status_code, response_data)
        except Exception as e:
            print(f"Error logging API request: {str(e)}")
        
        if response.status_code == 429:  # Rate limit exceeded
            print(f"🚫 Rate Limiting erkannt! Setze globalen Timeout für 30 Minuten...")
            set_rate_limit_timeout("bidder-get-user-reputation")
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
        elif response.status_code != 200:
            response.raise_for_status()
        
        data = response_data or response.json()
        
        # Update recent projects log if we got valid data
        if 'result' in data and 'projects' in data['result']:
            update_recent_projects_log(data['result']['projects'])
        
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
        
        # Log the API request
        try:
            response_data = response.json() if response.status_code == 200 else None
            log_api_request(endpoint, params, response.status_code, response_data)
        except Exception as e:
            log_api_request(endpoint, params, response.status_code)
            print(f"Error logging user details API request: {str(e)}")
        
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
            # Check global rate limit before making API call
            if is_rate_limited("bidder-get-active-projects"):
                print(f"🚫 Global rate limit active - skipping user reputation API call for user {user_id}")
                # Still return the expected structure but log that it's a fallback
                print(f"⚠️ Using fallback reputation data (all zeros) for user {user_id} due to rate limiting")
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
            
            # Add a small delay between requests to avoid rate limiting
            if attempt > 0:
                sleep_with_progress(retry_delay * attempt, f"Retry {attempt} - Rate Limiting")
            
            response = requests.get(endpoint, headers=headers, params=params)
            
            # Log the API request
            try:
                response_data = response.json() if response.status_code == 200 else None
                log_api_request(endpoint, params, response.status_code, response_data)
            except Exception as e:
                log_api_request(endpoint, params, response.status_code)
                print(f"Error logging reputation API request: {str(e)}")
            
            if response.status_code == 429:  # Rate limit exceeded
                print(f"🚫 Rate Limiting erkannt! Setze globalen Timeout für 30 Minuten...")
                set_rate_limit_timeout("bidder-get-user-reputation")
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
                
            if response.status_code != 200:
                print(f"⚠️ API error (attempt {attempt + 1}/{max_retries}): {response.status_code}")
                if attempt < max_retries - 1:
                    continue
            
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
        
        # ✅ LANGUAGE FILTER: Check LLM detected language
        llm_detected_language = ranking_data.get('llm_recog_language', 'unknown')
        allowed_languages = ['de', 'en', 'fr']  # Only German, English, French
        
        print(f"🌍 Language filter check for project {project_id}:")
        print(f"   LLM detected language: '{llm_detected_language}'")
        print(f"   Allowed languages: {allowed_languages}")
        
        if llm_detected_language not in allowed_languages:
            print(f"❌ LANGUAGE FILTER: Project {project_id} rejected - language '{llm_detected_language}' not in allowed list {allowed_languages}")
            print(f"   Project title: {project_data.get('title', 'Unknown')}")
            print(f"   Skipping save to JSON")
            return  # Exit early - do not save this project
        
        print(f"✅ LANGUAGE FILTER: Project {project_id} accepted - language '{llm_detected_language}' is allowed")
        
        project_url = config.PROJECT_URL_TEMPLATE.format(project_id)
        employer_earnings = 0
        if 'owner' in project_data and 'earnings' in project_data['owner']:
            employer_earnings = project_data['owner']['earnings']
        
        # Extract project type and currency
        project_type = project_data.get('type', 'fixed')
        currency = project_data.get('currency', {}).get('code', 'USD')
        
        # Process bid statistics with currency conversion
        bid_stats = dict(project_data.get('bid_stats', {}))
        avg_bid = bid_stats.get('bid_avg', 0)
        
        # If no bids yet (avg_bid is 0), calculate from budget average
        if avg_bid == 0:
            budget = project_data.get('budget', {})
            budget_min = budget.get('minimum', 0)
            budget_max = budget.get('maximum', 0)
            
            if budget_min > 0 and budget_max > 0:
                avg_bid = (budget_min + budget_max) / 2
                print(f"📊 No bids yet - using budget average: ({budget_min} + {budget_max}) / 2 = {avg_bid} {currency}")
            else:
                print(f"📊 No bids and no valid budget range - keeping avg_bid as 0")
        
        avg_bid_usd = currency_manager.convert_to_usd(avg_bid, currency, debug=True)
        
        # Store original currency and converted USD amount in bid_stats
        bid_stats.update({
            'currency': currency,
            'bid_avg_original': bid_stats.get('bid_avg', 0),  # Keep original API value
            'bid_avg_calculated': avg_bid,  # Store the calculated value (either original or budget average)
            'bid_avg_usd': avg_bid_usd
        })
        
        # Determine if project is high-paying based on average bid in USD
        is_high_paying = False
        if project_type == 'fixed':
            is_high_paying = avg_bid_usd >= LIMIT_HIGH_PAYING_FIXED
        else:  # hourly
            is_high_paying = avg_bid_usd >= LIMIT_HIGH_PAYING_HOURLY

        # Check if project is German-related
        is_german = False
        language = project_data.get('language', '')
        description = project_data.get('description', '').lower()
        country_code = project_data.get('country', '').lower()
        country_name = project_data.get('country', '')
        
        # Debug German detection
        is_german_language = language == 'de'
        
        # Check both country code and full country name
        is_german_country_code = country_code in config.GERMAN_SPEAKING_COUNTRIES
        is_german_country_name = country_name in config.GERMAN_SPEAKING_COUNTRIES.values()
        is_german_country = is_german_country_code or is_german_country_name
        
        has_german_keywords = any(word in description for word in ['deutsch', 'deutsche', 'deutscher', 'österreich', 'schweiz'])
        
        is_german = is_german_language or is_german_country or has_german_keywords
        
        # Debug output for German detection
        if is_german_language or is_german_country or has_german_keywords:
            print(f"\n=== German Detection Debug ===")
            print(f"Language: '{language}' -> German language: {is_german_language}")
            print(f"Country code: '{country_code}' -> German country code: {is_german_country_code}")
            print(f"Country name: '{country_name}' -> German country name: {is_german_country_name}")
            print(f"Overall German country: {is_german_country}")
            print(f"Has German keywords: {has_german_keywords}")
            print(f"Final is_german: {is_german}")
            print(f"Available countries in config: {config.GERMAN_SPEAKING_COUNTRIES}")
            print("================================")

        # Check if project is urgent
        is_urgent = False
        if 'urgent' in description or 'schnellstmöglich' in description or 'asap' in description or 'dringend' in description:
            is_urgent = True
        if 'urgent' in project_data.get('title', '').lower():
            is_urgent = True
        # Check for Freelancer.com 'urgent' flag if available
        if 'urgent' in project_data:
            if project_data['urgent']:
                is_urgent = True

        # Check if project is enterprise
        is_enterprise = False
        if 'enterprise' in description or 'konzern' in description or 'großunternehmen' in description or 'corporate' in description:
            is_enterprise = True
        if 'enterprise' in project_data.get('title', '').lower():
            is_enterprise = True

        # Run authenticity check only after all other filters have passed
        print("\nRunning authenticity check...")
        authenticity_data = ranker.detect_authenticity(project_data)
        is_authentic = authenticity_data['is_authentic']
        authenticity_score = authenticity_data['score']
        authenticity_explanation = authenticity_data['explanation']

        print(f"\nAuthenticity Analysis Results:")
        print(f"Score: {authenticity_score}")
        print(f"Is Authentic: {is_authentic}")
        print(f"Explanation: {authenticity_explanation}")
 
        # Check correlation score - use the main score from ranking_data
        is_corr = False
        if ranking_data and 'score' in ranking_data:
            is_corr = ranking_data['score'] >= LIMIT_CORRELATION_SCORE

        # Check employer reputation
        is_rep = False
        employer_rating = project_data.get('employer_overall_rating', 0)
        employer_reviews = project_data.get('employer_complete_projects', 0)
        is_rep = (employer_rating >= LIMIT_EMPLOYER_RATING and employer_reviews > LIMIT_EMPLOYER_REVIEWS)

        # Store all flags in a dict
        flags = {
            'is_high_paying': is_high_paying,
            'is_german': is_german,
            'is_urgent': is_urgent,
            'is_enterprise': is_enterprise,
            'is_authentic': is_authentic,
            'is_corr': is_corr,
            'is_rep': is_rep
        }

        final_project_data = {
            'project_details': {
                'id': project_id,
                'title': project_data.get('title', 'Unknown'),
                'description': project_data.get('description', ''),
                'time_submitted': project_data.get('submitdate') or project_data.get('time_submitted'),
                'submitdate': project_data.get('submitdate') or project_data.get('time_submitted'),
                'employer_earnings_score': employer_earnings,
                'employer_complete_projects': project_data.get('employer_complete_projects', 0),
                'employer_overall_rating': project_data.get('employer_overall_rating', 0),
                'country': project_data.get('country', 'Unknown'),
                'project_type': project_type,
                'currency': project_data.get('currency', {'code': 'USD'}),
                'budget': project_data.get('budget', {}),
                'hourly_rate': project_data.get('hourly_rate', 0),
                'bid_stats': bid_stats,
                'flags': flags,
                'authenticity': {
                    'score': authenticity_score,
                    'explanation': authenticity_explanation
                },
                'llm_recog_language': llm_detected_language  # Store LLM detected language
            },
            'project_url': project_url,
            'timestamp': project_data.get('submitdate') or project_data.get('time_submitted'),
            'bid_text': ranking_data.get('explanation', ''),
            'ranking': ranking_data
        }

        # Use only project ID for filename
        filename = f"job_{project_id}.json"
        jobs_dir = Path('jobs')
        jobs_dir.mkdir(parents=True, exist_ok=True)
        file_path = jobs_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(final_project_data, f, indent=4, ensure_ascii=False)
        
        print(f"✅ Saved job data for project {project_id}")
        
    except Exception as e:
        print(f"❌ Error saving job data for project {project_id}: {str(e)}")
        print(traceback.format_exc())

def format_project_display(project: dict, project_id: str, score: int, ranking: dict, ranker) -> str:
    """Format project details for display with ASCII art score and project information."""
    # Generate colored ASCII art score
    score_ascii_art = format_score_with_ascii_art(score)
    
    # Get currency symbol and code
    currency_info = project.get('currency', {'code': 'USD', 'sign': '$'})
    currency_symbol = currency_info.get('sign', '$')
    currency_code = currency_info.get('code', 'USD')
    
    # Format budget or hourly rate based on project type
    if project.get('type') == 'hourly':
        rate = project.get('hourly_rate', 0)
        budget_display = f"{currency_symbol}{rate}/hr ({currency_code})"
    else:
        budget_min = project.get('budget', {}).get('minimum', 0)
        budget_max = project.get('budget', {}).get('maximum', 0)
        budget_display = f"{currency_symbol}{budget_min} - {currency_symbol}{budget_max} ({currency_code})"
    
    # Create project details for display
    return f"""
📌 {project.get('title', 'No Title')}
🔗 {config.PROJECT_URL_TEMPLATE.format(project_id)}

┌────────────────────────────────┬────────────────────────────────┬────────────────────────────────┬────────────────────────────────┐
│ 🤖 SCORE:                       │ 🔧 PROJEKT-FÄHIGKEITEN:         │ 💼 ARBEITGEBER:                 │ 🤖 KI-KONTEXT:                 │
│ {score_ascii_art}               │                                │                                │   • Konversation: {ranker.conversation_id} │
│ 💰 BUDGET: {budget_display.ljust(20)} │                                │                                │ 🔗 LINKS:                      │
│                                │                                │                                │   • Projekt: {config.PROJECT_URL_TEMPLATE.format(project_id)} │
│                                │                                │                                │                                │
└────────────────────────────────┴────────────────────────────────┴────────────────────────────────┴────────────────────────────────┘
"""

def process_evaluated_project(project: dict, project_id: str, evaluation: dict, ranker, selected_profile: dict = None) -> None:
    """Process an evaluated project, display results and save if criteria are met."""
    project_title = project.get('title', 'No Title')
    
    if not evaluation['success']:
        print(f"\033[96m🤖\033[0m Skipped: {evaluation['reason']}")
        # Log AI evaluation failure
        log_project_evaluation(
            project_id=str(project_id),
            project_title=project_title,
            status="rejected",
            reason=evaluation['reason'],
            additional_data={
                'bid_count': project.get('bid_stats', {}).get('bid_count', 0),
                'project_type': project.get('type', 'unknown'),
                'currency': project.get('currency', {}).get('code', 'USD'),
                'rejection_stage': 'ai_evaluation_error'
            }
        )
        return False
    
    if not evaluation['meets_criteria']:
        print(f"\033[93m⚠️\033[0m Skipped: {evaluation['reason']}")
        # Log criteria failure
        log_project_evaluation(
            project_id=str(project_id),
            project_title=project_title,
            status="rejected",
            reason=evaluation['reason'],
            additional_data={
                'bid_count': project.get('bid_stats', {}).get('bid_count', 0),
                'project_type': project.get('type', 'unknown'),
                'currency': project.get('currency', {}).get('code', 'USD'),
                'ai_score': evaluation.get('score', 0),
                'rejection_stage': 'ai_evaluation_criteria'
            }
        )
        return False
    
    # If we get here, the project meets all criteria
    score = evaluation['score']
    ranking = evaluation['ranking_data']
    project_data = evaluation['project_data']
    
    # Display project details
    project_details = format_project_display(project, project_id, score, ranking, ranker)
    print(project_details)
    
    # Get score limit from profile or use default
    score_limit = selected_profile.get('score_limit', 50) if selected_profile else 50
    
    # Only save and process if score meets threshold
    if score >= score_limit:
        print(f"✅ New Project (Score: {score} >= {score_limit})")
        print(f"   Location: {project.get('country', 'Unknown')}")
        
        # Log accepted project
        log_project_evaluation(
            project_id=str(project_id),
            project_title=project_title,
            status="accepted",
            reason=f"Score {score} >= threshold {score_limit}",
            additional_data={
                'bid_count': project.get('bid_stats', {}).get('bid_count', 0),
                'project_type': project.get('type', 'unknown'),
                'currency': project.get('currency', {}).get('code', 'USD'),
                'ai_score': score,
                'score_threshold': score_limit,
                'country': project.get('country', 'Unknown'),
                'processing_stage': 'accepted_and_saved'
            }
        )
        
        # Save the project data to JSON
        save_job_to_json(project_data, ranking)
        
        # Process ranked project
        process_ranked_project(project_data, ranking, 
                             selected_profile.get('bid_limit', 40) if selected_profile else 40, 
                             score_limit)
        return True
    else:
        print(f"⏭️ Skipped: Score {score} below threshold {score_limit}")
        # Log score too low
        log_project_evaluation(
            project_id=str(project_id),
            project_title=project_title,
            status="rejected",
            reason=f"Score {score} below threshold {score_limit}",
            additional_data={
                'bid_count': project.get('bid_stats', {}).get('bid_count', 0),
                'project_type': project.get('type', 'unknown'),
                'currency': project.get('currency', {}).get('code', 'USD'),
                'ai_score': score,
                'score_threshold': score_limit,
                'rejection_stage': 'score_threshold'
            }
        )
        return False

def check_project_eligibility(project: dict, project_id: str, selected_profile: dict, seen_projects: set) -> tuple[bool, str]:
    """Check if a project meets basic eligibility criteria."""
    # Skip if project has pf_only upgrade
    upgrades = project.get('upgrades', {})
    if upgrades.get('pf_only', False):
        return False, "Project is PF only"
    
    # Skip if we've already seen this project
    if project_id in seen_projects:
        return False, "Project already processed"
    
    # Check bid count
    bid_count = project.get('bid_stats', {}).get('bid_count', 0)
    if bid_count >= selected_profile['bid_limit']:
        return False, f"Too many bids ({bid_count} >= {selected_profile['bid_limit']})"
    
    return True, ""

def prepare_project_data(project: dict, project_id: str, user_rep: dict, country: str) -> dict:
    """Prepare project data for evaluation."""
    # Handle case where user_rep is None
    if user_rep is None:
        user_rep = {}
    
    entire_history = user_rep.get('entire_history', {})
    earnings_score = user_rep.get('earnings_score', 0)
    
    return {
        'title': project.get('title', 'No Title'),
        'description': project.get('description', 'No description available'),
        'jobs': project.get('jobs', []),
        'bid_stats': project.get('bid_stats', {}),
        'employer_earnings_score': earnings_score,
        'employer_complete_projects': entire_history.get('complete', 0),
        'employer_overall_rating': entire_history.get('overall', 0),
        'country': country,
        'country_code': get_country_code_from_name(country),
        'id': project_id,
        'submitdate': project.get('submitdate'),
        'time_submitted': project.get('time_submitted'),
        'time_updated': project.get('time_updated'),
        'type': project.get('type', 'fixed'),
        'currency': project.get('currency', {'code': 'USD'}),
        'budget': project.get('budget', {}),
        'hourly_rate': project.get('hourly_rate', 0),
        'upgrades': project.get('upgrades', {}),
        'language': project.get('language', '')
    }

def check_high_paying_criteria(project: dict, currency_code: str) -> tuple[bool, str]:
    """Check if a project meets high-paying criteria."""
    project_type = project.get('type', 'fixed')
    
    if project_type == 'fixed':
        budget_min = project.get('budget', {}).get('minimum', 0)
        budget_max = project.get('budget', {}).get('maximum', 0)
        budget_min_usd = currency_manager.convert_to_usd(budget_min, currency_code, debug=True)
        budget_max_usd = currency_manager.convert_to_usd(budget_max, currency_code, debug=True)
        
        if budget_max_usd < LIMIT_HIGH_PAYING_FIXED:
            return False, f"Budget too low (${budget_max_usd:.2f} USD < ${LIMIT_HIGH_PAYING_FIXED})"
    else:  # hourly
        hourly_rate = project.get('hourly_rate', 0)
        hourly_rate_usd = currency_manager.convert_to_usd(hourly_rate, currency_code, debug=True)
        
        if hourly_rate_usd < LIMIT_HIGH_PAYING_HOURLY:
            return False, f"Hourly rate too low (${hourly_rate_usd:.2f} USD < ${LIMIT_HIGH_PAYING_HOURLY})"
    
    return True, ""

def check_country_criteria(project: dict, country: str, selected_profile: dict) -> tuple[bool, str]:
    """Check if a project meets country criteria."""
    if selected_profile['country_mode'] in ['y', 'g']:
        country_code = project.get('country', '').lower()
        
        if country_code:
            if selected_profile['country_mode'] == 'g':
                if country_code not in config.GERMAN_SPEAKING_COUNTRIES:
                    return False, f"Country code {country_code} not in German-speaking countries"
            else:
                if country_code not in config.RICH_COUNTRIES:
                    return False, f"Country code {country_code} not in target list"
        
        # Check full country name if available
        if country != "Unknown":
            if selected_profile['country_mode'] == 'g':
                if country not in config.GERMAN_SPEAKING_COUNTRIES.values():
                    return False, f"Country {country} not in German-speaking countries"
            else:
                if country not in config.RICH_COUNTRIES_FULL.values():
                    return False, f"Country {country} not in target list"
    
    return True, ""

def main(debug_mode=False):
    try:
        print("\n=== Initializing Bidder ===")
        
        # Update currency rates at startup and verify
        print("\nUpdating currency rates...")
        update_success, update_message = currency_manager.update_rates()
        
        # Verify we have valid rates
        if all(rate == 0 for rate in currency_manager.rates.values()):
            print("❌ Failed to initialize currency rates. Please check your internet connection.")
            return
        
        if debug_mode:
            print("\n=== DEBUG MODE ===")
            # Use default profile with debug settings
            selected_profile = {
                'search_query': 'python',  # Simple search query for testing
                'project_types': ['fixed'],
                'bid_limit': 100,
                'score_limit': 0,  # Accept all scores for testing
                'country_mode': 'y',
                'german_only': False,
                'scan_scope': 'recent',
                'high_paying_only': False,
                'clear_cache': False
            }
            print("Using debug profile with following settings:")
            for key, value in selected_profile.items():
                print(f"- {key}: {value}")
            clear_cache_response = 'n'  # Don't clear cache in debug mode
            search_query = selected_profile['search_query']  # Use search query from profile
        else:
            # Original profile selection code
            print("\n=== Configuration ===")
            # Show available profiles with numbers
            print("\nAvailable profiles:")
            profile_list = list(PROFILES.keys())
            for idx, profile_name in enumerate(profile_list, 1):
                print(f"{idx}. {profile_name}")
            
            # Ask for profile selection by number
            profile_input = input("\nSelect a profile number (or press Enter for no profile): ").strip()
            
            # Handle profile selection
            if profile_input.isdigit() and 1 <= int(profile_input) <= len(profile_list):
                profile_name = profile_list[int(profile_input) - 1]
                selected_profile = PROFILES[profile_name]
                print(f"\nSelected profile: {profile_name}")
            else:
                print("\nNo profile selected, using default settings")
                selected_profile = PROFILES['default']
            
            # Get minimum price settings
            try:
                min_fixed_input = input(f"\nEnter minimum fixed price in USD (or press Enter for {selected_profile.get('min_fixed', 250)}): ").strip()
                if min_fixed_input:
                    selected_profile['min_fixed'] = float(min_fixed_input)
                elif 'min_fixed' not in selected_profile:
                    selected_profile['min_fixed'] = 250
                
                min_hourly_input = input(f"\nEnter minimum hourly rate in USD (or press Enter for {selected_profile.get('min_hourly', 25)}): ").strip()
                if min_hourly_input:
                    selected_profile['min_hourly'] = float(min_hourly_input)
                elif 'min_hourly' not in selected_profile:
                    selected_profile['min_hourly'] = 25
            except ValueError as e:
                print(f"Invalid input for minimum prices, using profile defaults: {str(e)}")
            
            # Get search query (only if not already set in profile)
            search_query = selected_profile.get('search_query', '')
            if not search_query:
                search_query = input("Enter search terms (optional, space-separated): ").strip()
            
            clear_cache_response = 'j' if selected_profile['clear_cache'] else 'n'
        
        print("\nStarting project list test...")
        seen_projects = set()  # Track all projects we've seen
        failed_users = set()  # Track users we've failed to fetch
        cache = FileCache(cache_dir='cache', expiry=3600)
        
        # Process the cache clearing
        if clear_cache_response in ['j', 'ja']:
            print("🧹 Lösche alle Cache-Dateien...")
            cache.clear()
            print("✅ Cache wurde vollständig geleert.")
        else:
            print("ℹ️ Cache bleibt erhalten.")
            
        print(f"\nDebug: Configuration Summary:")
        print(f"- Search Query: {search_query if search_query else 'None'}")
        print(f"- Project Type: {', '.join(selected_profile['project_types'])}")
        print(f"- Bid Limit: {selected_profile['bid_limit']}")
        print(f"- Score Limit: {selected_profile['score_limit']}")
        print(f"- Country Mode: {selected_profile['country_mode']} (German Only: {selected_profile['german_only']}, Country Check: {selected_profile['country_mode'] in ['y', 'g']})")
        print(f"- Scan Scope: {selected_profile['scan_scope']}")
        print(f"- High-paying jobs only: {selected_profile['high_paying_only']}")
        
        ranker = ProjectRanker()
        
        # Initialize offset for past scanning
        current_offset = 0
        no_results_count = 0
        max_no_results = 3  # Reset offset after 3 empty results
        last_heartbeat = time.time()

        # Load our expertise/skills from skills.json
        our_skills = get_our_skills()
        
        # Extract job IDs and skill names for API request
        skill_ids = [skill['id'] for skill in our_skills if skill['id'] is not None]
        skill_names = [skill['name'] for skill in our_skills]
        skill_names_lower = [name.lower() for name in skill_names]

        # Send heartbeat with initial status
        send_heartbeat('bidder', {
            'status': 'running',
            'debug_mode': debug_mode,
            'profile': selected_profile,
            'scan_scope': selected_profile['scan_scope'],
            'search_query': search_query if search_query else 'None'
        })

        try:
            while True:
                # Send heartbeat every 60 seconds
                current_time = time.time()
                if current_time - last_heartbeat > 60:
                    send_heartbeat('bidder', {
                        'status': 'scanning',
                        'debug_mode': debug_mode,
                        'profile': selected_profile,
                        'offset': current_offset,
                        'seen_projects': len(seen_projects),
                        'failed_users': len(failed_users),
                        'no_results_count': no_results_count,
                        'rate_limit_status': 'active' if is_rate_limited() else 'clear',
                        'rate_limit_remaining': get_rate_limit_status()['remaining_seconds']
                    })
                    last_heartbeat = current_time
                # Adjust API parameters based on scan scope
                params = {
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
                    'upgrade_details': True,
                }
                
                current_limit = 20 if selected_profile['scan_scope'] == 'past' else 10
                params['limit'] = current_limit
                
                if selected_profile['scan_scope'] == 'past':
                    print(f"\n🔍 Scanning past projects with offset: {current_offset}")
                
                # Debug output for API call
                print(f"\nDebug: API Call:")
                print(f"- Endpoint: {config.FL_API_BASE_URL}{config.PROJECTS_ENDPOINT}")
                print(f"- Search Query: {search_query if search_query else 'None'}")
                print(f"- Project Types: {', '.join(selected_profile['project_types'])}")
                print(f"- Limit: {current_limit}")
                print(f"- Offset: {current_offset}")
                print(f"- German only: {selected_profile['german_only']}")
                
                result = get_active_projects(
                    limit=current_limit,
                    params=params,
                    offset=current_offset if selected_profile['scan_scope'] == 'past' else 0,
                    german_only=selected_profile['german_only'],
                    search_query=search_query,
                    project_types=selected_profile['project_types'],
                    scan_scope=selected_profile['scan_scope']
                )
                
                # Debug output for API response
                if 'result' in result and 'projects' in result['result']:
                    projects_found = len(result['result']['projects'])
                    print(f"Debug: Found {projects_found} projects in response")
                    
                    if selected_profile['scan_scope'] == 'past':
                        if projects_found > 0:
                            print(f"📊 Found {projects_found} projects, next offset will be: {current_offset + projects_found}")
                            current_offset += projects_found
                            no_results_count = 0
                        else:
                            no_results_count += 1
                            if no_results_count >= max_no_results:
                                print("🔄 No more projects found, resetting offset to 0")
                                current_offset = 0
                                no_results_count = 0
                    else:
                        # In recent mode, don't update offset, just reset no_results_count
                        if projects_found > 0:
                            no_results_count = 0
                        else:
                            no_results_count += 1
                else:
                    print("Debug: No projects found in response")
                    no_results_count += 1
                    if selected_profile['scan_scope'] == 'past' and no_results_count >= max_no_results:
                        print("🔄 No more projects found, resetting offset to 0")
                        current_offset = 0
                        no_results_count = 0

                if 'result' not in result or 'projects' not in result['result']:
                    print("\nNo projects in response, waiting 1 second...")
                    if selected_profile['scan_scope'] == 'past':
                        no_results_count += 1
                        if no_results_count >= max_no_results:
                            print("🔄 No more projects found, resetting offset to 0")
                            current_offset = 0
                            no_results_count = 0
                    sleep_with_progress(1, "Warte auf neue Projekte")
                    continue
                
                projects = result['result']['projects']
                if not projects:
                    print("\nEmpty projects list, waiting 6 seconds...")
                    if selected_profile['scan_scope'] == 'past':
                        no_results_count += 1
                        if no_results_count >= max_no_results:
                            print("🔄 No more projects found, resetting offset to 0")
                            current_offset = 0
                            no_results_count = 0
                    sleep_with_progress(6, "Warte auf neue Projekte")
                    continue    
                
                # Reset no_results_count since we got projects
                no_results_count = 0
                
                new_projects_found = 0
                total_projects = len(projects)
                current_project = 0
                
                # Update offset for next iteration only if in past mode
                if selected_profile['scan_scope'] == 'past':
                    print(f"📊 Processing {len(projects)} projects from offset {current_offset - len(projects)} to {current_offset}")
                else:
                    print(f"📊 Processing {len(projects)} recent projects (always newest)")

                # Process all projects
                for project in projects:
                    current_project += 1
                    project_id = project.get('id')
                    project_title = project.get('title', 'No Title')
                    
                    if not project_id:
                        continue
                    
                    print(f"\nProcessing project {current_project}/{total_projects}: {project_title} ({config.PROJECT_URL_TEMPLATE.format(project_id)})")
                    
                    # Check basic eligibility
                    is_eligible, reason = check_project_eligibility(project, project_id, selected_profile, seen_projects)
                    if not is_eligible:
                        print(f"\033[91m⏭️\033[0m Skipped: {reason}")
                        # Log rejected project
                        log_project_evaluation(
                            project_id=str(project_id),
                            project_title=project_title,
                            status="rejected",
                            reason=reason,
                            additional_data={
                                'bid_count': project.get('bid_stats', {}).get('bid_count', 0),
                                'project_type': project.get('type', 'unknown'),
                                'currency': project.get('currency', {}).get('code', 'USD'),
                                'rejection_stage': 'basic_eligibility'
                            }
                        )
                        seen_projects.add(project_id)
                        continue
                    
                    # Extract country information early (works for both new and cached projects)
                    country, country_code = extract_country_from_project(project)
                    
                    # Fallback: Get user details if country not found in project data
                    if country == "Unknown":
                        owner_id = project.get('owner_id')
                        user_details = get_user_details(owner_id, cache, failed_users)
                        
                        if 'result' in user_details:
                            user_data = user_details['result']
                            location = user_data.get('location', {})
                            if location and 'country' in location and location['country']:
                                country = location['country'].get('name', 'Unknown')
                                country_code_raw = location['country'].get('code', '')
                                country_code = country_code_raw.lower() if country_code_raw else ''
                                print(f"🌍 Fallback: Got country from user details: {country} ({country_code})")
                    
                    print(f"🏁 Final country determination: {country} ({country_code})")
                    
                    # Check country criteria early (before high-paying check)
                    is_valid_country, reason = check_country_criteria(project, country, selected_profile)
                    if not is_valid_country:
                        print(f"\033[93m🌍\033[0m Skipped: {reason}")
                        # Log rejected project
                        log_project_evaluation(
                            project_id=str(project_id),
                            project_title=project_title,
                            status="rejected",
                            reason=reason,
                            additional_data={
                                'bid_count': project.get('bid_stats', {}).get('bid_count', 0),
                                'project_type': project.get('type', 'unknown'),
                                'currency': project.get('currency', {}).get('code', 'USD'),
                                'country': country,
                                'country_code': country_code,
                                'rejection_stage': 'country_criteria_early'
                            }
                        )
                        seen_projects.add(project_id)
                        continue
                    
                    # Check if project is already cached
                    cached_project = cache.get('project_details', f"id_{project_id}")
                    is_new_project = cached_project is None
                    
                    if is_new_project:
                        # Check for high-paying jobs if enabled
                        if selected_profile['high_paying_only']:
                            currency_code = project.get('currency', {}).get('code', 'USD')
                            is_high_paying, reason = check_high_paying_criteria(project, currency_code)
                            if not is_high_paying:
                                print(f"\033[93m💰\033[0m Skipped: {reason}")
                                # Log rejected project
                                log_project_evaluation(
                                    project_id=str(project_id),
                                    project_title=project_title,
                                    status="rejected",
                                    reason=reason,
                                    additional_data={
                                        'bid_count': project.get('bid_stats', {}).get('bid_count', 0),
                                        'project_type': project.get('type', 'unknown'),
                                        'currency': currency_code,
                                        'budget': project.get('budget', {}),
                                        'hourly_rate': project.get('hourly_rate', 0),
                                        'rejection_stage': 'high_paying_criteria'
                                    }
                                )
                                seen_projects.add(project_id)
                                continue
                        
                        # Get user reputation (country already determined above)
                        owner_id = project.get('owner_id')
                        reputation_data = get_user_reputation(owner_id, cache)
                        if 'result' not in reputation_data:
                            print(f"\033[95m👤\033[0m Skipped: Failed to fetch reputation data")
                            # Log rejected project
                            log_project_evaluation(
                                project_id=str(project_id),
                                project_title=project_title,
                                status="rejected",
                                reason="Failed to fetch reputation data",
                                additional_data={
                                    'bid_count': project.get('bid_stats', {}).get('bid_count', 0),
                                    'project_type': project.get('type', 'unknown'),
                                    'currency': project.get('currency', {}).get('code', 'USD'),
                                    'country': country,
                                    'owner_id': owner_id,
                                    'rejection_stage': 'reputation_fetch'
                                }
                            )
                            seen_projects.add(project_id)
                            continue
                        
                        # Extract user-specific reputation data from the result
                        user_rep_data = {}
                        result = reputation_data['result']
                        if isinstance(result, dict):
                            # Check if user_id exists as key in result
                            user_key = str(owner_id)
                            if user_key in result:
                                user_rep_data = result[user_key]
                                print(f"💰 Retrieved reputation for user {owner_id}: earnings={user_rep_data.get('earnings_score', 0)}, complete={user_rep_data.get('entire_history', {}).get('complete', 0)}, rating={user_rep_data.get('entire_history', {}).get('overall', 0)}")
                            else:
                                print(f"⚠️ User {owner_id} not found in reputation result keys: {list(result.keys())}")
                                user_rep_data = {'earnings_score': 0, 'entire_history': {'complete': 0, 'overall': 0}}
                        else:
                            print(f"⚠️ Unexpected reputation result structure: {type(result)}")
                            user_rep_data = {'earnings_score': 0, 'entire_history': {'complete': 0, 'overall': 0}}
                            
                        # Prepare project data
                        project_data = prepare_project_data(project, project_id, user_rep_data, country)
                        
                        # Check language criteria - only accept 'en', 'de', or 'fr'
                        project_language = project_data.get('language', '')
                        if project_language not in ['en', 'de', 'fr']:
                            print(f"\033[93m🌐\033[0m Skipped: Language '{project_language}' not supported (only en, de, fr allowed)")
                            # Log rejected project
                            log_project_evaluation(
                                project_id=str(project_id),
                                project_title=project_title,
                                status="rejected",
                                reason=f"Language '{project_language}' not supported (only en, de, fr allowed)",
                                additional_data={
                                    'bid_count': project.get('bid_stats', {}).get('bid_count', 0),
                                    'project_type': project.get('type', 'unknown'),
                                    'currency': project.get('currency', {}).get('code', 'USD'),
                                    'country': country,
                                    'language': project_language,
                                    'rejection_stage': 'language_criteria'
                                }
                            )
                            seen_projects.add(project_id)
                            continue
                        
                        # Evaluate the project
                        evaluation = evaluate_project(project_data, selected_profile)
                        
                        if process_evaluated_project(project, project_id, evaluation, ranker, selected_profile):
                            seen_projects.add(project_id)
                            continue
                        
                        seen_projects.add(project_id)
                        continue
                    
                    # Remove the "Project already processed" message
                    continue
                
                sleep_with_progress(1, "Pausiere vor nächstem Scan-Durchlauf")
                
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
    import sys
    debug_mode = '--debug' in sys.argv
    main(debug_mode) 