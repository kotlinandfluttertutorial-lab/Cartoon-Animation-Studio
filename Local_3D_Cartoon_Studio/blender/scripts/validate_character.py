"""
validate_character.py - Validates a generated character .blend file.

Usage:
    blender --background --factory-startup --python validate_character.py -- <blend_file> <output_json>
"""
import sys
import os
import json
import bpy

if '--' in sys.argv:
    args = sys.argv[sys.argv.index('--') + 1:]
else:
    print('Usage: blender --background --python validate_character.py -- <blend_file> <output_json>')
    sys.exit(1)

blend_file = args[0]
output_json = args[1]

bpy.ops.wm.open_mainfile(filepath=blend_file)

# Determine prefix
prefix = None
for coll in bpy.data.collections:
    if coll.name in ('Aarav', 'Aanya'):
        prefix = coll.name
        break

checks = {}
statistics = {}

# 1. collection
checks['collection_exists'] = prefix is not None

# 2. armature
arm_name = f'{prefix}_Armature' if prefix else 'Unknown_Armature'
arm_obj = bpy.data.objects.get(arm_name)
checks['armature_exists'] = arm_obj is not None

# 3. bones
REQUIRED_BONES = ['root', 'hips', 'spine', 'chest', 'neck', 'head',
    'shoulder_L', 'upper_arm_L', 'forearm_L', 'hand_L',
    'shoulder_R', 'upper_arm_R', 'forearm_R', 'hand_R',
    'thigh_L', 'shin_L', 'foot_L', 'thigh_R', 'shin_R', 'foot_R']
missing_bones = []
if arm_obj and arm_obj.type == 'ARMATURE':
    bone_names = [b.name for b in arm_obj.data.bones]
    missing_bones = [b for b in REQUIRED_BONES if b not in bone_names]
checks['all_bones_present'] = len(missing_bones) == 0
checks['missing_bones'] = missing_bones

# 4. required objects
REQUIRED_SUFFIXES = ['Head', 'Torso', 'Neck', 'UpperLeg_L', 'UpperLeg_R', 'LowerLeg_L', 'LowerLeg_R', 'Foot_L', 'Foot_R', 'Eye_L', 'Eye_R', 'Mouth']
missing_objects = []
if prefix:
    for suffix in REQUIRED_SUFFIXES:
        full_name = f'{prefix}_{suffix}'
        if bpy.data.objects.get(full_name) is None:
            missing_objects.append(full_name)
checks['required_objects_present'] = len(missing_objects) == 0
checks['missing_objects'] = missing_objects

# 5. materials
default_color = (0.8, 0.8, 0.8, 1.0)
mat_valid = True
for mat in bpy.data.materials:
    if mat.name.startswith(prefix or '') and mat.diffuse_color[:] == default_color:
        mat_valid = False
checks['materials_valid'] = mat_valid

# 6. height
coll = bpy.data.collections.get(prefix or '')
min_z, max_z = float('inf'), float('-inf')
if coll:
    for obj in coll.all_objects:
        if obj.type == 'MESH':
            for v in obj.data.vertices:
                wco = obj.matrix_world @ v.co
                min_z = min(min_z, wco.z)
                max_z = max(max_z, wco.z)
height = max_z - min_z if min_z != float('inf') else 0
checks['height_valid'] = 1.5 <= height <= 2.5

# 7. ground level
checks['ground_level_valid'] = abs(min_z) <= 0.1 if min_z != float('inf') else False

# statistics
total_polys = 0
total_objs = 0
if coll:
    for obj in coll.all_objects:
        if obj.type == 'MESH':
            total_polys += len(obj.data.polygons)
            total_objs += 1
statistics['poly_count'] = total_polys
statistics['object_count'] = total_objs

overall = 'PASS' if all(v is True or (isinstance(v, list) and len(v) == 0) for k, v in checks.items() if k not in ('missing_bones', 'missing_objects')) else 'FAIL'
if missing_bones or missing_objects:
    overall = 'FAIL'

result = {
    'character': prefix or 'Unknown',
    'blend_file': blend_file,
    'overall': overall,
    'checks': checks,
    'statistics': statistics
}

with open(output_json, 'w') as f:
    json.dump(result, f, indent=2)

print(json.dumps(result))
sys.exit(0 if overall == 'PASS' else 1)
