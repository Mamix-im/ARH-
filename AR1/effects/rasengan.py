"""
effects/rasengan.py — 5-layer orb renderer.

Layers (bottom → top)
---------------------
  1. Pulsing outer glow halo
  2. Radial gradient core ball
  3. Spiral chakra arms (rotating)
  4. Rotating 3-D tilt rings
  5. Specular highlight (top-left hotspot)

The orb size scales with `charge_level` (0.0 – 1.0).
"""

import cv2
import numpy as np
import math
from core.config import Colors, RasenganConfig

cfg = RasenganConfig()
_c  = Colors()


def _alpha_blend(
    base:    np.ndarray,
    overlay: np.ndarray,
    alpha:   float,
    mask:    np.ndarray | None = None,
) -> np.ndarray:
    """
    Blend overlay onto base at `alpha` (0–1).
    Optional uint8 single-channel `mask` restricts the region.
    """
    result = base.astype(np.float32)
    ov     = overlay.astype(np.float32)
    if mask is not None:
        m = mask.astype(np.float32) / 255.0
        for ch in range(3):
            result[:, :, ch] += ov[:, :, ch] * m * alpha
    else:
        result = result + ov * alpha
    return np.clip(result, 0, 255).astype(np.uint8)


# ─── Layer 1 – pulsing glow halo ─────────────────────────────────────────────

def _draw_glow(
    canvas:  np.ndarray,
    cx: int, cy: int,
    radius: int,
    pulse_offset: float,
) -> np.ndarray:
    """Soft radial gradient corona around the orb."""
    h, w = canvas.shape[:2]
    pulse_r = int(radius * (1.0 + cfg.PULSE_AMPLITUDE * math.sin(pulse_offset)))

    Y, X   = np.ogrid[:h, :w]
    dist   = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2).astype(np.float32)
    glow   = np.clip(1.0 - dist / (pulse_r * 2.5), 0, 1) ** 2

    overlay = np.zeros_like(canvas, dtype=np.float32)
    for ch, val in enumerate(_c.RASENGAN_GLOW):
        overlay[:, :, ch] = glow * val

    base_f = canvas.astype(np.float32)
    return np.clip(base_f + overlay * cfg.ALPHA_GLOW, 0, 255).astype(np.uint8)


# ─── Layer 2 – gradient core ball ────────────────────────────────────────────

def _draw_core(
    canvas: np.ndarray,
    cx: int, cy: int,
    radius: int,
) -> np.ndarray:
    overlay = np.zeros_like(canvas)
    steps   = 8
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        t = i / steps                                  # 1 at edge, 0 at centre
        col = tuple(
            int(_c.RASENGAN_OUTER[ch] * t + _c.RASENGAN_CORE[ch] * (1 - t))
            for ch in range(3)
        )
        cv2.circle(overlay, (cx, cy), r, col, -1, cv2.LINE_AA)
    return _alpha_blend(canvas, overlay, cfg.ALPHA_CORE)


# ─── Layer 3 – spiral chakra arms ────────────────────────────────────────────

def _draw_spirals(
    canvas:   np.ndarray,
    cx: int, cy: int,
    radius: int,
    spin:   float,
) -> np.ndarray:
    overlay = np.zeros_like(canvas)
    for arm in range(cfg.NUM_ARMS):
        base_angle = spin + arm * (math.tau / cfg.NUM_ARMS)
        pts = []
        for k in range(cfg.ARM_POINTS):
            t     = k / cfg.ARM_POINTS
            r     = radius * 0.25 + (radius * 1.2 - radius * 0.25) * t
            angle = base_angle + t * math.pi * 2.5    # 1.25 full turns per arm
            pts.append((int(cx + math.cos(angle) * r),
                        int(cy + math.sin(angle) * r)))
        pts = np.array(pts, dtype=np.int32)
        for i in range(len(pts) - 1):
            alpha_local = int(255 * (1 - i / len(pts)))
            col = tuple(int(c * alpha_local / 255) for c in _c.RASENGAN_SPIRAL)
            cv2.line(overlay, tuple(pts[i]), tuple(pts[i + 1]),
                     col, cfg.ARM_THICKNESS, cv2.LINE_AA)
    return _alpha_blend(canvas, overlay, cfg.ALPHA_SPIRAL)


