"""
Voice server transcription client using urllib.

Sends audio to an OpenAI-compatible /v1/audio/transcriptions endpoint
via multipart/form-data POST. No external HTTP libraries required.
"""

import io
import json
import logging
import urllib.request
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


def _build_multipart_body(
    audio_data: io.BytesIO,
    model: str = "whisper-1",
    response_format: str = "json",
) -> tuple[bytes, str]:
    """Build a multipart/form-data request body.

    Args:
        audio_data: BytesIO with audio content and .name attribute.
        model: Model name for the transcription request.
        response_format: Desired response format (json or text).

    Returns:
        Tuple of (body_bytes, content_type_header).
    """
    boundary = uuid.uuid4().hex
    lines: list[bytes] = []

    filename = getattr(audio_data, "name", "recording.wav")
    audio_data.seek(0)
    file_content = audio_data.read()

    # File field
    lines.append(f"--{boundary}".encode())
    lines.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode()
    )
    lines.append(b"Content-Type: audio/wav")
    lines.append(b"")
    lines.append(file_content)

    # Model field
    lines.append(f"--{boundary}".encode())
    lines.append(b'Content-Disposition: form-data; name="model"')
    lines.append(b"")
    lines.append(model.encode())

    # Response format field
    lines.append(f"--{boundary}".encode())
    lines.append(b'Content-Disposition: form-data; name="response_format"')
    lines.append(b"")
    lines.append(response_format.encode())

    # Closing boundary
    lines.append(f"--{boundary}--".encode())
    lines.append(b"")

    body = b"\r\n".join(lines)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def transcribe_audio(
    audio_data: io.BytesIO,
    server_url: str,
    api_key: str,
    model: str = "whisper-1",
    response_format: str = "json",
    timeout: Optional[float] = 30.0,
) -> str:
    """Send audio to voice server for transcription.

    Args:
        audio_data: BytesIO with WAV audio data.
        server_url: Base URL of the voice server (e.g. http://localhost:8001).
        api_key: API key for authentication.
        model: Model name (default: whisper-1).
        response_format: Response format — 'json' or 'text'.
        timeout: Request timeout in seconds.

    Returns:
        Transcribed text string.

    Raises:
        urllib.error.URLError: On network errors.
        urllib.error.HTTPError: On HTTP error responses.
    """
    url = f"{server_url}/v1/audio/transcriptions"
    body, content_type = _build_multipart_body(audio_data, model, response_format)

    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": content_type,
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    logger.info("Sending transcription request to %s", url)

    with urllib.request.urlopen(request, timeout=timeout) as response:
        response_bytes = response.read()

    if response_format == "text":
        return response_bytes.decode("utf-8")

    result = json.loads(response_bytes)
    return result["text"]
