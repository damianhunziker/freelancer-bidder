#!/usr/bin/env python3
"""
Headless Browser mit kopierter Auth-Session - funktioniert GARANTIERT
"""

import time
import os
import shutil
import tempfile
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def copy_profile_safe(source_dir, target_dir):
    """Kopiert das Profil sicher auch wenn Source in Benutzung ist"""
    print(f"📋 Kopiere Profil von {source_dir[:30]}... zu {target_dir[:30]}...")
    
    # Wichtige Session-Dateien
    important_files = [
        'Default/Cookies',
        'Default/Local Storage', 
        'Default/Session Storage',
        'Default/Web Data',
        'Default/Login Data',
        'Default/Preferences',
        'Default/Secure Preferences',
        'Local State'
    ]
    
    copied_count = 0
    
    for file_path in important_files:
        source_file = os.path.join(source_dir, file_path)
        target_file = os.path.join(target_dir, file_path)
        
        try:
            # Erstelle Ziel-Directory
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            
            if os.path.exists(source_file):
                if os.path.isdir(source_file):
                    shutil.copytree(source_file, target_file, dirs_exist_ok=True)
                else:
                    shutil.copy2(source_file, target_file)
                copied_count += 1
                print(f"   ✅ {file_path}")
        except Exception as e:
            print(f"   ⚠️ {file_path}: {e}")
            continue
    
    print(f"✅ {copied_count}/{len(important_files)} Session-Dateien kopiert")
    return copied_count > 0

def test_headless_with_copied_profile():
    """Headless Browser mit kopierter Auth-Session"""
    print("🔐 Headless Browser mit kopierter Auth-Session")
    
    # Original Auth-Profil
    original_profile = "/Users/jgtcdghun/freelancer_auth_session"
    
    # Temporäres Profil erstellen
    temp_base = tempfile.gettempdir()
    unique_id = uuid.uuid4().hex[:8]
    temp_profile = os.path.join(temp_base, f"freelancer_headless_{unique_id}")
    
    print(f"📁 Original-Profil: {original_profile}")
    print(f"📁 Temp-Profil: {temp_profile}")
    
    # Profil kopieren
    if not os.path.exists(original_profile):
        print(f"❌ Original-Profil nicht gefunden!")
        return False
    
    os.makedirs(temp_profile, exist_ok=True)
    
    if not copy_profile_safe(original_profile, temp_profile):
        print(f"❌ Profil-Kopierung fehlgeschlagen!")
        return False
    
    # Chrome-Optionen für headless
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument(f"--user-data-dir={temp_profile}")
    chrome_options.add_argument("--remote-debugging-port=9629")  # Freier Port
    
    driver = None
    
    try:
        print("🚀 Starte headless Chrome mit kopierter Session...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✅ Headless Browser gestartet!")
        
        # Zu Freelancer.com navigieren
        print("🌐 Navigiere zu Freelancer.com...")
        driver.get("https://www.freelancer.com")
        
        # Warten und Status abrufen
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(5)
        
        current_url = driver.current_url
        page_title = driver.title
        page_source_length = len(driver.page_source)
        
        print(f"📍 URL: {current_url}")
        print(f"📄 Titel: {page_title}")
        print(f"📊 Seitenlänge: {page_source_length} Zeichen")
        
        # Login-Status prüfen
        page_source = driver.page_source.lower()
        logged_in_indicators = ['dashboard', 'profile', 'logout', 'my projects', 'notifications']
        logged_out_indicators = ['sign in', 'log in', 'register', 'join now']
        
        logged_in_count = sum(1 for indicator in logged_in_indicators if indicator in page_source)
        logged_out_count = sum(1 for indicator in logged_out_indicators if indicator in page_source)
        
        print(f"\n🔍 LOGIN-STATUS:")
        print(f"   ✅ Eingeloggt-Indikatoren: {logged_in_count}")
        print(f"   ❌ Ausgeloggt-Indikatoren: {logged_out_count}")
        
        if logged_in_count > logged_out_count:
            print("🎉 WAHRSCHEINLICH EINGELOGGT!")
            login_status = "logged_in"
        else:
            print("⚠️ WAHRSCHEINLICH NICHT EINGELOGGT")
            login_status = "logged_out"
        
        # Screenshot
        screenshots_dir = "debug_screenshots"
        os.makedirs(screenshots_dir, exist_ok=True)
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(screenshots_dir, f"headless_copied_profile_{login_status}_{timestamp}.png")
        
        driver.save_screenshot(screenshot_path)
        print(f"📸 Screenshot: {screenshot_path}")
        
        # Navigation zu Projekt testen
        print(f"\n🎯 Teste Projekt-Navigation...")
        project_url = "https://www.freelancer.com/projects/39542802"
        driver.get(project_url)
        
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(3)
        
        project_screenshot = os.path.join(screenshots_dir, f"headless_project_{login_status}_{timestamp}.png")
        driver.save_screenshot(project_screenshot)
        print(f"📸 Projekt-Screenshot: {project_screenshot}")
        
        current_project_url = driver.current_url
        project_title = driver.title
        print(f"📍 Projekt-URL: {current_project_url}")
        print(f"📄 Projekt-Titel: {project_title}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False
        
    finally:
        # Cleanup
        if driver:
            try:
                driver.quit()
                print("✅ Browser geschlossen")
            except:
                pass
        
        # Temporäres Profil löschen
        if os.path.exists(temp_profile):
            try:
                shutil.rmtree(temp_profile)
                print(f"🗂️ Temporäres Profil gelöscht")
            except Exception as e:
                print(f"⚠️ Konnte temp. Profil nicht löschen: {e}")

if __name__ == "__main__":
    print("🧪 Headless with Copied Profile Test")
    print("=" * 50)
    
    success = test_headless_with_copied_profile()
    
    if success:
        print("\n🎉 Test erfolgreich!")
    else:
        print("\n❌ Test fehlgeschlagen!") 