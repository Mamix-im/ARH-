"""
effects/glow.py — Anime-style bloom / glow post-process pass.

Provides:
  • region_glow()   – blur + brighten a circular region around the orb
  • bloom_pass()    – full-frame additive bloom
  • lens_flares()   – streak-style flares emanating from a bright point
  • vignette()      – dark-edge vignette overlay
"""

import cv2
import numpy as np
import math
from core.config import Colors, GlowConfig


cfg = GlowConfig()
_c  = Colors()


# ─── helpers ──────────────────────────────────────────────────────────────────

def _ensure_odd(k: int) -> int:
    return k if k % 2 == 1 else k + 1


def _blend(base: np.ndarray, overlay: np.ndarray, alpha: float) -> np.ndarray:
    """Alpha-blend overlay onto base (both uint8 BGR)."""
    return cv2.addWeighted(base, 1.0, overlay, alpha, 0)


# ─── Region glow ──────────────────────────────────────────────────────────────

def region_glow(
    frame: np.ndarray,
    center: tuple[int, int],
    radius: int,
    color_bgr: tuple = Colors.RASENGAN_OUTER,
    intensity: float = cfg.REGION_INTENSITY,
) -> np.ndarray:
    """
    Soft circular glow around `center`.
    Blends a radial gradient blob onto the frame.
    """
    h, w = frame.shape[:2]
    cx, cy = center

    # Create a radial gradient mask
    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2).astype(np.float32)
    mask = np.clip(1.0 - dist / (radius * 2.0), 0, 1) ** 2

    overlay = np.zeros_like(frame, dtype=np.float32)
    for ch, val in enumerate(color_bgr):
        overlay[:, :, ch] = mask * val

    base_f = frame.astype(np.float32)
    result = np.clip(base_f + overlay * intensity, 0, 255).astype(np.uint8)
    return result


# ─── Full-frame bloom ─────────────────────────────────────────────────────────

def bloom_pass(
    frame: np.ndarray,
    intensity: float = cfg.BLOOM_INTENSITY,
    kernel_size: int = cfg.BLOOM_KERNEL,
) -> np.ndarray:
    """
    Extract bright regions, blur heavily, add back additively.
    Creates the classic anime luminous bloom.
    """
    k = _ensure_odd(kernel_size)

    # Threshold bright areas
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, bright_mask = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)

    bright = cv2.bitwise_and(frame, frame, mask=bright_mask)
    blurred = cv2.GaussianBlur(bright, (k, k), 0)

    base_f    = frame.astype(np.float32)
    blurred_f = blurred.astype(np.float32)
    result    = np.clip(base_f + blurred_f * intensity, 0, 255).astype(np.uint8)
    return result


# ─── Lens flare streaks ───────────────────────────────────────────────────────

def lens_flares(
    frame: np.ndarray,
    center: tuple[int, int],
    num_streaks: int = cfg.LENS_FLARE_STREAKS,
    length_frac: float = cfg.LENS_FLARE_LENGTH,
    alpha: float = cfg.LENS_FLARE_ALPHA,
    color_bgr: tuple = Colors.LENS_FLARE,
) -> np.ndarray:
    """
    Draw star-burst lens-flare streaks emanating from `center`.
    """
    h, w   = frame.shape[:2]
    streak = min(h, w) * length_frac
    overlay = frame.copy()

    for i in range(num_streaks):
        angle = math.pi * i / num_streaks          # evenly spaced in half-circle
        dx    = int(math.cos(angle) * streak)
        dy    = int(math.sin(angle) * streak)
        cx, cy = center

        # Draw both directions (full star)
        for sign in (+1, -1):
            ex = cx + sign * dx
            ey = cy + sign * dy
            # gradient line: bright at center, fades out
            pts = np.linspace(0, 1, 20)
            for t0, t1 in zip(pts[:-1], pts[1:]):
                px0 = int(cx + sign * dx * t0)
                py0 = int(cy + sign * dy * t0)
                px1 = int(cx + sign * dx * t1)
                py1 = int(cy + sign * dy * t1)
                fade = int(255 * (1 - t0) ** 2)
                col  = tuple(int(c * fade / 255) for c in color_bgr)
                thick = max(1, int(3 * (1 - t0)))
                cv2.line(overlay, (px0, py0), (px1, py1), col, thick, cv2.LINE_AA)

    return _blend(frame, overlay, alpha)


# ─── Vignette ─────────────────────────────────────────────────────────────────

def vignette(
    frame: np.ndarray,
    strength: float = cfg.VIGNETTE_STRENGTH,
) -> np.ndarray:
    """
    Apply a soft radial vignette (dark edges).
    """
    h, w = frame.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    # Normalised distance from center (0=center, 1=corner)
    dist = np.sqrt(((X - cx) / (w / 2)) ** 2 + ((Y - cy) / (h / 2)) ** 2)
    mask = np.clip(dist, 0, 1) ** 2           # squared for smooth falloff
    mask = (mask * strength * 255).astype(np.uint8)
    vig  = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    result = cv2.subtract(frame, vig)
    return result


# ─── Combined post-process ────────────────────────────────────────────────────

def full_post_process(
    frame: np.ndarray,
    orb_center: tuple[int, int] | None = None,
    orb_radius: int = 80,
    bloom: bool = True,
    flares: bool = True,
    vig: bool = True,
) -> np.ndarray:
    """
    Convenience wrapper: applies all post effects in one call.
    Pass orb_center=None to skip orb-specific effects.
    """
    if orb_center is not None:
        frame = region_glow(frame, orb_center, orb_radius)
    if bloom:
        frame = bloom_pass(frame)
    if orb_center is not None and flares:
        frame = lens_flares(frame, orb_center)
    if vig:
        frame = vignette(frame)
    return frame
