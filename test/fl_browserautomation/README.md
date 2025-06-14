# Freelancer.com Universal WebSocket Monitor

## Überblick

Dieses Tool verwendet Browser-Automation (Selenium) um sich bei Freelancer.com anzumelden und **ALLE WebSocket-Verbindungen** in Echtzeit zu überwachen. **URL-unabhängig** - perfekt für sich ändernde WebSocket-Adressen!

## Features

- 🚀 **Automatischer Login** bei Freelancer.com
- 🌐 **Universelles WebSocket-Monitoring** - erfasst ALLE WebSocket-URLs
- 💼 **Job-Notification-Erkennung** mit sofortiger Benachrichtigung
- 🔄 **URL-unabhängig** - funktioniert auch wenn WebSocket-Adressen sich ändern
- 💾 **Vollständiger Datenexport** in JSON-Format
- 🎯 **Browser-Integration** für authentifizierte Sessions
- 📊 **Live-Statistics** während des Monitorings
- ⚡ **Erfasst alle Verbindungen** automatisch

## Warum Universal WebSocket Monitoring?

Da sich die WebSocket-URLs bei Freelancer.com ständig ändern (z.B. von `/816/yyw0q5ug/websocket` zu anderen IDs), überwacht dieses Tool **alle** WebSocket-Verbindungen automatisch:

- ✅ **Alle URLs erfasst** - egal welche WebSocket-Adresse verwendet wird
- ✅ **Connection-Tracking** - sieht alle neuen WebSocket-Verbindungen
- ✅ **Message-Logging** - kompletter Traffic aller Verbindungen
- ✅ **Error-Handling** - überwacht auch Verbindungsabbrüche

## Installation

1. **Dependencies installieren:**
```bash
pip install -r requirements.txt
```

2. **Chrome/Chromium Browser** muss installiert sein (für Selenium)

3. **Konfiguration** in `../config.py` erstellen:
```python
# Freelancer.com Login-Daten
FREELANCER_USERNAME = "dein_username"
FREELANCER_PASSWORD = "dein_passwort"
```

## Verwendung

### Universal-Monitoring

```bash
python browser_websocket_monitor.py
```

Das Tool wird:
1. Browser starten
2. Bei Freelancer.com einloggen  
3. Zu Job-Seite navigieren
4. **Universal WebSocket-Monitor** injizieren
5. **ALLE WebSocket-Verbindungen** automatisch erfassen
6. 10 Minuten lang kompletten WebSocket-Traffic überwachen
7. **Job-Notifications sofort anzeigen**
8. Vollständige Ergebnisse in JSON-Dateien speichern

### Launcher verwenden

```bash
python run_job_monitor.py
```

## Erkannte WebSocket-Events

Der Monitor erfasst **alle** WebSocket-Aktivitäten:

- 🔌 **Connection**: Neue WebSocket-Verbindungen
- 📨 **Messages**: Alle eingehenden Daten
- 📤 **Sends**: Alle ausgehenden Daten  
- ❌ **Errors**: Verbindungsfehler
- 🔌 **Close**: Verbindungsabbrüche

## Job-Detection-Keywords

```javascript
// Sucht in ALLEN WebSocket-Messages nach:
'project', 'job', 'bid', 'proposal', 'notification', 
'contest', 'freelancer', 'new', 'post'
```

## Output-Dateien

- `all_websocket_traffic_YYYYMMDD_HHMMSS.json` - Kompletter WebSocket-Traffic

### JSON-Struktur:
```json
{
  "messages": [...],           // Alle WebSocket-Messages
  "job_notifications": [...],  // Gefilterte Job-Notifications  
  "all_websockets": [...],     // Alle WebSocket-Verbindungen
  "total_messages": 150,
  "total_job_notifications": 8,
  "total_websocket_connections": 3
}
```

## Live-Logging

Das Tool zeigt Live-Output mit:
- 🔌 **WebSocket-Verbindungen** mit URLs
- 📨 **Eingehende Messages** mit Quell-URL
- 📤 **Ausgehende Messages** mit Ziel-URL
- 💼 **JOB NOTIFICATIONS** (sofort hervorgehoben)
- ⏱️ **Status-Updates** alle 30 Sekunden

## Troubleshooting

### Keine WebSocket-Verbindungen
- Stelle sicher dass JavaScript aktiviert ist
- Navigiere zu verschiedenen Freelancer-Seiten
- Warte länger - manche WebSockets verbinden erst nach Benutzeraktivität

### Login-Probleme
- **2FA/Captcha:** Tool pausiert für manuellen Login
- **Timeout:** Vergrößere Wartezeiten in der Konfiguration

## Technische Details

### Universal WebSocket Interception
```javascript
// Überschreibt den WebSocket-Konstruktor komplett
const OriginalWebSocket = window.WebSocket;
window.WebSocket = function(url, protocols) {
    // Automatische URL-Erfassung
    window.allWebSockets.push({url, protocols, timestamp});
    
    // Komplettes Event-Monitoring für ALLE Verbindungen
    ws.addEventListener('open', handler);
    ws.addEventListener('message', handler);  
    ws.addEventListener('error', handler);
    ws.addEventListener('close', handler);
}
```

## Beispiel-Output

```
🤖 Freelancer Universal WebSocket Monitor
======================================================================
💡 Überwacht ALLE WebSocket-Verbindungen für Job-Notifications
🌐 URL-unabhängig - erfasst alle WebSocket-Traffic

🚀 Browser wird eingerichtet...
✅ Browser erfolgreich gestartet!
🔐 Logge bei Freelancer.com ein...
✅ Erfolgreich eingeloggt!
💼 Navigiere zu Job-Seite...
💉 Injiziere WebSocket-Monitor...
✅ WebSocket-Monitor erfolgreich injiziert!
🌐 Überwacht ALLE WebSocket-Verbindungen (URL-unabhängig)

👂 Überwache WebSocket-Traffic für 10 Minuten...
🔍 Suche nach Job-Notifications...

📨 [10:30:15] WEBSOCKET_CONNECTED: wss://notifications.freelancer.com/816/abc123/websocket
📨 [10:30:16] {"type":"ping"} via wss://notifications.freelancer.com/816/abc123/websocket
📨 [10:30:20] {"type":"notification","project_id":123456} via wss://notifications.freelancer.com/816/abc123/websocket

🎉 JOB NOTIFICATION GEFUNDEN!
📄 Vollständige Daten: {"type":"job_notification","project_id":123456,"title":"New Web Development Project"}
--------------------------------------------------

======================================================================
📊 FINALE STATISTIKEN:
📨 Gesamt Messages: 145
💼 Job Notifications: 8  
🔌 WebSocket Verbindungen: 3

🌐 GEFUNDENE WEBSOCKET-VERBINDUNGEN:
1. wss://notifications.freelancer.com/816/abc123/websocket (seit 2024-01-15T10:30:15.123Z)
2. wss://chat.freelancer.com/socket.io/?transport=websocket (seit 2024-01-15T10:32:01.456Z)
3. wss://live.freelancer.com/updates/websocket (seit 2024-01-15T10:35:30.789Z)

🎉 GEFUNDENE JOB-NOTIFICATIONS:
1. 2024-01-15T10:30:20.456Z via wss://notifications.freelancer.com/816/abc123/websocket
   📄 {"type":"job_notification","project_id":123456,"title":"New Web Development Project"}

💾 Alle WebSocket-Daten gespeichert in: all_websocket_traffic_20240115_103045.json
🎉 ERFOLG! Job-Notifications gefunden! 