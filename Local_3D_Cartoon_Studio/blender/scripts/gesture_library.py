"""
gesture_library.py - Creates gesture animation actions for Aarav and Aanya.

Usage (Blender background mode):
    blender --background <blend_file> --python gesture_library.py -- <blend_file> <character_name>

Arguments after '--':
    blend_file      : path to aarav_stage4.blend or aanya_stage4.blend
    character_name  : 'Aarav' or 'Aanya'

Actions created (idempotent — existing actions with same names are replaced):
    <NAME>_WAVE      (24 frames) — arm wave greeting
    <NAME>_POINT     (20 frames) — pointing gesture
    <NAME>_NOD       (16 frames) — head nod
    <NAME>_GREETING  (48 frames) — composite wave + idle breathing

Also recreates WALK action with improved keyframes (Fix 3):
    <NAME>_WALK      (36 frames) — improved walk with hip sway, wider thigh swing

Prints 'GESTURES_CREATED_OK' on success.
"""

import sys
import os
import math

if '--' in sys.argv:
    args = sys.argv[sys.argv.index('--') + 1:]
else:
    print('Usage: blender --background <blend_file> --python gesture_library.py -- <blend_file> <character_name>')
    sys.exit(1)

if len(args) < 2:
    print('ERROR: need <blend_file> and <character_name>')
    sys.exit(1)

blend_file = args[0]
character_name = args[1]   # 'Aarav' or 'Aanya'

import bpy

# ---------------------------------------------------------------------------
# Open the working copy
# ---------------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=blend_file)

scene = bpy.context.scene
scene.render.fps = 24

arm_name = f'{character_name}_Armature'
arm_obj = bpy.data.objects.get(arm_name)
if arm_obj is None:
    print(f'ERROR: Armature object {arm_name!r} not found in {blend_file}')
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers (same as create_animations.py for consistency)
# ---------------------------------------------------------------------------

def get_or_create_action(name):
    """Get or create an action, purging any existing one with the same name."""
    existing = bpy.data.actions.get(name)
    if existing is not None:
        for obj in bpy.data.objects:
            if obj.animation_data:
                for track in list(obj.animation_data.nla_tracks):
                    for strip in list(track.strips):
                        if strip.action == existing:
                            track.strips.remove(strip)
                    if len(track.strips) == 0:
                        obj.animation_data.nla_tracks.remove(track)
                if obj.animation_data.action == existing:
                    obj.animation_data.action = None
        bpy.data.actions.remove(existing)
    action = bpy.data.actions.new(name=name)
    return action


def insert_key(action, data_path, array_index, frame, value):
    """Insert a keyframe into an action's fcurve for a pose bone channel."""
    fc = action.fcurves.find(data_path, index=array_index)
    if fc is None:
        fc = action.fcurves.new(
            data_path=data_path,
            index=array_index,
            action_group=data_path.split('"')[1]
        )
    kp = fc.keyframe_points.insert(frame=frame, value=value, options={'FAST'})
    kp.interpolation = 'BEZIER'


def bone_dp(bone_name):
    """Return the rotation_euler data_path for a bone."""
    return f'pose.bones["{bone_name}"].rotation_euler'


# ===========================================================================
# WAVE action (24 frames)
# ===========================================================================
# Frame  1: upper_arm_R X=0,    Y=0, Z=0     (rest)
# Frame  6: upper_arm_R X=-1.4, Y=0, Z=0.3  (arm raised)
# Frame 10: hand_R Z=+0.3                    (hand tilted one way)
# Frame 14: hand_R Z=-0.3                    (hand tilted other way)
# Frame 18: upper_arm_R X=-1.4              (still raised)
# Frame 24: upper_arm_R X=0, hand_R Z=0     (return to rest)
# ===========================================================================

wave_name = f'{character_name.upper()}_WAVE'
wave = get_or_create_action(wave_name)
wave.use_cyclic = False

dp_ua_r = bone_dp('upper_arm_R')
dp_hand_r = bone_dp('hand_R')

# upper_arm_R X
insert_key(wave, dp_ua_r, 0, 1,  0.0)
insert_key(wave, dp_ua_r, 0, 6,  -1.4)
insert_key(wave, dp_ua_r, 0, 18, -1.4)
insert_key(wave, dp_ua_r, 0, 24, 0.0)

# upper_arm_R Z (slight rotation when raised)
insert_key(wave, dp_ua_r, 2, 1,  0.0)
insert_key(wave, dp_ua_r, 2, 6,  0.3)
insert_key(wave, dp_ua_r, 2, 24, 0.0)

# hand_R Z (wave motion)
insert_key(wave, dp_hand_r, 2, 1,  0.0)
insert_key(wave, dp_hand_r, 2, 6,  0.0)
insert_key(wave, dp_hand_r, 2, 10, 0.3)
insert_key(wave, dp_hand_r, 2, 14, -0.3)
insert_key(wave, dp_hand_r, 2, 18, 0.0)
insert_key(wave, dp_hand_r, 2, 24, 0.0)

