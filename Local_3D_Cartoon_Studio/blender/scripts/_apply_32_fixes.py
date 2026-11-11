"""
Stage 3.2 — Apply targeted polish fixes to garden.blend.
Run: blender --background --factory-startup --python _apply_32_fixes.py

Fixes applied:
  A. Reposition clouds to be visible in sky band (closer, higher, correct side)
  B. Remove ground patches (hard rectangular edges)
  C. Raise Garden_Close_Camera for better composition
  D. Reposition clipping trees slightly inward
  E. Scale flowers up 50%
  F. Improve tree foliage colour variation (brighter range)
  G. Improve sky colour (brighter blue, use world.color directly)

Does NOT modify character blend files.
Does NOT change camera names, collection names, or any test-required structure.
Saves garden.blend when done.
"""
import bpy
import sys
import math
import mathutils

BLEND = r"P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\environments\garden\garden.blend"

bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene

print("[3.2] Starting Stage 3.2 fixes...")

# ── Helper ────────────────────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip('#')
    return (int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255)

def set_material_color(mat_name, hex_color):
    mat = bpy.data.materials.get(mat_name)
    if mat:
        rgba = hex_to_rgb(hex_color) + (1.0,)
        mat.diffuse_color = rgba
        bsdf = mat.node_tree.nodes.get("Principled BSDF") if mat.use_nodes else None
        if bsdf:
            bsdf.inputs["Base Color"].default_value = rgba
        return True
    return False

# ── Fix A: Reposition clouds ──────────────────────────────────────────────────
# Camera Garden_Main at (0, 9, 5.5) faces direction (0, -0.90, -0.43).
# Sky band is at the TOP of the frame. For clouds to appear in the sky strip:
#   - They need to be in front of the camera (Y < 9) ✓
#   - At the right height so the camera's upward frustum edge catches them
#   - Close enough to be visibly large (< 8 BU away)
#
# Camera FOV (50mm, 640x360):
#   Horizontal FOV ≈ 2*atan(36/(2*50)) = 39.6°
#   Vertical FOV ≈ 2*atan(20.25/(2*50)) = 22.9°  (sensor_height=36/1.78)
#
# Camera up vector ≈ (0, +0.43, -0.90) (perpendicular to forward, in vertical plane)
# Top of frustum = forward + 0.5*tan(11.45°) * up_normalized per unit depth
#
# For clouds to appear near the top of frame: place them ABOVE and SLIGHTLY IN FRONT
# of the camera, in the direction of the camera's up vector.
# Camera at (0, 9, 5.5), up ≈ (0, +0.43, -0.90) normalised.
# "Sky band" position: camera pos + 5*fwd + 3*up  (roughly)
#
# Mathematically: fwd=(0,-0.90,-0.43), up≈(0,0.43,-0.90)
# Sky target ≈ (0, 9) + 4*(0,-0.90) + 2*(0,0.43) = (0, 9-3.6+0.86) = (0, 6.26, 5.5-1.72+?) 
# Simpler approach: place clouds at Y=4..7, Z=7..9 (high above garden, in front of cameras)
# Verify: camera at Y=9 looking toward Y=-inf; clouds at Y=4-7 are in front. 
# At Z=7-9 they appear ABOVE the garden horizon in the sky strip. ✓

cloud_positions = [
    ("Cloud_01", (-4.0,  4.0, 8.0)),
    ("Cloud_02", (-2.0,  5.5, 7.5)),
    ("Cloud_03", ( 2.5,  3.5, 8.5)),
    ("Cloud_04", ( 4.5,  5.0, 7.0)),
    ("Cloud_05", ( 0.0,  2.0, 9.0)),
]
for name, (x, y, z) in cloud_positions:
    obj = bpy.data.objects.get(name)
    if obj:
        obj.location = (x, y, z)
        print(f"[3.2-A] {name} moved to ({x},{y},{z})")
    else:
        print(f"[3.2-A] WARNING: {name} not found")

# ── Fix B: Remove ground patches ─────────────────────────────────────────────
patches_removed = 0
for name in ["Ground_Patch_01", "Ground_Patch_02", "Ground_Patch_03"]:
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
        patches_removed += 1
        print(f"[3.2-B] Removed {name}")
print(f"[3.2-B] Removed {patches_removed} ground patches")

