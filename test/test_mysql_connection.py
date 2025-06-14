#!/usr/bin/env python3
"""
Test script für MySQL-Verbindung zur domain_analysis Datenbank
"""

import mysql.connector
from mysql.connector import Error
from mysql_config import MYSQL_CONFIG

def test_connection():
    """Teste die MySQL-Verbindung"""
    print("🔍 Teste MySQL-Verbindung...")
    print(f"Host: {MYSQL_CONFIG['host']}")
    print(f"Port: {MYSQL_CONFIG['port']}")
    print(f"User: {MYSQL_CONFIG['user']}")
    print(f"Database: {MYSQL_CONFIG['database']}")
    print("-" * 50)
    
    try:
        # Teste Verbindung zum MySQL Server (ohne spezifische Datenbank)
        test_config = MYSQL_CONFIG.copy()
        test_db = test_config.pop('database')  # Entferne Datenbank temporär
        
        print("1. Teste Verbindung zum MySQL Server...")
        connection = mysql.connector.connect(**test_config)
        
        if connection.is_connected():
            print("✅ MySQL Server-Verbindung erfolgreich!")
            
            # Prüfe ob Datenbank existiert
            cursor = connection.cursor()
            cursor.execute("SHOW DATABASES")
            databases = [db[0] for db in cursor.fetchall()]
            
            if test_db in databases:
                print(f"✅ Datenbank '{test_db}' existiert!")
                
                # Teste Verbindung zur spezifischen Datenbank
                cursor.close()
                connection.close()
                
                print("2. Teste Verbindung zur domain_analysis Datenbank...")
                connection = mysql.connector.connect(**MYSQL_CONFIG)
                cursor = connection.cursor()
                
                # Teste einfache Query
                cursor.execute("SELECT DATABASE()")
                current_db = cursor.fetchone()[0]
                print(f"✅ Verbunden mit Datenbank: {current_db}")
                
                # Zeige existierende Tabellen
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                if tables:
                    print(f"📋 Existierende Tabellen in {test_db}:")
                    for table in tables:
                        print(f"   - {table[0]}")
                else:
                    print(f"📋 Datenbank {test_db} ist leer (keine Tabellen)")
                
                cursor.close()
                connection.close()
                
                print("\n🎉 MySQL-Verbindung vollständig erfolgreich!")
                print("💡 Du kannst jetzt 'python import_domains_to_db.py' ausführen")
                return True
                
            else:
                print(f"❌ Datenbank '{test_db}' existiert nicht!")
                print(f"📋 Verfügbare Datenbanken: {', '.join(databases)}")
                print(f"💡 Erstelle die Datenbank mit: CREATE DATABASE {test_db};")
                cursor.close()
                connection.close()
                return False
        
    except Error as e:
        print(f"❌ MySQL-Verbindungsfehler: {e}")
        print("\n🔧 Überprüfe deine Einstellungen in mysql_config.py:")
        print("   - Host und Port korrekt?")
        print("   - Benutzername und Passwort richtig?")
        print("   - MySQL Server läuft?")
        return False
    
    except Exception as e:
        print(f"❌ Unerwarteter Fehler: {e}")
        return False

if __name__ == "__main__":
    test_connection() 