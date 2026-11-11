"""
create_aarav.py - Procedurally creates the Aarav cartoon boy character in Blender.

Usage:
    blender --background --factory-startup --python create_aarav.py

Compatible with Blender 4.4.3. Uses Workbench rendering.
"""
import sys
import os
import json
import time
import shutil
import math

# Add scripts directory to sys.path so character_utils can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy
from mathutils import Vector, Euler
import character_utils

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
start_time = time.time()

# ---------------------------------------------------------------------------
# Fresh scene
# ---------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------
base_dir = r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\characters\aarav'
env_override = os.environ.get('BLENDER_CONFIG_PATH')
if env_override:
    base_dir = env_override

os.makedirs(base_dir, exist_ok=True)

# ---------------------------------------------------------------------------
# Backup existing .blend
# ---------------------------------------------------------------------------
blend_path = os.path.join(base_dir, 'aarav.blend')
if os.path.exists(blend_path):
    backup_path = os.path.join(base_dir, f'aarav_v{int(time.time())}.blend')
    shutil.copy2(blend_path, backup_path)
    print(f"[Aarav] Backed up existing blend to: {backup_path}")

# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------
mat_skin       = character_utils.create_material('Aarav_Skin',      (0.776, 0.525, 0.259, 1.0))
mat_shirt      = character_utils.create_material('Aarav_Shirt',     (0.129, 0.588, 0.953, 1.0))
mat_trousers   = character_utils.create_material('Aarav_Trousers',  (0.102, 0.137, 0.494, 1.0))
mat_shoes      = character_utils.create_material('Aarav_Shoes',     (0.933, 0.933, 0.933, 1.0))
mat_hair       = character_utils.create_material('Aarav_Hair',      (0.243, 0.153, 0.137, 1.0))
mat_eye_white  = character_utils.create_material('Aarav_EyeWhite',  (1.0,   1.0,   1.0,   1.0))
mat_iris       = character_utils.create_material('Aarav_Iris',      (0.306, 0.204, 0.180, 1.0))
mat_mouth      = character_utils.create_material('Aarav_Mouth',     (0.898, 0.451, 0.451, 1.0))

# ---------------------------------------------------------------------------
# Helper: assign material and obj.color
# ---------------------------------------------------------------------------
def assign_mat(obj, mat):
    obj.data.materials.append(mat)
    obj.color = mat.diffuse_color


# ---------------------------------------------------------------------------
# Mesh objects
# Object spec: (name, build_fn, location, scale, material)
# build_fn is called immediately before naming/placing to create the primitive.
# ---------------------------------------------------------------------------

def make_sphere(segments, ring_count):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=ring_count, location=(0, 0, 0))

def make_cylinder(vertices):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, location=(0, 0, 0))

def make_cube():
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))


