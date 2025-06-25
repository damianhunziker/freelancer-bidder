#!/usr/bin/env python3
"""
Test für headless Selenium mit dem GLEICHEN Auth-Profil wie die laufende Instanz
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

def test_headless_with_auth():
    """Testet headless Browser mit dem GLEICHEN Auth-Profil"""
    print("🔐 Teste headless mit authentifizierter Session...")
    
    # Verwende EXAKT das gleiche Profil wie die laufende Instanz
    auth_profile_dir = "/Users/jgtcdghun/freelancer_auth_session"
    
    # Chrome-Optionen für headless mit Auth-Profil
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # WICHTIG: Verwende dasselbe Profil aber anderen Debug-Port
    chrome_options.add_argument(f"--user-data-dir={auth_profile_dir}")
    chrome_options.add_argument("--remote-debugging-port=9628")  # Anderer Port als 9627
    
    print(f"📁 Verwende Auth-Profil: {auth_profile_dir}")
    print(f"🔌 Debug-Port: 9628 (vermeidet Konflikt mit 9627)")
    
    driver = None
    
    try:
        # Prüfe ob Auth-Profil existiert
        if not os.path.exists(auth_profile_dir):
            print(f"❌ Auth-Profil nicht gefunden: {auth_profile_dir}")
            return False
            
        print(f"✅ Auth-Profil gefunden")
        
        # Browser starten
        print("🚀 Starte headless Chrome mit Auth-Session...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Window-Size bestätigen
        window_size = driver.get_window_size()
        print(f"✅ Headless Browser mit Auth-Session gestartet! Size: {window_size['width']}x{window_size['height']}")
        
        # Zu Freelancer.com navigieren
        print("🌐 Navigiere zu Freelancer.com...")
        driver.get("https://www.freelancer.com")
        
        # Warten auf Seitenbereitschaft
        print("⏳ Warte auf Seitenbereitschaft...")
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Warten für JavaScript und Session-Aktivierung
        time.sleep(5)
        
        # Status abrufen
        current_url = driver.current_url
        page_title = driver.title
        page_source_length = len(driver.page_source)
        
        print(f"✅ Navigation abgeschlossen!")
        print(f"📍 URL: {current_url}")
        print(f"📄 Titel: {page_title}")
        print(f"📊 Seitenlänge: {page_source_length} Zeichen")
        
        # Prüfe Login-Status durch Suche nach Login-relevanten Texten
        page_source = driver.page_source.lower()
        
        # Login-Indikatoren prüfen
        logged_in_indicators = ['dashboard', 'profile', 'logout', 'my projects', 'notifications']
        logged_out_indicators = ['sign in', 'log in', 'register', 'join now']
        
        logged_in_count = sum(1 for indicator in logged_in_indicators if indicator in page_source)
        logged_out_count = sum(1 for indicator in logged_out_indicators if indicator in page_source)
        
        print(f"\n🔍 LOGIN-STATUS ANALYSE:")
        print(f"   ✅ Eingeloggt-Indikatoren: {logged_in_count}")
        print(f"   ❌ Ausgeloggt-Indikatoren: {logged_out_count}")
        
        if logged_in_count > logged_out_count:
            print("🎉 WAHRSCHEINLICH EINGELOGGT!")
        elif logged_out_count > logged_in_count:
            print("⚠️ WAHRSCHEINLICH NICHT EINGELOGGT")
        else:
            print("❓ LOGIN-STATUS UNKLAR")
        
        # Screenshot erstellen
        print("\n📸 Erstelle Screenshot...")
        screenshots_dir = "debug_screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(screenshots_dir, f"headless_auth_test_{timestamp}.png")
        
        driver.save_screenshot(screenshot_path)
        print(f"✅ Screenshot gespeichert: {screenshot_path}")
        
        # Prüfe Screenshot
        if os.path.exists(screenshot_path):
            file_size = os.path.getsize(screenshot_path)
            print(f"📏 Screenshot-Größe: {file_size} Bytes")
            
            if file_size > 1000:
                print("✅ Screenshot scheint gültig zu sein!")
            else:
                print("⚠️ Screenshot sehr klein - möglicherweise leer")
        
        # Teste Navigation zu einem spezifischen Projekt
        print(f"\n🎯 Teste Navigation zu Projekt...")
        test_project_url = "https://www.freelancer.com/projects/39542802"
        print(f"🌐 Navigiere zu: {test_project_url}")
        
        driver.get(test_project_url)
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(3)
        
        project_url = driver.current_url
        project_title = driver.title
        print(f"📍 Projekt-URL: {project_url}")
        print(f"📄 Projekt-Titel: {project_title}")
        
        # Screenshot der Projekt-Seite
        project_screenshot = os.path.join(screenshots_dir, f"headless_project_test_{timestamp}.png")
        driver.save_screenshot(project_screenshot)
        print(f"📸 Projekt-Screenshot: {project_screenshot}")
        
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
    print("🧪 Headless Auth Session Test")
    print("=" * 50)
    
    success = test_headless_with_auth()
    
    if success:
        print("\n🎉 Test erfolgreich abgeschlossen!")
    else:
        print("\n❌ Test fehlgeschlagen!") 