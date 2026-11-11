"""
create_garden.py - Procedurally creates the reusable cartoon garden environment.

Usage:
    blender --background --factory-startup --python create_garden.py

Repeatable: starts from a clean empty scene each run, backs up any existing
garden.blend as garden.blend.YYYYMMDD_HHMMSS.bak, rebuilds the full garden,
saves garden.blend, and writes garden.json with REAL polygon/object/material
counts and timings. Compatible with Blender 4.4.3 (Workbench only).
"""
import sys
import os
import json
import time
import shutil
import datetime

# Make garden_utils importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy
import garden_utils

# ---------------------------------------------------------------------------
# Timing + fresh scene
# ---------------------------------------------------------------------------
start_time = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------
GARDEN_DIR = r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\environments\garden'
env_override = os.environ.get('GARDEN_DIR')
if env_override:
    GARDEN_DIR = env_override
os.makedirs(GARDEN_DIR, exist_ok=True)
os.makedirs(os.path.join(GARDEN_DIR, 'previews'), exist_ok=True)

# ---------------------------------------------------------------------------
# Backup existing garden.blend before overwriting
# ---------------------------------------------------------------------------
blend_path = os.path.join(GARDEN_DIR, 'garden.blend')
if os.path.exists(blend_path):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'{blend_path}.{ts}.bak'
    shutil.copy2(blend_path, backup_path)
    print(f'[Garden] Backed up existing blend to: {backup_path}')

# ---------------------------------------------------------------------------
# Build the garden
# ---------------------------------------------------------------------------
garden_utils.create_world_background('#87CEEB')
garden_utils.create_ground()
garden_utils.create_path()

# Trees (5): sides and rear, never in the character area
tree_defs = [
    (-3.0, 2.0, 1.0,  0.6,  '#66BB6A'),
    ( 3.0, 2.0, 1.1,  0.65, '#7CB342'),
    (-3.0, -3.0, 1.0, 0.55, '#4CAF50'),
    ( 3.0, -3.0, 1.05, 0.6, '#81C784'),
    ( 0.0,  5.0, 1.2, 0.7,  '#9CCC65'),
]
for td in tree_defs:
    garden_utils.create_tree(*td)

# Bushes (6): around garden edges
bush_defs = [
    (-2.0,  4.0, 0.4,  '#43A047'),
    ( 2.0,  4.0, 0.45, '#2E7D32'),
    (-2.0, -4.0, 0.4,  '#81C784'),
    ( 2.0, -4.0, 0.5,  '#43A047'),
    (-4.0,  0.0, 0.45, '#2E7D32'),
    ( 4.0,  0.0, 0.4,  '#81C784'),
]
for bd in bush_defs:
    garden_utils.create_bush(*bd)

# Flowers (12): scattered around borders and near the path
flower_pos = [
    (-1.5, 3.0), (1.5, 3.0), (-1.5, -3.0), (1.5, -3.0),
    (-3.5, 1.0), (3.5, 1.0), (-3.5, -1.0), (3.5, -1.0),
    (-2.5, 5.0), (2.5, 5.0), (-5.0, 2.0), (5.0, -2.0),
]
flower_colors = [
    '#F44336', '#FFEB3B', '#E91E63', '#FF9800',
    '#2196F3', '#F44336', '#FFEB3B', '#E91E63',
    '#FF9800', '#2196F3', '#F44336', '#FFEB3B',
]
for (fx, fy), fc in zip(flower_pos, flower_colors):
    garden_utils.create_flower(fx, fy, fc)

# Decorations: 4 stones, 1 sign, 1 bench — all outside the character area
for sd in [(-2.5, 2.5, 0.2), (2.5, -2.5, 0.18), (-4.0, -3.0, 0.22), (4.0, 3.0, 0.15)]:
    garden_utils.create_stone(*sd)
garden_utils.create_sign(4.0, -2.5)
garden_utils.create_bench(3.0, 4.5)

# Clouds (5): elongated white icospheres, Z=3-4, Y=-5 to -8 (background)
cloud_defs = [
    (-3.0, -6.5, 3.5, 1.0),
    (-1.5, -7.5, 3.8, 0.9),
    ( 1.5, -8.0, 3.3, 1.1),
    ( 3.0, -7.0, 3.6, 0.8),
    ( 0.0, -5.5, 4.0, 1.0),
]
for cd in cloud_defs:
    garden_utils.create_cloud(*cd)

# Lighting
garden_utils.create_sun_light()

# Cameras (3)
main_cam = garden_utils.create_camera('Garden_Main_Camera', (0, -6, 2.5), (0, 0, 0.8), 50)
garden_utils.create_camera('Garden_Wide_Camera', (0, -10, 4), (0, 0, 0), 35)
garden_utils.create_camera('Garden_Close_Camera', (0, -3, 1.8), (0, 0, 0.8), 85)
bpy.context.scene.camera = main_cam

# ---------------------------------------------------------------------------
# Save .blend
# ---------------------------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f'[Garden] Saved blend file: {blend_path}')

# ---------------------------------------------------------------------------
# Statistics (real counts)
# ---------------------------------------------------------------------------
generation_time = time.time() - start_time

total_polygons = 0
total_objects = 0
for obj in bpy.data.objects:
    total_objects += 1
    if obj.type == 'MESH':
        total_polygons += len(obj.data.polygons)
total_materials = len(bpy.data.materials)
blend_file_size = os.path.getsize(blend_path)

COLLECTIONS = [
    'Environment_Ground', 'Environment_Path', 'Environment_Trees',
    'Environment_Bushes', 'Environment_Flowers', 'Environment_Decorations',
    'Environment_Sky', 'Lighting', 'Cameras',
]
CAMERAS = ['Garden_Main_Camera', 'Garden_Wide_Camera', 'Garden_Close_Camera']

garden_data = {
    'environment_id': 'garden',
    'version': '1.0.0',
    'created_date': datetime.datetime.utcnow().isoformat() + 'Z',
    'blend_file': 'garden.blend',
    'statistics': {
        'total_polygons': total_polygons,
        'total_objects': total_objects,
        'total_materials': total_materials,
        'generation_time_s': round(generation_time, 3),
        'blend_file_size_bytes': blend_file_size,
    },
    'collections': COLLECTIONS,
    'cameras': CAMERAS,
    'previews': {
        'garden_wide': 'previews/garden_wide.png',
        'garden_main': 'previews/garden_main.png',
        'garden_close': 'previews/garden_close.png',
        'garden_with_characters': 'previews/garden_with_characters.png',
    },
}

json_path = os.path.join(GARDEN_DIR, 'garden.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(garden_data, f, indent=2)
print(f'[Garden] Saved garden.json: {json_path}')

summary = {
    'status': 'success',
    'blend_file': blend_path,
    'garden_json': json_path,
    'statistics': garden_data['statistics'],
}
print(json.dumps(summary, indent=2))
