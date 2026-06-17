"""
WordMine -- a peaceful 3D audio-first ESL progression game.

The runtime reuses the original free-look 3D architecture, TTS cache,
interactables, SRS progress store, and text-free HUD, but the game loop is now
listen -> act -> feedback.  There is no chase, no alarm pressure, no busted
state, and no required speaking in the first learner path.

Run:  python main.py   (or run_wordmine.bat)
"""
from __future__ import annotations

import os
from pathlib import Path

from ursina import (
    Ursina, Sky, DirectionalLight, AmbientLight, Vec2, Vec3,
    camera, color, mouse, time, window, application, raycast, invoke, distance,
)
from ursina.prefabs.first_person_controller import FirstPersonController

import config
from game.drone import CompanionDrone
from game.hud import HUD
from game.interactables import _color
from game.level import Level
from esl import loader
from esl.engine import SRSDirector
from esl.tts import TTSEngine
from esl.sfx import SFX


LEVEL_PROMPTS = {
    1: [
        {"phrase": "Apple.", "target": "apple"},
        {"phrase": "Cup.", "target": "cup"},
        {"phrase": "Ball.", "target": "ball"},
        {"phrase": "Book.", "target": "book"},
        {"phrase": "Go to the next room.", "target": "open"},
        {"phrase": "Find the key.", "target": "key"},
        {"phrase": "Find the box.", "target": "box"},
        {"phrase": "Touch the table.", "target": "table"},
        {"phrase": "Touch the basket.", "target": "basket"},
        {"phrase": "Go to the next room.", "target": "open"},
        {"phrase": "Find the robot.", "target": "robot"},
        {"phrase": "Touch the apple.", "target": "apple"},
        {"phrase": "Touch the cup.", "target": "cup"},
        {"phrase": "Touch the book.", "target": "book"},
        {"phrase": "Touch the ball.", "target": "ball"},
        {"phrase": "Go to the next level.", "target": "open"},
    ],
    2: [
        {"phrase": "Banana.", "target": "banana"},
        {"phrase": "Chair.", "target": "chair"},
        {"phrase": "Shoe.", "target": "shoe"},
        {"phrase": "Car.", "target": "car"},
        {"phrase": "Go to the next room.", "target": "open"},
        {"phrase": "Find the bed.", "target": "bed"},
        {"phrase": "Find the dog.", "target": "dog"},
        {"phrase": "Touch the table.", "target": "table"},
        {"phrase": "Touch the basket.", "target": "basket"},
        {"phrase": "Go to the next room.", "target": "open"},
        {"phrase": "Find the robot.", "target": "robot"},
        {"phrase": "Red apple.", "target": "red_apple"},
        {"phrase": "Green apple.", "target": "green_apple"},
        {"phrase": "Big apple.", "target": "big_apple"},
        {"phrase": "Small apple.", "target": "small_apple"},
        {"phrase": "Put the red apple in the basket.", "action": "place", "target": "red_apple", "destination": "basket"},
        {"phrase": "Put the green apple on the table.", "action": "place", "target": "green_apple", "destination": "table"},
        {"phrase": "Put the big apple in the box.", "action": "place", "target": "big_apple", "destination": "box"},
        {"phrase": "Put the small apple on the chair.", "action": "place", "target": "small_apple", "destination": "chair"},
        {"phrase": "Touch the banana.", "target": "banana"},
        {"phrase": "Touch the chair.", "target": "chair"},
        {"phrase": "Touch the shoe.", "target": "shoe"},
        {"phrase": "Touch the car.", "target": "car"},
    ],
}

WELCOME_LINE = "Welcome. Listen and touch."
LEVEL_START_LINES = {
    2: "Level two. Listen and touch.",
}
FINISH_LINE = "Great job. You finished level two."


