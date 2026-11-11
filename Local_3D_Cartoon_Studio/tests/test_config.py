"""Unit tests for config_manager.py."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.config_manager import ConfigManager, ConfigurationError
from studio.schemas import AppSettings, RenderProfile


VALID_SETTINGS = {
    "blender_executable": r"p:\AI\Cartoon-Animation-Studio\tools\blender-4.4.3-windows-x64\blender.exe",
    "ffmpeg_executable": r"C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe",
    "ffprobe_executable": r"C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "qwen3:4b",
    "output_dir": r"p:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\output",
    "projects_dir": r"p:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\projects",
    "logs_dir": r"p:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\logs",
    "process_timeout_seconds": 3600,
    "active_render_profile": "PREVIEW",
}

VALID_PROFILES = {
    "PREVIEW": {
        "width": 640,
        "height": 360,
        "fps": 12,
        "engine": "BLENDER_WORKBENCH",
        "image_format": "PNG",
        "shading": "SOLID",
        "enabled": True,
        "ffmpeg_output": False,
    },
    "EXPERIMENTAL_720P": {
        "width": 1280,
        "height": 720,
        "fps": 12,
        "engine": "BLENDER_WORKBENCH",
        "image_format": "PNG",
        "shading": "SOLID",
        "enabled": False,
        "ffmpeg_output": False,
    },
}


def _write_config_files(config_dir: Path, settings: dict, profiles: dict) -> None:
    (config_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    (config_dir / "render_profiles.json").write_text(json.dumps(profiles), encoding="utf-8")


class TestLoadValidSettings(unittest.TestCase):
    def test_load_valid_settings(self):
        """All fields present after loading a valid settings.json."""
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            with patch("pathlib.Path.exists", return_value=True):
                _write_config_files(config_dir, VALID_SETTINGS, VALID_PROFILES)
                mgr = ConfigManager(config_dir)
                mgr.load()

            self.assertEqual(mgr.settings.active_render_profile, "PREVIEW")
            self.assertEqual(mgr.settings.process_timeout_seconds, 3600)
            self.assertIn("PREVIEW", mgr.profiles)


class TestInvalidBlenderPath(unittest.TestCase):
    def test_invalid_blender_path(self):
        """settings.json with nonexistent blender path raises ConfigurationError."""
        bad_settings = {**VALID_SETTINGS, "blender_executable": r"C:\nonexistent\blender.exe"}
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            # Only ffmpeg/ffprobe paths exist; blender does not
            def mock_exists(self_path):
                p = str(self_path)
                return "nonexistent" not in p

            _write_config_files(config_dir, bad_settings, VALID_PROFILES)
            mgr = ConfigManager(config_dir)
            # Patch Path.exists so the config files are found but blender path is not
            original_exists = Path.exists

            def patched_exists(self_path):
                if str(self_path) == str(config_dir / "settings.json"):
                    return True
                if str(self_path) == str(config_dir / "render_profiles.json"):
                    return True
                if "nonexistent" in str(self_path):
                    return False
                return original_exists(self_path)

            with patch.object(Path, "exists", patched_exists):
                with self.assertRaises((ConfigurationError, ValueError)):
                    mgr.load()


class TestInvalidFFmpegPath(unittest.TestCase):
    def test_invalid_ffmpeg_path(self):
        """settings.json with nonexistent ffmpeg path raises ConfigurationError."""
        bad_settings = {**VALID_SETTINGS, "ffmpeg_executable": r"C:\nonexistent\ffmpeg.exe"}
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            _write_config_files(config_dir, bad_settings, VALID_PROFILES)
            mgr = ConfigManager(config_dir)
            original_exists = Path.exists

            def patched_exists(self_path):
                if str(self_path) in (
                    str(config_dir / "settings.json"),
                    str(config_dir / "render_profiles.json"),
                ):
                    return True
                if "nonexistent" in str(self_path):
                    return False
                return original_exists(self_path)

            with patch.object(Path, "exists", patched_exists):
                with self.assertRaises((ConfigurationError, ValueError)):
                    mgr.load()


class TestGetProfilePreview(unittest.TestCase):
    def test_get_profile_preview(self):
        """get_profile('PREVIEW') returns RenderProfile with width=640."""
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            with patch("pathlib.Path.exists", return_value=True):
                _write_config_files(config_dir, VALID_SETTINGS, VALID_PROFILES)
                mgr = ConfigManager(config_dir)
                mgr.load()
                profile = mgr.get_profile("PREVIEW")

            self.assertIsInstance(profile, RenderProfile)
            self.assertEqual(profile.width, 640)


class TestGetProfileDisabled(unittest.TestCase):
    def test_get_profile_disabled(self):
        """get_profile('EXPERIMENTAL_720P') raises ValueError because it is disabled."""
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            with patch("pathlib.Path.exists", return_value=True):
                _write_config_files(config_dir, VALID_SETTINGS, VALID_PROFILES)
                mgr = ConfigManager(config_dir)
                mgr.load()

            with self.assertRaises(ValueError):
                mgr.get_profile("EXPERIMENTAL_720P")


class TestBackupCreatedOnSave(unittest.TestCase):
    def test_backup_created_on_save(self):
        """Calling save_settings creates a file in config/backups/."""
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            with patch("pathlib.Path.exists", return_value=True):
                _write_config_files(config_dir, VALID_SETTINGS, VALID_PROFILES)
                mgr = ConfigManager(config_dir)
                mgr.load()
                new_settings = mgr.settings.model_copy()
                mgr.save_settings(new_settings)

            backups = list((config_dir / "backups").glob("settings_*.json"))
            self.assertGreater(len(backups), 0, "No backup file created")


class TestWindowsPathHandling(unittest.TestCase):
    def test_windows_path_handling(self):
        """Path with backslashes round-trips correctly through AppSettings."""
        with patch("pathlib.Path.exists", return_value=True):
            settings = AppSettings(**VALID_SETTINGS)
            # The path should be preserved (or normalised but still valid)
            self.assertIn("blender.exe", settings.blender_executable.lower())
            self.assertIn("ffmpeg.exe", settings.ffmpeg_executable.lower())


if __name__ == "__main__":
    unittest.main()
