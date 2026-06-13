"""
WordMine -- an educational voxel sandbox for learning English (ESL).

Mine glowing "Word Ore" (and keep mining ordinary blocks) to trigger ESL
challenges: listen to American-English narration, choose words, practice
grammar, and speak into your microphone. Answer correctly to earn XP and
building materials.

Run:  python main.py     (or double-click run_wordmine.bat)
"""
from __future__ import annotations

import os
import random
from pathlib import Path

from ursina import (
    Ursina, Sky, DirectionalLight, AmbientLight, Text, Vec2, Vec3,
    camera, color, mouse, time, window, application, distance,
)
from ursina.prefabs.first_person_controller import FirstPersonController


def _setup_font():
    """Use Segoe UI so IPA phonetics render; fall back to Ursina's default."""
    try:
        win_fonts = Path("C:/Windows/Fonts")
        if (win_fonts / "segoeui.ttf").exists():
            application.fonts_folder = win_fonts
            Text.default_font = "segoeui.ttf"
    except Exception as e:  # noqa: BLE001
        print(f"[font] falling back to default font: {e}")

import config
from game import blocks
from game.hud import HUD
from game.inventory import Inventory
from game.world import World, Voxel
from esl import loader
from esl.engine import ChallengeManager
from esl.tts import TTSEngine
from esl.speech import SpeechRecognizer
from esl.challenge_ui import ChallengeUI


