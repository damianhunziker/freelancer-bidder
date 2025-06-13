#!/usr/bin/env python3
"""
Freelancer.com WebSocket-Listener Starter

Dieses Script startet den WebSocket-Listener aus dem fl_websocket/ Ordner.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    websocket_dir = script_dir / "fl_websocket"
    
    # Check if the websocket directory exists
    if not websocket_dir.exists():
        print("❌ Der fl_websocket/ Ordner wurde nicht gefunden!")
        print("💡 Stelle sicher, dass der Ordner im gleichen Verzeichnis wie dieses Script liegt.")
        sys.exit(1)
    
    # Check if the main script exists
    main_script = websocket_dir / "websocket_listener.py"
    simple_script = websocket_dir / "websocket_simple.py"
    
    if not main_script.exists() and not simple_script.exists():
        print("❌ Keine WebSocket-Scripts gefunden!")
        print("💡 Stelle sicher, dass websocket_listener.py oder websocket_simple.py im fl_websocket/ Ordner liegt.")
        sys.exit(1)
    
    print("🚀 Freelancer.com WebSocket-Listener Starter")
    print("=" * 50)
    
    # Show available scripts
    available_scripts = []
    if main_script.exists():
        available_scripts.append(("1", "websocket_listener.py", "Asynchrone Version (empfohlen)"))
    if simple_script.exists():
        available_scripts.append(("2", "websocket_simple.py", "Synchrone Version (Alternative)"))
    
    if len(available_scripts) == 0:
        print("❌ Keine WebSocket-Scripts gefunden!")
        sys.exit(1)
    
    print("Verfügbare Scripts:")
    for num, script, desc in available_scripts:
        print(f"{num}. {script} - {desc}")
    
    # Let user choose or default to first option
    if len(available_scripts) == 1:
        choice = "1"
        print(f"\nStarte automatisch: {available_scripts[0][1]}")
    else:
        choice = input(f"\nWähle ein Script (1-{len(available_scripts)}) oder Enter für Standard: ").strip()
        if not choice:
            choice = "1"
    
    # Find the selected script
    selected_script = None
    for num, script, desc in available_scripts:
        if choice == num:
            selected_script = websocket_dir / script
            break
    
    if selected_script is None:
        print("❌ Ungültige Auswahl!")
        sys.exit(1)
    
    print(f"▶️  Starte: {selected_script.name}")
    print("💡 Drücke Ctrl+C zum Beenden")
    print("=" * 50)
    
    try:
        # Change to the websocket directory and run the script
        os.chdir(websocket_dir)
        subprocess.run([sys.executable, selected_script.name])
    except KeyboardInterrupt:
        print("\n🛑 WebSocket-Listener wurde beendet")
    except Exception as e:
        print(f"❌ Fehler beim Starten des Scripts: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 