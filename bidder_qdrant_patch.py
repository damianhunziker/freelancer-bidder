#!/usr/bin/env python3
"""
Bidder Qdrant Integration Patch
==============================

This script shows how to integrate Qdrant vector search into the existing bidder.py system.
Based on the correlation analysis shown in the attached code sample.

The integration enhances the existing correlation analysis with semantic similarity search.
"""

import json
import logging
from typing import Dict, Any, Optional
import traceback

# Import the Qdrant integration module
try:
    from qdrant_integration import QdrantJobAnalyzer, JobAnalysisResult
    QDRANT_INTEGRATION_AVAILABLE = True
except ImportError:
    QDRANT_INTEGRATION_AVAILABLE = False
    print("⚠️  Qdrant integration not available. Place qdrant_integration.py in the same directory.")

class EnhancedBidder:
    """Enhanced bidder with Qdrant vector search capabilities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize Qdrant analyzer if available
        if QDRANT_INTEGRATION_AVAILABLE:
            try:
                self.qdrant_analyzer = QdrantJobAnalyzer(fallback_to_legacy=True)
                self.logger.info("✅ Qdrant analyzer initialized")
            except Exception as e:
                self.logger.warning(f"Qdrant initialization failed: {e}")
                self.qdrant_analyzer = None
        else:
            self.qdrant_analyzer = None
    
    def enhanced_correlation_analysis(self, job_description: str, project_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Enhanced correlation analysis using Qdrant vector search
        
        This replaces or enhances the existing correlation analysis in bidder.py
        """
        self.logger.info("Starting enhanced correlation analysis...")
        
        # Use Qdrant if available, otherwise fall back to legacy analysis
        if self.qdrant_analyzer and self.qdrant_analyzer.is_initialized:
            try:
                self.logger.info("Using Qdrant-enhanced analysis")
                result = self.qdrant_analyzer.analyze_job_correlation(job_description, project_data)
                
                if result.enhanced_analysis:
                    self.logger.info("✅ Qdrant analysis successful")
                    return result.correlation_analysis
                else:
                    self.logger.warning(f"Qdrant analysis failed: {result.error_message}")
                    return self._legacy_correlation_analysis(job_description, project_data)
                    
            except Exception as e:
                self.logger.error(f"Qdrant analysis error: {e}")
                self.logger.error(traceback.format_exc())
                return self._legacy_correlation_analysis(job_description, project_data)
        else:
            self.logger.info("Using legacy correlation analysis")
            return self._legacy_correlation_analysis(job_description, project_data)
    
    def _legacy_correlation_analysis(self, job_description: str, project_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Legacy correlation analysis - integrate your existing correlation logic here
        
        This is where you would put the existing correlation analysis code from bidder.py
        """
        self.logger.info("Performing legacy correlation analysis")
        
        # Example structure - replace with your actual legacy analysis
        # This should mirror the structure from your existing bidder.py correlation analysis
        
        correlation_analysis = {
            "domains": [
                {
                    "domain": "reishauer.com",
                    "title": "reishauer.com",
                    "relevance_score": 0.85,
                    "tags": [
                        {
                            "name": "Data Visualization",
                            "relevance_score": 0.9
                        },
                        {
                            "name": "Laravel Development", 
                            "relevance_score": 0.8
                        }
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
        
        return correlation_analysis
    
    def generate_enhanced_bid(self, project_id: str, job_description: str) -> Dict[str, Any]:
        """
        Generate enhanced bid using Qdrant correlation analysis
        
        This method shows how to integrate the enhanced analysis into bid generation
        """
        self.logger.info(f"Generating enhanced bid for project {project_id}")
        
        try:
            # Perform enhanced correlation analysis
            correlation_analysis = self.enhanced_correlation_analysis(job_description)
            
            # Generate bid text based on correlation analysis
            # This would integrate with your existing bid generation logic
            bid_result = self._generate_bid_from_correlation(
                job_description, 
                correlation_analysis,
                project_id
            )
            
            # Add metadata about analysis type
            bid_result["analysis_metadata"] = {
                "enhanced_analysis": self.qdrant_analyzer is not None and self.qdrant_analyzer.is_initialized,
                "correlation_domains_count": len(correlation_analysis.get("domains", [])),
                "correlation_employment_count": len(correlation_analysis.get("employment", [])),
                "correlation_education_count": len(correlation_analysis.get("education", []))
            }
            
            return bid_result
            
        except Exception as e:
            self.logger.error(f"Error generating enhanced bid: {e}")
            self.logger.error(traceback.format_exc())
            raise
    
    def _generate_bid_from_correlation(self, job_description: str, correlation_analysis: Dict, project_id: str) -> Dict[str, Any]:
        """
        Generate bid text from correlation analysis
        
        This integrates with your existing bid text generation logic
        """
        # Extract relevant information from correlation analysis
        relevant_domains = correlation_analysis.get("domains", [])[:3]  # Top 3 domains
        relevant_employment = correlation_analysis.get("employment", [])[:2]  # Top 2 employment
        relevant_education = correlation_analysis.get("education", [])[:2]  # Top 2 education
        
        # Generate bid components
        greeting = "Hi there,"
        
        # First paragraph - technical approach with relevant domains
        domain_examples = ""
        if relevant_domains:
            domain_names = [domain.get("domain", "") for domain in relevant_domains if domain.get("domain")]
            if domain_names:
                domain_examples = f", similar to work we've done for {', '.join(domain_names[:2])}"
        
        first_paragraph = f"For your project requirements, we can implement a comprehensive solution using modern web technologies{domain_examples}. Our approach focuses on delivering scalable, maintainable code with excellent user experience."
        
        # Second paragraph - experience highlighting
        second_paragraph = "Our team brings relevant experience from multiple projects"
        if relevant_employment:
            companies = [emp.get("company", "") for emp in relevant_employment if emp.get("company")]
            if companies:
                second_paragraph += f" including our work at {', '.join(companies)}"
        second_paragraph += ". We combine technical expertise with business understanding to deliver solutions that meet your specific needs."
        
        # Closing
        closing = "Looking forward to discussing your project in detail."
        
        # Question
        question = "Could you provide more details about your specific requirements and timeline?"
        
        # Estimate (you would calculate this based on your existing logic)
        estimated_price = 5000  # Placeholder
        estimated_days = 14  # Placeholder
        
        # Final composed text
        final_composed_text = f"{greeting}\n\n{first_paragraph}\n\n{second_paragraph}\n\n{closing}\n\nBest regards,\nDamian Hunziker"
        
        return {
            "bid_teaser": {
                "greeting": greeting,
                "first_paragraph": first_paragraph,
                "second_paragraph": second_paragraph,
                "third_paragraph": "",
                "fourth_paragraph": "",
                "closing": closing,
                "question": question,
                "estimated_price": estimated_price,
                "estimated_days": estimated_days,
                "final_composed_text": final_composed_text
            },
            "correlation_analysis": correlation_analysis
        }

# Example integration into existing bidder workflow
def patch_existing_bidder():
    """
    Example of how to patch the existing bidder.py with Qdrant functionality
    
    This shows the minimal changes needed to integrate Qdrant into your existing system
    """
    
    # Replace this section in your existing bidder.py:
    # Original code (around line 900-1000 based on attached sample):
    """
    # Old correlation analysis code
    correlation_analysis = analyze_project_correlation(job_description)
    """
    
    # New enhanced code:
    enhanced_bidder = EnhancedBidder()
    correlation_analysis = enhanced_bidder.enhanced_correlation_analysis(job_description)
    
    # The rest of your existing code can remain the same
    # as the correlation_analysis structure is maintained
    
    return correlation_analysis

# Test function for the enhanced bidder
def test_enhanced_bidder():
    """Test the enhanced bidder functionality"""
    print("🧪 Testing Enhanced Bidder with Qdrant Integration...")
    
    bidder = EnhancedBidder()
    
    # Test job description (from your attached sample)
    test_job = """
    We need a real-time dashboard for data visualization. The project involves:
    - Laravel backend development
    - Vue.js frontend with Chart.js integration
    - Real-time data processing
    - Excel/CSV import functionality
    - API integrations
    """
    
    print(f"📋 Test Job: {test_job.strip()}")
    
    try:
        # Test correlation analysis
        correlation = bidder.enhanced_correlation_analysis(test_job)
        print("\n✅ Correlation Analysis Results:")
        print(json.dumps(correlation, indent=2, ensure_ascii=False))
        
        # Test bid generation
        bid_result = bidder.generate_enhanced_bid("TEST_PROJECT_123", test_job)
        print("\n✅ Generated Bid:")
        print(f"Final Bid Text:\n{bid_result['bid_teaser']['final_composed_text']}")
        print(f"\nEstimated Price: ${bid_result['bid_teaser']['estimated_price']}")
        print(f"Estimated Days: {bid_result['bid_teaser']['estimated_days']}")
        
        # Show analysis metadata
        metadata = bid_result.get("analysis_metadata", {})
        print(f"\n📊 Analysis Metadata:")
        print(f"Enhanced Analysis: {metadata.get('enhanced_analysis', False)}")
        print(f"Relevant Domains: {metadata.get('correlation_domains_count', 0)}")
        print(f"Relevant Employment: {metadata.get('correlation_employment_count', 0)}")
        print(f"Relevant Education: {metadata.get('correlation_education_count', 0)}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_enhanced_bidder()