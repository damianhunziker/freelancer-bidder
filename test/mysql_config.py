# MySQL Database Configuration for domain_analysis

# Database connection settings
# WICHTIG: Bitte diese Einstellungen an deine MySQL-Installation anpassen!
MYSQL_CONFIG = {
    'host': 'localhost',        # Dein MySQL Host (meist localhost)
    'port': 3306,              # MySQL Port (Standard: 3306)
    'user': 'root',            # Dein MySQL Benutzername
    'password': '',            # Dein MySQL Passwort (HIER EINTRAGEN!)
    'database': 'domain_analysis',  # Die Datenbank die verwendet werden soll
    'charset': 'utf8mb4',
    'autocommit': True,
    'use_unicode': True
}

# Alternative: Environment Variables verwenden (sicherer für Passwörter)
# import os
# MYSQL_CONFIG = {
#     'host': os.getenv('MYSQL_HOST', 'localhost'),
#     'port': int(os.getenv('MYSQL_PORT', 3306)),
#     'user': os.getenv('MYSQL_USER', 'root'),
#     'password': os.getenv('MYSQL_PASSWORD', ''),
#     'database': os.getenv('MYSQL_DATABASE', 'domain_analysis'),
#     'charset': 'utf8mb4',
#     'autocommit': True,
#     'use_unicode': True
# }

# ANLEITUNG:
# 1. Passe die MYSQL_CONFIG oben an deine MySQL-Einstellungen an
# 2. Stelle sicher, dass die Datenbank 'domain_analysis' bereits existiert
# 3. Führe dann aus: python import_domains_to_db.py 