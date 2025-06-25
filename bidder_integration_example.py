#!/usr/bin/env python3
"""
Bidder Integration Example - Qdrant Lite
========================================

Einfaches Beispiel für die Integration der Qdrant Lite Funktionalität 
in den bestehenden Bidder-Workflow.

Diese Datei zeigt, wie Sie mit wenigen Zeilen Code die semantische Suche
in Ihren bestehenden bidder.py integrieren können.
"""

import json
import logging

def integrate_qdrant_lite_into_bidder():
    """
    Beispiel für die Integration in bidder.py
    
    Ersetzen Sie in Ihrer bidder.py die bestehende Korrelationsanalyse
    durch diese Enhanced-Version.
    """
    
    # 1. Import am Anfang der Datei hinzufügen:
    try:
        from qdrant_lite_integration import QdrantLiteAnalyzer
        QDRANT_LITE_AVAILABLE = True
        print("✅ Qdrant Lite verfügbar")
    except ImportError:
        QDRANT_LITE_AVAILABLE = False
        print("⚠️  Qdrant Lite nicht verfügbar - Fallback auf Legacy")

    # 2. Analyzer als Klassenattribut initialisieren:
    class EnhancedBidder:
        def __init__(self):
            self.logger = logging.getLogger(__name__)
            
            if QDRANT_LITE_AVAILABLE:
                self.qdrant_analyzer = QdrantLiteAnalyzer()
                self.logger.info("Qdrant Lite Analyzer initialisiert")
            else:
                self.qdrant_analyzer = None

        def analyze_project_correlation(self, job_description, project_data=None):
            """
            DIESE METHODE ERSETZT IHRE BESTEHENDE KORRELATIONSANALYSE
            
            Drop-in Replacement für die bestehende correlation analysis Funktion
            """
            
            if self.qdrant_analyzer and self.qdrant_analyzer.is_initialized:
                # Verwende Enhanced Qdrant Lite Analysis
                self.logger.info("🚀 Using Qdrant Lite Enhanced Analysis")
                result = self.qdrant_analyzer.analyze_job_correlation(job_description, project_data)
                
                if result.enhanced_analysis:
                    self.logger.info("✅ Enhanced analysis successful")
                    return result.correlation_analysis
                else:
                    self.logger.warning(f"Enhanced analysis failed: {result.error_message}")
                    # Fall back to legacy
                    return self._legacy_correlation_analysis(job_description)
            else:
                # Verwende Legacy Analysis
                self.logger.info("📊 Using Legacy Analysis")
                return self._legacy_correlation_analysis(job_description)

        def _legacy_correlation_analysis(self, job_description):
            """Ihre bestehende Korrelationsanalyse - unverändert lassen"""
            # HIER IST IHR BESTEHENDER CODE
            correlation_analysis = {
                "domains": [
                    {
                        "domain": "reishauer.com",
                        "title": "reishauer.com", 
                        "relevance_score": 0.85,
                        "tags": [
                            {"name": "Data Visualization", "relevance_score": 0.9},
                            {"name": "Laravel Development", "relevance_score": 0.8}
                        ]
                    }
                ],
                "employment": [
                    {
                        "company": "BlueMouse GmbH",
                        "position": "Geschäftsleitung, Lead Developer",
                        "relevance_score": 0.8,
                        "description": "Lead developer role involved dashboard development"
                    }
                ],
                "education": [
                    {
                        "institution": "New York Institute of Finance",
                        "title": "Introduction to Trading, Machine Learning & GCP",
                        "relevance_score": 0.85,
                        "description": "Course covered real-time data analysis"
                    }
                ]
            }
            return correlation_analysis

    return EnhancedBidder

def simple_usage_example():
    """
    Einfaches Beispiel für die Verwendung
    """
    print("📋 Einfaches Verwendungsbeispiel:")
    
    # Direkte Verwendung ohne Klasse
    from qdrant_lite_integration import QdrantLiteAnalyzer
    
    analyzer = QdrantLiteAnalyzer()
    
    test_job = "Laravel dashboard development with real-time charts and Vue.js frontend"
    print(f"🔍 Analysiere Job: {test_job}")
    
    result = analyzer.analyze_job_correlation(test_job)
    
    if result.enhanced_analysis:
        print("✅ Enhanced Analysis verwendet")
        domains = result.correlation_analysis.get('domains', [])
        print(f"📊 Gefunden: {len(domains)} relevante Domains")
        
        # Zeige Top Domain
        if domains:
            top_domain = domains[0]
            print(f"🏆 Top Domain: {top_domain['domain']} (Score: {top_domain['relevance_score']})")
            
    else:
        print(f"⚠️  Legacy Analysis: {result.error_message}")

