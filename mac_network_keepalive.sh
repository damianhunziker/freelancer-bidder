#!/bin/bash

# Mac Network Keep-Alive & Python Script Monitor
# Prevents network disconnection during sleep/lock and monitors script execution

# Configuration
PYTHON_SCRIPT="freelancer-websocket-reader.py"
CHECK_INTERVAL=30  # Seconds between checks
PING_HOST="8.8.8.8"  # Google DNS for connectivity test
LOG_FILE="mac_network_monitor.log"
RESTART_DELAY=10  # Seconds to wait before restarting script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local color=""
    
    case $level in
        "INFO")  color=$GREEN ;;
        "WARN")  color=$YELLOW ;;
        "ERROR") color=$RED ;;
        "DEBUG") color=$BLUE ;;
    esac
    
    echo -e "${color}[$timestamp] [$level] $message${NC}"
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Configure macOS Power Management for Network Keep-Alive
configure_macos_power_settings() {
    log_message "INFO" "🔧 Configuring macOS Power Management Settings..."
    
    # Prevent sleep when on power adapter
    sudo pmset -c sleep 0
    sudo pmset -c displaysleep 10
    sudo pmset -c disksleep 0
    
    # Keep network active during sleep
    sudo pmset -a tcpkeepalive 1
    sudo pmset -a womp 1  # Wake on Magic Packet
    
    # Prevent automatic sleep
    sudo pmset -a autopoweroff 0
    sudo pmset -a standby 0
    sudo pmset -a hibernatemode 0
    
    # Network-specific settings
    sudo pmset -a powernap 1  # Power Nap keeps network active
    
    log_message "INFO" "✅ Power Management configured for network keep-alive"
    
    # Show current settings
    log_message "DEBUG" "Current power settings:"
    pmset -g | while read line; do
        log_message "DEBUG" "  $line"
    done
}

# Check internet connectivity
check_internet() {
    if ping -c 1 -W 2000 $PING_HOST >/dev/null 2>&1; then
        return 0  # Connected
    else
        return 1  # Not connected
    fi
}

# Check if Python script is running
check_python_script() {
    if pgrep -f "$PYTHON_SCRIPT" >/dev/null; then
        return 0  # Running
    else
        return 1  # Not running
    fi
}