OBJECT_DEFS = [
    # (name,               builder_fn,                       location,              scale,                   material)
    ('Aarav_Head',         lambda: make_sphere(16, 12),       (0,    0,    1.4),    (0.28,  0.28,  0.28),    mat_skin),
    ('Aarav_Neck',         lambda: make_cylinder(8),          (0,    0,    1.1),    (0.07,  0.07,  0.1),     mat_skin),
    ('Aarav_Torso',        make_cube,                         (0,    0,    0.85),   (0.22,  0.14,  0.22),    mat_shirt),
    ('Aarav_UpperArm_L',   lambda: make_cylinder(8),          (0.32, 0,    0.95),   (0.055, 0.055, 0.14),    mat_shirt),
    ('Aarav_UpperArm_R',   lambda: make_cylinder(8),          (-0.32,0,    0.95),   (0.055, 0.055, 0.14),    mat_shirt),
    ('Aarav_LowerArm_L',   lambda: make_cylinder(8),          (0.32, 0,    0.72),   (0.045, 0.045, 0.12),    mat_skin),
    ('Aarav_LowerArm_R',   lambda: make_cylinder(8),          (-0.32,0,    0.72),   (0.045, 0.045, 0.12),    mat_skin),
    ('Aarav_Hand_L',       make_cube,                         (0.32, 0,    0.56),   (0.06,  0.04,  0.07),    mat_skin),
    ('Aarav_Hand_R',       make_cube,                         (-0.32,0,    0.56),   (0.06,  0.04,  0.07),    mat_skin),
    ('Aarav_UpperLeg_L',   lambda: make_cylinder(8),          (0.1,  0,    0.5),    (0.07,  0.07,  0.17),    mat_trousers),
    ('Aarav_UpperLeg_R',   lambda: make_cylinder(8),          (-0.1, 0,    0.5),    (0.07,  0.07,  0.17),    mat_trousers),
    ('Aarav_LowerLeg_L',   lambda: make_cylinder(8),          (0.1,  0,    0.26),   (0.055, 0.055, 0.14),    mat_trousers),
    ('Aarav_LowerLeg_R',   lambda: make_cylinder(8),          (-0.1, 0,    0.26),   (0.055, 0.055, 0.14),    mat_trousers),
    ('Aarav_Foot_L',       make_cube,                         (0.1,  0.05, 0.07),   (0.08,  0.12,  0.07),    mat_shoes),
    ('Aarav_Foot_R',       make_cube,                         (-0.1, 0.05, 0.07),   (0.08,  0.12,  0.07),    mat_shoes),
    ('Aarav_Eye_L',        lambda: make_sphere(12, 8),        (0.1,  0.24, 1.42),   (0.055, 0.03,  0.055),   mat_eye_white),
    ('Aarav_Eye_R',        lambda: make_sphere(12, 8),        (-0.1, 0.24, 1.42),   (0.055, 0.03,  0.055),   mat_eye_white),
    ('Aarav_Iris_L',       lambda: make_sphere(8, 6),         (0.1,  0.265,1.42),   (0.03,  0.015, 0.03),    mat_iris),
    ('Aarav_Iris_R',       lambda: make_sphere(8, 6),         (-0.1, 0.265,1.42),   (0.03,  0.015, 0.03),    mat_iris),
    ('Aarav_Eyebrow_L',    make_cube,                         (0.1,  0.25, 1.49),   (0.055, 0.015, 0.012),   mat_hair),
    ('Aarav_Eyebrow_R',    make_cube,                         (-0.1, 0.25, 1.49),   (0.055, 0.015, 0.012),   mat_hair),
    ('Aarav_Nose',         lambda: make_sphere(8, 6),         (0,    0.265,1.37),   (0.03,  0.025, 0.025),   mat_skin),
    ('Aarav_Mouth',        make_cube,                         (0,    0.25, 1.32),   (0.065, 0.015, 0.018),   mat_mouth),
    ('Aarav_Hair_Top',     make_cube,                         (0,    0.05, 1.68),   (0.22,  0.18,  0.08),    mat_hair),
    ('Aarav_Hair_Back',    make_cube,                         (0,   -0.12, 1.5),    (0.2,   0.08,  0.15),    mat_hair),
    ('Aarav_Hair_Front',   make_cube,                         (0.0,  0.17, 1.65),   (0.15,  0.06,  0.06),    mat_hair),
]

mesh_objects = []

for obj_name, builder_fn, location, scale, mat in OBJECT_DEFS:
    builder_fn()
    obj = bpy.context.active_object
    obj.name = obj_name
    obj.location = Vector(location)
    obj.scale = Vector(scale)
    assign_mat(obj, mat)
    mesh_objects.append(obj)

