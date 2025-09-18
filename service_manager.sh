#!/bin/bash

# Presence Sensor Service Manager
# Usage: ./service_manager.sh [install|start|stop|restart|status|kill|logs]

SERVICE_NAME="presence-sensor"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root for safety reasons."
        print_error "It will use sudo when needed."
        exit 1
    fi
}

install_service() {
    print_status "Installing presence sensor service..."

    # Create the service file
    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Presence Detection TV Control
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$SCRIPT_DIR
Environment=PATH=$SCRIPT_DIR/venv/bin
ExecStart=$SCRIPT_DIR/venv/bin/python presence_sensor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    if [ $? -eq 0 ]; then
        print_status "Service file created at $SERVICE_FILE"

        # Reload systemd and enable service
        sudo systemctl daemon-reload
        sudo systemctl enable "$SERVICE_NAME"

        print_status "Service installed and enabled successfully!"
        print_status "Use './service_manager.sh start' to start the service"
    else
        print_error "Failed to create service file"
        exit 1
    fi
}

start_service() {
    print_status "Starting $SERVICE_NAME service..."
    sudo systemctl start "$SERVICE_NAME"

    if [ $? -eq 0 ]; then
        print_status "Service started successfully!"
        sleep 2
        show_status
    else
        print_error "Failed to start service"
        exit 1
    fi
}

stop_service() {
    print_status "Stopping $SERVICE_NAME service..."
    sudo systemctl stop "$SERVICE_NAME"

    if [ $? -eq 0 ]; then
        print_status "Service stopped successfully!"
    else
        print_error "Failed to stop service"
        exit 1
    fi
}

restart_service() {
    print_status "Restarting $SERVICE_NAME service..."
    sudo systemctl restart "$SERVICE_NAME"

    if [ $? -eq 0 ]; then
        print_status "Service restarted successfully!"
        sleep 2
        show_status
    else
        print_error "Failed to restart service"
        exit 1
    fi
}

kill_service() {
    print_warning "Force killing $SERVICE_NAME service and disabling it..."

    # Stop the service
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null

    # Disable the service
    sudo systemctl disable "$SERVICE_NAME" 2>/dev/null

    # Kill any remaining processes
    pkill -f "presence_sensor.py" 2>/dev/null

    print_status "Service killed and disabled"
    print_warning "Use './service_manager.sh install' to reinstall if needed"
}

show_status() {
    print_status "Service status:"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l
}

show_logs() {
    print_status "Recent service logs (press Ctrl+C to exit):"
    journalctl -u "$SERVICE_NAME" -f
}

uninstall_service() {
    print_warning "Uninstalling $SERVICE_NAME service..."

    # Stop and disable service
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null
    sudo systemctl disable "$SERVICE_NAME" 2>/dev/null

    # Remove service file
    if [ -f "$SERVICE_FILE" ]; then
        sudo rm "$SERVICE_FILE"
        print_status "Service file removed"
    fi

    # Reload systemd
    sudo systemctl daemon-reload
    sudo systemctl reset-failed

    print_status "Service uninstalled successfully"
}

show_help() {
    echo "Presence Sensor Service Manager"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install    Install the systemd service"
    echo "  start      Start the service"
    echo "  stop       Stop the service"
    echo "  restart    Restart the service"
    echo "  status     Show service status"
    echo "  kill       Force kill and disable the service"
    echo "  logs       Show live service logs"
    echo "  uninstall  Remove the service completely"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 install    # Install and enable the service"
    echo "  $0 start      # Start the presence detection"
    echo "  $0 logs       # Monitor what's happening"
    echo "  $0 kill       # Emergency stop everything"
}

# Main script logic
check_root

case "${1:-help}" in
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
    kill)
        kill_service
        ;;
    logs)
        show_logs
        ;;
    uninstall)
        uninstall_service
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac