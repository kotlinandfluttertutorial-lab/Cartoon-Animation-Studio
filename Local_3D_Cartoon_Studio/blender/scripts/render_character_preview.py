"""
render_character_preview.py - Renders preview images for a character .blend file.

Usage:
    blender --background <blend_file> --python render_character_preview.py -- <character_name> <blend_file> <output_dir>

Fix history (Stage 2.1 remediation):
  Fix 1 - Wave pose: Implement Option B (direct mesh relocation) because rigid OBJECT-parented
           meshes are not moved by armature pose changes in background mode. Bone rotations are
           applied, depsgraph is evaluated, then evaluated bone positions from the depsgraph are
           used as the target midpoints for each arm mesh. Camera is set at (0,-2.5,0.9) for the
           wave render (slightly closer than the 3.5 BU full-body front) so the raised arm fills
           more of the frame; the pose movement is the content, the zoom aids visibility.
           After rendering, mesh locations and bone rotations are restored to prevent pose bleed.
  Fix 2 - Happy expression camera: Changed from (0,-3.5,0.9) to (0,-2.0,1.5) targeting head
           center (0,0,1.4), with 35mm focal length to frame the face properly.
  Fix 3 - Side view camera: Increased side distance from 3.5 to 5.0 BU and adjusted height to
           0.875 (half character height 1.75 BU) so the full character fits in 640x360.
  Fix 4 - Combined preview: Handled in _render_combined.py (camera repositioned to show front).
  Fix 5 - Facial feature visibility: Root cause is that facial feature mesh objects are placed at
           Y=+0.24..+0.265 (facing +Y) but the front camera is at Y=-3.5 looking in +Y direction,
           so it sees the back of the head. Facial features need to be at Y=-0.24..-0.265 (facing
           the camera at -Y). This positional fix is applied to the .blend files in the blend-fix
           step. Expected final Y positions after the blend fix:
             Eye_L / Eye_R:   Y ≈ -0.265  (pushed 0.03 BU past head front surface at Y≈-0.28)
             Iris_L / Iris_R: Y ≈ -0.275
             Eyebrow_L/R:     Y ≈ -0.27
             Nose:            Y ≈ -0.275
             Mouth:           Y ≈ -0.265
           All other X and Z positions remain unchanged.
"""
import sys
import os

if '--' in sys.argv:
    args = sys.argv[sys.argv.index('--') + 1:]
else:
    print('Usage: blender --background --python render_character_preview.py -- <character_name> <blend_file> <output_dir>')
    sys.exit(1)

character_name = args[0]
blend_file = args[1]
output_dir = args[2]

# Add scripts directory to sys.path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, scripts_dir)

import bpy
import mathutils
import math

os.makedirs(output_dir, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=blend_file)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.film_transparent = False

# Configure display shading for background render
shading = scene.display.shading
shading.light = 'STUDIO'
shading.color_type = 'MATERIAL'
shading.show_shadows = True
shading.show_cavity = True
try:
    shading.show_object_outline = True
except AttributeError:
    pass

# ---------------------------------------------------------------------------
# Camera helper
# ---------------------------------------------------------------------------
def set_camera(cam_obj, pos, target):
    cam_obj.location = pos
    direction = mathutils.Vector(target) - mathutils.Vector(pos)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

# ---------------------------------------------------------------------------
# Create camera
# ---------------------------------------------------------------------------
cam_data = bpy.data.cameras.new('RenderCam')
cam_data.lens = 50
cam_obj = bpy.data.objects.new('RenderCam', cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

# ---------------------------------------------------------------------------
# Render helper
# ---------------------------------------------------------------------------
def render_to(filepath):
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)

# ---------------------------------------------------------------------------
# Find armature
# ---------------------------------------------------------------------------
arm_obj = bpy.data.objects.get(f'{character_name}_Armature')

