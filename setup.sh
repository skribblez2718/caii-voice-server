#!/bin/bash
# CAII Voice Server Setup Script
# Deploys and configures the voice server to run in /home/caii-voice-server/

set -e

echo "🔧 Setting up CAII Voice Server..."

# Determine source directory (where this script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_DIR="/home/caii-voice-server"

# Detect Python command and version
echo "🐍 Detecting Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python is not installed"
    echo "   Please install Python 3.x and try again"
    exit 1
fi

# Get Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

# Verify Python 3.x
if [ "$PYTHON_MAJOR" -ne 3 ]; then
    echo "❌ Error: Python 3.x is required (found Python $PYTHON_VERSION)"
    exit 1
fi

echo "✅ Found Python $PYTHON_VERSION at $(command -v $PYTHON_CMD)"

# Create system user and group
echo "📝 Creating caii-voice-server system user..."
if ! id caii-voice-server &>/dev/null; then
    sudo useradd --system --shell /bin/false --home-dir ${TARGET_DIR} --create-home caii-voice-server
    echo "✅ Created caii-voice-server user with home at ${TARGET_DIR}"
else
    echo "ℹ️  caii-voice-server user already exists"
    # Ensure home directory exists
    if [ ! -d "${TARGET_DIR}" ]; then
        sudo mkdir -p ${TARGET_DIR}
        sudo chown caii-voice-server:caii-voice-server ${TARGET_DIR}
        echo "✅ Created home directory at ${TARGET_DIR}"
    fi
    # Ensure shell is set to /bin/false
    sudo usermod --shell /bin/false caii-voice-server
fi

# Add to audio group for TTS/audio access
echo "🔊 Adding caii-voice-server to audio group..."
sudo usermod -a -G audio caii-voice-server

# Deploy application files to target directory
echo "📦 Deploying application files to ${TARGET_DIR}..."
sudo cp ${SCRIPT_DIR}/server.py ${TARGET_DIR}/
sudo cp ${SCRIPT_DIR}/requirements.txt ${TARGET_DIR}/
sudo chmod 644 ${TARGET_DIR}/server.py
sudo chmod 644 ${TARGET_DIR}/requirements.txt

# Handle .env file (don't overwrite if exists)
if [ -f "${TARGET_DIR}/.env" ]; then
    echo "ℹ️  .env already exists - preserving existing configuration"
else
    if [ -f "${SCRIPT_DIR}/.env.example" ]; then
        sudo cp ${SCRIPT_DIR}/.env.example ${TARGET_DIR}/.env
        sudo chmod 640 ${TARGET_DIR}/.env
        echo "📝 Created .env from template (edit with your API keys)"
    else
        echo "⚠️  No .env.example found - you'll need to create .env manually"
    fi
fi

# Set ownership for all deployed files
sudo chown -R caii-voice-server:caii-voice-server ${TARGET_DIR}

# Set up log directory
echo "📁 Setting up log directory..."
sudo mkdir -p ${TARGET_DIR}/logs
sudo chown caii-voice-server:caii-voice-server ${TARGET_DIR}/logs
sudo chmod 775 ${TARGET_DIR}/logs

# Set default ACL for new files in the log directory
if command -v setfacl &> /dev/null; then
    sudo setfacl -d -m user:caii-voice-server:rw ${TARGET_DIR}/logs
    sudo setfacl -d -m group:caii-voice-server:rw ${TARGET_DIR}/logs
    echo "✅ ACL permissions set for log directory"
else
    echo "⚠️  setfacl not found - install acl package for better permissions"
fi

# Install uv for caii-voice-server user
echo "⚡ Installing uv package manager for caii-voice-server user..."
UV_PATH="${TARGET_DIR}/.local/bin/uv"
if [ -f "${UV_PATH}" ]; then
    echo "ℹ️  uv already installed at ${UV_PATH}"
else
    # Install uv as caii-voice-server user with explicit HOME
    sudo -H -u caii-voice-server HOME="${TARGET_DIR}" bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"

    # Wait a moment for installation to complete
    sleep 2

    # Verify installation by checking file existence and executability
    if [ -f "${UV_PATH}" ] && [ -x "${UV_PATH}" ]; then
        echo "✅ uv installed successfully at ${UV_PATH}"
    else
        echo "❌ Error: uv installation failed (executable not found at ${UV_PATH})"
        echo "   Falling back to pip for dependency installation"
    fi
fi

# Set up virtual environment
echo "🔧 Setting up virtual environment..."
if [ -d "${TARGET_DIR}/.venv" ]; then
    echo "ℹ️  Virtual environment already exists - updating..."
    sudo rm -rf ${TARGET_DIR}/.venv
fi

# Create new virtual environment using uv (faster) or python venv
if [ -f "${UV_PATH}" ]; then
    sudo -H -u caii-voice-server bash -c "env PATH='${TARGET_DIR}/.local/bin:$PATH' uv venv ${TARGET_DIR}/.venv --python $PYTHON_CMD"
    echo "✅ Virtual environment created with uv"
else
    sudo -H -u caii-voice-server bash -c "$PYTHON_CMD -m venv ${TARGET_DIR}/.venv"
    echo "✅ Virtual environment created with python venv"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if [ -f "${UV_PATH}" ]; then
    sudo -H -u caii-voice-server bash -c "env PATH='${TARGET_DIR}/.local/bin:${TARGET_DIR}/.venv/bin:$PATH' uv pip install -r ${TARGET_DIR}/requirements.txt"
    echo "✅ Dependencies installed with uv"
else
    sudo -H -u caii-voice-server bash -c "${TARGET_DIR}/.venv/bin/pip install -r ${TARGET_DIR}/requirements.txt"
    echo "⚠️  Dependencies installed with pip (uv not available)"
fi

# Install systemd service
echo "🔧 Installing systemd service..."
sudo cp ${SCRIPT_DIR}/caii-voice-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable caii-voice-server
echo "✅ Service installed and enabled"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Deployment Summary:"
echo "   • User: caii-voice-server"
echo "   • Home: ${TARGET_DIR}"
echo "   • Logs: ${TARGET_DIR}/logs"
echo "   • Python: $PYTHON_CMD ($PYTHON_VERSION)"
if [ -f "${UV_PATH}" ]; then
    echo "   • Package Manager: uv (${UV_PATH})"
else
    echo "   • Package Manager: pip (fallback)"
fi
echo ""
echo "🔑 Next steps:"
echo "  1. Add your ElevenLabs API credentials to .env:"
echo "     sudo nano ${TARGET_DIR}/.env"
echo ""
echo "  2. Start the service:"
echo "     sudo systemctl start caii-voice-server"
echo ""
echo "  3. Check service status:"
echo "     sudo systemctl status caii-voice-server"
echo ""
echo "  4. View logs:"
echo "     sudo journalctl -u caii-voice-server -f"
echo ""
echo "  5. Test the service:"
echo "     curl http://localhost:<PORT>/health"
echo ""
echo "💡 To update the application, run this setup script again"
