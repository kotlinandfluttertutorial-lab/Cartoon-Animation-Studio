"""
render_stage42_previews.py - Renders 8 Stage 4.2 preview PNGs.

Usage:
    blender --background --python render_stage42_previews.py -- <output_dir>

Output (8 PNGs at 640x360 BLENDER_WORKBENCH):
    <output_dir>/aarav_wave.png            - Aarav AARAV_WAVE frame 10
    <output_dir>/aanya_wave.png            - Aanya AANYA_WAVE frame 10
    <output_dir>/aarav_point.png           - Aarav AARAV_POINT frame 8
    <output_dir>/aanya_nod.png             - Aanya AANYA_NOD frame 4
    <output_dir>/greeting_interaction.png  - Combined: Aarav GREETING fr6, Aanya GREETING fr6
    <output_dir>/walk_together.png         - Combined: Aarav WALK fr1, Aanya WALK fr1
    <output_dir>/both_facing_camera.png    - Combined: Aarav IDLE fr12, Aanya IDLE fr12
    <output_dir>/pointing_interaction.png  - Combined: Aarav POINT fr8, Aanya NOD fr4

Rendering technique: Option B (direct mesh repositioning via evaluated depsgraph),
identical to render_animation_preview.py.

Aanya orientation fix: Aanya armature may have a Z rotation offset relative to
Aarav.  When building combined scenes we probe the armature's rotation_euler[2]
and negate it at the object level so Aanya faces +Y consistently.

Prints 'RENDER_STAGE42_PREVIEW_OK' on success.
"""

import sys
import os
import math

if '--' in sys.argv:
    args = sys.argv[sys.argv.index('--') + 1:]
else:
    print('Usage: blender --background --python render_stage42_previews.py -- <output_dir>')
    sys.exit(1)

if len(args) < 1:
    print('ERROR: need <output_dir>')
    sys.exit(1)

output_dir = args[0]
os.makedirs(output_dir, exist_ok=True)

import bpy
import mathutils

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_BLENDER_DIR = os.path.dirname(_SCRIPTS_DIR)
_STUDIO_DIR  = os.path.dirname(_BLENDER_DIR)
_CHARACTERS_DIR = os.path.join(_STUDIO_DIR, 'blender', 'assets', 'characters')

AARAV_BLEND = os.path.join(_CHARACTERS_DIR, 'aarav', 'aarav_stage4.blend')
AANYA_BLEND = os.path.join(_CHARACTERS_DIR, 'aanya', 'aanya_stage4.blend')

for p in [AARAV_BLEND, AANYA_BLEND]:
    if not os.path.isfile(p):
        print(f'ERROR: blend file not found: {p}')
        sys.exit(1)

# ---------------------------------------------------------------------------
# Bone → mesh suffix mapping (verbatim from render_animation_preview.py)
# ---------------------------------------------------------------------------
_BONE_TO_MESH = {
    'spine':       ['Spine'],
    'chest':       ['Chest'],
    'neck':        ['Neck'],
    'head':        ['Head'],
    'shoulder_L':  ['Shoulder_L'],
    'upper_arm_L': ['UpperArm_L'],
    'forearm_L':   ['LowerArm_L'],
    'hand_L':      ['Hand_L'],
    'shoulder_R':  ['Shoulder_R'],
    'upper_arm_R': ['UpperArm_R'],
    'forearm_R':   ['LowerArm_R'],
    'hand_R':      ['Hand_R'],
    'thigh_L':     ['UpperLeg_L', 'Thigh_L'],
    'shin_L':      ['LowerLeg_L', 'Shin_L'],
    'foot_L':      ['Foot_L'],
    'thigh_R':     ['UpperLeg_R', 'Thigh_R'],
    'shin_R':      ['LowerLeg_R', 'Shin_R'],
    'foot_R':      ['Foot_R'],
    # hips bone drives torso offset in improved walk
    'hips':        [],
}


# ---------------------------------------------------------------------------
# Scene / camera helpers
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


def make_camera(scene, name, pos, target, lens=50):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_obj = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    cam_obj.location = mathutils.Vector(pos)
    direction = mathutils.Vector(target) - mathutils.Vector(pos)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()
    return cam_obj


def render_to(scene, filepath):
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# Option B — animation pose helpers
# (exact pattern from render_animation_preview.py)
# ---------------------------------------------------------------------------

def _apply_pose_from_action(arm_obj, action, frame):
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = mathutils.Euler((0.0, 0.0, 0.0), 'XYZ')
        pb.location = mathutils.Vector((0.0, 0.0, 0.0))
        pb.scale = mathutils.Vector((1.0, 1.0, 1.0))
    for fc in action.fcurves:
        if 'rotation_euler' not in fc.data_path:
            continue
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
    pb = arm_eval.pose.bones.get(bone_name)
    if pb is None:
        return None
    mw = arm_eval.matrix_world
    return (mw @ pb.head + mw @ pb.tail) * 0.5


