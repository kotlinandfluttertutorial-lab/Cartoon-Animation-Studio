"""Exercise Stage 13 camera data and deterministic movement without Blender."""

import importlib.util
from pathlib import Path

import pytest


path = Path(__file__).resolve().parents[1] / "blender/scripts/stage13_camera.py"
spec = importlib.util.spec_from_file_location("stage13_camera", path)
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)


def test_presets_cover_the_review_shots():
    assert set(camera.CAMERAS) == {
        "establishing", "full_body", "medium_two", "medium_single", "close_up",
        "extreme_close_up", "over_shoulder", "conversation", "walking_follow",
        "side_tracking",
    }
    for preset in camera.CAMERAS.values():
        assert preset.lens > 0
        assert preset.position != preset.target
        assert set(preset.subjects) <= {"Aarav", "Aanya"}


def test_lighting_parameters_are_bounded():
    assert len(camera.LIGHTS) == 6
    for studio, exposure, shadow, cavity, background in camera.LIGHTS.values():
        assert studio.endswith(".sl")
        assert -2 <= exposure <= 2
        assert 0 <= shadow <= 1 and 0 <= cavity <= 1
        assert all(0 <= channel <= 1 for channel in background)


@pytest.mark.parametrize("movement", camera.MOVEMENTS)
def test_movement_endpoints_and_determinism(movement):
    preset = camera.CAMERAS["medium_two"]
    assert camera.camera_pose("medium_two", movement, 0) == (preset.position, preset.target)
    expected = tuple(tuple(value + change for value, change in zip(vector, delta))
                     for vector, delta in zip((preset.position, preset.target), camera.MOVEMENTS[movement]))
    for actual, endpoint in zip(camera.camera_pose("medium_two", movement, 1), expected):
        assert actual == pytest.approx(endpoint)
    sample = camera.camera_pose("medium_two", movement, .27)
    assert sample == camera.camera_pose("medium_two", movement, .27)


def test_custom_endpoints_and_easing():
    position, target = (1, 5, 2), (0, 0, 2)
    assert camera.camera_pose("medium_two", "static", 1, end_position=position,
                              end_target=target) == (position, target)
    assert camera.interpolate((0,), (1,), .01)[0] < .001
    assert camera.interpolate((0,), (1,), .99)[0] > .999
    with pytest.raises(ValueError):
        camera.interpolate((0,), (1,), float("nan"))
