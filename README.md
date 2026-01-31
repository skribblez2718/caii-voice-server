# CAII Voice Server

A modular FastAPI server for Text-to-Speech (TTS) and Speech-to-Text (STT) using local AI models:
- **TTS**: Qwen-TTS for voice cloning and voice creation
- **STT**: Faster-Whisper for speech transcription

## Features

- **Voice Cloning**: Clone voices from reference audio files
- **Voice Creation**: Generate new voices from text descriptions using VoiceDesign
- **Speech-to-Text**: Transcribe audio using local Whisper models
- **Agent Voice Mapping**: Pre-configured voices for different AI agents
- **API Key Authentication**: Optional API key protection
- **Rate Limiting**: Configurable per-IP rate limiting
- **OpenAI-Compatible API**: Drop-in replacement for OpenAI TTS/STT endpoints

## System Requirements

### Hardware
- NVIDIA GPU with CUDA support (recommended)
- Minimum 8GB VRAM for TTS models
- 16GB+ RAM recommended

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip python3-venv ffmpeg

# For audio processing
sudo apt install libsndfile1
```

### AI Models Required
Download and place these models locally:
- **Qwen3-TTS-12Hz-1.7B-Base** - For voice cloning
- **Qwen3-TTS-12Hz-1.7B-VoiceDesign** - For voice creation

## Quick Setup

Use the automated setup script:
```bash
cd /path/to/caii-voice-server
sudo ./deploy/setup.sh
```

Then configure the server:
```bash
sudo nano /home/caii-voice-server/.env
# Set TTS_BASE_MODEL_PATH and TTS_VOICE_DESIGN_MODEL_PATH
```

Start the service:
```bash
sudo systemctl start caii-voice-server
```

## Configuration

All configuration is done via environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server bind address | `127.0.0.1` |
| `PORT` | Server port | `8001` |
| `VOICE_SERVER_API_KEY` | API key for authentication (optional) | None (auth disabled) |
| `VOICES_DIRECTORY` | Directory containing voice files | `./voices` |
| `TTS_BASE_MODEL_PATH` | Path to Qwen-TTS Base model | **Required** |
| `TTS_VOICE_DESIGN_MODEL_PATH` | Path to Qwen-TTS VoiceDesign model | **Required** |
| `STT_MODEL_NAME` | Whisper model size (tiny/base/small/medium/large) | `base` |
| `STT_DEVICE` | Device for STT (cuda/cpu) | `cuda` |
| `STT_COMPUTE_TYPE` | Compute type for STT | `float16` |
| `RATE_LIMIT_REQUESTS` | Max requests per window | `10` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate limit window | `60` |

## API Endpoints

### Health Check
```bash
curl http://localhost:8001/health
```

### Text-to-Speech (OpenAI-compatible)
```bash
curl -X POST http://localhost:8001/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "model": "tts-1",
    "input": "Hello, how are you today?",
    "voice": "alloy",
    "agent": "da"
  }' \
  --output speech.wav
```

The `agent` parameter selects which pre-configured voice to use.

### Speech-to-Text (OpenAI-compatible)
```bash
curl -X POST http://localhost:8001/v1/audio/transcriptions \
  -H "X-API-Key: your-api-key" \
  -F "file=@audio.wav" \
  -F "model=whisper-1"
```

### List Voices
```bash
curl http://localhost:8001/v1/voices \
  -H "X-API-Key: your-api-key"
```

### Create New Voice
```bash
curl -X POST http://localhost:8001/v1/voices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "agent_name": "custom",
    "instruct": "Female, mid-twenties. Warm, friendly timbre with natural mid-range pitch."
  }' \
  --output custom.wav
```

### Reload Voices
```bash
curl -X POST http://localhost:8001/v1/voices/reload \
  -H "X-API-Key: your-api-key"
