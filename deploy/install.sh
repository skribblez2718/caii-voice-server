#!/bin/bash
# CAII Voice Server Setup Script
# Deploys and configures the voice server to run in /home/caii-voice-server/

set -e

echo "🔧 Setting up CAII Voice Server..."

# Determine source directory (where this script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Project root is parent of deploy directory
PROJECT_DIR="$( cd "${SCRIPT_DIR}/.." && pwd )"
TARGET_DIR="/home/caii-voice-server"

echo "📁 Source: ${PROJECT_DIR}"
echo "📁 Target: ${TARGET_DIR}"

# Detect latest system Python (not pyenv/user-specific)
echo "🐍 Detecting system Python installation..."
PYTHON_CMD=""

# Check for system Python versions in order of preference (newest first)
for py_version in python3.13 python3.12 python3.11 python3.10; do
    if [ -x "/usr/bin/${py_version}" ]; then
        PYTHON_CMD="/usr/bin/${py_version}"
        break
    fi
done

# Fallback to generic python3 in /usr/bin
if [ -z "$PYTHON_CMD" ] && [ -x "/usr/bin/python3" ]; then
    PYTHON_CMD="/usr/bin/python3"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ Error: No system Python 3.x found in /usr/bin/"
    echo "   Please install Python 3.10+ and try again"
    exit 1
fi

# Get Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

# Verify Python 3.10+
if [ "$PYTHON_MAJOR" -ne 3 ] || [ "$PYTHON_MINOR" -lt 10 ]; then
    echo "❌ Error: Python 3.10+ is required (found Python $PYTHON_VERSION)"
    exit 1
fi

echo "✅ Found Python $PYTHON_VERSION at $PYTHON_CMD"

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

# Copy main entry point
sudo cp ${PROJECT_DIR}/main.py ${TARGET_DIR}/
sudo chmod 644 ${TARGET_DIR}/main.py

# Copy app module directory
sudo rm -rf ${TARGET_DIR}/app
sudo cp -r ${PROJECT_DIR}/app ${TARGET_DIR}/
# Remove __pycache__ directories to avoid stale bytecode with wrong paths
sudo find ${TARGET_DIR}/app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
sudo chmod -R 755 ${TARGET_DIR}/app
sudo find ${TARGET_DIR}/app -type f -name "*.py" -exec chmod 644 {} \;

# Copy voices directory (config and audio files)
sudo rm -rf ${TARGET_DIR}/voices
sudo cp -r ${PROJECT_DIR}/voices ${TARGET_DIR}/
sudo chmod 755 ${TARGET_DIR}/voices
sudo find ${TARGET_DIR}/voices -type f -exec chmod 644 {} \;
WAV_COUNT=$(sudo find ${TARGET_DIR}/voices -name "*.wav" 2>/dev/null | wc -l)
echo "✅ Voices directory copied (${WAV_COUNT} audio files)"

# Copy dependency files
sudo cp ${PROJECT_DIR}/pyproject.toml ${TARGET_DIR}/
sudo chmod 644 ${TARGET_DIR}/pyproject.toml
if [ -f "${PROJECT_DIR}/uv.lock" ]; then
    sudo cp ${PROJECT_DIR}/uv.lock ${TARGET_DIR}/
    sudo chmod 644 ${TARGET_DIR}/uv.lock
fi
if [ -f "${PROJECT_DIR}/requirements.txt" ]; then
    sudo cp ${PROJECT_DIR}/requirements.txt ${TARGET_DIR}/
    sudo chmod 644 ${TARGET_DIR}/requirements.txt
fi

# Handle .env file (don't overwrite if exists)
if [ -f "${TARGET_DIR}/.env" ]; then
    echo "ℹ️  .env already exists - preserving existing configuration"
else
    if [ -f "${PROJECT_DIR}/.env.example" ]; then
        sudo cp ${PROJECT_DIR}/.env.example ${TARGET_DIR}/.env
        sudo chmod 640 ${TARGET_DIR}/.env
        echo "📝 Created .env from template (edit to configure)"
    else
        echo "⚠️  No .env.example found - you'll need to create .env manually"
    fi
fi

# Set ownership for all deployed files
sudo chown -R caii-voice-server:caii-voice-server ${TARGET_DIR}