wave.frame_range = (1, 24)
wave.frame_start = 1
wave.frame_end = 24
wave.use_fake_user = True  # prevent orphan purge on load

print(f'Created action: {wave_name}')
wave_kf = sum(len(fc.keyframe_points) for fc in wave.fcurves)
print(f'  Keyframe points: {wave_kf}  Frame range: 1-24')


# ===========================================================================
# POINT action (20 frames)
# ===========================================================================
# Frame  1: rest (all zeros)
# Frame  6: upper_arm_R X=-0.8, Y=0, Z=-0.2 (arm raised forward)
# Frame  8: forearm_R X=-0.3                 (slight elbow bend)
# Frame 15: hold (same as frame 8)
# Frame 20: return to rest (all zeros)
# ===========================================================================

point_name = f'{character_name.upper()}_POINT'
point = get_or_create_action(point_name)
point.use_cyclic = False

dp_fa_r = bone_dp('forearm_R')

# upper_arm_R X
insert_key(point, dp_ua_r, 0, 1,  0.0)
insert_key(point, dp_ua_r, 0, 6,  -0.8)
insert_key(point, dp_ua_r, 0, 8,  -0.8)
insert_key(point, dp_ua_r, 0, 15, -0.8)
insert_key(point, dp_ua_r, 0, 20, 0.0)

# upper_arm_R Z
insert_key(point, dp_ua_r, 2, 1,  0.0)
insert_key(point, dp_ua_r, 2, 6,  -0.2)
insert_key(point, dp_ua_r, 2, 15, -0.2)
insert_key(point, dp_ua_r, 2, 20, 0.0)

# forearm_R X (elbow bend)
insert_key(point, dp_fa_r, 0, 1,  0.0)
insert_key(point, dp_fa_r, 0, 6,  0.0)
insert_key(point, dp_fa_r, 0, 8,  -0.3)
insert_key(point, dp_fa_r, 0, 15, -0.3)
insert_key(point, dp_fa_r, 0, 20, 0.0)

point.frame_range = (1, 20)
point.frame_start = 1
point.frame_end = 20
point.use_fake_user = True  # prevent orphan purge on load

print(f'Created action: {point_name}')
point_kf = sum(len(fc.keyframe_points) for fc in point.fcurves)
print(f'  Keyframe points: {point_kf}  Frame range: 1-20')


# ===========================================================================
# NOD action (16 frames)
# ===========================================================================
# Frame  1: head X=0    (neutral)
# Frame  4: head X=0.3  (nod down)
# Frame  8: head X=-0.1 (back up slightly past neutral)
# Frame 12: head X=0.2  (nod down again)
# Frame 16: head X=0    (neutral)
# ===========================================================================

nod_name = f'{character_name.upper()}_NOD'
nod = get_or_create_action(nod_name)
nod.use_cyclic = False

dp_head = bone_dp('head')

insert_key(nod, dp_head, 0, 1,  0.0)
insert_key(nod, dp_head, 0, 4,  0.3)
insert_key(nod, dp_head, 0, 8,  -0.1)
insert_key(nod, dp_head, 0, 12, 0.2)
insert_key(nod, dp_head, 0, 16, 0.0)

nod.frame_range = (1, 16)
nod.frame_start = 1
nod.frame_end = 16
nod.use_fake_user = True  # prevent orphan purge on load

print(f'Created action: {nod_name}')
nod_kf = sum(len(fc.keyframe_points) for fc in nod.fcurves)
print(f'  Keyframe points: {nod_kf}  Frame range: 1-16')


# ===========================================================================
# GREETING action (48 frames)
# Composite: raise arm → wave → lower arm → idle breathing
#
# Frames 1-6:   upper_arm_R X rises 0 → -1.4 (arm raises)
# Frames 6-18:  wave motion: hand_R Z alternates at 10, 14; arm stays up
# Frames 18-24: upper_arm_R X returns -1.4 → 0 (arm lowers)
# Frames 24-48: idle movement
#               spine Y: +0.03 at 36, 0 at 48
#               head Z:  +0.02 at 36, 0 at 48
# ===========================================================================

greet_name = f'{character_name.upper()}_GREETING'
greet = get_or_create_action(greet_name)
greet.use_cyclic = False

dp_spine = bone_dp('spine')

# upper_arm_R X
insert_key(greet, dp_ua_r, 0, 1,  0.0)
insert_key(greet, dp_ua_r, 0, 6,  -1.4)
insert_key(greet, dp_ua_r, 0, 18, -1.4)
insert_key(greet, dp_ua_r, 0, 24, 0.0)
insert_key(greet, dp_ua_r, 0, 48, 0.0)

