"""Geometry assertions executed inside Blender by test_stage4_3_render_geometry."""

import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def main():
    scripts, character = sys.argv[sys.argv.index("--") + 1:]
    sys.path.insert(0, scripts)
    from facial_preview import MouthShapes, mouth_surface, setup_preview, viseme_pose
    from studio.dialogue.expression_library import EXPRESSIONS, apply_expression, restore_expression

    def part(suffix):
        return bpy.data.objects[f"{character}_{suffix}"]

    def update():
        bpy.context.view_layer.update()

    def matrices():
        update()
        return {obj.name: obj.matrix_world.copy() for obj in parts}

    parts = [obj for obj in bpy.context.scene.objects if obj.name.startswith(f"{character}_")]
    head, nose, mouth = (part(suffix) for suffix in ("Head", "Nose", "Mouth"))
    original_mesh = mouth.data
    original_parent = mouth.parent
    original_matrices = matrices()
    scene = setup_preview(character)
    rest_matrices = matrices()
    assert all(
        rest_matrices[part(suffix).name] == original_matrices[part(suffix).name]
        for suffix in ("Armature", "Head", "Neck", "Torso", "Mouth")
    )

    front = Vector((0, 1 if character == "Aarav" else -1, 0))
    assert (nose.matrix_world.translation - head.matrix_world.translation).dot(front) > 0
    assert (scene.camera.location - nose.matrix_world.translation).dot(front) > 0
    camera_forward = scene.camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))
    assert camera_forward.dot(-front) > 0.999
    assert (scene.render.resolution_x, scene.render.resolution_y) == (640, 360)

    def check_frame(point):
        x, y, depth = world_to_camera_view(scene, scene.camera, point)
        assert 0 < x < 1 and 0 < y < 1 and depth > scene.camera.data.clip_start

    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in parts:
        if obj.type == "MESH":
            evaluated = obj.evaluated_get(depsgraph)
            for corner in evaluated.bound_box:
                check_frame(evaluated.matrix_world @ Vector(corner))

    if character == "Aarav":
        for suffix in ("Hair_Top", "Hair_Front"):
            hair = part(suffix)
            assert len(hair.evaluated_get(depsgraph).data.vertices) > len(hair.data.vertices)
    else:
        assert (part("Hijab_Back").matrix_world.translation - head.matrix_world.translation).dot(front) < 0

    def check_mouth(profile, expected_matrices):
        with mouth_surface(character, profile):
            points = [mouth.matrix_world @ vertex.co for vertex in mouth.data.vertices]
            width, depth, height = (
                max(point[i] for point in points) - min(point[i] for point in points)
                for i in range(3)
            )
            assert 0.04 < width < 0.2 and depth < 0.08 and 0 < height < 0.13
            assert mouth.parent == original_parent
            assert matrices() == expected_matrices

            inverse = head.matrix_world.inverted()
            direction = inverse.to_3x3() @ -front
            for point in points:
                check_frame(point)
                hit, surface, _, _ = head.ray_cast(inverse @ (point + front), direction)
                assert hit
                assert (point - (head.matrix_world @ surface) - 0.006 * front).length < 1e-5
            return width, height, tuple(tuple(point) for point in points)

    def check_rest():
        assert mouth.data == original_mesh
        assert matrices() == rest_matrices

    second = "EI" if character == "Aarav" else "MBP"
    shapes = {}
    rest_scale = mouth.scale.copy()
    for viseme in ("OPEN", second, "REST", "OPEN"):
        with viseme_pose(mouth, viseme):
            factors = MouthShapes.get_transform(viseme)["scale"]
            assert (mouth.scale - Vector([a * b for a, b in zip(rest_scale, factors)])).length < 1e-6
            posed = matrices()
            assert all(matrix == rest_matrices[name] for name, matrix in posed.items() if name != mouth.name)
            shape = check_mouth(viseme, posed)
            assert shapes.setdefault(viseme, shape) == shape
        check_rest()

    assert shapes["OPEN"][1] > 2 * shapes[second][1]
    assert shapes["REST"] != shapes["OPEN"]

    for emotion, transforms in EXPRESSIONS.items():
        saved = apply_expression(character, emotion)
        try:
            posed = matrices()
            expected_changes = {part(suffix).name for suffix in transforms}
            assert {name for name, matrix in posed.items() if matrix != rest_matrices[name]} == expected_changes
            check_mouth(emotion, posed)
            with viseme_pose(mouth, "OPEN"):
                speech_pose = matrices()
                assert all(matrix == posed[name] for name, matrix in speech_pose.items() if name != mouth.name)
                check_mouth("OPEN", speech_pose)
            assert matrices() == posed
        finally:
            restore_expression(saved)
        check_rest()

    print("FACIAL_PREVIEW_GEOMETRY_OK")


if __name__ == "__main__":
    main()