```

## Pre-configured Agent Voices

| Agent | Description |
|-------|-------------|
| `da` | Female, mid-thirties. Warm, smooth timbre with clear mid-range pitch |
| `analysis` | Male, early thirties. Sharp, focused timbre with clear mid-range pitch |
| `clarification` | Female, late twenties. Clear, gentle timbre with slightly bright mid-range pitch |
| `memory` | Male, mid-fifties. Rich, grounded timbre with warm low-mid pitch |
| `research` | Male, early forties. Warm, scholarly timbre with natural mid-range pitch |
| `synthesis` | Female, mid-forties. Smooth, harmonious timbre with calm mid-range pitch |
| `verification` | Female, late thirties. Crisp, confident timbre with clear mid-range pitch |

## File Structure

```
caii-voice-server/
├── main.py                     # Application entry point
├── app/
│   ├── __init__.py             # App factory with lifespan
│   ├── config.py               # Pydantic settings configuration
│   ├── dependencies.py         # Model loading & voice prompt caching
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py     # Route aggregation
│   │       ├── tts.py          # POST /v1/audio/speech
│   │       ├── stt.py          # POST /v1/audio/transcriptions
│   │       ├── voice.py        # Voice management endpoints
│   │       └── health.py       # Health check endpoints
│   └── middleware/
│       ├── __init__.py
│       ├── auth.py             # API key validation
│       └── rate_limit.py       # Rate limiting
├── voices/
│   ├── voices.json             # Voice metadata configuration
│   └── *.wav                   # Voice reference audio files
├── deploy/
│   ├── setup.sh                # Automated installation script
│   ├── uninstall.sh            # Complete removal script
│   └── caii-voice-server.service  # Systemd service file
├── .env.example                # Configuration template
├── pyproject.toml              # Python dependencies
└── README.md                   # This file
```

## Service Management

```bash
# Start/stop/restart
sudo systemctl start caii-voice-server
sudo systemctl stop caii-voice-server
sudo systemctl restart caii-voice-server

# Check status
sudo systemctl status caii-voice-server

# View logs
sudo journalctl -u caii-voice-server -f
sudo journalctl -u caii-voice-server -n 50
```

## Development

### Local Setup
```bash
# Clone and enter directory
cd caii-voice-server

# Create virtual environment
uv venv

# Install dependencies
uv sync

# Create .env from template
cp .env.example .env
# Edit .env to set model paths

# Run locally
python main.py
```

### Testing
```bash
# Health check
curl http://localhost:8001/health

# Test TTS
curl -X POST http://localhost:8001/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello world", "agent": "da"}' \
  --output test.wav

# Play audio
aplay test.wav
```

## Troubleshooting

### Service Issues
```bash
# Check service status
sudo systemctl status caii-voice-server

# View detailed logs
sudo journalctl -u caii-voice-server -f

# Test server manually
sudo -u caii-voice-server bash -c 'cd /home/caii-voice-server && .venv/bin/python main.py'
```

### Model Loading Issues
```bash
# Verify model paths in .env
sudo cat /home/caii-voice-server/.env | grep MODEL

# Check if models exist
ls -la /path/to/Qwen3-TTS-12Hz-1.7B-Base
ls -la /path/to/Qwen3-TTS-12Hz-1.7B-VoiceDesign
```

### Permission Issues
```bash
# Verify directory ownership
ls -la /home/caii-voice-server/

# Fix ownership if needed
sudo chown -R caii-voice-server:caii-voice-server /home/caii-voice-server
```

### CUDA/GPU Issues
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Check GPU memory
nvidia-smi
```

## Uninstallation

Use the automated uninstall script:
```bash
sudo ./deploy/uninstall.sh
```

This will:
- Stop and disable the systemd service
- Remove the service file
- Delete the application directory (`/home/caii-voice-server`)
- Remove the `caii-voice-server` system user and group

**Note**: The uninstall script does not remove:
- System Python or packages
- The source project directory
- External AI model files

## License

See [LICENSE](LICENSE) file.
