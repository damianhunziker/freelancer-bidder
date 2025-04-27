import requests
import re
from typing import List, Dict, Any
from urllib.parse import urlparse
from config import FREELANCER_API_KEY

# Configuration
if not FREELANCER_API_KEY:
    raise ValueError("FREELANCER_API_KEY not found in config.py")

BASE_URL = "https://www.freelancer.com/api/messages/0.1"
HEADERS = {
    "freelancer-oauth-v1": FREELANCER_API_KEY
}

def get_threads(offset: int = 0, limit: int = 100) -> List[Dict[Any, Any]]:
    """Get all message threads."""
    url = f"{BASE_URL}/threads"
    params = {
        "offset": offset,
        "limit": limit,
        "status": "active"
    }
    
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    
    return response.json().get("result", {}).get("threads", [])

def get_messages_for_thread(thread_id: int, offset: int = 0, limit: int = 100) -> List[Dict[Any, Any]]:
    """Get all messages for a specific thread."""
    url = f"{BASE_URL}/threads/{thread_id}/messages"
    params = {
        "offset": offset,
        "limit": limit
    }
    
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    
    return response.json().get("result", {}).get("messages", [])

def extract_domains(text: str) -> List[str]:
    """Extract domains from text using regex pattern."""
    # Pattern to match URLs or domain names
    pattern = r'(?:https?://)?(?:[\w-]+\.)+(?:com|net|org|edu|gov|mil|biz|info|mobi|name|aero|asia|jobs|museum|[a-z]{2})\b'
    
    matches = re.finditer(pattern, text.lower())
    domains = []
    
    for match in matches:
        domain = match.group(0)
        if not domain.startswith('http'):
            domain = 'http://' + domain
        parsed = urlparse(domain)
        domains.append(parsed.netloc)
    
    return list(set(domains))  # Remove duplicates

def scan_messages_for_domains():
    """Main function to scan all messages for domains."""
    print("Starting domain scan...")
    
    # Get all threads
    offset = 0
    limit = 100
    while True:
        threads = get_threads(offset, limit)
        if not threads:
            break
            
        for thread in threads:
            thread_id = thread.get("thread_id")
            
            # Get messages for this thread
            messages = get_messages_for_thread(thread_id)
            
            for message in messages:
                message_text = message.get("message", "")
                domains = extract_domains(message_text)
                
                if domains:
                    print("\nFound domains in message:")
                    print(f"Thread ID: {thread_id}")
                    print(f"From User: {message.get('from_user', {}).get('username', 'Unknown')}")
                    print(f"Domains found: {', '.join(domains)}")
                    print(f"Message: {message_text[:200]}...")  # Show first 200 chars
                    print("-" * 80)
        
        offset += limit
        print(f"Processed {offset} threads...")

if __name__ == "__main__":
    try:
        scan_messages_for_domains()
    except Exception as e:
        print(f"Error occurred: {str(e)}")
