#!/usr/bin/env python3
"""
Bidder Integration mit konfigurierbarem Correlation Manager
=========================================================

Zeigt, wie Sie den CorrelationManager in Ihren bestehenden bidder.py integrieren
können, um zwischen SQL, Vector Store und Hybrid-Modi zu wechseln.

EINFACHE INTEGRATION - NUR WENIGE ZEILEN ÄNDERN:
"""

import json
import logging
from typing import Dict, Any, Optional

def integrate_configurable_correlation_in_bidder():
    """
    Beispiel für die Integration des konfigurierbaren CorrelationManagers
    in den bestehenden bidder.py
    """
    
    print("🔧 Configurable Correlation Integration Example")
    print("=" * 60)
    
    # 1. IMPORT AM ANFANG DER DATEI HINZUFÜGEN
    print("📝 Schritt 1: Import hinzufügen")
    print("""
# Am Anfang Ihrer bidder.py hinzufügen:
try:
    from correlation_manager import CorrelationManager
    CORRELATION_MANAGER_AVAILABLE = True
    print("✅ Configurable CorrelationManager verfügbar")
except ImportError:
    CORRELATION_MANAGER_AVAILABLE = False
    print("⚠️  Fallback auf bestehende Korrelationsanalyse")
""")

    # 2. KLASSENMODIFIKATION
    print("\n📝 Schritt 2: Bidder Klasse erweitern")
    print("""
# In Ihrer Bidder Klasse __init__ Methode:
class YourExistingBidder:
    def __init__(self):
        # ... Ihr bestehender Code ...
        
        # NEU: CorrelationManager initialisieren
        if CORRELATION_MANAGER_AVAILABLE:
            self.correlation_manager = CorrelationManager()
            self.logger.info("🚀 CorrelationManager initialisiert")
        else:
            self.correlation_manager = None
            self.logger.info("📊 Using legacy correlation analysis")
""")

    # 3. METHODEN-ERSETZUNG
    print("\n📝 Schritt 3: Korrelationsanalyse ersetzen")
    print("""
# ALTE METHODE (wo auch immer sie in Ihrem Code steht):
# def analyze_project_correlation(self, job_description):
#     # Ihre bestehende Logik
#     return correlation_analysis

# NEUE METHODE - ERSETZT DIE ALTE:
def analyze_project_correlation(self, job_description, project_data=None):
    \"\"\"
    Configurable correlation analysis - automatischer Switch basierend auf config.py
    \"\"\"
    
    if self.correlation_manager:
        # Verwende konfigurierbaren Manager
        result = self.correlation_manager.analyze_job_correlation(
            job_description, project_data
        )
        
        # Log welcher Modus verwendet wurde
        self.logger.info(f"📊 Correlation analysis: {result.analysis_mode} "
                        f"in {result.execution_time_ms:.1f}ms")
        
        if result.fallback_used:
            self.logger.info(f"⚠️  Fallback used: {result.fallback_used}")
        
        return result.correlation_analysis
    else:
        # Fallback auf bestehende Methode
        return self.legacy_correlation_analysis(job_description)

def legacy_correlation_analysis(self, job_description):
    \"\"\"Ihre bestehende Korrelationsanalyse - unverändert lassen\"\"\"
    # HIER IST IHR BESTEHENDER CODE
    # Keine Änderungen nötig!
    pass
""")

    # Test der Integration
    print("\n🧪 Testing the Integration:")
    print("=" * 30)
    
    # Simuliere die Integration
    try:
        from correlation_manager import CorrelationManager
        
        manager = CorrelationManager()
        
        # Test verschiedene Job-Beschreibungen
        test_jobs = [
            "Laravel dashboard with real-time data visualization",
            "Vue.js e-commerce platform with payment integration",
            "Python machine learning API for financial trading"
        ]
        
        print(f"Teste mit {len(test_jobs)} Jobs...")
        
        for i, job_desc in enumerate(test_jobs, 1):
            print(f"\n  Test {i}: {job_desc[:40]}...")
            
            result = manager.analyze_job_correlation(job_desc)
            
            print(f"    ✅ Mode: {result.analysis_mode}")
            print(f"    ⏱️  Time: {result.execution_time_ms:.1f}ms")
            print(f"    📊 Enhanced: {result.enhanced_analysis}")
            
            if result.fallback_used:
                print(f"    ⚠️  Fallback: {result.fallback_used}")
        
        # Performance Stats
        stats = manager.get_performance_stats()
        print(f"\n📈 Performance Stats:")
        print(f"  - Total Calls: {stats['total_calls']}")
        print(f"  - Vector Store: {stats['vector_store_calls']}")
        print(f"  - SQL: {stats['sql_calls']}")
        print(f"  - Legacy: {stats['legacy_calls']}")
        print(f"  - Cache Hits: {stats['cache_hits']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def show_configuration_options():
    """Zeigt verfügbare Konfigurationsoptionen"""
    
    print("\n🔧 Konfigurationsoptionen in config.py:")
    print("=" * 50)
    
    print("""
# HAUPT-SWITCH: Wählen Sie Ihren Analysemodus
CORRELATION_ANALYSIS_MODE = 'VECTOR_STORE'  # Optionen: 'SQL', 'VECTOR_STORE', 'HYBRID'

# Vector Store Konfiguration
VECTOR_STORE_CONFIG = {
    'USE_LITE_VERSION': True,           # True = Keyword-based, False = Neural Embeddings
    'QDRANT_HOST': 'localhost',
    'QDRANT_PORT': 6333,
    'ENABLE_FALLBACK_TO_SQL': True,     # Fallback bei Vector Store Fehlern
    'ENABLE_FALLBACK_TO_LEGACY': True,  # Ultimate Fallback
    'MAX_DOMAINS': 5,                   # Anzahl Domains in Ergebnissen
    'MAX_EMPLOYMENT': 3,                # Anzahl Employment Records
    'MAX_EDUCATION': 3,                 # Anzahl Education Records
    'ENABLE_CACHING': True,             # Result Caching
    'CACHE_TTL_SECONDS': 3600,          # Cache Lebensdauer
}

# Debug und Performance
DEBUG_VECTOR_STORE = True              # Debug Logging
LOG_ANALYSIS_PERFORMANCE = True        # Performance Metriken
USE_LEGACY_CORRELATION = False         # Komplett deaktivieren (Notfall)
""")

def show_mode_comparison():
    """Vergleich der verschiedenen Modi"""
    
    print("\n📊 Modi-Vergleich:")
    print("=" * 30)
    
    modes = {
        'SQL': {
            'description': 'Direkte MySQL-basierte Analyse',
            'speed': '⚡ Sehr schnell (10-50ms)',
            'accuracy': '📊 Gut für Keyword-Matching',
            'setup': '🟢 Einfach (MySQL nur)',
            'fallback': '📜 Legacy Analysis'
        },
        'VECTOR_STORE': {
            'description': 'Qdrant semantic similarity search',
            'speed': '🚀 Schnell (50-100ms)',
            'accuracy': '🎯 Exzellent für semantische Ähnlichkeit',
            'setup': '🟡 Mittel (Qdrant + MySQL)',
            'fallback': '🗄️ SQL → Legacy'
        },
        'HYBRID': {
            'description': 'Kombiniert SQL und Vector Store',
            'speed': '⏳ Langsamer (100-200ms)',
            'accuracy': '🏆 Beste Genauigkeit',
            'setup': '🔴 Komplex (beide Systeme)',
            'fallback': '🔄 Beste verfügbare Methode'
        }
    }
    
    for mode, info in modes.items():
        print(f"\n🔹 **{mode}**")
        for key, value in info.items():
            print(f"  {key.capitalize()}: {value}")

def demonstrate_runtime_switching():
    """Zeigt, wie zur Laufzeit zwischen Modi gewechselt werden kann"""
    
    print("\n🔄 Runtime Mode Switching:")
    print("=" * 35)
    
    print("""
# Sie können zur Laufzeit den Modus ändern:
from correlation_manager import CorrelationManager

manager = CorrelationManager()

# Mode 1: Vector Store
manager.analysis_mode = 'VECTOR_STORE'
result1 = manager.analyze_job_correlation(job_description)

# Mode 2: SQL  
manager.analysis_mode = 'SQL'
result2 = manager.analyze_job_correlation(job_description)

# Mode 3: Hybrid
manager.analysis_mode = 'HYBRID'
result3 = manager.analyze_job_correlation(job_description)

# Vergleiche Ergebnisse
print(f"Vector Store: {len(result1.correlation_analysis['domains'])} domains")
print(f"SQL: {len(result2.correlation_analysis['domains'])} domains")  
print(f"Hybrid: {len(result3.correlation_analysis['domains'])} domains")
""")

def create_bidder_patch_example():
    """Erstellt ein vollständiges Beispiel für bidder.py Anpassung"""
    
    print("\n📝 Vollständiges bidder.py Patch-Beispiel:")
    print("=" * 50)
    
    patch_content = '''
# =============================================================================
# BIDDER.PY PATCH - Configurable Correlation Analysis
# =============================================================================
# Fügen Sie diese Änderungen in Ihre bestehende bidder.py ein:

# 1. IMPORTS (am Anfang der Datei)
try:
    from correlation_manager import CorrelationManager
    CORRELATION_MANAGER_AVAILABLE = True
except ImportError:
    CORRELATION_MANAGER_AVAILABLE = False

# 2. BIDDER KLASSE INIT (erweitern Sie Ihre __init__ Methode)
def __init__(self):
    # ... Ihr bestehender Code ...
    
    # Configurable Correlation Manager
    if CORRELATION_MANAGER_AVAILABLE:
        self.correlation_manager = CorrelationManager()
        self.logger.info("🚀 Configurable CorrelationManager initialized")
        
        # Health check
        health = self.correlation_manager.health_check()
        self.logger.info(f"📊 Analysis mode: {health['analysis_mode']}")
    else:
        self.correlation_manager = None

# 3. KORRELATIONSANALYSE METHODE (ersetzen Sie Ihre bestehende)
def analyze_project_correlation(self, job_description, project_data=None):
    """
    Configurable correlation analysis
    Automatischer Switch zwischen SQL/Vector Store/Hybrid basierend auf config.py
    """
    
    if self.correlation_manager:
        try:
            # Verwende konfigurierbaren Manager
            result = self.correlation_manager.analyze_job_correlation(
                job_description, project_data
            )
            
            # Performance Logging
            self.logger.info(
                f"📊 Correlation: {result.analysis_mode} "
                f"({result.execution_time_ms:.1f}ms) "
                f"Enhanced: {result.enhanced_analysis}"
            )
            
            if result.fallback_used:
                self.logger.warning(f"⚠️  Fallback used: {result.fallback_used}")
            
            if result.error_message:
                self.logger.warning(f"⚠️  Error: {result.error_message}")
            
            return result.correlation_analysis
            
        except Exception as e:
            self.logger.error(f"Configurable correlation failed: {e}")
            # Fallback to legacy
            return self.legacy_correlation_analysis(job_description)
    else:
        # Fallback wenn Manager nicht verfügbar
        return self.legacy_correlation_analysis(job_description)

def legacy_correlation_analysis(self, job_description):
    """
    Ihre bestehende Korrelationsanalyse
    KEINE ÄNDERUNGEN HIER NÖTIG!
    """
    # Ihr bestehender Code bleibt unverändert
    pass

# 4. OPTIONAL: Performance Monitoring
def get_correlation_stats(self):
    """Gibt Correlation Performance Statistiken zurück"""
    if self.correlation_manager:
        return self.correlation_manager.get_performance_stats()
    return {"legacy_mode": True}

# =============================================================================
# USAGE: Keine weiteren Änderungen nötig!
# =============================================================================
# Der Rest Ihres bidder.py Codes bleibt komplett unverändert.
# Die Korrelationsanalyse wird automatisch basierend auf config.py ausgeführt.
'''
    
    print(patch_content)

if __name__ == "__main__":
    print("🔧 Bidder Configuration Integration Guide")
    print("=" * 60)
    
    # Test Integration
    success = integrate_configurable_correlation_in_bidder()
    
    if success:
        print("\n✅ Integration Test erfolgreich!")
        
        # Zeige zusätzliche Informationen
        show_configuration_options()
        show_mode_comparison()
        demonstrate_runtime_switching()
        create_bidder_patch_example()
        
        print("\n🎉 Setup Complete!")
        print("\nNächste Schritte:")
        print("1. Kopieren Sie das Patch in Ihre bidder.py")
        print("2. Konfigurieren Sie CORRELATION_ANALYSIS_MODE in config.py")
        print("3. Testen Sie mit verschiedenen Modi")
        print("4. Überwachen Sie Performance mit get_correlation_stats()")
        
    else:
        print("\n❌ Integration Test fehlgeschlagen")
        print("Überprüfen Sie Dependencies und Konfiguration")
        
    print(f"\n📊 Aktueller Modus aus config.py:")
    try:
        from config import CORRELATION_ANALYSIS_MODE
        print(f"    CORRELATION_ANALYSIS_MODE = '{CORRELATION_ANALYSIS_MODE}'")
    except ImportError:
        print("    config.py nicht gefunden - verwende Standard: 'VECTOR_STORE'")