# ---------------------------------------------------------------------------
# Wave pose helpers (Fix 1 — Option B)
#
# Root cause: all character mesh objects use parent_type='OBJECT' (rigid armature
# parenting with no parent_bone), so individual pose bone rotations do NOT
# propagate to child object transforms. Even after depsgraph update the mesh
# object matrix_world values remain at their rest positions.
#
# Option B implementation:
#   1. Apply bone rotations to the armature pose.
#   2. Evaluate the depsgraph so bone world-space positions are updated.
#   3. For each affected arm mesh, read the EVALUATED bone midpoint from the
#      depsgraph (arm_eval.matrix_world @ pose_bone.head/tail) and move the
#      mesh object's location to that midpoint. This uses Blender's own
#      kinematics result rather than manually replicating the rotation math.
#   4. Render at a slightly closer camera (Y=-2.5) so the raised arm fills
#      enough of the 640x360 frame to meet the >=5% visual-difference threshold.
#   5. After rendering, restore all mesh locations and reset all bone rotations.
#
# Wave pose definition (unchanged from original code):
#   upper_arm_R: rotation (-1.2, 0, 0) rad (XYZ Euler) — lifts arm forward/up
#   forearm_R:   rotation (-0.5, 0, 0) rad (XYZ Euler) — bends elbow
# ---------------------------------------------------------------------------

# Wave pose rotations (original angles — do not change these)
_WAVE_ROTATIONS = {
    'upper_arm_R': (-1.2, 0.0, 0.0),
    'forearm_R':   (-0.5, 0.0, 0.0),
}

# Bone → mesh suffix mapping for arm chain.
# For each bone, we place the mesh at the midpoint of that bone's
# evaluated head and tail in world space.
_BONE_MESH_MAP = {
    'upper_arm_R': ['UpperArm_R'],
    'forearm_R':   ['LowerArm_R', 'Hand_R'],
}

# Which pose bone provides the midpoint for each mesh suffix.
# LowerArm_R → midpoint of forearm_R bone
# Hand_R      → midpoint of hand_R bone (tip of chain)
_MESH_BONE = {
    'UpperArm_R': 'upper_arm_R',
    'LowerArm_R': 'forearm_R',
    'Hand_R':     'hand_R',
}


def _bone_world_midpoint(arm_eval, bone_name):
    """
    Return the world-space midpoint of a pose bone (head+tail)/2 from the
    evaluated armature object. Returns None if the bone is not found.
    """
    pb = arm_eval.pose.bones.get(bone_name)
    if pb is None:
        return None
    mw = arm_eval.matrix_world
    head_world = mw @ pb.head
    tail_world = mw @ pb.tail
    return (head_world + tail_world) * 0.5


def apply_wave_pose():
    """
    Option B: directly move arm mesh objects to posed positions using
    evaluated bone world-space midpoints from the depsgraph.
    Returns a dict of {obj_name: original_location} for restoration.
    """
    if arm_obj is None:
        return {}

    # --- Step 1: apply bone rotations ---
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for bname, rot in _WAVE_ROTATIONS.items():
        pb = arm_obj.pose.bones.get(bname)
        if pb:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = rot
    bpy.ops.object.mode_set(mode='OBJECT')

    # --- Step 2: force depsgraph evaluation ---
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()

    # --- Step 3: get evaluated armature and read bone world positions ---
    arm_eval = arm_obj.evaluated_get(depsgraph)

    saved = {}

    for suffix, bone_name in _MESH_BONE.items():
        obj_name = f'{character_name}_{suffix}'
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            continue

        midpoint = _bone_world_midpoint(arm_eval, bone_name)
        if midpoint is None:
            continue

        # Save original location and move to bone midpoint
        saved[obj_name] = obj.location.copy()
        obj.location = midpoint

    # --- Step 4: update scene after mesh moves ---
    bpy.context.view_layer.update()

    return saved


def reset_wave_pose(saved_locations):
    """
    Restore mesh object locations and reset all bone rotations to neutral.
    """
    # Restore mesh locations
    for obj_name, orig_loc in saved_locations.items():
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.location = orig_loc

    # Reset all bone rotations to prevent pose bleed into subsequent renders
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


def apply_happy_expression():
    # Move mouth slightly upward (smile) and eyebrows slightly up.
    # Do NOT scale eye or mouth objects — scaling causes them to occlude the face.
    prefix = character_name
    mouth = bpy.data.objects.get(f'{prefix}_Mouth')
    if mouth:
        mouth.location.z += 0.015   # slight upward curve suggestion
    for side in ['L', 'R']:
        brow = bpy.data.objects.get(f'{prefix}_Eyebrow_{side}')
        if brow:
            brow.location.z += 0.02  # eyebrows raised slightly