# upper_arm_R Z
insert_key(greet, dp_ua_r, 2, 1,  0.0)
insert_key(greet, dp_ua_r, 2, 6,  0.3)
insert_key(greet, dp_ua_r, 2, 24, 0.0)
insert_key(greet, dp_ua_r, 2, 48, 0.0)

# hand_R Z (wave)
insert_key(greet, dp_hand_r, 2, 1,  0.0)
insert_key(greet, dp_hand_r, 2, 6,  0.0)
insert_key(greet, dp_hand_r, 2, 10, 0.3)
insert_key(greet, dp_hand_r, 2, 14, -0.3)
insert_key(greet, dp_hand_r, 2, 18, 0.0)
insert_key(greet, dp_hand_r, 2, 24, 0.0)
insert_key(greet, dp_hand_r, 2, 48, 0.0)

# spine Y (idle breathing in second half)
insert_key(greet, dp_spine, 1, 1,  0.0)
insert_key(greet, dp_spine, 1, 24, 0.0)
insert_key(greet, dp_spine, 1, 36, 0.03)
insert_key(greet, dp_spine, 1, 48, 0.0)

# head Z (idle sway in second half)
insert_key(greet, dp_head, 2, 1,  0.0)
insert_key(greet, dp_head, 2, 24, 0.0)
insert_key(greet, dp_head, 2, 36, 0.02)
insert_key(greet, dp_head, 2, 48, 0.0)

greet.frame_range = (1, 48)
greet.frame_start = 1
greet.frame_end = 48
greet.use_fake_user = True  # prevent orphan purge on load

print(f'Created action: {greet_name}')
greet_kf = sum(len(fc.keyframe_points) for fc in greet.fcurves)
print(f'  Keyframe points: {greet_kf}  Frame range: 1-48')


# ===========================================================================
# Improved WALK action (Fix 3) — recreate with:
#   - thigh swing +-0.5 rad (wider than original +-0.4)
#   - hips bone Z +-0.1 rad hip sway
#   - spine Y counter-rotation +-0.02 rad (out of phase)
#   - shin angles unchanged (keeps natural knee bend)
# ===========================================================================

walk_name = f'{character_name.upper()}_WALK'
walk = get_or_create_action(walk_name)
walk.use_cyclic = True

def walk_key(bone_name, axis_index, keyframes):
    dp = f'pose.bones["{bone_name}"].rotation_euler'
    for frame, val in keyframes:
        insert_key(walk, dp, axis_index, frame, val)

# thigh_L X — wider swing +-0.5 (Fix 3)
walk_key('thigh_L', 0, [(1, -0.5), (9, 0.0), (18, 0.5), (27, 0.0), (36, -0.5)])

# thigh_R X — wider swing +-0.5 (Fix 3)
walk_key('thigh_R', 0, [(1, 0.5), (9, 0.0), (18, -0.5), (27, 0.0), (36, 0.5)])

# upper_arm_L X — opposing arm swing
walk_key('upper_arm_L', 0, [(1, 0.3), (9, 0.0), (18, -0.3), (27, 0.0), (36, 0.3)])

# upper_arm_R X
walk_key('upper_arm_R', 0, [(1, -0.3), (9, 0.0), (18, 0.3), (27, 0.0), (36, -0.3)])

# shin_L X (natural knee bend)
walk_key('shin_L', 0, [(1, -0.2), (9, 0.0), (18, 0.1), (27, 0.0), (36, -0.2)])

# shin_R X
walk_key('shin_R', 0, [(1, 0.1), (9, 0.0), (18, -0.2), (27, 0.0), (36, 0.1)])

# hips Z — hip sway (Fix 3)
walk_key('hips', 2, [(1, 0.1), (9, 0.0), (18, -0.1), (27, 0.0), (36, 0.1)])

# spine Y — counter-rotation out of phase (Fix 3)
walk_key('spine', 1, [(1, -0.02), (9, 0.0), (18, 0.02), (27, 0.0), (36, -0.02)])

walk.frame_range = (1, 36)
walk.frame_start = 1
walk.frame_end = 36
walk.use_fake_user = True  # prevent orphan purge on load

print(f'Recreated action: {walk_name} (improved — Fix 3)')
walk_kf = sum(len(fc.keyframe_points) for fc in walk.fcurves)
print(f'  Keyframe points: {walk_kf}  Frame range: 1-36')


# ===========================================================================
# Leave active action as None to avoid NLA conflicts on save
# ===========================================================================
if arm_obj.animation_data:
    arm_obj.animation_data.action = None

# ===========================================================================
# Save working copy
# ===========================================================================
bpy.ops.wm.save_mainfile(filepath=blend_file)

print()
print('=== GESTURE LIBRARY SUMMARY ===')
print(f'Character : {character_name}')
print(f'Blend file: {blend_file}')
print(f'Actions   : {wave_name}, {point_name}, {nod_name}, {greet_name}, {walk_name} (improved)')
print(f'GESTURES_CREATED_OK')
sys.exit(0)
