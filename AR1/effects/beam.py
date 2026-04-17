"""
effects/beam.py — Multi-layer Rasengan blast beam.

Layers (outside → inside)
--------------------------
  1. Edge glow        (widest, most transparent)
  2. Outer fringe
  3. Mid layer
  4. Inner bright
  5. Core             (narrowest, fully opaque white)

Plus:
  • Muzzle flash at origin
  • Expanding impact ring at far end
  • Camera shake controller
"""

import cv2
import numpy as np
import math
import random
from core.config import Colors, BeamConfig

cfg = BeamConfig()
_c  = Colors()


# ─── Camera shake ─────────────────────────────────────────────────────────────

class CameraShake:
    def __init__(self):
        self._frames = 0
        self._mag    = 0

    def trigger(self, magnitude: int = cfg.SHAKE_MAGNITUDE, frames: int = cfg.SHAKE_FRAMES):
        self._frames = frames
        self._mag    = magnitude

    def get_offset(self) -> tuple[int, int]:
        if self._frames <= 0:
            return (0, 0)
        self._frames -= 1
        decay = self._frames / cfg.SHAKE_FRAMES
        ox = int(random.uniform(-self._mag, self._mag) * decay)
        oy = int(random.uniform(-self._mag, self._mag) * decay)
        return (ox, oy)

    @property
    def active(self) -> bool:
        return self._frames > 0


def apply_shake(frame: np.ndarray, offset: tuple[int, int]) -> np.ndarray:
    """Translate the entire frame by offset (wrap-free, black fill)."""
    ox, oy = offset
    M = np.float32([[1, 0, ox], [0, 1, oy]])
    return cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))


# ─── Impact ring ──────────────────────────────────────────────────────────────

class ImpactRing:
    def __init__(self):
        self._active = False
        self._cx = self._cy = 0
        self._r  = 0.0

    def trigger(self, cx: int, cy: int):
        self._active = True
        self._cx = cx
        self._cy = cy
        self._r  = 10.0

    def update_and_draw(self, frame: np.ndarray) -> np.ndarray:
        if not self._active:
            return frame
        alpha = max(0.0, 1.0 - self._r / cfg.IMPACT_RING_MAX)
        col   = tuple(int(c * alpha) for c in _c.IMPACT_RING)
        cv2.circle(frame, (self._cx, self._cy), int(self._r),
                   col, 3, cv2.LINE_AA)
        self._r += cfg.IMPACT_RING_SPEED
        if self._r >= cfg.IMPACT_RING_MAX:
            self._active = False
        return frame


# ─── Muzzle flash ─────────────────────────────────────────────────────────────

def draw_muzzle_flash(
    frame: np.ndarray,
    cx: int, cy: int,
    intensity: float = 1.0,
) -> np.ndarray:
    """Bright radial burst at the beam origin."""
    overlay = np.zeros_like(frame)
    r       = int(cfg.MUZZLE_RADIUS * intensity)
    for i in range(3, 0, -1):
        fade = int(255 * i / 3 * intensity)
        col  = tuple(int(c * fade / 255) for c in _c.MUZZLE_FLASH)
        cv2.circle(overlay, (cx, cy), r * i // 2, col, -1, cv2.LINE_AA)
    blurred = cv2.GaussianBlur(overlay, (31, 31), 0)
    return cv2.addWeighted(frame, 1.0, blurred, intensity * 0.8, 0)


# ─── Beam renderer ────────────────────────────────────────────────────────────

def _gaussian_beam_alpha(half_width: float, distance: float) -> float:
    """Gaussian falloff from beam centre-line."""
    sigma = half_width / 2.5
    if sigma <= 0:
        return 0.0
    return math.exp(-(distance ** 2) / (2 * sigma ** 2))


class BeamRenderer:
    """
    Stateful beam renderer.
    Call draw(frame, origin, direction_angle, progress, fade)
    """

    def __init__(self):
        self.shake      = CameraShake()
        self.impact     = ImpactRing()

    def draw(
        self,
        frame:           np.ndarray,
        origin:          tuple[int, int],
        direction_angle: float = 0.0,   # radians, default: shoot right
        progress:        float = 1.0,   # 0→1 beam length expansion
        fade:            float = 1.0,   # 1→0 after peak
    ) -> np.ndarray:
        """
        Parameters
        ----------
        origin           : (x, y) muzzle point
        direction_angle  : beam direction in radians
        progress         : 0.0=just fired, 1.0=fully extended
        fade             : 1.0=peak, 0.0=fully gone
        """
        h, w  = frame.shape[:2]
        ox, oy = int(origin[0]), int(origin[1])
        beam_len = int(w * cfg.LENGTH_FRAC * progress)

        if beam_len < 2:
            return frame

        dx = math.cos(direction_angle)
        dy = math.sin(direction_angle)

        # Perpendicular unit vector
        px = -dy
        py = dx

        canvas = frame.astype(np.float32)

        # Draw each layer
        layer_colors  = [_c.BEAM_EDGE, _c.BEAM_OUTER, _c.BEAM_MID,
                         _c.BEAM_INNER, _c.BEAM_CORE]
        layer_alphas  = [0.30, 0.50, 0.70, 0.85, 1.00]
        base_hw       = cfg.BASE_WIDTH + (cfg.MAX_WIDTH - cfg.BASE_WIDTH)

        for li, (rel_w, color, alpha) in enumerate(
            zip(cfg.LAYER_WIDTHS, layer_colors, layer_alphas)
        ):
            hw = int(base_hw * rel_w)          # half-width of this layer
            if hw < 1:
                continue
            final_alpha = alpha * fade

            # Build a polygon for this layer
            tip_x = int(ox + dx * beam_len)
            tip_y = int(oy + dy * beam_len)

            pts = np.array([
                [int(ox + px * hw), int(oy + py * hw)],
                [int(ox - px * hw), int(oy - py * hw)],
                [int(tip_x - px * (hw // 2)), int(tip_y - py * (hw // 2))],
                [int(tip_x + px * (hw // 2)), int(tip_y + py * (hw // 2))],
            ], dtype=np.int32)

            layer_img = np.zeros_like(frame)
            cv2.fillPoly(layer_img, [pts], color)
            # Blur for soft edge
            ksize = max(3, hw * 2 + 1) | 1      # must be odd
            blurred = cv2.GaussianBlur(layer_img, (ksize, ksize), 0)
            canvas = np.clip(
                canvas + blurred.astype(np.float32) * final_alpha, 0, 255
            )

        result = canvas.astype(np.uint8)

        # Muzzle flash
        if progress < 0.3 or fade > 0.8:
            flash_intensity = max(progress, fade) * fade
            result = draw_muzzle_flash(result, ox, oy, flash_intensity)

        # Update impact ring
        tip_x = int(ox + dx * beam_len)
        tip_y = int(oy + dy * beam_len)
        if progress >= 0.99 and fade > 0.5:
            self.impact.trigger(tip_x, tip_y)
        result = self.impact.update_and_draw(result)

        # Apply shake
        offset = self.shake.get_offset()
        if offset != (0, 0):
            result = apply_shake(result, offset)

        return result

    def fire(self):
        """Call once when beam is triggered to start shake."""
        self.shake.trigger()
