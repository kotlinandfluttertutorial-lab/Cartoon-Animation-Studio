"""
studio/dialogue/lipsync_generator.py
Generates, saves, and loads lip-sync data for cartoon characters.

LipsyncData maps frame numbers to viseme names and also encodes automatic
blink events at regular intervals.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from studio.dialogue.phoneme_mapper import text_to_viseme_sequence
from studio.dialogue.mouth_shapes import (
    VALID_VISEMES,
    BLINK_INTERVAL_FRAMES,
    BLINK_DURATION_FRAMES,
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LipsyncData:
    """
    Container for per-frame lip-sync information.

    Attributes
    ----------
    fps         : frames-per-second the data was generated at
    total_frames: total length of the clip in frames
    character   : character name ('Aarav' or 'Aanya')
    frames      : {frame_number: viseme_name}  — sparse; unlisted frames are REST
    blink_frames: list of frame numbers where a blink starts
    text        : original dialogue text (informational)
    """
    fps: int
    total_frames: int
    character: str
    frames: dict[int, str] = field(default_factory=dict)
    blink_frames: list[int] = field(default_factory=list)
    text: str = ""

    def __post_init__(self) -> None:
        # Coerce string keys from JSON to int (json.load always produces str keys)
        if self.frames and isinstance(next(iter(self.frames)), str):
            self.frames = {int(k): v for k, v in self.frames.items()}

    def get_viseme(self, frame: int) -> str:
        """Return the viseme for *frame*, defaulting to REST."""
        return self.frames.get(frame, "REST")


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class LipsyncGenerator:
    """Stateless factory — all logic is in module-level functions."""

    @staticmethod
    def generate(
        text: str,
        character: str,
        duration_s: float,
        fps: int = 24,
        include_blinks: bool = True,
    ) -> LipsyncData:
        return generate_lipsync(
            text=text,
            character=character,
            duration_s=duration_s,
            fps=fps,
            include_blinks=include_blinks,
        )


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def generate_lipsync(
    text: str,
    character: str,
    duration_s: float,
    fps: int = 24,
    include_blinks: bool = True,
) -> LipsyncData:
    """
    Generate a LipsyncData object for *text* spoken by *character*.

    Distributes visemes evenly across *duration_s*, adds automatic blink
    events at BLINK_INTERVAL_FRAMES intervals, and ensures frame 1 is REST.

    Parameters
    ----------
    text          : English dialogue text
    character     : 'Aarav' or 'Aanya'
    duration_s    : speech duration in seconds (must be > 0)
    fps           : frames per second (default 24)
    include_blinks: whether to add blink events (default True)

    Returns
    -------
    LipsyncData with frames dict and blink_frames list.
    """
    if duration_s <= 0:
        duration_s = 1.0

    total_frames = max(1, int(duration_s * fps))

    # Build frame→viseme mapping from text
    viseme_sequence = text_to_viseme_sequence(text, duration_s, fps)
    frames: dict[int, str] = {}
    for frame_num, viseme in viseme_sequence:
        frames[frame_num] = viseme

    # Ensure frame 1 is always REST (pre-speech silence)
    frames[1] = "REST"

    # Compute blink frames
    blink_frames: list[int] = []
    if include_blinks:
        f = BLINK_INTERVAL_FRAMES
        while f <= total_frames:
            blink_frames.append(f)
            f += BLINK_INTERVAL_FRAMES

    return LipsyncData(
        fps=fps,
        total_frames=total_frames,
        character=character,
        frames=frames,
        blink_frames=blink_frames,
        text=text,
    )


def save_lipsync(data: LipsyncData, path: str) -> None:
    """
    Serialise *data* to a JSON file at *path*.

    Creates parent directories automatically.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fps": data.fps,
        "total_frames": data.total_frames,
        "character": data.character,
        "text": data.text,
        # JSON object keys must be strings; we convert ints
        "frames": {str(k): v for k, v in sorted(data.frames.items())},
        "blink_frames": sorted(data.blink_frames),
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_lipsync(path: str) -> LipsyncData:
    """
    Load a LipsyncData from a JSON file at *path*.

    Returns a fully hydrated LipsyncData with int-keyed frames dict.

    Raises
    ------
    FileNotFoundError if path does not exist.
    ValueError if the file is malformed.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Lipsync file not found: {path}")

    raw = json.loads(p.read_text(encoding="utf-8"))
    try:
        return LipsyncData(
            fps=int(raw["fps"]),
            total_frames=int(raw["total_frames"]),
            character=str(raw["character"]),
            frames={int(k): str(v) for k, v in raw.get("frames", {}).items()},
            blink_frames=[int(b) for b in raw.get("blink_frames", [])],
            text=str(raw.get("text", "")),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed lipsync JSON in {path}: {exc}") from exc