class WordMine:
    def __init__(self):
        # --- window ---
        window.title = "WordMine — Learn English by Mining"
        window.borderless = False
        window.fullscreen = False
        window.exit_button.visible = True
        window.fps_counter.enabled = True
        window.color = color.rgb(0.53, 0.70, 0.92)
        _setup_font()

        # --- learning content (modular: swap the JSON in config.py) ---
        words = loader.load_vocabulary(config.VOCAB_FILES)
        rules = loader.load_grammar(config.GRAMMAR_FILES)

        # --- audio in / out ---
        self.tts = TTSEngine(
            voice=config.TTS_VOICE, rate=config.TTS_RATE, volume=config.TTS_VOLUME,
            cache_dir=config.TTS_CACHE_DIR, enabled=config.TTS_ENABLED,
        )
        self.speech = SpeechRecognizer(
            model_dir=config.VOSK_MODEL_DIR, sample_rate=config.SPEECH_SAMPLE_RATE,
            enabled=config.SPEECH_ENABLED,
        )

        # --- challenge engine ---
        self.manager = ChallengeManager(
            words, rules, progress_path=config.PROGRESS_FILE,
            speech_available=self.speech.available,
            match_threshold=config.SPEECH_MATCH_THRESHOLD,
            xp_per_correct=config.XP_PER_CORRECT,
        )

        # --- scene ---
        Sky()
        sun = DirectionalLight()
        sun.look_at(Vec3(1, -1.6, -1))
        AmbientLight(color=color.rgba(0.55, 0.55, 0.6, 1))

        self.world = World(config.WORLD_RADIUS, config.WORD_ORE_COUNT)
        self.world.generate()
        self.word_ore = [v for v in self.world.voxels.values() if v.block_type.is_word_ore]

        # --- player ---
        self.player = FirstPersonController(
            position=(0, config.PLAYER_START_HEIGHT, 0), mouse_sensitivity=Vec2(40, 40),
        )

        # --- inventory + HUD ---
        self.inventory = Inventory(blocks.HOTBAR, starting=16)
        self.hud = HUD()
        self.hud.update_hotbar(self.inventory)
        self.hud.set_stats(self.manager.stats())

        # --- challenge overlay ---
        self.challenge_ui = ChallengeUI(
            self.tts, self.speech,
            on_result=self.on_challenge_result, on_close=self.on_challenge_close,
        )

        self.mined = 0
        self.manual_pause = False

        # WORDMINE_SELFTEST=1 boots the full game, then quits after a moment
        # without capturing the mouse or playing audio (used for smoke tests).
        self.selftest = bool(os.environ.get("WORDMINE_SELFTEST"))
        self._selftest_frames = 0
        if self.selftest:
            self.player.enabled = False
            mouse.locked = False
            return

        # warm the TTS cache in the background and greet the player
        self.tts.prewarm(self.manager.prewarm_texts())
        welcome = ("Welcome to WordMine! Mine the glowing word ore to start a "
                   "challenge. Listen, choose, and speak to learn English. Have fun!")
        self.tts.speak(welcome)
        self.hud.show_subtitle(welcome, duration=6)
        if not self.speech.available:
            self.hud.toast("Mic off - run setup_models.py for speaking",
                           duration=6, col=color.orange)

    # -- control helpers ---------------------------------------------------
    def set_player_active(self, active: bool):
        self.player.enabled = active
        mouse.locked = active
        self.hud.crosshair.enabled = active

    # -- gameplay actions --------------------------------------------------
    def mine(self):
        target = mouse.hovered_entity
        if not isinstance(target, Voxel):
            return
        bt = target.block_type
        if target in self.word_ore:
            self.word_ore.remove(target)
        self.world.remove(target)

        if bt.is_word_ore:
            self.hud.toast("Word Ore!  Challenge time", col=color.gold)
            self.trigger_challenge()
        else:
            self.inventory.add(bt.id, 1)
            self.hud.update_hotbar(self.inventory)
            self.mined += 1
            if self.mined % config.CHALLENGE_EVERY_N_MINES == 0:
                self.trigger_challenge()

    def place(self):
        target = mouse.hovered_entity
        if not isinstance(target, Voxel) or mouse.normal is None:
            return
        bt = self.inventory.selected_block
        if self.inventory.count(bt.id) <= 0:
            self.hud.toast(f"Out of {bt.name}", col=color.orange)
            return
        new_pos = target.position + Vec3(*mouse.normal)
        if distance(new_pos, self.player.position) < 1.2:
            return  # don't entomb the player
        if self.world.key(new_pos) in self.world.voxels:
            return
        self.world.add(new_pos, bt)
        self.inventory.take(bt.id, 1)
        self.hud.update_hotbar(self.inventory)

    # -- challenge plumbing ------------------------------------------------
    def trigger_challenge(self):
        if self.challenge_ui.active:
            return
        ch = self.manager.next_challenge()
        if ch is None:
            return
        self.set_player_active(False)
        self.challenge_ui.open(ch, self.manager)

    def on_challenge_result(self, challenge, result):
        self.hud.set_stats(self.manager.stats())
        if result.correct:
            reward = random.choice(blocks.HOTBAR)
            self.inventory.add(reward.id, 3)
            self.hud.update_hotbar(self.inventory)
            self.hud.toast(f"+{result.xp} XP   +3 {reward.name}", col=color.lime)
        else:
            self.hud.toast("Keep practicing!", col=color.orange)

    def on_challenge_close(self):
        if not self.hud.journal_open:
            self.set_player_active(True)
        self.hud.update_hotbar(self.inventory)
        self.hud.set_stats(self.manager.stats())

    def toggle_journal(self):
        open_now = self.hud.toggle_journal(self.manager.learned_words(), len(self.manager.words))
        # release the mouse while reading
        self.set_player_active(not open_now and not self.challenge_ui.active)

    # -- engine hooks ------------------------------------------------------
    def input(self, key):
        if self.challenge_ui.active:
            self.challenge_ui.input(key)
            return

        if key == "j":
            self.toggle_journal()
            return
        if self.hud.journal_open:
            return  # journal is modal-ish

        if key == "escape":
            self.manual_pause = not self.manual_pause
            self.set_player_active(not self.manual_pause)
            self.hud.toast("Paused — press ESC to resume" if self.manual_pause else "",
                           duration=99 if self.manual_pause else 0.01)
            return
        if self.manual_pause:
            if key == "left mouse down":
                self.manual_pause = False
                self.set_player_active(True)
                self.hud.toast("", duration=0.01)
            return

        if key in ("1", "2", "3", "4", "5", "6"):
            self.inventory.select(int(key) - 1)
            self.hud.update_hotbar(self.inventory)
        elif key == "scroll up":
            self.inventory.scroll(-1)
            self.hud.update_hotbar(self.inventory)
        elif key == "scroll down":
            self.inventory.scroll(1)
            self.hud.update_hotbar(self.inventory)
        elif key == "left mouse down":
            self.mine()
        elif key == "right mouse down":
            self.place()

    def update(self):
        self.hud.update(time.dt)
        self.challenge_ui.update()
        # gently spin the word ore so it reads as "interactive / magical"
        for v in self.word_ore:
            v.rotation_y += time.dt * 45

        if self.selftest:
            self._selftest_frames += 1
            if self._selftest_frames >= 75:
                Path("selftest_ok.txt").write_text("booted", encoding="utf-8")
                print("SELFTEST OK")
                application.quit()


# --------------------------------------------------------------------------
app = Ursina()
game = WordMine()


def input(key):          # Ursina calls this
    game.input(key)


def update():            # Ursina calls this every frame
    game.update()


if __name__ == "__main__":
    app.run()
