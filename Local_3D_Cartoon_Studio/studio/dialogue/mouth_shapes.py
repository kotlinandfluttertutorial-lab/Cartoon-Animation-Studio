"""
studio/dialogue/mouth_shapes.py
Per-viseme mouth transform definitions for Aarav and Aanya cartoon characters.

Characters have separate mouth mesh objects (not shape keys):
  Aarav_Mouth / Aanya_Mouth

Each viseme is a dict describing how to adjust the mouth object's scale and
Z position relative to its rest pose.  Transforms are applied by
blender/scripts/apply_lipsync.py inside Blender.
"""
from __future__ import annotations

from typing import NamedTuple, TypedDict

# ---------------------------------------------------------------------------
# Mouth transform spec
# ---------------------------------------------------------------------------

class MouthTransform(TypedDict):
    scale: tuple[float, float, float]  # (X, Y, Z) scale multipliers
    z_offset: float                     # local Z delta from rest position


VISEME_MOUTH_TRANSFORMS: dict[str, MouthTransform] = {
    # Closed / resting position
    "REST": {"scale": (1.0, 1.0, 1.0), "z_offset":  0.0},
    # Lips pressed together — M, B, P
    "MBP":  {"scale": (0.4, 1.0, 0.3), "z_offset":  0.0},
    # Upper teeth on lower lip — F, V
    "FV":   {"scale": (0.6, 1.0, 0.4), "z_offset":  0.0},
    # Tongue tip sounds — T, D, N, L, S, Z
    "TD":   {"scale": (0.8, 1.0, 0.6), "z_offset": -0.005},
    # Rounded lips — W, R, OW, UW
    "WQ":   {"scale": (0.6, 1.0, 0.8), "z_offset": -0.005},
    # Open jaw — AA, AH, AO, AE
    "OPEN": {"scale": (1.3, 1.0, 1.4), "z_offset": -0.015},
    # Spread lips / smile — EH, IH, IY, AY
    "EI":   {"scale": (1.4, 1.0, 0.7), "z_offset":  0.0},
}

# Valid viseme names (used for validation)
VALID_VISEMES: frozenset[str] = frozenset(VISEME_MOUTH_TRANSFORMS.keys())

# ---------------------------------------------------------------------------
# Eye blink timing constants
# ---------------------------------------------------------------------------
BLINK_INTERVAL_FRAMES: int = 96   # auto-blink every 96 frames (~4 s at 24 fps)
BLINK_DURATION_FRAMES: int = 3    # blink lasts 3 frames


class MouthShapes:
    """
    Helper class providing access to viseme mouth transforms and blink constants.

    Wraps the module-level constants for use as a class attribute where
    callers prefer OO-style access.
    """

    transforms: dict[str, MouthTransform] = VISEME_MOUTH_TRANSFORMS
    valid_visemes: frozenset[str] = VALID_VISEMES
    blink_interval_frames: int = BLINK_INTERVAL_FRAMES
    blink_duration_frames: int = BLINK_DURATION_FRAMES

    @classmethod
    def get_transform(cls, viseme: str) -> MouthTransform:
        """Return the transform dict for *viseme*, defaulting to REST."""
        return cls.transforms.get(viseme, cls.transforms["REST"])

    @classmethod
    def is_valid(cls, viseme: str) -> bool:
        """Return True if *viseme* is a recognised viseme name."""
        return viseme in cls.valid_visemes
