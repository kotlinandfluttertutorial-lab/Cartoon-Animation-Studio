"""Build and render a short, two-shot Stage 4 movement preview in Blender.

Run with the garden blend open:
    blender -b garden.blend --python-exit-code 1 --python render_stage44_preview.py -- OUTPUT_DIR
"""

import argparse
from contextlib import ExitStack
from math import pi, radians, sin, tau
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from facial_preview import mouth_surface, prepare_character_face
from garden_utils import assign_material, configure_workbench, create_material
from studio.dialogue.expression_library import apply_expression

PROJECT = Path(__file__).resolve().parents[2]
CHARACTERS = PROJECT / "blender" / "assets" / "characters"
FPS = 12
FRAME_COUNT = 60
CUT = 31
BLINK_FRAMES = {"Aarav": 12, "Aanya": 44}


def key(obj, frame, *channels):
    for channel in channels:
        obj.keyframe_insert(data_path=channel, frame=frame)


def append_character(scene, character):
    name = character.lower()
    path = CHARACTERS / name / f"{name}_stage4.blend"
    prefix = f"{character}_"
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.objects = [name for name in source.objects if name.startswith(prefix)]
        target.actions = [name for name in source.actions if name.startswith(prefix.upper())]
    for obj in target.objects:
        scene.collection.objects.link(obj)
        obj.animation_data_clear()
    return bpy.data.objects[f"{character}_Armature"]


def pivot_pose(objects, frames, pivot, axis, angles):
    """Rotate rigid mesh pieces about one common pivot in their parent's space."""
    rest = {obj: obj.matrix_basis.copy() for obj in objects}
    for frame, angle in zip(frames, angles, strict=True):
        rotation = Matrix.Translation(pivot) @ Matrix.Rotation(angle, 4, axis)
        rotation @= Matrix.Translation(-pivot)
        for obj, matrix in rest.items():
            obj.matrix_basis = rotation @ matrix
            key(obj, frame, "location", "rotation_euler")


def dance(character, start, end, phase):
    """Key an in-place arm dance and head look without moving planted feet."""
    # Newly appended meshes expose unscaled bounds until Blender evaluates them.
    bpy.context.view_layer.update()

    def part(suffix):
        return bpy.data.objects[f"{character}_{suffix}"]

    frames = list(range(start, end, 4)) + [end]
    beat = [sin(tau * (frame - start) / 16 + phase) for frame in frames]
    torso = part("Torso")
    for side, sign in (("L", -1), ("R", 1)):
        upper, forearm, hand = (part(f"{part_name}_{side}") for part_name in ("UpperArm", "LowerArm", "Hand"))
        arm = (upper, forearm, hand)
        pivot = upper.location + Vector((0, 0, upper.dimensions.z / 2))
        shoulder = torso.location + Vector((
            -sign * torso.dimensions.x / 2, 0, torso.dimensions.z * 0.44,
        ))
        for obj in arm:
            obj.location += shoulder - pivot
        angles = [sign * radians(36 + 25 * sign * pulse) for pulse in beat]
        pivot_pose(arm, frames, shoulder, "Y", angles)

    head = part("Head")
    head_parts = [
        obj for obj in head.parent.children
        if obj.name.split("_", 1)[1].startswith(("Head", "Hair", "Hijab", "Eye", "Iris", "Nose", "Mouth"))
    ]
    pivot_pose(head_parts, frames, head.location.copy(), "Z", [radians(10 * pulse) for pulse in beat])


def blink(character, center):
    for suffix in ("Eye_L", "Eye_R", "Iris_L", "Iris_R"):
        eye = bpy.data.objects[f"{character}_{suffix}"]
        rest = eye.scale.copy()
        for frame, factor in ((center - 2, 1), (center, 0.06), (center + 2, 1)):
            eye.scale = (rest.x, rest.y, rest.z * factor)
            key(eye, frame, "scale")


def turn(root, facing, start, end, direction):
    for frame, angle in ((start, facing), (end, facing + direction * tau)):
        root.rotation_euler.z = angle
        key(root, frame, "rotation_euler")