# Get system sleep/wake status
get_system_status() {
    local idle_time=$(ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}')
    local screen_locked=$(python3 -c "
import Quartz
session = Quartz.CGSessionCopyCurrentDictionary()
if session and session.get('CGSSessionScreenIsLocked', False):
    print('locked')
else:
    print('unlocked')
" 2>/dev/null || echo "unknown")
    
    if [ "$screen_locked" = "locked" ]; then
        echo "LOCKED"
    elif [ $idle_time -gt 300 ]; then  # 5 minutes idle
        echo "IDLE"
    else
        echo "ACTIVE"
    fi
}

# Start Python script
start_python_script() {
    log_message "INFO" "🚀 Starting Python script: $PYTHON_SCRIPT"
    
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        log_message "ERROR" "❌ Python script not found: $PYTHON_SCRIPT"
        return 1
    fi
    
    # Start script in background
    nohup python3 "$PYTHON_SCRIPT" > "python_output.log" 2>&1 &
    local pid=$!
    
    log_message "INFO" "✅ Python script started with PID: $pid"
    echo $pid > "python_script.pid"
    
    # Wait a moment and check if it's still running
    sleep 3
    if check_python_script; then
        log_message "INFO" "✅ Python script is running successfully"
        return 0
    else
        log_message "ERROR" "❌ Python script failed to start or crashed immediately"
        return 1
    fi
}

# Stop Python script gracefully
stop_python_script() {
    log_message "INFO" "🛑 Stopping Python script..."
    
    # Try graceful shutdown first
    pkill -TERM -f "$PYTHON_SCRIPT"
    sleep 5
    
    # Force kill if still running
    if check_python_script; then
        log_message "WARN" "⚠️ Forcefully killing Python script"
        pkill -KILL -f "$PYTHON_SCRIPT"
        sleep 2
    fi
    
    # Clean up PID file
    rm -f "python_script.pid"
    
    log_message "INFO" "✅ Python script stopped"
}

# Monitor system and restart script if needed
monitor_system() {
    local consecutive_failures=0
    local last_status=""
    local script_start_time=$(date +%s)
    
    log_message "INFO" "🔍 Starting system monitoring (Check interval: ${CHECK_INTERVAL}s)"
    
    while true; do
        local current_time=$(date +%s)
        local system_status=$(get_system_status)
        local internet_status="OFFLINE"
        local script_status="STOPPED"
        
        # Check internet connectivity
        if check_internet; then
            internet_status="ONLINE"
            consecutive_failures=0
        else
            internet_status="OFFLINE"
            ((consecutive_failures++))
        fi
        
        # Check Python script status
        if check_python_script; then
            script_status="RUNNING"
            local runtime=$((current_time - script_start_time))
            local runtime_formatted=$(printf "%02d:%02d:%02d" $((runtime/3600)) $((runtime%3600/60)) $((runtime%60)))
        else
            script_status="STOPPED"
        fi
        
        # Log status if changed or every 10 cycles
        local status_summary="System: $system_status | Internet: $internet_status | Script: $script_status"
        if [ "$status_summary" != "$last_status" ] || [ $((current_time % (CHECK_INTERVAL * 10))) -eq 0 ]; then
            if [ "$script_status" = "RUNNING" ]; then
                log_message "INFO" "📊 Status: $status_summary | Runtime: $runtime_formatted"
            else
                log_message "INFO" "📊 Status: $status_summary"
            fi
            last_status="$status_summary"
        fi
        
        # Handle script restart logic
        if [ "$script_status" = "STOPPED" ]; then
            log_message "WARN" "⚠️ Python script not running, attempting restart..."
            if start_python_script; then
                script_start_time=$(date +%s)
                consecutive_failures=0
            else
                log_message "ERROR" "❌ Failed to restart Python script"
                sleep $RESTART_DELAY
            fi
        fi
        
        # Handle consecutive network failures
        if [ $consecutive_failures -ge 3 ]; then
            log_message "WARN" "⚠️ Network offline for $consecutive_failures checks, restarting script..."
            stop_python_script
            sleep $RESTART_DELAY
            
            # Try to restart network (requires admin rights)
            log_message "INFO" "🔄 Attempting network restart..."
            sudo ifconfig en0 down && sudo ifconfig en0 up
            sleep 5
            
            if start_python_script; then
                script_start_time=$(date +%s)
                consecutive_failures=0
            fi
        fi
        
        # Show detailed status every 5 minutes during sleep/lock
        if [ "$system_status" != "ACTIVE" ] && [ $((current_time % 300)) -eq 0 ]; then
            log_message "DEBUG" "🌙 Sleep/Lock mode - Network: $internet_status, Script: $script_status"
            
            # Test specific network components
            local wifi_status=$(networksetup -getairportpower en0 2>/dev/null | awk '{print $4}')
            local dns_test=$(nslookup google.com >/dev/null 2>&1 && echo "OK" || echo "FAIL")
            
            log_message "DEBUG" "   WiFi Power: $wifi_status | DNS Test: $dns_test"
        fi
        
        sleep $CHECK_INTERVAL
    done
}

# Cleanup function
cleanup() {
    log_message "INFO" "🧹 Cleaning up and restoring settings..."
    
    # Stop Python script
    stop_python_script
    
    # Optionally restore original power settings (uncomment if needed)
    # sudo pmset -a sleep 10
    # sudo pmset -a displaysleep 10
    # sudo pmset -a disksleep 10
    
    log_message "INFO" "✅ Cleanup completed"
    exit 0
}

# Install required dependencies
install_dependencies() {
    log_message "INFO" "📦 Checking dependencies..."
    
    # Check if we need to install anything
    if ! command -v python3 >/dev/null; then
        log_message "ERROR" "❌ Python3 not found. Please install Python3."
        exit 1
    fi
    
    log_message "INFO" "✅ All dependencies satisfied"
}

# Main function
main() {
    log_message "INFO" "🚀 Mac Network Keep-Alive & Python Monitor Started"
    log_message "INFO" "📝 Log file: $LOG_FILE"
    log_message "INFO" "🐍 Python script: $PYTHON_SCRIPT"
    
    # Check for admin rights
    if [ "$EUID" -ne 0 ]; then
        log_message "INFO" "🔐 This script needs sudo access for power management settings"
        log_message "INFO" "💡 You may be prompted for your password"
    fi
    
    # Install dependencies
    install_dependencies
    
    # Configure power settings
    configure_macos_power_settings
    
    # Set up signal handlers
    trap cleanup SIGINT SIGTERM
    
    # Start initial Python script
    if ! start_python_script; then
        log_message "ERROR" "❌ Failed to start initial Python script"
        exit 1
    fi
    
    # Start monitoring loop
    monitor_system
}

# Show usage
show_usage() {
    echo "Mac Network Keep-Alive & Python Monitor"
    echo
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -s, --setup-only    Only configure power settings, don't monitor"
    echo "  -m, --monitor-only  Only monitor, don't change power settings"
    echo "  -i, --interval N    Set check interval (default: 30 seconds)"
    echo
    echo "This script will:"
    echo "  1. Configure macOS to maintain network during sleep/lock"
    echo "  2. Monitor internet connectivity"
    echo "  3. Keep Python script running with auto-restart"
    echo "  4. Provide detailed logging and status updates"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -s|--setup-only)
            configure_macos_power_settings
            exit 0
            ;;
        -m|--monitor-only)
            SKIP_POWER_CONFIG=true
            shift
            ;;
        -i|--interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        *)
            log_message "ERROR" "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Run main function
main 