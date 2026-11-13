"""Command line entry point for Stage 5 planning and local audio preparation."""

import argparse
from pathlib import Path

from studio.config_manager import ConfigManager
from studio.story_planner import generate_story, load_story


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--idea")
    source.add_argument("--story", type=Path, help="Use an existing story JSON without calling Ollama.")
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True, help="New output directory.")
    parser.add_argument("--piper-studio", type=Path, help="Existing studio with a Piper-enabled .venv.")
    parser.add_argument("--aarav-voice", default="en_US-ryan-medium")
    parser.add_argument("--aanya-voice", default="en_US-ryan-medium")
    parser.add_argument("--aarav-speed", type=float, default=0.95)
    parser.add_argument("--aanya-speed", type=float, default=1.12)
    args = parser.parse_args()

    config = ConfigManager(Path(__file__).resolve().parent / "config")
    config.load()
    settings = config.settings
    try:
        if args.output.exists():
            raise ValueError("Choose a new output directory to preserve existing results.")
        story = (
            load_story(args.story) if args.story else
            generate_story(args.idea, args.duration, settings.ollama_url, settings.ollama_model)
        )
        args.output.mkdir(parents=True, exist_ok=False)
        path = args.output / "story.json"
        path.write_text(story.model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(f"Story saved to {path}")
        if args.piper_studio:
            from studio.story_audio import prepare_audio

            prepare_audio(
                story, args.output, args.piper_studio, settings.ffmpeg_executable,
                {"Aarav": (args.aarav_voice, args.aarav_speed),
                 "Aanya": (args.aanya_voice, args.aanya_speed)},
            )
            print(f"Audio and timing saved to {args.output}")
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
