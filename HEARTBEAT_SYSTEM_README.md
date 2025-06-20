# Heartbeat System Documentation

## Overview

The heartbeat system provides real-time monitoring of active processes by having each process send periodic "heartbeat" signals to a central monitoring system. This allows for more accurate process health monitoring beyond simple PID checking.

## Components

### 1. HeartbeatManager (`heartbeat_manager.py`)
- **Purpose**: Central manager for heartbeat functionality
- **Functions**:
  - `send_heartbeat(process_name, additional_data)`: Send heartbeat from a process
  - `get_heartbeat_status(process_name)`: Get heartbeat status for a specific process
  - `is_process_alive(process_name, timeout)`: Check if process is alive based on heartbeat

### 2. Enhanced ProcessMonitor (`process_monitor.py`)
- **Purpose**: Monitor processes with both PID detection and heartbeat tracking
- **Features**:
  - Shows time since last heartbeat for each process
  - Displays additional processes that send heartbeats but aren't in the monitored list
  - Enhanced status table with heartbeat information

### 3. Heartbeat Data Storage (`heartbeat_status.json`)
- **Format**: JSON file storing heartbeat data for all processes
- **Location**: Root directory of the project
- **Structure**:
```json
{
  "last_updated": 1703123456.789,
  "processes": {
    "process-name": {
      "last_heartbeat": 1703123456.789,
      "last_heartbeat_formatted": "2023-12-20 15:30:56",
      "pid": 12345,
      "status": "alive",
      "additional_data": "..."
    }
  }
}
```

## Implementation Status

### ✅ Implemented Processes

1. **freelancer-websocket-reader.py**
   - Heartbeat name: `websocket-reader`
   - Frequency: Every 30 seconds
   - Additional data: browser_status, cdp_status, consecutive_failures, messages_processed, etc.

2. **bidder.py**
   - Heartbeat name: `bidder`
   - Frequency: Every 60 seconds  
   - Additional data: status, debug_mode, offset, seen_projects, etc.

3. **vue-frontend/server/index.js**
   - Heartbeat name: `vue-frontend`
   - Frequency: Every 30 seconds
   - Additional data: port, uptime, memory_usage, etc.

### 🔄 To Be Implemented

4. **npm run serve** (Vue Development Server)
   - Heartbeat name: `vue-dev-server` 
   - Would need modification to package.json or vue.config.js

5. **npm run dev** (Development Server)
   - Heartbeat name: `vue-dev-server`
   - Would need modification to development scripts

## Usage

### Starting the Monitor
```bash
python process_monitor.py
```

### Testing the System
```bash
# Run the test script to simulate processes
python test_heartbeat.py

# In another terminal, run the monitor
python process_monitor.py
```

### Example Output
```
📊 PROCESS MONITOR STATUS WITH HEARTBEAT
================================================================================
💻 System: CPU 15.2% | RAM 65.1% (8.4GB free) | Disk 45.2% (125.3GB free)
⏱️  Monitor Runtime: 0:05:23

PROCESS                                  STATUS     PID      RUNTIME         LAST SEEN            HEARTBEAT                
--------------------------------------------------------------------------------
🌐 Vue Frontend (npm run serve)         🔴 STOPPED -        -               -                    ❌ No heartbeat          
⚡ Dev Server (npm run dev)             🔴 STOPPED -        -               -                    ❌ No heartbeat          
🤖 Bidder Script (bidder.py)           🟢 RUNNING 12345    0:04:12         15:30:45             💚 23s ago               
🔗 WebSocket Reader                     🟢 RUNNING 12346    0:04:15         15:30:44             💚 15s ago               

ADDITIONAL HEARTBEAT PROCESSES:
--------------------------------------------------------------------------------
🔍 vue-frontend                         HEARTBEAT   5002     -               -                    💚 8s ago                
🔍 test-process-1                       HEARTBEAT   12347    -               -                    💚 45s ago               
```

## Benefits

### 1. **Real-time Health Monitoring**
- Know exactly when a process last reported its status
- Detect hung processes that are still running but not responding

### 2. **Enhanced Process Information**
- Get additional context about what each process is doing
- Monitor performance metrics, progress, and internal state

### 3. **Better Debugging**
- See detailed process state information
- Track process behavior over time

### 4. **Automatic Cleanup**
- Old heartbeat data is automatically cleaned up
- No accumulation of stale process data

## Configuration

### Heartbeat Timeouts
- Default timeout: 60 seconds
- Processes are considered "dead" if no heartbeat received within timeout
- Configurable per process if needed

### Heartbeat Frequency
- freelancer-websocket-reader.py: 30 seconds
- bidder.py: 60 seconds  
- vue-frontend: 30 seconds
- Adjustable based on process requirements

## Troubleshooting

### Process Shows as Dead Despite Running
- Check if the process is actually sending heartbeats
- Verify heartbeat_status.json file permissions
- Look for error messages in process output

### Heartbeat File Issues
- File is automatically created if missing
- Located in project root directory
- Should be writable by all processes

### Missing Heartbeats
- Check process logs for heartbeat sending errors
- Verify heartbeat_manager.py is accessible
- Ensure proper imports in process files

## Future Enhancements

1. **Web Dashboard**: Real-time web interface for monitoring
2. **Alerts**: Email/Slack notifications for dead processes
3. **Metrics**: Historical data and performance graphs
4. **Auto-restart**: Automatic process restart on failure detection
5. **Remote Monitoring**: Monitor processes across multiple machines 