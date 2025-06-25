#!/usr/bin/env python3
"""
Test für Verbindung zu der bereits laufenden Browser-Instanz über Remote Debugging
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def test_connect_to_existing():
    """Verbindet zu der bereits laufenden Browser-Instanz"""
    print("🔗 Verbinde zu laufender Browser-Instanz...")
    
    # Debug-Port der laufenden Instanz
    existing_debug_port = 9627
    
    # Chrome-Optionen
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{existing_debug_port}")
    
    print(f"🔌 Verbinde zu Debug-Port: {existing_debug_port}")
    
    driver = None
    
    try:
        # Browser-Service (ohne neue Instanz zu starten)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✅ Erfolgreich mit laufender Browser-Instanz verbunden!")
        
        # Aktuelle Seite abrufen
        current_url = driver.current_url
        page_title = driver.title
        
        print(f"📍 Aktuelle URL: {current_url}")
        print(f"📄 Aktueller Titel: {page_title}")
        
        # Zu Freelancer.com navigieren
        print("\n🌐 Navigiere zu Freelancer.com...")
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
            login_status = "logged_in"
        elif logged_out_count > logged_in_count:
            print("⚠️ WAHRSCHEINLICH NICHT EINGELOGGT")
            login_status = "logged_out"
        else:
            print("❓ LOGIN-STATUS UNKLAR")
            login_status = "unclear"
        
        # Screenshot erstellen
        print("\n📸 Erstelle Screenshot...")
        screenshots_dir = "debug_screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(screenshots_dir, f"existing_browser_test_{login_status}_{timestamp}.png")
        
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
        project_screenshot = os.path.join(screenshots_dir, f"existing_browser_project_{login_status}_{timestamp}.png")
        driver.save_screenshot(project_screenshot)
        print(f"📸 Projekt-Screenshot: {project_screenshot}")
        
        # Prüfe if Frage-Feld vorhanden
        print(f"\n🔍 Suche nach Frage-Feld...")
        question_selectors = [
            "textarea[placeholder*='question']",
            "textarea[placeholder*='Question']", 
            "textarea[name*='question']",
            "textarea[id*='question']",
            "textarea[placeholder*='Ask']",
            "textarea[placeholder*='ask']",
            "textarea",  # Fallback
        ]
        
        question_field_found = False
        for selector in question_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            print(f"✅ Frage-Feld gefunden mit: {selector}")
                            question_field_found = True
                            break
                    if question_field_found:
                        break
            except Exception as e:
                continue
        
        if not question_field_found:
            print("❌ Kein Frage-Feld gefunden")
        
        return True
        
    except Exception as e:
        print(f"❌ Fehler beim Test: {e}")
        return False
        
    finally:
        # Browser NICHT schließen (es ist die laufende Instanz!)
        print("💡 Browser bleibt offen (laufende Instanz)")

if __name__ == "__main__":
    print("🧪 Existing Browser Connection Test")
    print("=" * 50)
    
    success = test_connect_to_existing()
    
    if success:
        print("\n🎉 Test erfolgreich abgeschlossen!")
    else:
        print("\n❌ Test fehlgeschlagen!") 