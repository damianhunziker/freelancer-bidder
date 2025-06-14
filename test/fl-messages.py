import requests
import re
import json
import csv
import os
import socket
import ssl
import concurrent.futures
from datetime import datetime
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

# Output directory
OUTPUT_DIR = "fl_messages"

def check_domain(domain: str) -> tuple[str, bool]:
    """Check if a domain is reachable online."""
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

def ensure_output_dir():
    """Ensure the output directory exists."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 Created directory: {OUTPUT_DIR}")

def save_json_data(data: Any, filename: str) -> None:
    """Save data to a JSON file in the fl_messages directory."""
    ensure_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = os.path.join(OUTPUT_DIR, f"{timestamp}_{filename}")
    
    with open(full_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved {full_filename}")

def save_csv_data(data: List[Dict], filename: str) -> None:
    """Save data to a CSV file in the fl_messages directory."""
    if not data:
        return
        
    ensure_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = os.path.join(OUTPUT_DIR, f"{timestamp}_{filename}")
    
    with open(full_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    print(f"💾 Saved {full_filename}")

def test_authentication():
    """Test if the API key is working."""
    print("Testing authentication...")
    url = f"{BASE_URL}/threads"
    params = {"offset": 0, "limit": 1}
    
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        print("✓ Authentication successful!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ Authentication failed: {e}")
        return False

def get_all_threads() -> List[Dict[Any, Any]]:
    """Get all message threads."""
    print("Fetching all threads...")
    all_threads = []
    offset = 0
    limit = 100
    
    while True:
        url = f"{BASE_URL}/threads"
        params = {
            "offset": offset,
            "limit": limit,
            "last_message": True,  # Get last message in each thread
            "message_count": True,  # Get message count
            "user_details": True    # Get user details
        }
        
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        
        result = response.json().get("result", {})
        threads = result.get("threads", [])
        
        if not threads:
            break
            
        all_threads.extend(threads)
        print(f"  Fetched {len(threads)} threads (total: {len(all_threads)})")
        
        offset += limit
        
        # If we got fewer threads than the limit, we're done
        if len(threads) < limit:
            break
    
    print(f"✓ Total threads found: {len(all_threads)}")
    
    # Save threads JSON
    save_json_data(all_threads, "freelancer_threads.json")
    
    return all_threads

def get_all_messages(thread_ids: List[int]) -> List[Dict[Any, Any]]:
    """Get all messages from specified threads."""
    if not thread_ids:
        return []
        
    print(f"Fetching messages from {len(thread_ids)} threads...")
    all_messages = []
    
    # Process threads in batches to avoid URL length limits
    batch_size = 50
    for i in range(0, len(thread_ids), batch_size):
        batch_thread_ids = thread_ids[i:i + batch_size]
        
        offset = 0
        limit = 100
        
        while True:
            url = f"{BASE_URL}/messages"
            
            # Build threads[] parameter
            params = {
                "offset": offset,
                "limit": limit,
                "thread_details": True,
                "user_details": True
            }
            
            # Add threads[] parameters
            for thread_id in batch_thread_ids:
                params[f"threads[]"] = thread_id
            
            # Convert to proper format for requests
            params_list = []
            for key, value in params.items():
                if key == "threads[]":
                    continue
                params_list.append((key, value))
            
            # Add all thread IDs
            for thread_id in batch_thread_ids:
                params_list.append(("threads[]", thread_id))
            
            response = requests.get(url, headers=HEADERS, params=params_list)
            response.raise_for_status()
            
            result = response.json().get("result", {})
            messages = result.get("messages", [])
            
            if not messages:
                break
                
            all_messages.extend(messages)
            print(f"  Batch {i//batch_size + 1}: Fetched {len(messages)} messages (total: {len(all_messages)})")
            
            offset += limit
            
            # If we got fewer messages than the limit, we're done with this batch
            if len(messages) < limit:
                break
    
    print(f"✓ Total messages found: {len(all_messages)}")
    
    # Save messages JSON
    save_json_data(all_messages, "freelancer_messages.json")
    
    return all_messages

def extract_domains(text: str) -> List[str]:
    """Extract domains from text using regex pattern."""
    if not text:
        return []
        
    # Pattern to match URLs or domain names
    pattern = r'(?:https?://)?(?:[\w-]+\.)+(?:com|net|org|edu|gov|mil|biz|info|mobi|name|aero|asia|jobs|museum|de|uk|fr|it|es|ru|cn|jp|au|ca|br|[a-z]{2})\b'
    
    matches = re.finditer(pattern, text.lower())
    domains = []
    
    for match in matches:
        domain = match.group(0)
        if not domain.startswith('http'):
            domain = 'http://' + domain
        try:
            parsed = urlparse(domain)
            if parsed.netloc:
                domains.append(parsed.netloc)
        except:
            continue
    
    return list(set(domains))  # Remove duplicates

def scan_messages_for_domains(
    fetch_data: bool = True,
    search_domains: bool = True, 
    check_reachability: bool = True,
    generate_reports: bool = True,
    show_listings: bool = True,
    max_threads: int = None,
    max_messages: int = None
):
    """
    Main function to scan all messages for domains with configurable options.
    
    Args:
        fetch_data (bool): Whether to fetch new data from Freelancer API
        search_domains (bool): Whether to search for domains in messages
        check_reachability (bool): Whether to check if domains are online
        generate_reports (bool): Whether to generate and save report files
        show_listings (bool): Whether to show results in console
        max_threads (int): Maximum number of threads to process (None for all)
        max_messages (int): Maximum number of messages to process (None for all)
    """
    print("=" * 80)
    print("FREELANCER MESSAGE DOMAIN SCANNER")
    print("=" * 80)
    print(f"Configuration:")
    print(f"  📥 Fetch new data: {'✓' if fetch_data else '✗'}")
    print(f"  🔍 Search domains: {'✓' if search_domains else '✗'}")
    print(f"  🌐 Check reachability: {'✓' if check_reachability else '✗'}")
    print(f"  📊 Generate reports: {'✓' if generate_reports else '✗'}")
    print(f"  📋 Show listings: {'✓' if show_listings else '✗'}")
    if max_threads:
        print(f"  📄 Max threads: {max_threads}")
    if max_messages:
        print(f"  💬 Max messages: {max_messages}")
    print("=" * 80)
    
    # Initialize variables
    threads = []
    messages = []
    domains_found = []
    online_domains = []
    offline_domains = []
    
    # Step 1: Authentication (always required)
    if fetch_data and not test_authentication():
        print("Cannot proceed without valid authentication.")
        return
    
    # Step 2: Get threads data
    if fetch_data:
        threads = get_all_threads()
        if not threads:
            print("No threads found.")
            return
        
        # Apply thread limit if specified
        if max_threads and len(threads) > max_threads:
            threads = threads[:max_threads]
            print(f"⚠️  Limited to first {max_threads} threads")
    else:
        print("⚠️  Skipping data fetch - using existing data only")
    
    # Step 3: Get messages data
    if fetch_data and threads:
        # Extract thread IDs
        thread_ids = []
        for thread in threads:
            thread_id = thread.get('id')
            if thread_id:
                thread_ids.append(thread_id)
        
        print(f"Extracted {len(thread_ids)} thread IDs")
        
        messages = get_all_messages(thread_ids)
        if not messages:
            print("No messages found.")
            return
            
        # Apply message limit if specified
        if max_messages and len(messages) > max_messages:
            messages = messages[:max_messages]
            print(f"⚠️  Limited to first {max_messages} messages")
    
    # Step 4: Search for domains in messages
    if search_domains and messages:
        print("Scanning messages for domains...")
        
        for message in messages:
            message_text = message.get("message", "")
            if not message_text:
                continue
                
            domains = extract_domains(message_text)
            
            if domains:
                # Get thread info
                thread_info = message.get("thread", {})
                thread_id = thread_info.get("id") or message.get("thread_id")
                
                # Get user info - handle both int and dict cases
                from_user = message.get("from_user")
                if isinstance(from_user, dict):
                    username = from_user.get("username", "Unknown")
                elif isinstance(from_user, int):
                    username = f"User_{from_user}"
                else:
                    username = "Unknown"
                
                for domain in domains:
                    domains_found.append({
                        'message_id': message.get('id'),
                        'thread_id': thread_id,
                        'domain': domain,
                        'from_user': username,
                        'time_created': message.get('time_created'),
                        'message_preview': message_text[:200] + "..." if len(message_text) > 200 else message_text,
                        'full_message': message_text
                    })
    
    # Step 5: Generate and save reports
    if generate_reports and domains_found:
        # Save domains as JSON
        save_json_data(domains_found, "freelancer_domains_found.json")
        
        # Save domains as CSV (without full_message for readability)
        csv_data = []
        for item in domains_found:
            csv_item = item.copy()
            csv_item.pop('full_message', None)  # Remove full message from CSV for readability
            csv_data.append(csv_item)
        save_csv_data(csv_data, "freelancer_domains_found.csv")
        
        # Create summary data
        all_domains = set()
        domain_stats = {}
        for result in domains_found:
            domain = result['domain']
            all_domains.add(domain)
            domain_stats[domain] = domain_stats.get(domain, 0) + 1
        
        # Save domain summary
        domain_summary = [
            {"domain": domain, "occurrences": count}
            for domain, count in sorted(domain_stats.items(), key=lambda x: x[1], reverse=True)
        ]
        save_json_data(domain_summary, "freelancer_domain_summary.json")
        save_csv_data(domain_summary, "freelancer_domain_summary.csv")
    
    # Step 6: Check domain reachability
    if check_reachability and domains_found:
        unique_domains = list(set([d['domain'] for d in domains_found]))
        print(f"\n{'='*80}")
        print(f"CHECKING DOMAIN REACHABILITY ({len(unique_domains)} unique domains)")
        print(f"{'='*80}")
        
        # Check domains with concurrent processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_domain, domain) for domain in unique_domains]
            for future in concurrent.futures.as_completed(futures):
                domain, is_reachable = future.result()
                status_icon = "🟢" if is_reachable else "🔴"
                status_text = "ONLINE" if is_reachable else "OFFLINE"
                
                if show_listings:
                    print(f"{status_icon} {domain} - {status_text}")
                
                if is_reachable:
                    online_domains.append(domain)
                else:
                    offline_domains.append(domain)
        
        # Save reachability results if generating reports
        if generate_reports:
            reachability_results = {
                "check_timestamp": datetime.now().isoformat(),
                "total_domains": len(unique_domains),
                "online_domains": {
                    "count": len(online_domains),
                    "domains": sorted(online_domains)
                },
                "offline_domains": {
                    "count": len(offline_domains), 
                    "domains": sorted(offline_domains)
                }
            }
            save_json_data(reachability_results, "freelancer_domain_reachability.json")
            
            # Create CSV for reachability
            reachability_csv = [
                {"domain": domain, "status": "ONLINE", "reachable": True}
                for domain in sorted(online_domains)
            ] + [
                {"domain": domain, "status": "OFFLINE", "reachable": False}
                for domain in sorted(offline_domains)
            ]
            save_csv_data(reachability_csv, "freelancer_domain_reachability.csv")
    
    # Step 7: Show final results and listings
    if show_listings:
        print(f"\n{'='*80}")
        print(f"SCAN COMPLETE")
        print(f"{'='*80}")
        if threads:
            print(f"Threads processed: {len(threads)}")
        if messages:
            print(f"Messages processed: {len(messages)}")
        if domains_found:
            print(f"Messages with domains: {len(set([d['message_id'] for d in domains_found]))}")
            print(f"Total domain occurrences: {len(domains_found)}")
            print(f"Unique domains found: {len(set([d['domain'] for d in domains_found]))}")
        
        if check_reachability and domains_found:
            print(f"🟢 Online domains: {len(online_domains)}")
            print(f"🔴 Offline domains: {len(offline_domains)}")
        
        print(f"{'='*80}")
        
        if generate_reports and domains_found:
            print("\nFILES SAVED:")
            if fetch_data:
                print("✓ Raw threads JSON")
                print("✓ Raw messages JSON") 
            print("✓ Domain findings JSON")
            print("✓ Domain findings CSV")
            print("✓ Domain summary JSON")
            print("✓ Domain summary CSV")
            if check_reachability:
                print("✓ Domain reachability JSON")
                print("✓ Domain reachability CSV")
            
        if domains_found and show_listings:
            print(f"\nTOP 10 MOST MENTIONED DOMAINS:")
            print("-" * 40)
            domain_counts = {}
            for result in domains_found:
                domain = result['domain']
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            for i, (domain, count) in enumerate(top_domains, 1):
                # Add status indicator if reachability was checked
                if check_reachability:
                    if domain in online_domains:
                        status = "🟢 ONLINE"
                    elif domain in offline_domains:
                        status = "🔴 OFFLINE"
                    else:
                        status = "⚪ UNKNOWN"
                    print(f"{i:2d}. {domain} ({count} mentions) - {status}")
                else:
                    print(f"{i:2d}. {domain} ({count} mentions)")
                
    elif not domains_found and show_listings:
        print("No domains found in any messages.")
    
    # Return results for programmatic use
    return {
        "threads_count": len(threads),
        "messages_count": len(messages), 
        "domains_found": domains_found,
        "online_domains": online_domains,
        "offline_domains": offline_domains,
        "unique_domains": len(set([d['domain'] for d in domains_found])) if domains_found else 0
    }

def quick_domain_check():
    """Quick scan: Only check domain reachability without fetching new data."""
    return scan_messages_for_domains(
        fetch_data=False,
        search_domains=False,
        check_reachability=True,
        generate_reports=False,
        show_listings=True
    )

def fetch_only():
    """Fetch new data from API without domain analysis."""
    return scan_messages_for_domains(
        fetch_data=True,
        search_domains=False,
        check_reachability=False,
        generate_reports=False,
        show_listings=True
    )

def domain_search_only():
    """Search for domains without fetching new data or checking reachability."""
    return scan_messages_for_domains(
        fetch_data=False,
        search_domains=True,
        check_reachability=False,
        generate_reports=True,
        show_listings=True
    )

def reachability_only():
    """Only check domain reachability from existing data."""
    return scan_messages_for_domains(
        fetch_data=False,
        search_domains=True,
        check_reachability=True,
        generate_reports=True,
        show_listings=True
    )

def silent_full_scan():
    """Full scan with minimal console output - just save files."""
    return scan_messages_for_domains(
        fetch_data=True,
        search_domains=True,
        check_reachability=True,
        generate_reports=True,
        show_listings=False
    )

def limited_scan(max_threads=50, max_messages=1000):
    """Limited scan for testing purposes."""
    return scan_messages_for_domains(
        fetch_data=True,
        search_domains=True,
        check_reachability=True,
        generate_reports=True,
        show_listings=True,
        max_threads=max_threads,
        max_messages=max_messages
    )

def list_domains_only():
    """List only domains and their availability status - clean output."""
    return scan_messages_for_domains(
        fetch_data=False,
        search_domains=True,
        check_reachability=True,
        generate_reports=False,
        show_listings=False  # We'll handle custom output
    )

def print_domains_list():
    """Print a clean list of domains with their availability."""
    print("🌐 Analyzing existing data for domains and checking availability...")
    print("=" * 60)
    
    # Run the scan without verbose output
    results = list_domains_only()
    
    if not results or not results.get('domains_found'):
        print("❌ No domains found in existing data.")
        print("💡 Try running: python fl-messages.py full")
        return
    
    # Get unique domains from results
    domains_found = results['domains_found']
    online_domains = results['online_domains']
    offline_domains = results['offline_domains']
    
    # Create a set of all unique domains
    all_unique_domains = set([d['domain'] for d in domains_found])
    
    print(f"📊 Found {len(all_unique_domains)} unique domains:")
    print("=" * 60)
    
    # Sort domains alphabetically and show status
    sorted_domains = sorted(all_unique_domains)
    
    online_count = 0
    offline_count = 0
    
    for domain in sorted_domains:
        if domain in online_domains:
            print(f"🟢 {domain}")
            online_count += 1
        elif domain in offline_domains:
            print(f"🔴 {domain}")
            offline_count += 1
        else:
            print(f"⚪ {domain} (not checked)")
    
    print("=" * 60)
    print(f"📈 Summary: {online_count} online, {offline_count} offline")
    print("=" * 60)

def load_existing_domains():
    """Load domains from existing saved files."""
    import glob
    
    # Find the most recent domain summary file
    domain_files = glob.glob(os.path.join(OUTPUT_DIR, "*_freelancer_domain_summary.json"))
    
    if not domain_files:
        return []
    
    # Get the largest file (most comprehensive data)
    latest_file = max(domain_files, key=os.path.getsize)
    print(f"📁 Loading domains from: {os.path.basename(latest_file)}")
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract just the domain names
        domains = [item['domain'] for item in data if isinstance(item, dict) and 'domain' in item]
        return domains
    except Exception as e:
        print(f"Error loading existing domain data: {e}")
        return []

def check_domains_from_file():
    """Load existing domains and check their availability."""
    print("🌐 Loading domains from existing data and checking availability...")
    print("=" * 60)
    
    # Load existing domains
    domains = load_existing_domains()
    
    if not domains:
        print("❌ No existing domain data found.")
        print("💡 Try running: python fl-messages.py full")
        return
    
    print(f"📊 Found {len(domains)} unique domains from saved data")
    print("🔍 Checking availability...")
    print("=" * 60)
    
    online_domains = []
    offline_domains = []
    
    # Check domains with concurrent processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_domain, domain) for domain in domains]
        for future in concurrent.futures.as_completed(futures):
            domain, is_reachable = future.result()
            
            if is_reachable:
                online_domains.append(domain)
                print(f"🟢 {domain}")
            else:
                offline_domains.append(domain)
                print(f"🔴 {domain}")
    
    print("=" * 60)
    print(f"📈 Summary: {len(online_domains)} online, {len(offline_domains)} offline")
    print("=" * 60)
    
    return {
        "total_domains": len(domains),
        "online_domains": online_domains,
        "offline_domains": offline_domains
    }

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments for different modes
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "fetch":
            print("🔄 Mode: Fetch only")
            fetch_only()
        elif mode == "search":
            print("🔍 Mode: Domain search only")
            domain_search_only()
        elif mode == "check":
            print("🌐 Mode: Reachability check only")
            reachability_only()
        elif mode == "quick":
            print("⚡ Mode: Quick domain check")
            quick_domain_check()
        elif mode == "silent":
            print("🤫 Mode: Silent full scan")
            silent_full_scan()
        elif mode == "limited":
            max_t = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            max_m = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
            print(f"🔬 Mode: Limited scan ({max_t} threads, {max_m} messages)")
            limited_scan(max_t, max_m)
        elif mode == "help":
            print("Available modes:")
            print("  python fl-messages.py fetch      - Fetch new data only")
            print("  python fl-messages.py search     - Search domains only")
            print("  python fl-messages.py check      - Check reachability only")
            print("  python fl-messages.py list       - List domains and availability only")
            print("  python fl-messages.py checkfile  - Check domains from saved files")
            print("  python fl-messages.py quick      - Quick domain check")
            print("  python fl-messages.py silent     - Silent full scan")
            print("  python fl-messages.py limited [threads] [messages] - Limited scan")
            print("  python fl-messages.py full       - Full scan (default)")
            print("  python fl-messages.py help       - Show this help")
        elif mode == "full":
            print("🚀 Mode: Full scan")
            scan_messages_for_domains()
        elif mode == "list":
            print("🌐 Mode: List domains only")
            print_domains_list()
        elif mode == "checkfile":
            print("🌐 Mode: Check domains from file")
            check_domains_from_file()
        else:
            print(f"Unknown mode: {mode}")
            print("Use 'python fl-messages.py help' for available modes")
    else:
        # Default: Full scan
        print("🚀 Mode: Full scan (default)")
        try:
            scan_messages_for_domains()
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            import traceback
            traceback.print_exc()
