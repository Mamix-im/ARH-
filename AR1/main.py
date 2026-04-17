"""
main.py — Rasengan AR: full camera → detect → engine → draw → HUD → display loop.

Controls
--------
  Q / ESC   : quit
  R         : reset state machine
  D         : toggle debug / skeleton overlay
  M         : toggle mock mode (no camera needed)
"""

import cv2
import math
import time
import sys
import numpy as np

from core.engine  import RasenganEngine, State
from core.config  import Colors, DisplayConfig, RasenganConfig, BeamConfig
from effects.rasengan  import RasenganRenderer
from effects.beam      import BeamRenderer
from effects.glow      import full_post_process
from effects.particles import ParticleSystem

# Try real detector; fall back to mock
try:
    from hand_tracking.hand_detector import HandDetector
    _DETECTOR_CLASS = HandDetector
except ImportError:
    from hand_tracking.hand_detector import MockHandDetector as _DETECTOR_CLASS

_c   = Colors()
_dc  = DisplayConfig()
_rc  = RasenganConfig()
_bc  = BeamConfig()


# ─── HUD ──────────────────────────────────────────────────────────────────────

def draw_hud(
    frame:   np.ndarray,
    engine:  RasenganEngine,
    gesture: str,
    fps:     float,
) -> np.ndarray:
    h, w = frame.shape[:2]
    p = _dc.HUD_PADDING
    fs = _dc.HUD_FONT_SCALE
    th = _dc.HUD_THICKNESS
    font = cv2.FONT_HERSHEY_SIMPLEX

    # State pill
    state_label = engine.state.name
    state_colors = {
        "IDLE":     (120, 120, 120),
        "CHARGING": (40,  180, 255),
        "FIRING":   (50,  50,  255),
        "COOLDOWN": (80,  200, 120),
    }
    scol = state_colors.get(state_label, (200, 200, 200))
    cv2.putText(frame, f"STATE: {state_label}", (p, p + 20),
                font, fs, scol, th, cv2.LINE_AA)

    # Gesture
    cv2.putText(frame, f"GESTURE: {gesture.upper()}", (p, p + 45),
                font, fs, _c.HUD_TEXT, th, cv2.LINE_AA)

    # FPS
    cv2.putText(frame, f"FPS: {fps:.0f}", (p, p + 70),
                font, fs, _c.HUD_TEXT, th, cv2.LINE_AA)

    # Charge bar
    bar_x   = p
    bar_y   = h - p - 20
    bar_w   = 200
    bar_h   = 14
    charge  = engine.charge
    fill_w  = int(bar_w * charge)
    fill_col = _c.HUD_BAR_FULL if charge >= 1.0 else _c.HUD_BAR_FILL

    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                  _c.HUD_BAR_BG, -1)
    if fill_w > 0:
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h),
                      fill_col, -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                  _c.HUD_ACCENT, 1)
    cv2.putText(frame, f"CHAKRA  {int(charge * 100):3d}%",
                (bar_x, bar_y - 5), font, fs * 0.85, _c.HUD_TEXT, th, cv2.LINE_AA)

    # Key hints
    hints = "[Q] Quit  [R] Reset  [D] Debug  [M] Mock"
    cv2.putText(frame, hints, (p, h - p - 40),
                font, fs * 0.7, (80, 80, 80), 1, cv2.LINE_AA)

    return frame


# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    # ── Init camera ───────────────────────────────────────────────────────────
    mock_mode = "--mock" in sys.argv or "-m" in sys.argv
    cap = None

    if not mock_mode:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[WARN] Could not open camera — switching to mock mode.")
            mock_mode = True

    if mock_mode:
        print("[INFO] Running in mock mode (no camera). "
              "A synthetic frame will be used.")
        from hand_tracking.hand_detector import MockHandDetector
        detector = MockHandDetector()
    else:
        detector = _DETECTOR_CLASS()

    # ── Init subsystems ───────────────────────────────────────────────────────
    engine    = RasenganEngine()
    orb_rend  = RasenganRenderer()
    beam_rend = BeamRenderer()
    particles = None          # initialised on first frame

    debug_mode = False

    # ── Callbacks ─────────────────────────────────────────────────────────────
    _fire_triggered = [False]

    def on_fire():
        _fire_triggered[0] = True
        beam_rend.fire()

    engine.on_fire = on_fire

    # ── FPS counter ───────────────────────────────────────────────────────────
    fps_timer  = time.perf_counter()
    fps_count  = 0
    fps_smooth = 30.0

    print("[INFO] Rasengan AR started.")
    print("[INFO] Make a FIST to charge. Point / Open-Palm to fire.")
    print("[INFO] Press Q or ESC to quit.")

    while True:
        # ── Grab frame ────────────────────────────────────────────────────────
        if mock_mode:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (20, 15, 10)     # dark background
        else:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Frame capture failed.")
                break
            if _dc.FLIP_FRAME:
                frame = cv2.flip(frame, 1)

        h, w = frame.shape[:2]
        cx_frame, cy_frame = w // 2, h // 2

        if particles is None:
            particles = ParticleSystem(w, h)

        # ── Hand detection ────────────────────────────────────────────────────
        hands = detector.process(frame)
        gesture = "none"
        orb_px  = (w // 4, h // 2)    # default position when no hand

        if hands:
            hand = hands[0]
            gesture = hand.gesture

            # Map normalised palm center to pixel coords
            px = int(hand.palm_center[0] * w)
            py = int(hand.palm_center[1] * h)
            orb_px = (px, py)

            if debug_mode:
                detector.draw_landmarks(frame, hand)

        # ── Engine update ─────────────────────────────────────────────────────
        engine.notify_gesture(gesture)
        engine.update()

        # ── Particle spawning ─────────────────────────────────────────────────
        if engine.is_charging:
            orb_radius = int(
                _rc.BASE_RADIUS +
                (_rc.MAX_RADIUS - _rc.BASE_RADIUS) * engine.charge
            )
            if fps_count % 2 == 0:               # spawn every 2 frames
                particles.spawn_orbital(orb_px[0], orb_px[1], orb_radius, count=4)

        if _fire_triggered[0]:
            _fire_triggered[0] = False
            # Beam shoots right (angle=0); adjust if you track finger direction
            particles.spawn_burst(orb_px[0], orb_px[1], angle=0.0)

        # ── Draw particles (behind orb) ────────────────────────────────────────
        frame = particles.update_and_draw(frame, orb_center=orb_px,
                                          orb_radius=orb_radius if engine.is_charging else 60)

        # ── Draw orb ──────────────────────────────────────────────────────────
        if engine.is_charging or engine.is_idle:
            charge_draw = engine.charge if engine.is_charging else 0.0
            if engine.is_charging:
                frame = orb_rend.draw(frame, orb_px, charge_draw)

        # ── Draw beam ─────────────────────────────────────────────────────────
        if engine.is_firing or engine.is_cooldown:
            progress = engine.fire_frac if engine.is_firing else 1.0
            fade     = 1.0 if engine.is_firing else max(0.0, 1.0 - engine.cooldown_frac * 2)
            frame    = beam_rend.draw(
                frame,
                origin          = orb_px,
                direction_angle = 0.0,
                progress        = progress,
                fade            = fade,
            )

        # ── Post-process glow ─────────────────────────────────────────────────
        if engine.is_charging or engine.is_firing:
            frame = full_post_process(
                frame,
                orb_center = orb_px if not engine.is_firing else None,
                orb_radius = orb_radius if engine.is_charging else 60,
                bloom      = True,
                flares     = engine.is_firing,
                vig        = True,
            )

        # ── HUD ───────────────────────────────────────────────────────────────
        fps_count += 1
        now = time.perf_counter()
        if now - fps_timer >= 0.5:
            fps_smooth = fps_count / (now - fps_timer)
            fps_count  = 0
            fps_timer  = now

        frame = draw_hud(frame, engine, gesture, fps_smooth)

        # ── Display ───────────────────────────────────────────────────────────
        cv2.imshow(_dc.WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):        # Q or ESC
            break
        elif key == ord('r'):
            engine = RasenganEngine()
            engine.on_fire = on_fire
            particles.clear()
            print("[INFO] State reset.")
        elif key == ord('d'):
            debug_mode = not debug_mode
            print(f"[INFO] Debug mode: {debug_mode}")
        elif key == ord('m'):
            mock_mode = not mock_mode
            print(f"[INFO] Mock mode: {mock_mode}")

    # ── Cleanup ───────────────────────────────────────────────────────────────
    if cap:
        cap.release()
    detector.close()
    cv2.destroyAllWindows()
    print("[INFO] Rasengan AR stopped.")


if __name__ == "__main__":
    main()
