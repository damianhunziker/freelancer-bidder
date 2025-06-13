#!/usr/bin/env python3
"""
Browser WebSocket Monitor - Echte Job-Notifications über Browser-Automation abgreifen
"""

import time
import json
import sys
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class FreelancerWebSocketMonitor:
    def __init__(self):
        self.driver = None
        self.websocket_messages = []
        self.job_notifications = []
        
    def setup_browser(self):
        """Browser mit WebSocket-Monitoring einrichten"""
        print("🚀 Browser wird eingerichtet...")
        
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Auskommentiert für Debugging
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # 🔑 WICHTIG: Verwende ein persistentes User-Data-Directory für Selenium
        # Dies verhindert Konflikte mit dem normalen Chrome und ermöglicht trotzdem gespeicherte Logins
        import os
        selenium_profile_dir = os.path.expanduser("~/selenium_freelancer_profile")
        if not os.path.exists(selenium_profile_dir):
            os.makedirs(selenium_profile_dir)
        chrome_options.add_argument(f"--user-data-dir={selenium_profile_dir}")
        
        # KEINE Inkognito-Mode Flags - damit Cookies gespeichert werden
        # chrome_options.add_argument("--incognito")  # Entfernt!
        
        # Bessere Kompatibilität
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Schneller laden
        
        # Enable console logging via dev tools
        chrome_options.add_argument("--enable-logging")
        chrome_options.add_argument("--v=1")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✅ Browser erfolgreich gestartet mit eigenem Profil!")
        
    def login_to_freelancer(self):
        """Bei Freelancer.com einloggen"""
        print("🔐 Logge bei Freelancer.com ein...")
        
        try:
            self.driver.get("https://www.freelancer.com/login")
            print("📄 Login-Seite geladen")
            
            # Warte auf Login-Formular
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Login-Daten eingeben
            username_field = self.driver.find_element(By.NAME, "username")
            password_field = self.driver.find_element(By.NAME, "password")
            
            username_field.send_keys(config.FREELANCER_USERNAME)
            password_field.send_keys(config.FREELANCER_PASSWORD)
            
            # Login-Button klicken
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            print("🔄 Login-Daten gesendet...")
            
            # Warte auf erfolgreichen Login (Dashboard oder Hauptseite)
            WebDriverWait(self.driver, 15).until(
                lambda driver: "dashboard" in driver.current_url.lower() or 
                              "freelancer.com" in driver.current_url and "login" not in driver.current_url
            )
            
            print("✅ Erfolgreich eingeloggt!")
            print(f"📍 Aktuelle URL: {self.driver.current_url}")
            
            return True
            
        except TimeoutException:
            print("❌ Login-Timeout - möglicherweise 2FA oder Captcha erforderlich")
            print("💡 Bitte manuell einloggen und dann Enter drücken...")
            input("⏳ Warten auf manuellen Login...")
            return True
            
        except Exception as e:
            print(f"❌ Login-Fehler: {e}")
            return False
    
    def navigate_to_jobs(self):
        """Zu Job-Seite navigieren für Notifications"""
        print("💼 Navigiere zu Job-Seite...")
        
        try:
            # Gehe zur Job-Browse-Seite
            self.driver.get("https://www.freelancer.com/projects")
            
            # Warte bis Seite geladen
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print("✅ Job-Seite geladen")
            print(f"📍 URL: {self.driver.current_url}")
            
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Laden der Job-Seite: {e}")
            return False
    
    def check_websocket_activity(self):
        """Direkte Überprüfung der WebSocket-Aktivität im Browser"""
        try:
            # Prüfe ob unser Monitor überhaupt geladen wurde
            monitor_loaded = self.driver.execute_script("return typeof window.websocketMessages !== 'undefined';")
            print(f"🔧 WebSocket-Monitor geladen: {monitor_loaded}")
            
            # Prüfe ob es überhaupt WebSocket-Unterstützung gibt
            websocket_support = self.driver.execute_script("return typeof WebSocket !== 'undefined';")
            print(f"🔧 WebSocket-Support: {websocket_support}")
            
            # Prüfe ob unsere Override-Funktion aktiv ist
            override_active = self.driver.execute_script("""
                return window.WebSocket.toString().includes('debugLog') || 
                       window.WebSocket.toString().includes('NEUE WEBSOCKET-VERBINDUNG');
            """)
            print(f"🔧 WebSocket-Override aktiv: {override_active}")
            
            # Versuche manuell eine Test-WebSocket zu erstellen
            test_result = self.driver.execute_script("""
                try {
                    console.log('🧪 TEST: Versuche WebSocket-Test...');
                    // Erstelle eine Test-WebSocket (wird höchstwahrscheinlich fehlschlagen, aber das ist OK)
                    var testWs = new WebSocket('wss://echo.websocket.org/');
                    console.log('🧪 TEST: WebSocket erstellt:', testWs);
                    return 'WebSocket-Test erfolgreich';
                } catch (error) {
                    console.log('🧪 TEST: WebSocket-Fehler (erwartet):', error);
                    return 'WebSocket-Test durchgeführt: ' + error.message;
                }
            """)
            print(f"🧪 WebSocket-Test: {test_result}")
            
            # Prüfe aktuelle Messages
            current_messages = self.driver.execute_script("return window.websocketMessages ? window.websocketMessages.length : 'undefined';")
            print(f"🔧 Aktuelle Messages: {current_messages}")
            
            # Prüfe ob es native WebSocket-Verbindungen gibt (Performance API)
            network_entries = self.driver.execute_script("""
                if (performance && performance.getEntriesByType) {
                    var entries = performance.getEntriesByType('resource');
                    var wsEntries = entries.filter(entry => 
                        entry.name.includes('websocket') || 
                        entry.name.includes('wss://') || 
                        entry.name.includes('ws://')) {
                        return wsEntries.map(entry => entry.name);
                    }
                }
                return [];
            """)
            print(f"🔧 Netzwerk WebSocket-Entries: {network_entries}")
            
        except Exception as e:
            print(f"❌ Fehler bei WebSocket-Activity-Check: {e}")
    
    def inject_websocket_monitor_early(self):
        """WebSocket-Monitor sofort nach Login injizieren - BEVOR WebSocket-Verbindungen erstellt werden"""
        print("💉 Injiziere WebSocket-Monitor FRÜH (vor WebSocket-Erstellung)...")
        
        early_monitor_js = """
        console.log('🔧 FRÜHER WEBSOCKET MONITOR WIRD GELADEN...');
        
        // Sofort WebSocket überschreiben, bevor die Seite eigene WebSockets erstellt
        (function() {
            // Debug-Funktion
            function debugLog(message, data = null) {
                const timestamp = new Date().toISOString();
                const logMessage = `[${timestamp}] 🔍 DEBUG: ${message}`;
                console.log(logMessage, data || '');
            }
            
            // WebSocket-Monitor Arrays initialisieren
            window.websocketMessages = [];
            window.jobNotifications = [];
            window.allWebSockets = [];
            window.debugLogs = [];
            
            debugLog('🚀 FRÜHE WebSocket-Monitor Initialisierung');
            
            // Prüfe ob bereits WebSockets existieren
            if (window.WebSocket && window.WebSocket.toString().includes('native code')) {
                debugLog('✅ Native WebSocket gefunden - wird überschrieben');
            } else {
                debugLog('⚠️ WebSocket bereits modifiziert oder nicht verfügbar');
            }
            
            // Original WebSocket sichern
            const OriginalWebSocket = window.WebSocket;
            
            // WebSocket überschreiben
            window.WebSocket = function(url, protocols) {
                debugLog('🔌 WEBSOCKET VERBINDUNG ERSTELLT', {url, protocols});
                console.log('🚨 WEBSOCKET DETECTED:', url);
                
                // WebSocket-Info speichern
                const wsInfo = {
                    url: url,
                    protocols: protocols,
                    timestamp: new Date().toISOString(),
                    status: 'creating'
                };
                window.allWebSockets.push(wsInfo);
                
                // Spezielle Behandlung für Freelancer Notification URLs
                if (url.includes('notifications.freelancer.com')) {
                    console.log('🎯 FREELANCER NOTIFICATION WEBSOCKET DETECTED:', url);
                    debugLog('🎯 GEFUNDEN: Freelancer Notification WebSocket', url);
                    
                    // Markiere als wichtige Verbindung
                    wsInfo.type = 'freelancer_notifications';
                    wsInfo.important = true;
                }
                
                // Originale WebSocket erstellen
                const ws = new OriginalWebSocket(url, protocols);
                
                // Event-Listener hinzufügen
                ws.addEventListener('open', function(event) {
                    debugLog('✅ WebSocket VERBUNDEN', url);
                    console.log('🟢 WEBSOCKET CONNECTED:', url);
                    
                    const message = {
                        timestamp: new Date().toISOString(),
                        data: 'WEBSOCKET_CONNECTED: ' + url,
                        type: 'connection',
                        url: url
                    };
                    window.websocketMessages.push(message);
                    
                    // Status updaten
                    wsInfo.status = 'connected';
                });
                
                ws.addEventListener('message', function(event) {
                    debugLog('📨 MESSAGE EMPFANGEN', {url, size: event.data.length});
                    console.log('📨 WEBSOCKET MESSAGE:', url, event.data);
                    
                    const message = {
                        timestamp: new Date().toISOString(),
                        data: event.data,
                        type: 'received',
                        url: url,
                        size: event.data.length
                    };
                    
                    window.websocketMessages.push(message);
                    
                    // Spezielle Behandlung für Freelancer Notifications
                    if (url.includes('notifications.freelancer.com')) {
                        console.log('🎯 FREELANCER NOTIFICATION WEBSOCKET:', url, event.data);
                        debugLog('🎯 FREELANCER NOTIFICATION', {url, data: event.data});
                        
                        // Alle Messages von notifications.freelancer.com sind wichtig
                        window.jobNotifications.push(message);
                    }
                    
                    // Job-Notification Check für andere URLs
                    const dataStr = event.data.toString().toLowerCase();
                    if (dataStr.includes('project') || dataStr.includes('job') || 
                        dataStr.includes('bid') || dataStr.includes('proposal') ||
                        dataStr.includes('notification') || dataStr.includes('freelancer')) {
                        
                        window.jobNotifications.push(message);
                        console.log('🎉 JOB NOTIFICATION FOUND:', event.data);
                        debugLog('💼 JOB NOTIFICATION!', message);
                    }
                });
                
                ws.addEventListener('error', function(event) {
                    debugLog('❌ WebSocket ERROR', {url, event});
                    console.log('❌ WEBSOCKET ERROR:', url, event);
                });
                
                ws.addEventListener('close', function(event) {
                    debugLog('🔌 WebSocket CLOSED', {url, code: event.code});
                    console.log('🔴 WEBSOCKET CLOSED:', url, event.code);
                    wsInfo.status = 'closed';
                });
                
                return ws;
            };
            
            debugLog('✅ WebSocket erfolgreich überschrieben');
            console.log('✅ WEBSOCKET MONITOR ACTIVE - alle neuen WebSocket-Verbindungen werden erfasst!');
        })();
        """
        
        try:
            self.driver.execute_script(early_monitor_js)
            print("✅ Früher WebSocket-Monitor erfolgreich injiziert!")
            return True
        except Exception as e:
            print(f"❌ Fehler beim frühen Injizieren: {e}")
            return False
    
    def detect_existing_websockets(self):
        """Versuche bereits existierende WebSocket-Verbindungen zu entdecken"""
        print("🔍 Suche nach bereits existierenden WebSocket-Verbindungen...")
        
        try:
            # Prüfe Performance API für WebSocket-Requests
            existing_ws = self.driver.execute_script("""
                var wsConnections = [];
                
                // 1. Performance API prüfen
                if (performance && performance.getEntriesByType) {
                    var entries = performance.getEntriesByType('resource');
                    entries.forEach(function(entry) {
                        if (entry.name.includes('websocket') || 
                            entry.name.includes('wss://') || 
                            entry.name.includes('ws://')) {
                            wsConnections.push({
                                url: entry.name,
                                type: 'performance_api',
                                startTime: entry.startTime
                            });
                        }
                    });
                }
                
                // 2. Prüfe ob Socket.IO existiert
                if (typeof io !== 'undefined') {
                    wsConnections.push({
                        url: 'Socket.IO detected',
                        type: 'socket_io',
                        sockets: Object.keys(io.sockets || {})
                    });
                }
                
                // 3. Prüfe globale WebSocket-Referenzen
                var globalProps = Object.getOwnPropertyNames(window);
                globalProps.forEach(function(prop) {
                    try {
                        if (window[prop] && window[prop].constructor && 
                            window[prop].constructor.name === 'WebSocket') {
                            wsConnections.push({
                                url: window[prop].url,
                                type: 'global_reference',
                                property: prop,
                                readyState: window[prop].readyState
                            });
                        }
                    } catch (e) {}
                });
                
                return wsConnections;
            """)
            
            if existing_ws:
                print(f"🔍 {len(existing_ws)} existierende WebSocket-Verbindungen gefunden:")
                for ws in existing_ws:
                    print(f"   🔌 {ws.get('type', 'unknown')}: {ws.get('url', 'unknown')}")
            else:
                print("⚠️  Keine existierenden WebSocket-Verbindungen erkannt")
                
            return existing_ws
            
        except Exception as e:
            print(f"❌ Fehler bei WebSocket-Erkennung: {e}")
            return []
    
    def monitor_network_activity(self):
        """Überwache Netzwerk-Aktivität für WebSocket-Verbindungen"""
        print("🌐 Überwache Netzwerk-Aktivität...")
        
        try:
            # Performance Observer für neue Netzwerk-Requests
            observer_script = """
            if (!window.networkObserver) {
                window.networkObserver = true;
                window.networkActivity = [];
                
                // Performance Observer für neue Requests
                if ('PerformanceObserver' in window) {
                    const observer = new PerformanceObserver((list) => {
                        list.getEntries().forEach((entry) => {
                            if (entry.name.includes('websocket') || 
                                entry.name.includes('wss://') || 
                                entry.name.includes('ws://')) {
                                console.log('🌐 NEUER WEBSOCKET REQUEST:', entry.name);
                                window.networkActivity.push({
                                    url: entry.name,
                                    timestamp: new Date().toISOString(),
                                    type: 'network_request'
                                });
                            }
                        });
                    });
                    observer.observe({entryTypes: ['resource']});
                    console.log('✅ Network Observer aktiviert');
                }
            }
            """
            
            self.driver.execute_script(observer_script)
            print("✅ Netzwerk-Observer aktiviert")
            
        except Exception as e:
            print(f"❌ Fehler beim Netzwerk-Monitoring: {e}")
    
    def get_websocket_messages(self):
        """WebSocket-Messages aus Browser abrufen"""
        try:
            messages = self.driver.execute_script("return window.websocketMessages || [];")
            job_notifications = self.driver.execute_script("return window.jobNotifications || [];")
            all_websockets = self.driver.execute_script("return window.allWebSockets || [];")
            debug_info = self.driver.execute_script("return window.getWebSocketDebugInfo ? window.getWebSocketDebugInfo() : null;")
            
            return messages, job_notifications, all_websockets, debug_info
        except Exception as e:
            print(f"❌ Fehler beim Abrufen der Messages: {e}")
            return [], [], [], None
    
    def get_browser_console_logs(self):
        """Browser-Console-Logs über JavaScript abrufen"""
        try:
            # Console-Logs über JavaScript sammeln
            logs_script = """
            if (!window.consoleLogs) {
                window.consoleLogs = [];
                
                // Console überschreiben um Logs zu sammeln
                const originalLog = console.log;
                const originalError = console.error;
                const originalWarn = console.warn;
                
                console.log = function(...args) {
                    window.consoleLogs.push({
                        level: 'LOG',
                        message: args.join(' '),
                        timestamp: new Date().toISOString()
                    });
                    return originalLog.apply(console, args);
                };
                
                console.error = function(...args) {
                    window.consoleLogs.push({
                        level: 'ERROR',
                        message: args.join(' '),
                        timestamp: new Date().toISOString()
                    });
                    return originalError.apply(console, args);
                };
                
                console.warn = function(...args) {
                    window.consoleLogs.push({
                        level: 'WARN',
                        message: args.join(' '),
                        timestamp: new Date().toISOString()
                    });
                    return originalWarn.apply(console, args);
                };
            }
            
            return window.consoleLogs || [];
            """
            
            logs = self.driver.execute_script(logs_script)
            return logs
        except Exception as e:
            print(f"❌ Fehler beim Abrufen der Console-Logs: {e}")
            return []
    
    def show_debug_info(self, debug_info):
        """Debug-Informationen anzeigen"""
        if debug_info:
            print("\n" + "🔧" * 50)
            print("DEBUG INFORMATIONEN:")
            print(f"📊 Total Messages: {debug_info.get('totalMessages', 0)}")
            print(f"💼 Job Notifications: {debug_info.get('jobNotifications', 0)}")
            print(f"🔌 WebSocket Connections: {debug_info.get('websocketConnections', 0)}")
            
            if debug_info.get('allConnections'):
                print("\n🌐 WEBSOCKET-VERBINDUNGEN:")
                for i, conn in enumerate(debug_info['allConnections'], 1):
                    status = conn.get('status', 'unknown')
                    print(f"  {i}. {conn['url']} - Status: {status}")
            
            if debug_info.get('lastMessages'):
                print("\n📨 LETZTE MESSAGES:")
                for msg in debug_info['lastMessages']:
                    print(f"  [{msg.get('timestamp', 'unknown')}] {msg.get('type', 'unknown')}: {str(msg.get('data', ''))[:100]}...")
            
            print("🔧" * 50)
    
    def monitor_websockets(self, duration_minutes=10):
        """WebSocket-Traffic für bestimmte Zeit überwachen"""
        print(f"👂 Überwache WebSocket-Traffic für {duration_minutes} Minuten...")
        print("🔍 Suche nach Job-Notifications...")
        print("-" * 70)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        last_message_count = 0
        
        while time.time() < end_time:
            try:
                # Messages abrufen
                messages, job_notifications, all_websockets, debug_info = self.get_websocket_messages()
                
                # Neue Messages anzeigen
                if len(messages) > last_message_count:
                    new_messages = messages[last_message_count:]
                    for msg in new_messages:
                        timestamp = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                        formatted_time = timestamp.strftime('%H:%M:%S')
                        direction = "📤" if msg['type'] == 'sent' else "📨"
                        
                        print(f"{direction} [{formatted_time}] {msg['data'][:100]}...")
                        
                        # Job-Notification gefunden!
                        if msg in job_notifications:
                            print("🎉 JOB NOTIFICATION GEFUNDEN!")
                            print(f"📄 Vollständige Daten: {msg['data']}")
                            print("-" * 50)
                    
                    last_message_count = len(messages)
                
                # Status-Update
                elapsed = time.time() - start_time
                remaining = (end_time - time.time()) / 60
                
                if int(elapsed) % 30 == 0:  # Alle 30 Sekunden
                    print(f"⏱️  {elapsed:.0f}s vergangen | {remaining:.1f}min verbleibend | {len(messages)} Messages | {len(job_notifications)} Job-Notifications")
                    
                    # Debug-Info alle 30 Sekunden anzeigen
                    if debug_info:
                        self.show_debug_info(debug_info)
                    
                    # Console-Logs anzeigen
                    console_logs = self.get_browser_console_logs()
                    if console_logs:
                        print("\n🔧 BROWSER CONSOLE LOGS (letzte):")
                        for log in console_logs[-5:]:  # Letzte 5 Logs
                            level = log.get('level', 'INFO')
                            message = log.get('message', '')
                            print(f"  [{level}] {message}")
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n⏹️  Monitoring gestoppt")
                break
            except Exception as e:
                print(f"❌ Monitoring-Fehler: {e}")
                time.sleep(5)
        
        # Finale Statistiken
        messages, job_notifications, all_websockets, debug_info = self.get_websocket_messages()
        print("\n" + "=" * 70)
        print("📊 FINALE STATISTIKEN:")
        print(f"📨 Gesamt Messages: {len(messages)}")
        print(f"💼 Job Notifications: {len(job_notifications)}")
        print(f"🔌 WebSocket Verbindungen: {len(all_websockets)}")
        
        if all_websockets:
            print("\n🌐 GEFUNDENE WEBSOCKET-VERBINDUNGEN:")
            for i, ws in enumerate(all_websockets, 1):
                print(f"{i}. {ws['url']} (seit {ws['timestamp']})")
        
        if job_notifications:
            print("\n🎉 GEFUNDENE JOB-NOTIFICATIONS:")
            for i, notification in enumerate(job_notifications, 1):
                print(f"\n{i}. {notification['timestamp']} via {notification.get('url', 'unknown')}")
                print(f"   📄 {notification['data']}")
        
        self.show_debug_info(debug_info)
        
        return messages, job_notifications, all_websockets, debug_info
    
    def cleanup(self):
        """Browser schließen"""
        if self.driver:
            print("🧹 Browser wird geschlossen...")
            self.driver.quit()
    
    def trigger_websocket_connections(self):
        """Verschiedene Seiten besuchen um WebSocket-Verbindungen zu triggern"""
        print("🔄 Triggere WebSocket-Verbindungen durch Navigation...")
        
        pages_to_visit = [
            "https://www.freelancer.com/dashboard",
            "https://www.freelancer.com/projects",
            "https://www.freelancer.com/projects/javascript",
            "https://www.freelancer.com/messages",
        ]
        
        for page in pages_to_visit:
            try:
                print(f"📄 Besuche: {page}")
                self.driver.get(page)
                time.sleep(3)  # Kurz warten für WebSocket-Verbindungen
                
                # Check für neue WebSocket-Verbindungen
                messages, job_notifications, all_websockets, debug_info = self.get_websocket_messages()
                if all_websockets:
                    print(f"✅ {len(all_websockets)} WebSocket-Verbindungen gefunden")
                    for ws in all_websockets:
                        print(f"   🔌 {ws['url']}")
                else:
                    print("⚠️  Noch keine WebSocket-Verbindungen")
                    
            except Exception as e:
                print(f"❌ Fehler beim Besuchen von {page}: {e}")
        
        print("✅ Navigation abgeschlossen")

