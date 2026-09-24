from __future__ import annotations

import os
import sys
import time
import wave
from pathlib import Path

# ------------------------------------------------------------
# Make project root importable when this file is run directly.
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env", override=False)


def require_api_key() -> str:
    """Load and validate the Sarvam API key without printing it."""
    key = (os.getenv("SARVAM_API_KEY") or "").strip()

    if not key:
        raise RuntimeError(
            "SARVAM_API_KEY is missing. "
            "Add it to the project's .env file."
        )

    return key


def create_silent_wav(path: Path, seconds: float = 1.0) -> None:
    """Create a valid 16 kHz mono PCM WAV for an authentication check."""
    sample_rate = 16000
    channels = 1
    sample_width = 2

    total_frames = int(sample_rate * seconds)
    silence = b"\x00\x00" * total_frames

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(silence)


def test_api_auth() -> None:
    """Verify that the configured key reaches Sarvam STT successfully."""
    import requests

    api_key = require_api_key()

    url = "https://api.sarvam.ai/speech-to-text"

    audio_path = PROJECT_ROOT / "scripts" / "_sarvam_auth_test.wav"

    create_silent_wav(audio_path)

    headers = {
        "api-subscription-key": api_key,
    }

    data = {
        "model": "saaras:v4",
        "language_code": "unknown",
    }

    print("Testing Sarvam STT authentication...")
    print(f"Audio: {audio_path.name}")
    print("Sending request...")

    try:
        with audio_path.open("rb") as audio_file:
            files = {
                "file": (
                    audio_path.name,
                    audio_file,
                    "audio/wav",
                )
            }

            response = requests.post(
                url,
                headers=headers,
                data=data,
                files=files,
                timeout=60,
            )

        print(f"HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError:
            payload = response.text

        print(payload)

        if response.status_code == 200:
            print()
            print(
                "SUCCESS: Sarvam authentication works. "
                "A silent file naturally produces an empty transcript."
            )

        elif response.status_code == 401:
            print()
            print("ERROR: Sarvam rejected the API credentials (401).")

        elif response.status_code == 403:
            print()
            print(
                "ERROR: Sarvam rejected the API key (403). "
                "Check SARVAM_API_KEY in .env."
            )

        else:
            print()
            print(
                "ERROR: Sarvam returned an unexpected HTTP status."
            )

    finally:
        try:
            audio_path.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    test_api_auth()