# Bones whose mesh objects are SAFE to move (arm/leg only).
# Head, Neck, Spine, Chest, Shoulder are excluded to avoid detachment
# in rigid-parenting mode.
_SAFE_BONES = frozenset({
    'upper_arm_L', 'forearm_L', 'hand_L',
    'upper_arm_R', 'forearm_R', 'hand_R',
    'thigh_L', 'shin_L', 'foot_L',
    'thigh_R', 'shin_R', 'foot_R',
})


def _compute_rest_offsets(arm_obj, char_prefix):
    """Compute per-object rest-pose offsets: offset = mesh_origin - rest_bone_midpoint."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = mathutils.Euler((0.0, 0.0, 0.0), 'XYZ')
        pb.location = mathutils.Vector((0.0, 0.0, 0.0))
        pb.scale = mathutils.Vector((1.0, 1.0, 1.0))
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()

    depsgraph = bpy.context.evaluated_depsgraph_get()
    arm_eval = arm_obj.evaluated_get(depsgraph)

    offsets = {}
    for bone_name, mesh_suffixes in _BONE_TO_MESH.items():
        midpoint = _bone_world_midpoint(arm_eval, bone_name)
        if midpoint is None:
            continue
        for suffix in mesh_suffixes:
            obj_name = f'{char_prefix}_{suffix}'
            obj = bpy.data.objects.get(obj_name)
            if obj is None:
                continue
            offsets[obj_name] = obj.location.copy() - midpoint
    return offsets


def apply_animation_pose(arm_obj, action, frame, char_prefix, rest_offsets=None):
    # Compute rest offsets if not provided
    if rest_offsets is None:
        rest_offsets = _compute_rest_offsets(arm_obj, char_prefix)

    _apply_pose_from_action(arm_obj, action, frame)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    arm_eval = arm_obj.evaluated_get(depsgraph)

    saved = {}
    keyed_bones = set()
    for fc in action.fcurves:
        if 'rotation_euler' in fc.data_path:
            try:
                keyed_bones.add(fc.data_path.split('"')[1])
            except IndexError:
                pass

    for bone_name in keyed_bones:
        if bone_name not in _SAFE_BONES:
            continue  # skip head, neck, spine, chest — prevents detachment
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
            # CORRECT: new_position = new_bone_midpoint + rest_offset
            offset = rest_offsets.get(obj_name, mathutils.Vector((0.0, 0.0, 0.0)))
            obj.location = midpoint + offset

    bpy.context.view_layer.update()
    return saved


def restore_pose(arm_obj, saved_locations):
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


# ---------------------------------------------------------------------------
# Aanya orientation fix
# ---------------------------------------------------------------------------

def probe_armature_rotation(arm_obj_name):
    """Return the rotation_euler of the named armature object (or zeros)."""
    arm = bpy.data.objects.get(arm_obj_name)
    if arm is None:
        return (0.0, 0.0, 0.0)
    return tuple(arm.rotation_euler)


def fix_aanya_orientation():
    """
    After appending Aanya into a combined scene, ensure Aanya faces +Y.

    Strategy: read Aanya_Armature.rotation_euler[2].  If non-zero, counter-
    rotate all Aanya root objects (parent is None) by -rotation_euler[2] on Z.
    This normalises Aanya to the same orientation as Aarav (+Y facing).
    """
    aanya_arm = bpy.data.objects.get('Aanya_Armature')
    if aanya_arm is None:
        return

    arm_z_rot = aanya_arm.rotation_euler[2]
    print(f'  Aanya_Armature.rotation_euler[2] = {arm_z_rot:.4f} rad')

    if abs(arm_z_rot) > 1e-4:
        # Counter-rotate all parentless Aanya objects
        for obj in bpy.data.objects:
            if obj.name.startswith('Aanya') and obj.parent is None:
                obj.rotation_euler[2] -= arm_z_rot
        print(f'  Applied counter-rotation of {-arm_z_rot:.4f} rad to Aanya root objects')
    else:
        print(f'  Aanya orientation OK (no correction needed)')

    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------
# Offset all objects of one character to target X position
# ---------------------------------------------------------------------------

def offset_character(prefix, target_x):
    """Move all parentless objects of *prefix* character to *target_x*."""
    for obj in bpy.data.objects:
        if obj.name.startswith(prefix) and obj.parent is None:
            obj.location.x = target_x
    bpy.context.view_layer.update()


# ===========================================================================
# Single-character render
# ===========================================================================

def render_single(blend_file, char_name, action_name, frame, out_filename,
                  cam_pos=(0, 4.5, 0.875), cam_target=(0, 0, 0.875), lens=50):
    bpy.ops.wm.open_mainfile(filepath=blend_file)
    scene = setup_scene()

    # Probe and report armature orientation
    rot = probe_armature_rotation(f'{char_name}_Armature')
    print(f'  {char_name}_Armature rotation_euler = {rot}')

    cam = make_camera(scene, 'RenderCam', cam_pos, cam_target, lens)

    arm_obj = bpy.data.objects.get(f'{char_name}_Armature')
    if arm_obj is None:
        print(f'WARNING: {char_name}_Armature not found')
        return

    action = bpy.data.actions.get(action_name)
    if action is None:
        print(f'WARNING: action {action_name!r} not found')
        return

    print(f'  Rendering {action_name} frame {frame} -> {out_filename}')
    saved = apply_animation_pose(arm_obj, action, frame, char_name)
    render_to(scene, os.path.join(output_dir, out_filename))
    restore_pose(arm_obj, saved)


# ===========================================================================
# Combined-character render
# ===========================================================================

def render_combined(aarav_action, aarav_frame,
                    aanya_action, aanya_frame,
                    out_filename,
                    cam_pos=(0, 6.0, 0.875), cam_target=(0, 0, 0.875), lens=40,
                    aarav_x=-0.5, aanya_x=0.5):
    """Load Aarav, append Aanya, apply orientation fix, render."""
    bpy.ops.wm.open_mainfile(filepath=AARAV_BLEND)
    scene = setup_scene()

    # Append Aanya objects AND actions
    with bpy.data.libraries.load(AANYA_BLEND, link=False) as (src, dst):
        dst.objects = [name for name in src.objects if 'Aanya' in name]
        dst.actions = [name for name in src.actions if 'AANYA' in name]

    # Link to scene
    existing_names = {o.name for o in scene.collection.objects}
    for obj in bpy.data.objects:
        if obj.name.startswith('Aanya') and obj.name not in existing_names:
            scene.collection.objects.link(obj)

    # Fix Aanya orientation BEFORE offsetting X positions
    fix_aanya_orientation()

    # Position characters
    offset_character('Aarav', aarav_x)
    offset_character('Aanya', aanya_x)

    cam = make_camera(scene, 'RenderCamBoth', cam_pos, cam_target, lens)

    aarav_arm = bpy.data.objects.get('Aarav_Armature')
    aanya_arm = bpy.data.objects.get('Aanya_Armature')

    saved_aarav = {}
    saved_aanya = {}

    aa_action = bpy.data.actions.get(aarav_action)
    an_action = bpy.data.actions.get(aanya_action)

    if aarav_arm and aa_action:
        saved_aarav = apply_animation_pose(aarav_arm, aa_action, aarav_frame, 'Aarav')
    elif not aa_action:
        print(f'WARNING: action {aarav_action!r} not found')

    if aanya_arm and an_action:
        saved_aanya = apply_animation_pose(aanya_arm, an_action, aanya_frame, 'Aanya')
    elif not an_action:
        print(f'WARNING: action {aanya_action!r} not found')

    print(f'  Rendering {out_filename}')
    render_to(scene, os.path.join(output_dir, out_filename))

    if aarav_arm:
        restore_pose(aarav_arm, saved_aarav)
    if aanya_arm:
        restore_pose(aanya_arm, saved_aanya)


# ===========================================================================
# Main render sequence
# ===========================================================================

print('=== RENDER STAGE 4.2 PREVIEWS ===')

# --- 1. aarav_wave.png ---
print('1/8 aarav_wave.png')
render_single(AARAV_BLEND, 'Aarav', 'AARAV_WAVE', 10, 'aarav_wave.png')

# --- 2. aanya_wave.png ---
print('2/8 aanya_wave.png')
render_single(AANYA_BLEND, 'Aanya', 'AANYA_WAVE', 10, 'aanya_wave.png')

# --- 3. aarav_point.png ---
print('3/8 aarav_point.png')
render_single(AARAV_BLEND, 'Aarav', 'AARAV_POINT', 8, 'aarav_point.png')

# --- 4. aanya_nod.png ---
print('4/8 aanya_nod.png')
render_single(AANYA_BLEND, 'Aanya', 'AANYA_NOD', 4, 'aanya_nod.png')

# --- 5. greeting_interaction.png ---
print('5/8 greeting_interaction.png')
render_combined(
    'AARAV_GREETING', 6,
    'AANYA_GREETING', 6,
    'greeting_interaction.png',
)

# --- 6. walk_together.png ---
print('6/8 walk_together.png')
render_combined(
    'AARAV_WALK', 1,
    'AANYA_WALK', 1,
    'walk_together.png',
)

# --- 7. both_facing_camera.png ---
print('7/8 both_facing_camera.png')
render_combined(
    'AARAV_IDLE', 12,
    'AANYA_IDLE', 12,
    'both_facing_camera.png',
)

# --- 8. pointing_interaction.png ---
print('8/8 pointing_interaction.png')
render_combined(
    'AARAV_POINT', 8,
    'AANYA_NOD', 4,
    'pointing_interaction.png',
)

# ---------------------------------------------------------------------------
# Verify outputs
# ---------------------------------------------------------------------------
print()
print('=== OUTPUT VERIFICATION ===')
expected = [
    'aarav_wave.png',
    'aanya_wave.png',
    'aarav_point.png',
    'aanya_nod.png',
    'greeting_interaction.png',
    'walk_together.png',
    'both_facing_camera.png',
    'pointing_interaction.png',
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
    print('RENDER_STAGE42_PREVIEW_OK')
else:
    print('RENDER_STAGE42_PREVIEW_WARNINGS')

sys.exit(0)
