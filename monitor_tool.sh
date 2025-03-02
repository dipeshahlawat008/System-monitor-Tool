#!/bin/bash

# System Monitoring Tool
# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display header
print_header() {
    clear
    echo -e "${BLUE}=== Linux System Monitoring Tool ===${NC}"
    echo -e "Date: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "------------------------------------"
}

# Function to check CPU usage
check_cpu() {
    echo -e "\n${GREEN}CPU Usage:${NC}"
    echo "----------------"
    # Get CPU usage percentage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}')
    echo "CPU Usage: ${cpu_usage}%"
    
    # Load averages
    echo "Load Average: $(uptime | awk '{print $8,$9,$10}')"
}

# Function to check memory usage
check_memory() {
    echo -e "\n${GREEN}Memory Usage:${NC}"
    echo "----------------"
    free -h | grep -E "Mem:|Swap:" | awk '{print $1" Total: "$2" Used: "$3" Free: "$4}'
}

# Function to check disk usage
check_disk() {
    echo -e "\n${GREEN}Disk Usage:${NC}"
    echo "----------------"
    df -h | grep -E "^/dev/" | awk '{print $1" Mounted on "$6": "$5" used ("$4" free)"}'
}

# Function to check network status
check_network() {
    echo -e "\n${GREEN}Network Status:${NC}"
    echo "----------------"
    # Show network interfaces and their status
    ip -br addr | awk '{print $1": "$3}'
    # Show active connections
    echo -e "\nActive Connections:"
    netstat -tunap 2>/dev/null | grep ESTABLISHED | wc -l | xargs echo "Total established connections:"
}

# Function to check running processes
check_processes() {
    echo -e "\n${GREEN}Processes:${NC}"
    echo "----------------"
    echo "Total running processes: $(ps aux | wc -l)"
    echo -e "\nTop 5 CPU-consuming processes:"
    ps -eo pid,ppid,cmd,%cpu --sort=-%cpu | head -n 6
}

# Function to check system temperature (if sensors available)
check_temperature() {
    if command -v sensors &> /dev/null; then
        echo -e "\n${GREEN}System Temperature:${NC}"
        echo "----------------"
        sensors | grep -E "Core|temp"
    fi
}

# Function to check system info
check_system() {
    echo -e "\n${GREEN}System Info:${NC}"
    echo "----------------"
    echo "Hostname: $(hostname)"
    echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
    echo "Kernel: $(uname -r)"
    echo "Uptime: $(uptime -p)"
}

# Main monitoring loop
monitor_system() {
    while true; do
        print_header
        check_system
        check_cpu
        check_memory
        check_disk
        check_network
        check_processes
        check_temperature
        
        echo -e "\n${YELLOW}Press Ctrl+C to exit, or wait 5 seconds for refresh${NC}"
        sleep 5
    done
}

# Check if script is run with sudo privileges when needed
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Note: Some features might require sudo privileges${NC}"
fi

# Trap Ctrl+C to exit gracefully
trap 'echo -e "\n${RED}Exiting System Monitor...${NC}"; exit 0' INT

# Start monitoring
monitor_system