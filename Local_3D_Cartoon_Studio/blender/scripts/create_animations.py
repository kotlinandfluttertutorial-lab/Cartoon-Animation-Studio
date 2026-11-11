"""
create_animations.py - Creates IDLE and WALK animation actions in a stage4 character blend file.

Usage (Blender background mode):
    blender --background <blend_file> --python create_animations.py -- <blend_file> <character_name>

Arguments after '--':
    blend_file      : path to aarav_stage4.blend or aanya_stage4.blend
    character_name  : 'Aarav' or 'Aanya' (matches armature object name <name>_Armature)

Animation actions created:
    <NAME>_IDLE  - 48 frames (2 s at 24 fps), looping subtle sway
    <NAME>_WALK  - 36 frames (1.5 s at 24 fps), looping stride cycle

Idempotent: running twice replaces (removes and recreates) existing actions with
the same names rather than duplicating them.

Bone channels are keyed as pose bone rotation_euler on the armature object.
The mesh objects use rigid OBJECT parenting and are therefore animated via
the Option B technique (direct mesh repositioning) at render time — see
render_animation_preview.py.
"""

import sys
import os
import math

if '--' in sys.argv:
    args = sys.argv[sys.argv.index('--') + 1:]
else:
    print('Usage: blender --background <blend_file> --python create_animations.py -- <blend_file> <character_name>')
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
# Helper: get or create an action, purging any existing one with the same name
# to ensure idempotency
# ---------------------------------------------------------------------------
def get_or_create_action(name):
    existing = bpy.data.actions.get(name)
    if existing is not None:
        # Unlink from NLA strips first so we can safely remove it
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


# ---------------------------------------------------------------------------
# Helper: insert a keyframe into an action's fcurve for a pose bone channel
#
# data_path : e.g. 'pose.bones["spine"].rotation_euler'
# array_index: 0=X, 1=Y, 2=Z
# frame      : frame number (int)
# value      : float value
# ---------------------------------------------------------------------------
def insert_key(action, data_path, array_index, frame, value):
    fc = action.fcurves.find(data_path, index=array_index)
    if fc is None:
        fc = action.fcurves.new(data_path=data_path, index=array_index, action_group=data_path.split('"')[1])
    kp = fc.keyframe_points.insert(frame=frame, value=value, options={'FAST'})
    kp.interpolation = 'BEZIER'


# ---------------------------------------------------------------------------
# Helper: apply action to armature via animation_data + NLA
# ---------------------------------------------------------------------------
def assign_action_to_armature(arm, action, track_name):
    if arm.animation_data is None:
        arm.animation_data_create()
    # Remove any existing NLA track with this name to stay idempotent
    for track in list(arm.animation_data.nla_tracks):
        if track.name == track_name:
            arm.animation_data.nla_tracks.remove(track)
    # Set as the active action
    arm.animation_data.action = action
    # Push to NLA
    track = arm.animation_data.nla_tracks.new()
    track.name = track_name
    strip = track.strips.new(name=action.name, start=1, action=action)
    strip.action_frame_start = 1
    strip.action_frame_end = action.frame_range[1]
    strip.frame_start = 1
    strip.frame_end = action.frame_range[1]
    try:
        strip.use_cyclic = True
    except AttributeError:
        pass  # Blender 4.x: cyclic repeat handled via action.use_cyclic


# ===========================================================================
# IDLE ACTION
# ===========================================================================
# 48 frames (2 s), looping subtle body sway.
#
# Frame  1: all bones (0,0,0)  — rest
# Frame 12: spine Y=+0.03, head Z=+0.02
# Frame 24: spine Y=0, head Z=0
# Frame 36: spine Y=-0.02, head Z=-0.02
# Frame 48: spine Y=0, head Z=0  (loops back to frame 1)
# ===========================================================================

idle_action_name = f'{character_name.upper()}_IDLE'
idle_action = get_or_create_action(idle_action_name)
idle_action.use_cyclic = True

# --- spine Y (index 1) ---
spine_dp = f'pose.bones["spine"].rotation_euler'
for frame, val in [(1, 0.0), (12, 0.03), (24, 0.0), (36, -0.02), (48, 0.0)]:
    insert_key(idle_action, spine_dp, 1, frame, val)

# --- head Z (index 2) ---
head_dp = f'pose.bones["head"].rotation_euler'
for frame, val in [(1, 0.0), (12, 0.02), (24, 0.0), (36, -0.02), (48, 0.0)]:
    insert_key(idle_action, head_dp, 2, frame, val)

# Set frame range
idle_action.frame_range = (1, 48)
idle_action.frame_start = 1
idle_action.frame_end = 48

assign_action_to_armature(arm_obj, idle_action, f'{character_name.upper()}_IDLE_NLA')

print(f'Created action: {idle_action_name}')
print(f'  Bone channels: spine (Y), head (Z)')
print(f'  Frame range: 1-48 (48 frames, 2.0 s at 24 fps)')
idle_kf_count = sum(len(fc.keyframe_points) for fc in idle_action.fcurves)
print(f'  Total keyframe points: {idle_kf_count}')

