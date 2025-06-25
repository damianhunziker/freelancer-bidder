#!/usr/bin/env python3
"""
Test Script für Node.js → Python Integration
===========================================

Testet die Korrelationsanalyse Integration zwischen Node.js und Python.
"""

import json
import sys

def test_correlation_analysis():
    """Test correlation analysis functionality"""
    try:
        from correlation_manager import CorrelationManager
        
        # Initialize manager
        manager = CorrelationManager()
        
        # Test job description
        job_description = """Laravel Dashboard Development
Build a real-time dashboard with Vue.js frontend and Laravel backend, including data visualization with charts
Skills: Laravel, Vue.js, MySQL, Chart.js"""
        
        # Run analysis
        result = manager.analyze_job_correlation(job_description)
        
        # Prepare output for Node.js
        output = {
            'success': True,
            'analysis_mode': result.analysis_mode,
            'execution_time_ms': result.execution_time_ms,
            'enhanced_analysis': result.enhanced_analysis,
            'correlation_analysis': result.correlation_analysis,
            'fallback_used': result.fallback_used,
            'error_message': result.error_message,
            'test_metadata': {
                'domains_found': len(result.correlation_analysis.get('domains', [])),
                'employment_found': len(result.correlation_analysis.get('employment', [])),
                'education_found': len(result.correlation_analysis.get('education', [])),
                'total_results': (
                    len(result.correlation_analysis.get('domains', [])) +
                    len(result.correlation_analysis.get('employment', [])) +
                    len(result.correlation_analysis.get('education', []))
                )
            }
        }
        
        return output
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'fallback_to_sql': True
        }

def test_mode_switching():
    """Test different analysis modes"""
    try:
        from correlation_manager import CorrelationManager
        
        modes = ['VECTOR_STORE', 'SQL', 'HYBRID']
        results = {}
        
        for mode in modes:
            try:
                manager = CorrelationManager()
                manager.analysis_mode = mode
                
                result = manager.analyze_job_correlation('Laravel dashboard')
                
                results[mode] = {
                    'success': True,
                    'analysis_mode': result.analysis_mode,
                    'execution_time_ms': result.execution_time_ms,
                    'enhanced_analysis': result.enhanced_analysis
                }
                
            except Exception as e:
                results[mode] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
        
    except Exception as e:
        return {'error': str(e)}

def test_config_loading():
    """Test config loading"""
    try:
        from config import CORRELATION_ANALYSIS_MODE, VECTOR_STORE_CONFIG
        
        return {
            'success': True,
            'mode': CORRELATION_ANALYSIS_MODE,
            'vector_store_enabled': CORRELATION_ANALYSIS_MODE in ['VECTOR_STORE', 'HYBRID'],
            'config_available': True
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'config_available': False
        }

def main():
    """Main test function"""
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        
        if test_type == 'correlation':
            result = test_correlation_analysis()
        elif test_type == 'modes':
            result = test_mode_switching()
        elif test_type == 'config':
            result = test_config_loading()
        else:
            result = {'error': f'Unknown test type: {test_type}'}
    else:
        # Run full integration test
        result = {
            'config': test_config_loading(),
            'correlation': test_correlation_analysis(),
            'modes': test_mode_switching()
        }
    
    # Output JSON for Node.js
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main() 