def empty(scene, name, parent=None):
    obj = bpy.data.objects.new(name, None)
    scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def bird_piece(name, parent, location, scale, material):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = location
    obj.scale = scale
    assign_material(obj, *material)
    return obj


def flying_bird(scene, name, color, start, end, lane, height):
    """Key a flight path and flap the two wings about separate shoulder pivots."""
    root = empty(scene, name)
    feathers = create_material(f"{name}_Feathers", color)
    wing_color = create_material(f"{name}_WingColor", "#244B88")
    beak = create_material(f"{name}_BeakColor", "#EF9736")
    bird_piece(f"{name}_Body", root, (0, 0, 0), (0.16, 0.085, 0.08), feathers)
    bird_piece(f"{name}_Head", root, (0.115, 0, 0.05), (0.073, 0.067, 0.067), feathers)
    bird_piece(f"{name}_Beak", root, (0.184, 0, 0.037), (0.058, 0.03, 0.027), beak)
    for sign, side in ((-1, "Near"), (1, "Far")):
        wing = empty(scene, f"{name}_Wing_{side}", root)
        wing.location = (0, sign * 0.055, 0.02)
        bird_piece(f"{wing.name}_Mesh", wing, (-0.045, sign * 0.13, 0), (0.12, 0.19, 0.034), wing_color)
        for frame in range(start, end + 1, 2):
            wing.rotation_euler.x = sign * radians(48) * sin(pi * (frame - start) / 4)
            key(wing, frame, "rotation_euler")

    for frame, x, lift in (
        (start, -2, 0), (start + (end - start) // 2, 0, 0.17), (end, 2, 0),
    ):
        root.location = (x, lane, height + lift)
        key(root, frame, "location")
    return root


def camera_move(scene, name, start, end, start_pose, end_pose):
    """Create an orthographic moving shot from (position, target, width) presets."""
    camera_data = bpy.data.cameras.new(name)
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new(name, camera_data)
    scene.collection.objects.link(camera)
    previous_rotation = None
    for frame, (position, target, width) in ((start, start_pose), (end, end_pose)):
        camera.location = position
        orientation = (Vector(target) - camera.location).to_track_quat("-Z", "Y")
        rotation = (
            orientation.to_euler("XYZ", previous_rotation)
            if previous_rotation is not None else orientation.to_euler("XYZ")
        )
        camera.rotation_euler = rotation
        previous_rotation = rotation
        camera_data.ortho_scale = width
        key(camera, frame, "location", "rotation_euler")
        key(camera_data, frame, "ortho_scale")
    scene.timeline_markers.new(name, frame=start).camera = camera
    return camera


def validate(scene, roots, birds, shots):
    """Sample the actual timeline, including both sides of the cut."""
    def bounds(obj):
        return [obj.matrix_world @ Vector(point) for point in obj.bound_box]

    def in_frame(camera, point):
        u, v, depth = world_to_camera_view(scene, camera, point)
        return 0 < u < 1 and 0 < v < 1 and depth > camera.data.clip_start

    feet = [bpy.data.objects[f"{name}_Foot_{side}"] for name in roots for side in ("L", "R")]
    character_meshes = [obj for root in roots.values() for obj in root.children if obj.type == "MESH"]
    boundary = {}
    flight = []
    flaps = []
    poses = []
    arm = bpy.data.objects["Aarav_UpperArm_L"]
    wing = bpy.data.objects["Bluebird_Wing_Near"]
    camera_positions = {}
    for frame in range(1, FRAME_COUNT + 1):
        scene.frame_set(frame)
        assert scene.camera == shots[int(frame >= CUT)], frame
        depsgraph = bpy.context.evaluated_depsgraph_get()
        toward_camera = scene.camera.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        for name, root in roots.items():
            for suffix in ("Head", "Torso", "Foot_L", "Foot_R"):
                obj = bpy.data.objects[f"{name}_{suffix}"]
                center = obj.matrix_world.translation
                distance = (scene.camera.location - center).dot(toward_camera)
                hit, _, _, _, visible, _ = scene.ray_cast(
                    depsgraph, center + distance * toward_camera, -toward_camera
                )
                assert hit and visible.parent == root, (frame, obj.name, visible)
        if frame in (1, CUT - 1, CUT, FRAME_COUNT):
            camera_positions[frame] = scene.camera.location.copy()
        for foot in feet:
            z = min(point.z for point in bounds(foot))
            assert 0 <= z <= 0.025, (frame, foot.name, z)
        for obj in character_meshes:
            assert all(in_frame(scene.camera, point) for point in bounds(obj)), (frame, obj.name)
        for bird in birds:
            for obj in bird.children_recursive:
                if obj.type == "MESH":
                    assert all(in_frame(scene.camera, point) for point in bounds(obj)), (frame, obj.name)
        if frame in (CUT - 1, CUT):
            boundary[frame] = [obj.matrix_world.translation.copy() for obj in character_meshes]
        for character, blink_frame in BLINK_FRAMES.items():
            if frame in (1, 24, FRAME_COUNT):
                head = bpy.data.objects[f"{character}_Head"].matrix_world.translation
                nose = bpy.data.objects[f"{character}_Nose"].matrix_world.translation
                assert (nose.y - head.y) * (-1 if frame == 24 else 1) > 0.12
            if frame in (blink_frame, blink_frame + 2):
                eye = bpy.data.objects[f"{character}_Eye_L"]
                assert (eye.scale.z < 0.01) == (frame == blink_frame)
        flight.append(birds[0].location.x)
        flaps.append(wing.rotation_euler.x)
        poses.append(arm.rotation_euler.y)
    assert max((a - b).length for a, b in zip(boundary[CUT - 1], boundary[CUT], strict=True)) < 0.25
    assert flight[-1] - flight[0] > 3.5
    assert max(flaps) - min(flaps) > 1.2
    assert max(poses) - min(poses) > 0.7
    assert (camera_positions[1] - camera_positions[CUT - 1]).length > 0.5
    assert (camera_positions[CUT] - camera_positions[FRAME_COUNT]).length > 0.5
    scene.frame_set(1)
    print("STAGE44_TIMELINE_OK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    scene = bpy.context.scene
    if "Ground_Plane" not in scene.objects:
        parser.error("Open the garden asset before running this script.")
    configure_workbench(scene)
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FRAME_COUNT
    scene.timeline_markers.clear()

    with ExitStack() as mouths:
        roots = {}
        for character, x, facing, direction in (("Aarav", -0.72, 0, 1), ("Aanya", 0.72, pi, -1)):
            root = append_character(scene, character)
            prepare_character_face(character)
            apply_expression(character, "happy")
            mouths.enter_context(mouth_surface(character, "happy"))
            dance(character, 1, FRAME_COUNT, facing)
            blink(character, BLINK_FRAMES[character])
            root.location = (x, -0.2, 0.012)
            turn(root, facing, 18, 29, direction)
            roots[character] = root

        birds = [
            flying_bird(scene, "Bluebird", "#4BADE8", 1, FRAME_COUNT, -0.35, 2.14),
            flying_bird(scene, "Swallow", "#B16CF0", 8, FRAME_COUNT, -0.55, 2.34),
        ]
        shared = ((0, 3.6, 2.12), (0, 0, 1.44), 6.0)
        shots = (
            camera_move(scene, "Garden approach", 1, CUT - 1, ((0.8, 4.0, 2.2), (0, 0, 1.43), 6.5), shared),
            camera_move(scene, "Garden follow", CUT, FRAME_COUNT, (*shared[:2], 5.65), ((-0.8, 3.7, 2.15), (0, 0, 1.44), 5.9)),
        )
        scene.camera = shots[0]
        validate(scene, roots, birds, shots)
        if not args.validate_only:
            output = args.output.resolve()
            output.mkdir(parents=True, exist_ok=True)
            scene.render.filepath = str(output / "frame_")
            bpy.ops.render.render(animation=True)
            print("STAGE44_RENDER_OK")


if __name__ == "__main__":
    main()
