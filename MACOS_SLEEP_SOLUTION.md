# macOS Sleep/Lock Solution für Python Bidder

## Problem
Python-Prozesse werden bei gesperrtem Mac oder nach längerer Inaktivität beendet. Dies liegt an macOS-Energiesparfunktionen und nicht an Cursor IDE.

## Ursachen
1. **macOS App Nap**: Deaktiviert inaktive Prozesse
2. **System Sleep**: Pausiert/beendet Hintergrundprozesse
3. **Memory Pressure**: Beendet Prozesse bei Speichermangel
4. **Process Suspension**: Pausiert Prozesse bei Inaktivität

## Lösung: Robuster Process Manager

### 1. Einfache Lösung: `start_bidder_robust.py`

```bash
# Starte Bidder mit robustem Manager
python start_bidder_robust.py
```

**Features:**
- ☕ **Sleep Prevention**: Verwendet `caffeinate` um System-Sleep zu verhindern
- 🔄 **Auto-Restart**: Startet Bidder automatisch neu bei Crash
- 📊 **Status Monitoring**: Überwacht Prozess-Gesundheit
- 🧹 **Graceful Shutdown**: Sauberes Beenden mit Ctrl+C
- 📝 **Status Logging**: Schreibt Status in `bidder_status.json`

### 2. Erweiterte Lösung: `python_process_manager.py`

```bash
# Starte mit erweitertem Process Manager
python python_process_manager.py bidder
```

**Zusätzliche Features:**
- 🔒 **Lock Detection**: Erkennt System-Sperrung
- 💓 **Heartbeat Monitoring**: Kontinuierliche Prozess-Überwachung
- 📊 **Detailliertes Logging**: Umfangreiches Logging in `python_process_manager.log`
- 🔧 **Konfigurierbar**: Anpassbare Parameter

## Konfiguration

### Sleep Prevention Optionen

```python
# In start_bidder_robust.py
config = {
    'auto_restart': True,      # Automatischer Neustart
    'prevent_sleep': True,     # System-Sleep verhindern
    'max_restarts': 10,        # Maximale Neustarts
    'restart_delay': 30,       # Pause zwischen Neustarts (Sekunden)
    'heartbeat_interval': 60   # Überwachungsintervall (Sekunden)
}
```

### macOS System-Einstellungen

1. **Systemeinstellungen > Energie sparen**:
   - "Computer in den Ruhezustand versetzen" auf "Nie"
   - "Festplatten in den Ruhezustand versetzen" deaktivieren

2. **Terminal/Python App Nap deaktivieren**:
   ```bash
   # Für Terminal
   defaults write com.apple.Terminal NSAppSleepDisabled -bool YES
   
   # Für Python (falls als App installiert)
   defaults write org.python.python NSAppSleepDisabled -bool YES
   ```

3. **Cursor IDE App Nap deaktivieren**:
   - Systemeinstellungen > Batterie > App Nap
   - Cursor deaktivieren

## Verwendung

### Schnellstart
```bash
# Einfacher robuster Start
python start_bidder_robust.py

# Mit erweitertem Manager
python python_process_manager.py bidder
```

### Status prüfen
```bash
# Status-Datei anzeigen
cat bidder_status.json

# Log-Datei anzeigen
tail -f python_process_manager.log
```

### Beenden
```bash
# Graceful shutdown mit Ctrl+C
^C

# Oder Process finden und beenden
ps aux | grep python
kill -TERM <PID>
```

## Troubleshooting

### Problem: Prozess wird trotzdem beendet
**Lösung:**
1. Prüfe ob `caffeinate` läuft: `ps aux | grep caffeinate`
2. Erhöhe `heartbeat_interval` auf 30 Sekunden
3. Aktiviere erweiterten Process Manager

### Problem: Zu viele Neustarts
**Lösung:**
1. Prüfe `bidder_status.json` für Fehlerdetails
2. Erhöhe `restart_delay` auf 60 Sekunden
3. Prüfe Bidder-Logs auf Fehler

### Problem: System wird trotzdem gesperrt
**Lösung:**
1. Verwende zusätzlich: `pmset -g assertions`
2. Manuell caffeinate starten: `caffeinate -d -i -m -s &`
3. Systemeinstellungen für Energie sparen prüfen

## Monitoring

### Status-Datei (`bidder_status.json`)
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "uptime_seconds": 3600,
  "restart_count": 2,
  "bidder_running": true,
  "sleep_prevention_active": true
}
```

### Log-Ausgabe
```
2024-01-15 10:30:00 [INFO] 🚀 MacOS Process Manager initialisiert
2024-01-15 10:30:01 [INFO] ☕ System-Sleep-Prevention aktiviert (caffeinate)
2024-01-15 10:30:02 [INFO] ✅ Prozess gestartet: freelancer-bidder (PID: 12345)
2024-01-15 10:35:00 [INFO] 📊 Status: Uptime 5min, Restarts: 0
```

## Automatischer Start beim Boot

### LaunchAgent erstellen
```bash
# Erstelle LaunchAgent
cat > ~/Library/LaunchAgents/com.freelancer.bidder.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.freelancer.bidder</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/$(whoami)/workspace/freelancer-bidder/start_bidder_robust.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/$(whoami)/workspace/freelancer-bidder</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/$(whoami)/workspace/freelancer-bidder/bidder_launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/$(whoami)/workspace/freelancer-bidder/bidder_launchd_error.log</string>
</dict>
</plist>
EOF

# Aktiviere LaunchAgent
launchctl load ~/Library/LaunchAgents/com.freelancer.bidder.plist
```

## Fazit

Das Problem liegt **nicht an Cursor IDE**, sondern an macOS-Energiesparfunktionen. Die bereitgestellten Lösungen verhindern:

1. ☕ **System-Sleep** durch `caffeinate`
2. 🔄 **Prozess-Crashes** durch Auto-Restart
3. 📊 **Unbemerkte Ausfälle** durch Monitoring
4. 🔒 **Lock-bedingte Beendigung** durch Sleep-Prevention

**Empfehlung**: Verwende `start_bidder_robust.py` für einfache Fälle oder `python_process_manager.py` für erweiterte Überwachung. 