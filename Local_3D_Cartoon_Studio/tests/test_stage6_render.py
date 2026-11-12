"""Regression checks for reusable production frames and subtitle timing."""

from pathlib import Path
import struct
from types import SimpleNamespace
import zlib

from studio.story_render import PNG_SIGNATURE, input_file, subtitles, valid_frame
import pytest


def chunk(kind, content):
    return struct.pack(">I", len(content)) + kind + content + struct.pack(">I", zlib.crc32(kind + content))


def test_frame_reuse_requires_dimensions_and_intact_png(tmp_path):
    path = tmp_path / "frame_0001.png"
    png = (
        PNG_SIGNATURE
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(4)))
        + chunk(b"IEND", b"")
    )
    assert not valid_frame(path, 1, 1)
    path.write_bytes(png)
    assert valid_frame(path, 1, 1)
    assert not valid_frame(path, 640, 360)
    path.write_bytes(png[:-1])
    assert not valid_frame(path, 1, 1)
    path.write_bytes(png[:42] + bytes([png[42] ^ 1]) + png[43:])
    assert not valid_frame(path, 1, 1)


def test_subtitles_follow_story_time_and_audio_duration():
    line = {"character": "Aanya", "text": "Look up!\n A bird.", "start_frame": 7, "duration_seconds": 1.25}
    scenes = [(SimpleNamespace(duration_seconds=5), None, []), (SimpleNamespace(duration_seconds=2), None, [line])]
    assert subtitles(scenes, 12) == "1\n00:00:05,500 --> 00:00:06,750\nAanya: Look up! A bird.\n"


def test_prepared_input_cannot_escape_its_directory(tmp_path):
    outside = tmp_path / "outside.wav"
    outside.touch()
    directory = tmp_path / "prepared"
    directory.mkdir()
    with pytest.raises(ValueError, match="invalid prepared input"):
        input_file(directory, Path("..") / outside.name)
