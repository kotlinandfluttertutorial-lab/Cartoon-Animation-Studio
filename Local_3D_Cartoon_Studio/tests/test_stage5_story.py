"""Validate Stage 5 story constraints and sample-accurate dialogue timing."""

from array import array
import json
from pathlib import Path
import wave

import pytest
from pydantic import ValidationError

from studio.story_audio import SAMPLE_RATE, mix_scene, read_voice, voice_timing, write_tone
from studio.story_planner import Story, generate_story, load_story


def story_data():
    return {
        "title": "Garden Birds",
        "duration_seconds": 10,
        "characters": ["Aarav", "Aanya"],
        "scenes": [{
            "title": "Look up",
            "duration_seconds": 10,
            "camera": "medium",
            "performances": [
                {"character": "Aarav", "action": "point", "expression": "happy", "entrance": False},
                {"character": "Aanya", "action": "wave", "expression": "surprised", "entrance": False},
            ],
            "narration": "",
            "dialogue": [{"character": "Aarav", "text": "Look, a bird!", "emotion": "happy"}],
            "sound_effects": [{"effect": "bird_chirp", "at_seconds": 3}],
        }],
    }


def test_manual_story_preserves_validated_plan(tmp_path):
    source = tmp_path / "story.json"
    source.write_text(json.dumps(story_data()), encoding="utf-8")
    expected = story_data()
    expected["scenes"][0]["props"] = []
    assert load_story(source).model_dump() == expected


@pytest.mark.parametrize("field, value", [("action", "teleport"), ("character", "Other")])
def test_unknown_actions_and_cast_are_rejected(field, value):
    data = story_data()
    data["scenes"][0]["performances"][0][field] = value
    with pytest.raises(ValidationError):
        Story.model_validate(data)


def test_wrong_scene_duration_is_rejected():
    data = story_data()
    data["scenes"][0]["duration_seconds"] = 8
    with pytest.raises(ValidationError, match="Scene durations"):
        Story.model_validate(data)


def test_establishing_shot_can_have_no_cast():
    data = story_data()
    data["scenes"][0].update(performances=[], dialogue=[], camera="pullback")
    assert Story.model_validate(data).scenes[0].performances == []


def test_entrance_requires_walk():
    data = story_data()
    performer = data["scenes"][0]["performances"][0]
    performer["entrance"] = True
    with pytest.raises(ValidationError, match="entrance requires the walk"):
        Story.model_validate(data)
    performer["action"] = "walk"
    assert Story.model_validate(data).scenes[0].performances[0].entrance


def test_ollama_request_constrains_short_story_duration(monkeypatch):
    import io

    data = story_data()
    data["scenes"][0]["props"] = [{
        "name": "Red drum",
        "position": "screen_left",
        "parts": [{"shape": "cylinder", "color": "#C53030", "center": [0, 0, 0.4], "size": [0.6, 0.6, 0.8]}],
    }]

    def respond(request, timeout):
        payload = json.loads(request.data)
        assert payload["format"]["properties"]["duration_seconds"]["enum"] == [10]
        assert payload["format"]["properties"]["scenes"]["maxItems"] == 1
        assert payload["format"]["$defs"]["SoundCue"]["properties"]["at_seconds"]["maximum"] == 9
        assert "props" in payload["format"]["$defs"]["Scene"]["required"]
        return io.StringIO(json.dumps({"message": {"content": json.dumps(data)}}))

    monkeypatch.setattr("studio.story_planner.urlopen", respond)
    story = generate_story("Add a red drum.", 10, "http://localhost:11434", "qwen3:4b")
    assert story.duration_seconds == 10
    assert story.scenes[0].props[0].parts[0].shape == "cylinder"
    assert Story.model_validate_json(story.model_dump_json()) == story


def test_ollama_cues_are_kept_inside_their_own_scene(monkeypatch, tmp_path):
    import io

    data = story_data()
    data["duration_seconds"] = 18
    data["scenes"].append({
        **data["scenes"][0],
        "duration_seconds": 8,
        "sound_effects": [
            {"effect": "chime", "at_seconds": 8},
            {"effect": "bird_chirp", "at_seconds": 12},
            {"effect": "chime", "at_seconds": 0},
        ],
    })
    source = tmp_path / "story.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValidationError, match="Sound effects must start within the scene"):
        load_story(source)

    response = json.dumps({"message": {"content": json.dumps(data)}})
    monkeypatch.setattr("studio.story_planner.urlopen", lambda *args, **kwargs: io.StringIO(response))
    story = generate_story("Find a bird in the garden.", 18, "http://localhost:11434", "qwen3:4b")
    assert [cue.at_seconds for cue in story.scenes[0].sound_effects] == [3]
    assert [cue.at_seconds for cue in story.scenes[1].sound_effects] == [7, 7, 0]


def test_silence_closes_mouth_and_partial_frame_is_retained(tmp_path):
    path = tmp_path / "voice.wav"
    # 121 samples at 120 Hz need 13 frames at 12 fps.
    samples = array("h", [0] * 20 + [1000, -1000] * 40 + [0] * 21)
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 120, 0, "NONE", "not compressed"))
        wav.writeframes(samples.tobytes())
    data, seconds = voice_timing({"character": "Aarav", "text": "Look up!"}, path)
    assert seconds == 121 / 120
    assert data.total_frames == 13
    assert data.get_viseme(1) == data.get_viseme(12) == data.get_viseme(13) == "REST"
    assert len({data.get_viseme(frame) for frame in range(3, 11)} - {"REST"}) >= 2


def test_scene_mix_ends_at_planned_duration(tmp_path):
    config = Path(__file__).resolve().parents[1] / "config/settings.json"
    ffmpeg = Path(json.loads(config.read_text(encoding="utf-8"))["ffmpeg_executable"])
    if not ffmpeg.is_file():
        pytest.skip("Configured FFmpeg is unavailable")
    music, effect, mixed = (tmp_path / name for name in ("music.wav", "effect.wav", "mix.wav"))
    write_tone(music, 1, "music")
    write_tone(effect, 0.6, "chime")
    mix_scene(ffmpeg, [(music, 0), (effect, 800)], mixed, 1)
    samples, rate = read_voice(mixed)
    assert rate == len(samples) == SAMPLE_RATE


def test_audio_ending_on_speech_gets_a_rest_frame(tmp_path):
    path = tmp_path / "voice.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 120, 0, "NONE", "not compressed"))
        wav.writeframes(array("h", [1000, -1000] * 5).tobytes())
    data, _ = voice_timing({"character": "Aarav", "text": "Wow!"}, path)
    assert data.total_frames == 2
    assert data.get_viseme(1) != "REST"
    assert data.get_viseme(2) == "REST"