# Verify deployment
echo "📋 Deployed files:"
echo "   • main.py"
echo "   • app/ ($(sudo find ${TARGET_DIR}/app -name '*.py' | wc -l) Python files)"
echo "   • voices/ ($(sudo find ${TARGET_DIR}/voices -name '*.wav' 2>/dev/null | wc -l) audio files + voices.json)"
echo "   • pyproject.toml"
[ -f "${TARGET_DIR}/uv.lock" ] && echo "   • uv.lock"
[ -f "${TARGET_DIR}/requirements.txt" ] && echo "   • requirements.txt"
echo "   • .env"

# Set up log directory
echo "📁 Setting up log directory..."
sudo mkdir -p ${TARGET_DIR}/logs
sudo chown caii-voice-server:caii-voice-server ${TARGET_DIR}/logs
sudo chmod 775 ${TARGET_DIR}/logs

# Set up cache directory (for numba JIT compilation cache)
echo "📁 Setting up cache directory..."
sudo mkdir -p ${TARGET_DIR}/.cache/numba
sudo chown -R caii-voice-server:caii-voice-server ${TARGET_DIR}/.cache
sudo chmod -R 775 ${TARGET_DIR}/.cache

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
UV_ENV_FILE="${TARGET_DIR}/.local/bin/env"
if sudo -H -u caii-voice-server bash -c "source '${UV_ENV_FILE}' 2>/dev/null && uv --version" &>/dev/null; then
    UV_VERSION=$(sudo -H -u caii-voice-server bash -c "source '${UV_ENV_FILE}' && uv --version" 2>/dev/null)
    echo "ℹ️  uv already installed (${UV_VERSION})"
else
    # Install uv as caii-voice-server user with explicit HOME
    sudo -H -u caii-voice-server HOME="${TARGET_DIR}" bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"

    # Wait a moment for installation to complete
    sleep 2

    # Verify installation by running uv as the target user with sourced env
    if sudo -H -u caii-voice-server bash -c "source '${UV_ENV_FILE}' && uv --version" &>/dev/null; then
        UV_VERSION=$(sudo -H -u caii-voice-server bash -c "source '${UV_ENV_FILE}' && uv --version" 2>/dev/null)
        echo "✅ uv installed successfully (${UV_VERSION})"
    else
        echo "❌ Error: uv installation failed"
        echo "   Check that curl can reach https://astral.sh/uv/install.sh"
        exit 1
    fi
fi

# Set up virtual environment and install dependencies
echo "🔧 Setting up virtual environment and installing dependencies..."
if [ -d "${TARGET_DIR}/.venv" ]; then
    echo "ℹ️  Virtual environment already exists - recreating..."
    sudo rm -rf ${TARGET_DIR}/.venv
fi

# uv sync creates venv and installs all dependencies from pyproject.toml
sudo -H -u caii-voice-server bash -c "source '${UV_ENV_FILE}' && cd ${TARGET_DIR} && uv sync --python $PYTHON_CMD"
echo "✅ Virtual environment created and dependencies installed"

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
echo "   • Voices: ${TARGET_DIR}/voices"
echo "   • Cache: ${TARGET_DIR}/.cache (numba JIT cache)"
echo "   • Python: $PYTHON_CMD ($PYTHON_VERSION)"
echo "   • Package Manager: uv"
# Read HOST and PORT from .env for display
ENV_HOST=$(sudo grep -E "^HOST=" ${TARGET_DIR}/.env 2>/dev/null | cut -d'=' -f2)
ENV_PORT=$(sudo grep -E "^PORT=" ${TARGET_DIR}/.env 2>/dev/null | cut -d'=' -f2)
# Use defaults if empty
ENV_HOST=${ENV_HOST:-127.0.0.1}
ENV_PORT=${ENV_PORT:-8001}

echo ""
echo "🔑 Next steps:"
echo "  1. Configure the server (REQUIRED - set model paths):"
echo "     sudo nano ${TARGET_DIR}/.env"
echo "     - Set TTS_BASE_MODEL_PATH and TTS_VOICE_DESIGN_MODEL_PATH"
echo "     - Optionally set VOICE_SERVER_API_KEY for authentication"
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
echo "     curl http://${ENV_HOST}:${ENV_PORT}/health"
echo ""
echo "💡 To update the application, run this setup script again"