# ---------------------------------------------------------------------------
# Smooth shading on spheres and cylinders
# ---------------------------------------------------------------------------
SMOOTH_OBJECTS = {
    'Aarav_Head', 'Aarav_Neck',
    'Aarav_UpperArm_L', 'Aarav_UpperArm_R',
    'Aarav_LowerArm_L', 'Aarav_LowerArm_R',
    'Aarav_UpperLeg_L', 'Aarav_UpperLeg_R',
    'Aarav_LowerLeg_L', 'Aarav_LowerLeg_R',
    'Aarav_Eye_L', 'Aarav_Eye_R',
    'Aarav_Iris_L', 'Aarav_Iris_R',
    'Aarav_Nose',
}
for obj in mesh_objects:
    if obj.name in SMOOTH_OBJECTS:
        character_utils.add_smooth_shading(obj)

# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------
for obj in mesh_objects:
    character_utils.add_to_collection(obj, 'Aarav')

# ---------------------------------------------------------------------------
# Armature (20 bones)
# ---------------------------------------------------------------------------
bpy.ops.object.add(type='ARMATURE', location=(0, 0, 0))
arm_obj = bpy.context.active_object
arm_obj.name = 'Aarav_Armature'
arm = arm_obj.data
arm.name = 'Aarav_Armature_Data'

bpy.ops.object.mode_set(mode='EDIT')

BONE_DEFS = [
    # (name,         head,                tail,                parent_name)
    ('root',         (0,    0,    0),      (0,    0,    0.1),   None),
    ('hips',         (0,    0,    0.62),   (0,    0,    0.72),  'root'),
    ('spine',        (0,    0,    0.72),   (0,    0,    0.85),  'hips'),
    ('chest',        (0,    0,    0.85),   (0,    0,    1.0),   'spine'),
    ('neck',         (0,    0,    1.05),   (0,    0,    1.15),  'chest'),
    ('head',         (0,    0,    1.15),   (0,    0,    1.5),   'neck'),
    ('shoulder_L',   (0.15, 0,    1.0),    (0.25, 0,    1.0),   'chest'),
    ('upper_arm_L',  (0.25, 0,    1.0),    (0.32, 0,    0.85),  'shoulder_L'),
    ('forearm_L',    (0.32, 0,    0.85),   (0.32, 0,    0.68),  'upper_arm_L'),
    ('hand_L',       (0.32, 0,    0.68),   (0.32, 0,    0.56),  'forearm_L'),
    ('shoulder_R',   (-0.15,0,    1.0),    (-0.25,0,    1.0),   'chest'),
    ('upper_arm_R',  (-0.25,0,    1.0),    (-0.32,0,    0.85),  'shoulder_R'),
    ('forearm_R',    (-0.32,0,    0.85),   (-0.32,0,    0.68),  'upper_arm_R'),
    ('hand_R',       (-0.32,0,    0.68),   (-0.32,0,    0.56),  'forearm_R'),
    ('thigh_L',      (0.1,  0,    0.65),   (0.1,  0,    0.42),  'hips'),
    ('shin_L',       (0.1,  0,    0.42),   (0.1,  0,    0.2),   'thigh_L'),
    ('foot_L',       (0.1,  0,    0.2),    (0.1,  0.12, 0.07),  'shin_L'),
    ('thigh_R',      (-0.1, 0,    0.65),   (-0.1, 0,    0.42),  'hips'),
    ('shin_R',       (-0.1, 0,    0.42),   (-0.1, 0,    0.2),   'thigh_R'),
    ('foot_R',       (-0.1, 0,    0.2),    (-0.1, 0.12, 0.07),  'shin_R'),
]

# Create all bones first
for bone_name, head, tail, _ in BONE_DEFS:
    b = arm.edit_bones.new(bone_name)
    b.head = Vector(head)
    b.tail = Vector(tail)

# Then set parents (all bones exist now)
for bone_name, _, _, parent_name in BONE_DEFS:
    if parent_name is not None:
        arm.edit_bones[bone_name].parent = arm.edit_bones[parent_name]

bpy.ops.object.mode_set(mode='OBJECT')

# Add armature to collection
character_utils.add_to_collection(arm_obj, 'Aarav')

# ---------------------------------------------------------------------------
# Parent all mesh objects to armature
# ---------------------------------------------------------------------------
for obj in mesh_objects:
    character_utils.parent_to_armature(obj, arm_obj)

