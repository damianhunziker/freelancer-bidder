#!/usr/bin/env python3
"""
Qdrant Integration Module for Freelancer Bidder
=============================================

This module provides enhanced job correlation analysis using Qdrant vector search.
It can be integrated into the existing bidder.py workflow to improve project matching.

Usage:
    from qdrant_integration import QdrantJobAnalyzer
    
    analyzer = QdrantJobAnalyzer()
    correlation = analyzer.analyze_job_correlation(job_description)
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import traceback

try:
    from qdrant_client import QdrantClient
    from sentence_transformers import SentenceTransformer
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    print("⚠️  Qdrant dependencies not installed. Run: pip install qdrant-client sentence-transformers")

@dataclass
class JobAnalysisResult:
    """Results from Qdrant-enhanced job analysis"""
    correlation_analysis: Dict[str, Any]
    enhanced_analysis: bool = True
    error_message: Optional[str] = None

class QdrantJobAnalyzer:
    """Enhanced job analyzer using Qdrant vector search"""
    
    def __init__(self, 
                 qdrant_host: str = 'localhost', 
                 qdrant_port: int = 6333,
                 fallback_to_legacy: bool = True):
        """
        Initialize Qdrant job analyzer
        
        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port  
            fallback_to_legacy: Whether to fall back to legacy analysis if Qdrant fails
        """
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.fallback_to_legacy = fallback_to_legacy
        
        self.client = None
        self.model = None
        self.is_initialized = False
        
        self.logger = logging.getLogger(__name__)
        
        # Collection names
        self.collections = {
            'domains': 'freelancer_domains',
            'employment': 'freelancer_employment', 
            'education': 'freelancer_education'
        }
        
        # Try to initialize
        if QDRANT_AVAILABLE:
            self._initialize()
    
    def _initialize(self) -> bool:
        """Initialize Qdrant client and embedding model"""
        try:
            self.logger.info("Initializing Qdrant job analyzer...")
            
            # Connect to Qdrant
            self.client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            
            # Test connection
            collections = self.client.get_collections()
            self.logger.info(f"Connected to Qdrant. Found {len(collections.collections)} collections")
            
            # Load embedding model
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            self.logger.info("Loaded embedding model")
            
            # Check if required collections exist
            available_collections = [col.name for col in collections.collections]
            missing_collections = []
            for collection_name in self.collections.values():
                if collection_name not in available_collections:
                    missing_collections.append(collection_name)
            
            if missing_collections:
                self.logger.warning(f"Missing collections: {missing_collections}")
                self.logger.warning("Run qdrant_vector_store.py to populate collections")
                return False
            
            self.is_initialized = True
            self.logger.info("✅ Qdrant analyzer initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Qdrant: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _search_similar_items(self, 
                             job_description: str, 
                             collection_name: str, 
                             limit: int = 5) -> List[Dict]:
        """Generic function to search similar items in any collection"""
        if not self.is_initialized:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.model.encode(job_description).tolist()
            
            # Search in Qdrant
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit
            )
            
            return [
                {
                    **result.payload,
                    "score": result.score,
                    "relevance_score": min(result.score * 100, 100)
                }
                for result in results
            ]
            
        except Exception as e:
            self.logger.error(f"Error searching in {collection_name}: {e}")
            return []
    
    def analyze_job_correlation(self, 
                              job_description: str, 
                              project_data: Optional[Dict] = None) -> JobAnalysisResult:
        """
        Enhanced job correlation analysis using Qdrant
        
        Args:
            job_description: The job description to analyze
            project_data: Optional project data from the original system
            
        Returns:
            JobAnalysisResult with enhanced correlation analysis
        """
        
        if not QDRANT_AVAILABLE or not self.is_initialized:
            self.logger.warning("Qdrant not available, falling back to legacy analysis")
            if self.fallback_to_legacy:
                return self._legacy_analysis(job_description, project_data)
            else:
                return JobAnalysisResult(
                    correlation_analysis={},
                    enhanced_analysis=False,
                    error_message="Qdrant not available"
                )
        
        try:
            self.logger.info("Performing Qdrant-enhanced job analysis...")
            
            # Search similar domains
            similar_domains = self._search_similar_items(
                job_description, 
                self.collections['domains'], 
                limit=5
            )
            
            # Search similar employment
            similar_employment = self._search_similar_items(
                job_description,
                self.collections['employment'],
                limit=3
            )
            
            # Search similar education  
            similar_education = self._search_similar_items(
                job_description,
                self.collections['education'],
                limit=3
            )
            
            # Format results to match existing structure
            correlation_analysis = {
                "domains": self._format_domain_results(similar_domains),
                "employment": self._format_employment_results(similar_employment),
                "education": self._format_education_results(similar_education)
            }
            
            self.logger.info(f"✅ Enhanced analysis complete: {len(similar_domains)} domains, "
                           f"{len(similar_employment)} employment, {len(similar_education)} education")
            
            return JobAnalysisResult(
                correlation_analysis=correlation_analysis,
                enhanced_analysis=True
            )
            
        except Exception as e:
            self.logger.error(f"Error in Qdrant analysis: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            if self.fallback_to_legacy:
                self.logger.info("Falling back to legacy analysis")
                return self._legacy_analysis(job_description, project_data)
            else:
                return JobAnalysisResult(
                    correlation_analysis={},
                    enhanced_analysis=False,
                    error_message=str(e)
                )
    
    def _format_domain_results(self, domains: List[Dict]) -> List[Dict]:
        """Format domain results to match existing structure"""
        formatted_domains = []
        
        for domain in domains:
            tags = domain.get('tags', [])
            formatted_tags = []
            
            for tag in tags[:5]:  # Top 5 tags
                formatted_tags.append({
                    "name": tag,
                    "relevance_score": round(domain['relevance_score'] / 100, 2)
                })
            
            formatted_domain = {
                "domain": domain.get('domain_name', ''),
                "title": domain.get('title', domain.get('domain_name', '')),
                "relevance_score": round(domain['relevance_score'] / 100, 2),
                "tags": formatted_tags
            }
            formatted_domains.append(formatted_domain)
        
        return formatted_domains
    
    def _format_employment_results(self, employment: List[Dict]) -> List[Dict]:
        """Format employment results to match existing structure"""
        formatted_employment = []
        
        for emp in employment:
            description = emp.get('description', '')
            if len(description) > 200:
                description = description[:200] + "..."
            
            formatted_emp = {
                "company": emp.get('company_name', ''),
                "position": emp.get('position', ''),
                "relevance_score": round(emp['relevance_score'] / 100, 2),
                "description": description
            }
            formatted_employment.append(formatted_emp)
        
        return formatted_employment
    
    def _format_education_results(self, education: List[Dict]) -> List[Dict]:
        """Format education results to match existing structure"""
        formatted_education = []
        
        for edu in education:
            description = edu.get('description', '')
            if len(description) > 200:
                description = description[:200] + "..."
            
            formatted_edu = {
                "institution": edu.get('institution', ''),
                "title": edu.get('title', ''),
                "relevance_score": round(edu['relevance_score'] / 100, 2),
                "description": description
            }
            formatted_education.append(formatted_edu)
        
        return formatted_education
    
    def _legacy_analysis(self, 
                        job_description: str, 
                        project_data: Optional[Dict] = None) -> JobAnalysisResult:
        """
        Fallback to legacy correlation analysis when Qdrant is not available
        This can be enhanced to use the existing MySQL-based logic
        """
        self.logger.info("Using legacy correlation analysis")
        
        # Placeholder for legacy analysis
        # You can integrate your existing correlation logic here
        correlation_analysis = {
            "domains": [
                {
                    "domain": "legacy-analysis.com",
                    "title": "Legacy Analysis Fallback",
                    "relevance_score": 0.7,
                    "tags": [
                        {
                            "name": "Fallback Mode",
                            "relevance_score": 0.7
                        }
                    ]
                }
            ],
            "employment": [
                {
                    "company": "Legacy Analysis Co.",
                    "position": "Fallback Developer",
                    "relevance_score": 0.7,
                    "description": "Using legacy correlation analysis as Qdrant is not available"
                }
            ],
            "education": [
                {
                    "institution": "Legacy Academy",
                    "title": "Fallback Analysis Course",
                    "relevance_score": 0.7,
                    "description": "Basic correlation analysis without vector search"
                }
            ]
        }
        
        return JobAnalysisResult(
            correlation_analysis=correlation_analysis,
            enhanced_analysis=False,
            error_message="Using legacy analysis - Qdrant not available"
        )
    
    def search_domains_by_tags(self, tags: List[str], limit: int = 10) -> List[Dict]:
        """Search domains by specific tags"""
        if not self.is_initialized:
            return []
        
        # Combine tags into search query
        query = " ".join(tags)
        return self._search_similar_items(query, self.collections['domains'], limit)
    
    def get_domain_details(self, domain_name: str) -> Optional[Dict]:
        """Get detailed information about a specific domain"""
        if not self.is_initialized:
            return None
        
        try:
            # Search for exact domain match
            results = self.client.scroll(
                collection_name=self.collections['domains'],
                scroll_filter={
                    "must": [
                        {
                            "key": "domain_name",
                            "match": {"value": domain_name}
                        }
                    ]
                },
                limit=1
            )
            
            if results[0]:  # results is tuple (points, next_page_offset)
                return results[0][0].payload
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting domain details: {e}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the Qdrant integration"""
        status = {
            "qdrant_available": QDRANT_AVAILABLE,
            "initialized": self.is_initialized,
            "collections": {},
            "model_loaded": self.model is not None
        }
        
        if self.is_initialized and self.client:
            try:
                collections = self.client.get_collections()
                for collection in collections.collections:
                    collection_info = self.client.get_collection(collection.name)
                    status["collections"][collection.name] = {
                        "points_count": collection_info.points_count,
                        "status": collection_info.status
                    }
            except Exception as e:
                status["error"] = str(e)
        
        return status

