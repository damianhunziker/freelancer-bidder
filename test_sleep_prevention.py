#!/usr/bin/env python3
"""
Test-Script für Sleep-Prevention
Testet ob macOS-Energiesparfunktionen korrekt verhindert werden
"""

import os
import sys
import time
import subprocess
import signal
from datetime import datetime

class SleepPreventionTester:
    def __init__(self):
        self.is_running = True
        self.caffeinate_process = None
        self.start_time = time.time()
        self.test_duration = 300  # 5 Minuten Test
        
        # Signal Handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("🧪 Sleep-Prevention Tester")
        print("=========================")
    
    def _signal_handler(self, signum, frame):
        """Graceful shutdown"""
        print(f"\n📡 Signal {signum} empfangen - Beende Test...")
        self.is_running = False
        self._cleanup()
        sys.exit(0)
    
    def _cleanup(self):
        """Cleanup beim Shutdown"""
        if self.caffeinate_process:
            try:
                self.caffeinate_process.terminate()
                self.caffeinate_process.wait(timeout=5)
                print("✅ Sleep-Prevention deaktiviert")
            except:
                pass
    
    def start_sleep_prevention(self):
        """Startet caffeinate"""
        try:
            self.caffeinate_process = subprocess.Popen([
                'caffeinate', '-d', '-i', '-m', '-s'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"☕ Sleep-Prevention gestartet (PID: {self.caffeinate_process.pid})")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Starten von caffeinate: {e}")
            return False
    
    def check_system_assertions(self):
        """Prüft aktive System-Assertions"""
        try:
            result = subprocess.run(['pmset', '-g', 'assertions'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                output = result.stdout
                
                # Suche nach caffeinate-Assertions
                caffeinate_found = 'caffeinate' in output.lower()
                prevent_sleep = 'preventuseridlesleep' in output.lower()
                prevent_display_sleep = 'preventuseridledisplaysleep' in output.lower()
                
                return {
                    'caffeinate_active': caffeinate_found,
                    'prevent_sleep': prevent_sleep,
                    'prevent_display_sleep': prevent_display_sleep,
                    'raw_output': output
                }
            
            return None
            
        except Exception as e:
            print(f"⚠️ Fehler bei Assertion-Check: {e}")
            return None
    
    def check_idle_time(self):
        """Prüft System-Idle-Zeit"""
        try:
            result = subprocess.run(['ioreg', '-n', 'IOHIDSystem', '-d1'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'HIDIdleTime' in line:
                        idle_time = int(line.split('=')[1].strip())
                        idle_seconds = idle_time / 1000000000  # Nanosekunden zu Sekunden
                        return idle_seconds
            
            return None
            
        except Exception as e:
            print(f"⚠️ Fehler bei Idle-Time-Check: {e}")
            return None
    
    def run_test(self):
        """Führt den Sleep-Prevention-Test durch"""
        print(f"🚀 Starte {self.test_duration} Sekunden Test...")
        print("💡 Sperre deinen Mac während des Tests um die Funktionalität zu testen!")
        print("")
        
        # Starte Sleep-Prevention
        if not self.start_sleep_prevention():
            print("❌ Konnte Sleep-Prevention nicht starten")
            return
        
        test_interval = 30  # Alle 30 Sekunden prüfen
        last_check = 0
        
        while self.is_running and (time.time() - self.start_time) < self.test_duration:
            current_time = time.time()
            
            if current_time - last_check >= test_interval:
                elapsed = int(current_time - self.start_time)
                remaining = self.test_duration - elapsed
                
                print(f"\n⏱️  Test läuft seit {elapsed}s (noch {remaining}s)")
                
                # Prüfe caffeinate-Prozess
                if self.caffeinate_process and self.caffeinate_process.poll() is None:
                    print("✅ caffeinate-Prozess läuft")
                else:
                    print("❌ caffeinate-Prozess beendet!")
                
                # Prüfe System-Assertions
                assertions = self.check_system_assertions()
                if assertions:
                    print(f"📊 System-Assertions:")
                    print(f"   - caffeinate aktiv: {assertions['caffeinate_active']}")
                    print(f"   - Sleep verhindert: {assertions['prevent_sleep']}")
                    print(f"   - Display-Sleep verhindert: {assertions['prevent_display_sleep']}")
                
                # Prüfe Idle-Zeit
                idle_time = self.check_idle_time()
                if idle_time is not None:
                    print(f"⏰ System Idle-Zeit: {idle_time:.1f} Sekunden")
                    if idle_time > 300:  # 5 Minuten
                        print("🔒 System scheint gesperrt zu sein")
                
                last_check = current_time
            
            time.sleep(5)  # Kurze Pause zwischen Checks
        
        # Test abgeschlossen
        elapsed = int(time.time() - self.start_time)
        print(f"\n✅ Test abgeschlossen nach {elapsed} Sekunden")
        
        # Finale Prüfung
        if self.caffeinate_process and self.caffeinate_process.poll() is None:
            print("✅ caffeinate-Prozess überlebte den gesamten Test")
        else:
            print("❌ caffeinate-Prozess wurde während des Tests beendet")
        
        self._cleanup()

def main():
    """Haupt-Funktion"""
    print("🧪 macOS Sleep-Prevention Tester")
    print("=================================")
    print("")
    print("Dieser Test prüft ob Sleep-Prevention korrekt funktioniert:")
    print("1. Startet caffeinate um System-Sleep zu verhindern")
    print("2. Überwacht System-Assertions und Idle-Zeit")
    print("3. Läuft 5 Minuten und zeigt Status-Updates")
    print("")
    print("💡 Sperre deinen Mac während des Tests!")
    print("")
    
    input("Drücke Enter um den Test zu starten...")
    
    tester = SleepPreventionTester()
    tester.run_test()

if __name__ == "__main__":
    main() 