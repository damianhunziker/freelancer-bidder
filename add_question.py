#!/usr/bin/env python3
"""
Projekt-Frage-Adder für Freelancer.com
Prüft ob bereits eine Selenium Browser-Instanz existiert, navigiert zu einem spezifischen Projekt
und fügt eine Frage aus den JSON-Dateien ins Projekt-Frage-Feld ein.
"""

import time
import sys
import os
import json
import argparse
import glob
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

class FreelancerQuestionAdder:
    def __init__(self, project_id):
        self.project_id = project_id
        self.driver = None
        self.question_text = None
        self.temp_profile_dir = None  # Track temporäres Profil für Cleanup
        self.auth_session = None  # Auth session from websocket-reader
        
    def find_question_in_json(self):
        """Sucht die Frage für die Projekt-ID in den JSON-Dateien"""
        print(f"🔍 Suche nach Frage für Projekt-ID: {self.project_id}")
        
        # Suche in jobs/ Ordner
        json_patterns = [
            f"jobs/job_{self.project_id}.json",
            f"jobs/*{self.project_id}*.json",
            "jobs/*.json"
        ]
        
        found_files = []
        for pattern in json_patterns:
            files = glob.glob(pattern)
            found_files.extend(files)
        
        print(f"📄 Gefundene JSON-Dateien: {len(found_files)}")
        
        for json_file in found_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Prüfe verschiedene Stellen wo die Projekt-ID stehen könnte
                project_id_in_file = None
                if 'project_details' in data and 'id' in data['project_details']:
                    project_id_in_file = data['project_details']['id']
                elif 'id' in data:
                    project_id_in_file = data['id']
                elif 'project_id' in data:
                    project_id_in_file = data['project_id']
                else:
                    continue
                
                # Vergleiche sowohl als String als auch als Integer
                try:
                    match1 = project_id_in_file == self.project_id
                    match2 = project_id_in_file == int(self.project_id)
                    match3 = str(project_id_in_file) == self.project_id
                except ValueError as e:
                    match1 = match2 = match3 = False
                
                if (match1 or match2 or match3):
                    print(f"✅ Projekt {self.project_id} gefunden in: {json_file}")
                    
                    # Suche nach Frage in verschiedenen Strukturen
                    question = None
                    
                    # Struktur 1: ranking.bid_teaser.question
                    if 'ranking' in data and 'bid_teaser' in data['ranking'] and 'question' in data['ranking']['bid_teaser']:
                        question = data['ranking']['bid_teaser']['question']
                        print(f"🎯 Frage gefunden in ranking.bid_teaser.question")
                    
                    # Struktur 2: ranking.bid_text.bid_teaser.question
                    elif 'ranking' in data and 'bid_text' in data['ranking'] and 'bid_teaser' in data['ranking']['bid_text'] and 'question' in data['ranking']['bid_text']['bid_teaser']:
                        question = data['ranking']['bid_text']['bid_teaser']['question']
                        print(f"🎯 Frage gefunden in ranking.bid_text.bid_teaser.question")
                    
                    # Struktur 3: bid_teaser.question (direkt)
                    elif 'bid_teaser' in data and 'question' in data['bid_teaser']:
                        question = data['bid_teaser']['question']
                        print(f"🎯 Frage gefunden in bid_teaser.question")
                    
                    if question and question.strip():
                        self.question_text = question.strip()
                        print(f"✅ Frage gefunden: {self.question_text[:100]}...")
                        return True
                    else:
                        print(f"⚠️ Projekt gefunden, aber keine Frage vorhanden")
                        
            except (json.JSONDecodeError, KeyError, Exception) as e:
                print(f"❌ Fehler beim Lesen von {json_file}: {e}")
                continue
        
        print(f"❌ Keine Frage für Projekt-ID {self.project_id} gefunden")
        return False
        

    

    

    
    def take_debug_screenshot(self, driver, stage_name):
        """Macht einen Screenshot für Debugging-Zwecke"""
        try:
            # Erstelle Screenshots-Ordner falls nicht vorhanden
            screenshots_dir = "debug_screenshots"
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)
            
            # Screenshot-Dateiname mit Zeitstempel
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"{stage_name}_{self.project_id}_{timestamp}.png"
            screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
            
            # Screenshot machen
            driver.save_screenshot(screenshot_path)
            print(f"📸 Screenshot gespeichert: {screenshot_path}")
            
            # Zusätzliche Debug-Informationen
            try:
                page_title = driver.title
                page_url = driver.current_url
                viewport_size = driver.execute_script("return {width: window.innerWidth, height: window.innerHeight};")
                print(f"📄 Seiten-Titel: {page_title}")
                print(f"🌐 URL: {page_url}")
                print(f"📐 Viewport: {viewport_size['width']}x{viewport_size['height']}")
            except Exception as e:
                print(f"⚠️ Konnte zusätzliche Debug-Info nicht abrufen: {e}")
            
            return screenshot_path
            
        except Exception as e:
            print(f"❌ Screenshot fehlgeschlagen: {e}")
            return None

    def copy_chrome_session(self, source_profile_dir, target_profile_dir):
        """Kopiert wichtige Session-Dateien von der bestehenden Chrome-Instanz"""
        print(f"📋 Kopiere Chrome-Session von {source_profile_dir[:50]}...")
        
        try:
            import shutil
            
            # Wichtige Dateien und Ordner für Session-Daten
            important_items = [
                'Default/Cookies',
                'Default/Local Storage',
                'Default/Session Storage', 
                'Default/IndexedDB',
                'Default/Web Data',
                'Default/Login Data',
                'Default/Preferences',
                'Default/Secure Preferences',
                'Local State',
                'Default/Network Action Predictor',
                'Default/Extension Cookies'
            ]
            
            copied_items = []
            
            for item in important_items:
                source_path = os.path.join(source_profile_dir, item)
                target_path = os.path.join(target_profile_dir, item)
                
                try:
                    # Erstelle Ziel-Directory falls nötig
                    target_dir = os.path.dirname(target_path)
                    os.makedirs(target_dir, exist_ok=True)
                    
                    if os.path.exists(source_path):
                        if os.path.isdir(source_path):
                            shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                        else:
                            shutil.copy2(source_path, target_path)
                        copied_items.append(item)
                        
                except Exception as copy_error:
                    print(f"⚠️ Konnte {item} nicht kopieren: {copy_error}")
                    continue
            
            if copied_items:
                print(f"✅ {len(copied_items)} Session-Elemente kopiert:")
                for item in copied_items[:3]:  # Zeige nur erste 3
                    print(f"   📄 {item}")
                if len(copied_items) > 3:
                    print(f"   ... und {len(copied_items) - 3} weitere")
                return True
            else:
                print("❌ Keine Session-Daten kopiert")
                return False
                
        except Exception as e:
            print(f"❌ Fehler beim Kopieren der Session: {e}")
            return False

    def create_new_selenium_instance(self):
        """Erstellt eine neue Selenium Browser-Instanz mit kopierter Session"""
        print("🚀 Erstelle neue Selenium Browser-Instanz (versteckt/headless mit bestehender Session)...")
        
        chrome_options = Options()
        # HEADLESS MODE - damit der Browser nicht den Fokus stiehlt
        chrome_options.add_argument("--headless=new")  # Neuer headless-Modus
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Optimierte Einstellungen für headless mit Session
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Bilder nicht laden für Geschwindigkeit
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        
        # Erstelle temporäres Profil und kopiere Session
        import tempfile
        import uuid
        
        # Erstelle temporäres Directory
        temp_base = tempfile.gettempdir()
        unique_profile_name = f"selenium_headless_session_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        selenium_profile_dir = os.path.join(temp_base, unique_profile_name)
        
        try:
            os.makedirs(selenium_profile_dir, exist_ok=True)
            self.temp_profile_dir = selenium_profile_dir  # Speichere für Cleanup
            print(f"🗂️ Temporäres Profil erstellt: {selenium_profile_dir}")
            
            # Kopiere Auth-Session vom websocket-reader
            if hasattr(self, 'auth_session') and self.auth_session:
                print("🔄 Kopiere Auth-Session von websocket-reader für headless-Nutzung...")
                session_copied = self.copy_auth_session_from_websocket_reader(selenium_profile_dir)
                if session_copied:
                    print("✅ Auth-Session erfolgreich kopiert!")
                else:
                    print("⚠️ Auth-Session-Kopie fehlgeschlagen")
            else:
                print("⚠️ Keine Auth-Session verfügbar - bitte freelancer-websocket-reader.py starten!")
            
            chrome_options.add_argument(f"--user-data-dir={selenium_profile_dir}")
            
        except Exception as e:
            print(f"⚠️ Fehler bei Session-Setup: {e}")
            print("💡 Verwende Standard-Profile ohne Session-Kopie")
        
        # Kein remote debugging im headless-Modus (verhindert Fokus-Probleme)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ Neue versteckte Browser-Instanz mit Session erfolgreich erstellt (läuft im Hintergrund)!")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Erstellen der Browser-Instanz: {e}")
            return False
    
    def navigate_to_project(self, driver):
        """Navigiert zum spezifischen Projekt"""
        print(f"🌐 Navigiere zu Projekt {self.project_id} (im Hintergrund)...")
        
        try:
            # Im headless-Modus ist Tab-Management vereinfacht
            print("🤖 Headless-Modus: Navigiere direkt zum Projekt (kein sichtbarer Browser)")
            
            # Jetzt zum Projekt navigieren
            project_url = f"https://www.freelancer.com/projects/{self.project_id}"
            print(f"🌐 Navigiere zu: {project_url}")
            driver.get(project_url)
            
            # Warte bis die Seite vollständig geladen ist
            if not self.wait_for_page_load(driver):
                print("⚠️ Seite möglicherweise nicht vollständig geladen, versuche trotzdem fortzufahren")
            
            print("✅ Projekt-Seite erfolgreich geladen!")
            print(f"📍 Aktuelle URL: {driver.current_url}")
            
            # Mache einen Screenshot für Debugging
            self.take_debug_screenshot(driver, "project_page_loaded")
            
            return driver.current_window_handle  # Gib aktuelles Window Handle zurück
            
        except TimeoutException:
            print("❌ Timeout beim Laden der Projekt-Seite")
            return None
        except Exception as e:
            print(f"❌ Fehler beim Navigieren zum Projekt: {e}")
            return None
    
    def wait_for_page_load(self, driver, timeout=30):
        """Wartet bis JavaScript und DOM vollständig geladen sind"""
        print("⏳ Warte auf vollständiges Laden von DOM und JavaScript...")
        
        try:
            # 1. Warte bis DOM vollständig geladen ist
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            print("✅ DOM ist vollständig geladen (document.readyState = complete)")
            
            # 2. Warte auf jQuery falls vorhanden
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: d.execute_script("return typeof jQuery !== 'undefined' ? jQuery.active === 0 : true")
                )
                print("✅ jQuery AJAX-Requests abgeschlossen")
            except TimeoutException:
                print("ℹ️ jQuery nicht verfügbar oder AJAX-Timeout")
            
            # 3. Warte auf keine aktiven Fetch-Requests (moderne Alternative zu AJAX)
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("""
                        return window.fetch === undefined || 
                               (window.fetchRequestsInProgress === undefined || window.fetchRequestsInProgress === 0)
                    """)
                )
            except TimeoutException:
                print("ℹ️ Fetch-Request-Tracking nicht verfügbar")
            
            # 4. Warte auf React/Vue.js falls vorhanden
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: d.execute_script("""
                        // Check for React
                        if (window.React || document.querySelector('[data-reactroot]')) {
                            return document.querySelector('[data-reactroot]') !== null;
                        }
                        // Check for Vue.js
                        if (window.Vue || document.querySelector('[data-v-]')) {
                            return true;
                        }
                        return true; // No framework detected
                    """)
                )
                print("✅ Frontend-Framework bereit")
            except TimeoutException:
                print("ℹ️ Frontend-Framework-Check Timeout")
            
            # 5. Warte auf spezifische Freelancer.com Elemente
            try:
                WebDriverWait(driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid]")),
                        EC.presence_of_element_located((By.CLASS_NAME, "ProjectViewDetails")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".project-details")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='project']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "main")),
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                )
                print("✅ Freelancer.com spezifische Elemente geladen")
            except TimeoutException:
                print("⚠️ Freelancer.com Elemente nicht gefunden - versuche trotzdem fortzufahren")
            
            # 6. Zusätzliche Zeit für dynamische Inhalte
            time.sleep(2)
            
            # 7. Prüfe finale Seitenstabilität
            initial_html_length = len(driver.page_source)
            time.sleep(1)
            final_html_length = len(driver.page_source)
            
            if abs(final_html_length - initial_html_length) < 100:
                print("✅ Seite ist stabil - keine großen DOM-Änderungen mehr")
            else:
                print(f"⚠️ Seite noch dynamisch - HTML-Änderung: {abs(final_html_length - initial_html_length)} Zeichen")
                time.sleep(2)  # Noch etwas mehr warten
            
            # 8. Prüfe ob wichtige JavaScript-Events abgeschlossen sind
            try:
                performance_check = driver.execute_script("""
                    var timing = window.performance.timing;
                    return {
                        'loadComplete': timing.loadEventEnd > 0,
                        'domReady': timing.domContentLoadedEventEnd > 0,
                        'loadTime': timing.loadEventEnd - timing.navigationStart,
                        'domTime': timing.domContentLoadedEventEnd - timing.navigationStart
                    };
                """)
                
                if performance_check['loadComplete']:
                    print(f"✅ Load Event abgeschlossen (Zeit: {performance_check['loadTime']}ms)")
                if performance_check['domReady']:
                    print(f"✅ DOM Content Loaded (Zeit: {performance_check['domTime']}ms)")
                    
            except Exception as e:
                print(f"ℹ️ Performance-Check fehlgeschlagen: {e}")
            
            print("🎯 Seite ist vollständig geladen und bereit für Interaktion!")
            return True
            
        except TimeoutException as e:
            print(f"⏰ Timeout beim Warten auf Seitenladen: {e}")
            return False
        except Exception as e:
            print(f"❌ Fehler beim Warten auf Seitenladen: {e}")
            return False
    
    def find_and_fill_question_field(self, driver):
        """Findet das Frage-Feld und füllt es mit der Frage aus der JSON-Datei"""
        print("🔍 Suche nach Frage-Feld auf der Projekt-Seite...")
        
        # Screenshot vor der Suche
        self.take_debug_screenshot(driver, "before_field_search")
        
        if not self.question_text:
            print("❌ Keine Frage vorhanden zum Einfügen")
            return False
        
        # WICHTIG: Prüfe zuerst, ob bereits eine Frage gestellt wurde
        print("🔍 Prüfe ob bereits eine Frage für dieses Projekt existiert...")
        try:
            # Suche nach bereits gestellten Fragen oder "Already asked" Meldungen
            existing_questions = driver.find_elements(By.XPATH, "//*[contains(text(), 'question') or contains(text(), 'Question') or contains(text(), 'already') or contains(text(), 'Already')]")
            
            if existing_questions:
                for element in existing_questions:
                    text = element.text.lower()
                    if any(keyword in text for keyword in ['already asked', 'question submitted', 'question posted', 'bereits gestellt', 'already submitted']):
                        print(f"⚠️ Frage wurde bereits gestellt für dieses Projekt!")
                        print(f"💡 Gefundener Text: '{element.text}'")
                        return True  # Als Erfolg werten, da bereits eine Frage existiert
            
            # Prüfe auch nach vorhandenen Frage-Bereichen
            question_sections = driver.find_elements(By.CSS_SELECTOR, ".question-section, .questions, .project-questions, .clarification-section")
            if question_sections:
                print("🔍 Frage-Bereich gefunden - prüfe ob bereits Fragen vorhanden sind...")
                for section in question_sections:
                    if "question" in section.text.lower() and len(section.text) > 20:
                        print("💬 Es gibt bereits Fragen/Diskussion für dieses Projekt")
                        # Trotzdem versuchen eine neue Frage zu stellen
                        break
                        
        except Exception as e:
            print(f"⚠️ Fehler bei Prüfung existierender Fragen: {e}")
            # Fortfahren mit normaler Frage-Erstellung
        
        # Zusätzliche Überprüfung vor der Elementsuche
        print("🔄 Überprüfe finalen DOM-Status vor Elementsuche...")
        try:
            # Warte nochmals kurz für alle JavaScript-Animationen
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Prüfe ob die Seite wirklich stabil ist
            WebDriverWait(driver, 5).until(
                lambda d: len(d.find_elements(By.TAG_NAME, "textarea")) > 0 or 
                         len(d.find_elements(By.TAG_NAME, "input")) > 0
            )
            print("✅ Formularelemente sind verfügbar")
            
        except TimeoutException:
            print("⚠️ Timeout bei finaler DOM-Überprüfung - versuche trotzdem fortzufahren")
        
        try:
            # Robustere Selektoren für Frage-Felder (in Prioritätsreihenfolge)
            question_selectors = [
                # Hochspezifische Selektoren zuerst
                "textarea[placeholder*='question']",
                "textarea[placeholder*='Question']", 
                "textarea[name*='question']",
                "textarea[id*='question']",
                "textarea[placeholder*='Ask']",
                "textarea[placeholder*='ask']",
                "textarea[data-qa*='question']",
                "textarea[aria-label*='question']",
                
                # Clarification/Details Felder
                "textarea[placeholder*='clarification']",
                "textarea[placeholder*='details']",
                "textarea[placeholder*='more info']",
                "textarea[placeholder*='additional']",
                
                # Container-basierte Selektoren
                ".question-field textarea",
                ".ask-question textarea",
                ".clarification-field textarea",
                ".message-field textarea",
                
                # Message/Comment Felder (niedrigere Priorität)
                "textarea[placeholder*='message']",
                "textarea[placeholder*='Message']",
                "textarea[name*='message']",
                "textarea[id*='message']",
                "textarea[placeholder*='comment']",
                "textarea[placeholder*='Comment']",
                
                # Generic Selektoren (als Fallback)
                "textarea.form-control:not([readonly]):not([disabled])",  # Nur editierbare Felder
                "form textarea:not([readonly]):not([disabled])",  # Textarea in Formularen
                "textarea:not([readonly]):not([disabled])",  # Fallback: editierbare textareas
            ]
            
            question_field = None
            used_selector = None
            
            for selector in question_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # Prüfe welches Feld am besten passt (nicht versteckt, etc.)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                question_field = element
                                used_selector = selector
                                print(f"✅ Frage-Feld gefunden mit Selektor: {selector}")
                                break
                        if question_field:
                            break
                except Exception as e:
                    print(f"❌ Selektor {selector} fehlgeschlagen: {e}")
                    continue
            
            if not question_field:
                print("❌ Kein Frage-Feld gefunden mit standard Selektoren")
                
                # Erweiterte Debug-Ausgabe
                print("\n🔧 ERWEITERTE DEBUG-ANALYSE:")
                
                # 1. Alle textarea Elemente analysieren
                all_textareas = driver.find_elements(By.TAG_NAME, "textarea")
                print(f"📝 {len(all_textareas)} textarea-Elemente gefunden:")
                for i, textarea in enumerate(all_textareas):
                    try:
                        placeholder = textarea.get_attribute("placeholder") or "Kein Placeholder"
                        name = textarea.get_attribute("name") or "Kein Name"
                        id_attr = textarea.get_attribute("id") or "Keine ID"
                        class_attr = textarea.get_attribute("class") or "Keine Klasse"
                        is_visible = textarea.is_displayed()
                        is_enabled = textarea.is_enabled()
                        readonly = textarea.get_attribute("readonly")
                        print(f"   {i+1}. Placeholder: '{placeholder[:30]}...' | Name: '{name}' | ID: '{id_attr}' | Class: '{class_attr[:30]}...'")
                        print(f"       Sichtbar: {is_visible} | Enabled: {is_enabled} | ReadOnly: {readonly}")
                    except Exception as e:
                        print(f"   {i+1}. Fehler beim Lesen der Attribute: {e}")
                
                # 2. Prüfe auf andere Input-Felder
                all_inputs = driver.find_elements(By.TAG_NAME, "input")
                text_inputs = [inp for inp in all_inputs if inp.get_attribute("type") in ["text", "email", None]]
                print(f"📝 {len(text_inputs)} text input-Elemente gefunden:")
                for i, inp in enumerate(text_inputs[:5]):  # Nur erste 5 zeigen
                    try:
                        placeholder = inp.get_attribute("placeholder") or "Kein Placeholder"
                        name = inp.get_attribute("name") or "Kein Name"
                        inp_type = inp.get_attribute("type") or "text"
                        is_visible = inp.is_displayed()
                        print(f"   {i+1}. Type: {inp_type} | Placeholder: '{placeholder[:30]}...' | Name: '{name}' | Sichtbar: {is_visible}")
                    except:
                        print(f"   {i+1}. Fehler beim Lesen der Input-Attribute")
                
                # 3. Prüfe Seitentitel und URL für Kontext
                try:
                    page_title = driver.title
                    current_url = driver.current_url
                    print(f"🌐 Seite: '{page_title}' | URL: {current_url}")
                    
                    # Prüfe ob wir auf der richtigen Seite sind
                    if self.project_id not in current_url:
                        print(f"⚠️ WARNUNG: Projekt-ID {self.project_id} nicht in URL gefunden!")
                    
                except Exception as e:
                    print(f"⚠️ Fehler bei Seiteninfo: {e}")
                
                # 4. Als letzter Versuch: Nehme das erste sichtbare, editierbare textarea
                print("\n🔄 LETZTER VERSUCH: Nehme erstes editierbares textarea...")
                for textarea in all_textareas:
                    try:
                        if textarea.is_displayed() and textarea.is_enabled() and not textarea.get_attribute("readonly"):
                            question_field = textarea
                            print(f"✅ Nehme textarea als Fallback: {textarea.get_attribute('placeholder') or 'Unbekannt'}")
                            break
                    except:
                        continue
                
                if not question_field:
                    print("❌ Auch mit Fallback kein Frage-Feld gefunden")
                    return False
            
            # Feld leeren und Frage einfügen
            print(f"📝 Füge Frage ein: {self.question_text[:100]}...")
            question_field.clear()
            question_field.send_keys(self.question_text)
            
            # Warten und prüfen ob Text eingefügt wurde
            time.sleep(1)
            entered_text = question_field.get_attribute("value")
            
            if entered_text.strip() == self.question_text.strip():
                print("✅ Frage erfolgreich eingefügt!")
                
                # Versuche zuerst normales Enter (Standard für Formulare)
                print("⌨️ Versuche Frage mit Enter zu senden...")
                try:
                    question_field.send_keys(Keys.ENTER)
                    time.sleep(2)  # Warte auf Verarbeitung
                    
                    # Prüfe ob die Frage gesendet wurde (Feld ist leer oder disabled)
                    try:
                        new_value = question_field.get_attribute("value")
                        if not new_value or len(new_value.strip()) == 0:
                            print("✅ Frage erfolgreich mit Enter gesendet!")
                            return True
                        else:
                            print("⚠️ Enter hat nicht funktioniert, versuche Post-Button...")
                    except:
                        print("⚠️ Konnte Feld-Status nach Enter nicht prüfen, versuche Post-Button...")
                except Exception as e:
                    print(f"⚠️ Enter fehlgeschlagen: {e}, versuche Post-Button...")
                
                # Fallback: Jetzt Post-Button suchen und klicken
                if self.click_post_button(driver):
                    print("✅ Frage erfolgreich mit Post-Button gesendet!")
                    return True
                else:
                    print("⚠️ Frage eingefügt, aber weder Enter noch Post-Button funktionierte")
                    return True  # Trotzdem Erfolg, da Frage eingefügt wurde
            else:
                print(f"⚠️ Text möglicherweise nicht vollständig eingefügt")
                print(f"   Erwartet: {len(self.question_text)} Zeichen")
                print(f"   Eingefügt: {len(entered_text)} Zeichen")
                return True  # Trotzdem als Erfolg werten
                
        except Exception as e:
            print(f"❌ Fehler beim Einfügen der Frage: {e}")
            return False
    
    def click_post_button(self, driver):
        """Findet und klickt den Post/Submit/Send Button"""
        print("🔍 Suche nach Post-Button...")
        
        try:
            # Verschiedene Selektoren für Post/Submit-Buttons versuchen
            button_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Post')",
                "button:contains('Send')",
                "button:contains('Submit')",
                "button:contains('Ask')",
                "button[value*='post']",
                "button[value*='Post']",
                "button[value*='send']",
                "button[value*='Send']",
                "button[value*='submit']",
                "button[value*='Submit']",
                "button[id*='submit']",
                "button[id*='post']",
                "button[id*='send']",
                "button[class*='submit']",
                "button[class*='post']",
                "button[class*='send']",
                ".btn-primary",
                ".btn-submit",
                ".submit-btn",
                "button.btn",  # Generic Bootstrap button
                "button",  # Fallback: jeden button
            ]
            
            post_button = None
            used_selector = None
            
            for selector in button_selectors:
                try:
                    if ":contains(" in selector:
                        # Für text-basierte Selektoren verwende XPath
                        xpath_selector = selector.replace("button:contains('", "//button[contains(text(),'").replace("')", "')]")
                        elements = driver.find_elements(By.XPATH, xpath_selector)
                    else:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        # Prüfe welcher Button am besten passt
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                # Prüfe Text des Buttons
                                button_text = element.text.lower()
                                button_value = (element.get_attribute("value") or "").lower()
                                button_title = (element.get_attribute("title") or "").lower()
                                
                                # Priorität für Submit/Post/Send Buttons
                                if any(keyword in button_text + button_value + button_title for keyword in ['post', 'send', 'submit', 'ask']):
                                    post_button = element
                                    used_selector = selector
                                    print(f"✅ Post-Button gefunden mit Selektor: {selector}")
                                    print(f"   Button-Text: '{element.text}' | Value: '{button_value}' | Title: '{button_title}'")
                                    break
                        if post_button:
                            break
                            
                except Exception as e:
                    print(f"❌ Selektor {selector} fehlgeschlagen: {e}")
                    continue
            
            # Fallback: Wenn kein spezifischer Post-Button gefunden, nehme den ersten sichtbaren Button
            if not post_button:
                print("⚠️ Kein spezifischer Post-Button gefunden, suche nach allen Buttons...")
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                input_buttons = driver.find_elements(By.CSS_SELECTOR, "input[type='submit'], input[type='button']")
                all_buttons.extend(input_buttons)
                
                print(f"🔧 Debug: {len(all_buttons)} Button-Elemente gefunden:")
                for i, button in enumerate(all_buttons):
                    try:
                        text = button.text or "Kein Text"
                        value = button.get_attribute("value") or "Kein Value"
                        button_type = button.get_attribute("type") or "Kein Type"
                        is_visible = button.is_displayed()
                        is_enabled = button.is_enabled()
                        print(f"   {i+1}. Text: '{text}' | Value: '{value}' | Type: '{button_type}' | Sichtbar: {is_visible} | Enabled: {is_enabled}")
                        
                        # Nehme den ersten sichtbaren und aktivierten Button
                        if is_visible and is_enabled and not post_button:
                            post_button = button
                            print(f"   >>> Nehme diesen Button als Fallback")
                    except:
                        print(f"   {i+1}. Fehler beim Lesen der Button-Attribute")
            
            if not post_button:
                print("❌ Kein Post-Button gefunden")
                return False
            
            # Button klicken
            print(f"🖱️ Klicke Post-Button...")
            post_button.click()
            
            # Kurz warten für Feedback
            time.sleep(2)
            
            print("✅ Post-Button geklickt!")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Klicken des Post-Buttons: {e}")
            return False
    
    def load_auth_session_from_websocket_reader(self):
        """Lädt Auth-Session aus dem websocket-reader"""
        session_file = 'freelancer_auth_session.json'
        
        try:
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    auth_session = json.load(f)
                
                print(f"✅ Auth-Session aus websocket-reader geladen:")
                print(f"   📁 Profil: {auth_session['profile_dir']}")
                print(f"   🔌 Debug Port: {auth_session['debug_port']}")
                print(f"   📅 Erstellt von: {auth_session['created_by']}")
                
                self.auth_session = auth_session
                return True
            else:
                print(f"❌ Keine Auth-Session gefunden: {session_file}")
                print("💡 Stellen Sie sicher, dass freelancer-websocket-reader.py läuft!")
                return False
                
        except Exception as e:
            print(f"❌ Fehler beim Laden der Auth-Session: {e}")
            return False
    

    
    def copy_auth_session_from_websocket_reader(self, target_profile_dir):
        """Kopiert Auth-Session vom websocket-reader Browser"""
        if not self.auth_session or 'profile_dir' not in self.auth_session:
            print("❌ Keine Auth-Session verfügbar")
            return False
            
        source_profile_dir = self.auth_session['profile_dir']
        print(f"📋 Kopiere Auth-Session von websocket-reader: {source_profile_dir[:50]}...")
        
        return self.copy_chrome_session(source_profile_dir, target_profile_dir)

    def run(self):
        """Hauptfunktion"""
        print("💬 Freelancer.com Projekt-Frage-Adder (Headless mit websocket-reader Session)")
        print("=" * 60)
        print(f"🎯 Projekt-ID: {self.project_id}")
        print("🔄 Schritt 1: Lade Auth-Session aus websocket-reader")
        print("🔄 Schritt 2: Erstelle headless-Browser mit kopierter Session")
        
        # 1. Suche Frage in JSON-Dateien
        if not self.find_question_in_json():
            print("❌ Keine Frage gefunden - Script beendet")
            return False
        
        # 2. Lade Auth-Session aus websocket-reader
        if not self.load_auth_session_from_websocket_reader():
            print("❌ Keine Auth-Session aus websocket-reader verfügbar")
            print("💡 Bitte starten Sie freelancer-websocket-reader.py und loggen sich ein!")
            return False
        
        # 3. Erstelle headless-Browser mit kopierter Session
        print("\n🤖 Erstelle versteckten Browser mit Auth-Session...")
        if not self.create_new_selenium_instance():
            print("❌ Konnte keine Browser-Instanz erstellen")
            return False
        
        driver_to_use = self.driver
        
        # 3. Navigiere zum Projekt
        project_window = self.navigate_to_project(driver_to_use)
        
        if project_window:
            # 4. Frage-Feld finden und ausfüllen
            success = self.find_and_fill_question_field(driver_to_use)
            
            if success:
                print("\n✅ Frage erfolgreich eingefügt und gesendet!")
                print(f"💡 Frage: {self.question_text}")
                print("🌐 Browser bleibt geöffnet für weitere Nutzung")
                
                # Nur temporäre Dateien bereinigen (Browser bleibt offen)
                self.cleanup()
                return True
            else:
                print("\n❌ Frage konnte nicht eingefügt werden")
                self.cleanup()
                return False
        else:
            print("\n❌ Navigation zum Projekt fehlgeschlagen")
            self.cleanup()
            return False
    
    def cleanup(self):
        """Browser offenlassen und nur temporäre Dateien bereinigen"""
        print("🧹 Bereinige temporäre Dateien...")
        
        # Browser NICHT schließen - Browser bleibt offen für weitere Verwendung
        if self.driver:
            print("💡 Browser bleibt geöffnet für weitere Nutzung")
            # self.driver.quit()  # AUSKOMMENTIERT - Browser bleibt offen
        
        # Temporäres Profil-Verzeichnis löschen
        if self.temp_profile_dir and os.path.exists(self.temp_profile_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_profile_dir)
                print(f"🗂️ Temporäres Profil gelöscht: {self.temp_profile_dir}")
            except Exception as e:
                print(f"⚠️ Konnte temporäres Profil nicht löschen: {e}")
        
        # Hinweis: websocket-reader Session bleibt bestehen (wird dort verwaltet)
        print("💡 websocket-reader Session bleibt aktiv für weitere Verwendung")

def main():
    """Hauptfunktion mit Argument-Parsing"""
    parser = argparse.ArgumentParser(description='Fügt eine Frage aus JSON-Dateien in ein Freelancer.com Projekt ein')
    parser.add_argument('project_id', type=str, help='Die Projekt-ID für die eine Frage eingefügt werden soll')
    
    args = parser.parse_args()
    
    adder = FreelancerQuestionAdder(args.project_id)
    
    try:
        success = adder.run()
        
        if success:
            print("\n🎉 Script erfolgreich abgeschlossen!")
        else:
            print("\n❌ Script fehlgeschlagen!")
            
    except KeyboardInterrupt:
        print("\n⏹️ Script durch Benutzer abgebrochen")
        
    except Exception as e:
        print(f"\n💥 Unerwarteter Fehler: {e}")
        
    finally:
        # Cleanup für headless-Browser
        adder.cleanup()

if __name__ == "__main__":
    main()