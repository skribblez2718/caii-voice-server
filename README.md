# CAII Voice Server

A modular FastAPI server for Text-to-Speech (TTS) and Speech-to-Text (STT) using local AI models:
- **TTS**: Qwen3-TTS (1.7B parameters) for voice cloning and voice creation
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

Both **GPU** and **CPU** execution modes are supported.

| Component | Requirement |
|-----------|-------------|
| **GPU** (optional) | NVIDIA with CUDA support (RTX 3060+ recommended) |
| **VRAM** | 6-8GB for Qwen3-TTS-1.7B; 2-10GB for Whisper (model dependent) |
| **CPU** | 4+ cores (8+ recommended for CPU-only mode) |
| **RAM** | 16GB minimum, 32GB recommended |
| **Storage** | 20GB+ free for models |

> **Note**: For CPU-only STT, set `STT_DEVICE=cpu` and `STT_COMPUTE_TYPE=int8`. Smaller Whisper models (tiny, base, small) perform well on CPU.

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip python3-venv ffmpeg

# For audio processing
sudo apt install libsndfile1
```

### AI Models Required

Download and place these models in your models directory:

| Model | Purpose | Size |
|-------|---------|------|
| **Qwen3-TTS-12Hz-1.7B-Base** | Voice cloning from reference audio | ~3.4GB |
| **Qwen3-TTS-12Hz-1.7B-VoiceDesign** | Voice creation from text descriptions | ~3.4GB |
| **Qwen3-TTS-Tokenizer-12Hz** | Shared tokenizer (required) | ~1MB |

Models can be downloaded from [Hugging Face](https://huggingface.co/Qwen).

## Quick Setup

Use the automated setup script:
```bash
cd /path/to/caii-voice-server
sudo ./deploy/install.sh
```

## Configuration

Configure the server **before** starting the service:
```bash
sudo nano /home/caii-voice-server/.env
```

Example model paths:
```bash
TTS_BASE_MODEL_PATH=/path/to/models/Qwen3-TTS-12Hz-1.7B-Base
TTS_VOICE_DESIGN_MODEL_PATH=/path/to/models/Qwen3-TTS-12Hz-1.7B-VoiceDesign
```

All configuration is done via environment variables in `.env`:

### Server Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server bind address | `127.0.0.1` |
| `PORT` | Server port | `8001` |
| `VOICE_SERVER_API_KEY` | API key for authentication (optional) | None |
| `RATE_LIMIT_REQUESTS` | Max requests per window | `10` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate limit window | `60` |

### TTS Settings (Qwen3-TTS)

| Variable | Description | Default |
|----------|-------------|---------|
| `TTS_BASE_MODEL_PATH` | Path to Qwen-TTS Base model | **Required** |
| `TTS_VOICE_DESIGN_MODEL_PATH` | Path to Qwen-TTS VoiceDesign model | **Required** |
| `VOICES_DIRECTORY` | Directory containing voice files | `./voices` |

### STT Settings (Faster-Whisper)

| Variable | Description | Default |
|----------|-------------|---------|
| `STT_MODEL_NAME` | Model: tiny, base, small, medium, large-v2, large-v3, turbo | `base` |
| `STT_DEVICE` | Device: cuda, cpu, auto | `cuda` |
| `STT_COMPUTE_TYPE` | Compute: int8, int8_float16, float16, auto | `float16` |
| `STT_BEAM_SIZE` | Beam search width (1-10, higher = more accurate) | `5` |
| `STT_BEST_OF` | Candidate sequences to consider (1-10) | `5` |
| `STT_VAD_FILTER` | Voice Activity Detection to skip silence | `true` |

## Starting the Service

After configuration, start and enable the service:
```bash
# Start the service
sudo systemctl start caii-voice-server

