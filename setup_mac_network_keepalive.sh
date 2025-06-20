#!/bin/bash

# Simple Mac Network Keep-Alive Setup
# Configures macOS to maintain network connection during sleep/lock

echo "🔧 Mac Network Keep-Alive Setup"
echo "================================"
echo
echo "This script will configure your Mac to:"
echo "  ✅ Keep network active during sleep"
echo "  ✅ Prevent automatic hibernate"
echo "  ✅ Enable Power Nap for network connectivity"
echo "  ✅ Optimize power settings for continuous operation"
echo

# Ask for confirmation
read -p "Do you want to proceed with these changes? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Setup cancelled"
    exit 1
fi

echo "🔐 This requires administrator privileges..."
echo

# Backup current settings
echo "💾 Backing up current power settings..."
pmset -g > "power_settings_backup_$(date +%Y%m%d_%H%M%S).txt"
echo "✅ Backup saved to power_settings_backup_$(date +%Y%m%d_%H%M%S).txt"

# Configure power settings for network keep-alive
echo "🔧 Configuring power management..."

# When plugged in (AC power)
echo "  📱 Setting AC power options..."
sudo pmset -c sleep 0          # Never sleep when plugged in
sudo pmset -c displaysleep 10  # Turn off display after 10 minutes
sudo pmset -c disksleep 0      # Never sleep hard disk

# When on battery
echo "  🔋 Setting battery power options..."
sudo pmset -b sleep 60         # Sleep after 60 minutes on battery
sudo pmset -b displaysleep 5   # Turn off display after 5 minutes on battery
sudo pmset -b disksleep 10     # Sleep hard disk after 10 minutes on battery

# Universal settings (both AC and battery)
echo "  🌐 Setting network keep-alive options..."
sudo pmset -a tcpkeepalive 1   # Maintain TCP connections during sleep
sudo pmset -a womp 1           # Wake on Magic Packet
sudo pmset -a powernap 1       # Enable Power Nap (keeps network active)

# Prevent deep sleep modes
echo "  😴 Disabling deep sleep modes..."
sudo pmset -a autopoweroff 0   # Disable auto power off
sudo pmset -a standby 0        # Disable standby mode
sudo pmset -a hibernatemode 0  # Disable hibernation

# Additional network optimizations
echo "  🔄 Additional optimizations..."
sudo pmset -a ttyskeepawake 1  # Prevent sleep when TTY is active
sudo pmset -a networkoversleep 0  # Don't prioritize network over sleep

echo
echo "✅ Power settings configured successfully!"
echo
echo "📊 Current power settings:"
echo "=========================="
pmset -g

echo
echo "🎯 What this means:"
echo "  • Your Mac will stay connected to internet during sleep/lock"
echo "  • Network connections will be maintained"
echo "  • Power Nap will keep essential services running"
echo "  • Deep sleep modes are disabled"
echo
echo "💡 To restore original settings, run:"
echo "     sudo pmset restoredefaults"
echo
echo "✅ Setup complete! Your Mac is now optimized for network keep-alive." 