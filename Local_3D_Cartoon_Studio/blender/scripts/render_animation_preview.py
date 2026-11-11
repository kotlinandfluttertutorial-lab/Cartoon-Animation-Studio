"""
render_animation_preview.py - Renders 5 animation preview PNGs for Stage 4.1.

Usage:
    blender --background --python render_animation_preview.py -- <output_dir>

Output (5 PNGs at 640x360 BLENDER_WORKBENCH):
    <output_dir>/aarav_idle.png          - Aarav frame 12 of AARAV_IDLE
    <output_dir>/aarav_walk.png          - Aarav frame 1  of AARAV_WALK
    <output_dir>/aanya_idle.png          - Aanya frame 12 of AANYA_IDLE
    <output_dir>/aanya_walk.png          - Aanya frame 1  of AANYA_WALK
    <output_dir>/both_characters_animation.png  - Both side-by-side, frame 1 of WALK

Rendering technique:
    Uses the same Option B (direct mesh repositioning) approach from
    render_character_preview.py that produced the working wave pose preview.
    For each animation frame:
      1. Set pose bone rotations from the action's fcurves at the target frame.
      2. Evaluate depsgraph so bone world matrices are updated.
      3. Move each mesh object to the evaluated bone midpoint in world space.
      4. Render.
      5. Restore mesh locations and clear bone rotations.

    The blend files loaded are the stage4 working copies that contain the
    AARAV_IDLE, AARAV_WALK, AANYA_IDLE, AANYA_WALK actions created by
    create_animations.py.
"""

import sys
import os
import math

if '--' in sys.argv:
    args = sys.argv[sys.argv.index('--') + 1:]
else:
    print('Usage: blender --background --python render_animation_preview.py -- <output_dir>')
    sys.exit(1)

if len(args) < 1:
    print('ERROR: need <output_dir>')
    sys.exit(1)

output_dir = args[0]
os.makedirs(output_dir, exist_ok=True)

import bpy
import mathutils

# ---------------------------------------------------------------------------
# Paths to stage4 blend files
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))   # blender/scripts
_BLENDER_DIR = os.path.dirname(_SCRIPTS_DIR)                  # blender/
_STUDIO_DIR = os.path.dirname(_BLENDER_DIR)                   # Local_3D_Cartoon_Studio
_CHARACTERS_DIR = os.path.join(_STUDIO_DIR, 'blender', 'assets', 'characters')

AARAV_BLEND = os.path.join(_CHARACTERS_DIR, 'aarav', 'aarav_stage4.blend')
AANYA_BLEND = os.path.join(_CHARACTERS_DIR, 'aanya', 'aanya_stage4.blend')

for p in [AARAV_BLEND, AANYA_BLEND]:
    if not os.path.isfile(p):
        print(f'ERROR: blend file not found: {p}')
        sys.exit(1)

# ---------------------------------------------------------------------------
# Render setup helpers
# ---------------------------------------------------------------------------

def setup_scene():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.film_transparent = False
    shading = scene.display.shading
    shading.light = 'STUDIO'
    shading.color_type = 'MATERIAL'
    shading.show_shadows = True
    shading.show_cavity = True
    try:
        shading.show_object_outline = True
    except AttributeError:
        pass
    return scene


def set_camera(cam_obj, pos, target):
    cam_obj.location = mathutils.Vector(pos)
    direction = mathutils.Vector(target) - mathutils.Vector(pos)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()


def make_camera(scene):
    cam_data = bpy.data.cameras.new('RenderCam')
    cam_data.lens = 50
    cam_obj = bpy.data.objects.new('RenderCam', cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    return cam_obj


def render_to(scene, filepath):
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# Animation pose helpers (Option B — same as wave pose in render_character_preview.py)
# ---------------------------------------------------------------------------

def _get_bone_rotations_at_frame(action, frame):
    """
    Sample all fcurves in an action at a given frame.
    Returns dict: {(data_path, array_index): value}
    """
    result = {}
    for fc in action.fcurves:
        val = fc.evaluate(frame)
        result[(fc.data_path, fc.array_index)] = val
    return result


def _apply_pose_from_action(arm_obj, action, frame):
    """
    Apply the pose defined by `action` at `frame` to the armature's pose bones.
    Sets rotation_euler values for each keyed bone channel.
    """
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')

    # First reset all bones to identity
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = mathutils.Euler((0.0, 0.0, 0.0), 'XYZ')
        pb.location = mathutils.Vector((0.0, 0.0, 0.0))
        pb.scale = mathutils.Vector((1.0, 1.0, 1.0))

    # Sample and apply each fcurve channel
    for fc in action.fcurves:
        # Only handle pose bone rotation_euler channels
        if 'rotation_euler' not in fc.data_path:
            continue
        # Extract bone name from data_path like: pose.bones["spine"].rotation_euler
        try:
            bone_name = fc.data_path.split('"')[1]
        except IndexError:
            continue
        pb = arm_obj.pose.bones.get(bone_name)
        if pb is None:
            continue
        pb.rotation_mode = 'XYZ'
        val = fc.evaluate(frame)
        pb.rotation_euler[fc.array_index] = val

    bpy.ops.object.mode_set(mode='OBJECT')


def _bone_world_midpoint(arm_eval, bone_name):
    """World-space midpoint of an evaluated pose bone (head+tail)/2."""
    pb = arm_eval.pose.bones.get(bone_name)
    if pb is None:
        return None
    mw = arm_eval.matrix_world
    head_world = mw @ pb.head
    tail_world = mw @ pb.tail
    return (head_world + tail_world) * 0.5


# Mapping from bone name to list of mesh suffixes it drives
# (same logic as _BONE_MESH_MAP in render_character_preview.py, extended to legs)
_BONE_TO_MESH = {
    # Spine chain
    'spine':       ['Spine'],
    'chest':       ['Chest'],
    'neck':        ['Neck'],
    'head':        ['Head'],
    # Arms - Left
    'shoulder_L':  ['Shoulder_L'],
    'upper_arm_L': ['UpperArm_L'],
    'forearm_L':   ['LowerArm_L'],
    'hand_L':      ['Hand_L'],
    # Arms - Right
    'shoulder_R':  ['Shoulder_R'],
    'upper_arm_R': ['UpperArm_R'],
    'forearm_R':   ['LowerArm_R'],
    'hand_R':      ['Hand_R'],
    # Legs - Left
    'thigh_L':     ['UpperLeg_L', 'Thigh_L'],
    'shin_L':      ['LowerLeg_L', 'Shin_L'],
    'foot_L':      ['Foot_L'],
    # Legs - Right
    'thigh_R':     ['UpperLeg_R', 'Thigh_R'],
    'shin_R':      ['LowerLeg_R', 'Shin_R'],
    'foot_R':      ['Foot_R'],
}


def apply_animation_pose(arm_obj, action, frame, char_prefix):
    """
    Apply animation pose at `frame` and reposition mesh objects via Option B.
    Returns saved_locations dict for restoration.
    """
    # Step 1: apply bone rotations from action at target frame
    _apply_pose_from_action(arm_obj, action, frame)

    # Step 2: force depsgraph evaluation
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    arm_eval = arm_obj.evaluated_get(depsgraph)

    saved = {}

    # Step 3: for each bone that has a channel in this action, move mesh to bone midpoint
    # Collect which bones are actually keyed in this action
    keyed_bones = set()
    for fc in action.fcurves:
        if 'rotation_euler' in fc.data_path:
            try:
                bone_name = fc.data_path.split('"')[1]
                keyed_bones.add(bone_name)
            except IndexError:
                pass

    for bone_name in keyed_bones:
        mesh_suffixes = _BONE_TO_MESH.get(bone_name, [])
        midpoint = _bone_world_midpoint(arm_eval, bone_name)
        if midpoint is None:
            continue
        for suffix in mesh_suffixes:
            obj_name = f'{char_prefix}_{suffix}'
            obj = bpy.data.objects.get(obj_name)
            if obj is None:
                continue
            saved[obj_name] = obj.location.copy()
            obj.location = midpoint

    # Step 4: update scene after mesh moves
    bpy.context.view_layer.update()

    return saved


def restore_pose(arm_obj, saved_locations):
    """Restore mesh locations and reset all bone rotations."""
    for obj_name, orig_loc in saved_locations.items():
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.location = orig_loc

    if arm_obj is not None:
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='POSE')
        for pb in arm_obj.pose.bones:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = mathutils.Euler((0.0, 0.0, 0.0), 'XYZ')
            pb.location = mathutils.Vector((0.0, 0.0, 0.0))
            pb.scale = mathutils.Vector((1.0, 1.0, 1.0))
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.context.view_layer.update()


# ===========================================================================
# Render function for a single character
# ===========================================================================

def render_character_animation(blend_file, char_name, renders):
    """
    Open blend_file, apply animation poses, render specified frames.

    renders: list of (action_name, frame, output_filename)
    """
    bpy.ops.wm.open_mainfile(filepath=blend_file)

    scene = setup_scene()
    cam_obj = make_camera(scene)

    # Front view camera — characters face +Y, so camera must be at +Y looking toward -Y
    # This is the same direction as the garden scene cameras
    set_camera(cam_obj, (0, 4.0, 0.80), (0, 0, 0.80))

    arm_name = f'{char_name}_Armature'
    arm_obj = bpy.data.objects.get(arm_name)
    if arm_obj is None:
        print(f'WARNING: {arm_name} not found')
        return

    for action_name, frame, out_filename in renders:
        action = bpy.data.actions.get(action_name)
        if action is None:
            print(f'WARNING: action {action_name!r} not found in {blend_file}')
            continue

        print(f'  Rendering {action_name} frame {frame} -> {out_filename}')
        saved = apply_animation_pose(arm_obj, action, frame, char_name)
        render_to(scene, os.path.join(output_dir, out_filename))
        restore_pose(arm_obj, saved)


