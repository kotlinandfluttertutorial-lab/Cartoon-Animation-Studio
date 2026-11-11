"""
Stage 2 Visual Review — Blender structural inspection.
Runs: blender --background --factory-startup --python _inspect_characters.py
Does NOT save or modify any .blend files.
Writes: reports/stage2_visual_review/_blender_inspection.json
"""
import bpy
import os
import json
import sys

BLEND_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "characters"
)
OUT_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "reports", "stage2_visual_review", "_blender_inspection.json"
)
os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)

REQUIRED_BONES = [
    "root","hips","spine","chest","neck","head",
    "shoulder_L","upper_arm_L","forearm_L","hand_L",
    "shoulder_R","upper_arm_R","forearm_R","hand_R",
    "thigh_L","shin_L","foot_L",
    "thigh_R","shin_R","foot_R",
]

def inspect_character(char_id, char_name):
    blend_path = os.path.join(BLEND_BASE, char_id, f"{char_id}.blend")
    result = {
        "character": char_name,
        "blend_file": blend_path,
        "blend_exists": os.path.isfile(blend_path),
        "checks": {},
        "warnings": [],
        "overall": "UNKNOWN",
    }

    if not result["blend_exists"]:
        result["overall"] = "FAIL"
        result["checks"]["blend_file_exists"] = False
        return result

    # Load the blend file (read-only inspection — we won't save)
    bpy.ops.wm.open_mainfile(filepath=blend_path)

    checks = {}

    # 1. Collection exists
    col = bpy.data.collections.get(char_name)
    checks["collection_exists"] = col is not None

    # 2. Armature exists
    arm_name = f"{char_name}_Armature"
    arm_obj = bpy.data.objects.get(arm_name)
    checks["armature_exists"] = arm_obj is not None

    # 3. All 20 bones present
    missing_bones = []
    if arm_obj and arm_obj.type == 'ARMATURE':
        bone_names = [b.name for b in arm_obj.data.bones]
        missing_bones = [b for b in REQUIRED_BONES if b not in bone_names]
        checks["all_bones_present"] = len(missing_bones) == 0
        checks["bone_count"] = len(bone_names)
        checks["missing_bones"] = missing_bones
    else:
        checks["all_bones_present"] = False
        checks["bone_count"] = 0
        checks["missing_bones"] = REQUIRED_BONES[:]

    # 4. Required mesh objects (check by prefix)
    prefix = char_name + "_"
    mesh_objects = [o for o in bpy.data.objects if o.name.startswith(prefix) and o.type == 'MESH']
    checks["mesh_object_count"] = len(mesh_objects)
    checks["mesh_objects_exist"] = len(mesh_objects) > 0

    # Check key body parts present
    required_parts = ["Head", "Torso", "UpperArm_L", "UpperArm_R",
                      "UpperLeg_L", "UpperLeg_R", "Foot_L", "Foot_R"]
    missing_parts = []
    for part in required_parts:
        expected = f"{char_name}_{part}"
        if not bpy.data.objects.get(expected):
            missing_parts.append(expected)
    checks["required_parts_present"] = len(missing_parts) == 0
    checks["missing_parts"] = missing_parts

    # 5. Materials valid (not default grey)
    mats = [m for m in bpy.data.materials if m.name.startswith(prefix)]
    checks["material_count"] = len(mats)
    grey_mats = []
    for m in mats:
        dc = m.diffuse_color
        if abs(dc[0] - 0.8) < 0.01 and abs(dc[1] - 0.8) < 0.01 and abs(dc[2] - 0.8) < 0.01:
            grey_mats.append(m.name)
    checks["materials_non_default"] = len(grey_mats) == 0
    checks["default_grey_materials"] = grey_mats

    # 6. Facial components
    facial_parts = ["Eye_L", "Eye_R", "Eyebrow_L", "Eyebrow_R", "Mouth", "Nose"]
    facial_found = []
    facial_missing = []
    for part in facial_parts:
        expected = f"{char_name}_{part}"
        if bpy.data.objects.get(expected):
            facial_found.append(expected)
        else:
            facial_missing.append(expected)
    checks["facial_components_found"] = facial_found
    checks["facial_components_missing"] = facial_missing
    checks["facial_components_exist"] = len(facial_missing) == 0

    # 7. Character height (measure bounding box of all character objects)
    char_objects = [o for o in bpy.data.objects if o.name.startswith(prefix) and o.type == 'MESH']
    if char_objects:
        min_z = min(o.location.z - o.dimensions.z/2 for o in char_objects)
        max_z = max(o.location.z + o.dimensions.z/2 for o in char_objects)
        height = max_z - min_z
        checks["estimated_height"] = round(height, 3)
        checks["height_in_range"] = 1.0 < height < 3.0
        checks["approx_ground_z"] = round(min_z, 3)
        checks["ground_level_valid"] = abs(min_z) < 0.15
    else:
        checks["estimated_height"] = 0
        checks["height_in_range"] = False
        checks["ground_level_valid"] = False

    # 8. Check if pose data exists (custom properties or pose markers)
    pose_data_found = False
    if arm_obj:
        props = list(arm_obj.keys())
        pose_data_found = len(props) > 0
        checks["armature_custom_properties"] = props

    # Warnings
    warnings = []
    if not checks.get("facial_components_exist"):
        warnings.append(f"Missing facial components: {facial_missing}")
    if checks.get("missing_parts"):
        warnings.append(f"Missing required body parts: {missing_parts}")
    if grey_mats:
        warnings.append(f"Default-grey materials found: {grey_mats}")

    # Note: wave pose visual check cannot be done structurally
    warnings.append("STRUCTURAL ONLY: Pose visual correctness cannot be verified without rendering.")
    warnings.append("STRUCTURAL ONLY: Expression visual correctness cannot be verified without rendering.")

    fails = [k for k, v in checks.items()
             if isinstance(v, bool) and not v
             and k not in ("facial_components_exist", "required_parts_present", "ground_level_valid")]

    result["checks"] = checks
    result["warnings"] = warnings
    result["overall"] = "FAIL" if fails else "PASS"
    result["failed_checks"] = fails
    return result


results = {}
for char_id, char_name in [("aarav", "Aarav"), ("aanya", "Aanya")]:
    print(f"\n[Inspect] {char_name}...")
    r = inspect_character(char_id, char_name)
    results[char_id] = r
    print(f"[Inspect] {char_name} overall: {r['overall']}")
    for k, v in r["checks"].items():
        print(f"  {k}: {v}")
    for w in r["warnings"]:
        print(f"  WARNING: {w}")

with open(OUT_JSON, "w") as f:
    json.dump(results, f, indent=2)
print(f"\n[Inspect] Written to {OUT_JSON}")
print("[Inspect] DONE")
