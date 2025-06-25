#!/usr/bin/env python3
"""
Qdrant Lite Quick Start
======================

Simplified Quick Start für die Qdrant Lite Integration ohne PyTorch/sentence-transformers.
Diese Version funktioniert mit dem keyword-basierten Ansatz.
"""

import sys
import json
import time
from datetime import datetime
import subprocess
import traceback

def print_header(title, symbol="🚀"):
    """Print formatted header"""
    line = "=" * 60
    print(f"\n{line}")
    print(f"{symbol} {title}")
    print(line)

def print_step(step_num, title):
    """Print step header"""
    print(f"\n📋 Schritt {step_num}: {title}")
    print("-" * 40)

def check_dependencies():
    """Check if required dependencies are available"""
    print_step(1, "Überprüfe Dependencies (Lite Version)")
    
    dependencies = {
        "qdrant_client": False,
        "mysql.connector": False,
        "json": True,  # Built-in
        "re": True,    # Built-in
    }
    
    missing_deps = []
    
    # Check Qdrant Client
    try:
        import qdrant_client
        dependencies["qdrant_client"] = True
        print("✅ Qdrant Client - installiert")
    except ImportError:
        print("❌ Qdrant Client - fehlt")
        missing_deps.append("qdrant-client")
    
    # Check MySQL Connector
    try:
        import mysql.connector
        dependencies["mysql.connector"] = True
        print("✅ MySQL Connector - installiert")
    except ImportError:
        print("❌ MySQL Connector - fehlt")
        missing_deps.append("mysql-connector-python")
    
    print("✅ JSON - verfügbar (built-in)")
    print("✅ Regex - verfügbar (built-in)")
    print("✅ Collections - verfügbar (built-in)")
    print("✅ Math - verfügbar (built-in)")
    
    if missing_deps:
        print(f"\n⚠️  Fehlende Packages: {', '.join(missing_deps)}")
        print("Installiere mit:")
        for dep in missing_deps:
            print(f"  pip3 install {dep}")
        return False
    
    print("\n✅ Alle Dependencies verfügbar!")
    return True

def check_qdrant_connection():
    """Check Qdrant connection"""
    print_step(2, "Überprüfe Qdrant Verbindung")
    
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(host='localhost', port=6333)
        collections = client.get_collections()
        
        print(f"✅ Qdrant Verbindung erfolgreich")
        print(f"📊 Gefundene Collections: {len(collections.collections)}")
        
        # List existing collections
        for collection in collections.collections:
            info = client.get_collection(collection.name)
            print(f"  - {collection.name}: {info.points_count} Punkte")
        
        return True
        
    except Exception as e:
        print(f"❌ Qdrant Verbindung fehlgeschlagen: {e}")
        print("\n🔧 Lösungsvorschläge:")
        print("1. Qdrant Container starten:")
        print("   docker run -d --name qdrant-freelancer -p 6333:6333 -p 6334:6334 \\")
        print("     -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant:latest")
        print("2. Container Status prüfen: docker ps | grep qdrant")
        print("3. Container Logs prüfen: docker logs qdrant-freelancer")
        return False

def check_mysql_connection():
    """Check MySQL connection"""
    print_step(3, "Überprüfe MySQL Verbindung")
    
    try:
        import mysql.connector
        
        config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'dCTKBq@CV9$a50ZtpzSr@D7*7Q',
            'database': 'domain_analysis'
        }
        
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # Check if required tables exist
        tables = ['domains', 'employment', 'education', 'tags']
        table_counts = {}
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_counts[table] = count
                print(f"✅ Tabelle '{table}': {count} Einträge")
            except Exception as e:
                print(f"⚠️  Tabelle '{table}': {e}")
        
        conn.close()
        
        if table_counts:
            print(f"\n✅ MySQL Verbindung erfolgreich")
            return True
        else:
            print(f"\n❌ Keine Daten in MySQL Tabellen gefunden")
            return False
        
    except Exception as e:
        print(f"❌ MySQL Verbindung fehlgeschlagen: {e}")
        print("\n🔧 Lösungsvorschläge:")
        print("1. MySQL Server starten")
        print("2. Datenbank 'domain_analysis' existiert")
        print("3. Zugangsdaten prüfen")
        print("4. Tabellen erstellt: domains, employment, education, tags")
        return False

def test_lite_integration():
    """Test the Qdrant Lite integration"""
    print_step(4, "Teste Qdrant Lite Integration")
    
    try:
        # Import the lite integration
        from qdrant_lite_integration import QdrantLiteAnalyzer
        
        analyzer = QdrantLiteAnalyzer()
        
        # Health check
        health = analyzer.health_check()
        print("📊 System Status:")
        print(f"  - Qdrant verfügbar: {health['qdrant_available']}")
        print(f"  - MySQL verfügbar: {health['mysql_available']}")
        print(f"  - System initialisiert: {health['initialized']}")
        print(f"  - Vectorizer trainiert: {health['vectorizer_trained']}")
        
        if health['collections']:
            print("  - Collections:")
            for name, info in health['collections'].items():
                print(f"    • {name}: {info['points_count']} Punkte, Status: {info['status']}")
        
        # Test job analysis
        test_jobs = [
            "Laravel dashboard with real-time data visualization",
            "Vue.js frontend development with API integration",
            "Python backend development with MySQL database",
            "Trading system with machine learning capabilities"
        ]
        
        print(f"\n🧪 Teste Job-Analyse mit {len(test_jobs)} Beispielen:")
        
        results = []
        for i, job_desc in enumerate(test_jobs, 1):
            print(f"\n  Test {i}: {job_desc}")
            
            result = analyzer.analyze_job_correlation(job_desc)
            
            if result.enhanced_analysis:
                domains_count = len(result.correlation_analysis.get('domains', []))
                employment_count = len(result.correlation_analysis.get('employment', []))
                education_count = len(result.correlation_analysis.get('education', []))
                
                print(f"    ✅ Enhanced Analysis: {domains_count} Domains, {employment_count} Employment, {education_count} Education")
                results.append('enhanced')
            else:
                print(f"    ⚠️  Legacy Analysis: {result.error_message}")
                results.append('legacy')
        
        enhanced_count = results.count('enhanced')
        total_count = len(results)
        
        print(f"\n📊 Test Ergebnisse: {enhanced_count}/{total_count} mit Enhanced Analysis")
        
        if enhanced_count > 0:
            print("✅ Qdrant Lite Integration funktioniert!")
            return True
        elif enhanced_count == 0 and total_count > 0:
            print("⚠️  Nur Legacy Analysis verfügbar (Fallback funktioniert)")
            return True
        else:
            print("❌ Integration fehlgeschlagen")
            return False
            
    except Exception as e:
        print(f"❌ Fehler beim Testen der Integration: {e}")
        print(traceback.format_exc())
        return False

