"""Shared Blender setup and surface-fitted mouths for Stage 4.3 renders."""

from contextlib import contextmanager
from math import cos, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector

# Background scripts are launched directly by Blender, outside the studio package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio.dialogue.mouth_shapes import MouthShapes

# Stage 4.2.3 uses each solo asset in its native orientation.
FRONT_Y = {"Aarav": 1, "Aanya": -1}


def setup_preview(character):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = False
    shading.show_cavity = True
    shading.show_object_outline = True

    camera_data = bpy.data.cameras.new("FacialPreviewCamera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 3.5
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    target = bpy.data.objects[f"{character}_Head"].matrix_world.translation.copy()
    target.z -= 0.52
    camera.location = target + Vector((0, 4.5 * FRONT_Y[character], 0))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()

    prepare_character_face(character)
    return scene


def prepare_character_face(character):
    """Apply the in-memory face and headwear adjustments in native rest space."""
    if character == "Aarav":
        # The Stage 4 working copy uses unit cubes for the crown and fringe.
        # Round them in the preview scene while preserving their authored fit.
        for suffix in ("Hair_Top", "Hair_Front"):
            hair = bpy.data.objects.get(f"Aarav_{suffix}")
            if hair is not None and len(hair.data.vertices) == 8:
                bevel = hair.modifiers.new("Round preview hair", "BEVEL")
                bevel.width = 0.85
                bevel.segments = 6
    else:
        # The rear panel was authored on the same side as the -Y face.
        # Move it behind the head and keep the cap's crown at its original height.
        back = bpy.data.objects.get("Aanya_Hijab_Back")
        if back is not None:
            back.location.y = abs(back.location.y)
        cap = bpy.data.objects.get("Aanya_Hijab_Cap")
        if cap is not None:
            cap.location.z += 0.08
            cap.scale.z -= 0.08
            cap.scale.y *= 0.85

        # Seat the features against the exposed face once the scarf is behind it.
        face_depths = {
            "Eye_L": -0.252, "Eye_R": -0.252,
            "Eyebrow_L": -0.239, "Eyebrow_R": -0.239,
            "Nose": -0.271,
        }
        for suffix, depth in face_depths.items():
            feature = bpy.data.objects.get(f"Aanya_{suffix}")
            if feature is not None:
                feature.location.y = depth

    # Iris and sclera are siblings. Keep the iris in front of the sclera,
    # including when the eye whites are enlarged for surprise.
    for side in ("L", "R"):
        eye = bpy.data.objects.get(f"{character}_Eye_{side}")
        iris = bpy.data.objects.get(f"{character}_Iris_{side}")
        if eye is not None and iris is not None:
            iris.location.y = eye.location.y + FRONT_Y[character] * eye.scale.y



@contextmanager
def viseme_pose(mouth, viseme):
    """Apply factors to the authored scale and restore the current frame's pose."""
    scale = mouth.scale.copy()
    z = mouth.location.z
    transform = MouthShapes.get_transform(viseme)
    try:
        mouth.scale = [base * factor for base, factor in zip(scale, transform["scale"])]
        mouth.location.z = z + transform["z_offset"]
        yield
    finally:
        mouth.scale = scale
        mouth.location.z = z


@contextmanager
def mouth_surface(character, profile):
    """Use the posed mouth width/height and fit a temporary silhouette to the head."""
    head = bpy.data.objects[f"{character}_Head"]
    mouth = bpy.data.objects[f"{character}_Mouth"]
    bpy.context.view_layer.update()
    head_inverse = head.matrix_world.inverted()
    mouth_inverse = mouth.matrix_world.inverted()
    front = Vector((0, FRONT_Y[character], 0))
    ray = head_inverse.to_3x3() @ -front

    # OPEN and surprise are taller than the resting mouth. Happy has raised corners.
    width, height, smile = {
        "happy": (1.0, 1.0, 1.45),
        "excited": (1.0, 1.0, 0.85),
        "sad": (0.9, 0.75, -0.65),
        "surprised": (0.62, 1.65, 0.0),
        "OPEN": (0.86, 1.5, 0.0),
        "EI": (1.0, 1.0, 0.55),
        "MBP": (1.45, 0.8, 0.0),
    }.get(profile, (1.0, 0.8, 0.0))

    def surface_point(x, z):
        point = mouth.matrix_world @ Vector((x * width, 0, z * height + smile * x * x))
        hit, surface, _, _ = head.ray_cast(head_inverse @ (point + front), ray)
        if not hit:
            raise ValueError(f"{mouth.name} profile extends beyond the head")
        return mouth_inverse @ (head.matrix_world @ surface + 0.006 * front)

    segments = 32
    vertices = [surface_point(0, 0)]
    vertices.extend(
        surface_point(cos(angle), sin(angle))
        for angle in (tau * index / segments for index in range(segments))
    )
    faces = [(0, index + 1, (index + 1) % segments + 1) for index in range(segments)]
    if FRONT_Y[character] > 0:
        faces = [face[::-1] for face in faces]

    original = mouth.data
    mesh = bpy.data.meshes.new("FacialPreviewMouth")
    material = bpy.data.materials.new("FacialPreviewMouthInterior")
    material.diffuse_color = (0.075, 0.012, 0.018, 1)
    try:
        mesh.from_pydata(vertices, [], faces)
        mesh.materials.append(material)
        mouth.data = mesh
        yield
    finally:
        mouth.data = original
        bpy.data.meshes.remove(mesh)
        bpy.data.materials.remove(material)
