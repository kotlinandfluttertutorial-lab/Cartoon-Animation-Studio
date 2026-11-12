"""
studio/dialogue/expression_library.py
Facial expression definitions for Aarav and Aanya cartoon characters.

Each expression is a dict mapping object suffixes (without character prefix)
to transform deltas:
    {"z_offset": float}  — vertical shift of the object
    {"scale": (x, y, z)} — scale factors applied to the object

The apply_expression() function is designed to work in two contexts:
  1. Inside Blender (bpy available): directly modifies bpy.data.objects
  2. Pure-Python test mode (bpy not available): returns saved state dict
     and applies/restores using stored object stubs (for unit testing).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

# ---------------------------------------------------------------------------
# Expression definitions
# ---------------------------------------------------------------------------

# Maps expression name → {object_suffix: {transform_key: value}}
# Object name = char_prefix + "_" + suffix  (e.g. "Aarav_Mouth")
EXPRESSIONS: dict[str, dict[str, dict[str, Any]]] = {
    "neutral": {},  # no changes from rest pose

    "happy": {
        "Eyebrow_L": {"z_offset": +0.025},
        "Eyebrow_R": {"z_offset": +0.025},
        "Mouth":     {"scale": (1.2, 1.0, 0.7)},
    },

    "surprised": {
        "Eyebrow_L": {"z_offset": +0.04},
        "Eyebrow_R": {"z_offset": +0.04},
        "Eye_L":     {"scale": (1.0, 1.0, 1.3)},
        "Eye_R":     {"scale": (1.0, 1.0, 1.3)},
        "Mouth":     {"scale": (1.3, 1.0, 1.3)},
    },

    "sad": {
        "Eyebrow_L": {"z_offset": -0.02},
        "Eyebrow_R": {"z_offset": -0.02},
        "Mouth":     {"scale": (0.9, 1.0, 0.8)},
    },

    "thinking": {
        "Eyebrow_R": {"z_offset": +0.02},
    },

    "excited": {
        "Eyebrow_L": {"z_offset": +0.03},
        "Eyebrow_R": {"z_offset": +0.03},
        "Mouth":     {"scale": (1.3, 1.0, 1.1)},
    },
}

VALID_EMOTIONS: frozenset[str] = frozenset(EXPRESSIONS.keys())


class ExpressionLibrary:
    """
    Class-based access to expression definitions.

    Pure-Python class — does NOT import bpy.  Blender-specific logic lives
    in blender/scripts/apply_expression.py.
    """

    expressions: dict[str, dict[str, dict[str, Any]]] = EXPRESSIONS
    valid_emotions: frozenset[str] = VALID_EMOTIONS

    @classmethod
    def get(cls, emotion: str) -> dict[str, dict[str, Any]]:
        """Return expression transforms for *emotion*, defaulting to neutral."""
        return cls.expressions.get(emotion, {})

    @classmethod
    def is_valid(cls, emotion: str) -> bool:
        """Return True if *emotion* is a recognised expression name."""
        return emotion in cls.valid_emotions

    @classmethod
    def all_emotions(cls) -> list[str]:
        """Return sorted list of all emotion names."""
        return sorted(cls.expressions.keys())


# ---------------------------------------------------------------------------
# Pure-Python apply/restore (no bpy dependency)
# ---------------------------------------------------------------------------
# These functions work with a simple object-stub protocol so they can be
# exercised in unit tests without Blender.  When bpy IS available (inside a
# Blender subprocess) the blender scripts call bpy directly.


def apply_expression(char_prefix: str, emotion: str) -> dict[str, Any]:
    """
    Apply an expression to character objects.

    In pure-Python mode (bpy not importable) this function attempts to look
    up bpy.data.objects; if bpy is unavailable it returns a stub saved-state
    dict that describes what WOULD be applied.  This allows unit tests to
    exercise the function without Blender.

    Parameters
    ----------
    char_prefix : 'Aarav' or 'Aanya'
    emotion     : expression name (e.g. 'happy')

    Returns
    -------
    dict  — {obj_name: {original_location_z, original_scale}} for use with
            restore_expression()
    """
    transforms = EXPRESSIONS.get(emotion, {})
    saved: dict[str, Any] = {}

    try:
        import bpy  # noqa: PLC0415 — intentional late import
        _apply_expression_bpy(char_prefix, emotion, transforms, saved)
    except ImportError:
        # Pure-Python stub: record what would be applied
        for suffix, tx in transforms.items():
            obj_name = f"{char_prefix}_{suffix}"
            saved[obj_name] = {
                "original_z": 0.0,
                "original_scale": (1.0, 1.0, 1.0),
                "applied": tx,
            }

    return saved


def restore_expression(saved: dict[str, Any]) -> None:
    """
    Restore objects to their pre-expression state.

    Parameters
    ----------
    saved : dict returned by apply_expression()
    """
    try:
        import bpy  # noqa: PLC0415
        _restore_expression_bpy(saved)
    except ImportError:
        # Pure-Python stub: nothing to restore
        pass


def _apply_expression_bpy(
    char_prefix: str,
    emotion: str,
    transforms: dict[str, dict[str, Any]],
    saved: dict[str, Any],
) -> None:
    """Apply expression transforms using bpy (called only inside Blender)."""
    import bpy  # noqa: PLC0415

    for suffix, tx in transforms.items():
        obj_name = f"{char_prefix}_{suffix}"
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            continue

        # Save originals
        saved[obj_name] = {
            "original_z":     float(obj.location.z),
            "original_scale": tuple(obj.scale),
        }

        # Apply z_offset
        if "z_offset" in tx:
            obj.location.z += tx["z_offset"]

        # Apply scale
        if "scale" in tx:
            sx, sy, sz = tx["scale"]
            obj.scale.x *= sx
            obj.scale.y *= sy
            obj.scale.z *= sz


def _restore_expression_bpy(saved: dict[str, Any]) -> None:
    """Restore objects from saved state using bpy (called only inside Blender)."""
    import bpy  # noqa: PLC0415

    for obj_name, state in saved.items():
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            continue
        if "original_z" in state:
            obj.location.z = state["original_z"]
        if "original_scale" in state:
            sx, sy, sz = state["original_scale"]
            obj.scale.x = sx
            obj.scale.y = sy
            obj.scale.z = sz
