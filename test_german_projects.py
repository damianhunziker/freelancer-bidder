#!/usr/bin/env python3
"""
Test-Script: Deutsche Projekte von Freelancer API abrufen
Führt die gleiche Query wie bidder.py aus, aber mit languages="de" Filter
"""

import requests
import json
from datetime import datetime
import config
import time
import traceback

def log_api_request(endpoint: str, params: dict, response_status: int, response_data: dict = None):
    """Log API request details to console"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"📝 API LOG [{timestamp}]: {endpoint} | STATUS: {response_status}")
        
        if params:
            key_params = {}
            if 'limit' in params:
                key_params['limit'] = params['limit']
            if 'query' in params:
                key_params['query'] = params['query']
            if 'languages[]' in params:
                key_params['languages'] = params['languages[]']
                
            if key_params:
                params_str = " | ".join([f"{k}={v}" for k, v in key_params.items()])
                print(f"   PARAMS: {params_str}")
        
        if response_data and 'result' in response_data:
            result = response_data['result']
            if 'projects' in result:
                print(f"   RESPONSE: projects_count={len(result['projects'])}")
                
    except Exception as e:
        print(f"Error logging API request: {str(e)}")

def get_german_projects(limit: int = 20, search_query: str = None) -> dict:
    """Get active German projects from Freelancer API"""
    try:
        endpoint = f'{config.FL_API_BASE_URL}{config.PROJECTS_ENDPOINT}'
        
        # Base parameters - gleich wie in bidder.py
        params = {
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
            'or_search_query': True,
            'project_types[]': ['fixed', 'hourly'],
            # WICHTIG: Deutscher Sprach-Filter
            'languages[]': ['de']
        }
        
        # Add search query if provided
        if search_query and search_query.strip():
            params['query'] = search_query.strip()
        
        headers = {
            'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        print(f"🌐 Sende API-Request für deutsche Projekte...")
        print(f"   Endpoint: {endpoint}")
        print(f"   Limit: {limit}")
        print(f"   Search Query: {search_query if search_query else 'None'}")
        print(f"   Language Filter: de")
        
        response = requests.get(endpoint, headers=headers, params=params)
        
        # Log the API request
        try:
            response_data = response.json() if response.status_code == 200 else None
            log_api_request(endpoint, params, response.status_code, response_data)
        except Exception as e:
            log_api_request(endpoint, params, response.status_code)
            print(f"Error logging API request: {str(e)}")
        
        if response.status_code == 429:  # Rate limit exceeded
            print(f"🚫 Rate Limiting erkannt!")
            return {'result': {'projects': []}}
        elif response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
        
        data = response_data or response.json()
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

def format_project_output(project: dict, index: int) -> str:
    """Format project for console output"""
    project_id = project.get('id', 'Unknown')
    title = project.get('title', 'No Title')
    description = project.get('description', 'No description')[:200] + "..." if len(project.get('description', '')) > 200 else project.get('description', 'No description')
    
    # Currency and budget info
    currency_info = project.get('currency', {'code': 'USD', 'sign': '$'})
    currency_symbol = currency_info.get('sign', '$')
    currency_code = currency_info.get('code', 'USD')
    
    project_type = project.get('type', 'unknown')
    
    if project_type == 'hourly':
        rate = project.get('hourly_rate', 0)
        budget_display = f"{currency_symbol}{rate}/hr ({currency_code})"
    else:
        budget = project.get('budget', {})
        budget_min = budget.get('minimum', 0)
        budget_max = budget.get('maximum', 0)
        budget_display = f"{currency_symbol}{budget_min} - {currency_symbol}{budget_max} ({currency_code})"
    
    # Bid statistics
    bid_stats = project.get('bid_stats', {})
    bid_count = bid_stats.get('bid_count', 0)
    bid_avg = bid_stats.get('bid_avg', 0)
    
    # Time info
    submit_time = project.get('submitdate') or project.get('time_submitted', 0)
    submit_datetime = datetime.fromtimestamp(submit_time).strftime('%Y-%m-%d %H:%M:%S') if submit_time else 'Unknown'
    
    # Country info
    country = 'Unknown'
    if 'owner' in project and project['owner'] and 'location' in project['owner']:
        location = project['owner']['location']
        if location and 'country' in location and location['country']:
            country = location['country'].get('name', 'Unknown')
    
    # Language
    language = project.get('language', 'unknown')
    
    # Skills
    skills = []
    if 'jobs' in project:
        skills = [job.get('name', '') for job in project['jobs']]
    
    output = f"""
{'='*100}
🇩🇪 DEUTSCHES PROJEKT #{index}
{'='*100}
📌 ID: {project_id}
🔗 URL: https://www.freelancer.com/projects/{project_id}
📋 Titel: {title}
🌍 Land: {country}
🗣️ Sprache: {language}
💰 Budget: {budget_display}
📊 Typ: {project_type.upper()}
👥 Gebote: {bid_count} (Durchschnitt: {currency_symbol}{bid_avg} {currency_code})
📅 Eingereicht: {submit_datetime}
🔧 Skills: {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}

📝 Beschreibung:
{description}
"""
    return output

def main():
    """Hauptfunktion"""
    print("🇩🇪 Test: Deutsche Projekte von Freelancer API")
    print("=" * 80)
    
    # Konfiguration
    limit = 20
    search_query = input("🔍 Suchbegriffe (optional, Enter für alle deutschen Projekte): ").strip()
    
    if not search_query:
        search_query = None
    
    print(f"\n🚀 Starte Abfrage...")
    print(f"   Limit: {limit} Projekte")
    print(f"   Sprache: Deutsch (de)")
    print(f"   Suchbegriffe: {search_query if search_query else 'Alle'}")
    
    # API Call
    result = get_german_projects(limit=limit, search_query=search_query)
    
    # Ergebnisse verarbeiten
    if 'result' not in result or 'projects' not in result['result']:
        print("❌ Keine Projekte in der API-Antwort gefunden")
        return
    
    projects = result['result']['projects']
    
    if not projects:
        print("❌ Keine deutschen Projekte gefunden")
        return
    
    print(f"\n✅ {len(projects)} deutsche Projekte gefunden!")
    print("=" * 80)
    
    # Projekte ausgeben
    for index, project in enumerate(projects, 1):
        project_output = format_project_output(project, index)
        print(project_output)
        
        # Pause zwischen Ausgaben für bessere Lesbarkeit
        if index < len(projects):
            input("\n⏸️  Drücke Enter für nächstes Projekt...")
    
    print("\n🎉 Alle deutschen Projekte angezeigt!")
    
    # Statistiken
    print(f"\n📊 STATISTIKEN:")
    print(f"   Gefundene Projekte: {len(projects)}")
    
    # Länder-Verteilung
    countries = {}
    for project in projects:
        country = 'Unknown'
        if 'owner' in project and project['owner'] and 'location' in project['owner']:
            location = project['owner']['location']
            if location and 'country' in location and location['country']:
                country = location['country'].get('name', 'Unknown')
        countries[country] = countries.get(country, 0) + 1
    
    print(f"   Länder-Verteilung:")
    for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True):
        print(f"     {country}: {count}")
    
    # Projekt-Typen
    types = {}
    for project in projects:
        project_type = project.get('type', 'unknown')
        types[project_type] = types.get(project_type, 0) + 1
    
    print(f"   Projekt-Typen:")
    for ptype, count in types.items():
        print(f"     {ptype}: {count}")

if __name__ == "__main__":
    main() 