# ── Fix C: Raise Garden_Close_Camera ─────────────────────────────────────────
# Current: pos=(0,5,2.5) looking toward (0,0,0.8) — essentially ground level
# Fix: raise to pos=(0,5,2.5) but target (0,0,0.5) so it shows path+flowers+some tree
# Actually current already has Z=2.5 but the issue is it looks nearly flat.
# Better: move to (0, 4, 2.0) targeting (0, -1, 0.3) — shows path receding away
close_cam = bpy.data.objects.get("Garden_Close_Camera")
if close_cam:
    pos    = mathutils.Vector((0, 4.5, 2.0))
    target = mathutils.Vector((0, -1.0, 0.2))
    close_cam.location = pos
    direction = target - pos
    rot_quat = direction.to_track_quat('-Z', 'Y')
    close_cam.rotation_euler = rot_quat.to_euler()
    print(f"[3.2-C] Garden_Close_Camera repositioned to {list(pos)}")

# ── Fix D: Move clipping trees inward ────────────────────────────────────────
# Trees at X=±3 with foliage radius 0.6–0.7 BU clip at frame edges in main/char views.
# Cameras at X=0, FOV ~39.6° horizontal → at Y=0, half-width coverage ≈ 9*tan(19.8°) ≈ 3.24 BU.
# Trees at X=±3 with foliage r=0.65 → outer edge at X=±3.65, which clips at ±3.24 BU.
# Move trees at X=±3,Y=2 inward to X=±2.5 — keeps them well within frame.
tree_adjustments = {
    "Tree_01": -2.5,  # was -3.0
    "Tree_02":  2.5,  # was  3.0
    # Trees at Y=-3 are at the bottom of the frame and don't clip horizontally
}
for tree_prefix, new_x in tree_adjustments.items():
    for suffix in ["_Trunk", "_Foliage"]:
        obj = bpy.data.objects.get(f"{tree_prefix}{suffix}")
        if obj:
            obj.location.x = new_x
            print(f"[3.2-D] {tree_prefix}{suffix} X → {new_x}")

# ── Fix E: Scale flowers up 50% ──────────────────────────────────────────────
flowers_scaled = 0
for obj in bpy.data.objects:
    if obj.name.startswith("Flower_"):
        obj.scale = (obj.scale.x * 1.5, obj.scale.y * 1.5, obj.scale.z * 1.5)
        # Also raise position proportionally since stem base should stay at Z=0
        # Stem centre was at Z=0.15; after 1.5x scale stem occupies Z=0 to 0.45
        # Petals were at Z=0.3 → now at Z=0.45; Centre was at Z=0.32 → now Z=0.48
        # We need to also scale the location Z for petal/centre objects
        if "Stem" not in obj.name:  # Stems are rooted at base, only petal/centre need Z raise
            obj.location.z = obj.location.z * 1.5
        flowers_scaled += 1
print(f"[3.2-E] Scaled {flowers_scaled} flower objects by 1.5x")

# ── Fix F: Improve tree foliage colour variation ─────────────────────────────
# Current foliage materials are Mat_Foliage_01..05 with very similar greens.
# Workbench studio lighting flattens variation. Use a wider colour range.
foliage_colors = {
    "Mat_Foliage_01": "#4CAF50",  # medium green (brighter than #66BB6A with lighting)
    "Mat_Foliage_02": "#8BC34A",  # yellow-green (lime)
    "Mat_Foliage_03": "#2E7D32",  # dark forest green
    "Mat_Foliage_04": "#AED581",  # light yellow-green
    "Mat_Foliage_05": "#388E3C",  # medium-dark green
}
for mat_name, color in foliage_colors.items():
    if set_material_color(mat_name, color):
        # Also update object.color for all objects using this material
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data.materials:
                for slot in obj.material_slots:
                    if slot.material and slot.material.name == mat_name:
                        rgba = hex_to_rgb(color) + (1.0,)
                        obj.color = rgba
        print(f"[3.2-F] {mat_name} → {color}")

# ── Fix G: Brighter sky colour ────────────────────────────────────────────────
# Workbench studio lighting desaturates world.color. Use a more saturated blue
# so it renders closer to the intended #87CEEB after lighting adjustment.
world = scene.world
if world:
    world.use_nodes = False
    # #87CEEB = (135,206,235)/255 = (0.529,0.808,0.922)
    # With Workbench studio lighting tinting, use a slightly more saturated value
    world.color = (0.45, 0.72, 0.95)  # slightly more saturated than #87CEEB
    print(f"[3.2-G] World color set to (0.45, 0.72, 0.95) — bright sky blue")

# ── Save ──────────────────────────────────────────────────────────────────────
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print(f"[3.2] Saved: {BLEND}")
print("[3.2] All Stage 3.2 fixes applied successfully.")
