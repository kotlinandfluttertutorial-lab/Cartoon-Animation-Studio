"""Stage 13 camera and Workbench lighting presets for the approved garden."""

from math import isfinite
from typing import NamedTuple


class CameraPreset(NamedTuple):
    position: tuple[float, float, float]
    target: tuple[float, float, float]
    lens: float
    subjects: tuple[str, ...] = ()


# The garden performance lane crosses (0, 0). Positive Y faces the cast.
CAMERAS = {
    "establishing": CameraPreset((4.4, 9.6, 4.4), (0, -2.0, .9), 29),
    "full_body": CameraPreset((.85, 4.8, 1.65), (0, 0, .88), 40, ("Aarav",)),
    "medium_two": CameraPreset((.35, 4.3, 1.66), (0, 0, 1.15), 46, ("Aarav", "Aanya")),
    "medium_single": CameraPreset((-.32, 3.65, 1.62), (-.62, 0, 1.17), 49, ("Aarav",)),
    "medium_aanya": CameraPreset((.32, 3.65, 1.62), (.62, 0, 1.17), 49, ("Aanya",)),
    "close_up": CameraPreset((.89, 2.55, 1.54), (.62, 0, 1.43), 54, ("Aanya",)),
    "extreme_close_up": CameraPreset((-.49, 2.03, 1.49), (-.62, 0, 1.40), 54, ("Aarav",)),
    "over_shoulder": CameraPreset((-1.53, 1.46, 1.76), (.40, 0, 1.38), 39, ("Aarav", "Aanya")),
    "conversation": CameraPreset((-.48, 4.1, 1.57), (0, 0, 1.24), 44, ("Aarav", "Aanya")),
    "walking_follow": CameraPreset((.7, 5.25, 1.64), (0, -.4, .89), 42, ("Aarav", "Aanya")),
    "side_tracking": CameraPreset((-2.85, 4.45, 1.55), (0, 0, .88), 39, ("Aarav", "Aanya")),
}

# Studio light, exposure, shadow intensity, cavity valley, background RGB.
LIGHTS = {
    "daylight": ("paint.sl", .48, .24, .48, (.25, .55, .76)),
    "morning": ("outdoor.sl", .53, .27, .49, (.46, .66, .74)),
    "afternoon": ("paint.sl", .35, .31, .64, (.35, .59, .72)),
    "golden_hour": ("paint.sl", .27, .39, .62, (.78, .54, .34)),
    "close_up": ("paint.sl", .50, .17, .34, (.33, .54, .67)),
    "conversation": ("paint.sl", .40, .23, .43, (.29, .55, .72)),
}

# Offsets from the preset position and target at the end of a move.
MOVEMENTS = {
    "static": ((0, 0, 0), (0, 0, 0)),
    "push_in": ((0, -.48, -.05), (0, 0, 0)),
    "pull_back": ((0, .60, .09), (0, 0, 0)),
    "pan": ((0, 0, 0), (.45, 0, 0)),
    "tilt": ((0, 0, 0), (0, 0, .30)),
    "track": ((.54, 0, 0), (.54, 0, 0)),
    "follow": ((0, .57, 0), (0, .57, 0)),
    "reveal": ((.58, .48, .08), (.36, 0, 0)),
    "reposition": ((-.35, .18, .10), (0, 0, .04)),
}


def interpolate(start, end, progress):
    """Ease a move to rest at both endpoints."""
    if not isfinite(progress) or not 0 <= progress <= 1:
        raise ValueError("Camera progress must be finite and between 0 and 1.")
    weight = progress * progress * (3 - 2 * progress)
    return tuple(a + (b - a) * weight for a, b in zip(start, end, strict=True))


def camera_pose(preset, movement, progress, *, end_position=None, end_target=None):
    camera = CAMERAS[preset]
    offset, aim_offset = MOVEMENTS[movement]
    if end_position is None:
        end_position = tuple(a + b for a, b in zip(camera.position, offset))
    if end_target is None:
        end_target = tuple(a + b for a, b in zip(camera.target, aim_offset))
    return (interpolate(camera.position, end_position, progress),
            interpolate(camera.target, end_target, progress))
