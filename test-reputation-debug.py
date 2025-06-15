#!/usr/bin/env python3

"""
Debug script to check the reputation data structure from the Freelancer API
"""

import sys
import json
from bidder import get_user_reputation, FileCache
import config

def debug_reputation_structure():
    print('🔍 Testing Reputation Data Structure')
    print('====================================\n')
    
    cache = FileCache(cache_dir='cache', expiry=3600)
    
    # Test with a known user ID (from a project)
    test_user_ids = [
        # Add some user IDs from existing projects
        # We'll get these from project files
    ]
    
    # Try to get some user IDs from existing job files
    import os
    from pathlib import Path
    
    jobs_dir = Path('jobs')
    if jobs_dir.exists():
        for job_file in list(jobs_dir.glob('job_*.json'))[:3]:  # Test with first 3 projects
            try:
                with open(job_file, 'r', encoding='utf-8') as f:
                    job_data = json.load(f)
                
                # Try to extract user ID from project (this might not exist in the JSON)
                # We'll need to get it from the original project data
                print(f"📄 Checking project file: {job_file.name}")
                
                # For now, let's use some example user IDs
                # In a real scenario, we'd extract owner_id from the original project data
                
            except Exception as e:
                print(f"❌ Error reading {job_file}: {e}")
    
    # Test with example user IDs (these are just for testing structure)
    test_user_ids = [3953491]  # Our own user ID as a test
    
    for user_id in test_user_ids:
        print(f"\n🧪 Testing User ID: {user_id}")
        print("=" * 50)
        
        try:
            reputation_data = get_user_reputation(user_id, cache)
            
            print("Raw reputation response structure:")
            print(json.dumps(reputation_data, indent=2, default=str))
            
            if 'result' in reputation_data:
                result = reputation_data['result']
                print(f"\n📊 Result structure for user {user_id}:")
                
                # Check if result is a dict with user_id as key
                if isinstance(result, dict):
                    for key, value in result.items():
                        print(f"Key: {key}")
                        if isinstance(value, dict):
                            print(f"  Available fields: {list(value.keys())}")
                            
                            # Check for expected fields
                            expected_fields = ['entire_history', 'earnings_score', 'earning_score', 'stats', 'complete', 'overall']
                            found_fields = []
                            
                            for field in expected_fields:
                                if field in value:
                                    found_fields.append(field)
                                    print(f"  ✅ Found field '{field}': {value[field]}")
                            
                            if not found_fields:
                                print(f"  ❌ None of the expected fields found!")
                                print(f"  Available fields: {list(value.keys())}")
                                
                            # Check nested structure
                            if 'entire_history' in value:
                                entire_history = value['entire_history']
                                print(f"  📈 entire_history structure: {entire_history}")
                                if isinstance(entire_history, dict):
                                    print(f"    - complete: {entire_history.get('complete', 'NOT FOUND')}")
                                    print(f"    - overall: {entire_history.get('overall', 'NOT FOUND')}")
                            
                            if 'earnings_score' in value:
                                print(f"  💰 earnings_score: {value['earnings_score']}")
                            elif 'earning_score' in value:
                                print(f"  💰 earning_score: {value['earning_score']}")
                        else:
                            print(f"  Value type: {type(value)}, Value: {value}")
                else:
                    print(f"Result is not a dict, type: {type(result)}")
                    print(f"Result content: {result}")
            else:
                print("❌ No 'result' key in reputation_data")
                print(f"Available keys: {list(reputation_data.keys())}")
                
        except Exception as e:
            print(f"❌ Error getting reputation for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n🔧 Debugging Summary:")
    print("====================")
    print("If you see 'entire_history' and 'earnings_score' fields, the structure is correct.")
    print("If not, we need to adjust the prepare_project_data function to match the actual API structure.")
    print("\nNext steps:")
    print("1. Check the actual field names in the API response")
    print("2. Update prepare_project_data() to use the correct field names") 
    print("3. Test with a real user ID from a current project")

if __name__ == "__main__":
    debug_reputation_structure() 