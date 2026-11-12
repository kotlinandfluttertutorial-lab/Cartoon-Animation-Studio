"""Prepare real local dialogue, narration, mouth timing, and scene audio mixes."""

from array import array
import json
from math import isqrt, sin, tau
import os
from pathlib import Path
import subprocess
import sys
import wave

from studio.dialogue.lipsync_generator import LipsyncData
from studio.dialogue.phoneme_mapper import PhonemeMapper
from studio.story_planner import Story

FPS = 12
SAMPLE_RATE = 22050
GAP_FRAMES = 4

# The existing Piper installation runs in its own environment. The bridge only
# imports its synthesis API and writes the requested files in this studio.
PIPER_BRIDGE = """
import json
from pathlib import Path
import sys
from studio import logger

logger.LOG_FILE = Path(sys.argv[1])
from studio.tts_piper import generate_speech

for line in json.load(sys.stdin):
    generate_speech(line["text"], line["audio"], voice_name=line["voice"], speed=line["speed"])
"""


def run(command, **kwargs):
    try:
        result = subprocess.run(
            command, capture_output=True, encoding="utf-8", errors="replace", **kwargs
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{Path(command[0]).name} timed out after {exc.timeout} seconds.") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-1800:]
        raise RuntimeError(f"{Path(command[0]).name} exited {result.returncode}. {detail}")


def read_voice(path):
    with wave.open(str(path), "rb") as wav:
        if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            raise ValueError(f"Expected mono 16-bit PCM from Piper at {path}.")
        samples = array("h", wav.readframes(wav.getnframes()))
        if sys.byteorder != "little":
            samples.byteswap()
        if not any(samples):
            raise ValueError(f"Piper returned an empty or silent track at {path}.")
        return samples, wav.getframerate()


def voice_timing(line, path, fps=FPS):
    """Use WAV activity for silence and distribute text visemes across voiced frames."""
    samples, rate = read_voice(path)
    total = (len(samples) * fps + rate - 1) // rate
    levels = []
    for i in range(total):
        segment = samples[i * rate // fps:(i + 1) * rate // fps]
        levels.append(isqrt(sum(sample * sample for sample in segment) // len(segment)) if segment else 0)

    threshold = max(50, max(levels) // 12)
    active = [i for i, level in enumerate(levels, 1) if level >= threshold]
    visemes = PhonemeMapper.text_to_viseme_list(line["text"])
    frames = {
        frame: visemes[index * len(visemes) // len(active)]
        for index, frame in enumerate(active)
    } if visemes else {}
    # Keep a closed/rest pose available for cuts and for a hold between lines.
    if frames.get(total, "REST") != "REST":
        total += 1
    data = LipsyncData(fps, total, line["character"], frames, text=line["text"])
    return data, len(samples) / rate


def write_tone(path, seconds, effect):
    """Create quiet, original synth music and cue samples without external media."""
    pcm = array("h")
    notes = (261.63, 329.63, 392.0, 329.63, 293.66, 349.23, 440.0, 349.23)
    for index in range(round(seconds * SAMPLE_RATE)):
        t = index / SAMPLE_RATE
        if effect == "music":
            beat = t * 2
            envelope = min(1, (beat % 1) * 25) * (1 - beat % 1) ** 2
            sample = sin(tau * notes[int(beat) % len(notes)] * t) * envelope * 0.045
        else:
            envelope = min(1, t * 70) * max(0, 1 - t / seconds) ** 2
            frequency = 1300 + 1600 * t if effect == "bird_chirp" else 784
            sample = sin(tau * frequency * t) * envelope * 0.13
        pcm.append(round(sample * 32767))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        wav.writeframes(pcm.tobytes())


def mix_scene(ffmpeg, inputs, destination, duration):
    command = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin", "-n"]
    filters = []
    for index, (path, milliseconds) in enumerate(inputs):
        command.extend(("-i", str(path)))
        filters.append(
            f"[{index}:a]aresample={SAMPLE_RATE},aformat=channel_layouts=mono,"
            f"adelay={milliseconds}:all=1[a{index}]"
        )
    labels = "".join(f"[a{i}]" for i in range(len(inputs)))
    filters.append(
        f"{labels}amix=inputs={len(inputs)}:normalize=0,alimiter=limit=0.95:latency=1,"
        f"atrim=duration={duration}[mix]"
    )
    run(command + [
        "-filter_complex_threads", "1", "-filter_complex", ";".join(filters),
        "-map", "[mix]", str(destination),
    ], timeout=90)


def prepare_audio(story: Story, output: Path, piper_studio: Path, ffmpeg: str, voices: dict):
    output = output.resolve()
    runtime = piper_studio.resolve()
    python = runtime / ".venv" / "Scripts" / "python.exe"
    if not python.is_file() or not (runtime / "studio/tts_piper.py").is_file():
        raise ValueError("Provide the existing Windows Piper studio with its .venv and studio/tts_piper.py.")
    if any(not voice.strip() or not 0.5 <= speed <= 2 for voice, speed in voices.values()):
        raise ValueError("Voice names are required and voice speeds must be between 0.5 and 2.")

    scenes = []
    requests = []
    for number, scene in enumerate(story.scenes, 1):
        directory = output / f"scene_{number:02}"
        directory.mkdir()
        lines = []
        if scene.narration:
            lines.append({"character": "Narrator", "text": scene.narration, "emotion": "neutral"})
        lines.extend(line.model_dump() for line in scene.dialogue)
        for index, line in enumerate(lines, 1):
            speaker = line["character"]
            line["voice"], line["speed"] = voices.get(speaker, voices["Aarav"])
            line["audio"] = str(directory / f"{index:02}_{speaker.lower()}.wav")
            requests.append(line)
        scenes.append((scene, directory, lines))

    if requests:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
        run(
            [str(python), "-c", PIPER_BRIDGE, str(output / "piper.log")],
            input=json.dumps(requests), cwd=runtime, env=env, timeout=600,
        )

    timeline = []
    story_frame = 1
    for scene, directory, lines in scenes:
        frame = 1
        inputs = []
        for line in lines:
            path = Path(line["audio"])
            data, duration = voice_timing(line, path)
            line.update(start_frame=frame, duration_frames=data.total_frames, duration_seconds=duration)
            if line["character"] != "Narrator":
                lipsync = path.with_suffix(".lipsync.json")
                lipsync.write_text(
                    json.dumps({**vars(data), "emotion": line["emotion"]}, indent=2) + "\n",
                    encoding="utf-8",
                )
                line["lipsync"] = str(lipsync.relative_to(output))
            line["audio"] = str(path.relative_to(output))
            inputs.append((path, round((frame - 1) * 1000 / FPS)))
            frame += data.total_frames + GAP_FRAMES

        if lines and frame - GAP_FRAMES - 1 > scene.duration_seconds * FPS:
            raise ValueError(f"Speech exceeds the duration of '{scene.title}'. Shorten the dialogue or extend the scene.")
        music = directory / "music.wav"
        write_tone(music, scene.duration_seconds, "music")
        inputs.append((music, 0))
        for index, cue in enumerate(scene.sound_effects, 1):
            effect = directory / f"effect_{index:02}_{cue.effect}.wav"
            write_tone(effect, 0.28 if cue.effect == "bird_chirp" else 0.6, cue.effect)
            inputs.append((effect, cue.at_seconds * 1000))

        mixed = directory / "mix.wav"
        mix_scene(ffmpeg, inputs, mixed, scene.duration_seconds)
        timeline.append({
            "title": scene.title,
            "start_frame": story_frame,
            "duration_frames": scene.duration_seconds * FPS,
            "mix": str(mixed.relative_to(output)),
            "lines": lines,
        })
        story_frame += scene.duration_seconds * FPS

    (output / "timing.json").write_text(
        json.dumps({"fps": FPS, "scenes": timeline}, indent=2) + "\n", encoding="utf-8"
    )
