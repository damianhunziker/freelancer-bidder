#!/usr/bin/env python3
"""
Quick Start Script für Qdrant Vector Store Integration
====================================================

Dieser Script testet die komplette Qdrant-Integration mit minimalen Setup-Anforderungen.
Führt alle wichtigen Funktionen aus und zeigt Beispiel-Resultate.

Verwendung:
    python3 quick_start_qdrant.py
"""

import json
import sys
import time
import traceback
from datetime import datetime

def print_header(title):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print(f"{'='*60}")

def print_step(step, description):
    """Print formatted step"""
    print(f"\n📋 Schritt {step}: {description}")
    print("-" * 40)

def check_dependencies():
    """Check if all required dependencies are installed"""
    print_step(1, "Überprüfe Dependencies")
    
    required_packages = [
        ('qdrant_client', 'Qdrant Client'),
        ('sentence_transformers', 'Sentence Transformers'),
        ('mysql.connector', 'MySQL Connector'),
        ('numpy', 'NumPy')
    ]
    
    missing_packages = []
    
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"✅ {name} - installiert")
        except ImportError:
            print(f"❌ {name} - fehlt")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Fehlende Packages: {', '.join(missing_packages)}")
        print("Installiere mit: pip install -r requirements_qdrant.txt")
        return False
    
    print("✅ Alle Dependencies verfügbar")
    return True

def check_qdrant_connection():
    """Check Qdrant connection"""
    print_step(2, "Teste Qdrant-Verbindung")
    
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient('localhost', port=6333)
        collections = client.get_collections()
        
        print(f"✅ Qdrant-Verbindung erfolgreich")
        print(f"📊 Verfügbare Collections: {len(collections.collections)}")
        
        for collection in collections.collections:
            print(f"   - {collection.name}")
        
        return True, client
        
    except Exception as e:
        print(f"❌ Qdrant-Verbindung fehlgeschlagen: {e}")
        print("💡 Starte Qdrant mit: ./setup_qdrant.sh")
        return False, None

def check_mysql_connection():
    """Check MySQL connection"""
    print_step(3, "Teste MySQL-Verbindung")
    
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
        
        # Test basic queries
        cursor.execute("SELECT COUNT(*) FROM domains")
        domain_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM employment")
        employment_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM education")
        education_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ MySQL-Verbindung erfolgreich")
        print(f"📊 Datenbankinhalt:")
        print(f"   - Domains: {domain_count}")
        print(f"   - Employment: {employment_count}")
        print(f"   - Education: {education_count}")
        
        return True, (domain_count, employment_count, education_count)
        
    except Exception as e:
        print(f"❌ MySQL-Verbindung fehlgeschlagen: {e}")
        print("💡 Überprüfe MySQL-Konfiguration und Datenbank")
        return False, None

def test_vector_store_setup():
    """Test vector store setup"""
    print_step(4, "Teste Vector Store Setup")
    
    try:
        from qdrant_vector_store import QdrantVectorStore
        
        vector_store = QdrantVectorStore()
        vector_store.initialize()
        
        print("✅ Vector Store initialisiert")
        
        # Test data extraction
        print("📥 Extrahiere Test-Daten...")
        domains = vector_store.extract_domains_from_mysql()
        employment = vector_store.extract_employment_from_mysql()
        education = vector_store.extract_education_from_mysql()
        
        print(f"✅ Daten extrahiert:")
        print(f"   - {len(domains)} Domains")
        print(f"   - {len(employment)} Employment Records")
        print(f"   - {len(education)} Education Records")
        
        vector_store.close_connections()
        return True
        
    except Exception as e:
        print(f"❌ Vector Store Setup fehlgeschlagen: {e}")
        print(f"Details: {traceback.format_exc()}")
        return False

def test_qdrant_integration():
    """Test Qdrant integration module"""
    print_step(5, "Teste Qdrant Integration")
    
    try:
        from qdrant_integration import QdrantJobAnalyzer
        
        analyzer = QdrantJobAnalyzer()
        
        # Health check
        health = analyzer.health_check()
        print(f"📊 System Health:")
        print(f"   - Qdrant verfügbar: {health.get('qdrant_available', False)}")
        print(f"   - Initialisiert: {health.get('initialized', False)}")
        print(f"   - Model geladen: {health.get('model_loaded', False)}")
        
        if health.get('collections'):
            print(f"   - Collections:")
            for name, info in health['collections'].items():
                print(f"     * {name}: {info.get('points_count', 0)} Punkte")
        
        # Test job analysis if initialized
        if analyzer.is_initialized:
            print("\n🔍 Teste Job-Analyse...")
            
            test_job = "Laravel dashboard with real-time data visualization using Chart.js and Vue.js"
            result = analyzer.analyze_job_correlation(test_job)
            
            if result.enhanced_analysis:
                print("✅ Qdrant-Enhanced Analysis aktiv")
                correlation = result.correlation_analysis
                
                print(f"📊 Resultate:")
                print(f"   - Relevante Domains: {len(correlation.get('domains', []))}")
                print(f"   - Relevante Employment: {len(correlation.get('employment', []))}")
                print(f"   - Relevante Education: {len(correlation.get('education', []))}")
                
                # Show top domain
                if correlation.get('domains'):
                    top_domain = correlation['domains'][0]
                    print(f"   - Top Domain: {top_domain.get('domain', 'N/A')} (Score: {top_domain.get('relevance_score', 0):.2f})")
                
            else:
                print(f"⚠️  Fallback auf Legacy Analysis: {result.error_message}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration Test fehlgeschlagen: {e}")
        print(f"Details: {traceback.format_exc()}")
        return False

