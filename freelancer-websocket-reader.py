import asyncio
import json
import subprocess
from pyppeteer import launch

async def execute_add_script(project_id):
    """Execute add.py script with project ID in a separate process"""
    try:
        print(f"🚀 Executing: python add.py {project_id}")
        
        # Start the process asynchronously
        process = await asyncio.create_subprocess_exec(
            'python', 'add.py', str(project_id),
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

async def execute_app_script(project_id):
    """Execute app.py script with project ID in a separate process and print output"""
    try:
        print(f"🚀 Executing: python app.py {project_id}")
        process = await asyncio.create_subprocess_exec(
            'python', 'app.py', str(project_id),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if stdout:
            print(f"✅ app.py output: {stdout.decode()}")
        if stderr:
            print(f"⚠️ app.py error: {stderr.decode()}")
        print(f"✅ Completed app.py process for ID: {project_id}")
    except Exception as e:
        print(f"❌ Error executing app.py for ID {project_id}: {e}")

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

async def main():
    print("🚀 Starting browser for Freelancer.com...")
    browser = await launch(
        headless=False,
        args=['--no-sandbox'],
        autoClose=False
    )
    
    print("📄 Creating new page...")
    page = await browser.newPage()
    
    print("🌐 Navigating to Freelancer.com...")
    await page.goto('https://www.freelancer.com')
    print("✅ Freelancer.com loaded successfully!")
    
    print("\n" + "="*60)
    print("🔐 PLEASE LOG IN TO YOUR FREELANCER ACCOUNT")
    print("="*60)
    print("1. Log in with your credentials in the browser window")
    print("2. Navigate to any page you want to monitor (dashboard, projects, etc.)")
    print("3. When ready, come back here and press ENTER to start monitoring")
    print("="*60)
    
    # Wait for user to log in
    input("Press ENTER when you are logged in and ready to start monitoring...")
    
    print("\n🔧 Setting up CDP session...")
    cdp = await page.target.createCDPSession()
    await cdp.send('Network.enable')
    await cdp.send('Page.enable')
    print("✅ CDP session ready!")

    # Track job IDs and projects
    job_ids = set()
    projects_found = []
    message_count = 0
    processed_ids = set()  # Track IDs we've already processed

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
                            print(f"🎯 NEW PROJECT ID - Triggering add.py script...")
                            
                            # Start the add.py script asynchronously
                            asyncio.create_task(execute_add_script(job_id))
                            asyncio.create_task(execute_app_script(job_id))
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
    
    try:
        while True:  # Endless loop
            await asyncio.sleep(1)  # Small sleep to prevent CPU overload
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")
    
    # Final summary
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