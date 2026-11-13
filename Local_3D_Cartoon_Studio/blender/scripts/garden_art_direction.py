"""Optional art direction for a warmer, more detailed garden cut."""

from math import cos, sin, tau
from random import Random

import bpy
from mathutils import Vector

from garden_utils import assign_material, create_material


def color(name, value):
    return create_material(f"GardenCut_{name}", value)


def paint(obj, material):
    assign_material(obj, *material)


def rounded_mesh(name, location, scale, material, *, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = location
    obj.scale = scale
    paint(obj, material)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def soften_character(root):
    """Round the existing rigid pieces while keeping the action pivots intact."""
    name = root.name.split("_", 1)[0]
    is_aarav = name == "Aarav"
    front = 1 if is_aarav else -1
    outfit = color(name + "_outfit", "#2785AD" if is_aarav else "#D6629C")
    trim = color(name + "_trim", "#FFD36B" if is_aarav else "#F8C079")
    eye = color(name + "_iris", "#322036")
    glint = color("Eye glint", "#FFFFFF")
    for obj in list(root.children):
        if obj.type != "MESH":
            continue
        part = obj.name.split("_", 1)[1]
        if part.startswith(("Torso", "Skirt", "UpperArm")):
            paint(obj, outfit)
        if part.startswith(("Torso", "Skirt", "Hand", "Foot", "Eyebrow", "Hijab_Side", "Hijab_Back")):
            bevel = obj.modifiers.new("Rounded edges", "BEVEL")
            bevel.width = 0.52 if part.startswith(("Hand", "Foot", "Hijab")) else 0.34
            bevel.segments = 4
            bevel.harden_normals = True
            for face in obj.data.polygons:
                face.use_smooth = True
            normals = obj.modifiers.new("Soft corner normals", "WEIGHTED_NORMAL")
            normals.keep_sharp = True
        if part.startswith("Iris"):
            paint(obj, eye)
            rounded_mesh(
                f"{obj.name}_Highlight", (-0.26, front * 0.88, 0.35),
                (0.23, 0.17, 0.22), glint, parent=obj,
            )
        if part == "Torso":
            for index in range(3):
                rounded_mesh(
                    f"{name}_CoatButton_{index}", (0, front * 1.01, 0.38 - index * 0.32),
                    (0.071, 0.10, 0.076), trim, parent=obj,
                )
        if part.startswith("Foot"):
            paint(obj, color(name + "_shoes", "#DF8F46" if is_aarav else "#AD5192"))


def flower_beds():
    """Build scattered petal rosettes and foliage as a single lightweight mesh."""
    rng = Random(910)
    palette = [
        color("Leaf", "#5B9C57"), color("Gold", "#FFD365"), color("Rose", "#ED79A0"),
        color("Lilac", "#B8A3EE"), color("Ivory", "#FFF1D9"),
    ]
    vertices, faces, indices = [], [], []

    def face(points, material):
        start = len(vertices)
        vertices.extend(points)
        faces.append(tuple(range(start, len(vertices))))
        indices.append(material)

    # Keep the center of the walking lane and the actors' marks open.
    for cx, cy, spread in ((-2.25, 0.7, 0.48), (2.1, 0.4, 0.48), (-2.0, -2.2, 0.65),
                           (1.95, -2.2, 0.65), (0.15, -3.4, 0.75), (-2.6, 2.1, 0.4),
                           (2.5, 2.25, 0.4), (0.0, 2.25, 0.32)):
        for _ in range(21):
            x, y = cx + rng.uniform(-spread, spread), cy + rng.uniform(-0.47, 0.47)
            height, radius = rng.uniform(0.09, 0.21), rng.uniform(0.033, 0.065)
            face(((x - .013, y, .015), (x + .013, y, .015), (x + .02, y, height)), 0)
            face(((x, y, .025), (x - .07, y - .025, height * .56), (x - .026, y, height * .63)), 0)
            shade = rng.randint(2, 4)
            for i in range(5):
                a = i * tau / 5
                face(
                    [(x + r * cos(a + d), y + r * sin(a + d), height + z)
                     for r, d, z in ((.011, -.36, 0), (radius, -.45, .016),
                                     (radius, .45, .023), (.011, .36, 0))], shade,
                )
            face([(x + .018 * cos(i * tau / 6), y + .018 * sin(i * tau / 6), height + .006)
                  for i in range(6)], 1)
    mesh = bpy.data.meshes.new("Wildflower bed mesh")
    mesh.from_pydata(vertices, [], faces)
    for material, _ in palette:
        mesh.materials.append(material)
    for polygon, index in zip(mesh.polygons, indices, strict=True):
        polygon.material_index = index
    obj = bpy.data.objects.new("Wildflower beds", mesh)
    bpy.context.scene.collection.objects.link(obj)


def dress_garden(scene):
    """Apply a warm palette and layered foliage in the render process only."""
    shading = scene.display.shading
    shading.studiolight_rotate_z = 0.35
    shading.show_object_outline = False
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.cavity_ridge_factor = 0.25
    shading.cavity_valley_factor = 0.65
    shading.show_shadows = True
    shading.shadow_intensity = 0.22
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.35
    scene.world.color = (0.32, 0.58, 0.77)
    grass = color("Grass", "#74AA57")
    path = color("Sand path", "#E8C992")
    greens = [color(f"Canopy {i}", shade) for i, shade in enumerate(("#699D50", "#7AB859", "#91BB56", "#55946B"))]
    trees = []
    for obj in list(scene.objects):
        if obj.type != "MESH":
            continue
        if obj.name.startswith("Ground"):
            paint(obj, grass)
        elif obj.name.startswith("Path"):
            paint(obj, path)
        elif "Canopy" in obj.name or "Foliage" in obj.name or obj.name.startswith("Bush"):
            paint(obj, greens[len(trees) % len(greens)])
            for face in obj.data.polygons:
                face.use_smooth = True
            if obj.name.startswith("Tree"):
                trees.append(obj)
    for i, tree in enumerate(trees):
        for dx, dy, dz in ((-.27, -.03, .04), (.24, .04, .16), (.02, .03, .32)):
            rounded_mesh(
                f"Canopy lobe {i}", tree.location + Vector((dx, dy, dz)),
                (.39, .39, .32), greens[(i + int(dz * 10)) % len(greens)],
            )
    hills = [color("Far hill", "#81BD98"), color("Near hill", "#75AD80")]
    for index, x in enumerate((-7, -4.2, -1.5, 1.3, 4.2, 7)):
        rounded_mesh(f"Distant hill {index}", (x, -9 + index % 2, -0.33),
                     (2.15, 1.0, 0.63 + 0.12 * (index % 3)), hills[index % 2])
    for index, (x, y, z) in enumerate(((-3.1, -7, 2.05), (-.85, -7, 2.4), (2.95, -8, 2.24), (4.8, -8, 2.1))):
        for dx, dz in ((-.38,0),(.01,.09),(.37,-.015)):
            rounded_mesh(f"Cloud puff {index}", (x+dx,y,z+dz), (.49,.28,.17), color("Cloud", "#F2FAFB"))
    flower_beds()
