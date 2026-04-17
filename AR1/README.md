# 🌀 Rasengan AR — Real-time Hand-Tracking Jutsu Effect

A Python + OpenCV + MediaPipe project that renders an anime-style Rasengan
chakra orb and blast beam on your webcam feed, driven entirely by hand gestures.

---

## Project Structure

```
rasengan_project/
│
├── main.py                        ← Entry point — full camera loop
│
├── core/
│   ├── config.py                  ← All tunable parameters (colors, speeds, sizes)
│   └── engine.py                  ← State machine: IDLE→CHARGING→FIRING→COOLDOWN
│
├── effects/
│   ├── rasengan.py                ← 5-layer orb renderer
│   ├── beam.py                    ← Multi-layer blast beam + shake + impact ring
│   ├── glow.py                    ← Anime bloom pass (region glow, bloom, flares, vignette)
│   └── particles.py               ← Full particle engine (orbital, burst, ambient)
│
├── hand_tracking/
│   └── hand_detector.py           ← MediaPipe wrapper + gesture classifier
│
├── requirements.txt
└── README.md
```

---

## Setup

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py

# Run without a webcam (mock mode)
python main.py --mock
```

---

## Gestures

| Gesture      | Action                              |
|-------------|--------------------------------------|
| ✊ Fist      | Start charging the Rasengan orb      |
| 👆 Point    | Fire the beam                        |
| 🖐 Open Palm | Fire the beam                        |
| ✌️ Peace    | (no action — reserved for extension) |

The orb **automatically fires** when charge reaches ~85%.

---

## Keyboard Controls (while running)

| Key     | Action                        |
|---------|-------------------------------|
| `Q/ESC` | Quit                          |
| `R`     | Reset state machine           |
| `D`     | Toggle debug skeleton overlay |
| `M`     | Toggle mock mode              |

---

## Tuning

All parameters live in `core/config.py`:

- **`RasenganConfig`** — orb size, charge speed, spiral arms, ring tilt, pulse
- **`BeamConfig`** — beam width, length, layers, shake magnitude
- **`GlowConfig`** — bloom kernel, flare streaks, vignette strength
- **`ParticleConfig`** — particle counts, speeds, gravity, turbulence
- **`EngineConfig`** — charge threshold, cooldown duration
- **`Colors`** — every color in BGR format

---

## Architecture

```
Camera Frame
     │
     ▼
HandDetector.process()
     │  gesture + palm_center
     ▼
RasenganEngine.notify_gesture()
RasenganEngine.update()          ← state machine tick
     │
     ├─ CHARGING ──► RasenganRenderer.draw()  (orb)
     │                ParticleSystem.spawn_orbital()
     │
     ├─ FIRING ───► BeamRenderer.draw()       (beam + shake + impact)
     │                ParticleSystem.spawn_burst()
     │
     └─ any ──────► ParticleSystem.update_and_draw()
                     full_post_process()      (bloom + vignette)
                     draw_hud()
                     cv2.imshow()
```

---

## Extending

**Add a new gesture action** — edit `engine.py` `notify_gesture()` and add a
new state or branch.

**Change orb position** — map `hand.index_tip` instead of `hand.palm_center`
in `main.py` for a fingertip-anchored orb.

**Shoot in finger direction** — compute `direction_angle` from wrist→index_tip
vector and pass it to `beam_rend.draw()`.

**Two-hand mode** — iterate over `hands[0]` and `hands[1]` and render two orbs.
