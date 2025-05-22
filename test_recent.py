import requests
import json
import os
import time
from datetime import datetime
import random
import sys
from collections import OrderedDict

# Configuration
FL_API_BASE_URL = "https://www.freelancer.com/api"
PROJECTS_ENDPOINT = "/projects/0.1/projects/active"
API_KEY = os.getenv("FREELANCER_API_KEY", "")
LOG_FILE = "new_projects.log"

def clear_console():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_recent_projects(limit=10):
    """
    Fetch most recent projects from Freelancer API
    """
    endpoint = f"{FL_API_BASE_URL}{PROJECTS_ENDPOINT}"
    
    params = {
        'limit': limit,
        'full_description': True,
        'job_details': True,
        'user_details': True,
        'sort_field': 'time_updated',
        'sort_direction': 'desc',
        'project_statuses[]': ['active'],
        'active_only': True,
        'project_types[]': ['fixed', 'hourly'],
        'compact': True,
        'or_search_query': True,
        'timeframe': 'last_24_hours'  # Only get projects from last 24 hours
    }
    
    headers = {
        'Freelancer-OAuth-V1': API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        # Add random timeout between requests to avoid rate limiting
        time.sleep(random.uniform(1.0, 2.0))
        
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching projects: {str(e)}")
        return None

def format_time(timestamp):
    """Convert timestamp to readable format"""
    try:
        return datetime.fromtimestamp(timestamp)
    except:
        return None

def format_time_difference(time_diff_seconds):
    """Format time difference in a readable way"""
    if time_diff_seconds < 60:
        return f"{time_diff_seconds} seconds"
    elif time_diff_seconds < 3600:
        minutes = time_diff_seconds // 60
        seconds = time_diff_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = time_diff_seconds // 3600
        minutes = (time_diff_seconds % 3600) // 60
        seconds = time_diff_seconds % 60
        return f"{hours}h {minutes}m {seconds}s"

def log_new_project(project):
    """Log new project to file with time differences"""
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            now = datetime.now()
            
            # Get project timestamps
            submitted_time = format_time(project.get('time_submitted', 0))
            updated_time = format_time(project.get('time_updated', 0))
            
            # Calculate time differences
            if submitted_time:
                time_since_submit = (now - submitted_time).total_seconds()
                submit_diff = format_time_difference(int(time_since_submit))
            else:
                submit_diff = "unknown"
                
            if updated_time:
                time_since_update = (now - updated_time).total_seconds()
                update_diff = format_time_difference(int(time_since_update))
            else:
                update_diff = "unknown"
            
            # Format the log entry
            log_entry = (
                f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] New Project: {project['title']}\n"
                f"  ID: {project['id']}\n"
                f"  URL: {project['url']}\n"
                f"  Submitted: {submitted_time.strftime('%Y-%m-%d %H:%M:%S') if submitted_time else 'unknown'} "
                f"({submit_diff} ago)\n"
                f"  Updated: {updated_time.strftime('%Y-%m-%d %H:%M:%S') if updated_time else 'unknown'} "
                f"({update_diff} ago)\n"
                f"{'='*80}\n"
            )
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to log file: {str(e)}")

def display_projects(projects_list, new_projects):
    """Display projects with newest at the bottom"""
    clear_console()
    
    print("\n=== LATEST PROJECTS ===")
    print("(Newest at bottom)")
    print("=" * 80)
    
    # Display all projects in reverse order (newest last)
    for project in reversed(projects_list):
        # Determine if this is a new project
        is_new = project['id'] in new_projects
        
        # Calculate time differences
        now = datetime.now()
        submitted_time = format_time(project.get('time_submitted', 0))
        time_diff = ""
        if submitted_time:
            time_since_submit = (now - submitted_time).total_seconds()
            time_diff = f" ({format_time_difference(int(time_since_submit))} ago)"
        
        # Format the line with optional highlighting
        line = f"{project['time_updated']} | {project['title']} (ID: {project['id']}){time_diff}"
        if is_new:
            print(f"\033[92m→ {line}\033[0m")
        else:
            print(line)
    
    # Display stats at the top
    print("\n=== STATS ===")
    print(f"Total Projects Shown: {len(projects_list)}")
    print(f"New Projects: {len(new_projects)}")
    print(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nPress Ctrl+C to stop")

def main():
    print("\nStarting recent projects monitor...")
    print(f"Logging new projects to: {LOG_FILE}")
    
    seen_project_ids = set()  # Track seen project IDs
    
    while True:
        try:
            # Fetch latest projects
            result = get_recent_projects(limit=10)
            
            if not result or 'result' not in result or 'projects' not in result['result']:
                print("\nNo projects in response, waiting 4 seconds...")
                time.sleep(4)
                continue
            
            projects = result['result']['projects']
            if not projects:
                print("\nEmpty projects list, waiting 4 seconds...")
                time.sleep(4)
                continue
            
            # Track new projects in this batch
            new_project_ids = set()
            current_projects = []
            
            # Process projects
            for project in projects:
                project_id = project.get('id')
                if not project_id:
                    continue
                
                # Create project entry
                project_entry = {
                    'id': project_id,
                    'title': project.get('title', 'No Title'),
                    'time_submitted': format_time(project.get('time_submitted', 0)),
                    'time_updated': format_time(project.get('time_updated', 0)),
                    'url': f"https://www.freelancer.com/projects/{project_id}"
                }
                
                # Check if this is a new project
                if project_id not in seen_project_ids:
                    new_project_ids.add(project_id)
                    seen_project_ids.add(project_id)
                    log_new_project(project)  # Log with original project data
                
                # Format times for display
                project_entry['time_submitted'] = project_entry['time_submitted'].strftime('%Y-%m-%d %H:%M:%S') if project_entry['time_submitted'] else 'Unknown'
                project_entry['time_updated'] = project_entry['time_updated'].strftime('%Y-%m-%d %H:%M:%S') if project_entry['time_updated'] else 'Unknown'
                current_projects.append(project_entry)
            
            # Display updated project list
            display_projects(current_projects, new_project_ids)
            
            # Wait before next fetch
            time.sleep(4)
            
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
            break
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            time.sleep(4)

if __name__ == "__main__":
    main() 