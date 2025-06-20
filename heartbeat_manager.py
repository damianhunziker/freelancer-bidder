#!/usr/bin/env python3
"""
Heartbeat Manager - Manages heartbeat signals from various processes
Used by freelancer-websocket-reader.py, bidder.py, vue-frontend, etc.
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, Optional

class HeartbeatManager:
    def __init__(self, heartbeat_file='heartbeat_status.json'):
        self.heartbeat_file = heartbeat_file
        self.ensure_heartbeat_file_exists()
    
    def ensure_heartbeat_file_exists(self):
        """Ensure the heartbeat file exists with proper structure"""
        if not os.path.exists(self.heartbeat_file):
            initial_data = {
                'last_updated': time.time(),
                'processes': {}
            }
            try:
                with open(self.heartbeat_file, 'w') as f:
                    json.dump(initial_data, f, indent=2)
            except Exception as e:
                print(f"Error creating heartbeat file: {e}")
    
    def send_heartbeat(self, process_name: str, additional_data: Optional[Dict] = None):
        """Send a heartbeat signal from a process"""
        try:
            # Read current data
            data = self.read_heartbeat_data()
            
            # Update process heartbeat
            process_data = {
                'last_heartbeat': time.time(),
                'last_heartbeat_formatted': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'pid': os.getpid(),
                'status': 'alive'
            }
            
            # Add any additional data
            if additional_data:
                process_data.update(additional_data)
            
            data['processes'][process_name] = process_data
            data['last_updated'] = time.time()
            
            # Write back to file
            with open(self.heartbeat_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error sending heartbeat for {process_name}: {e}")
    
    def read_heartbeat_data(self) -> Dict:
        """Read current heartbeat data"""
        try:
            if os.path.exists(self.heartbeat_file):
                with open(self.heartbeat_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading heartbeat data: {e}")
        
        # Return default structure if file doesn't exist or is corrupted
        return {
            'last_updated': time.time(),
            'processes': {}
        }
    
    def get_process_status(self, process_name: str) -> Optional[Dict]:
        """Get heartbeat status for a specific process"""
        data = self.read_heartbeat_data()
        return data.get('processes', {}).get(process_name)
    
    def get_time_since_last_heartbeat(self, process_name: str) -> Optional[float]:
        """Get time in seconds since last heartbeat for a process"""
        process_data = self.get_process_status(process_name)
        if process_data and 'last_heartbeat' in process_data:
            return time.time() - process_data['last_heartbeat']
        return None
    
    def is_process_alive(self, process_name: str, timeout_seconds: int = 60) -> bool:
        """Check if a process is considered alive based on heartbeat timeout"""
        time_since = self.get_time_since_last_heartbeat(process_name)
        if time_since is None:
            return False
        return time_since < timeout_seconds
    
    def get_all_processes_status(self) -> Dict:
        """Get status of all processes with heartbeat information"""
        data = self.read_heartbeat_data()
        current_time = time.time()
        
        result = {}
        for process_name, process_data in data.get('processes', {}).items():
            last_heartbeat = process_data.get('last_heartbeat', 0)
            time_since = current_time - last_heartbeat
            
            result[process_name] = {
                **process_data,
                'time_since_heartbeat': time_since,
                'time_since_formatted': self.format_duration(time_since),
                'is_alive': time_since < 60  # 60 second timeout
            }
        
        return result
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in a human-readable way"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def cleanup_old_processes(self, max_age_hours: int = 24):
        """Remove heartbeat data for processes that haven't sent heartbeats in a long time"""
        try:
            data = self.read_heartbeat_data()
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            processes_to_remove = []
            for process_name, process_data in data.get('processes', {}).items():
                last_heartbeat = process_data.get('last_heartbeat', 0)
                if current_time - last_heartbeat > max_age_seconds:
                    processes_to_remove.append(process_name)
            
            for process_name in processes_to_remove:
                del data['processes'][process_name]
            
            if processes_to_remove:
                data['last_updated'] = current_time
                with open(self.heartbeat_file, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"Cleaned up old heartbeat data for: {', '.join(processes_to_remove)}")
                
        except Exception as e:
            print(f"Error cleaning up old processes: {e}")

# Global instance for easy access
heartbeat_manager = HeartbeatManager()

def send_heartbeat(process_name: str, additional_data: Optional[Dict] = None):
    """Convenience function to send heartbeat"""
    heartbeat_manager.send_heartbeat(process_name, additional_data)

def get_heartbeat_status(process_name: str) -> Optional[Dict]:
    """Convenience function to get heartbeat status"""
    return heartbeat_manager.get_process_status(process_name)

def is_process_alive(process_name: str, timeout_seconds: int = 60) -> bool:
    """Convenience function to check if process is alive"""
    return heartbeat_manager.is_process_alive(process_name, timeout_seconds) 