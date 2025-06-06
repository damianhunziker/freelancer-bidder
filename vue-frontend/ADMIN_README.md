# Database Administration Interface

## Overview

Die Database Administration-Komponente bietet ein benutzerfreundliches CRUD-Interface zur Verwaltung aller Datenbank-Tabellen und deren Relationen.

## Features

### 🔧 Umfassende Datenverwaltung
- **Employment Management**: Vollständige CRUD-Operationen für Berufserfahrung
- **Education Management**: Verwaltung von Weiterbildungen mit Tag-Zuordnung
- **Tags Management**: Zentrale Tag-Verwaltung mit Nutzungsstatistiken
- **Domains Overview**: Readonly-Ansicht der Domain-Daten

### 🏷️ Intelligente Tag-Integration
- **N:M Relationen**: Saubere Verwaltung der Education-Tags-Beziehungen
- **Tag-Wiederverwendung**: Bestehende Tags können mehrfach zugeordnet werden
- **Nutzungsstatistiken**: Anzeige der Tag-Verwendung in verschiedenen Bereichen
- **Lösch-Schutz**: Tags mit aktiven Verknüpfungen können nicht gelöscht werden

### 🎨 Benutzerfreundliches Interface
- **Tab-Navigation**: Übersichtliche Trennung der verschiedenen Bereiche
- **Modal-Formulare**: Intuitive Formulare für Erstellen/Bearbeiten
- **Responsive Design**: Funktioniert auf Desktop und mobilen Geräten
- **Echtzeit-Updates**: Automatische Aktualisierung nach Änderungen

## API Endpoints

### Employment
```
GET    /api/admin/employment        # Liste aller Employment-Einträge
GET    /api/admin/employment/:id    # Einzelner Employment-Eintrag
POST   /api/admin/employment        # Neuen Employment-Eintrag erstellen
PUT    /api/admin/employment/:id    # Employment-Eintrag aktualisieren
DELETE /api/admin/employment/:id    # Employment-Eintrag löschen
```

### Education
```
GET    /api/admin/education         # Liste aller Education-Einträge mit Tags
GET    /api/admin/education/:id     # Einzelner Education-Eintrag mit Tags
POST   /api/admin/education         # Neuen Education-Eintrag erstellen
PUT    /api/admin/education/:id     # Education-Eintrag aktualisieren
DELETE /api/admin/education/:id     # Education-Eintrag löschen
```

### Tags
```
GET    /api/admin/tags              # Liste aller Tags mit Nutzungsstatistiken
POST   /api/admin/tags              # Neuen Tag erstellen
PUT    /api/admin/tags/:id          # Tag aktualisieren
DELETE /api/admin/tags/:id          # Tag löschen (nur wenn unbenutzt)
```

### Domains
```
GET    /api/admin/domains           # Liste aller Domains (readonly)
GET    /api/admin/domains/:id       # Einzelne Domain (readonly)
```

## Datenbank-Schema

### Employment Table
```sql
- id (Primary Key)
- company_name (VARCHAR)
- position (VARCHAR)
- start_date (VARCHAR)
- end_date (VARCHAR, nullable)
- description (TEXT)
- is_self_employed (BOOLEAN)
- location (VARCHAR)
- technologies (TEXT)
- achievements (TEXT)
```

### Education Table
```sql
- id (Primary Key)
- title (VARCHAR)
- institution (VARCHAR)
- start_date (VARCHAR)
- end_date (VARCHAR, nullable)
- duration (VARCHAR)
- description (TEXT)
- location (VARCHAR)
- type (ENUM: course, training, workshop, certification)
```

### Tags Table
```sql
- id (Primary Key)
- tag_name (VARCHAR, unique)
```

### Education_Tags Table (N:M Relation)
```sql
- education_id (Foreign Key)
- tag_id (Foreign Key)
- Primary Key: (education_id, tag_id)
```

## Verwendung

### Zugriff
Die Admin-Oberfläche ist unter `/admin` erreichbar und über die Navigation verfügbar.

### Employment verwalten
1. Klicken Sie auf "➕ Add Employment"
2. Füllen Sie die Pflichtfelder aus (Company Name, Position, Start Date)
3. Optionale Felder: End Date, Location, Description, Technologies, Achievements
4. Setzen Sie "Self-employed" wenn zutreffend

### Education verwalten
1. Klicken Sie auf "➕ Add Education"
2. Füllen Sie Title und Start Date aus
3. Wählen Sie passende Tags aus der Liste
4. Bei Bedarf können neue Tags erstellt werden

### Tags verwalten
1. Erstellen Sie neue Tags über "➕ Add Tag"
2. Tags zeigen ihre Nutzung in Education und Domain-Bereichen
3. Benutzte Tags können nicht gelöscht werden

## Technische Details

### Frontend (Vue.js)
- **Komponente**: `DatabaseAdmin.vue`
- **State Management**: Local component state
- **HTTP Client**: Axios
- **Styling**: Scoped CSS mit responsive Design

### Backend (Node.js/Express)
- **Database**: MySQL mit Knex.js Query Builder
- **Transaktionen**: Für konsistente N:M-Beziehungen
- **Error Handling**: Umfassende Fehlerbehandlung
- **CORS**: Konfiguriert für Frontend-Integration

### Sicherheit
- **Input Validation**: Server-seitige Validierung
- **Foreign Key Constraints**: Datenbank-Ebene Konsistenz
- **Transaction Rollbacks**: Bei Fehlern in komplexen Operationen

## Erweiterungen

### Geplante Features
- Bulk-Import/Export Funktionalität
- Erweiterte Such- und Filterfunktionen
- Domain-Management (Create/Update/Delete)
- Audit-Log für Änderungen
- Backup/Restore Funktionalität

### Anpassungen
Das System ist modular aufgebaut und kann einfach um weitere Tabellen und Relationen erweitert werden. 