"""
garden_utils.py - Shared helpers for building the reusable cartoon garden
environment. Runs inside Blender Python (bpy). Compatible with Blender 4.4.3.

Every material sets BOTH diffuse_color and the owning object's .color so that
Workbench MATERIAL shading displays the intended colours in background renders.
"""
import bpy
import math
import mathutils


# ---------------------------------------------------------------------------
# Counters (reset implicitly per Blender process). Names become Tree_01.. etc.
# ---------------------------------------------------------------------------
_tree_counter = [0]
_bush_counter = [0]
_flower_counter = [0]
_stone_counter = [0]
_cloud_counter = [0]


def hex_to_rgba(hex_color, alpha=1.0):
    """Convert '#RRGGBB' to a normalized (r, g, b, a) tuple."""
    h = hex_color.lstrip('#')
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return (r, g, b, alpha)


def create_material(name, hex_color):
    """Create or reuse a material; set diffuse_color and Principled BSDF base
    colour. Returns (material, rgba) so callers can also set object.color."""
    rgba = hex_to_rgba(hex_color)
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.diffuse_color = rgba
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
    return mat, rgba


def assign_material(obj, mat, rgba):
    """Assign material to a mesh object and set object.color (Workbench)."""
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    obj.color = rgba


def add_to_collection(obj, collection_name):
    """Ensure object is in the named collection, unlinking it from all others."""
    coll = bpy.data.collections.get(collection_name)
    if coll is None:
        coll = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(coll)
    if obj.name not in [o.name for o in coll.objects]:
        coll.objects.link(obj)
    for c in list(obj.users_collection):
        if c.name != collection_name:
            c.objects.unlink(obj)


def add_smooth_shading(obj):
    """Smooth-shade all polygons of a mesh object."""
    if obj.type != 'MESH':
        return
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.data.update()


def _new_mesh_primitive(add_callable, name, location, collection):
    """Run a bpy.ops mesh primitive add, rename, place, and move to collection."""
    add_callable()
    obj = bpy.context.active_object
    obj.name = name
    obj.location = location
    add_to_collection(obj, collection)
    return obj


# ---------------------------------------------------------------------------
# Camera helper (matches render_character_preview.py set_camera)
# ---------------------------------------------------------------------------
def set_camera(cam_obj, pos, target):
    cam_obj.location = pos
    direction = mathutils.Vector(target) - mathutils.Vector(pos)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()


def create_camera(name, pos, target, lens):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_obj = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    add_to_collection(cam_obj, 'Cameras')
    set_camera(cam_obj, pos, target)
    return cam_obj


# ---------------------------------------------------------------------------
# Workbench configuration (exact block)
# ---------------------------------------------------------------------------
def configure_workbench(scene):
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    shading = scene.display.shading
    shading.light = 'STUDIO'
    shading.color_type = 'MATERIAL'
    shading.show_shadows = True
    shading.show_cavity = True
    try:
        shading.show_object_outline = True
    except AttributeError:
        pass
    # Workbench background colour: set the viewport/background colour directly.
    # The world node tree is only used by EEVEE/Cycles; Workbench uses
    # scene.world.color (the flat viewport background) in background mode.
    _set_workbench_background_color(scene, '#87CEEB')


def _set_workbench_background_color(scene, hex_color):
    """Set the Workbench background to a solid colour.
    Workbench ignores world node trees; it reads scene.world.color directly."""
    rgba = hex_to_rgba(hex_color)
    if scene.world is None:
        scene.world = bpy.data.worlds.new('GardenWorld')
    # Use nodes=False so Workbench reads world.color as a flat background
    scene.world.use_nodes = False
    scene.world.color = rgba[:3]  # world.color is RGB not RGBA


# ---------------------------------------------------------------------------
# World background
# ---------------------------------------------------------------------------
def create_world_background(hex_color='#87CEEB'):
    """Set world background colour for Workbench rendering.
    Workbench uses world.color (not world node tree) in background mode.
    Sets use_nodes=False so the flat colour is used."""
    scene = bpy.context.scene
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new('GardenWorld')
        scene.world = world
    # Workbench reads world.color directly; node tree is for EEVEE/Cycles only
    world.use_nodes = False
    rgba = hex_to_rgba(hex_color)
    world.color = rgba[:3]


