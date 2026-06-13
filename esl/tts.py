"""
Text-to-speech using Microsoft Edge's American English neural voices
(via the `edge-tts` package), with on-disk caching and non-blocking playback.

Design:
  * A single background worker thread owns an asyncio loop (edge-tts is async)
    and the audio device (pygame-ce mixer). The game thread only ever enqueues
    requests, so rendering never blocks on network or audio.
  * Generated MP3s are cached under cache/tts/ keyed by a hash of
    (voice, rate, volume, text). After the first play -- or a prewarm pass --
    everything is instant and works offline.
  * Interactive speech is prioritised over background prewarming.
"""
from __future__ import annotations

import asyncio
import hashlib
import queue
import threading
import time
from pathlib import Path
from typing import Iterable, Optional

import edge_tts
import pygame


class TTSEngine:
    def __init__(
        self,
        voice: str,
        rate: str = "+0%",
        volume: str = "+0%",
        cache_dir: Optional[Path] = None,
        enabled: bool = True,
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache/tts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = enabled
        self.audio_ok = False

        self._q: "queue.PriorityQueue" = queue.PriorityQueue()
        self._seq = 0
        self._seq_lock = threading.Lock()
        self._skip = threading.Event()

        if enabled:
            try:
                pygame.mixer.init()
                self.audio_ok = True
            except Exception as e:  # noqa: BLE001 - audio is optional
                print(f"[tts] audio device unavailable, TTS muted: {e}")
                self.enabled = False

        self._thread = threading.Thread(target=self._run, name="tts-worker", daemon=True)
        self._thread.start()

    # -- public API --------------------------------------------------------
    def speak(self, text: str, voice: Optional[str] = None, interrupt: bool = True):
        """Queue text to be spoken now (highest priority)."""
        if not self.enabled or not text or not text.strip():
            return
        if interrupt:
            self.stop()
        self._enqueue(text, voice or self.voice, play=True, priority=0)

    def prewarm(self, texts: Iterable[str], voice: Optional[str] = None):
        """Generate (but do not play) audio in the background to fill the cache."""
        if not self.enabled:
            return
        for t in texts:
            if t and t.strip():
                self._enqueue(t, voice or self.voice, play=False, priority=2)

    def stop(self):
        """Stop whatever is currently playing and drop queued *playback*."""
        if not self.audio_ok:
            return
        self._skip.set()
        try:
            pygame.mixer.music.stop()
        except Exception:  # noqa: BLE001
            pass

    # -- internals ---------------------------------------------------------
    def _enqueue(self, text: str, voice: str, play: bool, priority: int):
        with self._seq_lock:
            self._seq += 1
            seq = self._seq
        self._q.put((priority, seq, {"text": text, "voice": voice, "play": play}))

    def _cache_path(self, text: str, voice: str) -> Path:
        key = f"{voice}|{self.rate}|{self.volume}|{text}"
        h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
        return self.cache_dir / f"{h}.mp3"

    async def _generate(self, text: str, voice: str, path: Path):
        comm = edge_tts.Communicate(text, voice, rate=self.rate, volume=self.volume)
        tmp = path.with_suffix(".part")
        await comm.save(str(tmp))
        if tmp.exists() and tmp.stat().st_size > 0:
            tmp.replace(path)
        else:
            tmp.unlink(missing_ok=True)
            raise RuntimeError("edge-tts produced empty audio")

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            _prio, _seq, item = self._q.get()
            text, voice, play = item["text"], item["voice"], item["play"]
            path = self._cache_path(text, voice)
            try:
                if not path.exists():
                    loop.run_until_complete(self._generate(text, voice, path))
                if play and self.audio_ok:
                    self._play(path)
            except Exception as e:  # noqa: BLE001 - never kill the worker
                print(f"[tts] could not speak {text!r}: {e}")
            finally:
                self._q.task_done()

    def _play(self, path: Path):
        self._skip.clear()
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
        except Exception as e:  # noqa: BLE001
            print(f"[tts] playback error: {e}")
            return
        while pygame.mixer.music.get_busy():
            if self._skip.is_set():
                pygame.mixer.music.stop()
                break
            time.sleep(0.03)
