"""Build prompt-designed props from validated geometric parts."""

from math import radians

import bpy
from mathutils import Vector

from garden_utils import assign_material, create_material


# The story camera looks from positive Y, so positive X is screen left.
PROP_SLOTS = {
    "screen_left": (1.85, 0.9),
    "center": (0, 1.2),
    "screen_right": (-1.85, 0.9),
}


def add_story_props(props):
    mesh_builders = {
        "box": bpy.ops.mesh.primitive_cube_add,
        "sphere": bpy.ops.mesh.primitive_uv_sphere_add,
        "cylinder": bpy.ops.mesh.primitive_cylinder_add,
        "cone": bpy.ops.mesh.primitive_cone_add,
        "torus": bpy.ops.mesh.primitive_torus_add,
    }
    for prop in props:
        meshes = []
        corners = []
        for index, part in enumerate(prop["parts"], 1):
            mesh_builders[part["shape"]]()
            obj = bpy.context.object
            obj.name = f"Story prop {prop['name']} - {index}"
            obj.scale = tuple(size / dimension for size, dimension in zip(part["size"], obj.dimensions))
            obj.location = part["center"]
            obj.rotation_euler = tuple(map(radians, part.get("rotation", (0, 0, 0))))
            color = part["color"]
            assign_material(obj, *create_material(f"Story prop {color.upper()}", color))
            meshes.append(obj)

        bpy.context.view_layer.update()
        for obj in meshes:
            corners.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
        minimum = Vector(tuple(min(point[axis] for point in corners) for axis in range(3)))
        maximum = Vector(tuple(max(point[axis] for point in corners) for axis in range(3)))
        span = maximum - minimum
        center = (minimum + maximum) / 2
        anchor = Vector((center.x, center.y, minimum.z))
        # Keep props in their own lanes and below the performers' faces.
        width = 0.65 if prop["position"] == "center" else 0.95
        scale = min(1, width / span.x, 0.7 / span.y, 0.85 / span.z)
        placement = Vector((*PROP_SLOTS[prop["position"]], 0.025))
        for obj in meshes:
            obj.location = placement + scale * (obj.location - anchor)
            obj.scale *= scale
