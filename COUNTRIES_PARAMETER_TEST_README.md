# Countries Parameter Test für Freelancer Active Projects API

## Übersicht

Diese Testdatei testet das `countries[]` Parameter der Freelancer Active Projects API, um zu verstehen, wie die Länder-Filterung funktioniert.

## API Dokumentation

```
GET /projects/0.1/projects/active/
```

**Parameter:**
- `countries[]`: array[string] (optional) 
- Beispiel: `au`, `us`
- Beschreibung: Gibt Projekte zurück, die mindestens einen der angegebenen Ländercodes haben
- `location_details`: boolean (optional)
- Beschreibung: Aktiviert detaillierte Standortinformationen für bessere Länder-Analyse

## Test-Szenarien

Die Testdatei `test_countries_parameter.js` testet folgende Szenarien:

### 1. Basis-Tests
- **Kein Filter**: Baseline ohne Länder-Filterung
- **Einzelne Länder**: au, us, de, gb

### 2. Mehrländer-Tests
- **Englischsprachige Länder**: au, us, gb, ca
- **DACH-Region**: de, at, ch  
- **Europa**: de, fr, it, es, nl, gb

### 3. Edge Cases
- **Ungültiger Ländercode**: xx
- **Gemischt gültig/ungültig**: us, xx, de

## Verwendung

### Voraussetzungen
1. Node.js installiert
2. `config.py` mit gültigem `FREELANCER_API_KEY`

### Test ausführen
```bash
node test_countries_parameter.js
```

### Ausgabe
Der Test zeigt für jeden Fall:
- ✅/❌ Erfolg/Fehler
- 📊 Anzahl gefundener Projekte
- 🌍 Gefundene Länder in den Ergebnissen
- 📋 Beispiel-Projekte (erste 5) mit detaillierten Standortinformationen
- ⏱️ Response-Zeit

### Erweiterte Standortdaten
Mit `location_details=true` werden zusätzliche Informationen abgerufen:
- **Stadt**: Spezifische Stadt des Projekt-Eigentümers
- **Region/Bundesland**: Administrative Einheit (z.B. Bayern, Kalifornien)
- **Vollständige Adresse**: Formatiert als "Stadt, Region, Land"

### Ergebnis-Datei
Detaillierte Ergebnisse werden in einer JSON-Datei gespeichert:
`countries_parameter_test_YYYY-MM-DDTHH-MM-SS-sssZ.json`

## Erwartete Ergebnisse

### Hypothesen
1. **Effektive Filterung**: Nur Projekte aus angegebenen Ländern werden zurückgegeben
2. **OR-Logik**: Bei mehreren Ländern werden Projekte aus ALLEN angegebenen Ländern zurückgegeben
3. **Ungültige Codes**: Werden ignoriert oder führen zu leeren Ergebnissen
4. **Performance**: Filterung sollte Response-Zeit nicht signifikant erhöhen

### Validierung
- Vergleich der gefundenen Länder mit den angeforderten
- Analyse der Projekt-Verteilung nach Ländern
- Performance-Vergleich mit/ohne Filter

## Rate Limiting

Der Test implementiert automatisches Rate Limiting:
- 3 Sekunden Pause zwischen Requests
- Respektiert Freelancer API Limits

## Beispiel-Output

```
🌍 Testing countries[] parameter for Freelancer Active Projects API

🔍 Testing: Single country: Germany
📝 Description: Test filtering for German projects only
🔗 Request URL: https://www.freelancer.com/api/projects/0.1/projects/active/?...&countries[]=de
✅ Success: Found 15 projects
🌍 Countries in results: de
📋 Sample projects:
   1. Website Development for German Company (Berlin, Berlin, Germany) - ID: 12345
   2. Mobile App Translation to German (Munich, Bavaria, Germany) - ID: 12346
⏱️  Response time: 1250ms
```

## API Integration Beispiel

```python
# In bidder.py
def get_active_projects(countries=None, **kwargs):
    params = {
        'limit': 20,
        'job_details': True,
        # ... andere Parameter
    }
    
    if countries:
        for country in countries:
            params[f'countries[]'] = country
    
    response = requests.get(endpoint, headers=headers, params=params)
    return response.json()

# Verwendung
german_projects = get_active_projects(countries=['de'])
dach_projects = get_active_projects(countries=['de', 'at', 'ch'])
```
