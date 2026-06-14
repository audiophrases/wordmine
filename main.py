"""
WordMine -- an audio-only ESL *heist*. Total Physical Response under pressure.

You're in a restricted facility. A Security Drone hunts you. There is no text:
a companion drone names the object you look at (Edge TTS, American voice), and
you act by *speaking* the word into your mic (offline Vosk):

  SEE / HEAR : look at a thing -> hear its English word.
  ECHO       : hold [V], say the word.
  ACT        : nouns are collected; verbs change the world --
               OPEN a door, STOP a trap or the drone, HIDE from it,
               RUN faster, CLOSE a door to stall it.

Three zones: scavenge (key/tool/battery) -> the chase (verbs) -> the SRS lockout
(the engine demands your weakest word) -> the exit. Get caught: "Busted", reset.

Run:  python main.py   (or run_wordmine.bat)
"""
from __future__ import annotations

import os
from pathlib import Path

from ursina import (
    Ursina, Sky, DirectionalLight, AmbientLight, Vec2, Vec3,
    camera, color, mouse, time, window, application, raycast, destroy, invoke, distance,
)
from ursina.prefabs.first_person_controller import FirstPersonController

import config
from game.chaser import SecurityDrone
from game.drone import CompanionDrone
from game.hud import HUD
from game.interactables import Interactable, _color
from game.level import Level
from esl import loader
from esl.engine import SRSDirector
from esl.tts import TTSEngine
from esl.speech import SpeechRecognizer
from esl.sfx import SFX