# ---------------------------------------------------------------------------
# Expressions stored as JSON custom property
# ---------------------------------------------------------------------------
expressions = {
    "neutral": {},
    "happy": {
        "Mouth":   {"scale": [1.1, 1.0, 0.8]},
        "Eye_L":   {"scale": [1.0, 1.0, 0.75]},
        "Eye_R":   {"scale": [1.0, 1.0, 0.75]},
    },
    "surprised": {
        "Eye_L":     {"scale": [1.2, 1.0, 1.2]},
        "Eye_R":     {"scale": [1.2, 1.0, 1.2]},
        "Eyebrow_L": {"location": [0, 0, 0.03]},
        "Eyebrow_R": {"location": [0, 0, 0.03]},
        "Mouth":     {"scale": [0.8, 1.0, 1.4]},
    },
    "sad": {
        "Mouth":     {"scale": [1.0, 1.0, 0.7]},
        "Eyebrow_L": {"location": [0, 0, -0.02]},
        "Eyebrow_R": {"location": [0, 0, -0.02]},
    },
}
arm_obj['expressions'] = json.dumps(expressions)

# ---------------------------------------------------------------------------
# Save .blend
# ---------------------------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"[Aarav] Saved blend file: {blend_path}")

# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
generation_time = time.time() - start_time

total_polygons = character_utils.count_polygons('Aarav')
mesh_count = sum(1 for obj in bpy.data.collections['Aarav'].all_objects if obj.type == 'MESH')
total_objects = len(list(bpy.data.collections['Aarav'].all_objects))
total_materials = len([m for m in bpy.data.materials if m.name.startswith('Aarav_')])

# ---------------------------------------------------------------------------
# character.json
# ---------------------------------------------------------------------------
import datetime
character_data = {
    "character_id": "aarav",
    "character_name": "Aarav",
    "version": "1.0.0",
    "created_date": datetime.datetime.utcnow().isoformat() + "Z",
    "blend_file": "aarav.blend",
    "statistics": {
        "total_polygons": total_polygons,
        "total_objects": mesh_count,
        "total_materials": total_materials,
        "armature_bones": 20,
        "generation_time_s": round(generation_time, 3),
        "peak_memory_mb": 0.0,
    },
    "expressions": ["neutral", "happy", "surprised", "sad"],
    "poses": ["rest", "wave", "dance"],
    "previews": {
        "front":             "previews/front.png",
        "side":              "previews/side.png",
        "three_quarter":     "previews/three_quarter.png",
        "wave_pose":         "previews/wave_pose.png",
        "happy_expression":  "previews/happy_expression.png",
    },
    "materials": {
        "Aarav_Skin":      "#C68642",
        "Aarav_Shirt":     "#2196F3",
        "Aarav_Trousers":  "#1A237E",
        "Aarav_Shoes":     "#EEEEEE",
        "Aarav_Hair":      "#3E2723",
        "Aarav_EyeWhite":  "#FFFFFF",
        "Aarav_Iris":      "#4E342E",
        "Aarav_Mouth":     "#E57373",
    },
    "bones": [
        "root", "hips", "spine", "chest", "neck", "head",
        "shoulder_L", "upper_arm_L", "forearm_L", "hand_L",
        "shoulder_R", "upper_arm_R", "forearm_R", "hand_R",
        "thigh_L", "shin_L", "foot_L",
        "thigh_R", "shin_R", "foot_R",
    ],
}

json_path = os.path.join(base_dir, 'character.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(character_data, f, indent=2)
print(f"[Aarav] Saved character.json: {json_path}")

# ---------------------------------------------------------------------------
# Summary to stdout
# ---------------------------------------------------------------------------
summary = {
    "status": "success",
    "character": "Aarav",
    "blend_file": blend_path,
    "character_json": json_path,
    "statistics": character_data["statistics"],
}
print(json.dumps(summary, indent=2))
