"""
core/engine.py — State machine: IDLE → CHARGING → FIRING → COOLDOWN → IDLE
Supports callbacks for every state transition.
"""

from enum import Enum, auto
from core.config import EngineConfig


class State(Enum):
    IDLE      = auto()
    CHARGING  = auto()
    FIRING    = auto()
    COOLDOWN  = auto()


class RasenganEngine:
    """
    Central state machine that drives the whole AR effect.

    Callbacks
    ---------
    on_state_change(old: State, new: State)
    on_charge_update(level: float)        # 0.0 – 1.0
    on_fire()
    on_cooldown_end()
    """

    def __init__(self):
        self.cfg              = EngineConfig()
        self.state            = State.IDLE
        self.charge           = 0.0          # 0.0 – 1.0
        self._cooldown_timer  = 0
        self._fire_timer      = 0

        # Callback slots (assign a callable or leave None)
        self.on_state_change  = None
        self.on_charge_update = None
        self.on_fire          = None
        self.on_cooldown_end  = None

    # ─── Public API ───────────────────────────────────────────────────────────

    def notify_gesture(self, gesture: str):
        """
        Feed the current gesture string from hand_detector.
        Expected values: 'open_palm', 'fist', 'point', 'peace', 'none'
        """
        if self.state == State.IDLE:
            if gesture == "fist":
                self._transition(State.CHARGING)

        elif self.state == State.CHARGING:
            if gesture == "fist":
                pass  # keep charging — handled in update()
            elif gesture in ("point", "open_palm"):
                self._trigger_fire()
            elif gesture == "none":
                self._transition(State.IDLE)
                self.charge = 0.0

        elif self.state == State.FIRING:
            pass  # fire holds for FIRE_HOLD_FRAMES regardless

        elif self.state == State.COOLDOWN:
            pass  # wait it out

    def update(self):
        """Call once per frame to advance the state machine."""
        if self.state == State.CHARGING:
            self.charge = min(1.0, self.charge + 0.018)
            if self.on_charge_update:
                self.on_charge_update(self.charge)
            if self.charge >= self.cfg.CHARGE_THRESHOLD:
                self._trigger_fire()

        elif self.state == State.FIRING:
            self._fire_timer -= 1
            if self._fire_timer <= 0:
                self._transition(State.COOLDOWN)
                self._cooldown_timer = self.cfg.COOLDOWN_FRAMES

        elif self.state == State.COOLDOWN:
            self._cooldown_timer -= 1
            if self._cooldown_timer <= 0:
                self.charge = 0.0
                self._transition(State.IDLE)
                if self.on_cooldown_end:
                    self.on_cooldown_end()

    # ─── Properties ───────────────────────────────────────────────────────────

    @property
    def is_idle(self):      return self.state == State.IDLE
    @property
    def is_charging(self):  return self.state == State.CHARGING
    @property
    def is_firing(self):    return self.state == State.FIRING
    @property
    def is_cooldown(self):  return self.state == State.COOLDOWN

    @property
    def cooldown_frac(self):
        """Returns 0.0 (just started cooldown) → 1.0 (done)."""
        if self.cfg.COOLDOWN_FRAMES == 0:
            return 1.0
        return 1.0 - self._cooldown_timer / self.cfg.COOLDOWN_FRAMES

    @property
    def fire_frac(self):
        """Returns 0.0 (just fired) → 1.0 (beam fading out)."""
        if self.cfg.FIRE_HOLD_FRAMES == 0:
            return 1.0
        return 1.0 - self._fire_timer / self.cfg.FIRE_HOLD_FRAMES

    # ─── Internal ─────────────────────────────────────────────────────────────

    def _trigger_fire(self):
        self._fire_timer = self.cfg.FIRE_HOLD_FRAMES
        self._transition(State.FIRING)
        if self.on_fire:
            self.on_fire()

    def _transition(self, new_state: State):
        old = self.state
        self.state = new_state
        if self.on_state_change and old != new_state:
            self.on_state_change(old, new_state)
