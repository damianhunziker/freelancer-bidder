# Project Evaluation Logging System

## Übersicht

Das Project Evaluation Logging System in `bidder.py` protokolliert **alle** überprüften Projekte mit ihrem Status und Ablehnungsgrund in strukturierten JSON-Dateien im `api_logs/` Ordner.

## Funktionalität

### Automatisches Logging
- **Alle gecheckte Projekte** werden automatisch geloggt
- **Status und Grund** für jede Entscheidung wird erfasst
- **Tägliche JSON-Dateien** mit Datum im Dateinamen
- **Strukturierte Daten** für einfache Analyse

### Log-Datei Format
```
api_logs/project_evaluations_YYYYMMDD.json
```

Beispiel: `api_logs/project_evaluations_20250619.json`

## JSON-Struktur

Jeder Log-Eintrag enthält:

```json
{
  "timestamp": "2025-06-19T10:30:45.123456",
  "project_id": "123456789",
  "project_title": "Build a React Dashboard",
  "status": "rejected",
  "reason": "Too many bids (45 >= 40)",
  "additional_data": {
    "bid_count": 45,
    "project_type": "fixed",
    "currency": "USD",
    "rejection_stage": "basic_eligibility"
  }
}
```

## Status-Werte

### ✅ Accepted
- `"accepted"` - Projekt wurde angenommen und gespeichert

### ❌ Rejected
- `"rejected"` - Projekt wurde aus verschiedenen Gründen abgelehnt

### ⚠️ Error
- `"error"` - Fehler bei der Projektverarbeitung

## Rejection Stages (Ablehnungsphasen)

### 1. `basic_eligibility`
- PF-only Projekte
- Bereits verarbeitete Projekte
- Zu viele Gebote

### 2. `high_paying_criteria`
- Budget zu niedrig
- Stundensatz zu niedrig

### 3. `country_criteria`
- Land nicht in Zielliste
- Nicht deutschsprachiges Land (bei German-only)

### 4. `reputation_fetch`
- Reputation konnte nicht abgerufen werden

### 5. `language_criteria`
- Sprache nicht unterstützt (nur en, de, fr erlaubt)

### 6. `ai_evaluation_error`
- KI-Bewertung fehlgeschlagen

### 7. `ai_evaluation_criteria`
- KI-Bewertung negativ (meets_criteria = false)

### 8. `score_threshold`
- KI-Score unter Schwellenwert

### 9. `accepted_and_saved`
- Projekt angenommen und gespeichert

## Zusätzliche Daten

Die `additional_data` enthalten je nach Ablehnungsphase:

- **bid_count**: Anzahl der Gebote
- **project_type**: "fixed" oder "hourly"
- **currency**: Währungscode (USD, EUR, etc.)
- **country**: Land des Arbeitgebers
- **language**: Projektsprache
- **budget**: Budget-Information
- **hourly_rate**: Stundensatz
- **ai_score**: KI-Bewertungsscore
- **score_threshold**: Schwellenwert für Annahme
- **owner_id**: Arbeitgeber-ID
- **rejection_stage**: Spezifische Ablehnungsphase

## Automatische Funktionen

### Datei-Management
- **Tägliche Rotation**: Neue Datei pro Tag
- **Automatische Verzeichniserstellung**: `api_logs/` wird erstellt falls nicht vorhanden
- **UTF-8 Encoding**: Unterstützt Umlaute und Sonderzeichen
- **JSON-Format**: Strukturiert und maschinenlesbar

### Fehlerbehandlung
- **Graceful Degradation**: Logging-Fehler stoppen nicht die Hauptfunktion
- **Konsolen-Feedback**: Bestätigung bei erfolgreichem Logging
- **Robuste JSON-Verarbeitung**: Behandelt beschädigte/fehlende Dateien

## Nutzung für Analyse

### Mit Python
```python
import json
from datetime import datetime

# Lade heutige Logs
today = datetime.now().strftime('%Y%m%d')
with open(f'api_logs/project_evaluations_{today}.json', 'r', encoding='utf-8') as f:
    logs = json.load(f)

# Analysiere Ablehnungsgründe
rejection_reasons = {}
for log in logs:
    if log['status'] == 'rejected':
        reason = log['reason']
        rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

print("Top Ablehnungsgründe:")
for reason, count in sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True):
    print(f"{count}: {reason}")
```

### Mit jq (Command Line)
```bash
# Alle akzeptierten Projekte heute
jq '.[] | select(.status == "accepted")' api_logs/project_evaluations_$(date +%Y%m%d).json

# Ablehnungsgründe zählen
jq -r '.[] | select(.status == "rejected") | .reason' api_logs/project_evaluations_$(date +%Y%m%d).json | sort | uniq -c | sort -nr

# Projekte nach Score
jq '.[] | select(.additional_data.ai_score) | {title: .project_title, score: .additional_data.ai_score}' api_logs/project_evaluations_$(date +%Y%m%d).json
```

## Vorteile

1. **Vollständige Transparenz**: Jedes gecheckte Projekt wird dokumentiert
2. **Detaillierte Gründe**: Exakte Ablehnungsgründe für Optimierung
3. **Strukturierte Daten**: Einfache maschinelle Auswertung
4. **Historische Daten**: Trends über Zeit erkennbar
5. **Debugging-Hilfe**: Nachvollziehbare Entscheidungslogik
6. **Performance-Analyse**: Identifikation von Bottlenecks

## Integration

Das Logging ist vollständig in `bidder.py` integriert und läuft automatisch bei jeder Projektüberprüfung. Keine manuelle Konfiguration erforderlich. 