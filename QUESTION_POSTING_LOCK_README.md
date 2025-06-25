# Question Posting Lock System

## Übersicht

Das Question Posting Lock System verhindert **doppelte Frage-Submissions** sowohl im Frontend als auch im Backend. Es stellt sicher, dass für jedes Projekt nur eine Frage gleichzeitig gesendet werden kann.

## Funktionalität

### Doppelter Schutz

#### Frontend-Schutz (Vue.js)
- **Set**: `questionPostingProjectIds`
- **Schutz vor**: Mehrfache Button-Klicks durch Benutzer
- **Scope**: Pro Browser-Session

#### Backend-Schutz (Node.js)
- **Set**: `questionPostingLocks`
- **Schutz vor**: Mehrfache API-Anfragen (auch von verschiedenen Clients)
- **Scope**: Global für alle Anfragen

## Workflow

### 1. Frage-Submission wird gestartet

#### Frontend:
```javascript
// Prüfung vor API-Aufruf
if (this.questionPostingProjectIds.has(projectId)) {
  throw new Error('Question posting already in progress');
}

// Lock setzen
this.questionPostingProjectIds.add(projectId);
```

#### Backend:
```javascript
// Prüfung bei API-Eingang
if (questionPostingLocks.has(projectId)) {
  return res.status(409).json({
    error: 'Question posting already in progress',
    status: 'duplicate_prevented'
  });
}

// Lock setzen
questionPostingLocks.add(projectId);
```

### 2. Python-Script wird ausgeführt

- **Asynchroner Prozess**: Fire-and-forget Selenium-Automation
- **Timeout**: 60 Sekunden automatische Beendigung
- **Monitoring**: Stdout/Stderr wird geloggt

### 3. Lock wird automatisch entfernt

#### Bei Erfolg:
```javascript
pythonProcess.on('close', (code) => {
  questionPostingLocks.delete(projectId);
  if (code === 0) {
    logAutoBiddingServer('Question posted successfully', 'success');
  }
});
```

#### Bei Fehler:
```javascript
pythonProcess.on('error', (error) => {
  questionPostingLocks.delete(projectId);
  logAutoBiddingServer('Question posting error', 'error');
});
```

#### Bei Timeout:
```javascript
setTimeout(() => {
  pythonProcess.kill('SIGTERM');
  questionPostingLocks.delete(projectId);
  logAutoBiddingServer('Question posting timeout', 'warning');
}, 60000);
```

## API-Endpoints

### Status abfragen
```bash
GET /api/question-posting-locks/status
```

**Response:**
```json
{
  "success": true,
  "activeLocks": ["123456", "789012"],
  "lockCount": 2,
  "timestamp": "2025-06-19T10:30:45.123Z"
}
```

### Locks manuell löschen
```bash
POST /api/question-posting-locks/clear
```

**Response:**
```json
{
  "success": true,
  "message": "Cleared 2 question posting locks",
  "clearedLocks": ["123456", "789012"],
  "timestamp": "2025-06-19T10:30:45.123Z"
}
```

## HTTP-Status-Codes

### 409 Conflict
- **Grund**: Frage wird bereits für dieses Projekt gesendet
- **Action**: Benutzer über laufende Operation informieren

### 500 Internal Server Error
- **Grund**: Systemfehler beim Question Posting
- **Action**: Lock wird automatisch entfernt

## Logging

### Frontend-Logs
```javascript
console.log('[PostQuestion] 🔒 LOCKED: Project 123456 marked as posting question');
console.log('[PostQuestion] 🔓 UNLOCKED: Project 123456 removed from question posting');
```

### Backend-Logs
```javascript
console.log('[PostQuestion] 🔒 LOCKED: Project 123456 marked as posting question. Active locks: 3');
console.log('[PostQuestion] 🔓 UNLOCKED: Project 123456 removed from question posting. Active locks: 2');
```

### Auto-Bidding Server Logs
```javascript
logAutoBiddingServer('Question posting started for project 123456. Active locks: 3', 'info', '123456');
logAutoBiddingServer('Question posted successfully for project 123456. Active locks: 2', 'success', '123456');
```

## Fehlerbehandlung

### Frontend-Fehler
```javascript
try {
  await this.postQuestionToProject(projectId);
} catch (error) {
  if (error.message.includes('already in progress')) {
    this.showNotification('Question is already being sent to this project', 'warning');
  }
} finally {
  // Lock wird automatisch im finally-Block entfernt
  this.questionPostingProjectIds.delete(projectId);
}
```

### Backend-Fehler-Scenarios

#### 1. Duplicate Prevention
```javascript
if (questionPostingLocks.has(projectId)) {
  return res.status(409).json({
    success: false,
    error: 'Question posting already in progress for this project',
    status: 'duplicate_prevented'
  });
}
```

#### 2. Python Process Error
```javascript
pythonProcess.on('error', (error) => {
  questionPostingLocks.delete(projectId);  // Unlock auf Fehler
  logAutoBiddingServer(`Question posting error: ${error.message}`, 'error');
});
```

#### 3. Timeout Handling
```javascript
setTimeout(() => {
  if (!processCompleted) {
    pythonProcess.kill('SIGTERM');
    questionPostingLocks.delete(projectId);  // Unlock bei Timeout
    logAutoBiddingServer('Question posting timeout (killed after 60s)', 'warning');
  }
}, 60000);
```

## Debugging

### Lock-Status prüfen
```bash
curl http://localhost:5002/api/question-posting-locks/status
```

### Alle Locks löschen (Notfall)
```bash
curl -X POST http://localhost:5002/api/question-posting-locks/clear
```

### Console-Debugging
```javascript
// Frontend
console.log('Current question posting projects:', Array.from(this.questionPostingProjectIds));

// Backend (in Browser Dev Tools -> Network -> Response)
// Siehe Auto-Bidding Logs oder direkt Status-Endpoint
```

## Vorteile

1. **Doppelter Schutz**: Frontend + Backend Prevention
2. **Robuste Cleanup**: Automatisches Unlock in allen Szenarien
3. **Monitoring**: Vollständige Nachverfolgung aller Locks
4. **Debugging-Tools**: Status-Abfrage und manuelles Clearing
5. **Performance**: Memory-effiziente Set-basierte Implementierung
6. **Skalierbarkeit**: Unterstützt beliebig viele gleichzeitige Projekte

## Sicherheitsfeatures

- **Memory Leak Prevention**: Automatisches Cleanup verhindert Speicher-Aufbau
- **Process Leak Prevention**: 60s Timeout verhindert hängende Python-Prozesse
- **Race Condition Prevention**: Atomare Set-Operationen verhindern Race Conditions
- **Error Resilience**: Locks werden auch bei unerwarteten Fehlern entfernt
- **Monitoring**: Vollständige Transparenz über aktive Locks

## Integration

Das System ist vollständig integriert und erfordert keine manuelle Konfiguration. Es funktioniert automatisch bei:

- Manuellen Question-Button Klicks
- Auto-Bidding mit aktiviertem Question Posting
- API-Aufrufen von externen Clients
- Entwicklungs- und Produktionsumgebungen 