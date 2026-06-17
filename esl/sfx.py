"""
Procedural sound effects (no asset files needed).

Synthesizes short chimes with numpy, caches them as WAVs, and plays them through
pygame's mixer on their own channels so they can overlap the Edge-TTS narration.
"""
from __future__ import annotations

import wave
from pathlib import Path
from typing import List, Tuple

import numpy as np

try:
    import pygame
except Exception:  # noqa: BLE001
    pygame = None

SAMPLE_RATE = 44100


def _tone(notes: List[Tuple[float, float]], volume: float = 0.5) -> np.ndarray:
    """notes = [(frequency_hz, duration_s), ...] played in sequence."""
    chunks = []
    for freq, dur in notes:
        n = int(SAMPLE_RATE * dur)
        if freq <= 0:  # a rest / silence
            chunks.append(np.zeros(n))
            continue
        t = np.linspace(0, dur, n, endpoint=False)
        wave_data = np.sin(2 * np.pi * freq * t)
        wave_data += 0.25 * np.sin(2 * np.pi * 2 * freq * t)  # a little brightness
        # short fade in/out to avoid clicks
        fade = max(1, int(SAMPLE_RATE * 0.008))
        env = np.ones(n)
        env[:fade] = np.linspace(0, 1, fade)
        env[-fade:] = np.linspace(1, 0, fade)
        chunks.append(wave_data * env)
    sig = np.concatenate(chunks) if chunks else np.zeros(1)
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * volume
    return (sig * 32767).astype(np.int16)


def _write_wav(path: Path, samples: np.ndarray):
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(samples.tobytes())


# Definitions for each calm learning cue (frequencies in Hz; 0 = a rest).
_DEFS = {
    "success":   [(523.25, 0.10), (659.25, 0.10), (783.99, 0.16)],   # C5 E5 G5 (up)
    "win":       [(523.25, 0.12), (659.25, 0.12), (783.99, 0.12), (1046.5, 0.30)],
    "fail":      [(220.0, 0.14), (174.6, 0.20)],                     # gentle low correction
    "select":    [(880.0, 0.05)],                                    # soft blip
    "gate":      [(392.0, 0.10), (587.33, 0.10), (784.0, 0.18)],     # open fanfare
}


class SFX:
    def __init__(self, cache_dir: Path, enabled: bool = True):
        self.enabled = enabled and pygame is not None
        self.sounds = {}
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # make sure the mixer exists (TTSEngine usually init'd it already)
        if self.enabled and not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e:  # noqa: BLE001
                print(f"[sfx] no audio device, sound effects off: {e}")
                self.enabled = False

        for name, notes in _DEFS.items():
            path = cache_dir / f"{name}.wav"
            try:
                if not path.exists():
                    vol = {"win": 0.65}.get(name, 0.55)
                    _write_wav(path, _tone(notes, volume=vol))
                if self.enabled:
                    self.sounds[name] = pygame.mixer.Sound(str(path))
            except Exception as e:  # noqa: BLE001
                print(f"[sfx] could not prepare {name}: {e}")

    def play(self, name: str):
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:  # noqa: BLE001
                pass
