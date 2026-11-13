"""Stage 7 UI smoke tests and render-state checks."""

from pathlib import Path

import pytest

from studio.story_render import atomic_json
from studio.ui_jobs import project_path, verify_result

APP = Path(__file__).resolve().parents[1] / "studio_ui.py"


@pytest.mark.parametrize("name", ["../escape", "CON", "bad name", ""])
def test_project_name_stays_within_workspace(tmp_path, name):
    with pytest.raises(ValueError):
        project_path(tmp_path, name)


def test_render_completion_requires_verified_video(tmp_path):
    atomic_json(tmp_path / "progress.json", {"scenes": {}})
    assert verify_result("render", tmp_path)["status"] == "paused"
    (tmp_path / "final_video.mp4").write_bytes(b"partial")
    assert verify_result("render", tmp_path)["status"] == "failed"
    atomic_json(tmp_path / "production_report.json", {"status": "complete"})
    assert verify_result("render", tmp_path)["status"] == "complete"


def test_dashboard_renders_and_rejects_invalid_project(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("CARTOON_STUDIO_PROJECTS", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    assert not app.exception
    assert app.title[0].value == "Cartoon Animation Studio"
    app.text_input(key="project_name").set_value("../escape")
    app.button[0].click().run()
    assert not app.exception
    assert any("project name" in error.value for error in app.error)
    assert list(tmp_path.iterdir()) == []
