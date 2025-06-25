#!/usr/bin/env python3
"""
Einfacher Test für headless Selenium mit Freelancer.com
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

def test_headless_freelancer():
    """Testet headless Browser mit Freelancer.com"""
    print("🤖 Teste headless Selenium mit Freelancer.com...")
    
    # Chrome-Optionen für headless
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    
    try:
        # Browser starten
        print("🚀 Starte headless Chrome...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Window-Size bestätigen
        window_size = driver.get_window_size()
        print(f"✅ Headless Browser gestartet! Window-Size: {window_size['width']}x{window_size['height']}")
        
        # Zu Freelancer.com navigieren
        print("🌐 Navigiere zu Freelancer.com...")
        driver.get("https://www.freelancer.com")
        
        # Warten auf Seitenbereitschaft
        print("⏳ Warte auf Seitenbereitschaft...")
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Kurz warten für JavaScript
        time.sleep(3)
        
        # Status abrufen
        current_url = driver.current_url
        page_title = driver.title
        page_source_length = len(driver.page_source)
        
        print(f"✅ Navigation abgeschlossen!")
        print(f"📍 URL: {current_url}")
        print(f"📄 Titel: {page_title}")
        print(f"📊 Seitenlänge: {page_source_length} Zeichen")
        
        # Screenshot erstellen
        print("📸 Erstelle Screenshot...")
        screenshots_dir = "debug_screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(screenshots_dir, f"headless_test_{timestamp}.png")
        
        driver.save_screenshot(screenshot_path)
        print(f"✅ Screenshot gespeichert: {screenshot_path}")
        
        # Prüfe ob Screenshot erstellt wurde
        if os.path.exists(screenshot_path):
            file_size = os.path.getsize(screenshot_path)
            print(f"📏 Screenshot-Größe: {file_size} Bytes")
            
            if file_size > 1000:  # Mindestens 1KB
                print("✅ Screenshot scheint gültig zu sein!")
            else:
                print("⚠️ Screenshot sehr klein - möglicherweise leer")
        else:
            print("❌ Screenshot-Datei nicht gefunden")
        
        return True
        
    except Exception as e:
        print(f"❌ Fehler beim Test: {e}")
        return False
        
    finally:
        # Browser schließen
        if driver:
            try:
                driver.quit()
                print("✅ Browser geschlossen")
            except Exception as e:
                print(f"⚠️ Fehler beim Schließen: {e}")

if __name__ == "__main__":
    print("🧪 Headless Selenium Test")
    print("=" * 50)
    
    success = test_headless_freelancer()
    
    if success:
        print("\n🎉 Test erfolgreich abgeschlossen!")
    else:
        print("\n❌ Test fehlgeschlagen!") 