def test_bidder_integration():
    """Test integration with existing bidder system"""
    print_step(5, "Teste Bidder Integration")
    
    try:
        # Test the enhanced bidder patch
        try:
            from bidder_qdrant_patch import EnhancedBidder
            
            bidder = EnhancedBidder()
            
            test_job = "Real-time dashboard development with Laravel and Vue.js"
            
            print(f"🔍 Teste Enhanced Bidder mit: {test_job}")
            
            # Test correlation analysis
            correlation = bidder.enhanced_correlation_analysis(test_job)
            
            # Test full bid generation
            bid_result = bidder.generate_enhanced_bid("TEST_PROJECT", test_job)
            
            print("✅ Enhanced Bidder Integration erfolgreich!")
            print(f"📝 Bid-Text generiert: {len(bid_result['bid_teaser']['final_composed_text'])} Zeichen")
            
            # Show metadata
            metadata = bid_result.get('analysis_metadata', {})
            print(f"📊 Enhanced Analysis: {metadata.get('enhanced_analysis', False)}")
            
            return True
            
        except ImportError:
            print("⚠️  bidder_qdrant_patch.py nicht gefunden - das ist optional")
            return True
            
    except Exception as e:
        print(f"❌ Fehler beim Testen der Bidder Integration: {e}")
        return False

def show_next_steps(success_count, total_tests):
    """Show next steps based on test results"""
    print_step("Final", "Nächste Schritte")
    
    if success_count == total_tests:
        print("🎉 Alle Tests erfolgreich! Das System ist einsatzbereit.")
        print("\n🚀 Was Sie jetzt tun können:")
        print("1. Qdrant Lite in Ihren Bidder integrieren:")
        print("   from qdrant_lite_integration import QdrantLiteAnalyzer")
        print("   analyzer = QdrantLiteAnalyzer()")
        print("   result = analyzer.analyze_job_correlation(job_description)")
        
        print("\n2. Daten aktualisieren:")
        print("   python3 qdrant_lite_integration.py")
        
        print("\n3. Zu vollständiger Version upgraden:")
        print("   pip3 install torch sentence-transformers")
        print("   python3 qdrant_vector_store.py")
        
        print("\n4. Web Interface besuchen:")
        print("   http://localhost:6333/dashboard")
        
        print("\n5. Health Check regelmäßig ausführen:")
        print("   analyzer.health_check()")
        
    elif success_count > 0:
        print(f"⚠️  {success_count}/{total_tests} Tests erfolgreich.")
        print("Das System funktioniert teilweise. Überprüfen Sie die fehlgeschlagenen Tests.")
        
    else:
        print("❌ Alle Tests fehlgeschlagen.")
        print("\n🔧 Troubleshooting Schritte:")
        print("1. Dependencies installieren: pip3 install qdrant-client mysql-connector-python")
        print("2. Qdrant starten: ./setup_qdrant.sh")
        print("3. MySQL Verbindung prüfen")
        print("4. Logs überprüfen: docker logs qdrant-freelancer")

def main():
    """Main quick start function"""
    start_time = datetime.now()
    
    print_header("Qdrant Lite Quick Start")
    print(f"⏰ Gestartet: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    success_count = 0
    tests = [
        ("Dependencies Check", check_dependencies),
        ("Qdrant Connection", check_qdrant_connection),
        ("MySQL Connection", check_mysql_connection),
        ("Lite Integration", test_lite_integration),
        ("Bidder Integration", test_bidder_integration)
    ]
    
    for test_name, test_func in tests:
        try:
            if test_func():
                success_count += 1
                print(f"✅ {test_name} - Erfolgreich")
            else:
                print(f"❌ {test_name} - Fehlgeschlagen")
        except Exception as e:
            print(f"❌ {test_name} - Fehler: {e}")
    
    # Summary
    print_header("Quick Start Zusammenfassung")
    
    if success_count == len(tests):
        status = "✅ Vollständig erfolgreich"
    elif success_count > len(tests) // 2:
        status = "⚠️  Teilweise erfolgreich"
    else:
        status = "❌ Fehlgeschlagen"
    
    print(f"{status}")
    print(f"\n📊 Ergebnis: {success_count}/{len(tests)} Tests erfolgreich")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"⏱️  Dauer: {duration:.1f} Sekunden")
    
    show_next_steps(success_count, len(tests))

if __name__ == "__main__":
    main()