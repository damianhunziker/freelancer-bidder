import asyncio
import json
import subprocess
import sys
import os
from datetime import datetime
from pyppeteer import launch
from rate_limit_manager import is_rate_limited, get_rate_limit_status
from heartbeat_manager import send_heartbeat

# API Logging setup for freelancer-websocket-reader
API_LOGS_DIR = 'api_logs'
API_REQUEST_LOG = os.path.join(API_LOGS_DIR, 'freelancer_requests.log')

def setup_api_logs_directory():
    """Setup/clean the API logs directory"""
    if not os.path.exists(API_LOGS_DIR):
        os.makedirs(API_LOGS_DIR)

def log_websocket_message(message_type, project_id=None, project_title=None):
    """Log important WebSocket messages related to projects"""
    try:
        # Ensure logs directory exists
        setup_api_logs_directory()
        
        # Create timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Format log entry
        log_entry = f"{timestamp} | WEBSOCKET-READER | {message_type}"
        if project_id:
            log_entry += f" | project_id={project_id}"
        if project_title:
            log_entry += f" | project_title={project_title[:50]}..." if len(project_title) > 50 else f" | project_title={project_title}"
        log_entry += "\n"
        
        # Write to log file
        with open(API_REQUEST_LOG, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
        # Also print to console
        print(f"📝 WEBSOCKET LOG: {log_entry.strip()}")
            
    except Exception as e:
        print(f"Error logging WebSocket message: {str(e)}")

# Get the correct Python path - use the same interpreter running this script
PYTHON_PATH = sys.executable

async def execute_add_script(project_id):
    """Execute add.py script with project ID in a separate process"""
    try:
        print(f"🚀 Executing: python add.py {project_id}")
        
        # Start the process asynchronously using the same Python interpreter
        process = await asyncio.create_subprocess_exec(
            PYTHON_PATH, 'add.py', str(project_id),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for completion and show output
        stdout, stderr = await process.communicate()
        if stdout:
            print(f"✅ add.py output: {stdout.decode()}")
        if stderr:
            print(f"⚠️ add.py error: {stderr.decode()}")
        
        print(f"✅ Completed add.py process for ID: {project_id}")
        
    except Exception as e:
        print(f"❌ Error executing add.py for ID {project_id}: {e}")


def decode_payload(payload):
    """Decode and format the payload data properly"""
    if not payload:
        return None, "Empty payload"
    
    try:
        # Handle heartbeat
        if payload == 'h':
            return {'type': 'heartbeat'}, "💓 HEARTBEAT"
        
        # Handle Socket.IO format: a["JSON_STRING"]
        if payload.startswith('a["') and payload.endswith('"]'):
            # Extract the JSON string from the Socket.IO wrapper
            json_str = payload[3:-2]  # Remove 'a["' and '"]'
            
            # Unescape the JSON string
            json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
            
            # Parse the JSON
            parsed_data = json.loads(json_str)
            return parsed_data, "✅ Successfully parsed Socket.IO JSON"
        
        # Handle regular JSON
        elif payload.startswith('{') or payload.startswith('['):
            parsed_data = json.loads(payload)
            return parsed_data, "✅ Successfully parsed JSON"
        
        # Handle other formats
        else:
            return {'raw': payload}, "⚠️ Unknown format, showing raw data"
            
    except json.JSONDecodeError as e:
        return None, f"❌ JSON decode error: {e}"
    except Exception as e:
        return None, f"❌ General parsing error: {e}"

def extract_job_info(data):
    """Extract job information from parsed data"""
    job_info = {}
    
    if not isinstance(data, dict):
        return job_info
    
    # Direct ID extraction
    if 'id' in data and isinstance(data['id'], (int, str)):
        job_info['id'] = str(data['id'])
    
    # Extract from nested body.data structure
    if 'body' in data and 'data' in data['body']:
        nested_data = data['body']['data']
        if 'id' in nested_data:
            job_info['id'] = str(nested_data['id'])
        if 'title' in nested_data:
            job_info['title'] = nested_data['title']
        if 'jobString' in nested_data:
            job_info['skills'] = nested_data['jobString']
        if 'minbudget' in nested_data and 'maxbudget' in nested_data:
            currency = nested_data.get('currency', '£')
            job_info['budget'] = f"{currency}{nested_data['minbudget']}-{currency}{nested_data['maxbudget']}"
        if 'bid_stats' in nested_data:
            bid_stats = nested_data['bid_stats']
            job_info['bid_count'] = bid_stats.get('bid_count', 0)
            job_info['bid_avg'] = bid_stats.get('bid_avg', 0)
    
    return job_info

async def setup_browser_session():
    """Setup browser and return browser, page, and cdp session"""
    print("🚀 Starting browser for Freelancer.com...")
    browser = await launch(
        headless=False,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-features=VizDisplayCompositor',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
        ],
        autoClose=False
    )
    
    print("📄 Creating new page...")
    page = await browser.newPage()
    
    # Check rate limit before attempting navigation
    if is_rate_limited():
        status = get_rate_limit_status()
        remaining_min = status['remaining_seconds'] // 60
        remaining_sec = status['remaining_seconds'] % 60
        print(f"⏳ Rate limit active. Remaining time: {remaining_min} minutes, {remaining_sec} seconds")
        print("💡 Skipping navigation while rate limited - user will need to manually navigate to Freelancer.com")
        return browser, page
    
    try:
        print("🌐 Navigating to Freelancer.com...")
        await page.goto('https://www.freelancer.com', {'timeout': 60000})  # Increase timeout to 60s
        print("✅ Freelancer.com loaded successfully!")
    except Exception as nav_error:
        print(f"⚠️ Navigation failed: {nav_error}")
        print("💡 Browser created but navigation failed - user will need to manually navigate to Freelancer.com")
        # Don't raise exception - return browser/page for manual navigation
    
    return browser, page

async def setup_cdp_session(page):
    """Setup CDP session with error handling"""
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            print(f"\n🔧 Setting up CDP session (attempt {attempt + 1}/{max_retries})...")
            cdp = await page.target.createCDPSession()
            await cdp.send('Network.enable')
            await cdp.send('Page.enable')
            print("✅ CDP session ready!")
            return cdp
        except Exception as e:
            print(f"❌ CDP setup failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"⏳ Waiting {retry_delay}s before retry...")
                await asyncio.sleep(retry_delay)
            else:
                raise Exception(f"Failed to setup CDP session after {max_retries} attempts")

async def check_session_health(page, cdp):
    """Check if browser and CDP session are still healthy"""
    try:
        # Test if page is still accessible
        await page.evaluate('() => document.readyState')
        
        # Test if CDP session is still responsive
        await cdp.send('Runtime.evaluate', {'expression': '1+1'})
        
        return True
    except Exception as e:
        print(f"⚠️ Session health check failed: {str(e)}")
        return False

async def recover_session(browser, page, cdp):
    """Attempt to recover from session failure (DEPRECATED - use light recovery instead)"""
    print("🔄 Attempting session recovery...")
    
    try:
        # Try to recreate CDP session without page reload
        print("🔄 Recreating CDP session...")
        cdp = await setup_cdp_session(page)
        
        print("✅ Session recovery successful!")
        return cdp
        
    except Exception as e:
        print(f"❌ Session recovery failed: {str(e)}")
        print("💡 Continuing without recovery - may resolve automatically...")
        # Don't raise exception - let the system continue
        return None

async def main():
    browser = None
    page = None
    cdp = None
    consecutive_failures = 0
    max_failures = 3
    last_heartbeat = 0
    
    # Initialize tracking variables at the start
    job_ids = set()
    projects_found = []
    message_count = 0
    processed_ids = set()
    
    while True:
        try:
            # Send heartbeat every 30 seconds
            current_time = asyncio.get_event_loop().time()
            if current_time - last_heartbeat > 30:
                send_heartbeat('websocket-reader', {
                    'browser_status': 'running' if browser else 'stopped',
                    'cdp_status': 'connected' if cdp else 'disconnected',
                    'consecutive_failures': consecutive_failures,
                    'messages_processed': message_count,
                    'projects_found': len(projects_found),
                    'job_ids_tracked': len(job_ids),
                    'rate_limit_status': 'active' if is_rate_limited() else 'clear'
                })
                last_heartbeat = current_time
            
            # Setup browser if not already done
            if browser is None or page is None:
                browser, page = await setup_browser_session()
                
                print("\n" + "="*60)
                print("🔐 PLEASE LOG IN TO YOUR FREELANCER ACCOUNT")
                print("="*60)
                print("1. Log in with your credentials in the browser window")
                print("2. Navigate to any page you want to monitor (dashboard, projects, etc.)")
                print("3. When ready, come back here and press ENTER to start monitoring")
                print("="*60)
                print("💡 Note: If navigation failed due to rate limits or timeouts, manually navigate to freelancer.com")
                
                # Wait for user to log in
                input("Press ENTER when you are logged in and ready to start monitoring...")
            
            # Setup CDP session
            if cdp is None:
                cdp = await setup_cdp_session(page)
            
            # Reset failure counter on successful setup
            consecutive_failures = 0

            def printResponse(response):
                nonlocal job_ids, projects_found, message_count, processed_ids
                message_count += 1
                
                print("\n" + "="*80)
                print(f"📦 WEBSOCKET MESSAGE #{message_count}")
                print("="*80)
                
                # Extract basic info
                request_id = response.get('requestId', 'unknown')
                timestamp = response.get('timestamp', 'unknown')
                print(f"🕐 Timestamp: {timestamp}")
                print(f"🔗 Request ID: {request_id}")
                
                if 'response' in response:
                    resp = response['response']
                    opcode = resp.get('opcode', 'unknown')
                    mask = resp.get('mask', 'unknown')
                    payload = resp.get('payloadData', '')
                    
                    print(f"📡 Opcode: {opcode}")
                    print(f"🎭 Mask: {mask}")
                    print(f"📏 Payload Length: {len(payload)}")
                    
                    if payload:
                        # Decode the payload
                        parsed_data, parse_status = decode_payload(payload)
                        print(f"\n📄 PARSE STATUS: {parse_status}")
                        
                        if parsed_data:
                            print("\n🎯 DECODED PAYLOAD:")
                            print("-" * 50)
                            print(json.dumps(parsed_data, indent=2, ensure_ascii=False))
                            
                            # Extract job information
                            job_info = extract_job_info(parsed_data)
                            
                            if job_info.get('id'):
                                job_id = job_info['id']
                                job_ids.add(job_id)
                                
                                print(f"\n🆔 JOB ID DETECTED: {job_id}")
                                
                                # Execute add.py if this ID hasn't been processed yet
                                if job_id not in processed_ids:
                                    processed_ids.add(job_id)
                                    
                                    # Log the project detection
                                    log_websocket_message("PROJECT_DETECTED", project_id=job_id, project_title=job_info.get('title'))
                                    
                                    # Check rate limit before processing
                                    if is_rate_limited():
                                        print(f"🚫 Global rate limit active - delaying processing of project {job_id}")
                                        status = get_rate_limit_status()
                                        remaining_min = status['remaining_seconds'] // 60
                                        print(f"⏳ Rate limit expires in {remaining_min} minutes")
                                        log_websocket_message("RATE_LIMITED", project_id=job_id)
                                    else:
                                        print(f"🎯 NEW PROJECT ID - Triggering add.py script...")
                                        log_websocket_message("EXECUTING_ADD_SCRIPT", project_id=job_id)
                                        
                                        # Start the add.py script asynchronously
                                        asyncio.create_task(execute_add_script(job_id))
                                else:
                                    print(f"🔄 Already processed ID: {job_id}")
                                
                                # Check if it's a project notification
                                if 'title' in job_info:
                                    print(f"\n🎯 PROJECT ALERT!")
                                    print(f"   📋 Title: {job_info['title']}")
                                    print(f"   🆔 ID: {job_id}")
                                    if 'budget' in job_info:
                                        print(f"   💰 Budget: {job_info['budget']}")
                                    if 'skills' in job_info:
                                        print(f"   🛠️  Skills: {job_info['skills']}")
                                    if 'bid_count' in job_info:
                                        print(f"   📊 Bids: {job_info['bid_count']} (avg: £{job_info['bid_avg']})")
                                    
                                    # Add to projects list
                                    projects_found.append(job_info)
                            
                            # Show message type and channel
                            if isinstance(parsed_data, dict):
                                msg_type = parsed_data.get('type', 'unknown')
                                channel = parsed_data.get('channel', 'unknown')
                                print(f"\n🏷️  Message Type: {msg_type}")
                                print(f"🏷️  Channel: {channel}")
                        
                        else:
                            print(f"\n📄 RAW PAYLOAD:")
                            print("-" * 50)
                            print(payload[:300] + "..." if len(payload) > 300 else payload)
                
                # Show current summary
                if job_ids:
                    print(f"\n📊 JOB IDs TRACKED: {len(job_ids)} unique IDs")
                    print(f"🔧 PROCESSED BY add.py: {len(processed_ids)} IDs")
                    recent_ids = list(job_ids)[-5:]  # Show last 5 IDs
                    print(f"   Recent: {', '.join(recent_ids)}")
                
                print("="*80)

            cdp.on('Network.webSocketFrameReceived', printResponse)
            cdp.on('Network.webSocketFrameSent', printResponse)
            
            # Main monitoring loop with health checks
            health_check_interval = 120  # Check every 2 minutes (less aggressive)
            last_health_check = 0
            
            while True:
                current_time = asyncio.get_event_loop().time()
                
                # Send heartbeat every 30 seconds during monitoring
                if current_time - last_heartbeat > 30:
                    send_heartbeat('websocket-reader', {
                        'browser_status': 'running' if browser else 'stopped',
                        'cdp_status': 'connected' if cdp else 'disconnected',
                        'consecutive_failures': consecutive_failures,
                        'messages_processed': message_count,
                        'projects_found': len(projects_found),
                        'job_ids_tracked': len(job_ids),
                        'rate_limit_status': 'active' if is_rate_limited() else 'clear'
                    })
                    last_heartbeat = current_time
                
                # Periodic health check (less aggressive)
                if current_time - last_health_check > health_check_interval:
                    try:
                        if not await check_session_health(page, cdp):
                            print("⚠️ Session unhealthy - attempting light recovery...")
                            # Try light recovery first - just recreate CDP
                            try:
                                cdp = await setup_cdp_session(page)
                                # Re-setup listeners
                                cdp.on('Network.webSocketFrameReceived', printResponse)
                                cdp.on('Network.webSocketFrameSent', printResponse)
                                print("✅ Light recovery successful")
                            except Exception as recovery_error:
                                print(f"⚠️ Light recovery failed: {recovery_error}")
                                print("💡 Will continue with current session...")
                        last_health_check = current_time
                    except Exception as health_error:
                        print(f"⚠️ Health check failed: {health_error} - continuing...")
                        last_health_check = current_time
                
                await asyncio.sleep(3)  # Increased sleep to reduce CPU load and be less aggressive
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
            break
            
        except Exception as e:
            consecutive_failures += 1
            print(f"❌ Error (failure #{consecutive_failures}): {str(e)}")
            
            if consecutive_failures >= max_failures:
                print(f"💥 Too many consecutive failures ({max_failures}). Exiting...")
                break
            
            print(f"🔄 Attempting to recover... (retry {consecutive_failures}/{max_failures})")
            
            # Try light recovery first - only reset CDP, keep browser/page
            cdp = None
            
            # Only close browser/page if it's a critical error
            error_str = str(e).lower()
            is_critical_error = any(keyword in error_str for keyword in [
                'browser disconnected', 'connection closed', 'browser closed', 
                'target closed', 'session closed'
            ])
            
            # Don't treat navigation timeouts as critical errors
            is_navigation_timeout = 'navigation timeout' in error_str or 'timeout exceeded' in error_str
            
            if is_navigation_timeout:
                # Check if rate limit is causing the timeout
                if is_rate_limited():
                    status = get_rate_limit_status()
                    remaining_min = status['remaining_seconds'] // 60
                    remaining_sec = status['remaining_seconds'] % 60
                    print(f"⏰ Navigation timeout likely due to rate limiting")
                    print(f"⏳ Rate limit active. Remaining time: {remaining_min} minutes, {remaining_sec} seconds")
                    print("💡 Keeping browser open and waiting for rate limit to clear...")
                    # Wait for rate limit to clear instead of retrying immediately
                    wait_time = min(status['remaining_seconds'] + 10, 300)  # Wait for rate limit + 10s, max 5 minutes
                else:
                    print("⏰ Navigation timeout - this is often temporary, keeping existing browser/page")
                    wait_time = 15  # Slightly longer wait for timeouts
                
                # Just reset CDP, keep browser open
                cdp = None
            elif is_critical_error or consecutive_failures >= 3:  # Increased threshold
                print("🔄 Critical error detected - full browser restart needed")
                try:
                    if page:
                        await page.close()
                except:
                    pass
                try:
                    if browser:
                        await browser.close()
                except:
                    pass
                
                browser = None
                page = None
                wait_time = 30  # Longer wait for full restart
            else:
                print("💡 Light error - keeping browser/page, only resetting CDP")
                cdp = None
                wait_time = 5
            
            print(f"⏳ Waiting {wait_time}s before retry...")
            await asyncio.sleep(wait_time)
    
    # Final cleanup and summary
    if 'job_ids' in locals():
        print("\n" + "="*80)
        print("📋 FINAL SUMMARY")
        print("="*80)
        print(f"📊 Total messages processed: {message_count}")
        print(f"🆔 Total unique Job IDs found: {len(job_ids)}")
        print(f"🔧 Total IDs processed by add.py: {len(processed_ids)}")
        
        if job_ids:
            print("\n📝 ALL JOB IDs:")
            for job_id in sorted(job_ids):
                status = "✅ Processed" if job_id in processed_ids else "⏳ Not processed"
                print(f"   • {job_id} ({status})")
        
        print(f"\n🎯 Total projects detected: {len(projects_found)}")
        if projects_found:
            print("\n📋 PROJECT DETAILS:")
            for i, project in enumerate(projects_found, 1):
                print(f"   {i}. [{project['id']}] {project.get('title', 'No title')[:60]}...")
                if 'budget' in project:
                    print(f"      💰 {project['budget']}")
                if 'skills' in project:
                    print(f"      🛠️  {project['skills']}")
    
    print("\n✅ Session complete!")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("👋 Script interrupted by user")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc() 