class WordMine:
    def __init__(self):
        window.title = "WordMine — Heist Protocol"
        window.borderless = False
        window.fullscreen = False
        window.exit_button.visible = True
        window.fps_counter.enabled = True
        window.color = color.rgb(0.06, 0.06, 0.09)

        self.selftest = bool(os.environ.get("WORDMINE_SELFTEST"))
        audio_enabled = config.TTS_ENABLED and not self.selftest

        words = loader.load_vocabulary(config.VOCAB_FILES)
        self.tts = TTSEngine(
            voice=config.TTS_VOICE, rate=config.TTS_RATE, volume=config.TTS_VOLUME,
            cache_dir=config.TTS_CACHE_DIR, enabled=audio_enabled,
        )
        self.sfx = SFX(config.CACHE_DIR / "sfx", enabled=audio_enabled)
        self.speech = SpeechRecognizer(
            model_dir=config.VOSK_MODEL_DIR, sample_rate=config.SPEECH_SAMPLE_RATE,
            enabled=config.SPEECH_ENABLED and not self.selftest,
        )
        self.srs = SRSDirector(
            words, progress_path=config.PROGRESS_FILE,
            match_threshold=config.SPEECH_MATCH_THRESHOLD,
            xp_per_correct=config.XP_PER_CORRECT,
        )

        # tense facility atmosphere
        Sky(color=color.rgb(0.05, 0.05, 0.08))
        sun = DirectionalLight()
        sun.look_at(Vec3(1, -1.4, 0.5))
        sun.color = color.rgba(0.7, 0.68, 0.7, 1)
        AmbientLight(color=color.rgba(0.34, 0.30, 0.34, 1))

        # player + free look
        self.player = FirstPersonController(height=1.8, mouse_sensitivity=Vec2(
            config.MOUSE_SENSITIVITY, config.MOUSE_SENSITIVITY))
        self.player.cursor.enabled = False
        self.player.speed = config.PLAYER_SPEED
        camera.fov = config.CAMERA_FOV

        self.hud = HUD()
        self.drone = CompanionDrone()

        # the chaser (persists across resets) + its "stop" handle
        self.chaser = SecurityDrone(
            (0, 0, 0), config.CHASER_BASE_SPEED, config.CHASER_ACCEL,
            config.CHASER_MAX_SPEED, config.CHASER_CATCH_RADIUS, config.CHASER_GRACE_SECS)
        self.chaser_stop = Interactable(
            self.chaser.root, "stop", word=self.srs.word("stop"),
            collider_entity=self.chaser.body, height=1.5, repeatable=True,
            cooldown=config.FREEZE_SECS + 1.0, payload={"chaser": self.chaser})

        self.level = None
        self.build_level()

        # runtime state
        self.target = None
        self.recording = False
        self._pending = None
        self._speak_timer = 0.0
        self.collected = set()
        self.powered = False
        self.gate_open = False
        self.hidden_timer = 0.0
        self.boost_timer = 0.0
        self.zone = 1
        self._hb_timer = 0.0
        self._near_cd = 0.0
        self.ready = False
        self.won = False
        self.manual_pause = False
        self._st_frames = 0

        self.reset_state()
        self.player.enabled = False
        mouse.locked = False

        # pre-bake narrator words + dispatcher lines + praise
        pairs = [(w.word, config.TTS_VOICE) for w in words]
        pairs += [(line, config.DISPATCH_VOICE) for line in config.DISPATCH.values()]
        pairs += [(p, config.TTS_VOICE) for p in config.PRAISE]
        self.tts.prebake_pairs(pairs)

    # ------------------------------------------------------------- level
    def build_level(self):
        self.level = Level(self.srs)

    def reset_state(self):
        """Place the player & chaser at the start and clear chase state."""
        self.player.position = Vec3(*self.level.start_pos)
        self.player.rotation_y = 180  # face the exit (-Z)
        self.chaser.reset(self.level.chaser_spawn)
        self.collected = set()
        self.powered = False
        self.gate_open = False
        self.hidden_timer = 0.0
        self.boost_timer = 0.0
        self.player.speed = config.PLAYER_SPEED
        self.zone = 1
        self._near_cd = 0.0
        self.target = None
        self.hud.set_reticle("idle")
        self.hud.set_hidden(False)
        self.hud.set_danger(0)
        self.hud.clear_pips()

    # --------------------------------------------------------- dispatcher
    def dispatch(self, key):
        line = config.DISPATCH.get(key)
        if line:
            self.tts.speak(line, voice=config.DISPATCH_VOICE)

    # ----------------------------------------------------------- control
    def set_player_active(self, active):
        self.player.enabled = active
        mouse.locked = active
        self.hud.reticle.enabled = active

    # --------------------------------------------------------- targeting
    def _acquire_target(self):
        hit = raycast(camera.world_position, camera.forward,
                      distance=config.INTERACT_RANGE, ignore=(self.player,))
        inter = getattr(hit.entity, "interactable", None) if hit.hit else None
        return inter if (inter is not None and inter.available()) else None

    def _set_target(self, inter):
        if inter is self.target:
            return
        if self.target:
            self.target.set_highlight(False)
        self.target = inter
        if inter:
            inter.set_highlight(True)
            self.hud.set_reticle("target")
            self.sfx.play("select")
            word = inter.current_word()
            if word:
                self.tts.speak(word.word)
                self.drone.set_speaking()
                self._speak_timer = 1.0
        else:
            self.hud.set_reticle("idle")
            self.drone.set_idle()

    # ------------------------------------------------------------- echo
    def _start_echo(self):
        if not self.target:
            return
        word = self.target.current_word()
        if not word:
            return
        if not self.speech.available:
            self._resolve_echo(word.word)  # no mic -> auto-accept so it's playable
            return
        self.tts.stop()
        if self.speech.begin():
            self.recording = True
            self.drone.set_listening()
            self.hud.set_reticle("listen")
            self.hud.set_listening(True)

    def _stop_echo(self):
        if not self.recording:
            return
        self.recording = False
        self.hud.set_listening(False)
        self._pending = None
        self.speech.end_async(lambda text: setattr(self, "_pending", (text,)))

    def _resolve_echo(self, heard):
        target = self.target
        if target is None:
            return
        word = target.current_word()
        correct = self.srs.accept(heard, word.word)
        self.srs.record(word.id, correct)
        if correct:
            self.drone.flash_good()
            self.apply_effect(target)
            if self.target and not self.target.available():
                self.target = None
                self.hud.set_reticle("idle")
                self.drone.set_idle()
        else:
            self.drone.flash_bad()
            self.sfx.play("fail")
            self.tts.speak(word.word)  # hear it again, then retry

    # --------------------------------------------------------- effects
    def _open_barrier(self, bar):
        bar.collision = False
        bar.animate_color(color.rgba(bar.color[0], bar.color[1], bar.color[2], 0), duration=0.5)
        invoke(setattr, bar, "enabled", False, delay=0.6)

    def apply_effect(self, inter):
        kind = inter.kind
        if kind == "scavenge":
            inter.succeed()
            self.collected.add(inter.current_word().id)
            spec = inter.current_word().world_object or {}
            self.hud.add_pip(_color(spec.get("color", [1, 1, 1])))
            self.sfx.play("success")
            if len(self.collected) >= len(config.SCAVENGE_TARGETS) and not self.powered:
                self.powered = True
                self.sfx.play("gate")
                self.dispatch("powered")

        elif kind == "open":
            if inter.payload.get("requires_power") and not self.powered:
                self.sfx.play("select")
                self.dispatch("zone1")   # hint: still need to power it
                return
            self._open_barrier(inter.payload["barrier"])
            inter.succeed()
            self.sfx.play("gate")

        elif kind == "close":
            bar = inter.payload["door_barrier"]
            bar.enabled = True
            bar.collision = True
            bar.color = color.rgba(1.0, 0.5, 0.15, 0.85)
            self.chaser.block(config.CLOSE_BLOCK_SECS)
            invoke(setattr, bar, "collision", False, delay=config.CLOSE_BLOCK_SECS)
            invoke(setattr, bar, "enabled", False, delay=config.CLOSE_BLOCK_SECS + 0.1)
            inter.succeed()
            self.sfx.play("gate")

        elif kind == "stop":
            if "trap" in inter.payload:
                inter.payload["trap"].freeze(config.FREEZE_SECS)
            elif "chaser" in inter.payload:
                self.chaser.freeze(config.FREEZE_SECS)
            inter.succeed()
            self.sfx.play("success")

        elif kind == "hide":
            self.hidden_timer = config.HIDE_SECS
            self.chaser.lose(config.HIDE_SECS)
            self.hud.set_hidden(True)
            self.dispatch("hidden")
            inter.succeed()
            self.sfx.play("success")

        elif kind == "run":
            self.boost_timer = config.RUN_BOOST_SECS
            self.player.speed = config.PLAYER_SPEED * config.RUN_BOOST_MULT
            inter.succeed()
            self.sfx.play("success")

        elif kind == "gate":
            self._open_barrier(inter.payload["barrier"])
            inter.succeed()
            self.gate_open = True
            self.sfx.play("gate")

    # ----------------------------------------------------- chase / states
    def _heartbeat(self, danger, hidden, dt):
        self._hb_timer -= dt
        if not hidden and danger > 0.1 and self._hb_timer <= 0:
            self.sfx.play("heartbeat")
            self._hb_timer = 1.1 - (1.1 - 0.28) * danger

    def _check_zone(self):
        z = self.player.z
        if self.zone == 1 and z < self.level.div_a:
            self.zone = 2
            self.dispatch("zone2")
        elif self.zone == 2 and z < self.level.div_b:
            self.zone = 3
            self.dispatch("zone3")

    def on_busted(self):
        self.sfx.play("busted")
        self.dispatch("busted")
        self.level.destroy()
        self.build_level()
        self.reset_state()

    def on_win(self):
        self.won = True
        self.sfx.play("win")
        self.dispatch("win")
        self.drone.flash_good()
        self.hud.set_danger(0)
        self.level.trophy.animate_scale(1.3, duration=0.4)

    # -------------------------------------------------------- engine hooks
    def input(self, key):
        if not self.ready:
            return
        if key == "escape":
            self.manual_pause = not self.manual_pause
            self.set_player_active(not self.manual_pause)
            return
        if self.manual_pause:
            if key == "left mouse down":
                self.manual_pause = False
                self.set_player_active(True)
            return
        if self.won:
            return
        if key == "v":
            self._start_echo()
        elif key == "v up":
            self._stop_echo()
        elif key == "r" and self.target:
            word = self.target.current_word()
            if word:
                self.tts.speak(word.word)

    def update(self):
        self.hud.update(time.dt)

        if not self.ready:
            frac = (self.tts.prep_done / self.tts.prep_total) if self.tts.prep_total else 1.0
            self.hud.set_loading(frac)
            self.drone.update(None, self.player)
            if self.tts.prep_ready:
                self._become_ready()
            return

        dt = time.dt
        self.level.update(dt)
        self.chaser_stop.tick(dt)

        if self._speak_timer > 0 and not self.recording:
            self._speak_timer -= dt
            if self._speak_timer <= 0:
                self.drone.set_idle()

        if self._pending is not None and not self.recording:
            heard = self._pending[0]
            self._pending = None
            self._resolve_echo(heard)

        if self.manual_pause or self.won:
            return

        # targeting + companion drone
        self._set_target(self._acquire_target())
        if self.target:
            self.target.animate_marker()
        self.drone.update(self.target.root if self.target else None, self.player)

        # the chase
        hidden = self.hidden_timer > 0
        self.chaser.add_crumb(self.player.world_position)
        busted = self.chaser.update(self.player, hidden)
        danger = 0.0 if hidden else self.chaser.danger(self.player)
        self.hud.set_danger(danger)
        self._heartbeat(danger, hidden, dt)

        self._near_cd = max(0.0, self._near_cd - dt)
        if danger > 0.55 and not hidden and self._near_cd <= 0:
            self.dispatch("near")
            self._near_cd = config.DISPATCH_NEAR_COOLDOWN

        # verb timers
        if self.hidden_timer > 0:
            self.hidden_timer -= dt
            if self.hidden_timer <= 0:
                self.hud.set_hidden(False)
        if self.boost_timer > 0:
            self.boost_timer -= dt
            if self.boost_timer <= 0:
                self.player.speed = config.PLAYER_SPEED

        self._check_zone()

        if busted:
            self.on_busted()
            return
        if self.gate_open and distance(self.player.world_position, self.level.trophy_pos) < 2.2:
            self.on_win()

        if self.selftest:
            self._run_selftest()

    # ------------------------------------------------------------ states
    def _become_ready(self):
        self.ready = True
        self.hud.finish_loading()
        if self.selftest:
            return
        self.set_player_active(True)
        self.sfx.play("alarm")
        self.dispatch("start")
        invoke(self.dispatch, "zone1", delay=4.0)

    def _run_selftest(self):
        self._st_frames += 1
        if self._st_frames == 5:
            for inter in self.level.interactables:
                if inter.kind == "scavenge":
                    self.target = inter
                    self._resolve_echo(inter.current_word().word)
                    break
        if self._st_frames == 14:
            self.on_busted()  # exercise destroy + rebuild + reset
        if self._st_frames >= 30:
            Path("selftest_ok.txt").write_text(
                f"ready collected={len(self.collected)} zone={self.zone} "
                f"interactables={len(self.level.interactables)}", encoding="utf-8")
            print("SELFTEST OK")
            application.quit()


# --------------------------------------------------------------------------
app = Ursina()
game = WordMine()


def input(key):
    game.input(key)


def update():
    game.update()


if __name__ == "__main__":
    app.run()
