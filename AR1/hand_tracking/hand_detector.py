"""
hand_tracking/hand_detector.py — MediaPipe hands wrapper + gesture classifier.

Detected gestures
-----------------
  'open_palm'  – all 5 fingers extended
  'fist'       – all fingers curled
  'point'      – only index finger extended
  'peace'      – index + middle extended, others curled
  'none'       – no hand detected or ambiguous
"""

from __future__ import annotations
import math
import numpy as np

try:
    import mediapipe as mp
    _MP_AVAILABLE = True
except ImportError:
    _MP_AVAILABLE = False

# Landmark indices (MediaPipe hand landmark model)
# Tip indices:  thumb=4, index=8, middle=12, ring=16, pinky=20
# Pip indices:  thumb=3, index=6, middle=10, ring=14, pinky=18

_TIPS = [4, 8, 12, 16, 20]
_PIPS = [3, 6, 10, 14, 18]


class HandInfo:
    """Snapshot of a detected hand for one frame."""
    __slots__ = ("landmarks", "gesture", "palm_center", "wrist", "index_tip")

    def __init__(self, landmarks, gesture: str, palm_center, wrist, index_tip):
        self.landmarks   = landmarks
        self.gesture     = gesture            # string
        self.palm_center = palm_center        # (x, y) normalised 0-1
        self.wrist       = wrist
        self.index_tip   = index_tip


class HandDetector:
    """
    Thin wrapper around MediaPipe Hands.

    Usage
    -----
        detector = HandDetector(max_hands=1)
        while True:
            frame = cap.read()[1]
            hands = detector.process(frame)
            if hands:
                print(hands[0].gesture, hands[0].palm_center)
    """

    def __init__(
        self,
        max_hands:          int   = 1,
        detection_conf:     float = 0.7,
        tracking_conf:      float = 0.6,
    ):
        if not _MP_AVAILABLE:
            raise ImportError(
                "mediapipe is not installed. Run: pip install mediapipe"
            )
        self._mp_hands = mp.solutions.hands
        self._hands    = self._mp_hands.Hands(
            max_num_hands              = max_hands,
            min_detection_confidence   = detection_conf,
            min_tracking_confidence    = tracking_conf,
        )
        self._mp_draw = mp.solutions.drawing_utils
        self._mp_draw_styles = mp.solutions.drawing_styles

    # ─── Public ───────────────────────────────────────────────────────────────

    def process(self, frame_bgr: np.ndarray) -> list[HandInfo]:
        """
        Process a BGR frame, return list of HandInfo (one per detected hand).
        Returns empty list if no hands found.
        """
        import cv2
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        rgb.flags.writeable = True

        if not results.multi_hand_landmarks:
            return []

        out = []
        for lm_list in results.multi_hand_landmarks:
            lms     = lm_list.landmark
            gesture = self._classify(lms)
            palm_cx = sum(lms[i].x for i in [0,1,5,9,13,17]) / 6
            palm_cy = sum(lms[i].y for i in [0,1,5,9,13,17]) / 6
            out.append(HandInfo(
                landmarks   = lms,
                gesture     = gesture,
                palm_center = (palm_cx, palm_cy),
                wrist       = (lms[0].x, lms[0].y),
                index_tip   = (lms[8].x, lms[8].y),
            ))
        return out

    def draw_landmarks(self, frame: np.ndarray, hand_info: HandInfo) -> np.ndarray:
        """Draw MediaPipe skeleton onto frame (in-place)."""
        if not _MP_AVAILABLE:
            return frame
        import mediapipe as mp_inner
        # Reconstruct NormalizedLandmarkList for drawing
        # (We stored raw landmark list, so re-wrap it)
        # draw directly from the raw landmark sequence
        h, w = frame.shape[:2]
        for lm in hand_info.landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            import cv2
            cv2.circle(frame, (cx, cy), 4, (0, 220, 180), -1)
        return frame

    def close(self):
        self._hands.close()

    # ─── Gesture classifier ───────────────────────────────────────────────────

    @staticmethod
    def _classify(lms) -> str:
        """
        Rule-based classifier using tip-vs-pip y-coordinates.
        Lower y = higher on screen (normalised coords).
        A finger is "extended" if its tip is clearly above its PIP joint.
        """
        extended = []
        for tip_i, pip_i in zip(_TIPS, _PIPS):
            tip_y = lms[tip_i].y
            pip_y = lms[pip_i].y
            # Thumb: use x-axis comparison (it extends sideways)
            if tip_i == 4:
                extended.append(abs(lms[4].x - lms[2].x) > 0.04)
            else:
                extended.append(tip_y < pip_y - 0.02)

        thumb, index, middle, ring, pinky = extended

        # ── Rules ──────────────────────────────────────────────────────────────
        if all(extended):
            return "open_palm"
        if not any(extended):
            return "fist"
        if index and middle and not ring and not pinky:
            return "peace"
        if index and not middle and not ring and not pinky:
            return "point"
        return "none"


# ─── Null / mock detector (no camera / mediapipe) ────────────────────────────

class MockHandDetector:
    """
    Drop-in replacement when MediaPipe is unavailable.
    Cycles through gestures on a timer — useful for UI testing.
    """
    _CYCLE = ["none", "fist", "fist", "fist", "open_palm", "point", "none"]

    def __init__(self):
        self._frame = 0

    def process(self, frame_bgr: np.ndarray) -> list:
        self._frame += 1
        idx = (self._frame // 30) % len(self._CYCLE)
        gesture = self._CYCLE[idx]
        return [HandInfo(
            landmarks   = [],
            gesture     = gesture,
            palm_center = (0.5, 0.7),
            wrist       = (0.5, 0.85),
            index_tip   = (0.5, 0.45),
        )]

    def draw_landmarks(self, frame, hand_info):
        return frame

    def close(self): pass