class WordMine:
    def __init__(self):
        window.title = "WordMine — ESL Listening Rooms"
        window.borderless = False
        window.fullscreen = False
        window.exit_button.visible = True
        window.fps_counter.enabled = True
        window.color = color.rgb(0.07, 0.08, 0.11)

        self.selftest = bool(os.environ.get("WORDMINE_SELFTEST"))
        audio_enabled = config.TTS_ENABLED and not self.selftest

        words = loader.load_vocabulary(config.VOCAB_FILES)
        self.tts = TTSEngine(
            voice=config.TTS_VOICE, rate=config.TTS_RATE, volume=config.TTS_VOLUME,
            cache_dir=config.TTS_CACHE_DIR, enabled=audio_enabled,
        )
        self.sfx = SFX(config.CACHE_DIR / "sfx", enabled=audio_enabled)
        self.srs = SRSDirector(
            words, progress_path=config.PROGRESS_FILE,
            match_threshold=config.SPEECH_MATCH_THRESHOLD,
            xp_per_correct=config.XP_PER_CORRECT,
        )

        # calm classroom/adventure atmosphere
        Sky(color=color.rgb(0.12, 0.16, 0.22))
        sun = DirectionalLight()
        sun.look_at(Vec3(1, -1.3, 0.6))
        sun.color = color.rgba(0.9, 0.86, 0.78, 1)
        AmbientLight(color=color.rgba(0.48, 0.50, 0.56, 1))

        self.player = FirstPersonController(height=1.8, mouse_sensitivity=Vec2(
            config.MOUSE_SENSITIVITY, config.MOUSE_SENSITIVITY))
        self.player.cursor.enabled = False
        self.player.speed = config.PLAYER_SPEED
        camera.fov = config.CAMERA_FOV

        self.hud = HUD()
        self.drone = CompanionDrone()
        self.max_level = max(LEVEL_PROMPTS)
        self.level_number = 1
        self.current_prompts = LEVEL_PROMPTS[self.level_number]
        self.level = Level(self.srs, level_number=self.level_number,
                           has_next_level=self.level_number < self.max_level)

        self.target = None
        self.carried = None
        self.ready = False
        self.manual_pause = False
        self.lesson_done = False
        self.prompt_index = -1
        self.current_prompt = None
        self._prompt_delay = 0.0
        self._level_transition_delay = 0.0
        self._speak_timer = 0.0
        self._st_frames = 0

        self.reset_state()
        self.player.enabled = False
        mouse.locked = False

        # Pre-bake narrator words, level prompts, praise, and common feedback.
        pairs = [(w.word, config.TTS_VOICE) for w in words]
        for prompts in LEVEL_PROMPTS.values():
            pairs += [(p["phrase"], config.TTS_VOICE) for p in prompts]
        pairs += [(p, config.TTS_VOICE) for p in config.PRAISE]
        pairs += [(WELCOME_LINE, config.TTS_VOICE), (FINISH_LINE, config.TTS_VOICE)]
        pairs += [(p, config.TTS_VOICE) for p in LEVEL_START_LINES.values()]
        self.tts.prebake_pairs(pairs)

    # ------------------------------------------------------------- state
    def reset_state(self):
        self.player.position = Vec3(*self.level.start_pos)
        self.player.rotation_y = 180
        self.player.speed = config.PLAYER_SPEED
        self.target = None
        self.carried = None
        self.hud.set_reticle("idle")
        self.hud.set_hidden(False)
        self.hud.set_danger(0)
        self.hud.clear_pips()

    def set_player_active(self, active):
        self.player.enabled = active
        mouse.locked = active
        self.hud.reticle.enabled = active

    def _load_next_level(self):
        if self.level_number >= self.max_level:
            self._finish_lesson()
            return
        if self.target:
            self.target.set_highlight(False)
            self.target = None
        self.level.destroy()
        self.level_number += 1
        self.current_prompts = LEVEL_PROMPTS[self.level_number]
        self.level = Level(self.srs, level_number=self.level_number,
                           has_next_level=self.level_number < self.max_level)
        self.lesson_done = False
        self.prompt_index = -1
        self.current_prompt = None
        self._level_transition_delay = 0.0
        self.reset_state()
        start_line = LEVEL_START_LINES.get(self.level_number)
        if start_line:
            self.tts.speak(start_line)
            self.drone.set_speaking()
            self._speak_timer = 1.3
        self._prompt_delay = 0.05 if self.selftest else 1.5

    # --------------------------------------------------------- prompts
    def _advance_prompt(self):
        self.prompt_index += 1
        if self.prompt_index >= len(self.current_prompts):
            self._finish_lesson()
            return
        self.current_prompt = self.current_prompts[self.prompt_index]
        self._speak_prompt()

    def _speak_prompt(self):
        if not self.current_prompt:
            return
        self.tts.speak(self.current_prompt["phrase"])
        self.drone.set_speaking()
        self._speak_timer = 1.3

    def _finish_lesson(self):
        self.lesson_done = True
        self.current_prompt = None
        self.sfx.play("win")
        self.tts.speak(FINISH_LINE)
        self.drone.flash_good()
        if getattr(self.level, "trophy", None):
            self.level.trophy.animate_scale(1.25, duration=0.4)

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
        else:
            self.hud.set_reticle("idle")
            self.drone.set_idle()

    # --------------------------------------------------------- actions
    def _open_barrier(self, bar):
        bar.collision = False
        bar.animate_color(color.rgba(bar.color[0], bar.color[1], bar.color[2], 0), duration=0.5)
        invoke(setattr, bar, "enabled", False, delay=0.6)

    def _act_on_target(self):
        if (
            self._prompt_delay > 0 or self._level_transition_delay > 0 or
            self.lesson_done or not self.current_prompt or not self.target
        ):
            return
        word = self.target.current_word()
        if not word:
            return

        if self.current_prompt.get("action") == "place":
            self._handle_place_prompt(self.target)
            return

        expected = self.current_prompt["target"]
        correct = word.id == expected
        self.srs.record(word.id, correct)

        if correct:
            self.drone.flash_good()
            self.sfx.play("success")
            result = self._apply_success(self.target)
            self.target = None
            self.hud.set_reticle("idle")
            if result == "level_transition":
                # The barrier fades and disables after 0.6s.  Even in selftest,
                # wait long enough before destroying Level 1 so Panda/Ursina
                # does not try to stash a NodePath that has already been removed.
                self._level_transition_delay = 0.75 if self.selftest else 1.0
            else:
                self._prompt_delay = 0.05 if self.selftest else 1.0
        else:
            self.drone.flash_bad()
            self.sfx.play("fail")
            self.tts.speak(f"{word.word}. {self.current_prompt['phrase']}")
            self.drone.set_speaking()
            self._speak_timer = 1.4

    def _speak_correction(self, word):
        self.drone.flash_bad()
        self.sfx.play("fail")
        self.tts.speak(f"{word.word}. {self.current_prompt['phrase']}")
        self.drone.set_speaking()
        self._speak_timer = 1.4

    def _disable_interactable_collider(self, inter, disabled=True):
        collider = getattr(inter, "collider_entity", None)
        if collider is None:
            return
        try:
            collider.enabled = not disabled
        except Exception:  # noqa: BLE001 - Ursina collider state is best-effort.
            pass

    def _pick_up(self, inter):
        self.carried = inter
        self._disable_interactable_collider(inter, True)
        inter.set_highlight(False)
        self.sfx.play("select")
        self.drone.flash_good()
        self.target = None
        self.hud.set_reticle("idle")

    def _place_carried(self, destination):
        item = self.carried
        if not item:
            return None
        item_word = item.current_word()
        item.root.parent = None
        item.root.position = destination.root.world_position + Vec3(0, 0.55, 0)
        self._disable_interactable_collider(item, False)
        item.repeatable = False
        item.succeed()
        self.carried = None
        return item_word

    def _complete_place_prompt(self, placed_word):
        self.drone.flash_good()
        self.sfx.play("success")
        spec = placed_word.world_object or {}
        self.hud.add_pip(_color(spec.get("color", [1, 1, 1])))
        if self.target:
            self.target.set_highlight(False)
        self.target = None
        self.hud.set_reticle("idle")
        self._prompt_delay = 0.05 if self.selftest else 1.0

    def _handle_place_prompt(self, inter):
        word = inter.current_word()
        if not word:
            return
        expected_item = self.current_prompt["target"]
        expected_destination = self.current_prompt["destination"]

        if self.carried is None:
            correct_item = word.id == expected_item and inter.kind != "gate"
            self.srs.record(word.id, correct_item)
            if correct_item:
                self._pick_up(inter)
            else:
                self._speak_correction(word)
            return

        carried_word = self.carried.current_word()
        correct_destination = word.id == expected_destination
        self.srs.record(word.id, correct_destination)
        if correct_destination:
            placed_word = self._place_carried(inter) or carried_word
            self._complete_place_prompt(placed_word)
        else:
            self._speak_correction(word)

    def _apply_success(self, inter):
        word = inter.current_word()
        if inter.kind == "gate":
            self._open_barrier(inter.payload["barrier"])
            self.sfx.play("gate")
            result = "level_transition" if inter.payload.get("transition") == "level" else "room_transition"
        else:
            spec = word.world_object or {}
            self.hud.add_pip(_color(spec.get("color", [1, 1, 1])))
            inter.root.animate_y(inter.root.y + 0.18, duration=0.18)
            invoke(inter.root.animate_y, inter.root.y, duration=0.18, delay=0.2)
            result = "prompt"
        inter.succeed()
        return result

    def _update_carried(self):
        if not self.carried:
            return
        self.carried.root.position = camera.world_position + camera.forward * 1.35 + Vec3(0, -0.35, 0)
        self.carried.root.rotation_y = camera.rotation_y

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
        if key in ("left mouse down", "e", "space"):
            self._act_on_target()
        elif key == "r" and self.current_prompt:
            self._speak_prompt()

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
        self._update_carried()

        if self._speak_timer > 0:
            self._speak_timer -= dt
            if self._speak_timer <= 0:
                self.drone.set_idle()

        if self.manual_pause:
            return

        self._set_target(self._acquire_target())
        if self.target:
            self.target.animate_marker()
        self.drone.update(self.target.root if self.target else None, self.player)

        if self._level_transition_delay > 0:
            self._level_transition_delay -= dt
            if self._level_transition_delay <= 0:
                self._load_next_level()
            return

        if self._prompt_delay > 0:
            self._prompt_delay -= dt
            if self._prompt_delay <= 0:
                self._advance_prompt()

        if self.lesson_done and distance(self.player.world_position, self.level.exit_pos) < 2.2:
            self.drone.flash_good()

        if self.selftest:
            self._run_selftest()

    # ------------------------------------------------------------ ready/test
    def _become_ready(self):
        self.ready = True
        self.hud.finish_loading()
        if self.selftest:
            self._advance_prompt()
            return
        self.set_player_active(True)
        self.tts.speak(WELCOME_LINE)
        invoke(self._advance_prompt, delay=2.0)

    def _run_selftest(self):
        self._st_frames += 1
        if self._prompt_delay > 0 or self._level_transition_delay > 0:
            return
        if self.current_prompt and not self.lesson_done:
            if self.current_prompt.get("action") == "place" and self.carried is not None:
                target_id = self.current_prompt["destination"]
            else:
                target_id = self.current_prompt["target"]
            for inter in self.level.interactables:
                word = inter.current_word()
                if inter.available() and word and word.id == target_id:
                    self.target = inter
                    self._act_on_target()
                    break
        if self.lesson_done or self._st_frames >= 600:
            Path("selftest_ok.txt").write_text(
                f"ready level={self.level_number} prompts={self.prompt_index} "
                f"done={self.lesson_done} interactables={len(self.level.interactables)}",
                encoding="utf-8")
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