def test_enhanced_bidder():
    """Test enhanced bidder functionality"""
    print_step(6, "Teste Enhanced Bidder")
    
    try:
        from bidder_qdrant_patch import EnhancedBidder
        
        bidder = EnhancedBidder()
        
        test_job = """
        We need a modern web application with the following requirements:
        - Laravel backend with API development
        - Vue.js frontend with real-time features
        - Data visualization using Chart.js
        - MySQL database integration
        - Responsive design
        """
        
        print("🎯 Teste Bid-Generierung...")
        print(f"Job: {test_job.strip()[:100]}...")
        
        bid_result = bidder.generate_enhanced_bid("QUICK_START_TEST", test_job)
        
        print("✅ Bid erfolgreich generiert")
        
        # Show bid preview
        bid_teaser = bid_result.get('bid_teaser', {})
        print(f"\n📝 Bid Preview:")
        print(f"Greeting: {bid_teaser.get('greeting', 'N/A')}")
        print(f"Price: ${bid_teaser.get('estimated_price', 0)}")
        print(f"Days: {bid_teaser.get('estimated_days', 0)}")
        
        # Show analysis metadata
        metadata = bid_result.get('analysis_metadata', {})
        print(f"\n📊 Analysis Metadata:")
        print(f"Enhanced: {metadata.get('enhanced_analysis', False)}")
        print(f"Domains: {metadata.get('correlation_domains_count', 0)}")
        print(f"Employment: {metadata.get('correlation_employment_count', 0)}")
        print(f"Education: {metadata.get('correlation_education_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced Bidder Test fehlgeschlagen: {e}")
        print(f"Details: {traceback.format_exc()}")
        return False

def show_next_steps():
    """Show next steps for the user"""
    print_header("Nächste Schritte")
    
    print("🎉 Quick Start erfolgreich abgeschlossen!")
    print("\nWas kannst du jetzt tun:")
    print("\n1. 📚 Vollständige Integration:")
    print("   - Lese das QDRANT_VECTOR_STORE_README.md")
    print("   - Integriere in dein bestehendes bidder.py System")
    
    print("\n2. 🔧 Optimierungen:")
    print("   - Teste verschiedene Embedding-Modelle")
    print("   - Konfiguriere Performance-Settings")
    print("   - Implementiere Caching für häufige Suchen")
    
    print("\n3. 📊 Monitoring:")
    print("   - Nutze Qdrant Web UI: http://localhost:6333/dashboard")
    print("   - Implementiere Logging für Produktionsumgebung")
    print("   - Überwache Performance-Metriken")
    
    print("\n4. 🚀 Erweiterungen:")
    print("   - Füge weitere Datenquellen hinzu")
    print("   - Implementiere Real-time Updates")
    print("   - Erstelle Custom Embedding-Strategien")
    
    print("\n💡 Tipps:")
    print("   - Backup deine Qdrant-Daten regelmäßig")
    print("   - Teste neue Features in einer Kopie")
    print("   - Dokumentiere deine Anpassungen")

def main():
    """Main quick start function"""
    print_header("Qdrant Vector Store Quick Start")
    print(f"⏰ Gestartet: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test sequence
    tests = [
        ("Dependencies", check_dependencies),
        ("Qdrant Connection", check_qdrant_connection),
        ("MySQL Connection", check_mysql_connection),
        ("Vector Store Setup", test_vector_store_setup),
        ("Qdrant Integration", test_qdrant_integration),
        ("Enhanced Bidder", test_enhanced_bidder)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if test_name in ["Qdrant Connection", "MySQL Connection"]:
                success, data = test_func()
            else:
                success = test_func()
            
            results.append((test_name, success))
            
            if not success and test_name in ["Dependencies", "Qdrant Connection", "MySQL Connection"]:
                print(f"\n❌ Kritischer Fehler in {test_name}. Stoppe Quick Start.")
                break
                
        except KeyboardInterrupt:
            print(f"\n⏸️  Quick Start unterbrochen")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Unerwarteter Fehler in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print_header("Quick Start Zusammenfassung")
    
    for test_name, success in results:
        status = "✅ Erfolgreich" if success else "❌ Fehlgeschlagen"
        print(f"{status} - {test_name}")
    
    successful_tests = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    print(f"\n📊 Ergebnis: {successful_tests}/{total_tests} Tests erfolgreich")
    
    if successful_tests == total_tests:
        print("🎉 Alle Tests bestanden! System ist einsatzbereit.")
        show_next_steps()
    elif successful_tests >= 3:  # Basic functionality working
        print("⚠️  Grundfunktionalität verfügbar, aber einige erweiterte Features fehlen.")
        print("Überprüfe die fehlgeschlagenen Tests und folge den Anweisungen.")
    else:
        print("❌ Setup unvollständig. Überprüfe die Grundkonfiguration:")
        print("1. Qdrant Container läuft: docker ps | grep qdrant")
        print("2. MySQL Datenbank verfügbar und konfiguriert")
        print("3. Python Dependencies installiert: pip install -r requirements_qdrant.txt")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n⏸️  Quick Start beendet")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Kritischer Fehler: {e}")
        print(f"Details: {traceback.format_exc()}")
        sys.exit(1)