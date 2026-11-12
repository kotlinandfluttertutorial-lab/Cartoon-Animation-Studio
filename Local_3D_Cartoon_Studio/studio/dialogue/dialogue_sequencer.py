"""
studio/dialogue/dialogue_sequencer.py
Dialogue sequencing: assigns frame timings, generates audio (Piper TTS) and
lip-sync data for each line in a scene.

Piper TTS is called via subprocess without shell=True.  Audio duration is
measured via ffprobe if available, otherwise estimated from text length.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from studio.dialogue.lipsync_generator import LipsyncData, generate_lipsync, save_lipsync


# ---------------------------------------------------------------------------
# Piper voice model mapping
# ---------------------------------------------------------------------------
# Default voice models bundled with Piper (en_US).  Can be overridden via
# the config dict passed to DialogueSequencer.__init__().
_DEFAULT_VOICE_MODELS: dict[str, str] = {
    "Aarav": "en_US-ryan-medium",
    "Aanya": "en_US-lessac-medium",
}

# Estimated speaking rate (phonemes per second) for duration estimation
# when ffprobe is unavailable.
_CHARS_PER_SECOND: float = 12.0
_MIN_DURATION_S: float = 0.5


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class DialogueLine:
    """
    A single line of dialogue spoken by one character.

    Attributes
    ----------
    character    : 'Aarav' or 'Aanya'
    text         : English dialogue text
    emotion      : expression to apply (e.g. 'happy', 'neutral')
    start_frame  : frame at which this line begins in the scene
    audio_path   : path to generated WAV file (populated by sequencer)
    lipsync_path : path to generated lipsync JSON (populated by sequencer)
    """
    character: str
    text: str
    emotion: str = "neutral"
    start_frame: int = 1
    audio_path: str = ""
    lipsync_path: str = ""


# ---------------------------------------------------------------------------
# Sequencer
# ---------------------------------------------------------------------------

class DialogueSequencer:
    """
    Coordinates audio generation and lip-sync for a list of DialogueLines.

    Parameters
    ----------
    config : dict with optional keys:
        piper_exe        : path to piper executable (default: auto-detect)
        voice_models     : {character: model_name} mapping
        fps              : frames per second (default 24)
        gap_frames       : silence gap between lines (default 12)
        ffprobe_exe      : path to ffprobe for duration measurement
        output_audio_dir : directory for generated WAV files
        output_lipsync_dir: directory for generated JSON files
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._fps: int = int(config.get("fps", 24))
        self._gap_frames: int = int(config.get("gap_frames", 12))
        self._piper_exe: Optional[str] = config.get("piper_exe") or self._find_piper()
        self._voice_models: dict[str, str] = {
            **_DEFAULT_VOICE_MODELS,
            **config.get("voice_models", {}),
        }
        self._ffprobe: Optional[str] = config.get("ffprobe_exe") or self._find_ffprobe()
        self._audio_dir = Path(config.get("output_audio_dir", tempfile.gettempdir()))
        self._lipsync_dir = Path(config.get("output_lipsync_dir", tempfile.gettempdir()))
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        self._lipsync_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_piper() -> Optional[str]:
        """Search common locations for the piper executable."""
        import shutil
        found = shutil.which("piper")
        if found:
            return found
        candidates = [
            r"C:\Program Files\piper\piper.exe",
            r"C:\piper\piper.exe",
            r"P:\AI\Cartoon-Animation-Studio\tools\piper\piper.exe",
            os.path.expanduser(r"~\AppData\Local\piper\piper.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    @staticmethod
    def _find_ffprobe() -> Optional[str]:
        """Search for ffprobe executable."""
        import shutil
        found = shutil.which("ffprobe")
        if found:
            return found
        # WinGet default location
        winget_base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
        if winget_base.exists():
            for candidate in winget_base.rglob("ffprobe.exe"):
                return str(candidate)
        return None

    def _estimate_duration(self, text: str) -> float:
        """Estimate speech duration from text length (fallback)."""
        char_count = len(text.strip())
        return max(_MIN_DURATION_S, char_count / _CHARS_PER_SECOND)

    def _measure_audio_duration(self, wav_path: str) -> float:
        """Measure audio duration with ffprobe; falls back to estimation."""
        if not self._ffprobe or not os.path.isfile(wav_path):
            return _MIN_DURATION_S

        cmd = [
            self._ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            wav_path,
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                duration = float(data["format"]["duration"])
                return max(_MIN_DURATION_S, duration)
        except Exception:
            pass
        return _MIN_DURATION_S

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_audio(self, text: str, character: str, output_path: str) -> float:
        """
        Run Piper TTS to synthesise *text* as a WAV file at *output_path*.

        Returns the audio duration in seconds.  If Piper is unavailable,
        creates an empty placeholder file and returns an estimated duration.

        Parameters
        ----------
        text        : dialogue text
        character   : 'Aarav' or 'Aanya'
        output_path : where to write the WAV

        Returns
        -------
        float — duration in seconds
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if not self._piper_exe or not os.path.isfile(self._piper_exe):
            # Piper not installed — create placeholder and estimate duration
            out.write_bytes(b"")  # zero-byte placeholder
            return self._estimate_duration(text)

        model = self._voice_models.get(character, "en_US-ryan-medium")
        cmd = [
            self._piper_exe,
            "--model", model,
            "--output_file", str(out),
        ]

        try:
            result = subprocess.run(
                cmd,
                input=text,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0 and out.exists() and out.stat().st_size > 0:
                return self._measure_audio_duration(str(out))
        except Exception:
            pass

        # Fallback: placeholder + estimate
        if not out.exists():
            out.write_bytes(b"")
        return self._estimate_duration(text)

    def generate_lipsync(
        self,
        text: str,
        character: str,
        duration_s: float,
        output_path: str,
    ) -> LipsyncData:
        """
        Generate and save a lipsync JSON file.

        Parameters
        ----------
        text        : dialogue text
        character   : 'Aarav' or 'Aanya'
        duration_s  : speech duration in seconds
        output_path : where to write the JSON

        Returns
        -------
        LipsyncData
        """
        data = generate_lipsync(
            text=text,
            character=character,
            duration_s=duration_s,
            fps=self._fps,
            include_blinks=True,
        )
        save_lipsync(data, output_path)
        return data

    def sequence_dialogue(self, lines: list[DialogueLine]) -> list[DialogueLine]:
        """
        Process a list of DialogueLines: assign start_frames, generate audio
        and lipsync data for each line.

        Lines are processed in order.  Each line starts immediately after the
        previous one ends (plus a gap of self._gap_frames frames).

        Parameters
        ----------
        lines : list of DialogueLine objects (modified in-place)

        Returns
        -------
        The same list with start_frame, audio_path, and lipsync_path populated.
        """
        current_frame = 1

        for idx, line in enumerate(lines):
            line.start_frame = current_frame

            # --- Audio ---
            audio_name = f"{line.character.lower()}_{idx + 1:02d}.wav"
            audio_path = str(self._audio_dir / audio_name)
            duration_s = self.generate_audio(line.text, line.character, audio_path)
            line.audio_path = audio_path

            # --- Lipsync ---
            lipsync_name = f"{line.character.lower()}_{idx + 1:02d}_lipsync.json"
            lipsync_path = str(self._lipsync_dir / lipsync_name)
            self.generate_lipsync(line.text, line.character, duration_s, lipsync_path)
            line.lipsync_path = lipsync_path

            # Advance frame counter
            line_frames = max(1, int(duration_s * self._fps))
            current_frame += line_frames + self._gap_frames

        return lines
