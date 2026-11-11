"""Unit tests for blender_runner.py."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.blender_runner import BlenderRunner, BlenderResult


FAKE_BLENDER = r"C:\fake\blender.exe"


def _make_runner() -> BlenderRunner:
    return BlenderRunner(blender_exe=FAKE_BLENDER, timeout=30)


def _mock_popen(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    """Return a Popen mock that communicate() resolves to (stdout, stderr)."""
    mock_proc = MagicMock()
    mock_proc.returncode = returncode
    mock_proc.pid = 12345
    mock_proc.communicate.return_value = (stdout, stderr)
    return mock_proc


class TestCommandConstruction(unittest.TestCase):
    def test_command_construction(self):
        """The command list must include --background, --factory-startup, --python."""
        runner = _make_runner()
        captured_cmd = []

        def fake_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            mock_proc = _mock_popen()
            return mock_proc

        with patch("subprocess.Popen", side_effect=fake_popen):
            with patch("psutil.Process"):
                runner.run("script.py", {"output_dir": r"C:\tmp"})

        self.assertIn("--background", captured_cmd)
        self.assertIn("--factory-startup", captured_cmd)
        self.assertIn("--python", captured_cmd)
        self.assertIn("script.py", captured_cmd)
        self.assertEqual(captured_cmd[0], FAKE_BLENDER)


class TestEnvVarSet(unittest.TestCase):
    def test_env_var_set(self):
        """BLENDER_CONFIG_PATH must be set in the subprocess environment."""
        runner = _make_runner()
        captured_env: dict = {}

        def fake_popen(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            return _mock_popen()

        with patch("subprocess.Popen", side_effect=fake_popen):
            with patch("psutil.Process"):
                runner.run("script.py", {"output_dir": r"C:\tmp"})

        self.assertIn("BLENDER_CONFIG_PATH", captured_env)
        self.assertTrue(captured_env["BLENDER_CONFIG_PATH"].endswith(".json"))


class TestExitCodeNonzeroIsFailure(unittest.TestCase):
    def test_exit_code_nonzero_is_failure(self):
        """Non-zero exit code results in BlenderResult.success == False."""
        runner = _make_runner()

        with patch("subprocess.Popen", return_value=_mock_popen(returncode=1)):
            with patch("psutil.Process"):
                result = runner.run("script.py", {"output_dir": r"C:\tmp"})

        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 1)


class TestDetectRenderErrorsTraceback(unittest.TestCase):
    def test_detect_render_errors_traceback(self):
        """'Traceback' in stderr produces a non-empty error list."""
        runner = _make_runner()
        errors = runner.detect_render_errors(
            stdout="",
            stderr="Traceback (most recent call last):\n  File 'x.py', line 1, in <module>",
        )
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("Traceback" in e for e in errors))


class TestDetectRenderErrorsClean(unittest.TestCase):
    def test_detect_render_errors_clean(self):
        """Clean output produces an empty error list."""
        runner = _make_runner()
        errors = runner.detect_render_errors(
            stdout="Blender 4.4.3\nSaved: frame_001.png\n",
            stderr="",
        )
        self.assertEqual(errors, [])


class TestTimeoutKillsProcess(unittest.TestCase):
    def test_timeout_kills_process(self):
        """When communicate() raises TimeoutExpired, the process is killed and success=False."""
        runner = _make_runner()

        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_proc.returncode = None
        mock_proc.communicate.side_effect = [
            __import__("subprocess").TimeoutExpired(cmd="blender", timeout=1),
            ("", ""),  # second call after kill()
        ]

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch("psutil.Process"):
                result = runner.run("script.py", {"output_dir": r"C:\tmp"}, timeout=1)

        mock_proc.kill.assert_called_once()
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
