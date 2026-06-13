"""
Microphone speech recognition (the player speaks; we check what they said).

Uses sounddevice (PortAudio, bundled in the wheel -- no PyAudio needed) to
capture push-to-talk audio, and Vosk for fully offline transcription (no API
key, no internet). If the Vosk model or a microphone is missing, `available`
is False and the game falls back to a "press Enter to continue" mode so the
prototype is always playable.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sounddevice as sd


class SpeechRecognizer:
    def __init__(
        self,
        model_dir: Path,
        sample_rate: int = 16000,
        enabled: bool = True,
    ):
        self.sample_rate = sample_rate
        self.available = False
        self.model = None
        self._frames = []
        self._stream: Optional[sd.InputStream] = None
        self._recording = False
        self.status = "disabled"

        if not enabled:
            return
        try:
            from vosk import Model, SetLogLevel

            SetLogLevel(-1)
            if not Path(model_dir).exists():
                self.status = "no-model"
                print(
                    f"[speech] Vosk model not found at {model_dir}.\n"
                    f"         Run:  python setup_models.py   to enable speaking challenges."
                )
                return
            self.model = Model(str(model_dir))
            # Probe that an input device exists.
            sd.check_input_settings(samplerate=sample_rate, channels=1, dtype="int16")
            self.available = True
            self.status = "ready"
            print("[speech] microphone + Vosk ready (offline recognition)")
        except Exception as e:  # noqa: BLE001 - speech is optional
            self.status = f"error: {e}"
            print(f"[speech] disabled: {e}")

    # -- push to talk ------------------------------------------------------
    def begin(self) -> bool:
        if not self.available or self._recording:
            return False
        self._frames = []

        def _cb(indata, frames, time_info, status):  # noqa: ANN001
            self._frames.append(indata.copy())

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                callback=_cb,
            )
            self._stream.start()
            self._recording = True
            return True
        except Exception as e:  # noqa: BLE001
            print(f"[speech] could not open microphone: {e}")
            self._recording = False
            return False

    def end_async(self, callback: Callable[[str], None]):
        """Stop recording and transcribe off the main thread; call back with text."""
        if not self._recording:
            callback("")
            return
        self._recording = False
        stream, self._stream = self._stream, None
        frames, self._frames = self._frames, []

        def _work():
            text = ""
            try:
                if stream is not None:
                    stream.stop()
                    stream.close()
                if frames:
                    pcm = np.concatenate(frames, axis=0).tobytes()
                    text = self._transcribe(pcm)
            except Exception as e:  # noqa: BLE001
                print(f"[speech] recognition error: {e}")
            callback(text)

        threading.Thread(target=_work, name="speech-recognize", daemon=True).start()

    @property
    def is_recording(self) -> bool:
        return self._recording

    def _transcribe(self, pcm_bytes: bytes) -> str:
        from vosk import KaldiRecognizer

        rec = KaldiRecognizer(self.model, self.sample_rate)
        rec.AcceptWaveform(pcm_bytes)
        result = json.loads(rec.FinalResult())
        return result.get("text", "").strip()