# ---------------------------------------------------------------------------
# Ground + path
# ---------------------------------------------------------------------------
def create_ground():
    """20x20 grass plane at Z=0 plus a few darker variation patches."""
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = 'Ground_Plane'
    mat, rgba = create_material('Mat_Grass', '#4CAF50')
    assign_material(plane, mat, rgba)
    add_to_collection(plane, 'Environment_Ground')

    mat_dark, rgba_dark = create_material('Mat_Grass_Dark', '#388E3C')
    patches = [((-4.0, 3.0), 4.0), ((5.0, -2.0), 5.0), ((-2.0, -5.0), 4.0)]
    for i, (pos, size) in enumerate(patches, 1):
        bpy.ops.mesh.primitive_plane_add(size=size, location=(pos[0], pos[1], 0.005))
        p = bpy.context.active_object
        p.name = f'Ground_Patch_{i:02d}'
        assign_material(p, mat_dark, rgba_dark)
        add_to_collection(p, 'Environment_Ground')
    return plane


def create_path():
    """Gently winding raised mesh strip (Z=0.01) running front-to-rear.
    The centre line follows x = 1.1*cos(2*pi*t) so the path bows to the left of
    the character performance area around (0,0) instead of crossing it."""
    n_seg = 24
    half_w = 0.4  # total width 0.8 BU
    y0, y1 = -9.0, 9.0
    pts = []
    for i in range(n_seg + 1):
        t = i / n_seg
        y = y0 + (y1 - y0) * t
        x = 1.1 * math.cos(2.0 * math.pi * t)
        pts.append((x, y))

    verts = []
    for i, (xc, yc) in enumerate(pts):
        if i == 0:
            dx, dy = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
        elif i == len(pts) - 1:
            dx, dy = pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1]
        else:
            dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        # perpendicular to the tangent
        px, py = dy, -dx
        plen = math.sqrt(px * px + py * py) or 1.0
        px, py = px / plen, py / plen
        left = (xc + px * half_w, yc + py * half_w, 0.01)
        right = (xc - px * half_w, yc - py * half_w, 0.01)
        verts.append(left)
        verts.append(right)

    faces = []
    for i in range(n_seg):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))

    mesh = bpy.data.meshes.new('Path_Main_Data')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new('Path_Main', mesh)
    bpy.context.scene.collection.objects.link(obj)
    mat, rgba = create_material('Mat_Path', '#D7CCC8')
    assign_material(obj, mat, rgba)
    add_to_collection(obj, 'Environment_Path')
    return obj


# ---------------------------------------------------------------------------
# Trees, bushes, flowers, stones, sign, bench, clouds, light
# ---------------------------------------------------------------------------
def create_tree(x, y, trunk_h=1.0, foliage_r=0.6, color='#66BB6A'):
    """Cylindrical trunk + icosphere foliage cluster."""
    _tree_counter[0] += 1
    idx = _tree_counter[0]

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=0.1, depth=trunk_h, location=(x, y, trunk_h / 2.0)
    )
    trunk = bpy.context.active_object
    trunk.name = f'Tree_{idx:02d}_Trunk'
    mat_t, rgba_t = create_material('Mat_Trunk', '#5D4037')
    assign_material(trunk, mat_t, rgba_t)
    add_to_collection(trunk, 'Environment_Trees')
    add_smooth_shading(trunk)

    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=2, radius=foliage_r, location=(x, y, trunk_h + foliage_r * 0.6)
    )
    foliage = bpy.context.active_object
    foliage.name = f'Tree_{idx:02d}_Foliage'
    mat_f, rgba_f = create_material(f'Mat_Foliage_{idx:02d}', color)
    assign_material(foliage, mat_f, rgba_f)
    add_to_collection(foliage, 'Environment_Trees')
    add_smooth_shading(foliage)
    return trunk, foliage


def create_bush(x, y, radius=0.4, color='#43A047'):
    """Rounded icosphere bush sitting on the ground (bottom at Z=0)."""
    _bush_counter[0] += 1
    idx = _bush_counter[0]
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=2, radius=radius, location=(x, y, radius)
    )
    bush = bpy.context.active_object
    bush.name = f'Bush_{idx:02d}'
    mat, rgba = create_material(f'Mat_Bush_{idx:02d}', color)
    assign_material(bush, mat, rgba)
    add_to_collection(bush, 'Environment_Bushes')
    add_smooth_shading(bush)
    return bush


