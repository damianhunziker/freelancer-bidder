#!/usr/bin/env python3
"""
Test Script für Rate Limit Logging System
Testet alle Funktionen des erweiterten Rate Limit Managers
"""

import time
from rate_limit_manager import (
    set_rate_limit_timeout, 
    get_rate_limit_status, 
    is_rate_limited, 
    clear_rate_limit_timeout,
    get_rate_limit_logs,
    analyze_rate_limit_patterns,
    log_rate_limit_activity
)

def test_rate_limit_logging():
    """Testet das Rate Limit Logging System"""
    
    print("🧪 TESTING RATE LIMIT LOGGING SYSTEM")
    print("=" * 60)
    
    # Test 1: Manuelle Log-Eingabe
    print("\n1. Testing manual log entry...")
    log_rate_limit_activity('TEST_EVENT', {'test_param': 'test_value'}, 'test-script')
    
    # Test 2: Rate Limit aktivieren
    print("\n2. Testing rate limit activation...")
    set_rate_limit_timeout('test-activation-context')
    
    # Test 3: Status prüfen
    print("\n3. Testing status check...")
    status = get_rate_limit_status()
    print(f"Status: {status}")
    
    # Test 4: Mehrfache is_rate_limited Aufrufe (um STILL_ACTIVE zu testen)
    print("\n4. Testing multiple is_rate_limited calls...")
    for i in range(3):
        result = is_rate_limited(f'test-check-{i}')
        print(f"Check {i+1}: Rate limited = {result}")
        time.sleep(1)
    
    # Test 5: Log-Analyse
    print("\n5. Testing log analysis...")
    logs = get_rate_limit_logs(10)
    print(f"Recent logs ({len(logs)} entries):")
    for log in logs[-5:]:  # Zeige nur die letzten 5
        print(f"  {log}")
    
    # Test 6: Pattern-Analyse
    print("\n6. Testing pattern analysis...")
    patterns = analyze_rate_limit_patterns()
    print(f"Pattern analysis:")
    print(f"  Total events: {patterns.get('total_events', 0)}")
    print(f"  Activations: {patterns.get('activations', 0)}")
    print(f"  Clears: {patterns.get('clears', 0)}")
    print(f"  Errors: {patterns.get('errors', 0)}")
    print(f"  Contexts: {patterns.get('contexts', {})}")
    
    # Test 7: Verschiedene Fehler-Events
    print("\n7. Testing error events...")
    log_rate_limit_activity('ACTIVATION_ERROR', {'error': 'Simulated error'}, 'test-error-context')
    log_rate_limit_activity('READ_ERROR', {'error': 'File not found'}, 'test-read-context')
    log_rate_limit_activity('CLEAR_ERROR', {'error': 'Permission denied'}, 'test-clear-context')
    
    # Test 8: Rate Limit löschen
    print("\n8. Testing rate limit clearing...")
    clear_rate_limit_timeout('test-clearing-context')
    
    # Test 9: Finale Analyse
    print("\n9. Final analysis...")
    final_patterns = analyze_rate_limit_patterns()
    print(f"Final pattern analysis:")
    print(f"  Total events: {final_patterns.get('total_events', 0)}")
    print(f"  Activations: {final_patterns.get('activations', 0)}")
    print(f"  Clears: {final_patterns.get('clears', 0)}")
    print(f"  Errors: {final_patterns.get('errors', 0)}")
    
    # Test 10: Alle Logs anzeigen
    print("\n10. All logs from this test session:")
    all_logs = get_rate_limit_logs(20)
    for log in all_logs[-10:]:  # Zeige die letzten 10
        print(f"  {log}")
    
    print("\n✅ Rate Limit Logging System Test completed!")
    print("📝 Check api_logs/rate_limit.log for the complete log file")

if __name__ == "__main__":
    test_rate_limit_logging() 