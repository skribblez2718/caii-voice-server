# CAII Voice Server - Linux Python Version

A Linux HTTP server for sending desktop notifications with optional text-to-speech capabilities using ElevenLabs or Linux TTS engines.

## System Requirements

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip libnotify-bin espeak-ng mpg123 ffmpeg curl

# Fedora
sudo dnf install python3 python3-pip libnotify espeak-ng mpg123 ffmpeg curl

# Arch Linux
sudo pacman -S python python-pip libnotify espeak-ng mpg123 ffmpeg curl
```

**Important:** `ffmpeg` is required for audio playback with `paplay` and as a fallback audio converter. Without it, audio notifications from the session start hook will fail silently.

### UV Package Manager (Recommended)
Install uv for faster Python package management using the official installer:

```bash
# Install uv globally (for regular users)
curl -LsSf https://astral.sh/uv/install.sh | sh

# For the caii-voice-server system user (with /usr/bin/false shell)
sudo -u caii-voice-server bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
```

After installation, uv will be installed to `$HOME/.local/bin` and you can activate the environment:
```bash
# For caii-voice-server user, uv is installed to /home/caii-voice-server/.local/bin
# Activate uv environment with: source $HOME/.local/bin/env
```

Alternative installation methods:
```bash
# Using pipx (if available)
pipx install uv

# Using wget instead of curl
wget -qO- https://astral.sh/uv/install.sh | sh
```

### Python Dependencies (Virtual Environment)
Required Python packages:
- FastAPI (web framework)
- uvicorn (ASGI server)
- httpx (HTTP client for ElevenLabs)
- pydantic (data validation)
- python-dotenv (environment variable loading)

## Quick Setup

For automated installation, use the setup script:
```bash
cd /home/caii-voice-server
sudo ./setup.sh
sudo systemctl start caii-voice-server
```

## Manual Installation

### 1. Install uv for the caii-voice-server user
Since the `caii-voice-server` user has `/usr/bin/false` as their shell, we need to use `bash -c` for the installation:

```bash
# Install uv using the official installer
sudo -u caii-voice-server bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'

# Verify installation (uv installs to $HOME/.local/bin)
sudo -u caii-voice-server bash -c 'source ~/.local/bin/env && uv --version'
```

### 2. Create Virtual Environment and Install Dependencies
```bash
cd /home/caii-voice-server

# Create virtual environment using uv as caii-voice-server user
sudo -u caii-voice-server bash -c 'cd /home/caii-voice-server && source ~/.local/bin/env && uv venv .venv'

# Install dependencies using uv as caii-voice-server user
sudo -u caii-voice-server bash -c 'cd /home/caii-voice-server && source ~/.local/bin/env && uv pip install -r requirements.txt --python .venv/bin/python'
```

### 3. Add caii-voice-server to audio group
```bash
sudo usermod -a -G audio caii-voice-server
```

### 4. Install systemd Service
```bash
sudo cp /home/caii-voice-server/caii-voice-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable caii-voice-server
sudo systemctl start caii-voice-server
```

### 5. Configuration

A template `.env` file is included with sample configuration. Add your ElevenLabs API key:
```bash
sudo bash -c 'echo "ELEVENLABS_API_KEY=your_api_key_here" >> /home/caii-voice-server/.env'
```

You can also edit the `.env` file directly to configure:
- `PORT` - Server port (default: 8888)
- `ELEVENLABS_API_KEY` - Your ElevenLabs API key
- `ELEVENLABS_VOICE_ID` - Specific voice ID to use

Without an API key, the server will use Linux TTS (espeak-ng/espeak/festival) as fallback.

## Service Management

```bash
# Service control
sudo systemctl start caii-voice-server
sudo systemctl stop caii-voice-server
sudo systemctl restart caii-voice-server
sudo systemctl status caii-voice-server

