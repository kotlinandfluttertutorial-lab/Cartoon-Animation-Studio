"""
studio/dialogue/conversation_scene.py
Orchestrates a two-character conversation: audio generation, lip-sync, and
Blender rendering.

ConversationScene accepts a list of DialogueLine objects, calls
DialogueSequencer to populate them, then optionally invokes Blender to
render each line's viseme frames.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from studio.dialogue.dialogue_sequencer import DialogueLine, DialogueSequencer

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------
_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent  # Local_3D_Cartoon_Studio/
_DEFAULT_AARAV_BLEND = str(
    _PROJECT_DIR / "blender" / "assets" / "characters" / "aarav" / "aarav_stage4.blend"
)
_DEFAULT_AANYA_BLEND = str(
    _PROJECT_DIR / "blender" / "assets" / "characters" / "aanya" / "aanya_stage4.blend"
)
_DEFAULT_APPLY_LIPSYNC_SCRIPT = str(
    _PROJECT_DIR / "blender" / "scripts" / "apply_lipsync.py"
)


@dataclass
class ConversationResult:
    """Result of rendering a conversation scene."""
    lines: list[DialogueLine]
    rendered_frames: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True


class ConversationScene:
    """
    High-level orchestrator for two-character conversation rendering.

    Parameters
    ----------
    config : dict with keys:
        blender_exe         : path to blender.exe (required for rendering)
        apply_lipsync_script: path to apply_lipsync.py Blender script
        aarav_blend         : path to aarav_stage4.blend
        aanya_blend         : path to aanya_stage4.blend
        output_dir          : base output directory for rendered frames
        fps                 : frames per second (default 24)
        gap_frames          : silence gap between lines (default 12)
        piper_exe           : optional path to Piper TTS
        ffprobe_exe         : optional path to ffprobe
        output_audio_dir    : directory for generated audio
        output_lipsync_dir  : directory for generated lipsync data
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._blender: Optional[str] = config.get("blender_exe")
        self._apply_script: str = config.get(
            "apply_lipsync_script", _DEFAULT_APPLY_LIPSYNC_SCRIPT
        )
        self._blends: dict[str, str] = {
            "Aarav": config.get("aarav_blend", _DEFAULT_AARAV_BLEND),
            "Aanya": config.get("aanya_blend", _DEFAULT_AANYA_BLEND),
        }
        self._output_dir = Path(config.get("output_dir", str(_PROJECT_DIR / "output" / "stage4_3")))
        self._sequencer = DialogueSequencer(config)

    def _blend_for(self, character: str) -> str:
        return self._blends.get(character, self._blends["Aarav"])

    def _render_lipsync(
        self,
        line: DialogueLine,
        output_subdir: str,
    ) -> list[str]:
        """
        Invoke Blender to render lip-sync frames for a single line.

        Returns list of rendered PNG paths (may be empty on failure).
        """
        if not self._blender or not os.path.isfile(self._blender):
            return []
        if not line.lipsync_path or not os.path.isfile(line.lipsync_path):
            return []
        if not os.path.isfile(self._apply_script):
            return []

        blend = self._blend_for(line.character)
        if not os.path.isfile(blend):
            return []

        frame_dir = str(self._output_dir / output_subdir)
        Path(frame_dir).mkdir(parents=True, exist_ok=True)

        cmd = [
            self._blender,
            "--background",
            blend,
            "--python",
            self._apply_script,
            "--",
            line.lipsync_path,
            line.character,
            frame_dir,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                return sorted(
                    str(p)
                    for p in Path(frame_dir).glob("frame_*.png")
                )
        except Exception:
            pass

        return []

    def render_conversation(
        self,
        lines: list[DialogueLine],
        render: bool = False,
    ) -> ConversationResult:
        """
        Process and optionally render a conversation.

        Parameters
        ----------
        lines  : list of DialogueLine objects
        render : if True, calls Blender to render lip-sync frames

        Returns
        -------
        ConversationResult with populated lines and rendered frame paths.
        """
        # Sequence: assign frames, generate audio + lipsync
        sequenced = self._sequencer.sequence_dialogue(lines)

        result = ConversationResult(lines=sequenced)

        if render:
            for idx, line in enumerate(sequenced):
                subdir = f"line_{idx + 1:02d}_{line.character.lower()}"
                frames = self._render_lipsync(line, subdir)
                result.rendered_frames.extend(frames)
                if not frames:
                    result.errors.append(
                        f"Line {idx + 1} ({line.character}): no frames rendered"
                    )

            result.success = len(result.errors) == 0

        return result
