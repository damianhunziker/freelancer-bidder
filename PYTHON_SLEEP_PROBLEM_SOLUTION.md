# Python Sleep Problem - Lösung für macOS

## 🔍 Problem-Analyse

**Das Problem liegt NICHT an Cursor IDE**, sondern an macOS-Energiesparfunktionen:

### Ursachen
1. **macOS App Nap**: Pausiert inaktive Anwendungen automatisch
2. **System Sleep**: Versetzt Computer in Ruhezustand bei Inaktivität
3. **Process Suspension**: Pausiert Hintergrundprozesse bei gesperrtem Bildschirm
4. **Memory Pressure**: Beendet Prozesse bei Speichermangel
5. **Thermal Management**: Drosselt/beendet Prozesse bei Überhitzung

### Symptome
- ✅ Python-Script läuft normal wenn Mac entsperrt ist
- ❌ Python-Script bricht ab nach längerer Mac-Sperrung
- ❌ Prozess wird ohne Fehlermeldung beendet
- ❌ Keine Logs über Prozess-Beendigung

## 🛠️ Lösungen

### 1. Schnelle Lösung: Shell-Script
```bash
# Einfacher Start mit Sleep-Prevention
./start_bidder.sh
```

**Features:**
- ☕ Automatische Sleep-Prevention mit `caffeinate`
- 🔄 Auto-Restart bei Prozess-Crash
- 📊 Status-Monitoring
- 🧹 Graceful Shutdown mit Ctrl+C

### 2. Robuste Lösung: Python Process Manager
```bash
# Erweiterte Überwachung und Management
python start_bidder_robust.py
```

**Features:**
- 🔒 Erweiterte Sleep-Prevention
- 📊 Detailliertes Status-Logging
- 🔄 Intelligenter Auto-Restart
- 📝 JSON-Status-Export
- ⚙️ Konfigurierbare Parameter

### 3. Professionelle Lösung: Process Manager
```bash
# Vollständiger Process Manager
python python_process_manager.py bidder
```

**Features:**
- 🔒 System-Lock-Erkennung
- 💓 Heartbeat-Monitoring
- 📊 Umfangreiches Logging
- 🔧 Multi-Process-Management
- 📈 Performance-Monitoring

## 🚀 Schnellstart

### Sofort verwendbar:
```bash
# 1. Shell-Script ausführbar machen
chmod +x start_bidder.sh

# 2. Bidder mit Sleep-Prevention starten
./start_bidder.sh

# 3. Mit Ctrl+C beenden
```

### Erweiterte Nutzung:
```bash
# Python-Manager verwenden
python start_bidder_robust.py

# Status prüfen
cat bidder_status.json

# Test der Sleep-Prevention
python test_sleep_prevention.py
```

## ⚙️ Konfiguration

### macOS System-Einstellungen optimieren:

1. **Systemeinstellungen > Batterie/Energie**:
   ```
   - "Computer in Ruhezustand" → "Nie"
   - "Festplatten in Ruhezustand" → Deaktiviert
   - "Wake for network access" → Aktiviert
   ```

2. **App Nap für relevante Apps deaktivieren**:
   ```bash
   # Terminal
   defaults write com.apple.Terminal NSAppSleepDisabled -bool YES
   
   # Cursor IDE
   defaults write com.todesktop.230313mzl4w4u92 NSAppSleepDisabled -bool YES
   
   # Python
   defaults write org.python.python NSAppSleepDisabled -bool YES
   ```

3. **Manuell caffeinate testen**:
   ```bash
   # Sleep-Prevention manuell starten
   caffeinate -d -i -m -s &
   
   # Status prüfen
   pmset -g assertions | grep caffeinate
   
   # Beenden
   killall caffeinate
   ```

## 📊 Monitoring & Debugging

### Status prüfen:
```bash
# Aktive Python-Prozesse
ps aux | grep python

# Sleep-Prevention Status
pmset -g assertions

# System Idle-Zeit
ioreg -n IOHIDSystem -d1 | grep HIDIdleTime

# Bidder Status (JSON)
cat bidder_status.json | jq .
```

### Log-Dateien:
```bash
# Robuster Starter
tail -f python_process_manager.log

# Shell-Script Logs
tail -f bidder_launchd.log

# System Logs
log show --predicate 'process == "caffeinate"' --last 1h
```

## 🔧 Troubleshooting

### Problem: Prozess wird trotzdem beendet
**Diagnose:**
```bash
# Prüfe ob caffeinate läuft
ps aux | grep caffeinate

# Prüfe System-Assertions
pmset -g assertions | grep -i prevent

# Prüfe Speicher-Druck
memory_pressure
```

**Lösung:**
1. Verwende `start_bidder_robust.py` statt direkten Start
2. Erhöhe `heartbeat_interval` auf 30 Sekunden
3. Aktiviere erweiterten Process Manager

### Problem: Zu viele Restarts
**Diagnose:**
```bash
# Status-Datei prüfen
cat bidder_status.json

# Letzte Fehler anzeigen
tail -50 python_process_manager.log | grep ERROR
```

**Lösung:**
1. Erhöhe `restart_delay` auf 60 Sekunden
2. Reduziere `max_restarts` auf 5
3. Prüfe bidder.py auf Fehler

### Problem: caffeinate funktioniert nicht
**Diagnose:**
```bash
# Manuell testen
caffeinate -d -i -m -s sleep 300 &

# Assertions prüfen
pmset -g assertions

# System-Einstellungen prüfen
pmset -g
```

**Lösung:**
1. Systemeinstellungen für Energie sparen anpassen
2. Administrator-Rechte prüfen
3. Alternative: `pmset prevent sleep` verwenden

## 📈 Performance-Optimierung

### Ressourcen-schonende Konfiguration:
```python
# In start_bidder_robust.py
config = {
    'heartbeat_interval': 120,    # Weniger häufige Checks
    'restart_delay': 60,          # Längere Pause zwischen Restarts
    'prevent_sleep': True,        # Sleep-Prevention aktiv lassen
    'max_restarts': 5             # Begrenzte Restart-Versuche
}
```

### Speicher-optimiert:
```bash
# Bidder mit reduziertem Speicher-Footprint
export PYTHONOPTIMIZE=1
python start_bidder_robust.py
```

## 🎯 Empfehlungen

### Für normale Nutzung:
```bash
# Einfach und zuverlässig
./start_bidder.sh
```

### Für Entwicklung/Debugging:
```bash
# Mit detailliertem Logging
python start_bidder_robust.py
```

### Für Produktions-Umgebung:
```bash
# Mit vollständigem Monitoring
python python_process_manager.py bidder
```

### Für automatischen Start:
```bash
# LaunchAgent für Boot-Start
launchctl load ~/Library/LaunchAgents/com.freelancer.bidder.plist
```

## ✅ Fazit

**Das Problem liegt definitiv NICHT an Cursor IDE**, sondern an macOS-Energiesparfunktionen. Die bereitgestellten Lösungen adressieren alle bekannten Ursachen:

1. ☕ **Sleep-Prevention** verhindert System-Ruhezustand
2. 🔄 **Auto-Restart** kompensiert unerwartete Beendigungen  
3. 📊 **Monitoring** erkennt Probleme frühzeitig
4. 🔧 **Konfiguration** optimiert System-Verhalten

**Empfehlung**: Starte mit `./start_bidder.sh` für sofortige Lösung, verwende `start_bidder_robust.py` für erweiterte Features. 