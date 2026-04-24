"""
HELIX — Voice Listener (Phase 5 full implementation)
Uses sounddevice + SpeechRecognition for mic capture.
PyAudio replaced with sounddevice — works on Python 3.14.

Phase 1: Text input fallback (this file)
Phase 5: Full async voice capture integrated into PyQt6 HUD
"""
import sys
import os
import io
import threading
import queue

import sounddevice as sd
import numpy as np
import speech_recognition as sr

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ── Constants ──────────────────────────────────────────────
SAMPLE_RATE = 16000   # Hz — Whisper optimal
CHANNELS = 1
CHUNK_DURATION = 3    # seconds per audio chunk


class VoiceListener:
    """
    Captures microphone audio via sounddevice and converts to text
    via SpeechRecognition (Google STT) or local Whisper.

    Usage:
        listener = VoiceListener()
        text = listener.listen_once()   # blocking, returns string
    """

    def __init__(self, use_whisper: bool = False):
        self.recognizer = sr.Recognizer()
        self.use_whisper = use_whisper
        self._check_mic()

    def _check_mic(self):
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        if not input_devices:
            raise RuntimeError("[Voice] No input devices found.")
        print(f"[Voice] Mic ready: {sd.query_devices(kind='input')['name']}")

    def listen_once(self, timeout: int = 5) -> str:
        """
        Records audio for up to `timeout` seconds.
        Returns transcribed text or empty string on failure.
        """
        print(f"[Voice] Listening for {timeout}s...")
        audio_data = sd.rec(
            int(timeout * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='int16'
        )
        sd.wait()

        # Convert numpy array to AudioData for SpeechRecognition
        raw_bytes = audio_data.tobytes()
        audio = sr.AudioData(raw_bytes, SAMPLE_RATE, 2)

        try:
            if self.use_whisper:
                import whisper
                # Save to temp file for Whisper
                import tempfile, wave
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_path = f.name
                with wave.open(tmp_path, 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(2)
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(raw_bytes)
                model = whisper.load_model("base")
                result = model.transcribe(tmp_path)
                os.unlink(tmp_path)
                return result["text"].strip()
            else:
                text = self.recognizer.recognize_google(audio)
                print(f"[Voice] Heard: '{text}'")
                return text
        except sr.UnknownValueError:
            print("[Voice] Could not understand audio.")
            return ""
        except sr.RequestError as e:
            print(f"[Voice] STT service error: {e}")
            return ""
        except Exception as e:
            print(f"[Voice] Error: {e}")
            return ""
