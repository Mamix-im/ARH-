"""
effects/particles.py — Full particle engine.

Particle types
--------------
  OrbitalParticle  – chakra spiralling inward toward the orb
  BurstParticle    – explode outward when beam fires
  AmbientParticle  – gentle ambient drift floating around

All particles respect:
  • gravity         (configurable)
  • turbulence      (random velocity nudge per frame)
  • life cycle      (born → alive → dead, with alpha fade)
"""

import cv2
import numpy as np
import math
import random
from dataclasses import dataclass, field
from typing import List
from core.config import Colors, ParticleConfig

cfg = ParticleConfig()
_c  = Colors()
rng = np.random.default_rng()


# ─── Base particle ────────────────────────────────────────────────────────────

@dataclass
class Particle:
    x:      float
    y:      float
    vx:     float
    vy:     float
    life:   int            # frames remaining
    max_life: int
    size:   float
    color:  tuple          # BGR
    alpha:  float = 1.0

    @property
    def alive(self) -> bool:
        return self.life > 0

    @property
    def life_frac(self) -> float:
        return self.life / max(self.max_life, 1)

    def _physics(self):
        self.vx += rng.uniform(-cfg.TURBULENCE, cfg.TURBULENCE)
        self.vy += cfg.GRAVITY
        self.x  += self.vx
        self.y  += self.vy
        self.life -= 1

    def draw(self, frame: np.ndarray):
        raise NotImplementedError


# ─── Orbital / chakra particle ────────────────────────────────────────────────

class OrbitalParticle(Particle):
    """
    Orbits at a radius then spirals inward as it ages.
    Gives the classic Rasengan chakra-winding look.
    """
    def __init__(self, cx: float, cy: float, orb_radius: float):
        r     = orb_radius * random.uniform(cfg.ORBITAL_RADIUS_MIN, cfg.ORBITAL_RADIUS_MAX)
        angle = random.uniform(0, math.tau)
        life  = random.randint(40, 70)
        size  = random.uniform(cfg.SIZE_MIN, cfg.SIZE_MAX)
        super().__init__(
            x        = cx + math.cos(angle) * r,
            y        = cy + math.sin(angle) * r,
            vx       = 0.0,
            vy       = 0.0,
            life     = life,
            max_life = life,
            size     = size,
            color    = _c.PARTICLE_CHAKRA,
        )
        self._cx    = cx
        self._cy    = cy
        self._r     = r
        self._angle = angle
        self._orb_r = orb_radius

    def update(self, cx: float, cy: float):
        """Update center position and advance spiral."""
        self._cx     = cx
        self._cy     = cy
        self._angle += cfg.ORBITAL_SPEED
        self._r      = max(0, self._r - cfg.ORBITAL_INWARD_V)
        self.x       = cx + math.cos(self._angle) * self._r
        self.y       = cy + math.sin(self._angle) * self._r
        self.life   -= 1
        self.alpha   = self.life_frac

    def draw(self, frame: np.ndarray):
        if not self.alive:
            return
        a    = max(0.0, min(1.0, self.alpha))
        col  = tuple(int(c * a) for c in self.color)
        r    = max(1, int(self.size * self.life_frac))
        cv2.circle(frame, (int(self.x), int(self.y)), r, col, -1, cv2.LINE_AA)


# ─── Burst particle ───────────────────────────────────────────────────────────

class BurstParticle(Particle):
    """Launches outward in a cone when the beam fires."""

    def __init__(self, cx: float, cy: float, direction_angle: float = 0.0):
        spread = math.pi / 6                  # ±30° cone
        angle  = direction_angle + random.uniform(-spread, spread)
        speed  = random.uniform(cfg.BURST_SPEED_MIN, cfg.BURST_SPEED_MAX)
        life   = random.randint(20, cfg.BURST_LIFE)
        size   = random.uniform(cfg.SIZE_MIN, cfg.SIZE_MAX)
        super().__init__(
            x        = cx,
            y        = cy,
            vx       = math.cos(angle) * speed,
            vy       = math.sin(angle) * speed,
            life     = life,
            max_life = life,
            size     = size,
            color    = _c.PARTICLE_BURST,
        )

    def update(self):
        self._physics()
        self.alpha = self.life_frac ** 0.6    # slightly slower fade

    def draw(self, frame: np.ndarray):
        if not self.alive:
            return
        a   = max(0.0, min(1.0, self.alpha))
        col = tuple(int(c * a) for c in self.color)
        r   = max(1, int(self.size * self.life_frac))
        cv2.circle(frame, (int(self.x), int(self.y)), r, col, -1, cv2.LINE_AA)
        # trail line
        tx = int(self.x - self.vx * 3)
        ty = int(self.y - self.vy * 3)
        cv2.line(frame, (int(self.x), int(self.y)), (tx, ty), col, 1, cv2.LINE_AA)


