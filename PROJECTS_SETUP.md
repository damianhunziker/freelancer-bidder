# Projects Management Setup

This document describes the new Projects management functionality added to the admin area.

## Database Setup

First, run the SQL script to create the necessary database tables:

```bash
mysql -u root -p domain_analysis < create_projects_tables.sql
```

This will create the following tables:
- `projects` - Main project information
- `project_tags` - Many-to-many relationship between projects and tags
- `project_files` - Files associated with each project
- `project_file_tags` - Tags for individual files

## Features

### Projects Management
- **Create/Edit Projects**: Full CRUD operations for projects
- **Status Tracking**: Projects can be in different states:
  - Planning
  - Active
  - Completed
  - On Hold
  - Cancelled
- **Budget Management**: Track minimum and maximum budget in different currencies
- **Job Linking**: Link projects to original jobs when they are won

### File Management
- **File Storage**: Add files to projects with metadata
- **File Tagging**: Tag files with expandable tag system
- **Communication Files**: Mark files as communication-related
- **File Types**: Track different file types (PDF, DOCX, etc.)

### Tag System
- **Self-Expanding Tags**: Tags are automatically created if they don't exist
- **Shared Tags**: Same tags used across employment, education, domains, and projects
- **File-Level Tags**: Individual files can have their own tags

## Usage

### Creating a Project
1. Go to the Admin area
2. Click on the "Projects" tab
3. Click "➕ Add Project"
4. Fill in the project details:
   - Title (required)
   - Description
   - Status
   - Project type (hourly/fixed)
   - Budget range
   - Country
   - Start/End dates
   - Internal notes
   - Tags

### Converting Jobs to Projects
When you win a job, you can convert it to a project:
1. Use the API endpoint `/api/admin/projects/from-job` 
2. Send the job data to automatically create a project with the same fields

### Managing Project Files
1. Click the 📁 button next to a project
2. Add files with:
   - File name
   - File path/location
   - File type
   - Description
   - Communication flag
   - Tags for organization

### API Endpoints

The following API endpoints are available:

```
GET    /api/admin/projects              - Get all projects
GET    /api/admin/projects/:id          - Get project by ID
POST   /api/admin/projects              - Create new project
PUT    /api/admin/projects/:id          - Update project
DELETE /api/admin/projects/:id          - Delete project

POST   /api/admin/projects/:id/files    - Add file to project
PUT    /api/admin/projects/files/:id    - Update project file
DELETE /api/admin/projects/files/:id    - Delete project file

POST   /api/admin/projects/:id/link-job - Link job to project
POST   /api/admin/projects/from-job     - Create project from job
POST   /api/admin/projects/:id/tags     - Add tag to project
DELETE /api/admin/projects/:id/tags/:tagId - Remove tag from project
```

## Future Automation Features

The system is designed to support future automation:

1. **Tag Generation**: Automatically read project files and generate relevant tags
2. **Domain Conversion**: Turn completed projects into domains for future reference
3. **Progress Tracking**: Monitor work done based on files and communications
4. **Client Communication**: Track all communications related to a project

## Integration

The projects system integrates with:
- **Jobs System**: Convert won jobs to active projects
- **Tags System**: Shared tagging across all content types
- **Domain System**: Convert projects to domains for knowledge base
- **File System**: Organize all project-related files

## Notes

- All project data is stored in the `domain_analysis` database
- The system maintains referential integrity with foreign key constraints
- Tags are automatically created when they don't exist
- Files can be tagged independently of their parent project
- The interface provides visual status indicators and file counts 