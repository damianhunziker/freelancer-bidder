def main():
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
                'limit': 20,
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
            # ... existing code ...
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        print(traceback.format_exc())

    # ... existing code ... 