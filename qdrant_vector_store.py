#!/usr/bin/env python3
"""
Qdrant Vector Store Integration for Freelancer Bidder
==================================================

This script integrates the existing MySQL domain_analysis database with Qdrant
for semantic similarity search of domains, tags, and subtags.

Features:
- Extract domains, tags, employment, and education data from MySQL
- Generate embeddings using sentence-transformers
- Store in Qdrant vector database
- Provide similarity search for job matching
- Update existing project evaluation workflow

Dependencies:
pip install qdrant-client sentence-transformers mysql-connector-python
"""

import json
import logging
import mysql.connector
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Vector embeddings
from sentence_transformers import SentenceTransformer
import numpy as np

# Qdrant client
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct

# Configuration
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'dCTKBq@CV9$a50ZtpzSr@D7*7Q',
    'database': 'domain_analysis'
}

QDRANT_CONFIG = {
    'host': 'localhost',
    'port': 6333
}

# Collection names
COLLECTIONS = {
    'domains': 'freelancer_domains',
    'employment': 'freelancer_employment',
    'education': 'freelancer_education',
    'projects': 'freelancer_projects'
}

# Embedding model configuration
EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
EMBEDDING_DIMENSION = 384

@dataclass
class DomainRecord:
    """Represents a domain with its associated tags and metadata"""
    id: int
    domain_name: str
    title: str = ""
    description: str = ""
    tags: List[str] = None
    subtags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.subtags is None:
            self.subtags = []
    
    @property
    def search_text(self) -> str:
        """Generate searchable text combining all domain information"""
        parts = [self.domain_name]
        if self.title:
            parts.append(self.title)
        if self.description:
            parts.append(self.description)
        if self.tags:
            parts.extend(self.tags)
        if self.subtags:
            parts.extend(self.subtags)
        return " ".join(parts)

@dataclass
class EmploymentRecord:
    """Represents employment history with tags"""
    id: int
    company_name: str
    position: str
    description: str
    technologies: str = ""
    achievements: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    is_self_employed: bool = False
    
    @property
    def search_text(self) -> str:
        """Generate searchable text for employment record"""
        parts = [self.company_name, self.position, self.description]
        if self.technologies:
            parts.append(self.technologies)
        if self.achievements:
            parts.append(self.achievements)
        return " ".join(filter(None, parts))

@dataclass
class EducationRecord:
    """Represents education/training with tags"""
    id: int
    title: str
    institution: str = ""
    description: str = ""
    type: str = "course"
    start_date: str = ""
    end_date: str = ""
    duration: str = ""
    location: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    @property
    def search_text(self) -> str:
        """Generate searchable text for education record"""
        parts = [self.title]
        if self.institution:
            parts.append(self.institution)
        if self.description:
            parts.append(self.description)
        if self.tags:
            parts.extend(self.tags)
        return " ".join(filter(None, parts))

