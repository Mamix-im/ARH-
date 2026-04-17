"""
core/config.py — Central configuration for the Rasengan AR project.
Tune all visual, physics, and timing parameters here.
"""

# ─── COLORS (BGR format for OpenCV) ───────────────────────────────────────────

class Colors:
    # Rasengan core colors
    RASENGAN_CORE       = (255, 255, 255)    # Bright white center
    RASENGAN_MID        = (255, 220, 100)    # Warm yellow-white
    RASENGAN_OUTER      = (255, 140,  30)    # Orange glow
    RASENGAN_GLOW       = (200,  80,   0)    # Deep orange corona
    RASENGAN_SPIRAL     = (180, 200, 255)    # Blue-white spiral arms
    RASENGAN_RING       = (100, 180, 255)    # Electric-blue rings

    # Beam colors
    BEAM_CORE           = (255, 255, 255)    # Pure white
    BEAM_INNER          = (255, 240, 180)    # Hot yellow-white
    BEAM_MID            = (255, 160,  40)    # Orange
    BEAM_OUTER          = (200,  80,   0)    # Dark orange
    BEAM_EDGE           = ( 80,  30,   0)    # Almost-dark fringe
    MUZZLE_FLASH        = (220, 220, 255)    # Cool white flash
    IMPACT_RING         = (  0, 140, 255)    # Bright orange-red

    # Particle colors
    PARTICLE_CHAKRA     = (255, 200,  80)    # Warm chakra energy
    PARTICLE_BURST      = (180, 220, 255)    # Cool burst
    PARTICLE_AMBIENT    = (120, 160, 255)    # Soft blue drift

    # Glow / bloom
    LENS_FLARE          = (200, 220, 255)    # Cold lens streak
    VIGNETTE            = (  0,   0,   0)    # Black edges

    # HUD
    HUD_TEXT            = (200, 230, 255)
    HUD_BAR_BG          = ( 30,  30,  50)
    HUD_BAR_FILL        = (255, 180,  40)
    HUD_BAR_FULL        = (  0, 220, 120)
    HUD_ACCENT          = (  0, 180, 255)


# ─── RASENGAN ORB ──────────────────────────────────────────────────────────────

class RasenganConfig:
    BASE_RADIUS         = 60          # pixels at charge 0 %
    MAX_RADIUS          = 130         # pixels at charge 100 %
    CHARGE_SPEED        = 0.018       # charge units per frame (0-1)
    PULSE_SPEED         = 0.12        # radians per frame (glow pulse)
    PULSE_AMPLITUDE     = 0.18        # fraction of radius

    # Spiral arms
    NUM_ARMS            = 6
    ARM_POINTS          = 40
    ARM_THICKNESS       = 2
    SPIRAL_SPEED        = 0.09        # radians per frame

    # Rotating 3-D rings
    NUM_RINGS           = 3
    RING_TILT_ANGLES    = [0, 60, 120]   # degrees — tilt per ring
    RING_SPEED          = 0.07           # radians per frame
    RING_THICKNESS      = 2

    # Layer opacities (0-1)
    ALPHA_GLOW          = 0.55
    ALPHA_CORE          = 0.90
    ALPHA_SPIRAL        = 0.70
    ALPHA_RING          = 0.65
    ALPHA_SPECULAR      = 0.85


# ─── BEAM ─────────────────────────────────────────────────────────────────────

class BeamConfig:
    BASE_WIDTH          = 60          # pixels at center (half-width)
    MAX_WIDTH           = 110
    LENGTH_FRAC         = 0.85        # fraction of frame width
    NUM_LAYERS          = 5
    LAYER_WIDTHS        = [1.0, 0.65, 0.40, 0.22, 0.10]  # relative to BASE_WIDTH
    BEAM_SPEED          = 0.22        # how fast beam expands (0-1)
    FADE_SPEED          = 0.05        # how fast beam fades after firing
    SHAKE_FRAMES        = 8           # frames of camera shake
    SHAKE_MAGNITUDE     = 14          # pixels
    MUZZLE_RADIUS       = 55
    IMPACT_RING_SPEED   = 6           # pixels per frame expansion
    IMPACT_RING_MAX     = 180


# ─── GLOW / BLOOM ─────────────────────────────────────────────────────────────

class GlowConfig:
    BLOOM_KERNEL        = 61          # must be odd; larger = wider bloom
    BLOOM_INTENSITY     = 0.55
    REGION_BLUR_KERNEL  = 41
    REGION_INTENSITY    = 0.70
    LENS_FLARE_STREAKS  = 6
    LENS_FLARE_LENGTH   = 0.35        # fraction of shorter frame dimension
    LENS_FLARE_ALPHA    = 0.45
    VIGNETTE_STRENGTH   = 0.55        # 0 = none, 1 = full black edges


# ─── PARTICLES ────────────────────────────────────────────────────────────────

class ParticleConfig:
    # Orbital / chakra spiral
    ORBITAL_COUNT       = 60
    ORBITAL_RADIUS_MIN  = 0.9         # fraction of orb radius
    ORBITAL_RADIUS_MAX  = 2.2
    ORBITAL_INWARD_V    = 0.8         # px per frame inward drift
    ORBITAL_SPEED       = 0.08        # angular speed

    # Burst (beam firing)
    BURST_COUNT         = 120
    BURST_SPEED_MIN     = 4
    BURST_SPEED_MAX     = 18
    BURST_LIFE          = 35          # frames

    # Ambient drift
    AMBIENT_COUNT       = 40
    AMBIENT_SPEED       = 0.6
    AMBIENT_LIFE        = 80

    # Physics
    GRAVITY             = 0.12        # px per frame² downward
    TURBULENCE          = 0.25        # random velocity nudge per frame
    SIZE_MIN            = 2
    SIZE_MAX            = 6


# ─── STATE MACHINE ────────────────────────────────────────────────────────────

class EngineConfig:
    CHARGE_THRESHOLD    = 0.85        # charge level to auto-trigger fire
    COOLDOWN_FRAMES     = 55          # frames before returning to IDLE
    FIRE_HOLD_FRAMES    = 30          # minimum frames beam is held on


# ─── CAMERA / DISPLAY ─────────────────────────────────────────────────────────

class DisplayConfig:
    WINDOW_NAME         = "Rasengan AR"
    FLIP_FRAME          = True        # mirror like a selfie cam
    TARGET_FPS          = 30
    HUD_FONT_SCALE      = 0.6
    HUD_THICKNESS       = 1
    HUD_PADDING         = 12
