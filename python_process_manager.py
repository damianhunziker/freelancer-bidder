#!/usr/bin/env python3
"""
Python Process Manager für macOS
Verhindert Prozess-Beendigung bei gesperrtem Mac und verwaltet Energiesparfunktionen
"""

import os
import sys
import time
import signal
import subprocess
import threading
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('python_process_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MacOSProcessManager:
    """
    Verwaltet Python-Prozesse und verhindert Beendigung bei gesperrtem Mac
    """
    
    def __init__(self):
        self.is_running = True
        self.processes = {}
        self.system_state = {
            'is_locked': False,
            'last_activity': time.time(),
            'sleep_prevention_active': False
        }
        self.config = {
            'heartbeat_interval': 30,  # Sekunden
            'max_idle_time': 3600,     # 1 Stunde
            'prevent_sleep': True,
            'auto_restart': True
        }
        
        # Signal Handler für graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("🚀 MacOS Process Manager initialisiert")
    
    def _signal_handler(self, signum, frame):
        """Graceful shutdown bei SIGINT/SIGTERM"""
        logger.info(f"📡 Signal {signum} empfangen - Graceful shutdown...")
        self.is_running = False
        self._cleanup()
        sys.exit(0)
    
    def prevent_system_sleep(self):
        """Verhindert System-Sleep mit caffeinate"""
        try:
            if not self.system_state['sleep_prevention_active']:
                # caffeinate verhindert System-Sleep
                self.caffeinate_process = subprocess.Popen([
                    'caffeinate', '-d', '-i', '-m', '-s'
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                self.system_state['sleep_prevention_active'] = True
                logger.info("☕ System-Sleep-Prevention aktiviert (caffeinate)")
                
        except Exception as e:
            logger.error(f"❌ Fehler beim Aktivieren der Sleep-Prevention: {e}")
    
    def allow_system_sleep(self):
        """Erlaubt System-Sleep wieder"""
        try:
            if self.system_state['sleep_prevention_active'] and hasattr(self, 'caffeinate_process'):
                self.caffeinate_process.terminate()
                self.caffeinate_process.wait(timeout=5)
                self.system_state['sleep_prevention_active'] = False
                logger.info("😴 System-Sleep-Prevention deaktiviert")
                
        except Exception as e:
            logger.error(f"❌ Fehler beim Deaktivieren der Sleep-Prevention: {e}")
    
    def detect_system_lock(self):
        """Erkennt ob das System gesperrt ist"""
        try:
            # Verwende ioreg um Screen-Lock-Status zu prüfen
            result = subprocess.run([
                'ioreg', '-n', 'IOHIDSystem', '-d1'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Suche nach HIDIdleTime
                for line in result.stdout.split('\n'):
                    if 'HIDIdleTime' in line:
                        # Extrahiere Idle-Zeit
                        idle_time = int(line.split('=')[1].strip())
                        # Wenn Idle-Zeit > 5 Minuten, wahrscheinlich gesperrt
                        is_locked = idle_time > 300000000000  # 5 Minuten in Nanosekunden
                        
                        if is_locked != self.system_state['is_locked']:
                            self.system_state['is_locked'] = is_locked
                            if is_locked:
                                logger.info("🔒 System-Sperrung erkannt")
                                self.on_system_locked()
                            else:
                                logger.info("🔓 System entsperrt")
                                self.on_system_unlocked()
                        
                        return is_locked
            
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Fehler bei System-Lock-Erkennung: {e}")
            return False
    
    def on_system_locked(self):
        """Wird aufgerufen wenn System gesperrt wird"""
        logger.info("🔒 System gesperrt - Aktiviere Schutzmaßnahmen...")
        
        if self.config['prevent_sleep']:
            self.prevent_system_sleep()
        
        # Erhöhe Heartbeat-Frequenz für aktive Prozesse
        for process_name, process_info in self.processes.items():
            if process_info['status'] == 'running':
                logger.info(f"🔄 Erhöhe Heartbeat für Prozess: {process_name}")
    
    def on_system_unlocked(self):
        """Wird aufgerufen wenn System entsperrt wird"""
        logger.info("🔓 System entsperrt - Normalisiere Betrieb...")
        
        if not self.config['prevent_sleep']:
            self.allow_system_sleep()
        
        # Prüfe Prozess-Status nach Entsperrung
        self.check_all_processes()
    
    def register_process(self, name: str, command: list, working_dir: str = None, auto_restart: bool = True):
        """Registriert einen Prozess zur Überwachung"""
        self.processes[name] = {
            'command': command,
            'working_dir': working_dir or os.getcwd(),
            'auto_restart': auto_restart,
            'process': None,
            'pid': None,
            'status': 'stopped',
            'last_heartbeat': time.time(),
            'restart_count': 0,
            'start_time': None
        }
        logger.info(f"📝 Prozess registriert: {name}")
    
    def start_process(self, name: str):
        """Startet einen registrierten Prozess"""
        if name not in self.processes:
            logger.error(f"❌ Prozess nicht registriert: {name}")
            return False
        
        process_info = self.processes[name]
        
        try:
            # Wechsle in Arbeitsverzeichnis
            original_cwd = os.getcwd()
            os.chdir(process_info['working_dir'])
            
            # Starte Prozess
            process = subprocess.Popen(
                process_info['command'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Zurück zum ursprünglichen Verzeichnis
            os.chdir(original_cwd)
            
            # Update Prozess-Info
            process_info['process'] = process
            process_info['pid'] = process.pid
            process_info['status'] = 'running'
            process_info['start_time'] = time.time()
            process_info['last_heartbeat'] = time.time()
            
            logger.info(f"✅ Prozess gestartet: {name} (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Starten von {name}: {e}")
            process_info['status'] = 'error'
            return False
    
    def stop_process(self, name: str, timeout: int = 10):
        """Stoppt einen Prozess graceful"""
        if name not in self.processes:
            logger.error(f"❌ Prozess nicht registriert: {name}")
            return False
        
        process_info = self.processes[name]
        
        if process_info['status'] != 'running' or not process_info['process']:
            logger.warning(f"⚠️ Prozess {name} läuft nicht")
            return True
        
        try:
            process = process_info['process']
            
            # Versuche graceful shutdown
            process.terminate()
            
            try:
                process.wait(timeout=timeout)
                logger.info(f"✅ Prozess {name} graceful beendet")
            except subprocess.TimeoutExpired:
                # Force kill wenn graceful nicht funktioniert
                process.kill()
                process.wait()
                logger.warning(f"⚠️ Prozess {name} force-killed")
            
            process_info['status'] = 'stopped'
            process_info['process'] = None
            process_info['pid'] = None
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Stoppen von {name}: {e}")
            return False
    
    def check_process_health(self, name: str):
        """Prüft Gesundheit eines Prozesses"""
        if name not in self.processes:
            return False
        
        process_info = self.processes[name]
        
        if process_info['status'] != 'running' or not process_info['process']:
            return False
        
        try:
            # Prüfe ob Prozess noch läuft
            process = process_info['process']
            poll_result = process.poll()
            
            if poll_result is not None:
                # Prozess ist beendet
                logger.warning(f"⚠️ Prozess {name} unerwartet beendet (Exit Code: {poll_result})")
                process_info['status'] = 'crashed'
                
                # Auto-Restart wenn aktiviert
                if process_info['auto_restart'] and self.config['auto_restart']:
                    logger.info(f"🔄 Auto-Restart für {name}...")
                    process_info['restart_count'] += 1
                    time.sleep(5)  # Kurze Pause vor Restart
                    return self.start_process(name)
                
                return False
            
            # Prozess läuft noch
            process_info['last_heartbeat'] = time.time()
            return True
            
        except Exception as e:
            logger.error(f"❌ Fehler bei Health-Check für {name}: {e}")
            return False
    
    def check_all_processes(self):
        """Prüft alle registrierten Prozesse"""
        for name in list(self.processes.keys()):
            self.check_process_health(name)
    
    def get_process_status(self):
        """Gibt Status aller Prozesse zurück"""
        status = {}
        for name, info in self.processes.items():
            status[name] = {
                'status': info['status'],
                'pid': info['pid'],
                'restart_count': info['restart_count'],
                'uptime': time.time() - info['start_time'] if info['start_time'] else 0,
                'last_heartbeat': info['last_heartbeat']
            }
        return status
    
    def heartbeat_loop(self):
        """Haupt-Heartbeat-Loop"""
        logger.info("💓 Heartbeat-Loop gestartet")
        
        while self.is_running:
            try:
                # System-Lock-Status prüfen
                self.detect_system_lock()
                
                # Alle Prozesse prüfen
                self.check_all_processes()
                
                # Status loggen (alle 5 Minuten)
                if int(time.time()) % 300 == 0:
                    status = self.get_process_status()
                    logger.info(f"📊 Prozess-Status: {json.dumps(status, indent=2)}")
                
                # Heartbeat-Intervall warten
                time.sleep(self.config['heartbeat_interval'])
                
            except Exception as e:
                logger.error(f"❌ Fehler im Heartbeat-Loop: {e}")
                time.sleep(10)  # Längere Pause bei Fehlern
    
    def _cleanup(self):
        """Cleanup beim Shutdown"""
        logger.info("🧹 Cleanup wird durchgeführt...")
        
        # Alle Prozesse stoppen
        for name in list(self.processes.keys()):
            self.stop_process(name)
        
        # Sleep-Prevention deaktivieren
        self.allow_system_sleep()
        
        logger.info("✅ Cleanup abgeschlossen")
    
    def run(self):
        """Startet den Process Manager"""
        logger.info("🚀 Process Manager wird gestartet...")
        
        try:
            # Starte Heartbeat-Loop in separatem Thread
            heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
            heartbeat_thread.start()
            
            # Haupt-Loop
            while self.is_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("⌨️ Keyboard Interrupt - Beende Process Manager...")
        except Exception as e:
            logger.error(f"❌ Unerwarteter Fehler: {e}")
        finally:
            self._cleanup()

def create_bidder_manager():
    """Erstellt einen Process Manager für den Bidder"""
    manager = MacOSProcessManager()
    
    # Registriere Bidder-Prozess
    manager.register_process(
        name='freelancer-bidder',
        command=['python', 'bidder.py'],
        working_dir=os.getcwd(),
        auto_restart=True
    )
    
    return manager

def main():
    """Haupt-Funktion"""
    print("🔒 MacOS Python Process Manager")
    print("===============================")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'bidder':
            # Starte Bidder mit Process Manager
            manager = create_bidder_manager()
            manager.start_process('freelancer-bidder')
            manager.run()
            
        elif command == 'status':
            # Zeige Status (TODO: Implementiere IPC)
            print("Status-Abfrage noch nicht implementiert")
            
        else:
            print(f"Unbekannter Befehl: {command}")
            print("Verfügbare Befehle: bidder, status")
    else:
        print("Verwendung:")
        print("  python python_process_manager.py bidder   # Startet Bidder mit Process Manager")
        print("  python python_process_manager.py status   # Zeigt Status")

if __name__ == "__main__":
    main() 