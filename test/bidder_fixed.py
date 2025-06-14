import time
import json
import os
import traceback
from typing import Dict, List, Any

def main():
    try:
        # Your main code here
        print("Starting the bidder...")
        time.sleep(1)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 