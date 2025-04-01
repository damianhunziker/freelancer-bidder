import os
import json
import glob

def generate_list():
    jobs_dir = 'jobs'
    projects = []
    
    # Read all JSON files in the jobs directory that match the pattern job_*.json
    job_files = glob.glob(os.path.join(jobs_dir, 'job_*.json'))
    
    for file_path in job_files:
        try:
            with open(file_path, 'r') as f:
                project_data = json.load(f)
                # Ensure the project data has all required fields
                if all(key in project_data for key in ['project_details', 'project_url', 'timestamp']):
                    projects.append(project_data)
                else:
                    print(f"Warning: Skipping {file_path} - missing required fields")
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    # Sort projects by timestamp in descending order (newest first)
    projects.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Write the list.json file
    output_path = os.path.join(jobs_dir, 'list.json')
    try:
        with open(output_path, 'w') as f:
            json.dump(projects, f, indent=2)
        print(f"Successfully created {output_path} with {len(projects)} projects")
    except Exception as e:
        print(f"Error writing list.json: {e}")

if __name__ == '__main__':
    generate_list() 