# Convenience function for direct usage
def analyze_job_with_qdrant(job_description: str, 
                          project_data: Optional[Dict] = None) -> JobAnalysisResult:
    """
    Convenience function to analyze a job using Qdrant
    
    Args:
        job_description: Job description to analyze
        project_data: Optional project data
        
    Returns:
        JobAnalysisResult with correlation analysis
    """
    analyzer = QdrantJobAnalyzer()
    return analyzer.analyze_job_correlation(job_description, project_data)

# Test function
def test_qdrant_integration():
    """Test the Qdrant integration"""
    print("🧪 Testing Qdrant Integration...")
    
    analyzer = QdrantJobAnalyzer()
    
    # Health check
    health = analyzer.health_check()
    print(f"📊 Health Status: {json.dumps(health, indent=2)}")
    
    if not analyzer.is_initialized:
        print("❌ Qdrant not initialized. Run setup_qdrant.sh and qdrant_vector_store.py first")
        return
    
    # Test job analysis
    test_job = "Laravel dashboard with real-time data visualization using Chart.js and Vue.js"
    print(f"\n🔍 Testing with job: {test_job}")
    
    result = analyzer.analyze_job_correlation(test_job)
    
    if result.enhanced_analysis:
        print("✅ Enhanced analysis successful!")
        print(f"📋 Found {len(result.correlation_analysis.get('domains', []))} relevant domains")
        print(f"📋 Found {len(result.correlation_analysis.get('employment', []))} relevant employment records")
        print(f"📋 Found {len(result.correlation_analysis.get('education', []))} relevant education records")
    else:
        print(f"⚠️  Enhanced analysis not available: {result.error_message}")
    
    print("\n🎯 Sample Results:")
    print(json.dumps(result.correlation_analysis, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_qdrant_integration()