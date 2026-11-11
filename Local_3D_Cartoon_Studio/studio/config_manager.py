"""Configuration manager for the Local 3D Cartoon Animation Studio."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from studio.schemas import AppSettings, RenderProfile


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""


class ConfigManager:
    """Loads, validates, and saves studio configuration."""

    def __init__(self, config_dir: str | Path) -> None:
        self._config_dir = Path(config_dir)
        self._settings_path = self._config_dir / "settings.json"
        self._profiles_path = self._config_dir / "render_profiles.json"
        self._backups_dir = self._config_dir / "backups"
        self._settings: Optional[AppSettings] = None
        self._profiles: dict[str, RenderProfile] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def settings(self) -> AppSettings:
        if self._settings is None:
            raise ConfigurationError("Configuration not loaded. Call load() first.")
        return self._settings

    @property
    def profiles(self) -> dict[str, RenderProfile]:
        return dict(self._profiles)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load settings.json and render_profiles.json and validate all paths."""
        if not self._settings_path.exists():
            raise ConfigurationError(f"settings.json not found at: {self._settings_path}")
        if not self._profiles_path.exists():
            raise ConfigurationError(
                f"render_profiles.json not found at: {self._profiles_path}"
            )

        with open(self._settings_path, "r", encoding="utf-8") as f:
            raw_settings = json.load(f)

        # Validate paths exist before constructing AppSettings
        for key in ("blender_executable", "ffmpeg_executable", "ffprobe_executable"):
            path_val = raw_settings.get(key, "")
            if path_val and not Path(path_val).exists():
                raise ConfigurationError(
                    f"Executable path not found for '{key}': {path_val}"
                )

        try:
            self._settings = AppSettings(**raw_settings)
        except Exception as exc:
            raise ConfigurationError(f"Invalid settings.json: {exc}") from exc

        with open(self._profiles_path, "r", encoding="utf-8") as f:
            raw_profiles = json.load(f)

        self._profiles = {}
        for name, data in raw_profiles.items():
            try:
                self._profiles[name] = RenderProfile(**data)
            except Exception as exc:
                raise ConfigurationError(
                    f"Invalid render profile '{name}': {exc}"
                ) from exc

    def save_settings(self, new_settings: AppSettings) -> None:
        """Save new settings, creating a timestamped backup first."""
        self._backups_dir.mkdir(parents=True, exist_ok=True)

        if self._settings_path.exists():
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            backup_path = self._backups_dir / f"settings_{ts}.json"
            shutil.copy2(self._settings_path, backup_path)

        data = new_settings.model_dump()
        with open(self._settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        self._settings = new_settings

    def get_profile(self, name: str) -> RenderProfile:
        """Return a named render profile.

        Raises ValueError if the profile is not found or is disabled.
        """
        if name not in self._profiles:
            available = ", ".join(self._profiles.keys())
            raise ValueError(
                f"Render profile '{name}' not found. Available: {available}"
            )
        profile = self._profiles[name]
        if not profile.enabled:
            raise ValueError(
                f"Render profile '{name}' is disabled. Enable it in render_profiles.json first."
            )
        return profile

    def detect_executables(self) -> dict[str, str | None]:
        """Search common Windows locations for blender.exe and ffmpeg.exe.

        Returns a dict with keys 'blender' and 'ffmpeg', values are paths or None.
        """
        results: dict[str, str | None] = {"blender": None, "ffmpeg": None}

        local_app_data = os.environ.get("LOCALAPPDATA", "")

        blender_search_paths = [
            r"C:\Program Files\Blender Foundation",
            os.path.join(local_app_data, "Programs"),
            # WinGet / portable installs under common drives
            r"C:\Program Files\Blender Foundation\Blender 4.4",
            r"C:\Program Files\Blender Foundation\Blender 4.3",
            r"C:\Program Files\Blender Foundation\Blender 4.2",
            r"D:\Blender",
            r"E:\Blender",
            r"p:\AI\Cartoon-Animation-Studio\tools",
        ]

        ffmpeg_search_paths = [
            os.path.join(local_app_data, "Microsoft", "WinGet", "Packages"),
            r"C:\Program Files\ffmpeg\bin",
            r"C:\ffmpeg\bin",
            r"D:\ffmpeg\bin",
        ]

        # Blender — try PATH first
        blender_in_path = shutil.which("blender")
        if blender_in_path:
            results["blender"] = blender_in_path
        else:
            for search_dir in blender_search_paths:
                p = Path(search_dir)
                if p.exists():
                    # Walk one level deep for portability
                    for candidate in p.rglob("blender.exe"):
                        results["blender"] = str(candidate)
                        break
                if results["blender"]:
                    break

        # FFmpeg — try PATH first
        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path:
            results["ffmpeg"] = ffmpeg_in_path
        else:
            for search_dir in ffmpeg_search_paths:
                p = Path(search_dir)
                if p.exists():
                    for candidate in p.rglob("ffmpeg.exe"):
                        results["ffmpeg"] = str(candidate)
                        break
                if results["ffmpeg"]:
                    break

        return results
