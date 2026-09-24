import math
import os
import tempfile
from array import array
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThread

try:
    import speech_recognition as sr
except ImportError:
    sr = None

from services.provider_factory import build_provider


class VoiceWorker(QObject):
    finished = Signal(str)
    language_detected = Signal(str)
    error = Signal(str)
    status = Signal(str)

    def __init__(self, language_code=None):
        super().__init__()
        self.language_code = language_code

    @staticmethod
    def _rms(audio):
        """Return the RMS level of captured 16-bit mono PCM audio."""
        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        if not raw:
            return 0.0
        samples = array("h")
        samples.frombytes(raw)
        if not samples:
            return 0.0
        return math.sqrt(sum(sample * sample for sample in samples) / len(samples))

    def run(self):
        if sr is None:
            self.error.emit("Install SpeechRecognition and PyAudio for microphone capture.")
            return

        provider = None
        provider_error = ""
        try:
            provider = build_provider()
        except Exception as error:
            provider_error = str(error)
            self.status.emit(f"Language provider unavailable; using fallback: {error}")

        recognizer = sr.Recognizer()
        try:
            device_index = None
            raw_index = os.getenv("MICROPHONE_DEVICE_INDEX", "").strip()
            if raw_index:
                try:
                    device_index = int(raw_index)
                except ValueError:
                    self.status.emit(f"Invalid MICROPHONE_DEVICE_INDEX '{raw_index}', using default")

            self.status.emit("Listening… speak now")
            mic = sr.Microphone(device_index=device_index, sample_rate=16000)
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)

            rms = self._rms(audio)
            duration = len(audio.frame_data) / max(audio.sample_rate * audio.sample_width, 1)
            if rms < 120:
                self.error.emit(
                    "Microphone captured almost no usable audio. "
                    f"RMS={rms:.1f}, duration={duration:.2f}s. "
                    "Check Windows microphone input/default device and try again."
                )
                return

            # Primary path: Sarvam Saaras STT for Indic + code-mixed speech.
            if provider is not None:
                self.status.emit("Recognizing Indian-language speech…")
                temp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
                        temp_path = Path(temp.name)
                        wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
                        temp.write(wav_bytes)

                    stt_kwargs = {
                        "language_code": self.language_code or "unknown",
                        "mode": "codemix",
                    }
                    response = provider.speech_to_text(str(temp_path), **stt_kwargs)
                    text = (response.get("transcript") or "").strip()
                    detected = response.get("language_code") or self.language_code or ""
                    if detected:
                        self.language_detected.emit(detected)
                    if text:
                        self.finished.emit(text)
                        return

                    # A second mode is useful for clips where codemix VAD/model
                    # normalization produces an empty transcript. Only retry when
                    # the first request succeeded, so auth/network errors are not
                    # duplicated unnecessarily.
                    self.status.emit("No transcript returned; retrying speech recognition…")
                    response = provider.speech_to_text(
                        str(temp_path),
                        language_code=self.language_code or "unknown",
                        mode="transcribe",
                    )
                    text = (response.get("transcript") or "").strip()
                    detected = response.get("language_code") or detected
                    if detected:
                        self.language_detected.emit(detected)
                    if text:
                        self.finished.emit(text)
                        return
                    provider_error = (
                        "Sarvam returned an empty transcript even though the microphone "
                        f"captured audio (RMS={rms:.1f}, duration={duration:.2f}s)"
                    )
                except Exception as error:
                    # Do not kill the voice worker here. A transient/network/auth
                    # failure should either fall through to local/Google recognition
                    # or be reported with the real provider error.
                    provider_error = str(error)
                    self.status.emit(f"Sarvam voice recognition failed; trying fallback… {error}")
                finally:
                    if temp_path is not None:
                        temp_path.unlink(missing_ok=True)

            # Fallback path. This is useful for basic English/Hindi operation,
            # but Sarvam must be configured with a valid API key for full 22-language STT.
            self.status.emit("Using fallback speech recognition…")
            fallback_languages = []
            if self.language_code:
                fallback_languages.append(self.language_code)
            for language in ["en-IN", "hi-IN"]:
                if language not in fallback_languages:
                    fallback_languages.append(language)

            for language in fallback_languages:
                try:
                    text = recognizer.recognize_google(audio, language=language).strip()
                    if text:
                        self.language_detected.emit(language)
                        self.finished.emit(text)
                        return
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    self.error.emit(
                        "Fallback speech recognition is unavailable. "
                        "Configure a valid Sarvam/BHASHINI key or check internet access."
                    )
                    return

            if provider_error:
                self.error.emit(
                    "Sarvam voice recognition failed. "
                    f"{provider_error} "
                    "Check SARVAM_API_KEY in .env. "
                    "Text search may still appear to work because it has a local fallback."
                )
            else:
                self.error.emit("I could not understand your speech. Please try again.")

        except sr.WaitTimeoutError:
            self.error.emit("No speech detected. Please try speaking again.")
        except OSError:
            self.error.emit("Microphone could not be accessed. Check microphone permissions and PyAudio installation.")
        except Exception as error:
            self.error.emit(f"Voice input failed: {error}")


class VoiceAssistant(QObject):
    text_received = Signal(str)
    language_detected = Signal(str)
    status_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None, language_code=None):
        super().__init__(parent)
        self.thread = None
        self.worker = None
        self.language_code = language_code

    def set_language_code(self, language_code):
        self.language_code = language_code

    def start(self):
        if self.thread is not None and self.thread.isRunning():
            return
        self.thread = QThread()
        self.worker = VoiceWorker(self.language_code)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.status.connect(self.status_changed.emit)
        self.worker.finished.connect(self._handle_finished)
        self.worker.language_detected.connect(self.language_detected.emit)
        self.worker.error.connect(self._handle_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.finished.connect(self._cleanup)
        self.thread.start()

    def _handle_finished(self, text: str):
        self.text_received.emit(text)

    def _handle_error(self, message: str):
        self.error_occurred.emit(message)

    def _cleanup(self):
        if self.worker is not None:
            self.worker.deleteLater()
        if self.thread is not None:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None
