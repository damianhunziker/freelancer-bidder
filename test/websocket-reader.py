import asyncio
import json
from pyppeteer import launch

async def main():
    print("🚀 Starting browser...")
    browser = await launch(
        headless=False,  # Changed to False to see what's happening
        args=['--no-sandbox', '--disable-web-security'],
        autoClose=False
    )
    
    print("📄 Creating new page...")
    page = await browser.newPage()
    
    print("🌐 Navigating to TradingView...")
    await page.goto('https://www.tradingview.com/symbols/BTCUSD/', waitUntil='networkidle0')
    print("✅ Page loaded successfully!")
    
    print("🔧 Setting up CDP session...")
    cdp = await page.target.createCDPSession()
    await cdp.send('Network.enable')
    await cdp.send('Page.enable')
    print("✅ CDP session ready!")

    # Counter for received messages
    message_count = 0

    def printResponse(response):
        nonlocal message_count
        message_count += 1
        print(f"📦 WebSocket Message #{message_count}:")
        print(f"   Type: {response.get('type', 'unknown')}")
        print(f"   Timestamp: {response.get('timestamp', 'unknown')}")
        
        if 'response' in response:
            resp = response['response']
            print(f"   URL: {resp.get('url', 'unknown')}")
            print(f"   Payload Length: {len(resp.get('payloadData', ''))}")
            
            # Try to decode payload if it's text
            payload = resp.get('payloadData', '')
            if payload:
                try:
                    # Try to parse as JSON
                    decoded = json.loads(payload)
                    print(f"   Payload (JSON): {json.dumps(decoded, indent=2)[:200]}...")
                except:
                    print(f"   Payload (raw): {payload[:100]}...")
        
        print("   " + "="*50)

    def onWebSocketCreated(response):
        print(f"🔌 WebSocket Created: {response}")

    def onWebSocketClosed(response):
        print(f"❌ WebSocket Closed: {response}")

    # Listen to all WebSocket events
    cdp.on('Network.webSocketCreated', onWebSocketCreated)
    cdp.on('Network.webSocketClosed', onWebSocketClosed)
    cdp.on('Network.webSocketFrameReceived', printResponse)
    cdp.on('Network.webSocketFrameSent', printResponse)
    
    print("👂 Listening for WebSocket traffic...")
    print("⏰ Waiting for 30 seconds to capture WebSocket messages...")
    
    # Wait for WebSockets to be established
    await asyncio.sleep(10)
    
    # Check if any WebSockets are active
    print("🔍 Checking for active WebSocket connections...")
    
    # Try to trigger some activity by interacting with the page
    print("🎯 Trying to trigger WebSocket activity...")
    try:
        await page.evaluate('() => { console.log("Page interaction"); }')
        await page.mouse.move(100, 100)
        await asyncio.sleep(5)
        
        # Try to scroll or click to trigger data loading
        await page.evaluate('() => { window.scrollBy(0, 100); }')
        await asyncio.sleep(5)
    except Exception as e:
        print(f"⚠️ Error during interaction: {e}")
    
    print(f"📊 Total messages received so far: {message_count}")
    
    if message_count == 0:
        print("🤔 No WebSocket messages detected. Let's try a different approach...")
        
        # Get all network requests to see what's happening
        print("🔍 Analyzing all network activity...")
        await cdp.send('Network.clearBrowserCache')
        await page.reload(waitUntil='networkidle0')
        await asyncio.sleep(10)
    
    print(f"📈 Final count: {message_count} WebSocket messages captured")
    print("✅ Debugging session complete!")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("👋 Script interrupted by user")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()