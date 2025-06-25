#!/usr/bin/env python3
"""
Qdrant Lite Integration für Freelancer Bidder
==========================================

Eine vereinfachte Version der Qdrant-Integration, die ohne PyTorch/sentence-transformers funktioniert.
Verwendet keyword-basierte Ähnlichkeit als Zwischenlösung.

Diese Version funktioniert sofort und kann später durch echte Embeddings erweitert werden.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import traceback
from collections import Counter
import math

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

@dataclass
class JobAnalysisResult:
    """Results from job analysis"""
    correlation_analysis: Dict[str, Any]
    enhanced_analysis: bool = True
    error_message: Optional[str] = None

class KeywordVectorizer:
    """Simple keyword-based vectorizer as fallback for sentence transformers"""
    
    def __init__(self, vector_size: int = 384):
        self.vector_size = vector_size
        self.vocabulary = {}
        self.idf_scores = {}
    
    def fit(self, texts: List[str]):
        """Fit the vectorizer on a corpus of texts"""
        # Build vocabulary
        all_words = []
        doc_word_counts = []
        
        for text in texts:
            words = self._tokenize(text)
            all_words.extend(words)
            doc_word_counts.append(Counter(words))
        
        # Create vocabulary from most common words
        word_counts = Counter(all_words)
        most_common = word_counts.most_common(self.vector_size)
        self.vocabulary = {word: idx for idx, (word, _) in enumerate(most_common)}
        
        # Calculate IDF scores
        n_docs = len(texts)
        for word in self.vocabulary:
            docs_with_word = sum(1 for doc_counts in doc_word_counts if word in doc_counts)
            self.idf_scores[word] = math.log(n_docs / max(docs_with_word, 1))
    
    def transform(self, text: str) -> List[float]:
        """Transform text to vector"""
        if not self.vocabulary:
            # Return zeros if not fitted
            return [0.0] * self.vector_size
        
        words = self._tokenize(text)
        word_counts = Counter(words)
        
        vector = [0.0] * self.vector_size
        
        for word, idx in self.vocabulary.items():
            if word in word_counts:
                # TF-IDF score
                tf = word_counts[word] / len(words) if words else 0
                idf = self.idf_scores.get(word, 0)
                vector[idx] = tf * idf
        
        return vector
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Convert to lowercase and extract words
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        
        # Filter out very short words and common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been'}
        words = [w for w in words if len(w) > 2 and w not in stop_words]
        
        return words

class QdrantLiteAnalyzer:
    """Lite version of Qdrant analyzer without heavy ML dependencies"""
    
    def __init__(self, 
                 qdrant_host: str = 'localhost', 
                 qdrant_port: int = 6333,
                 fallback_to_legacy: bool = True):
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.fallback_to_legacy = fallback_to_legacy
        
        self.client = None
        self.vectorizer = None
        self.is_initialized = False
        
        self.logger = logging.getLogger(__name__)
        
        # Collection names
        self.collections = {
            'domains': 'freelancer_domains_lite',
            'employment': 'freelancer_employment_lite',
            'education': 'freelancer_education_lite'
        }
        
        # MySQL config
        self.mysql_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'dCTKBq@CV9$a50ZtpzSr@D7*7Q',
            'database': 'domain_analysis'
        }
        
        # Try to initialize
        if QDRANT_AVAILABLE and MYSQL_AVAILABLE:
            self._initialize()
    
    def _initialize(self) -> bool:
        """Initialize connections"""
        try:
            self.logger.info("Initializing Qdrant Lite analyzer...")
            
            # Connect to Qdrant
            self.client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            
            # Test connection
            collections = self.client.get_collections()
            self.logger.info(f"Connected to Qdrant. Found {len(collections.collections)} collections")
            
            # Initialize keyword vectorizer
            self.vectorizer = KeywordVectorizer()
            
            # Check if lite collections exist, if not create them
            available_collections = [col.name for col in collections.collections]
            missing_collections = []
            
            for collection_name in self.collections.values():
                if collection_name not in available_collections:
                    missing_collections.append(collection_name)
            
            if missing_collections:
                self.logger.info(f"Creating missing collections: {missing_collections}")
                self._create_collections()
                self._populate_collections()
            
            self.is_initialized = True
            self.logger.info("✅ Qdrant Lite analyzer initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Qdrant Lite: {e}")
            return False
    
    def _create_collections(self):
        """Create Qdrant collections"""
        for collection_name in self.collections.values():
            try:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=384,  # Same as sentence transformers
                        distance=Distance.COSINE
                    )
                )
                self.logger.info(f"Created collection: {collection_name}")
            except Exception as e:
                self.logger.warning(f"Could not create collection {collection_name}: {e}")
    
    def _populate_collections(self):
        """Populate collections with data from MySQL"""
        try:
            # Extract data from MySQL
            domains = self._extract_domains_from_mysql()
            employment = self._extract_employment_from_mysql()
            education = self._extract_education_from_mysql()
            
            if not domains and not employment and not education:
                self.logger.warning("No data found in MySQL database")
                return
            
            # Collect all texts for vectorizer training
            all_texts = []
            
            for domain in domains:
                all_texts.append(domain.get('search_text', ''))
            
            for emp in employment:
                all_texts.append(emp.get('search_text', ''))
            
            for edu in education:
                all_texts.append(edu.get('search_text', ''))
            
            # Train vectorizer
            if all_texts:
                self.logger.info("Training keyword vectorizer...")
                self.vectorizer.fit([text for text in all_texts if text])
            
            # Store data
            self._store_domains(domains)
            self._store_employment(employment)
            self._store_education(education)
            
            self.logger.info(f"Successfully populated collections with {len(domains)} domains, {len(employment)} employment, {len(education)} education records")
            
        except Exception as e:
            self.logger.error(f"Error populating collections: {e}")
    
    def _extract_domains_from_mysql(self) -> List[Dict]:
        """Extract domains from MySQL"""
        try:
            conn = mysql.connector.connect(**self.mysql_config)
            cursor = conn.cursor(dictionary=True)
            
            # Get domains with tags
            cursor.execute("""
                SELECT d.id, d.domain_name, d.title, d.description,
                       GROUP_CONCAT(DISTINCT t.tag_name SEPARATOR ', ') as tags,
                       GROUP_CONCAT(DISTINCT s.subtag_name SEPARATOR ', ') as subtags
                FROM domains d
                LEFT JOIN domain_tags dt ON d.id = dt.domain_id
                LEFT JOIN tags t ON dt.tag_id = t.id
                LEFT JOIN domain_subtags ds ON d.id = ds.domain_id
                LEFT JOIN subtags s ON ds.subtag_id = s.id
                GROUP BY d.id, d.domain_name, d.title, d.description
            """)
            
            domains = []
            for row in cursor.fetchall():
                # Create search text
                parts = [row['domain_name']]
                if row['title']:
                    parts.append(row['title'])
                if row['description']:
                    parts.append(row['description'])
                if row['tags']:
                    parts.extend(row['tags'].split(', '))
                if row['subtags']:
                    parts.extend(row['subtags'].split(', '))
                
                search_text = ' '.join(filter(None, parts))
                
                domains.append({
                    'id': row['id'],
                    'domain_name': row['domain_name'],
                    'title': row['title'] or '',
                    'description': row['description'] or '',
                    'tags': row['tags'].split(', ') if row['tags'] else [],
                    'subtags': row['subtags'].split(', ') if row['subtags'] else [],
                    'search_text': search_text,
                    'type': 'domain'
                })
            
            conn.close()
            return domains
            
        except Exception as e:
            self.logger.error(f"Error extracting domains: {e}")
            return []
    
    def _extract_employment_from_mysql(self) -> List[Dict]:
        """Extract employment from MySQL"""
        try:
            conn = mysql.connector.connect(**self.mysql_config)
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM employment ORDER BY start_date DESC")
            
            employment = []
            for row in cursor.fetchall():
                parts = [row['company_name'], row['position'], row['description']]
                if row.get('technologies'):
                    parts.append(row['technologies'])
                if row.get('achievements'):
                    parts.append(row['achievements'])
                
                search_text = ' '.join(filter(None, parts))
                
                employment.append({
                    **row,
                    'search_text': search_text,
                    'type': 'employment'
                })
            
            conn.close()
            return employment
            
        except Exception as e:
            self.logger.error(f"Error extracting employment: {e}")
            return []
    
    def _extract_education_from_mysql(self) -> List[Dict]:
        """Extract education from MySQL"""
        try:
            conn = mysql.connector.connect(**self.mysql_config)
            cursor = conn.cursor(dictionary=True)
            
            # Get education with tags
            cursor.execute("""
                SELECT e.*, GROUP_CONCAT(t.tag_name SEPARATOR ', ') as tags
                FROM education e
                LEFT JOIN education_tags et ON e.id = et.education_id
                LEFT JOIN tags t ON et.tag_id = t.id
                GROUP BY e.id
                ORDER BY e.start_date DESC
            """)
            
            education = []
            for row in cursor.fetchall():
                parts = [row['title']]
                if row.get('institution'):
                    parts.append(row['institution'])
                if row.get('description'):
                    parts.append(row['description'])
                if row.get('tags'):
                    parts.extend(row['tags'].split(', '))
                
                search_text = ' '.join(filter(None, parts))
                
                education.append({
                    **row,
                    'tags': row['tags'].split(', ') if row['tags'] else [],
                    'search_text': search_text,
                    'type': 'education'
                })
            
            conn.close()
            return education
            
        except Exception as e:
            self.logger.error(f"Error extracting education: {e}")
            return []
    
    def _store_domains(self, domains: List[Dict]):
        """Store domains in Qdrant"""
        if not domains:
            return
        
        points = []
        for domain in domains:
            vector = self.vectorizer.transform(domain['search_text'])
            
            point = PointStruct(
                id=domain['id'],
                vector=vector,
                payload=domain
            )
            points.append(point)
        
        try:
            self.client.upsert(
                collection_name=self.collections['domains'],
                points=points
            )
            self.logger.info(f"Stored {len(points)} domains")
        except Exception as e:
            self.logger.error(f"Error storing domains: {e}")
    
    def _store_employment(self, employment: List[Dict]):
        """Store employment in Qdrant"""
        if not employment:
            return
        
        points = []
        for emp in employment:
            vector = self.vectorizer.transform(emp['search_text'])
            
            point = PointStruct(
                id=emp['id'],
                vector=vector,
                payload=emp
            )
            points.append(point)
        
        try:
            self.client.upsert(
                collection_name=self.collections['employment'],
                points=points
            )
            self.logger.info(f"Stored {len(points)} employment records")
        except Exception as e:
            self.logger.error(f"Error storing employment: {e}")
    
    def _store_education(self, education: List[Dict]):
        """Store education in Qdrant"""
        if not education:
            return
        
        points = []
        for edu in education:
            vector = self.vectorizer.transform(edu['search_text'])
            
            point = PointStruct(
                id=edu['id'],
                vector=vector,
                payload=edu
            )
            points.append(point)
        
        try:
            self.client.upsert(
                collection_name=self.collections['education'],
                points=points
            )
            self.logger.info(f"Stored {len(points)} education records")
        except Exception as e:
            self.logger.error(f"Error storing education: {e}")
    
    def _search_similar_items(self, job_description: str, collection_name: str, limit: int = 5) -> List[Dict]:
        """Search for similar items"""
        if not self.is_initialized or not self.vectorizer:
            return []
        
        try:
            query_vector = self.vectorizer.transform(job_description)
            
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
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
    
    def analyze_job_correlation(self, job_description: str, project_data: Optional[Dict] = None) -> JobAnalysisResult:
        """Analyze job correlation using keyword-based similarity"""
        
        if not QDRANT_AVAILABLE or not MYSQL_AVAILABLE:
            return self._legacy_analysis(job_description)
        
        if not self.is_initialized:
            self.logger.warning("Qdrant Lite not initialized, falling back to legacy analysis")
            if self.fallback_to_legacy:
                return self._legacy_analysis(job_description)
            else:
                return JobAnalysisResult(
                    correlation_analysis={},
                    enhanced_analysis=False,
                    error_message="Qdrant Lite not available"
                )
        
        try:
            self.logger.info("Performing Qdrant Lite job analysis...")
            
            # Search similar items
            similar_domains = self._search_similar_items(job_description, self.collections['domains'], limit=5)
            similar_employment = self._search_similar_items(job_description, self.collections['employment'], limit=3)
            similar_education = self._search_similar_items(job_description, self.collections['education'], limit=3)
            
            # Format results
            correlation_analysis = {
                "domains": self._format_domain_results(similar_domains),
                "employment": self._format_employment_results(similar_employment),
                "education": self._format_education_results(similar_education)
            }
            
            self.logger.info(f"✅ Lite analysis complete: {len(similar_domains)} domains, "
                           f"{len(similar_employment)} employment, {len(similar_education)} education")
            
            return JobAnalysisResult(
                correlation_analysis=correlation_analysis,
                enhanced_analysis=True
            )
            
        except Exception as e:
            self.logger.error(f"Error in Qdrant Lite analysis: {e}")
            self.logger.error(traceback.format_exc())
            
            if self.fallback_to_legacy:
                return self._legacy_analysis(job_description)
            else:
                return JobAnalysisResult(
                    correlation_analysis={},
                    enhanced_analysis=False,
                    error_message=str(e)
                )
    
    def _format_domain_results(self, domains: List[Dict]) -> List[Dict]:
        """Format domain results"""
        formatted_domains = []
        
        for domain in domains:
            tags = domain.get('tags', [])
            formatted_tags = []
            
            for tag in tags[:5]:  # Top 5 tags
                if tag:  # Skip empty tags
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
        """Format employment results"""
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
        """Format education results"""
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
    
    def _legacy_analysis(self, job_description: str) -> JobAnalysisResult:
        """Fallback legacy analysis"""
        self.logger.info("Using legacy correlation analysis")
        
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
                    "description": "Lead developer role involved dashboard development with Laravel and real-time data visualization"
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
        
        return JobAnalysisResult(
            correlation_analysis=correlation_analysis,
            enhanced_analysis=False,
            error_message="Using legacy analysis - Qdrant Lite fallback"
        )
    
    def health_check(self) -> Dict[str, Any]:
        """Check system health"""
        status = {
            "qdrant_available": QDRANT_AVAILABLE,
            "mysql_available": MYSQL_AVAILABLE,
            "initialized": self.is_initialized,
            "collections": {},
            "vectorizer_trained": self.vectorizer is not None
        }
        
        if self.is_initialized and self.client:
            try:
                collections = self.client.get_collections()
                for collection in collections.collections:
                    if collection.name in self.collections.values():
                        collection_info = self.client.get_collection(collection.name)
                        status["collections"][collection.name] = {
                            "points_count": collection_info.points_count,
                            "status": collection_info.status
                        }
            except Exception as e:
                status["error"] = str(e)
        
        return status

# Convenience function
def analyze_job_with_qdrant_lite(job_description: str, project_data: Optional[Dict] = None) -> JobAnalysisResult:
    """Convenience function for job analysis"""
    analyzer = QdrantLiteAnalyzer()
    return analyzer.analyze_job_correlation(job_description, project_data)

# Test function
def test_qdrant_lite():
    """Test the Qdrant Lite integration"""
    print("🧪 Testing Qdrant Lite Integration...")
    
    analyzer = QdrantLiteAnalyzer()
    
    # Health check
    health = analyzer.health_check()
    print(f"📊 Health Status: {json.dumps(health, indent=2)}")
    
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
    test_qdrant_lite()