# ===========================================================================
# WALK ACTION
# ===========================================================================
# 36 frames (1.5 s), looping stride cycle with alternating leg/arm swing.
#
# Frame  1: thigh_L X=-0.4, thigh_R X=+0.4, upper_arm_L X=+0.3, upper_arm_R X=-0.3
# Frame  9: thigh_L X=0,    thigh_R X=0,    upper_arm_L X=0,    upper_arm_R X=0  (passing)
# Frame 18: thigh_L X=+0.4, thigh_R X=-0.4, upper_arm_L X=-0.3, upper_arm_R X=+0.3
# Frame 27: thigh_L X=0,    thigh_R X=0  (passing)
# Frame 36: same as frame 1 (loop)
#
# Shin bounce: shin_L/shin_R X follow thigh with slight trailing bend
#   When thigh is extended forward (negative X = forward) shin bends back X=-0.2
# ===========================================================================

walk_action_name = f'{character_name.upper()}_WALK'
walk_action = get_or_create_action(walk_action_name)
walk_action.use_cyclic = True

def walk_key(bone_name, axis_index, keyframes):
    """Insert keyframes for a bone channel in the walk action."""
    dp = f'pose.bones["{bone_name}"].rotation_euler'
    for frame, val in keyframes:
        insert_key(walk_action, dp, axis_index, frame, val)

# --- thigh_L X ---
walk_key('thigh_L', 0, [(1, -0.4), (9, 0.0), (18, 0.4), (27, 0.0), (36, -0.4)])

# --- thigh_R X ---
walk_key('thigh_R', 0, [(1, 0.4), (9, 0.0), (18, -0.4), (27, 0.0), (36, 0.4)])

# --- upper_arm_L X ---
walk_key('upper_arm_L', 0, [(1, 0.3), (9, 0.0), (18, -0.3), (27, 0.0), (36, 0.3)])

# --- upper_arm_R X ---
walk_key('upper_arm_R', 0, [(1, -0.3), (9, 0.0), (18, 0.3), (27, 0.0), (36, -0.3)])

# --- shin_L X: bends back (positive X) when thigh_L is forward (negative X)
#     Frame 1:  thigh_L forward → shin bends back a bit
#     Frame 9:  passing → shin straight
#     Frame 18: thigh_L back → shin slightly bent
#     Frame 27: passing → shin straight
#     Frame 36: same as 1
walk_key('shin_L', 0, [(1, -0.2), (9, 0.0), (18, 0.1), (27, 0.0), (36, -0.2)])

# --- shin_R X: opposite phase to shin_L
walk_key('shin_R', 0, [(1, 0.1), (9, 0.0), (18, -0.2), (27, 0.0), (36, 0.1)])

# Set frame range
walk_action.frame_range = (1, 36)
walk_action.frame_start = 1
walk_action.frame_end = 36

# Walk action goes into its own NLA track separate from idle
# But first remove the idle from active so walk becomes active
arm_obj.animation_data.action = walk_action

# Push walk to NLA too
track_walk = arm_obj.animation_data.nla_tracks.new()
track_walk.name = f'{character_name.upper()}_WALK_NLA'
strip_walk = track_walk.strips.new(name=walk_action.name, start=1, action=walk_action)
strip_walk.action_frame_start = 1
strip_walk.action_frame_end = walk_action.frame_range[1]
strip_walk.frame_start = 1
strip_walk.frame_end = walk_action.frame_range[1]
try:
    strip_walk.use_cyclic = True
except AttributeError:
    pass  # Blender 4.x: cyclic repeat handled via action.use_cyclic

print(f'Created action: {walk_action_name}')
print(f'  Bone channels: thigh_L, thigh_R, upper_arm_L, upper_arm_R, shin_L, shin_R')
print(f'  Frame range: 1-36 (36 frames, 1.5 s at 24 fps)')
walk_kf_count = sum(len(fc.keyframe_points) for fc in walk_action.fcurves)
print(f'  Total keyframe points: {walk_kf_count}')

# ===========================================================================
# Leave active action as None (avoid NLA conflicts on save)
# ===========================================================================
arm_obj.animation_data.action = None

# ===========================================================================
# Save working copy
# ===========================================================================
bpy.ops.wm.save_mainfile(filepath=blend_file)

print()
print('=== ANIMATION CREATION SUMMARY ===')
print(f'Character : {character_name}')
print(f'Blend file: {blend_file}')
print(f'Actions   : {idle_action_name} ({idle_kf_count} kf pts), {walk_action_name} ({walk_kf_count} kf pts)')
print(f'Bones keyed (idle) : spine, head')
print(f'Bones keyed (walk) : thigh_L, thigh_R, upper_arm_L, upper_arm_R, shin_L, shin_R')
print(f'FPS       : 24')
print(f'ANIMATIONS_CREATED_OK')
sys.exit(0)
