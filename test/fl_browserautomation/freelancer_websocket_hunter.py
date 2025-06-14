#!/usr/bin/env python3
"""
Freelancer WebSocket Hunter - Speziell für dynamische notification URLs
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
from webdriver_manager.chrome import ChromeDriverManager

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class FreelancerWebSocketHunter:
    def __init__(self):
        self.driver = None
        self.websocket_urls = []
        self.notification_messages = []
        
    def setup_browser(self):
        """Browser mit spezialisiertem WebSocket-Hunting einrichten"""
        print("🎯 Freelancer WebSocket Hunter wird gestartet...")
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Verwende persistentes Profil (kein privater Browser!)
        selenium_profile_dir = os.path.expanduser("~/selenium_freelancer_profile")
        if not os.path.exists(selenium_profile_dir):
            os.makedirs(selenium_profile_dir)
        chrome_options.add_argument(f"--user-data-dir={selenium_profile_dir}")
        
        # Enable logging to capture WebSocket connections
        chrome_options.add_argument("--enable-logging")
        chrome_options.add_argument("--log-level=0")
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # Enable Chrome DevTools Protocol for network monitoring
        chrome_options.add_argument("--remote-debugging-port=9222")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✅ Browser gestartet!")
        
    def inject_websocket_hunter(self):
        """Spezialisierten WebSocket-Hunter injizieren"""
        print("🕵️ Injiziere WebSocket-Hunter...")
        
        hunter_js = """
        console.log('🎯 FREELANCER WEBSOCKET HUNTER AKTIV');
        
        // Global variables for tracking
        window.freelancerWebSockets = [];
        window.freelancerMessages = [];
        window.allNetworkRequests = [];
        
        // Sehr aggressive WebSocket-Überwachung
        (function() {
            const originalWebSocket = window.WebSocket;
            
            window.WebSocket = function(url, protocols) {
                console.log('🔍 WEBSOCKET CREATED:', url);
                
                // Prüfe auf Freelancer Notification URLs (dynamisch)
                if (url.includes('notifications.freelancer.com')) {
                    console.log('🎯 FREELANCER NOTIFICATION WEBSOCKET GEFUNDEN!', url);
                    console.log('🔗 Vollständige URL:', url);
                    
                    const wsInfo = {
                        url: url,
                        timestamp: new Date().toISOString(),
                        type: 'freelancer_notification'
                    };
                    window.freelancerWebSockets.push(wsInfo);
                    
                    // Alert für sofortige Erkennung
                    console.warn('🚨 WICHTIG: Freelancer WebSocket erkannt:', url);
                }
                
                // Original WebSocket erstellen
                const ws = new originalWebSocket(url, protocols);
                
                // Event-Listener für diese WebSocket
                ws.addEventListener('open', function(event) {
                    console.log('✅ WebSocket connected:', url);
                    if (url.includes('notifications.freelancer.com')) {
                        console.log('🎉 FREELANCER NOTIFICATION WEBSOCKET VERBUNDEN!');
                    }
                });
                
                ws.addEventListener('message', function(event) {
                    if (url.includes('notifications.freelancer.com')) {
                        console.log('📨 FREELANCER NOTIFICATION MESSAGE:', event.data);
                        window.freelancerMessages.push({
                            url: url,
                            data: event.data,
                            timestamp: new Date().toISOString()
                        });
                    }
                });
                
                ws.addEventListener('error', function(event) {
                    console.error('❌ WebSocket error:', url, event);
                });
                
                return ws;
            };
            
            // Performance Observer für alle Netzwerk-Requests
            if (window.PerformanceObserver) {
                const observer = new PerformanceObserver((list) => {
                    list.getEntries().forEach((entry) => {
                        // Alle Freelancer-bezogenen Requests loggen
                        if (entry.name.includes('freelancer.com')) {
                            console.log('🌐 FREELANCER REQUEST:', entry.name);
                            window.allNetworkRequests.push({
                                url: entry.name,
                                timestamp: new Date().toISOString(),
                                type: entry.entryType
                            });
                            
                            // Spezielle Behandlung für WebSocket-URLs
                            if (entry.name.includes('notifications.freelancer.com') || 
                                entry.name.includes('websocket')) {
                                console.log('🎯 WEBSOCKET NETWORK REQUEST:', entry.name);
                            }
                        }
                    });
                });
                
                observer.observe({entryTypes: ['navigation', 'resource']});
                console.log('✅ Performance Observer aktiv');
            }
            
            console.log('✅ WebSocket Hunter erfolgreich installiert');
        })();
        
        // Zusätzliche Funktionen für manuelles Suchen
        window.findFreelancerWebSockets = function() {
            console.log('🔍 Suche nach Freelancer WebSockets...');
            console.log('WebSocket-Verbindungen:', window.freelancerWebSockets);
            console.log('Network Requests:', window.allNetworkRequests.filter(req => 
                req.url.includes('websocket') || req.url.includes('notifications')));
            return window.freelancerWebSockets;
        };
        """
        
        try:
            self.driver.execute_script(hunter_js)
            print("✅ WebSocket-Hunter erfolgreich injiziert!")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Injizieren: {e}")
            return False
    
    def navigate_and_trigger(self):
        """Verschiedene Seiten besuchen um WebSocket-Verbindungen zu triggern"""
        print("🚀 Navigiere zu verschiedenen Seiten um WebSockets zu triggern...")
        
        # Seiten, die wahrscheinlich WebSocket-Verbindungen erstellen
        pages = [
            "https://www.freelancer.com/dashboard",
            "https://www.freelancer.com/projects",
            "https://www.freelancer.com/messages",
            "https://www.freelancer.com/projects/javascript",
            "https://www.freelancer.com/projects/python",
            "https://www.freelancer.com/notifications"
        ]
        
        for page in pages:
            try:
                print(f"📄 Besuche: {page}")
                self.driver.get(page)
                time.sleep(5)  # Warten auf WebSocket-Verbindungen
                
                # Prüfe auf gefundene WebSockets
                found_websockets = self.check_for_websockets()
                if found_websockets:
                    print(f"🎯 {len(found_websockets)} WebSocket(s) auf {page} gefunden!")
                    for ws in found_websockets:
                        if ws not in self.websocket_urls:
                            self.websocket_urls.append(ws)
                            print(f"✅ Neue WebSocket-URL: {ws}")
                
            except Exception as e:
                print(f"❌ Fehler beim Besuchen von {page}: {e}")
    
    def check_for_websockets(self):
        """Prüfe auf gefundene WebSocket-Verbindungen"""
        try:
            websockets = self.driver.execute_script("""
                // Alle gefundenen Freelancer WebSockets zurückgeben
                if (window.freelancerWebSockets) {
                    return window.freelancerWebSockets.map(ws => ws.url);
                }
                return [];
            """)
            
            return websockets
            
        except Exception as e:
            print(f"❌ Fehler beim Prüfen der WebSockets: {e}")
            return []
    
    def get_messages(self):
        """Hole alle gefangenen Messages"""
        try:
            messages = self.driver.execute_script("""
                if (window.freelancerMessages) {
                    return window.freelancerMessages;
                }
                return [];
            """)
            
            return messages
            
        except Exception as e:
            print(f"❌ Fehler beim Holen der Messages: {e}")
            return []
    
    def hunt_websockets(self, duration_minutes=5):
        """Haupt-Hunting-Loop"""
        print(f"🕵️ Starte WebSocket-Hunting für {duration_minutes} Minuten...")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        while time.time() < end_time:
            try:
                # Prüfe regelmäßig auf neue WebSockets
                current_websockets = self.check_for_websockets()
                
                for ws_url in current_websockets:
                    if ws_url not in self.websocket_urls:
                        self.websocket_urls.append(ws_url)
                        print(f"🎯 NEUE WEBSOCKET GEFUNDEN: {ws_url}")
                
                # Prüfe auf neue Messages
                current_messages = self.get_messages()
                if len(current_messages) > len(self.notification_messages):
                    new_messages = current_messages[len(self.notification_messages):]
                    self.notification_messages.extend(new_messages)
                    
                    for msg in new_messages:
                        print(f"📨 NEUE MESSAGE: {msg['url']} - {msg['data'][:100]}...")
                
                # Status-Update
                elapsed = time.time() - start_time
                remaining = (end_time - time.time()) / 60
                
                if int(elapsed) % 15 == 0:  # Alle 15 Sekunden
                    print(f"⏱️  {elapsed:.0f}s | {remaining:.1f}min verbleibend | {len(self.websocket_urls)} WebSockets | {len(self.notification_messages)} Messages")
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n⏹️  Hunting gestoppt")
                break
            except Exception as e:
                print(f"❌ Hunting-Fehler: {e}")
                time.sleep(2)
        
        return self.websocket_urls, self.notification_messages
    
    def cleanup(self):
        """Browser schließen"""
        if self.driver:
            print("🧹 Browser wird geschlossen...")
            self.driver.quit()

def main():
    print("🎯 Freelancer WebSocket Hunter")
    print("=" * 50)
    print("🔍 Spezialisiert auf dynamische notification URLs")
    print()
    
    hunter = FreelancerWebSocketHunter()
    
    try:
        # Browser einrichten
        hunter.setup_browser()
        
        # WebSocket-Hunter injizieren
        if not hunter.inject_websocket_hunter():
            print("❌ Hunter-Injektion fehlgeschlagen")
            return
        
        # Navigation durchführen
        hunter.navigate_and_trigger()
        
        # WebSocket-Hunting starten
        websockets, messages = hunter.hunt_websockets(duration_minutes=5)
        
        # Ergebnisse anzeigen
        print("\n" + "=" * 50)
        print("📊 HUNTING ERGEBNISSE:")
        print(f"🔌 Gefundene WebSocket-URLs: {len(websockets)}")
        print(f"📨 Gefangene Messages: {len(messages)}")
        
        if websockets:
            print("\n🎯 GEFUNDENE WEBSOCKET-URLS:")
            for i, url in enumerate(websockets, 1):
                print(f"{i}. {url}")
                
                # URL-Pattern analysieren
                if 'notifications.freelancer.com' in url:
                    parts = url.split('/')
                    if len(parts) >= 5:
                        session_id = parts[3]  # z.B. "667"
                        token = parts[4]       # z.B. "3xur2wdv"
                        print(f"   📝 Session-ID: {session_id}")
                        print(f"   🔑 Token: {token}")
                        print(f"   🔗 Pattern: wss://notifications.freelancer.com/{session_id}/{token}/websocket")
        
        if messages:
            print("\n📨 GEFANGENE MESSAGES:")
            for i, msg in enumerate(messages[-5:], 1):  # Letzte 5 Messages
                print(f"{i}. {msg['timestamp']} - {msg['data'][:100]}...")
        
        # Ergebnisse speichern
        if websockets or messages:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"freelancer_websockets_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump({
                    'websocket_urls': websockets,
                    'messages': messages,
                    'total_websockets': len(websockets),
                    'total_messages': len(messages),
                    'timestamp': timestamp
                }, f, indent=2)
            
            print(f"💾 Ergebnisse gespeichert in: {filename}")
        
        if websockets:
            print("\n🎉 ERFOLG! WebSocket-URLs gefunden!")
        else:
            print("\n⚠️  Keine WebSocket-URLs gefunden")
            print("💡 Versuche längere Hunting-Zeit oder andere Seiten")
    
    except KeyboardInterrupt:
        print("\n⏹️  Hunter gestoppt")
    except Exception as e:
        print(f"\n❌ Unerwarteter Fehler: {e}")
        import traceback
        traceback.print_exc()
    finally:
        hunter.cleanup()

if __name__ == "__main__":
    main() 