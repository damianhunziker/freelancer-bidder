#!/usr/bin/env python3
"""
Test script for LinkedIn Jobs Fetcher

This script demonstrates how to use the LinkedIn Jobs Fetcher to search for jobs.
"""

import sys
import os
from linkedin_fetcher import LinkedInJobsFetcher


def test_basic_search():
    """Test basic job search functionality."""
    print("=== Testing LinkedIn Jobs Fetcher ===\n")
    
    # Initialize the fetcher
    fetcher = LinkedInJobsFetcher()
    
    # Test 1: Basic search
    print("Test 1: Basic job search for Python developers in Germany")
    results = fetcher.search_jobs(
        keywords=["Python", "Django", "Flask"],
        location="Germany",
        limit=5
    )
    
    if results['success']:
        print(f"✅ Success! Found {results['count']} jobs")
        
        # Display results
        for i, job in enumerate(results['jobs'], 1):
            print(f"\n--- Job {i} ---")
            print(f"Title: {job['title']}")
            print(f"Company: {job['company']['name']}")
            print(f"Location: {job['location']}")
            print(f"URL: {job['url']}")
            
        # Save to file
        filename = fetcher.save_jobs_to_file(results, "test_linkedin_jobs.json")
        print(f"\n💾 Results saved to: {filename}")
        
    else:
        print(f"❌ Error: {results['error']}")
    
    print("\n" + "="*50)


def test_advanced_search():
    """Test advanced search with additional filters."""
    print("Test 2: Advanced job search with filters")
    
    fetcher = LinkedInJobsFetcher()
    
    results = fetcher.search_jobs(
        keywords=["Backend Developer", "API"],
        location="Berlin, Germany",
        limit=3,
        job_type="full-time",
        experience_level="mid"
    )
    
    if results['success']:
        print(f"✅ Advanced search successful! Found {results['count']} jobs")
        
        # Display more detailed results
        for i, job in enumerate(results['jobs'], 1):
            print(f"\n--- Advanced Job {i} ---")
            print(f"Title: {job['title']}")
            print(f"Company: {job['company']['name']}")
            print(f"Location: {job['location']}")
            print(f"Experience Level: {job['experience_level']}")
            print(f"Skills: {', '.join(job['skills'][:3])}")
            print(f"Job Type: {job['job_type']}")
            
    else:
        print(f"❌ Advanced search failed: {results['error']}")
    
    print("\n" + "="*50)


def test_configuration():
    """Test configuration and setup."""
    print("Test 3: Configuration check")
    
    from config import (
        LINKEDIN_API_KEY,
        LINKEDIN_ACCESS_TOKEN,
        LINKEDIN_API_BASE_URL,
        LINKEDIN_DEFAULT_KEYWORDS
    )
    
    print("Configuration status:")
    print(f"API Key configured: {'✅ Yes' if LINKEDIN_API_KEY else '❌ No'}")
    print(f"Access Token configured: {'✅ Yes' if LINKEDIN_ACCESS_TOKEN else '❌ No'}")
    print(f"API Base URL: {LINKEDIN_API_BASE_URL}")
    print(f"Default Keywords: {LINKEDIN_DEFAULT_KEYWORDS}")
    
    if not LINKEDIN_ACCESS_TOKEN:
        print("\n⚠️  Warning: LinkedIn access token not configured!")
        print("Please set the following constants in config.py:")
        print("- LINKEDIN_API_KEY")
        print("- LINKEDIN_CLIENT_SECRET") 
        print("- LINKEDIN_ACCESS_TOKEN")
        print("\nAdd your LinkedIn API credentials directly to config.py.")
    
    print("\n" + "="*50)


if __name__ == "__main__":
    print("LinkedIn Jobs Fetcher Test Suite")
    print("=" * 50)
    
    # Run tests
    test_configuration()
    test_basic_search()
    test_advanced_search()
    
    print("\nTest suite completed! 🎉")
    print("\nTo get started:")
    print("1. Set up your LinkedIn API credentials in environment variables")
    print("2. Run: python test_linkedin_fetcher.py")
    print("3. Check the generated JSON files in the jobs/ directory") 