"""Render an expression from a solo Stage 4 character blend in Blender.

Usage: blender -b <blend> --python apply_expression.py -- <char_name> <emotion> <output_png>
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
from facial_preview import mouth_surface, setup_preview
from studio.dialogue.expression_library import apply_expression, restore_expression


def main():
    character, emotion, output = sys.argv[sys.argv.index("--") + 1:]
    scene = setup_preview(character)
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output)

    saved = apply_expression(character, emotion)
    try:
        with mouth_surface(character, emotion):
            bpy.ops.render.render(write_still=True)
    finally:
        restore_expression(saved)

    print("EXPRESSION_RENDER_OK")


if __name__ == "__main__":
    main()
