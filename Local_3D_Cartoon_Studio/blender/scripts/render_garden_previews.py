"""
render_garden_previews.py - Renders the 4 garden preview PNGs (640x360 Workbench).

Usage:
    blender --background --factory-startup --python render_garden_previews.py

Renders three garden-only views from garden.blend (wide / main / close) using the
three cameras stored in the blend, then appends Aarav and Aanya into the same
scene (root-object offsets only, matching _render_combined.py) and renders the
combined view with Garden_Main_Camera. garden.blend is never re-saved, so it
stays free of character data. Writes render timings to render_timings.json.
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy
import garden_utils

GARDEN_DIR = r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\environments\garden'
BLEND = os.path.join(GARDEN_DIR, 'garden.blend')
PREVIEWS = os.path.join(GARDEN_DIR, 'previews')
AARAV_BLEND = r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\characters\aarav\aarav.blend'
AANYA_BLEND = r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\characters\aanya\aanya.blend'

os.makedirs(PREVIEWS, exist_ok=True)

# Load the garden
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
garden_utils.configure_workbench(scene)


def render_with(cam_name, out_name):
    cam = bpy.data.objects.get(cam_name)
    scene.camera = cam
    scene.render.filepath = os.path.join(PREVIEWS, out_name)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return round(time.time() - t, 3)


timings = {}
timings['garden_wide'] = render_with('Garden_Wide_Camera', 'garden_wide.png')
timings['garden_main'] = render_with('Garden_Main_Camera', 'garden_main.png')
timings['garden_close'] = render_with('Garden_Close_Camera', 'garden_close.png')

# ---------------------------------------------------------------------------
# Character integration: append Aarav + Aanya, offset root objects only.
# ---------------------------------------------------------------------------
bpy.ops.wm.append(
    filepath=AARAV_BLEND + r'\Collection\Aarav',
    directory=AARAV_BLEND + r'\Collection\\',
    filename='Aarav',
)
bpy.ops.wm.append(
    filepath=AANYA_BLEND + r'\Collection\Aanya',
    directory=AANYA_BLEND + r'\Collection\\',
    filename='Aanya',
)

aarav_col = bpy.data.collections.get('Aarav')
if aarav_col:
    for obj in aarav_col.all_objects:
        if obj.parent is None:
            obj.location.x -= 0.4   # to X = -0.4 (root starts at 0)

aanya_col = bpy.data.collections.get('Aanya')
if aanya_col:
    for obj in aanya_col.all_objects:
        if obj.parent is None:
            obj.location.x += 0.5   # to X = 0.5 (root starts at 0)

# Re-apply Workbench settings (append can reset shading display)
garden_utils.configure_workbench(scene)
scene.camera = bpy.data.objects.get('Garden_Main_Camera')
scene.render.filepath = os.path.join(PREVIEWS, 'garden_with_characters.png')
t = time.time()
bpy.ops.render.render(write_still=True)
timings['garden_with_characters'] = round(time.time() - t, 3)

# Persist timings for the results assembler
with open(os.path.join(GARDEN_DIR, 'render_timings.json'), 'w', encoding='utf-8') as f:
    json.dump(timings, f, indent=2)

print(json.dumps({'status': 'RENDER_COMPLETE', 'timings': timings}, indent=2))
