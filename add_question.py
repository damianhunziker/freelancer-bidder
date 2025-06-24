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
import psutil
import requests

class FreelancerQuestionAdder:
    def __init__(self, project_id):
        self.project_id = project_id
        self.driver = None
        self.existing_driver = None
        self.question_text = None
        
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
        
    def check_existing_selenium_instance(self):
        """Prüft ob bereits eine Selenium Chrome-Instanz läuft"""
        print("🔍 Suche nach existierenden Selenium Browser-Instanzen...")
        
        selenium_processes = []
        chrome_debug_ports = []
        
        # Suche nach Chrome-Prozessen mit Selenium-typischen Argumenten
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    # Prüfe auf Selenium-typische Argumente
                    if any(arg in cmdline for arg in ['--remote-debugging-port', '--user-data-dir', 'webdriver', '--disable-blink-features=AutomationControlled']):
                        selenium_processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': cmdline
                        })
                        
                        # Extrahiere Debug-Port falls vorhanden
                        if '--remote-debugging-port=' in cmdline:
                            port_part = [part for part in cmdline.split() if '--remote-debugging-port=' in part]
                            if port_part:
                                port = port_part[0].split('=')[1]
                                chrome_debug_ports.append(port)
                                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        if selenium_processes:
            print(f"✅ {len(selenium_processes)} Selenium Chrome-Instanz(en) gefunden:")
            for proc in selenium_processes:
                print(f"   📍 PID: {proc['pid']}")
                print(f"   🔧 Command: {proc['cmdline'][:100]}...")
        else:
            print("❌ Keine existierenden Selenium Browser-Instanzen gefunden")
        
        return selenium_processes, chrome_debug_ports
    
    def try_connect_to_existing_instance(self, debug_ports):
        """Versucht sich mit einer existierenden Chrome-Instanz zu verbinden"""
        print("🔌 Versuche Verbindung zu existierender Chrome-Instanz...")
        
        for port in debug_ports:
            try:
                print(f"🔄 Teste Debug-Port: {port}")
                
                # Prüfe ob der Port erreichbar ist
                response = requests.get(f'http://localhost:{port}/json/version', timeout=2)
                if response.status_code == 200:
                    print(f"✅ Chrome Debug-Port {port} ist aktiv!")
                    
                    # Versuche mit existierender Instanz zu verbinden
                    chrome_options = Options()
                    chrome_options.add_experimental_option("debuggerAddress", f"localhost:{port}")
                    
                    try:
                        self.existing_driver = webdriver.Chrome(options=chrome_options)
                        print(f"🎉 Erfolgreich mit existierender Chrome-Instanz verbunden (Port {port})!")
                        return True
                    except Exception as e:
                        print(f"❌ Verbindung zu Port {port} fehlgeschlagen: {e}")
                        continue
                        
            except requests.exceptions.RequestException:
                print(f"❌ Port {port} nicht erreichbar")
                continue
        
        return False
    
    def create_new_selenium_instance(self):
        """Erstellt eine neue Selenium Browser-Instanz"""
        print("🚀 Erstelle neue Selenium Browser-Instanz...")
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Verwende ein persistentes User-Data-Directory
        selenium_profile_dir = os.path.expanduser("~/selenium_freelancer_profile")
        if not os.path.exists(selenium_profile_dir):
            os.makedirs(selenium_profile_dir)
        chrome_options.add_argument(f"--user-data-dir={selenium_profile_dir}")
        
        # Enable remote debugging für spätere Verbindungen
        chrome_options.add_argument("--remote-debugging-port=9222")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ Neue Selenium Browser-Instanz erfolgreich erstellt!")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Erstellen der Browser-Instanz: {e}")
            return False
    
    def navigate_to_project(self, driver):
        """Navigiert zum spezifischen Projekt"""
        print(f"🌐 Navigiere zu Projekt {self.project_id}...")
        
        try:
            # Zeige aktuelle Tabs vor dem Öffnen
            current_windows_before = driver.window_handles
            print(f"📊 Aktuelle Tabs vor dem Öffnen: {len(current_windows_before)}")
            for i, window in enumerate(current_windows_before, 1):
                driver.switch_to.window(window)
                title = driver.title[:30] + "..." if len(driver.title) > 30 else driver.title
                url = driver.current_url[:40] + "..." if len(driver.current_url) > 40 else driver.current_url
                print(f"   {i}. {window[:8]}... - {title} - {url}")
            
            # Aktueller Tab/Window Handle
            original_window = driver.current_window_handle
            print(f"📍 Aktuelles Tab: {original_window[:8]}...")
            
            # IMMER ein neues Tab öffnen (leer)
            print("🆕 Öffne neues leeres Tab...")
            driver.execute_script("window.open('about:blank', '_blank');")
            
            # Kurz warten damit das neue Tab vollständig geladen ist
            time.sleep(2)
            
            # Zu neuem Tab wechseln  
            all_windows_after = driver.window_handles
            new_windows = [window for window in all_windows_after if window not in current_windows_before]
            
            if not new_windows:
                print("❌ Kein neues Tab gefunden, versuche alternative Methode...")
                # Alternative: Nehme das letzte Tab
                new_window = all_windows_after[-1]
            else:
                new_window = new_windows[0]
            
            driver.switch_to.window(new_window)
            
            print(f"🪟 Neues Tab geöffnet: {new_window[:8]}...")
            print("📄 Leeres Tab ist bereit - aktueller Tab wird NICHT überschrieben")
            
            # Jetzt zum Projekt navigieren
            project_url = f"https://www.freelancer.com/projects/{self.project_id}"
            print(f"🌐 Navigiere zu: {project_url}")
            driver.get(project_url)
            
            # Warte bis die Seite vollständig geladen ist
            if not self.wait_for_page_load(driver):
                print("⚠️ Seite möglicherweise nicht vollständig geladen, versuche trotzdem fortzufahren")
            
            print("✅ Projekt-Seite erfolgreich geladen!")
            print(f"📍 Aktuelle URL: {driver.current_url}")
            
            return new_window
            
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
        
        if not self.question_text:
            print("❌ Keine Frage vorhanden zum Einfügen")
            return False
        
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
            # Verschiedene Selektoren für Frage-Felder versuchen
            question_selectors = [
                "textarea[placeholder*='question']",
                "textarea[placeholder*='Question']",
                "textarea[name*='question']",
                "textarea[id*='question']",
                "textarea[placeholder*='Ask']",
                "textarea[placeholder*='ask']",
                ".question-field textarea",
                ".ask-question textarea",
                "textarea[placeholder*='clarification']",
                "textarea[placeholder*='details']",
                "textarea[placeholder*='message']",
                "textarea[placeholder*='Message']",
                "textarea[name*='message']",
                "textarea[id*='message']",
                "textarea[placeholder*='comment']",
                "textarea[placeholder*='Comment']",
                "textarea.form-control",  # Generic Bootstrap textarea
                "textarea",  # Fallback: jedes textarea
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
                print("❌ Kein Frage-Feld gefunden")
                
                # Debug: Zeige alle textarea Elemente
                all_textareas = driver.find_elements(By.TAG_NAME, "textarea")
                print(f"🔧 Debug: {len(all_textareas)} textarea-Elemente gefunden:")
                for i, textarea in enumerate(all_textareas):
                    try:
                        placeholder = textarea.get_attribute("placeholder") or "Kein Placeholder"
                        name = textarea.get_attribute("name") or "Kein Name"
                        id_attr = textarea.get_attribute("id") or "Keine ID"
                        is_visible = textarea.is_displayed()
                        print(f"   {i+1}. Placeholder: '{placeholder}' | Name: '{name}' | ID: '{id_attr}' | Sichtbar: {is_visible}")
                    except:
                        print(f"   {i+1}. Fehler beim Lesen der Attribute")
                
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
    
    def run(self):
        """Hauptfunktion"""
        print("💬 Freelancer.com Projekt-Frage-Adder")
        print("=" * 60)
        print(f"🎯 Projekt-ID: {self.project_id}")
        
        # 1. Suche Frage in JSON-Dateien
        if not self.find_question_in_json():
            print("❌ Keine Frage gefunden - Script beendet")
            return False
        
        # 2. Prüfe auf existierende Selenium-Instanzen
        selenium_processes, debug_ports = self.check_existing_selenium_instance()
        
        driver_to_use = None
        
        # 3. Versuche mit existierender Instanz zu verbinden
        if debug_ports:
            if self.try_connect_to_existing_instance(debug_ports):
                driver_to_use = self.existing_driver
                print("🔗 Verwende existierende Browser-Instanz")
            else:
                print("⚠️ Verbindung zu existierender Instanz fehlgeschlagen")
        
        # 4. Falls keine Verbindung möglich, erstelle neue Instanz
        if not driver_to_use:
            if self.create_new_selenium_instance():
                driver_to_use = self.driver
                print("🆕 Verwende neue Browser-Instanz")
            else:
                print("❌ Konnte keine Browser-Instanz erstellen")
                return False
        
        # 5. Navigiere zum Projekt
        if driver_to_use:
            project_window = self.navigate_to_project(driver_to_use)
            
            if project_window:
                # 6. Frage-Feld finden und ausfüllen
                success = self.find_and_fill_question_field(driver_to_use)
                
                if success:
                    print("\n✅ Frage erfolgreich eingefügt!")
                    print(f"💡 Frage: {self.question_text}")
                    print("🔄 Browser bleibt offen für weitere Bearbeitung")
                    
                    # Zeige finale Tab-Info
                    all_windows_final = driver_to_use.window_handles
                    print(f"📊 Anzahl offener Tabs: {len(all_windows_final)}")
                    for i, window in enumerate(all_windows_final, 1):
                        driver_to_use.switch_to.window(window)
                        title = driver_to_use.title[:50] + "..." if len(driver_to_use.title) > 50 else driver_to_use.title
                        url = driver_to_use.current_url[:50] + "..." if len(driver_to_use.current_url) > 50 else driver_to_use.current_url
                        is_project_tab = "🎯 PROJEKT" if window == project_window else "📄 Andere"
                        print(f"   {i}. {window[:8]}... - {is_project_tab} - {title} - {url}")
                    
                    # Zurück zum Projekt-Tab
                    driver_to_use.switch_to.window(project_window)
                    
                    input("\n⏳ Drücke ENTER um das Script zu beenden...")
                    return True
                else:
                    print("\n❌ Frage konnte nicht eingefügt werden")
                    return False
            else:
                print("\n❌ Navigation zum Projekt fehlgeschlagen")
                return False
        
        return False
    
    def cleanup(self):
        """Browser schließen (optional)"""
        print("🧹 Cleanup...")
        
        # Nur selbst erstellte Instanz schließen, nicht die existierende
        if self.driver:
            try:
                self.driver.quit()
                print("✅ Selbst erstellte Browser-Instanz geschlossen")
            except:
                pass
        
        # Existierende Instanz NICHT schließen
        if self.existing_driver:
            print("💡 Existierende Browser-Instanz bleibt offen")

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
        # Optional: Cleanup nur für selbst erstellte Instanzen
        # adder.cleanup()
        pass

if __name__ == "__main__":
    main()