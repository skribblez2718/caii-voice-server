# Medium-Term Security Hardening

Estimated effort: 1-2 days

## 1. Expand Test Coverage to 80%+

Priority areas:
- `app/middleware/auth.py` — test all auth paths (missing key, invalid key, exempt paths, Bearer vs X-API-Key)
- `app/middleware/rate_limit.py` — test window expiry, concurrent requests, limit enforcement
- Error paths in all route handlers (400, 413, 500 responses)
- Integration tests for full request lifecycle (auth + rate limit + handler)

## 2. Wrap Blocking Model Calls with `asyncio.to_thread()`

**File:** `app/services/tts_manager.py`

The `_ensure_models_on_gpu()` method performs synchronous GPU transfers that block the event loop. Wrap with `asyncio.to_thread()` or run in an executor to prevent request starvation during model loading.

## 3. Split Health Endpoint

Current `/health` endpoint exposes model status and system details without authentication.

Fix:
- `GET /health` — public, returns only `{"status": "ok"}` (for load balancers)
- `GET /health/detail` — authenticated, returns full model status, GPU info, uptime

## 4. Default PTT Client to HTTPS

**File:** `ptt_client/main.py`

- Change default scheme from `http://` to `https://`
- Add `--no-tls` flag for explicit opt-out during local development
- Support custom CA certificates via `--ca-cert` flag

## 5. Remove Docs Endpoints from Auth Exemption in Production

**File:** `app/middleware/auth.py`

- Remove `/docs`, `/redoc`, `/openapi.json` from `EXEMPT_PATHS`
- Or make their exemption conditional on an env var like `ENABLE_DOCS=true` (default `false`)

## 6. Add Structured JSON Logging

Replace ad-hoc f-string log messages with structured JSON logging:
- Use `python-json-logger` or equivalent
- Include request_id, client_ip, endpoint, duration in every log line
- Simplifies log aggregation and SIEM integration

## 7. Remove Stale `requirements.txt`

**File:** `requirements.txt`

The project uses `pyproject.toml` for dependency management. The `requirements.txt` is stale and diverged. Either:
- Delete it entirely
- Or add a CI step to regenerate it from pyproject.toml (`pip-compile`)

## 8. Fix `pydub` audioop Deprecation

The `audioop` module is removed in Python 3.13. The `pydub` library depends on it for audio format conversion.

Fix:
- Pin `pydub` to a version that supports 3.13+ (when available)
- Or replace `pydub` usage with direct `ffmpeg` subprocess calls
- Or use `audioop-lts` backport package

## 9. Add Dockerfile for Containerized Deployment

Create a multi-stage Dockerfile:
- Build stage: install dependencies
- Runtime stage: minimal image with CUDA support
- Non-root user
- Health check configured
- `.dockerignore` to exclude dev files

## 10. Add systemd Resource Limits

**File:** `caii-voice-server.service`

Add resource constraints to prevent runaway processes:
- `MemoryMax=8G` (or appropriate for GPU model size)
- `CPUQuota=200%` (limit to 2 cores)
- `TimeoutStopSec=30`

## 11. Remove Hardcoded Model Path from Service File

**File:** `caii-voice-server.service`

The service file contains a hardcoded `/home/skribblez/ai/models` path. Replace with:
- Environment variable reference: `Environment=MODEL_PATH=%h/ai/models`
- Or use the `.env` file that the application already reads
