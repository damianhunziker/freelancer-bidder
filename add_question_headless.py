#!/usr/bin/env python3
"""
Headless Projekt-Frage-Adder für Freelancer.com
Verwendet die authentifizierte Session aus dem freelancer-websocket-reader.
Läuft vollständig im Hintergrund ohne Login-Interaktion.
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

class FreelancerQuestionAdderHeadless:
    def __init__(self, project_id):
        self.project_id = project_id
        self.driver = None
        self.question_text = None
        self.temp_profile_dir = None  # Track temporäres Profil für Cleanup
        self.auth_session = None  # Auth session info from websocket-reader
        self.project_file_path = None  # Store path to project JSON file
        self.project_data = None  # Store loaded project data
        
    def load_auth_session(self):
        """Lädt die Auth-Session aus dem websocket-reader"""
        session_file = 'freelancer_auth_session.json'
        
        try:
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    self.auth_session = json.load(f)
                
                print(f"✅ Auth-Session geladen:")
                print(f"   📁 Profil: {self.auth_session['profile_dir']}")
                print(f"   🔌 Debug Port: {self.auth_session['debug_port']}")
                print(f"   📅 Erstellt: {self.auth_session['created_by']}")
                return True
            else:
                print(f"❌ Auth-Session-Datei nicht gefunden: {session_file}")
                return False
                
        except Exception as e:
            print(f"❌ Fehler beim Laden der Auth-Session: {e}")
            return False
    
    def check_duplicate_protection(self, force_override=False):
        """🚫 CRITICAL: Prüft ob bereits eine Frage gepostet wurde oder gerade gepostet wird"""
        print(f"🔍 Prüfe Duplicate-Protection für Projekt {self.project_id}...")
        
        if force_override:
            print("⚠️ FORCE-Modus: Duplicate-Protection wird übersprungen!")
            return True
        
        if not self.project_data:
            print("⚠️ Keine Projekt-Daten geladen - kann Duplicate-Protection nicht prüfen")
            return False
            
        # Prüfe buttonStates
        button_states = self.project_data.get('buttonStates', {})
        
        # 1. Prüfe ob Frage bereits gesendet wurde
        if button_states.get('questionSent'):
            # Zusätzliche Validierung: Prüfe ob Timestamp vorhanden ist
            timestamp = button_states.get('questionSentAt')
            if timestamp:
                print(f"🚫 DUPLICATE PROTECTION: Frage bereits gesendet für Projekt {self.project_id}")
                print(f"   📅 Gesendet am: {timestamp}")
                print(f"   💡 Verwende --force um trotzdem zu posten")
                return False
            else:
                # Kein Timestamp vorhanden - wahrscheinlich veralteter/korrupter Status
                print(f"⚠️ WARNUNG: questionSent=true aber kein Timestamp gefunden")
                print(f"   💡 Vermutlich veralteter Status - bereinige und erlaube Posting")
                button_states['questionSent'] = False
                self.save_project_data()
            
        # 2. Prüfe ob gerade eine Frage gesendet wird
        if button_states.get('sendingQuestion'):
            timestamp = button_states.get('sendingQuestionStartedAt')
            
            # Prüfe ob der Lock zu alt ist (über 30 Minuten)
            if timestamp:
                try:
                    from datetime import datetime, timedelta
                    lock_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    lock_age_minutes = (datetime.now(lock_time.tzinfo) - lock_time).total_seconds() / 60
                    
                    if lock_age_minutes > 30:  # Lock älter als 30 Minuten = wahrscheinlich abgebrochener Prozess
                        print(f"⚠️ WARNUNG: sendingQuestion-Lock ist {int(lock_age_minutes)} Minuten alt")
                        print(f"   💡 Vermutlich abgebrochener Prozess - bereinige Lock")
                        button_states['sendingQuestion'] = False
                        button_states.pop('sendingQuestionStartedAt', None)
                        self.save_project_data()
                    else:
                        print(f"🚫 DUPLICATE PROTECTION: Frage wird bereits gesendet für Projekt {self.project_id}")
                        print(f"   ⏰ Gestartet am: {timestamp} (vor {int(lock_age_minutes)} Minuten)")
                        print(f"   💡 Verwende --force um trotzdem zu posten")
                        return False
                except Exception as e:
                    print(f"⚠️ Fehler beim Prüfen des Lock-Alters: {e}")
                    print(f"   💡 Bereinige ungültigen Lock")
                    button_states['sendingQuestion'] = False
                    button_states.pop('sendingQuestionStartedAt', None)
                    self.save_project_data()
            else:
                # Kein Timestamp vorhanden - bereinige Lock
                print(f"⚠️ WARNUNG: sendingQuestion=true aber kein Timestamp gefunden")
                print(f"   💡 Bereinige ungültigen Lock")
                button_states['sendingQuestion'] = False
                self.save_project_data()
            
        # 3. Prüfe ob kürzlich ein Fehler beim Senden aufgetreten ist (Cooldown)
        if button_states.get('questionSendFailed'):
            last_attempt = button_states.get('lastQuestionSendAttempt')
            if last_attempt:
                try:
                    from datetime import datetime, timedelta
                    last_attempt_time = datetime.fromisoformat(last_attempt.replace('Z', '+00:00'))
                    cooldown_minutes = 5  # 5 Minuten Cooldown nach fehlgeschlagenem Versuch
                    cooldown_until = last_attempt_time + timedelta(minutes=cooldown_minutes)
                    
                    if datetime.now(cooldown_until.tzinfo) < cooldown_until:
                        remaining_seconds = (cooldown_until - datetime.now(cooldown_until.tzinfo)).total_seconds()
                        print(f"🚫 COOLDOWN: Letzter Versuch fehlgeschlagen. Warte noch {int(remaining_seconds)}s")
                        print(f"   💡 Verwende --force um Cooldown zu umgehen")
                        return False
                except Exception as e:
                    print(f"⚠️ Fehler beim Prüfen des Cooldowns: {e}")
        
        print(f"✅ Duplicate-Protection OK - kann Frage für Projekt {self.project_id} posten")
        return True
    
    def set_question_posting_lock(self):
        """🔒 Setzt das Lock-Flag dass eine Frage gerade gepostet wird"""
        print(f"🔒 Setze Question-Posting-Lock für Projekt {self.project_id}...")
        
        if not self.project_data:
            print("❌ Keine Projekt-Daten - kann Lock nicht setzen")
            return False
            
        # Initialisiere buttonStates falls nicht vorhanden
        if 'buttonStates' not in self.project_data:
            self.project_data['buttonStates'] = {}
            
        # Setze Lock-Flags
        from datetime import datetime
        current_time = datetime.now().isoformat() + 'Z'
        
        self.project_data['buttonStates']['sendingQuestion'] = True
        self.project_data['buttonStates']['sendingQuestionStartedAt'] = current_time
        self.project_data['buttonStates']['lastQuestionSendAttempt'] = current_time
        
        # Speichere sofort um Race Conditions zu verhindern
        return self.save_project_data()
    
    def set_question_posted_success(self):
        """✅ Markiert die Frage als erfolgreich gepostet"""
        print(f"✅ Markiere Frage als erfolgreich gepostet für Projekt {self.project_id}...")
        
        if not self.project_data:
            print("❌ Keine Projekt-Daten - kann Status nicht setzen")
            return False
            
        # Initialisiere buttonStates falls nicht vorhanden
        if 'buttonStates' not in self.project_data:
            self.project_data['buttonStates'] = {}
            
        # Setze Success-Flags
        from datetime import datetime
        current_time = datetime.now().isoformat() + 'Z'
        
        self.project_data['buttonStates']['questionSent'] = True
        self.project_data['buttonStates']['questionSentAt'] = current_time
        self.project_data['buttonStates']['sendingQuestion'] = False
        self.project_data['buttonStates']['questionSendFailed'] = False
        
        # Speichere dauerhaft
        return self.save_project_data()
    
    def set_question_posted_failed(self, error_message):
        """❌ Markiert das Question-Posting als fehlgeschlagen"""
        print(f"❌ Markiere Question-Posting als fehlgeschlagen für Projekt {self.project_id}: {error_message}")
        
        if not self.project_data:
            print("❌ Keine Projekt-Daten - kann Fehler-Status nicht setzen")
            return False
            
        # Initialisiere buttonStates falls nicht vorhanden
        if 'buttonStates' not in self.project_data:
            self.project_data['buttonStates'] = {}
            
        # Setze Fehler-Flags
        from datetime import datetime
        current_time = datetime.now().isoformat() + 'Z'
        
        self.project_data['buttonStates']['sendingQuestion'] = False
        self.project_data['buttonStates']['questionSendFailed'] = True
        self.project_data['buttonStates']['questionSendErrorMessage'] = error_message
        self.project_data['buttonStates']['questionSendErrorAt'] = current_time
        
        # Speichere dauerhaft
        return self.save_project_data()
    
    def save_project_data(self):
        """Speichert die Projekt-Daten zurück in die JSON-Datei"""
        if not self.project_file_path or not self.project_data:
            print("❌ Keine Projekt-Datei oder -Daten zum Speichern")
            return False
            
        try:
            with open(self.project_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.project_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Projekt-Daten gespeichert: {self.project_file_path}")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Speichern der Projekt-Daten: {e}")
            return False
    
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
                    
                    # Speichere Projekt-Daten und Dateipfad für Duplicate-Protection
                    self.project_data = data
                    self.project_file_path = json_file
                    
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
            
            return screenshot_path
            
        except Exception as e:
            print(f"❌ Screenshot fehlgeschlagen: {e}")
            return None

    def copy_auth_session(self, source_profile_dir, target_profile_dir):
        """Kopiert Auth-Session von websocket-reader Browser - VERBESSERTE VERSION"""
        print(f"📋 Kopiere Auth-Session von {source_profile_dir[:50]}...")
        
        try:
            import shutil
            
            # REDUZIERTE Liste der wichtigsten Session-Dateien (wie im funktionierenden Test)
            important_items = [
                'Default/Cookies',
                'Default/Local Storage',
                'Default/Session Storage',
                'Default/Web Data',
                'Default/Login Data',
                'Default/Preferences',
                'Default/Secure Preferences',
                'Local State'
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
                        print(f"   ✅ {item}")
                        
                except Exception as copy_error:
                    print(f"   ⚠️ {item}: {copy_error}")
                    continue
            
            print(f"✅ {len(copied_items)}/{len(important_items)} Session-Dateien kopiert")
            return len(copied_items) > 0
                
        except Exception as e:
            print(f"❌ Fehler beim Kopieren der Session: {e}")
            return False

    def create_headless_browser(self):
        """Erstellt headless Browser mit kopierter Auth-Session - VERBESSERTE VERSION"""
        print("🤖 Erstelle headless Browser mit kopierter Auth-Session...")
        
        # Chrome-Optionen (wie im funktionierenden Test)
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Session-basierte Profil-Erstellung
        import tempfile
        import uuid
        
        # NEUE STRATEGIE: Kopiere das Auth-Profil in ein temporäres Verzeichnis
        if self.auth_session and 'profile_dir' in self.auth_session:
            auth_profile_dir = self.auth_session['profile_dir']
            
            if os.path.exists(auth_profile_dir):
                print(f"📁 Original Auth-Profil gefunden: {auth_profile_dir[:50]}...")
                
                # Erstelle temporäres Profil für Kopie
                temp_base = tempfile.gettempdir()
                unique_profile_name = f"freelancer_headless_{uuid.uuid4().hex[:8]}"
                temp_profile_dir = os.path.join(temp_base, unique_profile_name)
                os.makedirs(temp_profile_dir, exist_ok=True)
                
                print(f"📁 Temporäres Profil: {temp_profile_dir[:50]}...")
                
                # Kopiere Auth-Session
                if self.copy_auth_session(auth_profile_dir, temp_profile_dir):
                    chrome_options.add_argument(f"--user-data-dir={temp_profile_dir}")
                    self.temp_profile_dir = temp_profile_dir
                    print("✅ Auth-Session erfolgreich kopiert!")
                else:
                    print("❌ Auth-Session Kopierung fehlgeschlagen - verwende leeres Profil")
                    chrome_options.add_argument(f"--user-data-dir={temp_profile_dir}")
                    self.temp_profile_dir = temp_profile_dir
                
            else:
                print(f"❌ Auth-Profil nicht gefunden: {auth_profile_dir}")
                # Fallback: Leeres temporäres Profil
                temp_base = tempfile.gettempdir()
                unique_profile_name = f"selenium_headless_fallback_{uuid.uuid4().hex[:8]}"
                temp_profile_dir = os.path.join(temp_base, unique_profile_name)
                os.makedirs(temp_profile_dir, exist_ok=True)
                chrome_options.add_argument(f"--user-data-dir={temp_profile_dir}")
                self.temp_profile_dir = temp_profile_dir
        else:
            print("❌ Keine Auth-Session verfügbar - verwende temporäres Profil")
            # Fallback: Leeres temporäres Profil
            temp_base = tempfile.gettempdir()
            unique_profile_name = f"selenium_headless_noauth_{uuid.uuid4().hex[:8]}"
            temp_profile_dir = os.path.join(temp_base, unique_profile_name)
            os.makedirs(temp_profile_dir, exist_ok=True)
            chrome_options.add_argument(f"--user-data-dir={temp_profile_dir}")
            self.temp_profile_dir = temp_profile_dir
        
        # Debug-Port
        debug_port = 9629  # Fester freier Port
        chrome_options.add_argument(f"--remote-debugging-port={debug_port}")
        print(f"🔌 Debug-Port: {debug_port}")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Bestätige headless mode
            window_size = self.driver.get_window_size()
            print(f"✅ Headless Browser erstellt! Window-Size: {window_size['width']}x{window_size['height']}")
                
            return True
        except Exception as e:
            print(f"❌ Fehler beim Erstellen des Browsers: {e}")
            return False
    
    def navigate_to_project(self):
        """Einfache, direkte Navigation zum Projekt"""
        print(f"🌐 Navigiere direkt zu Projekt {self.project_id}...")
        
        try:
            project_url = f"https://www.freelancer.com/projects/{self.project_id}"
            print(f"🌐 URL: {project_url}")
            
            # Direkte Navigation zum Projekt (Session ist bereits aktiv)
            self.driver.get(project_url)
            
            # VERBESSERTES WARTEN: Dynamisches Selenium-basiertes Warten
            print("⏳ Warte auf vollständige Seitenlastung...")
            
            # 1. Warte auf document.readyState == "complete"
            WebDriverWait(self.driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            print("   ✅ DOM bereit")
            
            # 2. Warte auf jQuery falls vorhanden
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return typeof jQuery !== 'undefined' ? jQuery.active == 0 : true")
                )
                print("   ✅ jQuery AJAX-Requests abgeschlossen")
            except TimeoutException:
                print("   ⚠️ jQuery nicht gefunden oder Timeout")
            
            # 3. Warte auf typische Freelancer-Seiten-Elemente
            try:
                print("⏳ Warte auf Projekt-Seitenelemente...")
                WebDriverWait(self.driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".ProjectViewDetails")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='project-view']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".project-details")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "main")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
                    )
                )
                print("   ✅ Projekt-Hauptelemente geladen")
            except TimeoutException:
                print("   ⚠️ Typische Projekt-Elemente nicht gefunden, fortfahren...")
            
            # 4. Kurze Pufferzeit für dynamisches Rendering
            print("⏳ Kurze Pufferzeit für dynamisches Rendering...")
            time.sleep(2)
            
            # Status-Check
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            print(f"✅ Navigation abgeschlossen!")
            print(f"📍 URL: {current_url}")
            print(f"📄 Titel: {page_title}")
            
            # Screenshot für Debugging
            self.take_debug_screenshot(self.driver, "project_page_loaded")
            
            # Grundlegende Validierung
            if self.project_id in current_url and "freelancer" in page_title.lower():
                print("✅ Projekt-Seite erfolgreich geladen!")
                return True
            else:
                print(f"⚠️ Mögliches Problem - prüfe Screenshot")
                return True  # Fortfahren trotzdem
            
        except Exception as e:
            print(f"❌ Fehler bei Navigation: {e}")
            
            # Debug-Screenshot auch bei Fehlern
            try:
                self.take_debug_screenshot(self.driver, "navigation_error")
            except:
                pass
                
            return False
    
    def find_and_fill_question_field(self):
        """Findet das Frage-Feld und füllt es aus - mit verbessertem Timing"""
        print("🔍 Suche nach Frage-Feld...")
        
        # Screenshot vor der Suche
        self.take_debug_screenshot(self.driver, "before_field_search")
        
        if not self.question_text:
            print("❌ Keine Frage vorhanden")
            return False
        
        try:
            # Verschiedene Selektoren für Frage-Felder
            question_selectors = [
                "textarea[placeholder*='question']",
                "textarea[placeholder*='Question']", 
                "textarea[name*='question']",
                "textarea[id*='question']",
                "textarea[placeholder*='Ask']",
                "textarea[placeholder*='ask']",
                "textarea[placeholder*='clarification']",
                "textarea[placeholder*='details']",
                "textarea[placeholder*='message']",
                "textarea[placeholder*='Message']",
                "textarea",  # Fallback
            ]
            
            question_field = None
            
            # SELENIUM-BASIERTES WARTEN: Warte intelligent auf das Frage-Feld
            print("⏳ Intelligentes Warten auf Frage-Feld...")
            
            # Erste Methode: Selenium WebDriverWait mit expected_conditions
            for selector in question_selectors[:3]:  # Teste die wichtigsten Selektoren zuerst
                try:
                    print(f"   🔍 Prüfe Selector: {selector}")
                    question_field = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if question_field:
                        print(f"✅ Frage-Feld gefunden mit Selenium WebDriverWait: {selector}")
                        break
                except TimeoutException:
                    print(f"   ⏰ Timeout für {selector}")
                    continue
                except Exception as e:
                    print(f"   ❌ Fehler für {selector}: {e}")
                    continue
            
            # Fallback: Manueller Check falls WebDriverWait fehlschlägt
            if not question_field:
                print("⏳ Fallback: Manueller Check...")
                max_wait_time = 15
                check_interval = 2
                waited_time = 0
                
                while waited_time < max_wait_time and not question_field:
                    print(f"   🔍 Manueller Versuch nach {waited_time + check_interval}s...")
                    
                    for selector in question_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                for element in elements:
                                    if element.is_displayed() and element.is_enabled():
                                        question_field = element
                                        print(f"✅ Frage-Feld gefunden (manuell): {selector} (nach {waited_time + check_interval}s)")
                                        break
                                if question_field:
                                    break
                        except Exception as e:
                            continue
                    
                    if not question_field:
                        time.sleep(check_interval)
                        waited_time += check_interval
            
            if not question_field:
                print(f"❌ Kein Frage-Feld gefunden nach {max_wait_time}s Wartezeit")
                
                # Debug: Zeige alle textarea Elemente
                try:
                    all_textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
                    print(f"🔍 DEBUG: {len(all_textareas)} textarea-Elemente gefunden:")
                    for i, ta in enumerate(all_textareas[:5]):  # Zeige nur erste 5
                        try:
                            placeholder = ta.get_attribute("placeholder") or "keine"
                            name = ta.get_attribute("name") or "keine"
                            id_attr = ta.get_attribute("id") or "keine"
                            displayed = ta.is_displayed()
                            enabled = ta.is_enabled()
                            print(f"   {i+1}. placeholder='{placeholder}', name='{name}', id='{id_attr}', sichtbar={displayed}, aktiv={enabled}")
                        except Exception as e:
                            print(f"   {i+1}. Fehler beim Lesen: {e}")
                except Exception as e:
                    print(f"❌ DEBUG-Analyse fehlgeschlagen: {e}")
                
                return False
            
            # Frage einfügen
            print(f"📝 Füge Frage ein: {self.question_text[:100]}...")
            question_field.clear()
            question_field.send_keys(self.question_text)
            
            # Screenshot nach dem Einfügen der Frage
            screenshot_path = self.take_debug_screenshot(self.driver, "after_question_inserted")
            if screenshot_path:
                print(f"🔗 Screenshot nach Frage-Einfügung: {screenshot_path}")
            
            # Versuche Enter
            try:
                question_field.send_keys(Keys.ENTER)
                time.sleep(2)
                
                # Screenshot nach dem Absenden mit Enter
                screenshot_path = self.take_debug_screenshot(self.driver, "after_enter_submit")
                if screenshot_path:
                    print(f"🔗 Screenshot nach Enter-Absendung: {screenshot_path}")
                
                # Prüfe ob erfolgreich
                new_value = question_field.get_attribute("value")
                if not new_value or len(new_value.strip()) == 0:
                    print("✅ Frage erfolgreich mit Enter gesendet!")
                    return True
            except:
                pass
            
            # Versuche Post-Button
            try:
                post_button = self.driver.find_element(By.XPATH, "//button[contains(text(),'Post')]")
                if post_button.is_displayed() and post_button.is_enabled():
                    post_button.click()
                    time.sleep(2)
                    
                    # Screenshot nach dem Absenden mit Post-Button
                    screenshot_path = self.take_debug_screenshot(self.driver, "after_post_button_submit")
                    if screenshot_path:
                        print(f"🔗 Screenshot nach Post-Button-Absendung: {screenshot_path}")
                    
                    print("✅ Frage erfolgreich mit Post-Button gesendet!")
                    return True
            except:
                pass
            
            print("✅ Frage eingefügt (Sendung unklar)")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Einfügen der Frage: {e}")
            return False
    
    def cleanup(self):
        """Browser schließen und nur temporäre Dateien bereinigen"""
        print("🧹 Cleanup...")
        
        if self.driver:
            try:
                self.driver.quit()
                print("✅ Headless Browser geschlossen")
            except Exception as e:
                print(f"⚠️ Fehler beim Schließen: {e}")
        
        # Nur temporäres Profil löschen (NICHT das Original Auth-Profil!)
        if self.temp_profile_dir and os.path.exists(self.temp_profile_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_profile_dir)
                print(f"🗂️ Temporäres Profil gelöscht: {self.temp_profile_dir}")
            except Exception as e:
                print(f"⚠️ Konnte temporäres Profil nicht löschen: {e}")
        else:
            print("💡 Kein temporäres Profil zu löschen (verwendet Original Auth-Session)")

    def run(self, force_override=False):
        """Hauptfunktion mit Duplicate-Protection"""
        print("💬 Freelancer.com Headless Question Adder")
        print("=" * 60)
        print(f"🎯 Projekt-ID: {self.project_id}")
        print("🤖 Verwendet Auth-Session aus websocket-reader")
        print("🚫 Mit Duplicate-Protection wie beim Bidding-System")
        
        if force_override:
            print("⚠️ FORCE-Modus aktiviert: Duplicate-Protection wird übersprungen!")
        
        try:
            # 1. Lade Auth-Session
            if not self.load_auth_session():
                print("❌ Keine Auth-Session verfügbar - Script beendet")
                return False
            
            # 2. Suche Frage (lädt auch Projekt-Daten für Duplicate-Protection)
            if not self.find_question_in_json():
                print("❌ Keine Frage gefunden - Script beendet") 
                return False
            
            # 3. 🚫 CRITICAL: Duplicate-Protection prüfen (außer bei Force-Modus)
            if not self.check_duplicate_protection(force_override=force_override):
                print("🚫 Script beendet - Duplicate-Protection verhindert doppeltes Posting")
                return False
            
            # 4. 🔒 Lock setzen - markiere dass Posting startet (außer bei Force-Modus)
            if not force_override:
                if not self.set_question_posting_lock():
                    print("❌ Konnte Question-Posting-Lock nicht setzen - Script beendet")
                    return False
            else:
                print("⚠️ FORCE-Modus: Überspringe Lock-Setzung")
            
            # 5. Erstelle headless Browser
            if not self.create_headless_browser():
                print("❌ Browser-Erstellung fehlgeschlagen")
                if not force_override:
                    self.set_question_posted_failed("Browser-Erstellung fehlgeschlagen")
                return False
            
            # 6. Navigiere zum Projekt
            if not self.navigate_to_project():
                print("❌ Navigation fehlgeschlagen")
                self.cleanup()
                if not force_override:
                    self.set_question_posted_failed("Navigation zum Projekt fehlgeschlagen")
                return False
            
            # 7. Frage einfügen und senden
            success = self.find_and_fill_question_field()
            
            if success:
                # ✅ Erfolg - markiere als gepostet (außer bei Force-Modus, der Status nicht ändert)
                if not force_override:
                    if self.set_question_posted_success():
                        print("\n✅ Frage erfolgreich verarbeitet und Status gespeichert!")
                        print(f"💡 Frage: {self.question_text}")
                    else:
                        print("\n⚠️ Frage gepostet aber Status-Speicherung fehlgeschlagen")
                else:
                    print(f"\n✅ Frage erfolgreich verarbeitet (FORCE-Modus - Status nicht geändert)!")
                    print(f"💡 Frage: {self.question_text}")
            else:
                # ❌ Fehler - markiere als fehlgeschlagen (außer bei Force-Modus)
                if not force_override:
                    self.set_question_posted_failed("Frage-Einfügung/Sendung fehlgeschlagen")
                print("\n❌ Frage-Verarbeitung fehlgeschlagen")
            
            # 8. Cleanup
            self.cleanup()
            return success
            
        except Exception as e:
            # Bei unerwarteten Fehlern: Status als fehlgeschlagen markieren (außer bei Force-Modus)
            error_msg = f"Unerwarteter Fehler: {str(e)}"
            print(f"💥 {error_msg}")
            if not force_override:
                self.set_question_posted_failed(error_msg)
            self.cleanup()
            return False

def main():
    """Hauptfunktion mit Argument-Parsing"""
    parser = argparse.ArgumentParser(description='Headless Question Adder - verwendet Auth-Session aus websocket-reader mit Duplicate-Protection')
    parser.add_argument('project_id', type=str, help='Die Projekt-ID für die eine Frage eingefügt werden soll')
    parser.add_argument('--status', action='store_true', help='Zeigt nur den aktuellen Status der Frage für das Projekt an')
    parser.add_argument('--reset', action='store_true', help='Setzt den Question-Status zurück (nur für Debugging)')
    parser.add_argument('--force', action='store_true', help='Überspringt Duplicate-Protection und postet Frage trotzdem (für manuelles Posting)')
    
    args = parser.parse_args()
    
    # Status-Modus: Zeige nur aktuellen Status
    if args.status:
        adder = FreelancerQuestionAdderHeadless(args.project_id)
        if adder.find_question_in_json():
            button_states = adder.project_data.get('buttonStates', {})
            print(f"\n📊 Question-Status für Projekt {args.project_id}:")
            print(f"   🚫 Frage gesendet: {button_states.get('questionSent', False)}")
            print(f"   ⏳ Wird gerade gesendet: {button_states.get('sendingQuestion', False)}")
            print(f"   ❌ Letzter Versuch fehlgeschlagen: {button_states.get('questionSendFailed', False)}")
            
            if button_states.get('questionSentAt'):
                print(f"   📅 Gesendet am: {button_states['questionSentAt']}")
            if button_states.get('questionSendErrorMessage'):
                print(f"   💬 Fehler-Nachricht: {button_states['questionSendErrorMessage']}")
            if button_states.get('questionSendErrorAt'):
                print(f"   🕐 Fehler am: {button_states['questionSendErrorAt']}")
        else:
            print(f"❌ Projekt {args.project_id} nicht gefunden")
        return
    
    # Reset-Modus: Setze Status zurück (nur für Debugging)
    if args.reset:
        adder = FreelancerQuestionAdderHeadless(args.project_id)
        if adder.find_question_in_json():
            if 'buttonStates' in adder.project_data:
                # Entferne Question-bezogene Flags
                question_flags = ['questionSent', 'questionSentAt', 'sendingQuestion', 
                                'sendingQuestionStartedAt', 'questionSendFailed', 
                                'questionSendErrorMessage', 'questionSendErrorAt', 
                                'lastQuestionSendAttempt']
                
                for flag in question_flags:
                    adder.project_data['buttonStates'].pop(flag, None)
                
                if adder.save_project_data():
                    print(f"✅ Question-Status für Projekt {args.project_id} zurückgesetzt")
                else:
                    print(f"❌ Fehler beim Zurücksetzen des Status")
            else:
                print(f"💡 Keine buttonStates gefunden - nichts zu zurückzusetzen")
        else:
            print(f"❌ Projekt {args.project_id} nicht gefunden")
        return
    
    adder = FreelancerQuestionAdderHeadless(args.project_id)
    
    try:
        success = adder.run(force_override=args.force)
        
        if success:
            print("\n🎉 Script erfolgreich abgeschlossen!")
        else:
            print("\n❌ Script fehlgeschlagen!")
            
    except KeyboardInterrupt:
        print("\n⏹️ Script durch Benutzer abgebrochen")
        
    except Exception as e:
        print(f"\n💥 Unerwarteter Fehler: {e}")
        
    finally:
        # Cleanup
        adder.cleanup()

if __name__ == "__main__":
    main() 