#!/usr/bin/env python3
"""
Process Monitor - Überwacht laufende Prozesse ohne sie zu starten
Überwacht: npm run serve, npm run dev, bidder.py, freelancer-websocket-reader.py
Mit Heartbeat-System für genauere Statusüberwachung
"""

import subprocess
import time
import psutil
import signal
import sys
from datetime import datetime
import json
import os
from heartbeat_manager import HeartbeatManager
from rate_limit_manager import get_rate_limit_status, is_rate_limited

class ProcessMonitor:
    def __init__(self):
        self.monitored_processes = {
            'npm_serve': {
                'pattern': ['vue-cli-service', 'serve'],
                'description': '🌐 Vue Frontend (npm run serve)',
                'status': 'STOPPED',
                'pid': None,
                'start_time': None,
                'last_seen': None,
                'heartbeat_name': 'vue-frontend'
            },
            'npm_dev': {
                'pattern': ['node', 'server/index.js'],
                'description': '⚡ Dev Server (npm run dev)',
                'status': 'STOPPED',
                'pid': None,
                'start_time': None,
                'last_seen': None,
                'heartbeat_name': 'vue-frontend'  # Same as serve since both run same server
            },
            'bidder': {
                'pattern': ['python', 'bidder.py'],
                'description': '🤖 Bidder Script (bidder.py)',
                'status': 'STOPPED',
                'pid': None,
                'start_time': None,
                'last_seen': None,
                'heartbeat_name': 'bidder'
            },
            'websocket_reader': {
                'pattern': ['python', 'freelancer-websocket-reader.py'],
                'description': '🔗 WebSocket Reader (freelancer-websocket-reader.py)',
                'status': 'STOPPED',
                'pid': None,
                'start_time': None,
                'last_seen': None,
                'heartbeat_name': 'websocket-reader'
            }
        }
        self.running = True
        self.start_time = datetime.now()
        self.log_file = 'process_monitor.log'
        self.heartbeat_manager = HeartbeatManager()
        
    def log_message(self, message, level='INFO'):
        """Log message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Console output with colors
        if level == 'INFO':
            print(f"\033[92m{log_entry}\033[0m")  # Green
        elif level == 'WARNING':
            print(f"\033[93m{log_entry}\033[0m")  # Yellow
        elif level == 'ERROR':
            print(f"\033[91m{log_entry}\033[0m")  # Red
        else:
            print(log_entry)
        
        # File output
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"❌ Logging error: {e}")

    def find_process_by_pattern(self, pattern):
        """Find process by command line pattern"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                    
                    # Check if all pattern elements are in the command line
                    cmdline_str = ' '.join(cmdline).lower()
                    pattern_match = all(p.lower() in cmdline_str for p in pattern)
                    
                    if pattern_match:
                        return proc.info
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            self.log_message(f"Error scanning processes: {e}", 'ERROR')
        
        return None

    def check_process_status(self, process_key):
        """Check if a specific process is running"""
        process_info = self.monitored_processes[process_key]
        pattern = process_info['pattern']
        
        proc_info = self.find_process_by_pattern(pattern)
        
        if proc_info:
            pid = proc_info['pid']
            create_time = proc_info['create_time']
            
            # Process is running
            if process_info['status'] == 'STOPPED':
                # Process just started
                process_info['status'] = 'RUNNING'
                process_info['pid'] = pid
                process_info['start_time'] = datetime.fromtimestamp(create_time)
                
                self.log_message(f"✅ {process_info['description']} STARTED (PID: {pid})")
            
            process_info['last_seen'] = datetime.now()
            return True
        else:
            # Process is not running
            if process_info['status'] == 'RUNNING':
                # Process just stopped
                runtime = datetime.now() - process_info['start_time'] if process_info['start_time'] else None
                runtime_str = str(runtime).split('.')[0] if runtime else 'unknown'
                
                self.log_message(f"❌ {process_info['description']} STOPPED (Runtime: {runtime_str})", 'WARNING')
                
            process_info['status'] = 'STOPPED'
            process_info['pid'] = None
            process_info['start_time'] = None
            process_info['last_seen'] = None
            return False

    def get_system_info(self):
        """Get system resource information"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2)
            }
        except Exception as e:
            self.log_message(f"Error getting system info: {e}", 'ERROR')
            return None

    def print_status_table(self):
        """Print current status table with heartbeat information"""
        print("\n" + "="*120)
        print("📊 PROCESS MONITOR STATUS WITH HEARTBEAT")
        print("="*120)
        
        # System info
        sys_info = self.get_system_info()
        if sys_info:
            print(f"💻 System: CPU {sys_info['cpu_percent']:.1f}% | RAM {sys_info['memory_percent']:.1f}% ({sys_info['memory_available_gb']}GB free) | Disk {sys_info['disk_percent']:.1f}% ({sys_info['disk_free_gb']}GB free)")
        
        # Rate Limit Status
        rate_limit_status = get_rate_limit_status()
        if rate_limit_status['is_rate_limited']:
            remaining_min = rate_limit_status['remaining_seconds'] // 60
            remaining_sec = rate_limit_status['remaining_seconds'] % 60
            print(f"🚫 GLOBAL RATE LIMIT AKTIV: {remaining_min}m {remaining_sec}s verbleibend (bis {rate_limit_status['timeout_until']})")
        else:
            print("✅ Rate Limit: CLEAR")
        
        # Runtime
        runtime = datetime.now() - self.start_time
        runtime_str = str(runtime).split('.')[0]
        print(f"⏱️  Monitor Runtime: {runtime_str}")
        
        print("-"*120)
        print(f"{'PROCESS':<40} {'STATUS':<10} {'PID':<8} {'RUNTIME':<15} {'LAST SEEN':<20} {'HEARTBEAT':<25}")
        print("-"*120)
        
        # Get all heartbeat statuses
        heartbeat_statuses = self.heartbeat_manager.get_all_processes_status()
        
        for key, proc in self.monitored_processes.items():
            status_icon = "🟢" if proc['status'] == 'RUNNING' else "🔴"
            status = f"{status_icon} {proc['status']}"
            
            pid = str(proc['pid']) if proc['pid'] else '-'
            
            if proc['start_time']:
                runtime = datetime.now() - proc['start_time']
                runtime_str = str(runtime).split('.')[0]
            else:
                runtime_str = '-'
                
            last_seen = proc['last_seen'].strftime('%H:%M:%S') if proc['last_seen'] else '-'
            
            # Get heartbeat information with rate limit indicator
            heartbeat_name = proc.get('heartbeat_name', key)
            heartbeat_info = heartbeat_statuses.get(heartbeat_name, {})
            
            if heartbeat_info:
                is_alive = heartbeat_info.get('is_alive', False)
                time_since = heartbeat_info.get('time_since_formatted', 'unknown')
                heartbeat_icon = "💚" if is_alive else "💔"
                
                # Add rate limit indicator
                rate_limit_indicator = ""
                if rate_limit_status['is_rate_limited']:
                    remaining_min = rate_limit_status['remaining_seconds'] // 60
                    rate_limit_indicator = f" 🚫{remaining_min}m"
                
                heartbeat_status = f"{heartbeat_icon} {time_since}{rate_limit_indicator}"
            else:
                heartbeat_status = "❌ No heartbeat"
            
            print(f"{proc['description']:<40} {status:<15} {pid:<8} {runtime_str:<15} {last_seen:<20} {heartbeat_status:<25}")
        
        # Show additional heartbeat processes that aren't in monitored_processes
        monitored_heartbeat_names = {proc.get('heartbeat_name', key) for key, proc in self.monitored_processes.items()}
        additional_processes = {name: status for name, status in heartbeat_statuses.items() 
                              if name not in monitored_heartbeat_names}
        
        if additional_processes:
            print("-"*120)
            print("ADDITIONAL HEARTBEAT PROCESSES:")
            print("-"*120)
            for name, status in additional_processes.items():
                is_alive = status.get('is_alive', False)
                time_since = status.get('time_since_formatted', 'unknown')
                heartbeat_icon = "💚" if is_alive else "💔"
                pid = status.get('pid', '-')
                
                # Add rate limit indicator for additional processes too
                rate_limit_indicator = ""
                if rate_limit_status['is_rate_limited']:
                    remaining_min = rate_limit_status['remaining_seconds'] // 60
                    rate_limit_indicator = f" 🚫{remaining_min}m"
                
                heartbeat_status = f"{heartbeat_icon} {time_since}{rate_limit_indicator}"
                
                print(f"{'🔍 ' + name:<40} {'HEARTBEAT':<15} {pid:<8} {'-':<15} {'-':<20} {heartbeat_status:<25}")
        
        print("="*120)
        print("Legende: 💚 = Aktiv | 💔 = Inaktiv | ❌ = Kein Heartbeat | 🚫 = Rate Limit (verbleibende Minuten)")

    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        signal_name = signal.Signals(signum).name
        self.log_message(f"Received {signal_name} signal - shutting down gracefully...")
        self.running = False

    def monitor_loop(self, check_interval=5, status_interval=30):
        """Main monitoring loop"""
        self.log_message("🚀 Process Monitor started")
        self.log_message(f"📋 Monitoring: {', '.join([proc['description'] for proc in self.monitored_processes.values()])}")
        self.log_message(f"⏱️  Check interval: {check_interval}s | Status display: {status_interval}s")
        
        last_status_display = 0
        
        try:
            while self.running:
                current_time = time.time()
                
                # Check all processes
                for process_key in self.monitored_processes.keys():
                    self.check_process_status(process_key)
                
                # Display status table periodically
                if current_time - last_status_display >= status_interval:
                    self.print_status_table()
                    last_status_display = current_time
                
                # Sleep until next check
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            self.log_message("👋 Monitor stopped by user")
        except Exception as e:
            self.log_message(f"❌ Monitor error: {e}", 'ERROR')
        
        # Final status
        self.print_status_table()
        
        total_runtime = datetime.now() - self.start_time
        self.log_message(f"✅ Process Monitor stopped (Total runtime: {str(total_runtime).split('.')[0]})")

def main():
    """Main function"""
    print("🔍 Process Monitor - Überwacht laufende Prozesse")
    print("Überwacht: npm run serve, npm run dev, bidder.py, freelancer-websocket-reader.py")
    print("Hinweis: Startet KEINE Prozesse - überwacht nur bereits laufende!")
    print("Drücke Ctrl+C zum Beenden\n")
    
    monitor = ProcessMonitor()
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, monitor.handle_signal)
    signal.signal(signal.SIGTERM, monitor.handle_signal)
    
    # Check command line arguments
    check_interval = 5  # Default check every 5 seconds
    status_interval = 30  # Show status every 30 seconds
    
    if len(sys.argv) > 1:
        try:
            check_interval = int(sys.argv[1])
            if len(sys.argv) > 2:
                status_interval = int(sys.argv[2])
        except ValueError:
            print("❌ Invalid arguments. Usage: python process_monitor.py [check_interval] [status_interval]")
            print("   Default: check_interval=5s, status_interval=30s")
            sys.exit(1)
    
    monitor.monitor_loop(check_interval, status_interval)

if __name__ == "__main__":
    main() 