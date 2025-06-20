#!/usr/bin/env python3
"""
Colored Log Tail für freelancer_requests.log
Zeigt verschiedene Log-Typen in unterschiedlichen Farben an
"""

import os
import sys
import time
import re
from datetime import datetime

# ANSI Color Codes
COLORS = {
    'RESET': '\033[0m',
    'BOLD': '\033[1m',
    
    # Text Colors
    'RED': '\033[91m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'WHITE': '\033[97m',
    'GRAY': '\033[90m',
    
    # Background Colors
    'BG_RED': '\033[101m',
    'BG_GREEN': '\033[102m',
    'BG_YELLOW': '\033[103m',
    'BG_BLUE': '\033[104m',
    'BG_MAGENTA': '\033[105m',
    'BG_CYAN': '\033[106m',
}

def colorize_log_line(line):
    """Färbt eine Log-Zeile basierend auf ihrem Inhalt ein"""
    
    # Original line für pattern matching (ohne Farben)
    orig_line = line.strip()
    
    # VUE-FRONTEND GET_PROJECT_DETAILS (häufigste Kategorie)
    if 'VUE-FRONTEND' in orig_line and 'GET_PROJECT_DETAILS' in orig_line:
        # Blau für Vue Frontend Project Details
        timestamp_match = re.match(r'^([^|]+)', orig_line)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            rest = orig_line[len(timestamp):]
            
            # Projekt-IDs hervorheben
            rest = re.sub(r'(projects\[\]=\d+)', 
                         f'{COLORS["CYAN"]}\\1{COLORS["BLUE"]}', rest)
            
            # Response count hervorheben
            rest = re.sub(r'(projects_count=\d+)', 
                         f'{COLORS["WHITE"]}{COLORS["BOLD"]}\\1{COLORS["BLUE"]}{COLORS["RESET"]}{COLORS["BLUE"]}', rest)
            
            return f'{COLORS["GRAY"]}{timestamp}{COLORS["BLUE"]}{rest}{COLORS["RESET"]}'
    
    # VUE-INTERNAL (GET_JOBS)
    elif 'VUE-INTERNAL' in orig_line and 'GET_JOBS' in orig_line:
        # Grün für interne Vue API Calls
        return f'{COLORS["GREEN"]}{orig_line}{COLORS["RESET"]}'
    
    # GET_ACTIVE_PROJECTS (bidder.py)
    elif 'GET_ACTIVE_PROJECTS' in orig_line:
        # Gelb für Bidder Active Projects
        timestamp_match = re.match(r'^([^|]+)', orig_line)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            rest = orig_line[len(timestamp):]
            
            # Query parameters hervorheben
            rest = re.sub(r'(query=.*?)(\s+\|)', 
                         f'{COLORS["CYAN"]}\\1{COLORS["YELLOW"]}\\2', rest)
            
            # Response counts hervorheben
            rest = re.sub(r'(projects_count=\d+|users_count=\d+)', 
                         f'{COLORS["WHITE"]}{COLORS["BOLD"]}\\1{COLORS["YELLOW"]}{COLORS["RESET"]}{COLORS["YELLOW"]}', rest)
            
            return f'{COLORS["GRAY"]}{timestamp}{COLORS["YELLOW"]}{rest}{COLORS["RESET"]}'
    
    # User API calls
    elif '/users/' in orig_line:
        # Magenta für User API calls
        return f'{COLORS["MAGENTA"]}{orig_line}{COLORS["RESET"]}'
    
    # Reputation API calls
    elif '/reputations/' in orig_line:
        # Cyan für Reputation API calls
        return f'{COLORS["CYAN"]}{orig_line}{COLORS["RESET"]}'
    
    # Error or high status codes
    elif re.search(r'STATUS: [4-5]\d\d', orig_line):
        # Rot für Fehler
        return f'{COLORS["RED"]}{COLORS["BOLD"]}{orig_line}{COLORS["RESET"]}'
    
    # WebSocket Reader Logs
    elif 'WEBSOCKET-READER' in orig_line:
        # Magenta für WebSocket Reader
        return f'{COLORS["MAGENTA"]}{orig_line}{COLORS["RESET"]}'
    
    # Rate Limit Logs
    elif 'RATE_LIMIT' in orig_line:
        # Rot mit gelbem Hintergrund für Rate Limits
        return f'{COLORS["BG_YELLOW"]}{COLORS["RED"]}{COLORS["BOLD"]}{orig_line}{COLORS["RESET"]}'
    
    # Default - keine spezielle Färbung
    else:
        return f'{COLORS["WHITE"]}{orig_line}{COLORS["RESET"]}'

def tail_file(filepath, lines=50):
    """Tail-ähnliche Funktionalität mit Farben"""
    
    if not os.path.exists(filepath):
        print(f"{COLORS['RED']}Error: File {filepath} does not exist{COLORS['RESET']}")
        return
    
    print(f"{COLORS['BOLD']}{COLORS['CYAN']}🎨 Colored Log Tail - {filepath}{COLORS['RESET']}")
    print(f"{COLORS['GRAY']}{'='*80}{COLORS['RESET']}")
    print(f"{COLORS['YELLOW']}Color Legend:{COLORS['RESET']}")
    print(f"  {COLORS['BLUE']}🔵 VUE-FRONTEND GET_PROJECT_DETAILS{COLORS['RESET']}")
    print(f"  {COLORS['GREEN']}🟢 VUE-INTERNAL GET_JOBS{COLORS['RESET']}")
    print(f"  {COLORS['YELLOW']}🟡 GET_ACTIVE_PROJECTS (bidder.py){COLORS['RESET']}")
    print(f"  {COLORS['MAGENTA']}🟣 User/WebSocket API calls{COLORS['RESET']}")
    print(f"  {COLORS['CYAN']}🔵 Reputation API calls{COLORS['RESET']}")
    print(f"  {COLORS['RED']}{COLORS['BOLD']}🔴 Errors (4xx/5xx status){COLORS['RESET']}")
    print(f"  {COLORS['BG_YELLOW']}{COLORS['RED']}{COLORS['BOLD']}⚠️  Rate Limits{COLORS['RESET']}")
    print(f"{COLORS['GRAY']}{'='*80}{COLORS['RESET']}")
    
    try:
        # Zeige die letzten N Zeilen
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            file_lines = f.readlines()
            
        # Zeige die letzten 'lines' Zeilen
        recent_lines = file_lines[-lines:] if len(file_lines) > lines else file_lines
        
        for line in recent_lines:
            if line.strip():  # Skip empty lines
                colored_line = colorize_log_line(line)
                print(colored_line)
        
        print(f"\n{COLORS['CYAN']}📡 Following log file in real-time... (Ctrl+C to exit){COLORS['RESET']}")
        
        # Follow the file (wie tail -f)
        f = open(filepath, 'r', encoding='utf-8', errors='ignore')
        f.seek(0, 2)  # Go to end of file
        
        while True:
            line = f.readline()
            if line:
                if line.strip():  # Skip empty lines
                    colored_line = colorize_log_line(line)
                    print(colored_line)
            else:
                time.sleep(0.1)  # Wait for new content
                
    except KeyboardInterrupt:
        print(f"\n{COLORS['YELLOW']}👋 Log tail stopped by user{COLORS['RESET']}")
    except Exception as e:
        print(f"{COLORS['RED']}Error: {str(e)}{COLORS['RESET']}")
    finally:
        try:
            f.close()
        except:
            pass

def main():
    """Main function"""
    log_file = 'api_logs/freelancer_requests.log'
    
    # Check if file exists
    if not os.path.exists(log_file):
        print(f"{COLORS['RED']}Error: Log file {log_file} not found{COLORS['RESET']}")
        print(f"{COLORS['YELLOW']}Make sure you're in the correct directory and the log file exists{COLORS['RESET']}")
        sys.exit(1)
    
    # Parse command line arguments
    lines = 50  # Default number of lines to show
    if len(sys.argv) > 1:
        try:
            lines = int(sys.argv[1])
        except ValueError:
            print(f"{COLORS['YELLOW']}Invalid number of lines, using default: {lines}{COLORS['RESET']}")
    
    tail_file(log_file, lines)

if __name__ == "__main__":
    main() 