def create_flower(x, y, petal_color='#F44336'):
    """Thin stem + 6-sided low-poly petal disc + tiny yellow centre sphere."""
    _flower_counter[0] += 1
    idx = _flower_counter[0]

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=6, radius=0.02, depth=0.3, location=(x, y, 0.15)
    )
    stem = bpy.context.active_object
    stem.name = f'Flower_{idx:02d}_Stem'
    mat_s, rgba_s = create_material('Mat_Stem', '#2E7D32')
    assign_material(stem, mat_s, rgba_s)
    add_to_collection(stem, 'Environment_Flowers')

    bpy.ops.mesh.primitive_circle_add(
        vertices=6, radius=0.08, fill_type='NGON', location=(x, y, 0.3)
    )
    petals = bpy.context.active_object
    petals.name = f'Flower_{idx:02d}_Petals'
    mat_p, rgba_p = create_material(f'Mat_Petals_{idx:02d}', petal_color)
    assign_material(petals, mat_p, rgba_p)
    add_to_collection(petals, 'Environment_Flowers')

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=8, ring_count=6, radius=0.04, location=(x, y, 0.32)
    )
    centre = bpy.context.active_object
    centre.name = f'Flower_{idx:02d}_Centre'
    mat_c, rgba_c = create_material('Mat_FlowerCentre', '#FFEB3B')
    assign_material(centre, mat_c, rgba_c)
    add_to_collection(centre, 'Environment_Flowers')
    add_smooth_shading(centre)
    return stem, petals, centre


def create_stone(x, y, radius=0.2):
    """Slightly squashed gray icosphere resting on the ground."""
    _stone_counter[0] += 1
    idx = _stone_counter[0]
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=2, radius=radius, location=(x, y, radius * 0.6)
    )
    stone = bpy.context.active_object
    stone.name = f'Stone_{idx:02d}'
    stone.scale.z = 0.6
    mat, rgba = create_material('Mat_Stone', '#9E9E9E')
    assign_material(stone, mat, rgba)
    add_to_collection(stone, 'Environment_Decorations')
    add_smooth_shading(stone)
    return stone


def create_sign(x, y):
    """Wooden signboard: cylindrical post + flat board."""
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=8, radius=0.04, depth=0.8, location=(x, y, 0.4)
    )
    post = bpy.context.active_object
    post.name = 'Sign_01_Post'
    mat, rgba = create_material('Mat_Sign', '#795548')
    assign_material(post, mat, rgba)
    add_to_collection(post, 'Environment_Decorations')

    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 0.7))
    board = bpy.context.active_object
    board.name = 'Sign_01_Board'
    board.scale = (0.5, 0.04, 0.2)
    mat_b, rgba_b = create_material('Mat_SignBoard', '#795548')
    assign_material(board, mat_b, rgba_b)
    add_to_collection(board, 'Environment_Decorations')
    return post, board


def create_bench(x, y):
    """Simple garden bench: seat board + two legs."""
    mat, rgba = create_material('Mat_Bench', '#6D4C41')

    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 0.45))
    seat = bpy.context.active_object
    seat.name = 'Bench_01_Seat'
    seat.scale = (1.2, 0.3, 0.05)
    assign_material(seat, mat, rgba)
    add_to_collection(seat, 'Environment_Decorations')

    legs = []
    for dx, side in ((-0.5, 'L'), (0.5, 'R')):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x + dx, y, 0.2))
        leg = bpy.context.active_object
        leg.name = f'Bench_01_Leg_{side}'
        leg.scale = (0.08, 0.25, 0.4)
        assign_material(leg, mat, rgba)
        add_to_collection(leg, 'Environment_Decorations')
        legs.append(leg)
    return seat, legs


def create_cloud(x, y, z, scale=1.0):
    """Elongated white icosphere cloud in the sky."""
    _cloud_counter[0] += 1
    idx = _cloud_counter[0]
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=2, radius=0.6 * scale, location=(x, y, z)
    )
    cloud = bpy.context.active_object
    cloud.name = f'Cloud_{idx:02d}'
    cloud.scale = (1.8 * scale, 0.8 * scale, 0.5 * scale)
    mat, rgba = create_material('Mat_Cloud', '#FFFFFF')
    assign_material(cloud, mat, rgba)
    add_to_collection(cloud, 'Environment_Sky')
    add_smooth_shading(cloud)
    return cloud


def create_sun_light():
    """Sun lamp, energy 3.0, ~45 deg elevation, warm white."""
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 8))
    sun = bpy.context.active_object
    sun.name = 'Sun_Light'
    sun.data.energy = 3.0
    sun.data.color = (1.0, 0.95, 0.85)
    sun.rotation_euler = (math.radians(45), math.radians(10), math.radians(30))
    add_to_collection(sun, 'Lighting')
    return sun
