#!/bin/bash
# CAII Voice Server Uninstall Script
# Completely removes the voice server installation

set -e

echo "🗑️  Uninstalling CAII Voice Server..."
echo ""

TARGET_DIR="/home/caii-voice-server"
SERVICE_NAME="caii-voice-server"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# Confirmation prompt
read -p "⚠️  This will completely remove the CAII Voice Server. Are you sure? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Uninstall cancelled."
    exit 0
fi

echo ""

# Stop and disable the systemd service
echo "🛑 Stopping and disabling service..."
if systemctl is-active --quiet ${SERVICE_NAME} 2>/dev/null; then
    sudo systemctl stop ${SERVICE_NAME}
    echo "   ✓ Service stopped"
else
    echo "   ℹ️  Service was not running"
fi

if systemctl is-enabled --quiet ${SERVICE_NAME} 2>/dev/null; then
    sudo systemctl disable ${SERVICE_NAME}
    echo "   ✓ Service disabled"
else
    echo "   ℹ️  Service was not enabled"
fi

# Remove the systemd service file
echo "📄 Removing service file..."
if [ -f "${SERVICE_FILE}" ]; then
    sudo rm -f ${SERVICE_FILE}
    sudo systemctl daemon-reload
    echo "   ✓ Service file removed"
else
    echo "   ℹ️  Service file not found"
fi

# Remove the application directory
echo "📁 Removing application directory..."
if [ -d "${TARGET_DIR}" ]; then
    # Show what will be deleted
    echo "   Contents to be removed:"
    sudo ls -la ${TARGET_DIR} 2>/dev/null | head -10 || true
    if [ $(sudo ls -la ${TARGET_DIR} 2>/dev/null | wc -l) -gt 11 ]; then
        echo "   ... and more"
    fi

    sudo rm -rf ${TARGET_DIR}
    echo "   ✓ Application directory removed"
else
    echo "   ℹ️  Application directory not found"
fi

# Remove the system user and group
echo "👤 Removing system user..."
if id ${SERVICE_NAME} &>/dev/null; then
    sudo userdel ${SERVICE_NAME}
    echo "   ✓ User '${SERVICE_NAME}' removed"
else
    echo "   ℹ️  User '${SERVICE_NAME}' not found"
fi

# Remove group if it still exists (userdel should remove it, but just in case)
if getent group ${SERVICE_NAME} &>/dev/null; then
    sudo groupdel ${SERVICE_NAME} 2>/dev/null || true
    echo "   ✓ Group '${SERVICE_NAME}' removed"
fi

# Clean up any remaining systemd artifacts
echo "🧹 Cleaning up systemd..."
sudo systemctl reset-failed ${SERVICE_NAME} 2>/dev/null || true

echo ""
echo "✅ Uninstall complete!"
echo ""
echo "📋 Summary of removed items:"
echo "   • Service: ${SERVICE_NAME}"
echo "   • Service file: ${SERVICE_FILE}"
echo "   • User/Group: ${SERVICE_NAME}"
echo "   • Directory: ${TARGET_DIR}"
echo ""
echo "💡 Note: This script does not remove:"
echo "   • System Python or packages"
echo "   • The source project directory"
echo "   • Any external model files"
