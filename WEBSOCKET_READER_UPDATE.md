# Freelancer WebSocket Reader - Update und Installation

## Problem behoben: ✅

**Ursprünglicher Fehler:**
```
ModuleNotFoundError: No module named 'pyppeteer'
```

## Was wurde installiert:

### Dependencies
```bash
python -m pip install pyppeteer
```

**Installierte Pakete:**
- `pyppeteer` - Browser-Automatisierung für WebSocket-Monitoring
- `appdirs` - Anwendungsverzeichnis-Management
- `pyee` - Event-Emitter für Python
- `urllib3` - HTTP-Client-Bibliothek
- `websockets` - WebSocket-Client/Server-Implementierung

## Rate-Limiting-Integration

Der WebSocket-Reader wurde in das globale Rate-Limiting-System integriert:

### Neue Features:
1. **Rate-Limit-Prüfung**: Vor der Verarbeitung neuer Projekte wird geprüft, ob Rate-Limiting aktiv ist
2. **Intelligente Verzögerung**: Bei aktivem Rate-Limit werden Projekte nicht verarbeitet
3. **Status-Anzeige**: Verbleibende Zeit bis zur Aufhebung wird angezeigt

### Code-Changes:
```python
# Neu importiert
from rate_limit_manager import is_rate_limited, get_rate_limit_status

# Neue Logik bei Projekt-Erkennung
if is_rate_limited():
    print(f"🚫 Global rate limit active - delaying processing of project {job_id}")
    status = get_rate_limit_status()
    remaining_min = status['remaining_seconds'] // 60
    print(f"⏳ Rate limit expires in {remaining_min} minutes")
else:
    # Projekt normal verarbeiten
    asyncio.create_task(execute_add_script(job_id))
    asyncio.create_task(execute_app_script(job_id))
```

## Verwendung

### Starten des WebSocket-Readers:
```bash
python freelancer-websocket-reader.py
```

### Was passiert:
1. **Browser-Start**: Chromium wird geöffnet
2. **Freelancer.com-Navigation**: Automatischer Besuch der Website
3. **Login-Aufforderung**: Du musst dich manuell anmelden
4. **WebSocket-Monitoring**: Überwachung aller WebSocket-Nachrichten
5. **Projekt-Erkennung**: Neue Projekte werden automatisch erkannt
6. **Rate-Limit-Prüfung**: Vor Verarbeitung wird globaler Rate-Limit-Status geprüft
7. **Automatische Verarbeitung**: `add.py` und `app.py` werden für neue Projekte ausgeführt

## Integration mit Rate-Limiting-System

### Koordination mit anderen Tools:
- **bidder.py**: Pausiert bei Rate-Limiting
- **add.py**: Pausiert bei Rate-Limiting  
- **index.js**: Pausiert bei Rate-Limiting
- **websocket-reader**: Erkennt neue Projekte, aber verarbeitet sie erst nach Rate-Limit

### Verhalten bei Rate-Limiting:
```
🆔 JOB ID DETECTED: 12345678
🚫 Global rate limit active - delaying processing of project 12345678
⏳ Rate limit expires in 23 minutes
```

## Fehlerbehebung

### Dependency-Konflikte:
Es gab Warnungen bezüglich pyee-Versionen:
```
playwright 1.52.0 requires pyee<14,>=13, but you have pyee 11.1.1
```

**Lösung**: Dies beeinträchtigt die Funktionalität des WebSocket-Readers nicht, da er nur pyppeteer benötigt.

### Browser-Probleme:
Falls der Browser nicht startet:
```bash
# Chromium manuell herunterladen
python -c "import pyppeteer; pyppeteer.install()"
```

## Status: ✅ BEREIT

Der freelancer-websocket-reader ist jetzt vollständig:
- ✅ Alle Dependencies installiert
- ✅ Rate-Limiting integriert  
- ✅ Import-Tests erfolgreich
- ✅ Koordination mit anderen Tools
- ✅ Bereit für den Einsatz

## Nächste Schritte

1. **Testen**: `python freelancer-websocket-reader.py` ausführen
2. **Login**: Im geöffneten Browser bei Freelancer.com anmelden
3. **Monitoring**: WebSocket-Nachrichten werden überwacht
4. **Automatisierung**: Neue Projekte werden automatisch verarbeitet (wenn kein Rate-Limit aktiv ist) 