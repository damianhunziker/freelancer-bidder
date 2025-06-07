# Automatic Bidding Feature

## Übersicht

Das **Automatic Bidding Feature** ermöglicht es dem System, automatisch auf ausgewählte Projekte zu bieten, die bestimmte Qualitätskriterien erfüllen.

## Funktionsweise

### 1. Aktivierung
- **Checkbox "Automatic Bidding"** im Header des Vue Frontends
- Zeigt ein Robot-Icon 🤖 an, wenn aktiviert
- Pulsierender Effekt zur visuellen Bestätigung

### 2. Projekt-Auswahlkriterien
Ein Projekt wird **automatisch gebottet**, wenn es "eingerahmt" ist, d.h.:

**Qualitäts-Flags (mindestens eines):**
- `is_corr` - Hohe Korrelation
- `is_rep` - Gute Reputation  
- `is_authentic` - Authentisch
- `is_enterprise` - Enterprise-Projekt

**UND**

**Dringlichkeits-Flags (mindestens eines):**
- `is_high_paying` - Gut bezahlt
- `is_urgent` - Dringend
- `is_german` - Deutschsprachig
- Stündliches Projekt (HR-Flag)

### 3. Automatischer Workflow

**Für bestehende Projekte (beim Aktivieren):**
1. System prüft alle aktuellen Projekte
2. Identifiziert eingerahmte Projekte ohne bestehende Bewerbung
3. Generiert automatisch Bid-Text (Score: 75)
4. Sendet Bewerbung über Freelancer API

**Für neue Projekte (laufend):**
1. Neue Projekte werden automatisch geprüft
2. Eingerahmte Projekte werden sofort gebottet
3. 1-Sekunden-Verzögerung vor Prüfung
4. 3-Sekunden-Verzögerung zwischen Bids

## Sicherheitsfeatures

### Duplikat-Schutz
- Keine Bewerbung auf bereits gebottete Projekte
- Prüfung über `buttonStates.bidSubmitted` und `buttonStates.applicationSent`

### Rate Limiting
- Verzögerungen zwischen API-Aufrufen
- Verhindert Überlastung der Freelancer API

### Fehlerbehandlung
- **API-Erfolg**: Bestätigung mit Betrag und Dauer
- **API-Fehler**: Fallback zu manuellem Text
- **Technische Fehler**: Detaillierte Fehlermeldungen

## UI-Feedback

### Benachrichtigungen
```javascript
// Erfolg
"✅ Automatic bid submitted for '{Projekttitel}' - ${Betrag}"

// Warnung  
"⚠️ Automatic bid failed for '{Projekttitel}' - manual submission required"

// Fehler
"❌ Automatic bid error for '{Projekttitel}': {Fehlermeldung}"
```

### Visuelle Indikatoren
- **Loading-State**: Während Bid-Generierung und -Submission
- **Robot-Icon**: Pulsiert bei aktiviertem Automatic Bidding
- **Project-Rahmen**: Zeigt eingerahmte Projekte visuell an

## Code-Struktur

### Frontend-Methoden
- `onAutomaticBiddingToggle()` - Checkbox-Handler
- `shouldAutomaticallyBid(project)` - Prüft Bid-Kriterien
- `checkProjectsForAutomaticBidding()` - Prüft alle Projekte
- `performAutomaticBid(project)` - Führt automatischen Bid aus

### Backend-Integration
- **Bid-Generierung**: `/api/generate-bid/{projectId}`
- **Bid-Submission**: `/api/send-application/{projectId}`
- **Freelancer API**: Direkte Integration für echte Bids

## Monitoring

### Console-Logs
```
[AutoBid] Checking projects for automatic bidding...
[AutoBid] Project {ID} qualifies for automatic bidding
[AutoBid] Starting automatic bid for project: {Titel}
[AutoBid] Bid text generated for project {ID}
[AutoBid] Submitting bid for project {ID}
[AutoBid] Successfully submitted automatic bid for project {ID}
```

### Metrics
- Automatische Bids pro Session
- Erfolgsrate der API-Aufrufe
- Projektqualifikations-Rate

## Konfiguration

### Standard-Parameter
- **Score für automatische Bids**: 75
- **Erklärung**: "Automatic bid based on project matching quality and urgency criteria."
- **Verzögerungen**: 1s vor Prüfung, 3s zwischen Bids

## Systemvoraussetzungen

### Backend-Konfiguration
```javascript
// config.py
FREELANCER_API_KEY = "your_oauth_token"
FREELANCER_USER_ID = "webskillssl"  // oder numeric ID
```

### API-Berechtigungen
- OAuth-Token mit Scopes: `basic`, `fln:project_manage`
- Gültige Freelancer.com-Authentifizierung

## Troubleshooting

### Häufige Probleme

**Keine automatischen Bids:**
1. Checkbox aktiviert? ✓
2. Projekte erfüllen Kriterien? ✓
3. OAuth-Token gültig? ✓
4. Bereits gebottet? ✓

**API-Fehler:**
- 401: Token abgelaufen → Neues OAuth-Token generieren
- 409: Bereits gebottet → Normal, System verhindert Duplikate
- 403: Keine Berechtigung → OAuth-Scopes prüfen

**Performance:**
- Zu viele gleichzeitige Bids → Rate Limiting erhöhen
- Langsame Responses → API-Endpunkt prüfen

## Monitoring-Dashboard

Das System bietet vollständige Transparenz über:
- Anzahl qualifizierter Projekte
- Automatische Bid-Versuche
- Erfolgs-/Fehlerrate
- API-Response-Zeiten

## Deaktivierung

Automatisches Bidding kann jederzeit durch Abwählen der Checkbox gestoppt werden. Laufende Bids werden abgeschlossen, neue werden nicht gestartet. 