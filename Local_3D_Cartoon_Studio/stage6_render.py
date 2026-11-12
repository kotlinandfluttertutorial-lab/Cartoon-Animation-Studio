"""Render a prepared Stage 5 story as a resumable Workbench production."""

import argparse
import json
from pathlib import Path
import subprocess

from studio.config_manager import ConfigManager
from studio.story_render import render_story


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prepared", type=Path, help="Directory with story.json, timing.json, and prepared audio.")
    parser.add_argument("output", type=Path)
    parser.add_argument("--quality", choices=("preview", "720p"), default="preview")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--frame-budget", type=int, help="Pause after rendering this many new frames.")
    args = parser.parse_args()
    if args.frame_budget is not None and args.frame_budget < 1:
        parser.error("--frame-budget must be positive.")
    config = ConfigManager(Path(__file__).resolve().parent / "config")
    config.load()
    preview = config.get_profile("PREVIEW")
    profile = (preview.width, preview.height, preview.fps) if args.quality == "preview" else (1280, 720, 24)
    try:
        result = render_story(args.prepared, args.output, profile, config.settings, args.resume, args.frame_budget)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
