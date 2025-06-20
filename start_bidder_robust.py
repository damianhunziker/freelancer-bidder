#!/usr/bin/env python3
"""
Robuster Bidder-Starter für macOS
Verhindert Prozess-Beendigung bei gesperrtem Mac
"""

import os
import sys
import time
import subprocess
import signal
import json
from datetime import datetime
from pathlib import Path

class RobustBidderStarter:
    def __init__(self):
        self.is_running = True
        self.bidder_process = None
        self.caffeinate_process = None
        self.config = {
            'auto_restart': True,
            'prevent_sleep': True,
            'max_restarts': 10,
            'restart_delay': 30,
            'heartbeat_interval': 60
        }
        self.restart_count = 0
        self.start_time = time.time()
        
        # Signal Handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("🚀 Robuster Bidder-Starter initialisiert")
    
    def _signal_handler(self, signum, frame):
        """Graceful shutdown"""
        print(f"\n📡 Signal {signum} empfangen - Beende Bidder...")
        self.is_running = False
        self._cleanup()
        sys.exit(0)
    
    def _cleanup(self):
        """Cleanup beim Shutdown"""
        print("🧹 Cleanup wird durchgeführt...")
        
        # Bidder-Prozess beenden
        if self.bidder_process:
            try:
                self.bidder_process.terminate()
                self.bidder_process.wait(timeout=10)
                print("✅ Bidder-Prozess beendet")
            except:
                try:
                    self.bidder_process.kill()
                    print("⚠️ Bidder-Prozess force-killed")
                except:
                    pass
        
        # Caffeinate beenden
        if self.caffeinate_process:
            try:
                self.caffeinate_process.terminate()
                self.caffeinate_process.wait(timeout=5)
                print("✅ Sleep-Prevention deaktiviert")
            except:
                pass
    
    def start_sleep_prevention(self):
        """Startet caffeinate um System-Sleep zu verhindern"""
        if self.config['prevent_sleep'] and not self.caffeinate_process:
            try:
                self.caffeinate_process = subprocess.Popen([
                    'caffeinate', '-d', '-i', '-m', '-s'
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("☕ Sleep-Prevention aktiviert (caffeinate)")
            except Exception as e:
                print(f"⚠️ Fehler bei Sleep-Prevention: {e}")
    
    def start_bidder(self):
        """Startet den Bidder-Prozess"""
        try:
            print(f"🔄 Starte Bidder-Prozess (Versuch {self.restart_count + 1})...")
            
            # Starte bidder.py
            self.bidder_process = subprocess.Popen([
                sys.executable, 'bidder.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            print(f"✅ Bidder gestartet (PID: {self.bidder_process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Starten des Bidders: {e}")
            return False
    
    def check_bidder_health(self):
        """Prüft ob Bidder noch läuft"""
        if not self.bidder_process:
            return False
        
        poll_result = self.bidder_process.poll()
        
        if poll_result is not None:
            # Prozess ist beendet
            print(f"⚠️ Bidder-Prozess beendet (Exit Code: {poll_result})")
            
            # Zeige letzte Ausgabe
            try:
                stdout, stderr = self.bidder_process.communicate(timeout=1)
                if stderr:
                    print(f"📄 Letzte Fehlerausgabe:\n{stderr[-500:]}")  # Letzte 500 Zeichen
            except:
                pass
            
            self.bidder_process = None
            return False
        
        return True
    
    def should_restart(self):
        """Prüft ob Restart durchgeführt werden soll"""
        if not self.config['auto_restart']:
            return False
        
        if self.restart_count >= self.config['max_restarts']:
            print(f"❌ Maximale Anzahl Restarts erreicht ({self.config['max_restarts']})")
            return False
        
        return True
    
    def log_status(self):
        """Loggt aktuellen Status"""
        uptime = time.time() - self.start_time
        status = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': int(uptime),
            'restart_count': self.restart_count,
            'bidder_running': self.bidder_process is not None and self.check_bidder_health(),
            'sleep_prevention_active': self.caffeinate_process is not None
        }
        
        # Status in Datei schreiben
        try:
            with open('bidder_status.json', 'w') as f:
                json.dump(status, f, indent=2)
        except:
            pass
        
        print(f"📊 Status: Uptime {int(uptime/60)}min, Restarts: {self.restart_count}")
    
    def run(self):
        """Haupt-Loop"""
        print("🚀 Starte robusten Bidder...")
        
        # Sleep-Prevention aktivieren
        self.start_sleep_prevention()
        
        # Ersten Bidder-Start
        if not self.start_bidder():
            print("❌ Konnte Bidder nicht starten")
            return
        
        # Haupt-Überwachungsloop
        last_status_log = 0
        
        while self.is_running:
            try:
                # Bidder-Gesundheit prüfen
                if not self.check_bidder_health():
                    if self.should_restart():
                        print(f"🔄 Bidder-Restart in {self.config['restart_delay']} Sekunden...")
                        time.sleep(self.config['restart_delay'])
                        
                        self.restart_count += 1
                        if self.start_bidder():
                            print("✅ Bidder erfolgreich neu gestartet")
                        else:
                            print("❌ Bidder-Restart fehlgeschlagen")
                    else:
                        print("❌ Beende aufgrund zu vieler Restarts")
                        break
                
                # Status loggen (alle 5 Minuten)
                current_time = time.time()
                if current_time - last_status_log > 300:
                    self.log_status()
                    last_status_log = current_time
                
                # Kurze Pause
                time.sleep(self.config['heartbeat_interval'])
                
            except KeyboardInterrupt:
                print("\n⌨️ Keyboard Interrupt empfangen")
                break
            except Exception as e:
                print(f"❌ Unerwarteter Fehler: {e}")
                time.sleep(10)
        
        # Cleanup
        self._cleanup()
        print("✅ Robuster Bidder-Starter beendet")

def main():
    """Haupt-Funktion"""
    print("🔒 Robuster Bidder-Starter für macOS")
    print("====================================")
    
    # Prüfe ob bidder.py existiert
    if not os.path.exists('bidder.py'):
        print("❌ bidder.py nicht gefunden!")
        print("Bitte führe das Script im Projektverzeichnis aus.")
        return
    
    # Starte robusten Bidder
    starter = RobustBidderStarter()
    starter.run()

if __name__ == "__main__":
    main() 