# ─── Ambient drift particle ───────────────────────────────────────────────────

class AmbientParticle(Particle):
    """Slow dreamy particles floating in the background."""

    def __init__(self, frame_w: int, frame_h: int):
        life = random.randint(50, cfg.AMBIENT_LIFE)
        size = random.uniform(1, 3)
        super().__init__(
            x        = random.uniform(0, frame_w),
            y        = random.uniform(0, frame_h),
            vx       = random.uniform(-cfg.AMBIENT_SPEED, cfg.AMBIENT_SPEED),
            vy       = random.uniform(-cfg.AMBIENT_SPEED * 0.5, cfg.AMBIENT_SPEED * 0.5),
            life     = life,
            max_life = life,
            size     = size,
            color    = _c.PARTICLE_AMBIENT,
        )

    def update(self):
        self.vx += rng.uniform(-0.1, 0.1)
        self.vy += rng.uniform(-0.1, 0.1)
        self.x  += self.vx
        self.y  += self.vy
        self.life -= 1
        # Soft fade in + fade out
        frac = self.life_frac
        self.alpha = 4 * frac * (1 - frac)   # bell curve

    def draw(self, frame: np.ndarray):
        if not self.alive:
            return
        a   = max(0.0, min(1.0, self.alpha))
        col = tuple(int(c * a) for c in self.color)
        cv2.circle(frame, (int(self.x), int(self.y)), max(1, int(self.size)), col, -1, cv2.LINE_AA)


# ─── Particle manager ─────────────────────────────────────────────────────────

class ParticleSystem:
    """
    Manages all particle pools.
    Call spawn_orbital / spawn_burst / ensure_ambient as appropriate,
    then call update_and_draw(frame) each frame.
    """

    def __init__(self, frame_w: int, frame_h: int):
        self.fw = frame_w
        self.fh = frame_h
        self._orbital:  List[OrbitalParticle] = []
        self._burst:    List[BurstParticle]   = []
        self._ambient:  List[AmbientParticle] = []

    # ── Spawners ──────────────────────────────────────────────────────────────

    def spawn_orbital(self, cx: float, cy: float, orb_radius: float, count: int = 3):
        for _ in range(count):
            self._orbital.append(OrbitalParticle(cx, cy, orb_radius))

    def spawn_burst(self, cx: float, cy: float, angle: float = 0.0, count: int = None):
        n = count if count is not None else cfg.BURST_COUNT
        for _ in range(n):
            self._burst.append(BurstParticle(cx, cy, angle))

    def ensure_ambient(self):
        """Top up ambient pool to AMBIENT_COUNT."""
        needed = cfg.AMBIENT_COUNT - len(self._ambient)
        for _ in range(max(0, needed)):
            self._ambient.append(AmbientParticle(self.fw, self.fh))

    # ── Update + draw ─────────────────────────────────────────────────────────

    def update_and_draw(
        self,
        frame: np.ndarray,
        orb_center: tuple[float, float] | None = None,
        orb_radius: float = 80,
    ) -> np.ndarray:

        overlay = frame.copy()

        # Ambient
        self.ensure_ambient()
        for p in self._ambient:
            p.update()
            p.draw(overlay)
        self._ambient = [p for p in self._ambient if p.alive]

        # Orbital
        if orb_center:
            cx, cy = orb_center
            for p in self._orbital:
                p.update(cx, cy)
                p.draw(overlay)
        self._orbital = [p for p in self._orbital if p.alive]

        # Burst
        for p in self._burst:
            p.update()
            p.draw(overlay)
        self._burst = [p for p in self._burst if p.alive]

        return cv2.addWeighted(frame, 0.0, overlay, 1.0, 0)

    def clear(self):
        self._orbital.clear()
        self._burst.clear()
        self._ambient.clear()