# Enable auto-start on boot
sudo systemctl enable caii-voice-server
```

## API Endpoints

### Health Check

Returns server health status and loaded model information.

```bash
curl http://localhost:8001/health
```

**Response**: JSON object with server status and model availability.

---

### Text-to-Speech (OpenAI-compatible)

Converts text to speech audio using the configured TTS model. This endpoint is compatible with the OpenAI TTS API format.

**Endpoint**: `POST /v1/audio/speech`

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `input` | string | **Yes** | The text to convert to speech (max 4096 characters) |
| `voice` | string | No | Voice identifier to use. Defaults to `alloy` for OpenAI compatibility |
| `agent` | string | No | Agent name to select a pre-configured voice (overrides `voice`) |
| `model` | string | No | Model identifier (ignored, included for OpenAI compatibility) |
| `response_format` | string | No | Output format: `wav`, `mp3`, `opus`, `flac`. Default: `wav` |
| `speed` | float | No | Speech speed multiplier (0.25-4.0). Default: `1.0` |

#### Example Request
```bash
curl -X POST http://localhost:8001/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "input": "Hello, how are you today?",
    "voice": "alloy",
    "agent": "da",
    "response_format": "wav",
    "speed": 1.0
  }' \
  --output speech.wav
```

#### Response
Binary audio data in the requested format.

---

### Speech-to-Text (OpenAI-compatible)

Transcribes audio files to text using Faster-Whisper. This endpoint is compatible with the OpenAI Whisper API format.

**Endpoint**: `POST /v1/audio/transcriptions`

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | file | **Yes** | Audio file to transcribe (wav, mp3, m4a, webm, mp4, mpeg, mpga, oga, ogg) |
| `model` | string | No | Model identifier (ignored, uses server-configured model) |
| `language` | string | No | ISO-639-1 language code (e.g., `en`, `es`, `fr`). Auto-detected if omitted |
| `prompt` | string | No | Optional text to guide transcription style or provide context |
| `response_format` | string | No | Output format: `json`, `text`, `verbose_json`, `srt`, `vtt`. Default: `json` |
| `temperature` | float | No | Sampling temperature (0.0-1.0). Lower = more deterministic. Default: `0.0` |

#### Example Request
```bash
curl -X POST http://localhost:8001/v1/audio/transcriptions \
  -H "X-API-Key: your-api-key" \
  -F "file=@audio.wav" \
  -F "model=whisper-1" \
  -F "language=en" \
  -F "response_format=json"
```

#### Response (JSON format)
```json
{
  "text": "The transcribed text from the audio file."
}
```

#### Response (verbose_json format)
```json
{
  "text": "The transcribed text from the audio file.",
  "segments": [...],
  "language": "en",
  "duration": 5.2
}
```

---

### List Voices

Returns all available voices configured on the server.

**Endpoint**: `GET /v1/voices`

#### Parameters

None.

#### Example Request
```bash
curl http://localhost:8001/v1/voices \
  -H "X-API-Key: your-api-key"
```

#### Response
```json
{
  "voices": [
    {
      "name": "da",
      "description": "Female, mid-thirties. Warm, smooth timbre."
    },
    ...
  ]
}
```

---

### Create New Voice

Creates a new voice using the VoiceDesign model based on a text description.

**Endpoint**: `POST /v1/voices`

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_name` | string | **Yes** | Unique identifier for the new voice |
| `instruct` | string | **Yes** | Text description of the desired voice characteristics (gender, age, timbre, pitch, etc.) |

#### Example Request
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

#### Response
Binary WAV audio file containing a sample of the generated voice.

---

### Reload Voices

Reloads the voice configuration from disk without restarting the server. Use this after adding new voice files or modifying `voices.json`.

**Endpoint**: `POST /v1/voices/reload`

#### Parameters

None.

#### Example Request
```bash
curl -X POST http://localhost:8001/v1/voices/reload \
  -H "X-API-Key: your-api-key"
```

#### Response
```json
{
  "status": "ok",
  "voices_loaded": 7
}
```

---

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
│   ├── install.sh              # Automated installation script
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

# Enable/disable auto-start
sudo systemctl enable caii-voice-server
sudo systemctl disable caii-voice-server

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
ls -la /path/to/models/Qwen3-TTS-12Hz-1.7B-Base
ls -la /path/to/models/Qwen3-TTS-12Hz-1.7B-VoiceDesign
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
