#!/usr/bin/env python3
"""
Test Script für Browser Startup
Testet nur das Browser-Setup wie in freelancer-websocket-reader.py
"""

import asyncio
from pyppeteer import launch
import sys

async def test_browser_startup():
    """Test browser startup exactly like in freelancer-websocket-reader.py"""
    browser = None
    page = None
    
    try:
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
        
        try:
            print("🌐 Navigating to Freelancer.com...")
            await page.goto('https://www.freelancer.com', {'timeout': 60000})  # 60s timeout
            print("✅ Freelancer.com loaded successfully!")
        except Exception as nav_error:
            print(f"⚠️ Navigation failed: {nav_error}")
            print("💡 Browser created but navigation failed - this is expected if rate limited")
        
        print("🎯 Browser startup test completed successfully!")
        print("💡 Browser window is now open and will stay open")
        print("🔄 Browser will remain open - you can manually close it when done")
        
    except Exception as e:
        print(f"❌ Browser startup failed: {e}")
        sys.exit(1)
    
    print("✅ Test completed - browser left open - exit()")
    sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(test_browser_startup())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1) 