def integration_in_existing_file():
    """
    Zeigt die konkreten Änderungen für bidder.py
    """
    print("\n📝 Konkrete Änderungen für bidder.py:")
    print("=" * 50)
    
    print("""
# SCHRITT 1: Import am Anfang der Datei hinzufügen
try:
    from qdrant_lite_integration import QdrantLiteAnalyzer
    QDRANT_LITE_AVAILABLE = True
except ImportError:
    QDRANT_LITE_AVAILABLE = False

# SCHRITT 2: In der Bidder Klasse __init__ hinzufügen:
def __init__(self):
    # ... bestehender Code ...
    
    if QDRANT_LITE_AVAILABLE:
        self.qdrant_analyzer = QdrantLiteAnalyzer()
    else:
        self.qdrant_analyzer = None

# SCHRITT 3: Bestehende Korrelationsanalyse ersetzen
# VORHER (um Zeile 900-1000 in Ihrem Code):
# correlation_analysis = analyze_project_correlation(job_description)

# NACHHER:
def enhanced_correlation_analysis(self, job_description):
    if self.qdrant_analyzer and self.qdrant_analyzer.is_initialized:
        result = self.qdrant_analyzer.analyze_job_correlation(job_description)
        if result.enhanced_analysis:
            return result.correlation_analysis
    
    # Fallback auf bestehende Analyse
    return self.legacy_correlation_analysis(job_description)

# SCHRITT 4: Verwenden Sie enhanced_correlation_analysis statt der alten Funktion
correlation_analysis = self.enhanced_correlation_analysis(job_description)
""")

def test_complete_integration():
    """
    Vollständiger Test der Integration
    """
    print("\n🧪 Vollständiger Integrationstest:")
    print("=" * 40)
    
    try:
        # Erstelle Enhanced Bidder
        EnhancedBidder = integrate_qdrant_lite_into_bidder()
        bidder = EnhancedBidder()
        
        # Test verschiedene Job-Beschreibungen
        test_jobs = [
            "Laravel e-commerce platform with payment integration",
            "Vue.js dashboard with real-time data visualization", 
            "Python machine learning system for trading",
            "React Native mobile app with REST API backend"
        ]
        
        print(f"Teste {len(test_jobs)} verschiedene Job-Beschreibungen:")
        
        for i, job_desc in enumerate(test_jobs, 1):
            print(f"\n  Test {i}: {job_desc[:50]}...")
            
            correlation = bidder.analyze_project_correlation(job_desc)
            
            domains = correlation.get('domains', [])
            employment = correlation.get('employment', [])
            education = correlation.get('education', [])
            
            print(f"    📊 Ergebnis: {len(domains)} Domains, {len(employment)} Employment, {len(education)} Education")
            
            if domains:
                top_domain = domains[0]
                print(f"    🏆 Top: {top_domain.get('domain', 'N/A')} (Score: {top_domain.get('relevance_score', 0)})")
        
        print("\n✅ Integration Test erfolgreich!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration Test fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Qdrant Lite Integration Example")
    print("=" * 50)
    
    # Einfaches Beispiel
    simple_usage_example()
    
    # Integration in bestehende Datei
    integration_in_existing_file()
    
    # Vollständiger Test
    if test_complete_integration():
        print("\n🎉 Integration ist bereit!")
        print("\nNächste Schritte:")
        print("1. Kopieren Sie die Änderungen in Ihre bidder.py")
        print("2. Testen Sie mit: python3 bidder.py") 
        print("3. Überwachen Sie die Logs für 'Enhanced Analysis' Meldungen")
        print("4. Bei Problemen wird automatisch auf Legacy Analysis zurückgefallen")
    else:
        print("\n⚠️  Bitte überprüfen Sie die Konfiguration")