# ─── Layer 4 – rotating 3-D rings ────────────────────────────────────────────

def _draw_rings(
    canvas:    np.ndarray,
    cx: int, cy: int,
    radius: int,
    ring_spin: float,
) -> np.ndarray:
    overlay = np.zeros_like(canvas)
    for i, tilt_deg in enumerate(cfg.RING_TILT_ANGLES):
        tilt  = math.radians(tilt_deg + ring_spin * 57.3)  # convert spin to deg first
        phase = ring_spin + i * (math.tau / cfg.NUM_RINGS)
        pts   = []
        for k in range(72):
            angle = k * (math.tau / 72)
            x3d   = math.cos(angle) * radius
            y3d   = math.sin(angle) * radius
            # Project: rotate around Y axis by `tilt`
            x2d = int(cx + x3d * math.cos(tilt))
            y2d = int(cy + y3d)
            pts.append((x2d, y2d))
        pts = np.array(pts, dtype=np.int32)
        cv2.polylines(overlay, [pts], isClosed=True,
                      color=_c.RASENGAN_RING,
                      thickness=cfg.RING_THICKNESS,
                      lineType=cv2.LINE_AA)
    return _alpha_blend(canvas, overlay, cfg.ALPHA_RING)


# ─── Layer 5 – specular highlight ────────────────────────────────────────────

def _draw_specular(
    canvas: np.ndarray,
    cx: int, cy: int,
    radius: int,
) -> np.ndarray:
    overlay = np.zeros_like(canvas)
    spec_cx = cx - int(radius * 0.30)
    spec_cy = cy - int(radius * 0.30)
    spec_r  = max(3, int(radius * 0.22))
    cv2.circle(overlay, (spec_cx, spec_cy), spec_r,
               _c.RASENGAN_CORE, -1, cv2.LINE_AA)
    blurred = cv2.GaussianBlur(overlay, (spec_r * 2 + 1, spec_r * 2 + 1), 0)
    return _alpha_blend(canvas, blurred, cfg.ALPHA_SPECULAR)


# ─── Public draw function ─────────────────────────────────────────────────────

class RasenganRenderer:
    """
    Stateful renderer — keeps internal animation timers.
    Call draw(frame, center, charge_level) every frame.
    """

    def __init__(self):
        self._spiral_angle = 0.0
        self._ring_angle   = 0.0
        self._pulse_offset = 0.0

    def draw(
        self,
        frame:        np.ndarray,
        center:       tuple[int, int],
        charge_level: float = 1.0,
    ) -> np.ndarray:
        """
        Composite all 5 layers onto `frame`.

        Parameters
        ----------
        frame        : BGR uint8 image
        center       : (x, y) pixel position of orb center
        charge_level : 0.0 – 1.0
        """
        cx, cy = int(center[0]), int(center[1])
        radius = int(
            cfg.BASE_RADIUS + (cfg.MAX_RADIUS - cfg.BASE_RADIUS) * charge_level
        )

        canvas = frame.copy()
        canvas = _draw_glow   (canvas, cx, cy, radius, self._pulse_offset)
        canvas = _draw_core   (canvas, cx, cy, radius)
        canvas = _draw_spirals(canvas, cx, cy, radius, self._spiral_angle)
        canvas = _draw_rings  (canvas, cx, cy, radius, self._ring_angle)
        canvas = _draw_specular(canvas, cx, cy, radius)

        # Advance animation
        self._spiral_angle = (self._spiral_angle + cfg.SPIRAL_SPEED) % math.tau
        self._ring_angle   = (self._ring_angle   + cfg.RING_SPEED)   % math.tau
        self._pulse_offset = (self._pulse_offset + cfg.PULSE_SPEED)  % math.tau

        return canvas
