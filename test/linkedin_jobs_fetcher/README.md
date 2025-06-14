# LinkedIn Jobs Fetcher

A Python module for fetching job listings from the LinkedIn API.

## Features

- 🔍 Search for jobs by keywords, location, and filters
- 📊 Extract detailed job information including company details, skills, and salary
- 💾 Save results to JSON files for further processing
- 🔧 Configurable search parameters
- 🛡️ Built-in error handling and rate limiting awareness

## Setup

### 1. LinkedIn API Access

To use this module, you need LinkedIn API credentials:

1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com/)
2. Create a new app or use an existing one
3. Get your API credentials:
   - Client ID (API Key)
   - Client Secret
   - Access Token

### 2. Configuration

Add your LinkedIn API credentials directly to the central `config.py` file:

```python
# LinkedIn API Configuration
LINKEDIN_API_KEY = "your_client_id_here"
LINKEDIN_CLIENT_SECRET = "your_client_secret_here"
LINKEDIN_ACCESS_TOKEN = "your_access_token_here"
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

The module uses constants from the central `config.py` file:

```python
# LinkedIn API Configuration
LINKEDIN_API_KEY = ""  # LinkedIn API Key - add your LinkedIn app client ID here
LINKEDIN_CLIENT_SECRET = ""  # LinkedIn Client Secret - add your LinkedIn app client secret here
LINKEDIN_ACCESS_TOKEN = ""  # LinkedIn Access Token - add your access token here
LINKEDIN_API_BASE_URL = "https://api.linkedin.com/v2"
LINKEDIN_JOBS_ENDPOINT = "/jobSearchResults"
LINKEDIN_MAX_RESULTS = 25
LINKEDIN_DEFAULT_KEYWORDS = ["software developer", "web developer", "python developer"]
LINKEDIN_DEFAULT_LOCATION = "Germany"
```

## Usage

### Basic Example

```python
from linkedin_jobs_fetcher import LinkedInJobsFetcher

# Initialize the fetcher
fetcher = LinkedInJobsFetcher()

# Search for jobs
results = fetcher.search_jobs(
    keywords=["Python developer", "Django"],
    location="Germany",
    limit=10
)

if results['success']:
    print(f"Found {results['count']} jobs")
    
    # Save to file
    fetcher.save_jobs_to_file(results)
    
    # Display results
    for job in results['jobs']:
        print(f"Title: {job['title']}")
        print(f"Company: {job['company']['name']}")
        print(f"Location: {job['location']}")
        print(f"URL: {job['url']}")
        print("---")
else:
    print(f"Error: {results['error']}")
```

### Advanced Search with Filters

```python
# Search with additional filters
results = fetcher.search_jobs(
    keywords=["Backend Developer", "API"],
    location="Berlin, Germany",
    limit=20,
    job_type="full-time",
    experience_level="mid",
    company_id="specific_company_id"
)
```

### Get Detailed Job Information

```python
# Get details for a specific job
job_details = fetcher.get_job_details("job_id_here")
```

## API Methods

### `search_jobs(keywords, location, limit, job_type, experience_level, company_id)`

Search for jobs with various filters.

**Parameters:**
- `keywords` (List[str]): Keywords to search for
- `location` (str): Location to search in
- `limit` (int): Maximum number of results
- `job_type` (str): Job type filter
- `experience_level` (str): Experience level filter  
- `company_id` (str): Specific company ID

**Returns:** Dictionary with search results

### `get_job_details(job_id)`

Get detailed information about a specific job.

**Parameters:**
- `job_id` (str): LinkedIn job ID

**Returns:** Dictionary with job details

### `save_jobs_to_file(jobs_data, filename)`

Save job search results to a JSON file.

**Parameters:**
- `jobs_data` (Dict): Job search results
- `filename` (str): Custom filename (optional)

**Returns:** Path to saved file

## Response Format

```json
{
  "success": true,
  "total_results": 150,
  "count": 10,
  "timestamp": "2024-01-15T10:30:00",
  "jobs": [
    {
      "id": "job_id",
      "title": "Senior Python Developer",
      "company": {
        "id": "company_id",
        "name": "Tech Company GmbH",
        "logo": "company_logo_url",
        "industry": ["Technology"],
        "size": "51-200"
      },
      "location": "Berlin, Germany",
      "description": "Job description...",
      "job_type": ["full-time"],
      "posted_date": 1705305600000,
      "expires_date": 1707897600000,
      "url": "https://www.linkedin.com/jobs/view/job_id",
      "skills": ["Python", "Django", "REST API"],
      "experience_level": "mid",
      "industry": ["Technology"],
      "salary": {
        "currency": "EUR",
        "min_amount": 60000,
        "max_amount": 80000,
        "period": "yearly"
      },
      "applicant_count": 45
    }
  ]
}
```

## Testing

Run the test script to verify everything is working:

```bash
cd linkedin_jobs_fetcher
python test_linkedin_fetcher.py
```

## Error Handling

The module includes comprehensive error handling for:
- Authentication failures
- Rate limiting (HTTP 429)
- Network errors
- Invalid parameters
- API response parsing errors

## Rate Limiting

LinkedIn API has rate limits. The module:
- Respects API limits (max 25 results per request)
- Provides clear error messages for rate limit issues
- Includes retry logic recommendations

## Files Structure

```
linkedin_jobs_fetcher/
├── __init__.py              # Package initialization
├── linkedin_fetcher.py      # Main fetcher class
├── test_linkedin_fetcher.py # Test and example script
├── requirements.txt         # Python dependencies
└── README.md               # This documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is part of the freelancer-bidder application. 