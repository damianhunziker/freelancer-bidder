import json
import re
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures
import requests
from typing import List, Dict
import socket
import ssl

def check_domain(domain: str) -> tuple[str, bool]:
    try:
        # First try DNS resolution
        socket.gethostbyname(domain)
        
        # Then try HTTPS connection
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                return domain, True
    except:
        try:
            # Fallback to HTTP request
            response = requests.head(f"http://{domain}", timeout=3, allow_redirects=True)
            return domain, response.status_code < 400
        except:
            return domain, False

def extract_domains(text: str) -> List[str]:
    # Find URLs in the text
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    domains = []
    for url in urls:
        try:
            domain = urlparse(url).netloc
            if domain and 'skype.com' not in domain:
                domains.append(domain)
        except:
            continue
    return domains

def parse_messages(file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content.startswith('%'):
                content = content[1:]
            
            data = json.loads(content)
            all_domains = set()
            
            if 'conversations' in data:
                for conversation in data['conversations']:
                    if 'MessageList' in conversation:
                        for message in conversation['MessageList']:
                            if 'content' in message and message['content']:
                                content = message['content']
                                domains = extract_domains(content)
                                all_domains.update(domains)
            
            print("\nDomain Reachability Results:")
            print("-" * 80)
            
            # Check domains and print results immediately
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(check_domain, domain) for domain in all_domains]
                for future in concurrent.futures.as_completed(futures):
                    domain, is_reachable = future.result()
                    status_icon = "🟢" if is_reachable else "🔴"
                    print(f"{status_icon} {domain}")
            
    except Exception as e:
        print(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    file_path = "8_damian42639_export/messages.json"
    parse_messages(file_path)
