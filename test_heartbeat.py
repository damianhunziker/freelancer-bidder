#!/usr/bin/env python3
"""
Test script to demonstrate heartbeat functionality
This script simulates different processes sending heartbeats
"""

import time
import random
from heartbeat_manager import send_heartbeat

def main():
    print("🔄 Starting heartbeat test script...")
    print("This script will simulate various processes sending heartbeats")
    print("Run process_monitor.py in another terminal to see the heartbeat status")
    print("Press Ctrl+C to stop\n")
    
    processes = [
        'test-process-1',
        'test-process-2', 
        'test-process-3'
    ]
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            
            for process_name in processes:
                # Simulate some processes being more active than others
                if random.random() > 0.2:  # 80% chance of sending heartbeat
                    additional_data = {
                        'iteration': iteration,
                        'simulated_work': random.randint(1, 100),
                        'status': random.choice(['working', 'processing', 'waiting'])
                    }
                    
                    send_heartbeat(process_name, additional_data)
                    print(f"💚 Sent heartbeat for {process_name}")
                else:
                    print(f"💔 Skipped heartbeat for {process_name} (simulating unresponsive process)")
            
            # Wait between iterations
            sleep_time = random.randint(10, 30)
            print(f"⏱️  Waiting {sleep_time}s before next iteration...")
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\n\n👋 Test script stopped by user")
        
        # Send final heartbeat to mark processes as stopped
        for process_name in processes:
            send_heartbeat(process_name, {'status': 'stopped', 'final': True})
            print(f"🛑 Sent final heartbeat for {process_name}")

if __name__ == "__main__":
    main() 