"""
LinkedIn Jobs Fetcher

This module fetches job listings from the LinkedIn API using the LinkedIn Jobs API.
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    LINKEDIN_API_KEY,
    LINKEDIN_CLIENT_SECRET,
    LINKEDIN_ACCESS_TOKEN,
    LINKEDIN_API_BASE_URL,
    LINKEDIN_JOBS_ENDPOINT,
    LINKEDIN_MAX_RESULTS,
    LINKEDIN_DEFAULT_KEYWORDS,
    LINKEDIN_DEFAULT_LOCATION
)


class LinkedInJobsFetcher:
    """
    A class to fetch job listings from the LinkedIn API.
    """
    
    def __init__(self):
        """Initialize the LinkedIn Jobs Fetcher."""
        self.api_key = LINKEDIN_API_KEY
        self.client_secret = LINKEDIN_CLIENT_SECRET
        self.access_token = LINKEDIN_ACCESS_TOKEN
        self.base_url = LINKEDIN_API_BASE_URL
        self.jobs_endpoint = LINKEDIN_JOBS_ENDPOINT
        self.max_results = LINKEDIN_MAX_RESULTS
        self.session = requests.Session()
        
        # Set up authentication headers
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        if not self.access_token:
            print("Warning: LinkedIn access token not configured. Please set LINKEDIN_ACCESS_TOKEN in config.py.")
    
    def search_jobs(self, 
                   keywords: Optional[List[str]] = None,
                   location: Optional[str] = None,
                   limit: Optional[int] = None,
                   job_type: Optional[str] = None,
                   experience_level: Optional[str] = None,
                   company_id: Optional[str] = None) -> Dict:
        """
        Search for jobs on LinkedIn.
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in
            limit: Maximum number of results to return
            job_type: Type of job (full-time, part-time, contract, etc.)
            experience_level: Experience level (entry, mid, senior, etc.)
            company_id: Specific company ID to search within
            
        Returns:
            Dictionary containing job search results
        """
        
        # Use defaults if not provided
        if keywords is None:
            keywords = LINKEDIN_DEFAULT_KEYWORDS
        if location is None:
            location = LINKEDIN_DEFAULT_LOCATION
        if limit is None:
            limit = self.max_results
            
        # Build search parameters
        params = {
            'keywords': ' '.join(keywords),
            'location': location,
            'count': min(limit, 25),  # LinkedIn API limit per request
            'start': 0
        }
        
        if job_type:
            params['jobType'] = job_type
        if experience_level:
            params['experienceLevel'] = experience_level
        if company_id:
            params['companyId'] = company_id
            
        try:
            # Make API request
            url = f"{self.base_url}{self.jobs_endpoint}"
            response = self.session.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return self._process_job_results(response.json())
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': 'Authentication failed. Please check your LinkedIn access token.',
                    'jobs': []
                }
            elif response.status_code == 429:
                return {
                    'success': False,
                    'error': 'Rate limit exceeded. Please try again later.',
                    'jobs': []
                }
            else:
                return {
                    'success': False,
                    'error': f'API request failed with status code: {response.status_code}',
                    'response': response.text,
                    'jobs': []
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'jobs': []
            }
    
    def _process_job_results(self, data: Dict) -> Dict:
        """
        Process the raw API response and extract job information.
        
        Args:
            data: Raw API response data
            
        Returns:
            Processed job results
        """
        processed_jobs = []
        
        try:
            elements = data.get('elements', [])
            
            for job_data in elements:
                job = self._extract_job_details(job_data)
                if job:
                    processed_jobs.append(job)
                    
            return {
                'success': True,
                'total_results': data.get('paging', {}).get('total', 0),
                'count': len(processed_jobs),
                'jobs': processed_jobs,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing job results: {str(e)}',
                'jobs': []
            }
    
    def _extract_job_details(self, job_data: Dict) -> Optional[Dict]:
        """
        Extract relevant details from a single job posting.
        
        Args:
            job_data: Raw job data from API
            
        Returns:
            Extracted job details or None if extraction fails
        """
        try:
            job = {
                'id': job_data.get('id'),
                'title': job_data.get('title'),
                'company': self._extract_company_info(job_data.get('company', {})),
                'location': job_data.get('formattedLocation'),
                'description': job_data.get('description', {}).get('text', ''),
                'job_type': job_data.get('workplaceTypes', []),
                'posted_date': job_data.get('listedAt'),
                'expires_date': job_data.get('expireAt'),
                'url': self._generate_job_url(job_data.get('id')),
                'skills': self._extract_skills(job_data.get('skills', [])),
                'experience_level': job_data.get('workExperience'),
                'industry': job_data.get('industries', []),
                'salary': self._extract_salary_info(job_data.get('salary')),
                'applicant_count': job_data.get('applicantCount'),
                'raw_data': job_data  # Keep original data for debugging
            }
            
            return job
            
        except Exception as e:
            print(f"Error extracting job details: {str(e)}")
            return None
    
    def _extract_company_info(self, company_data: Dict) -> Dict:
        """Extract company information from job data."""
        return {
            'id': company_data.get('id'),
            'name': company_data.get('name'),
            'logo': company_data.get('logo'),
            'industry': company_data.get('industries', []),
            'size': company_data.get('staffCountRange')
        }
    
    def _extract_skills(self, skills_data: List) -> List[str]:
        """Extract skills from job data."""
        return [skill.get('name', '') for skill in skills_data if skill.get('name')]
    
    def _extract_salary_info(self, salary_data: Optional[Dict]) -> Optional[Dict]:
        """Extract salary information from job data."""
        if not salary_data:
            return None
            
        return {
            'currency': salary_data.get('currency'),
            'min_amount': salary_data.get('from'),
            'max_amount': salary_data.get('to'),
            'period': salary_data.get('period')
        }
    
    def _generate_job_url(self, job_id: str) -> str:
        """Generate LinkedIn job URL from job ID."""
        if job_id:
            return f"https://www.linkedin.com/jobs/view/{job_id}"
        return ""
    
    def save_jobs_to_file(self, jobs_data: Dict, filename: str = None) -> str:
        """
        Save job search results to a JSON file.
        
        Args:
            jobs_data: Job search results
            filename: Custom filename (optional)
            
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_jobs_{timestamp}.json"
            
        filepath = os.path.join(os.path.dirname(__file__), '..', 'jobs', filename)
        
        # Create jobs directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(jobs_data, f, indent=2, ensure_ascii=False)
            
            print(f"Jobs saved to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Error saving jobs to file: {str(e)}")
            return ""
    
    def get_job_details(self, job_id: str) -> Dict:
        """
        Get detailed information about a specific job.
        
        Args:
            job_id: LinkedIn job ID
            
        Returns:
            Detailed job information
        """
        try:
            url = f"{self.base_url}/jobs/{job_id}"
            response = self.session.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'job': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to fetch job details: {response.status_code}'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }


def main():
    """
    Example usage of the LinkedIn Jobs Fetcher.
    """
    fetcher = LinkedInJobsFetcher()
    
    # Search for Python developer jobs in Germany
    print("Searching for Python developer jobs in Germany...")
    results = fetcher.search_jobs(
        keywords=["Python developer", "Backend developer"],
        location="Germany",
        limit=10
    )
    
    if results['success']:
        print(f"Found {results['count']} jobs out of {results['total_results']} total results")
        
        # Save results to file
        filename = fetcher.save_jobs_to_file(results)
        
        # Display first few jobs
        for i, job in enumerate(results['jobs'][:3], 1):
            print(f"\n--- Job {i} ---")
            print(f"Title: {job['title']}")
            print(f"Company: {job['company']['name']}")
            print(f"Location: {job['location']}")
            print(f"URL: {job['url']}")
            print(f"Skills: {', '.join(job['skills'][:5])}")
    else:
        print(f"Error: {results['error']}")


if __name__ == "__main__":
    main() 