class QdrantVectorStore:
    """Main class for Qdrant vector store operations"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.model = None
        self.qdrant_client = None
        self.mysql_connection = None
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def initialize(self):
        """Initialize connections and models"""
        self.logger.info("Initializing Qdrant Vector Store...")
        
        # Load embedding model
        self.logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Connect to Qdrant
        self.logger.info(f"Connecting to Qdrant at {QDRANT_CONFIG['host']}:{QDRANT_CONFIG['port']}")
        self.qdrant_client = QdrantClient(
            host=QDRANT_CONFIG['host'],
            port=QDRANT_CONFIG['port']
        )
        
        # Connect to MySQL
        self.logger.info("Connecting to MySQL database...")
        self.mysql_connection = mysql.connector.connect(**MYSQL_CONFIG)
        
        self.logger.info("Initialization complete!")
    
    def create_collections(self):
        """Create Qdrant collections for different data types"""
        self.logger.info("Creating Qdrant collections...")
        
        for collection_name in COLLECTIONS.values():
            try:
                # Delete existing collection if it exists
                try:
                    self.qdrant_client.delete_collection(collection_name)
                    self.logger.info(f"Deleted existing collection: {collection_name}")
                except Exception:
                    pass  # Collection doesn't exist
                
                # Create new collection
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIMENSION,
                        distance=Distance.COSINE
                    )
                )
                self.logger.info(f"Created collection: {collection_name}")
                
            except Exception as e:
                self.logger.error(f"Error creating collection {collection_name}: {e}")
                raise
    
    def extract_domains_from_mysql(self) -> List[DomainRecord]:
        """Extract domains with tags and subtags from MySQL"""
        self.logger.info("Extracting domains from MySQL...")
        
        cursor = self.mysql_connection.cursor(dictionary=True)
        
        try:
            # Get all domains
            cursor.execute("""
                SELECT id, domain_name, title, description 
                FROM domains 
                ORDER BY id
            """)
            domains_data = cursor.fetchall()
            
            domains = []
            for domain_data in domains_data:
                domain = DomainRecord(
                    id=domain_data['id'],
                    domain_name=domain_data['domain_name'],
                    title=domain_data.get('title', '') or '',
                    description=domain_data.get('description', '') or ''
                )
                
                # Get tags for this domain
                cursor.execute("""
                    SELECT t.tag_name 
                    FROM domain_tags dt
                    JOIN tags t ON dt.tag_id = t.id
                    WHERE dt.domain_id = %s
                """, (domain.id,))
                
                tags = [row['tag_name'] for row in cursor.fetchall()]
                domain.tags = tags
                
                # Get subtags for this domain
                cursor.execute("""
                    SELECT s.subtag_name 
                    FROM domain_subtags ds
                    JOIN subtags s ON ds.subtag_id = s.id
                    WHERE ds.domain_id = %s
                """, (domain.id,))
                
                subtags = [row['subtag_name'] for row in cursor.fetchall()]
                domain.subtags = subtags
                
                domains.append(domain)
                
            self.logger.info(f"Extracted {len(domains)} domains")
            return domains
            
        except Exception as e:
            self.logger.error(f"Error extracting domains: {e}")
            raise
        finally:
            cursor.close()
    
    def extract_employment_from_mysql(self) -> List[EmploymentRecord]:
        """Extract employment history from MySQL"""
        self.logger.info("Extracting employment data from MySQL...")
        
        cursor = self.mysql_connection.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT * FROM employment ORDER BY start_date DESC
            """)
            employment_data = cursor.fetchall()
            
            employment_records = []
            for emp_data in employment_data:
                record = EmploymentRecord(
                    id=emp_data['id'],
                    company_name=emp_data['company_name'],
                    position=emp_data['position'],
                    description=emp_data['description'],
                    technologies=emp_data.get('technologies', '') or '',
                    achievements=emp_data.get('achievements', '') or '',
                    start_date=emp_data.get('start_date', '') or '',
                    end_date=emp_data.get('end_date', '') or '',
                    location=emp_data.get('location', '') or '',
                    is_self_employed=bool(emp_data.get('is_self_employed', False))
                )
                employment_records.append(record)
            
            self.logger.info(f"Extracted {len(employment_records)} employment records")
            return employment_records
            
        except Exception as e:
            self.logger.error(f"Error extracting employment: {e}")
            raise
        finally:
            cursor.close()
    
    def extract_education_from_mysql(self) -> List[EducationRecord]:
        """Extract education/training data from MySQL"""
        self.logger.info("Extracting education data from MySQL...")
        
        cursor = self.mysql_connection.cursor(dictionary=True)
        
        try:
            # Get all education records
            cursor.execute("""
                SELECT * FROM education ORDER BY start_date DESC
            """)
            education_data = cursor.fetchall()
            
            education_records = []
            for edu_data in education_data:
                record = EducationRecord(
                    id=edu_data['id'],
                    title=edu_data['title'],
                    institution=edu_data.get('institution', '') or '',
                    description=edu_data.get('description', '') or '',
                    type=edu_data.get('type', 'course') or 'course',
                    start_date=edu_data.get('start_date', '') or '',
                    end_date=edu_data.get('end_date', '') or '',
                    duration=edu_data.get('duration', '') or '',
                    location=edu_data.get('location', '') or ''
                )
                
                # Get tags for this education record
                cursor.execute("""
                    SELECT t.tag_name 
                    FROM education_tags et
                    JOIN tags t ON et.tag_id = t.id
                    WHERE et.education_id = %s
                """, (record.id,))
                
                tags = [row['tag_name'] for row in cursor.fetchall()]
                record.tags = tags
                
                education_records.append(record)
            
            self.logger.info(f"Extracted {len(education_records)} education records")
            return education_records
            
        except Exception as e:
            self.logger.error(f"Error extracting education: {e}")
            raise
        finally:
            cursor.close()
    
    def store_domains_in_qdrant(self, domains: List[DomainRecord]):
        """Store domain records in Qdrant"""
        self.logger.info(f"Storing {len(domains)} domains in Qdrant...")
        
        points = []
        for domain in domains:
            # Generate embedding
            embedding = self.model.encode(domain.search_text).tolist()
            
            # Create point
            point = PointStruct(
                id=domain.id,
                vector=embedding,
                payload={
                    "domain_name": domain.domain_name,
                    "title": domain.title,
                    "description": domain.description,
                    "tags": domain.tags,
                    "subtags": domain.subtags,
                    "search_text": domain.search_text,
                    "type": "domain"
                }
            )
            points.append(point)
        
        # Batch upload to Qdrant
        self.qdrant_client.upsert(
            collection_name=COLLECTIONS['domains'],
            points=points
        )
        
        self.logger.info(f"Successfully stored {len(points)} domains in Qdrant")
    
    def store_employment_in_qdrant(self, employment: List[EmploymentRecord]):
        """Store employment records in Qdrant"""
        self.logger.info(f"Storing {len(employment)} employment records in Qdrant...")
        
        points = []
        for emp in employment:
            # Generate embedding
            embedding = self.model.encode(emp.search_text).tolist()
            
            # Create point
            point = PointStruct(
                id=emp.id,
                vector=embedding,
                payload={
                    "company_name": emp.company_name,
                    "position": emp.position,
                    "description": emp.description,
                    "technologies": emp.technologies,
                    "achievements": emp.achievements,
                    "start_date": emp.start_date,
                    "end_date": emp.end_date,
                    "location": emp.location,
                    "is_self_employed": emp.is_self_employed,
                    "search_text": emp.search_text,
                    "type": "employment"
                }
            )
            points.append(point)
        
        # Batch upload to Qdrant
        self.qdrant_client.upsert(
            collection_name=COLLECTIONS['employment'],
            points=points
        )
        
        self.logger.info(f"Successfully stored {len(points)} employment records in Qdrant")
    
    def store_education_in_qdrant(self, education: List[EducationRecord]):
        """Store education records in Qdrant"""
        self.logger.info(f"Storing {len(education)} education records in Qdrant...")
        
        points = []
        for edu in education:
            # Generate embedding
            embedding = self.model.encode(edu.search_text).tolist()
            
            # Create point
            point = PointStruct(
                id=edu.id,
                vector=embedding,
                payload={
                    "title": edu.title,
                    "institution": edu.institution,
                    "description": edu.description,
                    "type": edu.type,
                    "start_date": edu.start_date,
                    "end_date": edu.end_date,
                    "duration": edu.duration,
                    "location": edu.location,
                    "tags": edu.tags,
                    "search_text": edu.search_text,
                    "type": "education"
                }
            )
            points.append(point)
        
        # Batch upload to Qdrant
        self.qdrant_client.upsert(
            collection_name=COLLECTIONS['education'],
            points=points
        )
        
        self.logger.info(f"Successfully stored {len(points)} education records in Qdrant")
    
    def search_similar_domains(self, job_description: str, limit: int = 5) -> List[Dict]:
        """Search for similar domains based on job description"""
        self.logger.info(f"Searching for similar domains for job: {job_description[:100]}...")
        
        # Generate query embedding
        query_embedding = self.model.encode(job_description).tolist()
        
        # Search in Qdrant
        results = self.qdrant_client.search(
            collection_name=COLLECTIONS['domains'],
            query_vector=query_embedding,
            limit=limit
        )
        
        similar_domains = []
        for result in results:
            domain_info = {
                "domain_name": result.payload["domain_name"],
                "title": result.payload["title"],
                "tags": result.payload["tags"],
                "subtags": result.payload["subtags"],
                "score": result.score,
                "relevance_score": min(result.score * 100, 100)  # Convert to percentage
            }
            similar_domains.append(domain_info)
        
        self.logger.info(f"Found {len(similar_domains)} similar domains")
        return similar_domains
    
    def search_similar_employment(self, job_description: str, limit: int = 3) -> List[Dict]:
        """Search for similar employment experiences"""
        self.logger.info(f"Searching for similar employment for job: {job_description[:100]}...")
        
        # Generate query embedding
        query_embedding = self.model.encode(job_description).tolist()
        
        # Search in Qdrant
        results = self.qdrant_client.search(
            collection_name=COLLECTIONS['employment'],
            query_vector=query_embedding,
            limit=limit
        )
        
        similar_employment = []
        for result in results:
            emp_info = {
                "company": result.payload["company_name"],
                "position": result.payload["position"],
                "description": result.payload["description"],
                "technologies": result.payload["technologies"],
                "start_date": result.payload["start_date"],
                "end_date": result.payload["end_date"],
                "score": result.score,
                "relevance_score": min(result.score * 100, 100)
            }
            similar_employment.append(emp_info)
        
        self.logger.info(f"Found {len(similar_employment)} similar employment records")
        return similar_employment
    
    def search_similar_education(self, job_description: str, limit: int = 3) -> List[Dict]:
        """Search for similar education/training"""
        self.logger.info(f"Searching for similar education for job: {job_description[:100]}...")
        
        # Generate query embedding
        query_embedding = self.model.encode(job_description).tolist()
        
        # Search in Qdrant
        results = self.qdrant_client.search(
            collection_name=COLLECTIONS['education'],
            query_vector=query_embedding,
            limit=limit
        )
        
        similar_education = []
        for result in results:
            edu_info = {
                "title": result.payload["title"],
                "institution": result.payload["institution"],
                "description": result.payload["description"],
                "tags": result.payload["tags"],
                "type": result.payload["type"],
                "score": result.score,
                "relevance_score": min(result.score * 100, 100)
            }
            similar_education.append(edu_info)
        
        self.logger.info(f"Found {len(similar_education)} similar education records")
        return similar_education
    
    def analyze_job_correlation(self, job_description: str) -> Dict[str, Any]:
        """Comprehensive job correlation analysis using vector similarity"""
        self.logger.info("Performing comprehensive job correlation analysis...")
        
        analysis = {
            "correlation_analysis": {
                "domains": [],
                "employment": [],
                "education": []
            }
        }
        
        # Get similar domains
        similar_domains = self.search_similar_domains(job_description, limit=5)
        for domain in similar_domains:
            domain_analysis = {
                "domain": domain["domain_name"],
                "title": domain["title"],
                "relevance_score": round(domain["relevance_score"] / 100, 2),
                "tags": [
                    {
                        "name": tag,
                        "relevance_score": round(domain["relevance_score"] / 100, 2)
                    }
                    for tag in domain["tags"][:5]  # Top 5 tags
                ]
            }
            analysis["correlation_analysis"]["domains"].append(domain_analysis)
        
        # Get similar employment
        similar_employment = self.search_similar_employment(job_description, limit=3)
        for emp in similar_employment:
            emp_analysis = {
                "company": emp["company"],
                "position": emp["position"],
                "relevance_score": round(emp["relevance_score"] / 100, 2),
                "description": emp["description"][:200] + "..." if len(emp["description"]) > 200 else emp["description"]
            }
            analysis["correlation_analysis"]["employment"].append(emp_analysis)
        
        # Get similar education
        similar_education = self.search_similar_education(job_description, limit=3)
        for edu in similar_education:
            edu_analysis = {
                "institution": edu["institution"],
                "title": edu["title"],
                "relevance_score": round(edu["relevance_score"] / 100, 2),
                "description": edu["description"][:200] + "..." if len(edu["description"]) > 200 else edu["description"]
            }
            analysis["correlation_analysis"]["education"].append(edu_analysis)
        
        return analysis
    
    def close_connections(self):
        """Close database connections"""
        if self.mysql_connection:
            self.mysql_connection.close()
            self.logger.info("MySQL connection closed")

def main():
    """Main function to initialize and populate Qdrant vector store"""
    vector_store = QdrantVectorStore()
    
    try:
        # Initialize
        vector_store.initialize()
        
        # Create collections
        vector_store.create_collections()
        
        # Extract data from MySQL
        domains = vector_store.extract_domains_from_mysql()
        employment = vector_store.extract_employment_from_mysql()
        education = vector_store.extract_education_from_mysql()
        
        # Store in Qdrant
        vector_store.store_domains_in_qdrant(domains)
        vector_store.store_employment_in_qdrant(employment)
        vector_store.store_education_in_qdrant(education)
        
        print("✅ Qdrant vector store setup complete!")
        print(f"📊 Stored {len(domains)} domains, {len(employment)} employment records, {len(education)} education records")
        
        # Test search
        test_job = "Laravel dashboard with real-time data visualization using Chart.js"
        print(f"\n🔍 Testing similarity search with: {test_job}")
        
        analysis = vector_store.analyze_job_correlation(test_job)
        print("\n📋 Analysis Results:")
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        vector_store.close_connections()

if __name__ == "__main__":
    main()