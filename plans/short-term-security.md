# Short-Term Security Improvements

Estimated effort: ~half day

## 1. Rewrite Rate Limiter

**File:** `app/middleware/rate_limit.py`

Current issues:
- No `asyncio.Lock` protecting the shared `requests` dict — concurrent requests can race
- No periodic eviction of expired entries — memory grows unbounded under sustained traffic
- Uses `X-Forwarded-For` header for client identification — trivially spoofable

Fix:
- Add `asyncio.Lock` around all reads/writes to the request tracking dict
- Add a periodic background task (or check-on-access) to evict entries older than the window
- Use `request.client.host` as the primary client identifier (falls back to socket peer address)

## 2. Sanitize Transcription Text in PTT Client

**File:** `ptt_client/main.py`

Current issue:
- Raw transcription output is injected into the Claude Code command without sanitization
- Control characters, newlines, or shell metacharacters in transcribed speech could cause unexpected behavior

Fix:
- Strip control characters (ASCII 0x00-0x1F except space/tab)
- Replace newlines with spaces
- Escape or strip shell metacharacters (`; | & $ \` ( ) { }`)
- Apply sanitization before passing text to any subprocess or command

## 3. Add Pydantic Validators for Config Value Ranges

**File:** `app/config.py`

Current issue:
- Numeric config values have no range validation — a negative `stt_beam_size` or `rate_limit_requests=0` would cause runtime errors

Fix:
- Add `ge=1, le=10` to `stt_beam_size`
- Add `ge=1, le=10` to `stt_best_of`
- Add `ge=1` to `rate_limit_requests`
- Add `ge=1` to `rate_limit_window_seconds`
- Add `ge=1` to `max_upload_size_bytes`
- Add `ge=30` to `model_idle_timeout_seconds`
- Add `ge=10` to `model_offload_check_interval_seconds`
