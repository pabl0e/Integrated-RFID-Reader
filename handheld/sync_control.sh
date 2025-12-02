#!/bin/bash
"""
RFID Auto-Sync Service Control Script
Manages the automated database synchronization service
"""

SERVICE_NAME="rfid-autosync"
SERVICE_FILE="rfid-autosync.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/rfid_sync.log"
STATUS_FILE="/tmp/rfid_sync_status.json"

show_usage() {
    echo "RFID Auto-Sync Service Control"
    echo "Usage: $0 {install|start|stop|restart|status|logs|uninstall}"
    echo ""
    echo "Commands:"
    echo "  install   - Install and enable the auto-sync service"
    echo "  start     - Start the auto-sync service"
    echo "  stop      - Stop the auto-sync service"
    echo "  restart   - Restart the auto-sync service"
    echo "  status    - Show service status and sync information"
    echo "  logs      - Show recent service logs"
    echo "  uninstall - Stop and remove the auto-sync service"
}

install_service() {
    echo "Installing RFID Auto-Sync Service..."
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        echo "Error: Installation requires root privileges. Run with sudo."
        exit 1
    fi
    
    # Copy service file to systemd directory
    cp "$SCRIPT_DIR/$SERVICE_FILE" /etc/systemd/system/
    
    # Create log file with proper permissions
    touch $LOG_FILE
    chown binslibal:binslibal $LOG_FILE
    chmod 664 $LOG_FILE
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    echo "✅ Service installed successfully"
    echo "Use 'sudo $0 start' to start the service"
}

start_service() {
    echo "Starting RFID Auto-Sync Service..."
    systemctl start $SERVICE_NAME
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "✅ Service started successfully"
    else
        echo "❌ Failed to start service"
        systemctl status $SERVICE_NAME
    fi
}

stop_service() {
    echo "Stopping RFID Auto-Sync Service..."
    systemctl stop $SERVICE_NAME
    echo "✅ Service stopped"
}

restart_service() {
    echo "Restarting RFID Auto-Sync Service..."
    systemctl restart $SERVICE_NAME
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "✅ Service restarted successfully"
    else
        echo "❌ Failed to restart service"
        systemctl status $SERVICE_NAME
    fi
}

show_status() {
    echo "=== RFID Auto-Sync Service Status ==="
    echo ""
    
    # Service status
    echo "Service Status:"
    systemctl status $SERVICE_NAME --no-pager -l
    echo ""
    
    # Sync status from file
    if [ -f "$STATUS_FILE" ]; then
        echo "Sync Status:"
        cat $STATUS_FILE | python3 -m json.tool
        echo ""
    fi
    
    # Recent sync activity
    echo "Recent Activity (last 10 lines):"
    if [ -f "$LOG_FILE" ]; then
        tail -n 10 $LOG_FILE
    else
        echo "No log file found"
    fi
}

show_logs() {
    echo "=== RFID Auto-Sync Service Logs ==="
    echo "Press Ctrl+C to exit log view"
    echo ""
    
    if [ -f "$LOG_FILE" ]; then
        tail -f $LOG_FILE
    else
        echo "No log file found. Showing systemd journal:"
        journalctl -u $SERVICE_NAME -f
    fi
}

uninstall_service() {
    echo "Uninstalling RFID Auto-Sync Service..."
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        echo "Error: Uninstallation requires root privileges. Run with sudo."
        exit 1
    fi
    
    # Stop and disable service
    systemctl stop $SERVICE_NAME 2>/dev/null
    systemctl disable $SERVICE_NAME 2>/dev/null
    
    # Remove service file
    rm -f /etc/systemd/system/$SERVICE_FILE
    
    # Reload systemd
    systemctl daemon-reload
    
    echo "✅ Service uninstalled successfully"
}

manual_sync() {
    echo "Performing manual sync..."
    python3 "$SCRIPT_DIR/auto_sync_service.py" --manual-sync
}

case "$1" in
    install)
        install_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    uninstall)
        uninstall_service
        ;;
    sync)
        manual_sync
        ;;
    *)
        show_usage
        exit 1
        ;;
esac