def main():
    print("🤖 Freelancer Universal WebSocket Monitor")
    print("=" * 70)
    print("💡 Überwacht ALLE WebSocket-Verbindungen für Job-Notifications")
    print("🌐 URL-unabhängig - erfasst alle WebSocket-Traffic")
    print()
    
    monitor = FreelancerWebSocketMonitor()
    
    try:
        # Browser einrichten
        monitor.setup_browser()
        
        # Bei Freelancer einloggen
        if not monitor.login_to_freelancer():
            print("❌ Login fehlgeschlagen")
            return
        
        # SOFORT nach Login WebSocket-Monitor injizieren (vor Navigation)
        print("\n🎯 Injiziere WebSocket-Monitor SOFORT nach Login...")
        if not monitor.inject_websocket_monitor_early():
            print("❌ Frühe Monitor-Injektion fehlgeschlagen")
            return
        
        # Existierende WebSocket-Verbindungen suchen
        existing_websockets = monitor.detect_existing_websockets()
        
        # Zu Job-Seite navigieren
        if not monitor.navigate_to_jobs():
            print("❌ Navigation fehlgeschlagen")
            return
        
        # Nach Navigation nochmal prüfen
        existing_websockets_after = monitor.detect_existing_websockets()
        
        # WebSocket-Monitor ist bereits injiziert - kein weiterer Aufruf nötig
        print("✅ WebSocket-Monitor bereits aktiv")
        
        # Verschiedene Seiten besuchen um WebSocket-Verbindungen zu triggern
        monitor.trigger_websocket_connections()
        
        # Kurz warten für WebSocket-Verbindungen
        print("⏳ Warte 10 Sekunden auf WebSocket-Verbindungen...")
        time.sleep(10)
        
        # Initiale Debug-Info
        messages, job_notifications, all_websockets, debug_info = monitor.get_websocket_messages()
        print(f"\n📊 INITIAL STATUS:")
        print(f"📨 Messages: {len(messages)}")
        print(f"💼 Job-Notifications: {len(job_notifications)}")
        print(f"🔌 WebSocket-Verbindungen: {len(all_websockets)}")
        
        if debug_info:
            monitor.show_debug_info(debug_info)
        
        # Console-Logs anzeigen
        console_logs = monitor.get_browser_console_logs()
        if console_logs:
            print("\n🔧 BROWSER CONSOLE LOGS:")
            for log in console_logs:
                level = log.get('level', 'INFO')
                message = log.get('message', '')
                if 'websocket' in message.lower() or 'debug' in message.lower():
                    print(f"  [{level}] {message}")
        
        # WebSocket-Traffic überwachen
        messages, job_notifications, all_websockets, debug_info = monitor.monitor_websockets(duration_minutes=10)
        
        # Ergebnisse speichern
        if messages or all_websockets:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"all_websocket_traffic_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump({
                    'messages': messages,
                    'job_notifications': job_notifications,
                    'all_websockets': all_websockets,
                    'total_messages': len(messages),
                    'total_job_notifications': len(job_notifications),
                    'total_websocket_connections': len(all_websockets)
                }, f, indent=2)
            
            print(f"💾 Alle WebSocket-Daten gespeichert in: {filename}")
        
        if job_notifications:
            print("\n🎉 ERFOLG! Job-Notifications gefunden!")
            print("💡 WebSocket-Monitoring funktioniert!")
        elif all_websockets:
            print(f"\n🌐 {len(all_websockets)} WebSocket-Verbindungen erfasst!")
            print("💡 Keine Job-Notifications in diesem Zeitraum, aber WebSocket-Traffic funktioniert")
        else:
            print("\n⚠️  Keine WebSocket-Aktivität erkannt")
            print("💡 Versuche längere Überwachungszeit oder navigiere zu anderen Seiten")
    
    except KeyboardInterrupt:
        print("\n⏹️  Programm gestoppt")
    except Exception as e:
        print(f"\n❌ Unerwarteter Fehler: {e}")
        import traceback
        traceback.print_exc()
    finally:
        monitor.cleanup()

if __name__ == "__main__":
    main() 