# View logs
journalctl -u caii-voice-server -f
journalctl -u caii-voice-server -n 50
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8888/health
```

### Send Notification
```bash
curl -X POST http://localhost:8888/notify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Notification",
    "message": "Hello from CAII Voice Server",
    "voice_enabled": true,
    "voice_id": "optional_elevenlabs_voice_id"
  }'
```

### Voice Server Notification
```bash
curl -X POST http://localhost:8888/notify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "CAII Voice Server",
    "message": "Task completed successfully"
  }'
```

## Features

### Audio/TTS Support
- **ElevenLabs**: Premium AI voices (requires API key)
- **Linux TTS**: espeak-ng, espeak, festival, spd-say
- **Audio Playback**: mpg123 (recommended), mpv, ffplay, paplay
  - **Note**: `paplay` requires `ffmpeg` for MP3->WAV conversion
  - Session start audio notifications will fail silently without a compatible audio player

### Desktop Notifications
- Uses Linux `notify-send` for desktop notifications
- Works with most Linux desktop environments

### Security
- CORS restricted to localhost
- Input validation and sanitization
- Rate limiting (10 requests/minute per IP)
- Systemd service isolation
- Protected file system access

## File Structure

```
/home/caii-voice-server/
├── server.py                    # Main Python server
├── requirements.txt             # Python dependencies
├── caii-voice-server.service  # systemd service file
├── setup.sh                     # Setup script
├── .env                         # Configuration template
├── .venv/                       # Python virtual environment
├── logs/                        # Log directory
└── README.md                    # This file
```

## Troubleshooting

### Service Issues
```bash
# Check service status
sudo systemctl status caii-voice-server

# View detailed logs
journalctl -u caii-voice-server -f

# Test server manually (as caii-voice-server user)
sudo -u caii-voice-server bash -c 'cd /home/caii-voice-server && .venv/bin/python server.py'
```

### Permission Issues
```bash
# Verify log directory permissions
ls -la /home/caii-voice-server/logs

# Check if caii-voice-server user can write to logs
sudo -u caii-voice-server bash -c 'touch /home/caii-voice-server/logs/test.log && rm /home/caii-voice-server/logs/test.log'
```

### UV Installation Issues
```bash
# If curl fails, try wget
sudo -u caii-voice-server bash -c 'wget -qO- https://astral.sh/uv/install.sh | sh'

# Manual installation if installer fails
sudo mkdir -p /home/caii-voice-server/.local/bin
sudo wget -O /home/caii-voice-server/.local/bin/uv https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu
sudo chmod +x /home/caii-voice-server/.local/bin/uv
sudo chown caii-voice-server:caii-voice-server /home/caii-voice-server/.local/bin/uv

# Test manual installation
sudo -u caii-voice-server bash -c '/home/caii-voice-server/.local/bin/uv --version'
```

### Missing Dependencies
```bash
# Install notification support
sudo apt install libnotify-bin notification-daemon

# Install TTS engine
sudo apt install espeak-ng

# Install audio players for ElevenLabs MP3 playback
# mpg123 is lightweight and recommended
sudo apt install mpg123

# OR install mpv (full-featured player)
sudo apt install mpv

# ffmpeg is REQUIRED if only paplay is available
# (paplay needs ffmpeg to convert MP3 to WAV)
sudo apt install ffmpeg
```

### Virtual Environment Issues
```bash
# Recreate virtual environment if corrupted
sudo -u caii-voice-server bash -c 'cd /home/caii-voice-server && rm -rf .venv'
sudo -u caii-voice-server bash -c 'cd /home/caii-voice-server && source ~/.local/bin/env && uv venv .venv'
sudo -u caii-voice-server bash -c 'cd /home/caii-voice-server && source ~/.local/bin/env && uv pip install -r requirements.txt --python .venv/bin/python'
```

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop caii-voice-server
sudo systemctl disable caii-voice-server
sudo rm /etc/systemd/system/caii-voice-server.service
sudo systemctl daemon-reload

# Remove system user
sudo userdel caii-voice-server

# Remove server files (optional)
sudo rm -rf /home/caii-voice-server
```
