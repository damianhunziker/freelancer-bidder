#!/usr/bin/env python3
"""
Example usage of LinkedIn Jobs Fetcher

This script shows practical examples of using the LinkedIn Jobs Fetcher.
"""

import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linkedin_jobs_fetcher import LinkedInJobsFetcher


def search_python_jobs():
    """Example: Search for Python developer jobs in Germany."""
    print("🔍 Searching for Python developer jobs in Germany...")
    
    fetcher = LinkedInJobsFetcher()
    
    # Search for Python jobs
    results = fetcher.search_jobs(
        keywords=["Python", "Django", "Flask", "FastAPI"],
        location="Germany",
        limit=15
    )
    
    if results['success']:
        print(f"✅ Found {results['count']} Python jobs!")
        
        # Save results
        filename = fetcher.save_jobs_to_file(results, "python_jobs_germany.json")
        
        # Show top jobs
        print("\n📋 Top Python Jobs:")
        for i, job in enumerate(results['jobs'][:5], 1):
            print(f"\n{i}. {job['title']}")
            print(f"   Company: {job['company']['name']}")
            print(f"   Location: {job['location']}")
            print(f"   Skills: {', '.join(job['skills'][:3])}")
            print(f"   URL: {job['url']}")
    else:
        print(f"❌ Error: {results['error']}")


def search_remote_jobs():
    """Example: Search for remote developer jobs."""
    print("\n🏠 Searching for remote developer jobs...")
    
    fetcher = LinkedInJobsFetcher()
    
    # Search for remote jobs
    results = fetcher.search_jobs(
        keywords=["Remote", "Frontend Developer", "React"],
        location="Remote",
        limit=10,
        job_type="full-time"
    )
    
    if results['success']:
        print(f"✅ Found {results['count']} remote jobs!")
        
        # Save results
        filename = fetcher.save_jobs_to_file(results, "remote_frontend_jobs.json")
        
        # Show remote jobs
        print("\n📋 Remote Frontend Jobs:")
        for i, job in enumerate(results['jobs'][:3], 1):
            print(f"\n{i}. {job['title']}")
            print(f"   Company: {job['company']['name']}")
            print(f"   Type: {', '.join(job['job_type'])}")
            print(f"   Skills: {', '.join(job['skills'][:4])}")
    else:
        print(f"❌ Error: {results['error']}")


def search_startup_jobs():
    """Example: Search for startup jobs with specific criteria."""
    print("\n🚀 Searching for startup developer jobs...")
    
    fetcher = LinkedInJobsFetcher()
    
    # Search for startup/tech jobs
    results = fetcher.search_jobs(
        keywords=["Startup", "Software Engineer", "JavaScript"],
        location="Berlin, Germany",
        limit=8,
        experience_level="mid"
    )
    
    if results['success']:
        print(f"✅ Found {results['count']} startup jobs!")
        
        # Save results
        filename = fetcher.save_jobs_to_file(results, "startup_jobs_berlin.json")
        
        # Analyze results
        print("\n📊 Job Analysis:")
        companies = [job['company']['name'] for job in results['jobs']]
        skills = []
        for job in results['jobs']:
            skills.extend(job['skills'])
        
        print(f"   Companies: {len(set(companies))} unique companies")
        print(f"   Most common skills: {', '.join(list(set(skills))[:5])}")
        
    else:
        print(f"❌ Error: {results['error']}")


def main():
    """Main function to run all examples."""
    print("=" * 60)
    print("LinkedIn Jobs Fetcher - Example Usage")
    print("=" * 60)
    
    # Check configuration first
    fetcher = LinkedInJobsFetcher()
    if not fetcher.access_token:
        print("⚠️  Warning: LinkedIn API credentials not configured!")
        print("Please set up your LinkedIn API credentials in config.py first.")
        print("See README.md for setup instructions.")
        return
    
    # Run examples
    try:
        search_python_jobs()
        search_remote_jobs()
        search_startup_jobs()
        
        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("📁 Check the jobs/ directory for saved JSON files.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        print("Please check your LinkedIn API configuration.")


if __name__ == "__main__":
    main() 