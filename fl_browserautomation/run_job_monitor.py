#!/usr/bin/env python3
"""
Launcher für Freelancer Universal WebSocket Monitor
"""

import os
import sys

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser_websocket_monitor import main

if __name__ == "__main__":
    print("🚀 Starte Freelancer Universal WebSocket Monitor...")
    print("🌐 Erfasst ALLE WebSocket-Verbindungen (URL-unabhängig)")
    print("=" * 70)
    main() 