# ===========================================================================
# Render both characters side by side (combined scene)
# ===========================================================================

def render_both_characters(frame=1):
    """
    Load both characters into a single scene, place them side by side, render.
    Aarav at X=-0.8, Aanya at X=+0.8
    """
    # Start with Aarav's blend file
    bpy.ops.wm.open_mainfile(filepath=AARAV_BLEND)

    scene = setup_scene()

    # Append all objects from Aanya's blend file
    aanya_char_dir = os.path.join(_CHARACTERS_DIR, 'aanya')
    with bpy.data.libraries.load(AANYA_BLEND, link=False) as (src, dst):
        dst.objects = [name for name in src.objects if 'Aanya' in name]

    # Link appended objects to scene
    for obj in bpy.data.objects:
        if obj.name.startswith('Aanya') and obj.name not in [o.name for o in scene.collection.objects]:
            scene.collection.objects.link(obj)

    # Offset characters: Aarav at X=-0.8, Aanya at X=+0.8
    for obj in bpy.data.objects:
        if obj.name.startswith('Aarav'):
            obj.location.x -= 0.8
        elif obj.name.startswith('Aanya'):
            obj.location.x += 0.8

    # Camera wider for two characters: pull back to X=0, Y=-5.5 for side-by-side
    cam_data = bpy.data.cameras.new('RenderCamBoth')
    cam_data.lens = 40   # slightly wider FOV to fit two characters
    cam_obj = bpy.data.objects.new('RenderCamBoth', cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    set_camera(cam_obj, (0, 5.5, 0.80), (0, 0, 0.80))

    # Apply walk animation frame 1 to Aarav
    aarav_arm = bpy.data.objects.get('Aarav_Armature')
    aanya_arm = bpy.data.objects.get('Aanya_Armature')

    saved_aarav = {}
    saved_aanya = {}

    aarav_walk = bpy.data.actions.get('AARAV_WALK')
    aanya_walk = bpy.data.actions.get('AANYA_WALK')

    if aarav_arm and aarav_walk:
        saved_aarav = apply_animation_pose(aarav_arm, aarav_walk, frame, 'Aarav')
    if aanya_arm and aanya_walk:
        saved_aanya = apply_animation_pose(aanya_arm, aanya_walk, frame, 'Aanya')

    out_path = os.path.join(output_dir, 'both_characters_animation.png')
    scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f'  Rendered both_characters_animation.png')

    # Restore
    if aarav_arm:
        restore_pose(aarav_arm, saved_aarav)
    if aanya_arm:
        restore_pose(aanya_arm, saved_aanya)


# ===========================================================================
# Main render sequence
# ===========================================================================

print('=== RENDER ANIMATION PREVIEWS ===')

# --- Aarav renders ---
print('Rendering Aarav...')
render_character_animation(
    AARAV_BLEND, 'Aarav',
    [
        ('AARAV_IDLE', 12, 'aarav_idle.png'),
        ('AARAV_WALK', 1,  'aarav_walk.png'),
    ]
)

# --- Aanya renders ---
print('Rendering Aanya...')
render_character_animation(
    AANYA_BLEND, 'Aanya',
    [
        ('AANYA_IDLE', 12, 'aanya_idle.png'),
        ('AANYA_WALK', 1,  'aanya_walk.png'),
    ]
)

# --- Both characters ---
print('Rendering both characters...')
render_both_characters(frame=1)

# ---------------------------------------------------------------------------
# Verify outputs
# ---------------------------------------------------------------------------
print()
print('=== OUTPUT VERIFICATION ===')
expected = [
    'aarav_idle.png',
    'aarav_walk.png',
    'aanya_idle.png',
    'aanya_walk.png',
    'both_characters_animation.png',
]

all_ok = True
for fname in expected:
    fpath = os.path.join(output_dir, fname)
    if os.path.isfile(fpath):
        size = os.path.getsize(fpath)
        status = 'OK' if size > 20480 else 'SMALL'
        print(f'  {fname}: {size} bytes [{status}]')
        if size <= 20480:
            all_ok = False
    else:
        print(f'  {fname}: MISSING')
        all_ok = False

if all_ok:
    print('RENDER_ANIMATION_PREVIEW_OK')
else:
    print('RENDER_ANIMATION_PREVIEW_WARNINGS')

sys.exit(0)