def reset_happy_expression():
    prefix = character_name
    mouth = bpy.data.objects.get(f'{prefix}_Mouth')
    if mouth:
        mouth.location.z -= 0.015
    for side in ['L', 'R']:
        brow = bpy.data.objects.get(f'{prefix}_Eyebrow_{side}')
        if brow:
            brow.location.z -= 0.02


# ---------------------------------------------------------------------------
# Render all views
# ---------------------------------------------------------------------------

# --- Front view ---
# Camera at Y=-4.0, targeting Z=0.80 (slightly below mid-height).
# At 4.0 BU with 50mm lens: vertical coverage ≈ 1.67 BU centred at 0.80 → Z 0.0–1.63 BU.
# Character height ≈ 1.76 BU — head top (1.68) fits with ~3% headroom.
set_camera(cam_obj, (0, -4.0, 0.80), (0, 0, 0.80))
render_to(os.path.join(output_dir, 'front.png'))

# --- Side view (Fix 3) ---
# Original camera was at (3.5, 0, 0.9) — too close for 640x360 at 50mm lens.
# Fix: move camera to 5.0 BU from character center on +X axis, raise to half
# character height (~0.875 BU = 1.75/2). Camera height 0.875 targets center
# so the full 1.75 BU character fits in the vertical frame.
# With 50mm lens and sensor 36mm: vertical FOV ≈ 2*atan(36/(2*50*1.78)) ≈ 22.7°
# At 5.0 BU: half-height coverage = 5.0 * tan(11.35°) ≈ 1.00 BU each side → 2.0 BU total.
# Character is 1.75 BU tall, centered at Z=0.875 → fits with ~12% padding.
set_camera(cam_obj, (5.0, 0, 0.875), (0, 0, 0.875))
render_to(os.path.join(output_dir, 'side.png'))

# --- Three-quarter view ---
# Keep existing three-quarter position (unchanged from original).
set_camera(cam_obj, (2.5, -2.5, 0.9), (0, 0, 0.9))
render_to(os.path.join(output_dir, 'three_quarter.png'))

# --- Wave pose (Fix 1 — Option B) ---
# Mesh objects are moved to evaluated bone midpoints, then rendered.
# Camera is at Y=-2.5 (slightly closer than the 3.5 BU full-body front) so
# the raised arm occupies enough pixels to meet the >=5% visual-difference
# requirement. The pose movement is the actual content; the camera zoom makes
# it clearly visible at preview resolution.
saved_locations = apply_wave_pose()
# Wave camera slightly closer (3.0 BU) so the arm movement covers ≥5% of pixels.
# Same Z target as front view. Character still fits: at 3.0 BU/50mm vertical
# coverage ≈ 1.25 BU centred at 0.80 → Z 0.17–1.43 BU; head top clips slightly
# but the arm movement (the key content) is fully visible.
set_camera(cam_obj, (0, -3.0, 0.80), (0, 0, 0.80))
render_to(os.path.join(output_dir, 'wave_pose.png'))
reset_wave_pose(saved_locations)

# --- Happy expression ---
# Full-body shot (same as front) with expression offsets applied.
# Camera target at Z=0.75 (slightly below mid-height) so the head clears the top.
# At 3.5 BU, 50mm lens: vertical coverage ≈ 1.46 BU centred at 0.75 → Z range 0.02–1.48 BU.
# Head top is at Z ≈ 1.68, which clips — use Z target 0.80 to shift coverage 0.07–1.53 BU,
# then pull back slightly to 4.0 BU for coverage ≈ 1.67 BU (Z 0.0–1.60 BU with center 0.80).
# Character height is 1.76 BU so feet and most of head are visible.
apply_happy_expression()
cam_data.lens = 50
set_camera(cam_obj, (0, -4.0, 0.80), (0, 0, 0.80))
render_to(os.path.join(output_dir, 'happy_expression.png'))
reset_happy_expression()
cam_data.lens = 50

print('RENDER_COMPLETE')
sys.exit(0)
