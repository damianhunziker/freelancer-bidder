#!/usr/bin/env python3
"""
Correlation Analysis Manager
===========================

Intelligenter Manager für Korrelationsanalyse mit konfigurierbarem Switch
zwischen SQL, Vector Store und Hybrid-Modi.

Verwendung:
    from correlation_manager import CorrelationManager
    
    manager = CorrelationManager()
    result = manager.analyze_job_correlation(job_description)
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import traceback

# Import configuration
try:
    from config import (
        CORRELATION_ANALYSIS_MODE, 
        VECTOR_STORE_CONFIG, 
        MYSQL_CONFIG,
        DEBUG_VECTOR_STORE,
        LOG_ANALYSIS_PERFORMANCE,
        USE_LEGACY_CORRELATION
    )
except ImportError:
    # Fallback configuration if config.py not found
    CORRELATION_ANALYSIS_MODE = 'VECTOR_STORE'
    VECTOR_STORE_CONFIG = {
        'USE_LITE_VERSION': True,
        'QDRANT_HOST': 'localhost',
        'QDRANT_PORT': 6333,
        'ENABLE_FALLBACK_TO_SQL': True,
        'ENABLE_FALLBACK_TO_LEGACY': True,
        'MAX_DOMAINS': 5,
        'MAX_EMPLOYMENT': 3,
        'MAX_EDUCATION': 3,
        'MIN_RELEVANCE_SCORE': 0.0,
        'ENABLE_CACHING': True,
        'CACHE_TTL_SECONDS': 3600,
    }
    MYSQL_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': 'dCTKBq@CV9$a50ZtpzSr@D7*7Q',
        'database': 'domain_analysis'
    }
    DEBUG_VECTOR_STORE = True
    LOG_ANALYSIS_PERFORMANCE = True
    USE_LEGACY_CORRELATION = False

@dataclass
class AnalysisResult:
    """Result from correlation analysis"""
    correlation_analysis: Dict[str, Any]
    analysis_mode: str
    execution_time_ms: float
    enhanced_analysis: bool = False
    error_message: Optional[str] = None
    fallback_used: Optional[str] = None

class CorrelationManager:
    """
    Intelligenter Manager für Korrelationsanalyse
    
    Wählt automatisch zwischen SQL, Vector Store und Legacy-Analyse
    basierend auf Konfiguration und Verfügbarkeit.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache = {}  # Simple in-memory cache
        
        # Initialize based on configuration
        self.analysis_mode = CORRELATION_ANALYSIS_MODE
        self.config = VECTOR_STORE_CONFIG
        
        if DEBUG_VECTOR_STORE:
            self.logger.setLevel(logging.DEBUG)
            self.logger.info(f"🔧 CorrelationManager initialized with mode: {self.analysis_mode}")
        
        # Initialize components
        self._init_vector_store()
        self._init_sql_analyzer()
        
        # Performance tracking
        self.performance_stats = {
            'vector_store_calls': 0,
            'sql_calls': 0,
            'legacy_calls': 0,
            'cache_hits': 0,
            'total_calls': 0
        }
    
    def _init_vector_store(self):
        """Initialize vector store analyzer"""
        self.vector_store_analyzer = None
        
        if self.analysis_mode in ['VECTOR_STORE', 'HYBRID']:
            try:
                if self.config.get('USE_LITE_VERSION', True):
                    from qdrant_lite_integration import QdrantLiteAnalyzer
                    self.vector_store_analyzer = QdrantLiteAnalyzer(
                        qdrant_host=self.config.get('QDRANT_HOST', 'localhost'),
                        qdrant_port=self.config.get('QDRANT_PORT', 6333),
                        fallback_to_legacy=self.config.get('ENABLE_FALLBACK_TO_LEGACY', True)
                    )
                    self.logger.info("✅ Qdrant Lite Analyzer initialized")
                else:
                    from qdrant_integration import QdrantJobAnalyzer
                    self.vector_store_analyzer = QdrantJobAnalyzer(
                        qdrant_host=self.config.get('QDRANT_HOST', 'localhost'),
                        qdrant_port=self.config.get('QDRANT_PORT', 6333),
                        fallback_to_legacy=self.config.get('ENABLE_FALLBACK_TO_LEGACY', True)
                    )
                    self.logger.info("✅ Qdrant Full Analyzer initialized")
                    
            except Exception as e:
                self.logger.warning(f"Vector store initialization failed: {e}")
                self.vector_store_analyzer = None
    
    def _init_sql_analyzer(self):
        """Initialize SQL-based analyzer"""
        self.sql_analyzer = None
        
        if self.analysis_mode in ['SQL', 'HYBRID'] or self.config.get('ENABLE_FALLBACK_TO_SQL', True):
            try:
                # Initialize SQL-based correlation analyzer
                self.sql_analyzer = SQLCorrelationAnalyzer(MYSQL_CONFIG)
                self.logger.info("✅ SQL Analyzer initialized")
            except Exception as e:
                self.logger.warning(f"SQL analyzer initialization failed: {e}")
                self.sql_analyzer = None
    
    def analyze_job_correlation(self, job_description: str, project_data: Optional[Dict] = None) -> AnalysisResult:
        """
        Hauptfunktion für Korrelationsanalyse
        
        Entscheidet basierend auf Konfiguration zwischen verschiedenen Analysemodi.
        """
        start_time = time.time()
        self.performance_stats['total_calls'] += 1
        
        if DEBUG_VECTOR_STORE:
            self.logger.debug(f"🔍 Analyzing job with mode: {self.analysis_mode}")
            self.logger.debug(f"📝 Job description: {job_description[:100]}...")
        
        # Check cache first
        if self.config.get('ENABLE_CACHING', True):
            cache_key = f"{self.analysis_mode}:{hash(job_description)}"
            if cache_key in self.cache:
                cache_result = self.cache[cache_key]
                if time.time() - cache_result['timestamp'] < self.config.get('CACHE_TTL_SECONDS', 3600):
                    self.performance_stats['cache_hits'] += 1
                    if DEBUG_VECTOR_STORE:
                        self.logger.debug("💾 Using cached result")
                    
                    execution_time = (time.time() - start_time) * 1000
                    return AnalysisResult(
                        correlation_analysis=cache_result['data'],
                        analysis_mode=f"{self.analysis_mode}_CACHED",
                        execution_time_ms=execution_time,
                        enhanced_analysis=cache_result.get('enhanced', False)
                    )
        
        # Perform analysis based on mode
        try:
            if USE_LEGACY_CORRELATION:
                result = self._legacy_analysis(job_description)
                result.analysis_mode = "LEGACY_FORCED"
            elif self.analysis_mode == 'VECTOR_STORE':
                result = self._vector_store_analysis(job_description, project_data)
            elif self.analysis_mode == 'SQL':
                result = self._sql_analysis(job_description, project_data)
            elif self.analysis_mode == 'HYBRID':
                result = self._hybrid_analysis(job_description, project_data)
            else:
                self.logger.warning(f"Unknown analysis mode: {self.analysis_mode}")
                result = self._legacy_analysis(job_description)
                result.analysis_mode = "LEGACY_FALLBACK"
            
            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time
            
            # Cache result
            if self.config.get('ENABLE_CACHING', True) and not result.error_message:
                cache_key = f"{self.analysis_mode}:{hash(job_description)}"
                self.cache[cache_key] = {
                    'data': result.correlation_analysis,
                    'timestamp': time.time(),
                    'enhanced': result.enhanced_analysis
                }
            
            # Log performance
            if LOG_ANALYSIS_PERFORMANCE:
                self.logger.info(f"📊 Analysis completed: {result.analysis_mode} in {execution_time:.1f}ms")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            if DEBUG_VECTOR_STORE:
                self.logger.error(traceback.format_exc())
            
            # Ultimate fallback
            fallback_result = self._legacy_analysis(job_description)
            fallback_result.analysis_mode = "EMERGENCY_FALLBACK"
            fallback_result.error_message = str(e)
            fallback_result.execution_time_ms = (time.time() - start_time) * 1000
            
            return fallback_result
    
    def _vector_store_analysis(self, job_description: str, project_data: Optional[Dict] = None) -> AnalysisResult:
        """Vector Store basierte Analyse"""
        self.performance_stats['vector_store_calls'] += 1
        
        if not self.vector_store_analyzer:
            if DEBUG_VECTOR_STORE:
                self.logger.debug("Vector store not available, falling back to SQL")
            
            if self.config.get('ENABLE_FALLBACK_TO_SQL', True):
                result = self._sql_analysis(job_description, project_data)
                result.fallback_used = "SQL"
                return result
            else:
                result = self._legacy_analysis(job_description)
                result.fallback_used = "LEGACY"
                return result
        
        try:
            if DEBUG_VECTOR_STORE:
                self.logger.debug("🚀 Using vector store analysis")
            
            vector_result = self.vector_store_analyzer.analyze_job_correlation(job_description, project_data)
            
            if vector_result.enhanced_analysis:
                return AnalysisResult(
                    correlation_analysis=vector_result.correlation_analysis,
                    analysis_mode="VECTOR_STORE",
                    execution_time_ms=0,  # Will be set by caller
                    enhanced_analysis=True
                )
            else:
                # Vector store analysis failed, try fallback
                if self.config.get('ENABLE_FALLBACK_TO_SQL', True):
                    result = self._sql_analysis(job_description, project_data)
                    result.fallback_used = "SQL"
                    result.error_message = vector_result.error_message
                    return result
                else:
                    result = self._legacy_analysis(job_description)
                    result.fallback_used = "LEGACY"
                    result.error_message = vector_result.error_message
                    return result
                    
        except Exception as e:
            self.logger.error(f"Vector store analysis failed: {e}")
            
            if self.config.get('ENABLE_FALLBACK_TO_SQL', True):
                result = self._sql_analysis(job_description, project_data)
                result.fallback_used = "SQL"
                result.error_message = str(e)
                return result
            else:
                result = self._legacy_analysis(job_description)
                result.fallback_used = "LEGACY"
                result.error_message = str(e)
                return result
    
    def _sql_analysis(self, job_description: str, project_data: Optional[Dict] = None) -> AnalysisResult:
        """SQL basierte Analyse"""
        self.performance_stats['sql_calls'] += 1
        
        if not self.sql_analyzer:
            if DEBUG_VECTOR_STORE:
                self.logger.debug("SQL analyzer not available, falling back to legacy")
            
            result = self._legacy_analysis(job_description)
            result.fallback_used = "LEGACY"
            return result
        
        try:
            if DEBUG_VECTOR_STORE:
                self.logger.debug("🗄️ Using SQL analysis")
            
            correlation_analysis = self.sql_analyzer.analyze_correlation(job_description, project_data)
            
            return AnalysisResult(
                correlation_analysis=correlation_analysis,
                analysis_mode="SQL",
                execution_time_ms=0,  # Will be set by caller
                enhanced_analysis=True
            )
            
        except Exception as e:
            self.logger.error(f"SQL analysis failed: {e}")
            
            result = self._legacy_analysis(job_description)
            result.fallback_used = "LEGACY"
            result.error_message = str(e)
            return result
    
    def _hybrid_analysis(self, job_description: str, project_data: Optional[Dict] = None) -> AnalysisResult:
        """Hybrid Analyse (kombiniert Vector Store und SQL)"""
        if DEBUG_VECTOR_STORE:
            self.logger.debug("🔀 Using hybrid analysis")
        
        # Try vector store first
        vector_result = self._vector_store_analysis(job_description, project_data)
        
        # Try SQL analysis
        sql_result = self._sql_analysis(job_description, project_data)
        
        # Combine results
        try:
            combined_analysis = self._combine_analyses(vector_result.correlation_analysis, sql_result.correlation_analysis)
            
            return AnalysisResult(
                correlation_analysis=combined_analysis,
                analysis_mode="HYBRID",
                execution_time_ms=0,  # Will be set by caller
                enhanced_analysis=vector_result.enhanced_analysis or sql_result.enhanced_analysis
            )
            
        except Exception as e:
            self.logger.error(f"Hybrid analysis combination failed: {e}")
            
            # Return best available result
            if vector_result.enhanced_analysis:
                vector_result.analysis_mode = "HYBRID_VECTOR_ONLY"
                return vector_result
            elif sql_result.enhanced_analysis:
                sql_result.analysis_mode = "HYBRID_SQL_ONLY"
                return sql_result
            else:
                result = self._legacy_analysis(job_description)
                result.analysis_mode = "HYBRID_FALLBACK"
                return result
    
    def _combine_analyses(self, vector_analysis: Dict, sql_analysis: Dict) -> Dict:
        """Kombiniert Vector Store und SQL Analyse Ergebnisse"""
        combined = {
            "domains": [],
            "employment": [],
            "education": []
        }
        
        # Combine domains (prioritize vector store, add unique SQL results)
        vector_domains = vector_analysis.get('domains', [])
        sql_domains = sql_analysis.get('domains', [])
        
        combined['domains'] = vector_domains[:3]  # Top 3 from vector store
        
        # Add unique SQL domains
        vector_domain_names = {d.get('domain', '') for d in vector_domains}
        for sql_domain in sql_domains[:2]:  # Top 2 from SQL
            if sql_domain.get('domain', '') not in vector_domain_names:
                combined['domains'].append(sql_domain)
        
        # Limit to max configured
        max_domains = self.config.get('MAX_DOMAINS', 5)
        combined['domains'] = combined['domains'][:max_domains]
        
        # Similar logic for employment and education
        combined['employment'] = vector_analysis.get('employment', [])[:self.config.get('MAX_EMPLOYMENT', 3)]
        combined['education'] = vector_analysis.get('education', [])[:self.config.get('MAX_EDUCATION', 3)]
        
        return combined
    
    def _legacy_analysis(self, job_description: str) -> AnalysisResult:
        """Legacy Fallback Analyse"""
        self.performance_stats['legacy_calls'] += 1
        
        if DEBUG_VECTOR_STORE:
            self.logger.debug("📜 Using legacy analysis")
        
        # Static legacy result (replace with your existing logic)
        legacy_correlation = {
            "domains": [
                {
                    "domain": "reishauer.com",
                    "title": "reishauer.com",
                    "relevance_score": 0.85,
                    "tags": [
                        {"name": "Data Visualization", "relevance_score": 0.9},
                        {"name": "Laravel Development", "relevance_score": 0.8},
                        {"name": "Plotly.js", "relevance_score": 0.85},
                        {"name": "Chart.js", "relevance_score": 0.8},
                        {"name": "Real-time Charts", "relevance_score": 0.9}
                    ]
                },
                {
                    "domain": "damianhunziker.net/en/dmx-bot-2",
                    "title": "damianhunziker.net/en/dmx-bot-2",
                    "relevance_score": 0.75,
                    "tags": [
                        {"name": "Real-time Trade Monitoring", "relevance_score": 0.8},
                        {"name": "CSV Export System", "relevance_score": 0.7},
                        {"name": "API Connections", "relevance_score": 0.8},
                        {"name": "Plotly Chart Generation", "relevance_score": 0.75}
                    ]
                }
            ],
            "employment": [
                {
                    "company": "BlueMouse GmbH",
                    "position": "Geschäftsleitung, Lead Developer",
                    "relevance_score": 0.8,
                    "description": "Lead developer role involved dashboard development with Laravel and real-time data visualization"
                },
                {
                    "company": "Vyftec Hunziker",
                    "position": "Geschäftsleitung, Lead Developer",
                    "relevance_score": 0.9,
                    "description": "Current role developing trading dashboards with real-time data feeds and API integrations"
                }
            ],
            "education": [
                {
                    "institution": "New York Institute of Finance",
                    "title": "Introduction to Trading, Machine Learning & GCP",
                    "relevance_score": 0.85,
                    "description": "Course covered real-time data analysis and visualization techniques for financial applications"
                }
            ]
        }
        
        return AnalysisResult(
            correlation_analysis=legacy_correlation,
            analysis_mode="LEGACY",
            execution_time_ms=0,  # Will be set by caller
            enhanced_analysis=False
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Gibt Performance-Statistiken zurück"""
        return {
            **self.performance_stats,
            'cache_size': len(self.cache),
            'analysis_mode': self.analysis_mode,
            'vector_store_available': self.vector_store_analyzer is not None,
            'sql_analyzer_available': self.sql_analyzer is not None
        }
    
    def health_check(self) -> Dict[str, Any]:
        """System Health Check"""
        health = {
            'correlation_manager': True,
            'analysis_mode': self.analysis_mode,
            'vector_store_analyzer': self.vector_store_analyzer is not None,
            'sql_analyzer': self.sql_analyzer is not None,
            'cache_enabled': self.config.get('ENABLE_CACHING', True),
            'performance_stats': self.get_performance_stats()
        }
        
        if self.vector_store_analyzer:
            try:
                vs_health = self.vector_store_analyzer.health_check()
                health['vector_store_health'] = vs_health
            except Exception as e:
                health['vector_store_health'] = {'error': str(e)}
        
        return health

class SQLCorrelationAnalyzer:
    """SQL-basierte Korrelationsanalyse"""
    
    def __init__(self, mysql_config: Dict[str, str]):
        self.mysql_config = mysql_config
        self.logger = logging.getLogger(__name__)
    
    def analyze_correlation(self, job_description: str, project_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Führt SQL-basierte Korrelationsanalyse durch"""
        
        # Hier würde Ihre bestehende SQL-basierte Logik stehen
        # Für jetzt verwenden wir ein Beispiel
        
        import mysql.connector
        
        try:
            conn = mysql.connector.connect(**self.mysql_config)
            cursor = conn.cursor(dictionary=True)
            
            # Beispiel: Suche Domains basierend auf Keywords im Job
            keywords = self._extract_keywords(job_description)
            
            # SQL Query für relevante Domains
            domain_query = """
                SELECT d.domain_name, d.title, 
                       GROUP_CONCAT(DISTINCT t.tag_name SEPARATOR ', ') as tags
                FROM domains d
                LEFT JOIN domain_tags dt ON d.id = dt.domain_id
                LEFT JOIN tags t ON dt.tag_id = t.id
                WHERE d.description LIKE %s OR d.title LIKE %s
                GROUP BY d.id, d.domain_name, d.title
                LIMIT 5
            """
            
            search_pattern = f"%{keywords[0]}%" if keywords else "%web%"
            cursor.execute(domain_query, (search_pattern, search_pattern))
            domains = cursor.fetchall()
            
            # Employment Query
            cursor.execute("SELECT * FROM employment ORDER BY start_date DESC LIMIT 3")
            employment = cursor.fetchall()
            
            # Education Query  
            cursor.execute("SELECT * FROM education ORDER BY start_date DESC LIMIT 3")
            education = cursor.fetchall()
            
            conn.close()
            
            # Format results
            formatted_domains = []
            for domain in domains:
                formatted_domains.append({
                    "domain": domain['domain_name'],
                    "title": domain['title'] or domain['domain_name'],
                    "relevance_score": 0.7,  # Static for now
                    "tags": [{"name": tag, "relevance_score": 0.7} 
                            for tag in (domain['tags'] or '').split(', ') if tag]
                })
            
            formatted_employment = []
            for emp in employment:
                formatted_employment.append({
                    "company": emp['company_name'],
                    "position": emp['position'],
                    "relevance_score": 0.7,
                    "description": emp['description'][:200] + "..." if len(emp['description']) > 200 else emp['description']
                })
            
            formatted_education = []
            for edu in education:
                formatted_education.append({
                    "institution": edu['institution'],
                    "title": edu['title'],
                    "relevance_score": 0.7,
                    "description": edu['description'][:200] + "..." if len(edu['description']) > 200 else edu['description']
                })
            
            return {
                "domains": formatted_domains,
                "employment": formatted_employment,
                "education": formatted_education
            }
            
        except Exception as e:
            self.logger.error(f"SQL analysis failed: {e}")
            raise
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrahiert Keywords aus Text"""
        import re
        
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter wichtige Tech-Keywords
        tech_keywords = ['laravel', 'vue', 'react', 'python', 'javascript', 'php', 'mysql', 'api', 'dashboard', 'chart']
        
        found_keywords = [word for word in words if word in tech_keywords]
        
        return found_keywords if found_keywords else ['web', 'development']

# Convenience function for easy usage
def analyze_job_correlation(job_description: str, project_data: Optional[Dict] = None) -> AnalysisResult:
    """Convenience function for job correlation analysis"""
    manager = CorrelationManager()
    return manager.analyze_job_correlation(job_description, project_data)