# Rate Limit Logging System

Das Rate Limit Logging System überwacht und dokumentiert alle Rate Limiting Aktivitäten zwischen den verschiedenen Freelancer API Clients (Python und Node.js).

## Überblick

### Zweck
- **Transparenz**: Vollständige Nachverfolgung aller Rate Limit Ereignisse
- **Debugging**: Identifikation von Rate Limit Patterns und Ursachen
- **Optimierung**: Analyse der Rate Limit Häufigkeit zur Verbesserung der API-Nutzung
- **Koordination**: Synchrone Rate Limit Verwaltung zwischen mehreren Prozessen

### Log-Struktur
Alle Rate Limit Logs werden in `api_logs/rate_limit.log` gespeichert mit folgendem Format:
```
2024-01-20 14:30:15 | RATE_LIMIT | ACTIVATED | context=bidder-get-active-projects | timeout_until=2024-01-20 15:00:15 | timeout_duration_minutes=30
```

## Ereignistypen

### ACTIVATED
Rate Limit wurde aktiviert (429 Fehler erkannt)
- **Details**: timeout_until, timeout_duration_minutes, timeout_timestamp
- **Context**: Welcher API Call das Rate Limit ausgelöst hat

### STILL_ACTIVE
Rate Limit ist noch aktiv (wird alle 60 Sekunden geloggt)
- **Details**: remaining_minutes, remaining_seconds, timeout_until
- **Context**: Welcher Prozess das Rate Limit geprüft hat

### CLEARED
Rate Limit wurde automatisch aufgehoben (Timeout abgelaufen)
- **Details**: was_timeout_until, cleared_at
- **Context**: Welcher Prozess das Clearing erkannt hat

### READ_ERROR
Fehler beim Lesen der Rate Limit Datei
- **Details**: error (Fehlermeldung)

### ACTIVATION_ERROR
Fehler beim Setzen des Rate Limits
- **Details**: error (Fehlermeldung)
- **Context**: Ursprünglicher Kontext

### CLEAR_ERROR
Fehler beim Löschen der Rate Limit Datei
- **Details**: error (Fehlermeldung)
- **Context**: Ursprünglicher Kontext

## Context Werte

### Python (bidder.py)
- `bidder-get-active-projects`: Rate Limit beim Laden aktiver Projekte
- `bidder-get-user-reputation`: Rate Limit beim Laden von User-Reputationen

### Node.js (vue-frontend)
- `vue-frontend-bid-submission`: Rate Limit bei automatischen Bid-Einreichungen
- `vue-frontend-project-check`: Rate Limit bei Projekt-Validierungen
- `vue-frontend-user-lookup`: Rate Limit bei User-Lookups

### WebSocket Reader
- `websocket-reader-project-validation`: Rate Limit bei Projekt-Validierungen

## Implementierung

### Python (rate_limit_manager.py)
```python
from rate_limit_manager import is_rate_limited, set_rate_limit_timeout

# Vor API Call prüfen
if is_rate_limited("my-context"):
    print("Rate limit aktiv - überspringe API Call")
    return fallback_data

# Bei 429 Fehler
if response.status_code == 429:
    set_rate_limit_timeout("my-context")
    return fallback_data
```

### Node.js (rateLimitManager.js)
```javascript
const { shouldProceedWithApiCall, handleRateLimitResponse } = require('./rateLimitManager');

// Vor API Call prüfen
if (!shouldProceedWithApiCall('my-context')) {
    console.log('Rate limit aktiv - überspringe API Call');
    return fallbackData;
}

// Bei 429 Fehler
if (response.status === 429) {
    handleRateLimitResponse('my-context');
    return fallbackData;
}
```

## Log-Analyse

### Verfügbare Funktionen

#### Python
```python
from rate_limit_manager import get_rate_limit_logs, analyze_rate_limit_patterns

# Letzte 50 Log-Einträge
recent_logs = get_rate_limit_logs(50)

# Pattern-Analyse
patterns = analyze_rate_limit_patterns()
print(f"Aktivierungen: {patterns['activations']}")
print(f"Kontexte: {patterns['contexts']}")
```

#### Node.js
```javascript
const { getRateLimitLogs, analyzeRateLimitPatterns } = require('./rateLimitManager');

// Letzte 50 Log-Einträge
const recentLogs = getRateLimitLogs(50);

// Pattern-Analyse
const patterns = analyzeRateLimitPatterns();
console.log(`Aktivierungen: ${patterns.activations}`);
console.log(`Kontexte:`, patterns.contexts);
```

## Monitoring

### Heartbeat Integration
Das Rate Limit Logging ist in das Heartbeat System integriert:

```python
send_heartbeat('process-name', {
    'rate_limit_status': 'active' if is_rate_limited() else 'clear',
    'rate_limit_remaining': get_rate_limit_status()['remaining_seconds']
})
```

### Log-Rotation
- Logs werden automatisch im `api_logs/` Verzeichnis erstellt
- Keine automatische Rotation - bei Bedarf manuell verwalten
- Empfehlung: Logs älter als 30 Tage regelmäßig archivieren

## Beispiel-Logs

```
2024-01-20 14:30:15 | RATE_LIMIT | ACTIVATED | context=bidder-get-active-projects | timeout_until=2024-01-20 15:00:15 | timeout_duration_minutes=30 | timeout_timestamp=1705752015
2024-01-20 14:31:20 | RATE_LIMIT | STILL_ACTIVE | context=vue-frontend-bid-submission | remaining_minutes=28 | remaining_seconds=55 | timeout_until=2024-01-20 15:00:15
2024-01-20 15:00:15 | RATE_LIMIT | CLEARED | context=bidder-get-active-projects | was_timeout_until=2024-01-20 15:00:15 | cleared_at=2024-01-20 15:00:15
```

## Troubleshooting

### Häufige Probleme

1. **Logs werden nicht erstellt**
   - Prüfe Schreibrechte für `api_logs/` Verzeichnis
   - Verzeichnis wird automatisch erstellt wenn nicht vorhanden

2. **Rate Limit wird nicht erkannt**
   - Prüfe ob `.rate_limit_timestamp` Datei existiert
   - Vergleiche Timestamps zwischen Prozessen

3. **Logs werden doppelt erstellt**
   - Normal - jeder Prozess loggt seine eigenen Ereignisse
   - Context unterscheidet zwischen Prozessen

### Debug-Modus
Führe die Rate Limit Manager direkt aus zum Testen:

```bash
# Python
python rate_limit_manager.py

# Node.js
node vue-frontend/server/rateLimitManager.js
```

## Integration in bestehende Systeme

### Process Monitor
Der Process Monitor zeigt Rate Limit Status in der HEARTBEAT Spalte an:
- 💚 = Kein Rate Limit aktiv
- 💔 = Rate Limit aktiv

### Vue Frontend
Rate Limit Status wird in der Auto-Bidding Log API angezeigt:
- GET `/api/auto-bidding-logs` zeigt Rate Limit Events

### API Logs
Rate Limit Ereignisse werden auch in `api_logs/freelancer_requests.log` geloggt für API-spezifische Analyse.

## Konfiguration

### Timeout-Dauer
Standard: 30 Minuten
Anpassbar in den Konstanten:
- Python: `rate_limit_manager.py` Zeile 26
- Node.js: `rateLimitManager.js` Zeile 66

### Log-Level
Standard: Alle Ereignisse werden geloggt
Reduktion möglich durch Anpassung der Funktionen:
- Häufige STILL_ACTIVE Logs auf weniger als alle 60 Sekunden
- Entfernen von Debug-Ausgaben in Konsole 