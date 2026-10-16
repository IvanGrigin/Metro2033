"""Locations built from code. The same builder always produces the same geometry, so every scene
and every camera in a location share one set. Axes: +Y north, X across, Z up, floor z = 0."""
import bpy, bmesh, math, random
from mathutils import Vector
from kit import mat, put, box, cyl, sphere, cone, empty, attach

R, CZ = 2.55, 1.6  # Moscow running tunnel: inner radius, axis height above the trackbed


def wall_x(z, side):
    return side * math.sqrt(max(R * R - (z - CZ) ** 2, 0))


def half_tube(name, radius, length, center, m, a0=0.0, a1=180.0, segs=32, zscale=1.0):
    """Open arched vault along Y: an arc of `radius` from angle a0 to a1 (degrees, 0 = +X, 90 = up) around
    `center` (x, z), extruded over `length`. Unlike a full cylinder it leaves everything below open."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rows = []
    for y in (-length / 2, length / 2):
        rows.append([bm.verts.new((center[0] + radius * math.cos(math.radians(a0 + (a1 - a0) * i / segs)), y,
                                   center[1] + zscale * radius * math.sin(math.radians(a0 + (a1 - a0) * i / segs))))
                     for i in range(segs + 1)])
    for i in range(segs):
        bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return put(o, m)


def arch_spandrel(x, y0, y1, z_spring, z_top, m, soffit_m, thick=1.5, segs=12):
    """Wall above a round-headed passage between pylons (spans y0..y1, crown at z_top, springing at z_top - r):
    the two corner pieces are triangle fans from the top corners (a concave n-gon would be filled solid), and the
    curved underside of the arch is a separate strip in `soffit_m` (green on the real station)."""
    r = (y1 - y0) / 2
    yc, zc = (y0 + y1) / 2, z_top - r
    arc = [(yc + r * math.cos(math.radians(180 - 180 * i / segs)), zc + r * math.sin(math.radians(180 - 180 * i / segs)))
           for i in range(segs + 1)]  # from (y0, zc) over the crown to (y1, zc)
    me = bpy.data.meshes.new("arch_spandrel")
    bm = bmesh.new()
    for side in (-1, 1):
        xs = x + side * thick / 2
        left, right = bm.verts.new((xs, y0, z_top)), bm.verts.new((xs, y1, z_top))
        av = [bm.verts.new((xs, py, pz)) for py, pz in arc]
        half = segs // 2
        for i in range(half):  # left fan from the top-left corner
            bm.faces.new((left, av[i], av[i + 1]))
        for i in range(half, segs):  # right fan from the top-right corner
            bm.faces.new((right, av[i], av[i + 1]))
        bm.faces.new((left, av[half], right))
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("arch_spandrel", me)
    bpy.context.scene.collection.objects.link(o)
    put(o, m)
    me2 = bpy.data.meshes.new("arch_soffit")  # underside of the arch
    bm = bmesh.new()
    rows = [[bm.verts.new((x + side * thick / 2, py, pz)) for py, pz in arc] for side in (-1, 1)]
    for i in range(segs):
        bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
    bm.to_mesh(me2)
    bm.free()
    o2 = bpy.data.objects.new("arch_soffit", me2)
    bpy.context.scene.collection.objects.link(o2)
    put(o2, soffit_m)


def running_tunnel(length=90.0, x=0.0, y=0.0, lining="iron"):
    """Cast-iron ring tunnel, single 1520 mm track on the axis, third rail on the right, wall cables.
    Built along Y centred on (x, y)."""
    before = set(bpy.context.scene.objects)
    iron = mat("cast_iron", (0.10, 0.08, 0.07), flat=(0.42, 0.42, 0.45), rough=0.6, metal=0.6)
    conc = mat("concrete", (0.20, 0.18, 0.16), flat=(0.33, 0.32, 0.30))
    rust = mat("rail_rust", (0.22, 0.12, 0.07), flat=(0.70, 0.72, 0.78), rough=0.5, metal=0.8)
    wood = mat("old_wood", (0.13, 0.08, 0.05), flat=(0.45, 0.30, 0.15))
    cable = mat("cable", (0.03, 0.03, 0.03), flat=(0.12, 0.12, 0.12), rough=0.5)
    shell_mat = mat("rc_blocks", (0.22, 0.21, 0.19), flat=(0.55, 0.55, 0.52), rough=0.8) if lining == "concrete" else iron
    cyl(R + 0.15, length, (0, 0, CZ), shell_mat, rot=(math.pi / 2, 0, 0), verts=64, name="tunnel_shell")
    if lining == "concrete":  # reinforced-concrete blocks: smooth wall, only thin joints every metre
        iron = shell_mat
    bpy.ops.mesh.primitive_torus_add(major_radius=R + (0.06 if lining == "concrete" else 0), minor_radius=0.07 if lining == "iron" else 0.02,
                                     major_segments=64, minor_segments=8, location=(0, -length / 2, CZ), rotation=(math.pi / 2, 0, 0))
    ring = put(bpy.context.object, iron, "ring_flanges")
    bpy.ops.object.transform_apply(rotation=True)
    _array_y(ring, int(length), 1.0)
    box((2 * abs(wall_x(0, 1)), length, 1.0), (0, 0, -0.5), conc, name="trackbed")
    s = box((2.7, 0.25, 0.14), (0, -length / 2, 0.07), wood, name="sleepers")
    _array_y(s, int(length / 0.55), 0.55)
    for rx in (-0.795, 0.795):  # gauge 1520 mm between inner faces; not `x`: that is the tunnel offset applied below
        box((0.07, length, 0.15), (rx, 0, 0.215), rust, name="rail")
    box((0.08, length, 0.10), (1.55, 0, 0.40), rust, name="third_rail")
    box((0.30, length, 0.02), (1.55, 0, 0.55), wood, name="third_rail_cover")
    for side in (-1, 1):
        for i, z in enumerate((1.15, 1.30, 1.45, 1.60, 1.75)):
            cyl(0.025 + 0.008 * (i % 2), length, (wall_x(z, side) - side * 0.18, 0, z), cable,
                rot=(math.pi / 2, 0, 0), verts=8, name="cable")
    for o in set(bpy.context.scene.objects) - before:  # shift only what this call created
        if o.parent is None:
            o.location.x += x
            o.location.y += y


def _array_y(o, count, step):
    a = o.modifiers.new("arr", "ARRAY")
    a.count, a.use_relative_offset, a.use_constant_offset = count, False, True
    a.constant_offset_displace = (0, step / o.scale.y, 0)  # the offset is in object space, so undo the box's own scale


def wall_number(text, y, side=-1, z=2.15):
    """Painted kilometre mark, centred on (y, z); above the cable run (cables end at z 1.78)."""
    paint = mat("white_paint", (0.75, 0.75, 0.72), flat=(1, 1, 1), rough=0.7)
    bpy.ops.object.text_add(location=(wall_x(z + 0.25, side) - side * 0.04, y, z),
                            rotation=(math.pi / 2, 0, math.pi / 2 if side < 0 else -math.pi / 2))
    t = bpy.context.object
    t.data.body, t.data.size, t.data.extrude = text, 0.45, 0.005
    t.data.align_x, t.data.align_y = "CENTER", "CENTER"
    return put(t, paint, f"mark_{text}")


def striped_post(text, x, y):
    paint = mat("white_paint", (0.75, 0.75, 0.72), flat=(1, 1, 1), rough=0.7)
    black = mat("black_paint", (0.02, 0.02, 0.02), flat=(0.02, 0.02, 0.02), rough=0.7)
    # white paint (bands and plate) glows faintly: the far firelight it catches, so the striped post can be made out
    # at the edge of the dark (script: «за кругом света, в темноте»)
    glint = mat("post_glint_paint", (0.75, 0.75, 0.72), flat=(1, 1, 1), rough=0.7, emit=(1.0, 0.7, 0.45), strength=0.15)
    for k in range(8):
        cyl(0.06, 0.18, (x, y, 0.09 + k * 0.18), glint if k % 2 else black, verts=12, name=f"post_{text}")
    box((0.35, 0.02, 0.22), (x, y - 0.07, 1.55), glint, name=f"post_{text}_plate")
    bpy.ops.object.text_add(location=(x, y - 0.085, 1.55), rotation=(math.pi / 2, 0, 0))
    t = bpy.context.object
    t.data.body, t.data.size = text, 0.16
    t.data.align_x, t.data.align_y = "CENTER", "CENTER"
    put(t, black, f"post_{text}_text")


def campfire(at, energy=90):
    """Split sleeper pieces, embers, flames (no shadows: the light sits inside), flickering point light,
    tripod with a kettle (one spout, one handle), two mugs on a sleeper end."""
    from kit import mug
    f = Vector(at)
    char = mat("charred", (0.03, 0.02, 0.02), flat=(0.20, 0.12, 0.08))
    flame = mat("flame", (1, 0.5, 0.1), flat=(1.0, 0.62, 0.10), rough=1, emit=(1.0, 0.45, 0.08), strength=25.0)
    ember = mat("ember", (1, 0.3, 0.05), flat=(1.0, 0.35, 0.05), rough=1, emit=(1.0, 0.25, 0.03), strength=8.0)
    soot = mat("sooty_metal", (0.04, 0.035, 0.03), flat=(0.25, 0.25, 0.27), rough=0.6, metal=0.7)
    for a in (0, 60, 120):
        cyl(0.07, 0.8, (f.x, f.y, 0.07), char, rot=(math.pi / 2, 0, math.radians(a)), verts=10, name="fire_log")
    sphere(0.28, (f.x, f.y, 0.08), ember, name="embers", scale=(1, 1, 0.25)).visible_shadow = False
    for dx, dy, h in ((0, 0, 0.7), (0.1, 0.05, 0.45), (-0.08, -0.06, 0.5)):
        cone(0.14, 0, h, (f.x + dx, f.y + dy, 0.12 + h / 2), flame, name="flame").visible_shadow = False
    bpy.ops.object.light_add(type="POINT", location=(f.x, f.y, 0.55))
    li = bpy.context.object
    li.name = "fire_light"
    li.data.energy, li.data.color, li.data.shadow_soft_size = energy, (1.0, 0.52, 0.22), 0.25
    li.data.keyframe_insert("energy", frame=1)
    noise = li.data.animation_data.action.fcurves[0].modifiers.new("NOISE")
    noise.scale, noise.strength = 3.0, energy * 0.35  # firelight flicker
    for a in (0, 120, 240):
        ang = math.radians(a)
        p = Vector((math.cos(ang) * 0.45, math.sin(ang) * 0.45, 0.45))
        cyl(0.012, 1.0, f + p, soot, rot=(math.sin(ang) * 0.45, -math.cos(ang) * 0.45, 0), verts=6, name="tripod")
    sphere(0.13, (f.x, f.y, 0.78), soot, name="kettle", scale=(1, 1, 0.8))
    cyl(0.02, 0.18, (f.x + 0.14, f.y, 0.83), soot, rot=(0, math.radians(55), 0), verts=8, name="kettle_spout")
    bpy.ops.mesh.primitive_torus_add(major_radius=0.1, minor_radius=0.008, location=(f.x, f.y, 0.92), rotation=(math.pi / 2, 0, 0))
    put(bpy.context.object, soot, "kettle_handle")
    for i, (dx, dy) in enumerate(((0.55, -0.45), (0.68, -0.32))):
        m = mug(f"mug_sleeper_{i}")
        m.location = (f.x + dx, f.y + dy, 0.14)


def tunnel_250():
    """VDNKh north tunnel at the 250 m mark: scenes 1, 4, 6, 15. Fire at (-1.3, 0). Single-track tube (the turnback
    dead ends north of VDNKh are single-track deep tunnels); toward Botanichesky Sad the 1978 tunnels are lined with
    reinforced-concrete blocks, not cast-iron rings (russos.livejournal.com/1302721, see WORLD.md)."""
    running_tunnel(length=220.0, lining="concrete")  # long enough that its end is lost in the dark and haze behind «300»
    wall_number("250", -1.2)
    striped_post("300", -1.9, 48.8)  # 50 m on, beyond the firelight, in the dark (script line 18)
    campfire((-1.3, 0.0, 0.0))





# ---------------------------------------------------------------- set dressing helpers

def _rng(seed):
    return random.Random(seed)


def lamp_row(xs, ys, z, color, energy, name="lamp"):
    """Ceiling lamps: small glowing boxes with point lights."""
    glow = mat(f"{name}_glow", color, flat=(1, 0.95, 0.8), emit=color, strength=6)
    for x in xs:
        for y in ys:
            box((0.5, 0.2, 0.08), (x, y, z), glow, name=name).visible_shadow = False
            bpy.ops.object.light_add(type="POINT", location=(x, y, z - 0.2))
            li = bpy.context.object
            li.name = f"{name}_light"
            li.data.energy, li.data.color, li.data.shadow_soft_size = energy, color, 0.3
            li.data.use_shadow = False


def _drop_faces(o, normal):
    """Delete the mesh faces whose local normal points along `normal` (open a box top, a prism bottom)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    n = Vector(normal)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.dot(n) > 0.9], context="FACES")
    bm.to_mesh(o.data)
    bm.free()


def army_tent(name, at, facing=0.0, size=(2.2, 2.8), h=1.9, rgb=(0.20, 0.22, 0.14), flat=(0.40, 0.48, 0.30), open_flap=False):
    """Ridge tent made of a box and a prism roof; door flap on the +Y side (after `facing`)."""
    root = empty(name)
    canvas = mat(f"canvas_{flat}", rgb, flat=flat, rough=0.95)
    w, d = size
    wall = attach(box((w, d, h * 0.65), (0, 0, 0), canvas, name=f"{name}.wall"), root, (0, 0, h * 0.325))
    _drop_faces(wall, (0, 0, 1))  # open top: inside, the tent is as high as its ridge (people stand, cameras fit)
    bpy.ops.mesh.primitive_cylinder_add(vertices=3, radius=w * 0.58, depth=d, location=(0, 0, 0), rotation=(math.pi / 2, 0, 0))
    roof = put(bpy.context.object, canvas, f"{name}.roof")
    _drop_faces(roof, (0, -1, 0))  # the prism's flat underside
    roof.scale = (1, 0.55, 1)
    attach(roof, root, (0, 0, h * 0.65 + w * 0.14), (math.pi / 2, 0, math.pi / 2 * 0))
    if open_flap:  # a real opening in the front wall: two side panels, the middle 0.45 w open
        _drop_faces(wall, (0, 1, 0))
        for sx in (-1, 1):
            attach(box((w * 0.275, 0.02, h * 0.65), (0, 0, 0), canvas, name=f"{name}.front"), root, (sx * w * 0.3625, d / 2, h * 0.325))
    root.location = (at[0], at[1], 0)
    root.rotation_euler = (0, 0, math.radians(-facing))
    return root


def scatter_crates(rng, area, n, z=0.0, name="crate"):
    wood = mat("crate_wood", (0.12, 0.09, 0.06), flat=(0.55, 0.40, 0.25))
    (x0, x1), (y0, y1) = area
    for i in range(n):
        s = rng.uniform(0.35, 0.6)
        box((s, s * rng.uniform(0.8, 1.3), s * rng.uniform(0.6, 1.0)), (rng.uniform(x0, x1), rng.uniform(y0, y1), z + s * 0.3),
            wood, rot=(0, 0, rng.uniform(0, 3.14)), name=name)


def scatter_debris(rng, area, n, z=0.0):
    junk = mat("debris", (0.10, 0.09, 0.08), flat=(0.38, 0.36, 0.33))
    (x0, x1), (y0, y1) = area
    for i in range(n):
        s = rng.uniform(0.05, 0.3)
        box((s, s * rng.uniform(0.5, 2), s * 0.3), (rng.uniform(x0, x1), rng.uniform(y0, y1), z + 0.03), junk,
            rot=(rng.uniform(0, 0.4), rng.uniform(0, 0.4), rng.uniform(0, 3.14)), name="debris")


def laundry_line(a, b, z, rng):
    rope = mat("cable", (0.03, 0.03, 0.03), flat=(0.12, 0.12, 0.12), rough=0.5)
    cloth = mat("laundry", (0.35, 0.33, 0.30), flat=(0.85, 0.85, 0.80))
    a, b = Vector(a), Vector(b)
    d = b - a
    cyl(0.008, d.length, ((a + b) / 2).to_tuple()[:2] + (z,), rope, rot=(math.pi / 2, 0, math.atan2(-d.x, d.y)), verts=4, name="rope")
    for i in range(int(d.length / 0.6)):
        p = a + d * ((i + 0.5) / int(d.length / 0.6))
        box((0.35, 0.02, rng.uniform(0.3, 0.6)), (p.x, p.y, z - 0.25), cloth, rot=(0, 0, math.atan2(-d.x, d.y)), name="laundry")


def wall_clock(text, at, facing=180.0):
    """Station clock: a black box with glowing red digits, facing -Y by default (toward the platform)."""
    box((1.4, 0.15, 0.45), at, mat("clock_box", (0.02, 0.02, 0.02), flat=(0.05, 0.05, 0.05)), name="clock")
    bpy.ops.object.text_add(location=(at[0] - 0.55, at[1] - 0.09 if facing == 180 else at[1] + 0.09, at[2] - 0.15),
                            rotation=(math.pi / 2, 0, 0 if facing == 180 else math.pi))
    t = bpy.context.object
    t.data.body, t.data.size = text, 0.32
    put(t, mat("clock_digits", (1, 0.1, 0.05), flat=(1, 0.2, 0.1), emit=(1, 0.08, 0.03), strength=8), "clock_digits")


# ---------------------------------------------------------------- station archetypes

PLAT_H = 1.1  # platform top above the station floor datum z = 0
TRACK_Z = -0.29  # station trackbed level: rail head (0.29 above the trackbed) ends 1.1 m below the platform edge
# Real dimensions and world facts with sources: storyboard/3d/WORLD.md.
KINDS = {
    # VDNKh: pylon three-vault deep station, central hall 9.5 m, platform 162 m, 18 pylons a side (9 m pitch:
    # 6 m pylon + 3 m arched passage ~4 m high), white marble, green bevels, round medallions, benches, chandeliers.
    "pylon": {"plat_half": 8.25, "track_x": 9.85, "wall_x": 11.65},  # side naves: ~2 m platform strip beyond the pylons (estimate)
    # Timiryazevskaya: single-vault deep station (Leningrad design): one ribbed vault over platform and tracks,
    # a central row of lamp columns with benches, yellow-grey marble walls with a black stripe.
    "single_vault": {"plat_half": 5.0, "track_x": 6.4, "wall_x": 8.2},
    # Botanichesky Sad: shallow three-span column station: two rows of 26 square white-marble columns at 6.5 m,
    # platform 10.5 m, flat coffered gold ceiling about 4 m above the platform.
    "column": {"plat_half": 5.25, "track_x": 6.65, "wall_x": 8.45},
}


def station(kind="pylon", length=162.0, light=(1.0, 0.25, 0.15), energy=180, lamps_every=9.0, seed=1, north_opening=0.0):
    """Island-platform station along Y centred on 0: platform top z = 1.1, tracks at x = ±track_x on z = 0.
    Tunnel mouths at both ends on each track. Returns the dimensions used."""
    K = KINDS[kind]
    ph, tx_, wx = K["plat_half"], K["track_x"], K["wall_x"]
    marble = mat("marble", (0.42, 0.40, 0.37), flat=(0.80, 0.78, 0.74), rough=0.35)
    floor = mat("granite_floor", (0.20, 0.14, 0.12), flat=(0.55, 0.42, 0.38), rough=0.5)
    conc = mat("vault_plaster", (0.38, 0.37, 0.35), flat=(0.72, 0.72, 0.70))
    wood = mat("old_wood", (0.13, 0.08, 0.05), flat=(0.45, 0.30, 0.15))
    rust = mat("rail_rust", (0.22, 0.12, 0.07), flat=(0.70, 0.72, 0.78), rough=0.5, metal=0.8)
    dark = mat("dark_inside", (0.01, 0.01, 0.01), flat=(0.1, 0.1, 0.1))
    box((2 * ph, length, PLAT_H - TRACK_Z), (0, 0, (PLAT_H + TRACK_Z) / 2), floor, name="platform")
    for sx in (-1, 1):  # skirts under the side walls down to the lowered trackbed
        box((1.2, length, -TRACK_Z), (sx * (wx - 0.2), 0, TRACK_Z / 2), marble, name="wall_skirt")
    box((2 * wx + 1, length, 0.5), (0, 0, TRACK_Z - 0.25), mat("concrete", (0.20, 0.18, 0.16), flat=(0.33, 0.32, 0.30)), name="trackbed")
    for tx in (-tx_, tx_):
        sl = box((2.7, 0.25, 0.14), (tx, -length / 2, TRACK_Z + 0.07), wood, name="sleepers")
        _array_y(sl, int(length / 0.55), 0.55)
        for dx in (-0.795, 0.795):
            box((0.07, length, 0.15), (tx + dx, 0, TRACK_Z + 0.215), rust, name="rail")
    if kind == "pylon":
        yellow = mat("track_tile", (0.55, 0.45, 0.18), flat=(0.92, 0.82, 0.45))
        black = mat("black_tile", (0.03, 0.03, 0.03), flat=(0.10, 0.10, 0.10))
        green = mat("pylon_green", (0.05, 0.22, 0.12), flat=(0.15, 0.55, 0.30))
        for sx in (-1, 1):
            box((0.4, length, 1.6), (sx * (wx + 0.2), 0, 0.8), black, name="track_wall_low")
            box((0.4, length, 4.4), (sx * (wx + 0.2), 0, 3.8), yellow, name="track_wall_high")
            # arched roof over the side nave and track; the arc stops over the pylons so it never dips into the
            # central hall in front of the arches
            half_tube("side_vault", 4.4, length, (sx * (tx_ - 1.0), 3.4), conc, a0=0 if sx > 0 else 41, a1=139 if sx > 0 else 180)
        half_tube("central_vault", 4.75, length, (0, PLAT_H + 4.2), conc, segs=48, zscale=0.6)  # springs above the arches, crown ~7 m (photo)
        y = -length / 2
        pylons = 0
        while y + 6.0 <= length / 2 + 0.01:
            for sx in (-1, 1):
                cx = sx * 5.5
                box((1.5, 6.0, 4.2), (cx, y + 3.0, PLAT_H + 2.1), marble, name="pylon")
                for ey in (y + 0.1, y + 5.9):  # green bevels on the pylon ends, facing the arched passages
                    box((1.52, 0.2, 3.2), (cx, ey, PLAT_H + 1.8), green, name="pylon_bevel")
                box((1.5, 3.0, 0.9), (cx, y + 7.5, PLAT_H + 4.65), marble, name="arch_lintel")
                arch_spandrel(cx, y + 6.0, y + 9.0, PLAT_H + 2.7, PLAT_H + 4.2, marble, green)  # round arch, ~4.2 m at the crown
                cyl(0.45, 0.06, (sx * 4.72, y + 3.0, PLAT_H + 3.2), mat("medallion", (0.20, 0.16, 0.05), flat=(0.75, 0.62, 0.25), metal=0.8),
                    rot=(0, math.pi / 2, 0), verts=24, name="medallion")
                box((0.5, 2.4, 0.45), (sx * 4.35, y + 3.0, PLAT_H + 0.22), marble, name="bench")
            pylons += 1
            y += 9.0
        for sx in (-1, 1):  # side naves have their own lamps over the platform strip and track
            for cy in _range(-length / 2 + 4.5, length / 2 - 4.5, lamps_every * 2):
                bpy.ops.object.light_add(type="POINT", location=(sx * 7.6, cy, PLAT_H + 4.0))
                li = bpy.context.object
                li.name, li.data.energy, li.data.color, li.data.shadow_soft_size = "side_nave_light", energy * 0.6, light, 0.4
                li.data.use_shadow = False
        for cy in _range(-length / 2 + 4.5, length / 2 - 4.5, lamps_every):  # six-arm chandeliers along the axis
            cyl(0.02, 1.4, (0, cy, PLAT_H + 5.9), dark, verts=6, name="chandelier_rod")
            cyl(0.45, 0.6, (0, cy, PLAT_H + 4.9), mat("chandelier", (0.6, 0.55, 0.45), flat=(0.95, 0.90, 0.70), emit=light, strength=4), verts=6, name="chandelier")
            bpy.ops.object.light_add(type="POINT", location=(0, cy, PLAT_H + 4.6))
            li = bpy.context.object
            li.name, li.data.energy, li.data.color, li.data.shadow_soft_size = "chandelier_light", energy, light, 0.4
            li.data.use_shadow = False  # dozens of hall lights: shadows cost minutes per frame and add nothing to a reference
    elif kind == "single_vault":
        cyl(wx + 0.3, length, (0, 0, 1.5), conc, rot=(math.pi / 2, 0, 0), verts=64, name="vault")
        bpy.ops.mesh.primitive_torus_add(major_radius=wx + 0.05, minor_radius=0.12, major_segments=64, minor_segments=6,
                                         location=(0, -length / 2, 1.5), rotation=(math.pi / 2, 0, 0))
        rib = put(bpy.context.object, conc, "vault_ribs")
        bpy.ops.object.transform_apply(rotation=True)
        _array_y(rib, int(length / 2.0), 2.0)
        for sx in (-1, 1):
            box((0.4, length, 2.0), (sx * (wx - 0.6), 0, 1.0), marble, name="track_wall")
            box((0.42, length, 0.25), (sx * (wx - 0.6), 0, 1.6), mat("black_tile", (0.03, 0.03, 0.03), flat=(0.10, 0.10, 0.10)), name="black_stripe")
        for cy in _range(-length / 2 + 6, length / 2 - 6, 12.0):  # central row of lamp columns with benches
            cyl(0.18, 3.0, (0, cy, PLAT_H + 1.5), marble, verts=12, name="lamp_column")
            cyl(0.6, 0.3, (0, cy, PLAT_H + 3.1), mat("lamp_head", (0.6, 0.6, 0.55), flat=(0.95, 0.95, 0.85), emit=light, strength=4), verts=8, name="lamp_head")
            box((0.45, 2.2, 0.45), (0.0, cy + 1.6, PLAT_H + 0.22), marble, name="bench")
            bpy.ops.object.light_add(type="POINT", location=(0, cy, PLAT_H + 3.6))
            li = bpy.context.object
            li.name, li.data.energy, li.data.color, li.data.shadow_soft_size = "column_light", energy, light, 0.5
            li.data.use_shadow = False
    else:  # column
        gold = mat("coffer_gold", (0.35, 0.28, 0.12), flat=(0.85, 0.72, 0.40), metal=0.6)
        box((2 * wx + 0.8, length, 0.3), (0, 0, PLAT_H + 4.35), gold, name="ceiling")
        for gx in _range(-wx, wx, 1.6):
            box((0.08, length, 0.35), (gx, 0, PLAT_H + 4.05), gold, name="coffer_rib")
        cross = box((2 * wx, 0.08, 0.35), (0, -length / 2, PLAT_H + 4.05), gold, name="coffer_rib_x")  # square coffers
        _array_y(cross, int(length / 1.6), 1.6)
        for sx in (-1, 1):
            box((0.4, length, 4.6), (sx * (wx + 0.2), 0, 2.3), marble, name="track_wall")
            for cy in _range(-length / 2 + 3.25, length / 2 - 3.25, 6.5):
                box((0.8, 0.8, 4.2), (sx * 2.9, cy, PLAT_H + 2.1), marble, name="column")
        if energy > 0:
            lamp_row([-1.4, 1.4], _range(-length / 2 + 6, length / 2 - 6, lamps_every), PLAT_H + 4.1, light, energy)
    for ey in (-length / 2, length / 2):  # end walls with black tunnel mouths on the tracks
        wy = ey + (0.2 if ey > 0 else -0.2)
        # end wall with real openings: both track tunnels (a 30 m running-tunnel stub behind each) and, if asked,
        # a passage through the middle of the north wall (doors, escalator)
        low = PLAT_H + 4.4  # wall band that holds the openings; above it one lintel spans the whole width
        holes = sorted([(tx - 2.6, tx + 2.6) for tx in (-tx_, tx_)] +
                       ([(-north_opening / 2, north_opening / 2)] if ey > 0 and north_opening > 0 else []))
        x = -wx - 0.5
        for h0, h1 in holes + [(wx + 0.5, wx + 0.5)]:
            if h0 > x:
                box((h0 - x, 0.4, low), ((x + h0) / 2, wy, low / 2), marble, name="end_wall")
            x = h1
        box((2 * wx + 1, 0.4, 9.0 - low), (0, wy, low + (9.0 - low) / 2), marble, name="end_wall_lintel")
        for h0, h1 in [(-wx - 0.5, -tx_ - 2.6), (-tx_ + 2.6, tx_ - 2.6), (tx_ + 2.6, wx + 0.5)]:  # below z = 0 beside the portals
            if h1 > h0:
                box((h1 - h0, 0.4, -TRACK_Z), ((h0 + h1) / 2, wy, TRACK_Z / 2), marble, name="end_wall")
        for tx in (-tx_, tx_):
            top = 4.3 + TRACK_Z  # tunnel crown (lowered with the track) + a little
            box((5.2, 0.4, low - top), (tx, wy, top + (low - top) / 2), marble, name="end_wall")  # over the tunnel
            _tunnel_stub(tx, ey + (15.2 if ey > 0 else -15.2))
            _portal_ring(tx, wy - (0.21 if ey > 0 else -0.21), TRACK_Z + CZ, marble)  # closes the corners round the tube
    return {"length": length, "plat_z": PLAT_H, **K}


def _portal_ring(x, y, zc, m, r_in=R + 0.15, r_out=3.8, n=48):
    """Flat annulus facing the station: fills the corners between the round tunnel and the square wall opening."""
    bm = bmesh.new()
    inner = [bm.verts.new((x + r_in * math.cos(2 * math.pi * i / n), y, zc + r_in * math.sin(2 * math.pi * i / n))) for i in range(n)]
    outer = [bm.verts.new((x + r_out * math.cos(2 * math.pi * i / n), y, zc + r_out * math.sin(2 * math.pi * i / n))) for i in range(n)]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((inner[i], inner[j], outer[j], outer[i]))
    me = bpy.data.meshes.new("portal_ring")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("portal_ring", me)
    bpy.context.scene.collection.objects.link(o)
    return put(o, m)


def _tunnel_stub(x, y, length=30.0):
    """Short running tunnel behind a station portal, open toward the station, black far end."""
    before = set(bpy.context.scene.objects)
    running_tunnel(length=length, x=x, y=y)
    for o in set(bpy.context.scene.objects) - before:  # same track level as the station
        if o.parent is None:
            o.location.z += TRACK_Z
    for o in set(bpy.context.scene.objects) - before:
        if o.name.startswith("tunnel_shell"):  # remove both caps of the shell cylinder
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.z) > 0.9], context="FACES")  # caps: local z
            bm.to_mesh(o.data)
            bm.free()
    far = y + (length / 2 if y > 0 else -length / 2)
    box((5.6, 0.1, 5.6), (x, far, CZ), mat("dark_inside", (0.01, 0.01, 0.01), flat=(0.1, 0.1, 0.1)), name="tunnel_far_end")


def _range(a, b, step):
    out, v = [], a
    while v <= b:
        out.append(v)
        v += step
    return out


def tent_street(rng, y0, y1, gap=1.6, rows_x=(-2.4, 2.4), plat_z=PLAT_H, dressed=True):
    """Two rows of army tents on the platform facing a central aisle ('Main Street')."""
    y = y0
    i = 0
    while y < y1:
        for rx in rows_x:
            t = army_tent(f"tent_{i}", (rx, y), facing=90 if rx < 0 else 270, size=(2.4, rng.uniform(2.4, 3.2)),
                          h=rng.uniform(1.7, 2.1), open_flap=rng.random() < 0.4)
            t.location.z = plat_z
            i += 1
        if dressed:
            scatter_crates(rng, ((-0.9, 0.9), (y - 0.5, y + 1.5)), rng.randint(0, 2), z=plat_z)
        y += 3.0 + gap * rng.random()


# ---------------------------------------------------------------- locations by scene

def north_cordon():
    """Sandbag post in the north tunnel (scene 5): wall at y = 0 across the track, MG and searchlight on top."""
    from kit import sandbags, machine_gun, searchlight
    running_tunnel()  # cast iron: the cordon may stand in the 1958 section, the 250 m post in the 1978 extension (V6 — check)
    s = sandbags("cordon_bags", width=4.4, height=1.2)
    s.location = (0, 0, 0)
    mg = machine_gun("cordon_mg")
    mg.location = (0.6, -0.35, 0.95)
    sl = searchlight("cordon_searchlight")
    sl.location = (-1.2, -0.3, 1.75)
    bpy.ops.object.light_add(type="SPOT", location=(-1.2, -0.05, 1.75), rotation=(math.radians(-90 + 0), 0, 0))
    li = bpy.context.object
    li.name, li.data.energy, li.data.spot_size, li.data.spot_blend = "cordon_beam", 6000, math.radians(18), 0.3
    li.rotation_euler = (math.radians(87), 0, 0)  # along +Y, dipping to chest height ~17 m out where the Dark Ones come
    rng = _rng(5)
    scatter_crates(rng, ((-1.8, -0.6), (-2.5, -1.0)), 3)


def peregon_savelovskaya():
    """Tunnel toward Savyolovskaya (scene 3): sandbag barricade at y = 60 with a gap for the track, warm light behind it."""
    from kit import sandbags
    running_tunnel(length=140, y=30)
    for x in (-1.75, 1.75):
        s = sandbags(f"barricade_{x}", width=1.4, height=1.5)  # 7 rows, top 1.405: the flamethrower man stands on it (3.03)
        s.location = (x, 60, 0)
    bpy.ops.object.light_add(type="POINT", location=(0, 63, 2.0))
    li = bpy.context.object
    li.name, li.data.energy, li.data.color = "savelovskaya_light", 1500, (1.0, 0.8, 0.55)


def timiryazevskaya():
    """Single-vault station (scene 2 flashback, 2014): dim cold lamps; the side tunnel the rats pour from opens in the
    west track wall at the north end (x = -8.2, y = 73)."""
    station("single_vault", length=162, light=(0.75, 0.82, 1.0), energy=300)
    # side tunnel "leading deep into unexplored passages" (metro.fandom): a dark portal in the west track wall at the
    # north end, where the rat flood comes from (x = -8.2, y = 73, its floor at track level)
    dark = mat("dark_inside", (0.01, 0.01, 0.01), flat=(0.1, 0.1, 0.1))
    box((0.6, 4.0, 3.4), (-8.0, 73.0, 1.7), dark, name="side_tunnel_mouth")
    for o in [o for o in bpy.data.objects if o.name.startswith(("track_wall", "black_stripe")) and o.location.x < 0]:
        # open the west track wall in front of the portal (y 71..75) so the rats pour straight down onto the track
        sx, sy, sz = o.scale
        for y0, y1 in ((-sy / 2, 71.0), (75.0, sy / 2)):
            box((sx, y1 - y0, sz), (o.location.x, (y0 + y1) / 2, o.location.z), o.data.materials[0], name=o.name)
        bpy.data.objects.remove(o)
    cyl(1.9, 12, (-14.0, 73.0, 1.9), mat("concrete", (0.20, 0.18, 0.16), flat=(0.33, 0.32, 0.30)), rot=(0, math.pi / 2, 0), verts=32, name="side_tunnel")
    rng = _rng(2)
    scatter_crates(rng, ((-4, 4), (-40, 40)), 14, z=PLAT_H)
    scatter_debris(rng, ((-4.5, 4.5), (-45, 45)), 60, z=PLAT_H)


def vdnkh():
    """VDNKh (scenes 7, 18, 19, 20, 24): pylon station, red emergency light. Layout follows the real station
    (WORLD.md) and the script ("two rows of tents along the platform; the passage between them is Main Street"):
    * Main Street = the open central hall (x in -4.75..4.75); laundry strung between pylons; crates, benches.
    * Dwellings: a family tent in every arched passage between pylons, at its hall end (passage centres y = -73.5 + 9 k, x = ±5.7)
      and wooden 'apartments' along the side naves in front of each pylon (x = ±7.4) — about 70 homes for ~200 people.
    * Guest tent: at the east platform edge in front of the pylon at y = 36..42 (centre (7.25, 39.0)), flap facing south onto the edge walkway ("edge of the platform,
      away from Main Street").
    * North end (y = 81): sealed blast gate of the escalator passage in the central hall; the tea factory is the dead
      end in front of it (y = 62..76); station clock over the east (right) track tunnel mouth.
    * Tracks at x = ±9.85 on z = 0; platform top z = 1.1; south tunnel mouths at y = -81."""
    station("pylon", length=162, light=(1.0, 0.22, 0.12), energy=200)
    rng = _rng(7)
    shack = mat("shack_wood", (0.14, 0.10, 0.07), flat=(0.62, 0.48, 0.32))
    k = 0
    for sx in (-1, 1):
        y = -81 + 6.0  # first passage after the first pylon
        while y + 3.0 <= 81 - 6.0 + 0.01:
            yc = y + 1.5
            free = k % 3 == 1  # every third arch stays open: the way from Main Street to the platform edge and trains
            if not free and yc < 60:  # leave the factory end
                # tent at the hall end of its arch, flap 0.35 m out on Main Street: the two rows of the script read along the hall
                t = army_tent(f"arch_tent_{k}", (sx * 5.7, yc), facing=270 if sx > 0 else 90, size=(2.4, 2.6),
                              h=rng.uniform(1.8, 2.1), open_flap=rng.random() < 0.4)
                t.location.z = PLAT_H
            if yc - 4.5 > -78 and yc - 4.5 < 58 and not (sx > 0 and abs(yc - 4.5 - 39.0) < 0.1):  # apartment in the side nave in front of the pylon (not at the guest tent)
                # against the pylon's outer face (x 6.25..7.25): a 1 m walkway stays along the platform edge
                box((1.0, 4.2, rng.uniform(1.9, 2.3)), (sx * 6.75, yc - 4.5, PLAT_H + 1.05), shack, name=f"apartment_{k}")
            k += 1
            y += 9.0
    # guest tent: at the platform edge, off Main Street (script), in the east side nave in front of the pylon at y 36..42;
    # long side along the track, flap to the south onto the edge walkway
    g = army_tent("guest_tent", (7.25, 39.0), facing=180, size=(1.9, 2.8), h=2.0, rgb=(0.22, 0.20, 0.15), flat=(0.55, 0.50, 0.38), open_flap=True)
    g.location.z = PLAT_H
    for i in range(10):  # laundry on wires along the faces of the west pylons, between the arches (clear of the tents)
        yc = -73.5 + i * 9
        laundry_line((-4.05, yc + 1.8), (-4.05, yc + 7.2), PLAT_H + 1.95, rng)  # over the bench edge, within reach
    scatter_crates(rng, ((-3.5, 3.5), (-70, 55)), 18, z=PLAT_H)
    box((5.0, 0.5, 4.0), (0, 80.2, PLAT_H + 2.0), mat("blast_door", (0.12, 0.12, 0.11), flat=(0.40, 0.42, 0.40), rough=0.5, metal=0.7),
        name="escalator_gate")  # sealed passage to the north vestibule
    wall_clock("--:--", (9.85, 80.925, 5.3))  # the time is set by every scene ("clock"); run_scene refuses a scene without it
    # tea factory in the dead end before the sealed gate: rows of wires with drying mushroom caps, small fires, door tables
    # tarp partition with a wide doorway: closes the factory off from Main Street so it reads as a dead end; 2.4 m high,
    # so the existing cameras above it (19.01, 7.13) still look in
    tarp = mat("tarp", (0.16, 0.14, 0.10), flat=(0.50, 0.45, 0.33))
    for sx in (-1, 1):
        box((3.05, 0.05, 2.4), (sx * 3.25, 61.8, PLAT_H + 1.2), tarp, name="tea_partition")
    caps = mat("mushroom_caps", (0.75, 0.72, 0.62), flat=(0.95, 0.92, 0.80), rough=0.8)
    wire = mat("cable", (0.03, 0.03, 0.03), flat=(0.12, 0.12, 0.12), rough=0.5)
    for row in range(8):  # thousands in the script; ~500 caps read as a dense drying field at this scale
        y = 62.6 + row * 1.6
        cyl(0.006, 8.0, (0, y, PLAT_H + 2.1), wire, rot=(0, math.pi / 2, 0), verts=4, name="tea_wire")
        for i in range(60):
            sphere(0.035, (-3.9 + i * 0.13, y, PLAT_H + 2.05 - rng.random() * 0.04), caps, name="cap", scale=(1, 1, 0.5))
    door = mat("door_table", (0.18, 0.15, 0.11), flat=(0.60, 0.52, 0.40))
    for tx in (-2.2, 2.2):
        box((1.0, 6.0, 0.06), (tx, 69, PLAT_H + 0.8), door, name="door_table")
        for ly in (66.5, 71.5):
            for lx in (-0.4, 0.4):
                box((0.06, 0.06, 0.8), (tx + lx, ly, PLAT_H + 0.4), door, name="table_leg")
    for fx, fy in ((0, 65.5), (0, 72.5)):
        campfire_small((fx, fy, PLAT_H))
    scatter_crates(rng, ((-4.0, 4.0), (62, 76)), 8, z=PLAT_H)
    # smoke of the drying fires hanging under the vault ("дымки костров"): a thin grey volume, lit pass only
    smoke = box((9.0, 14.0, 4.5), (0, 69.0, PLAT_H + 2.6), _smoke_mat(), name="tea_smoke")
    smoke["lit_only"] = True
    smoke.hide_viewport = True  # out of scene.ray_cast (camera occlusion tests); render visibility is set per pass


def _smoke_mat():
    m = bpy.data.materials.get("smoke") or bpy.data.materials.new("smoke")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Color"].default_value = (0.5, 0.48, 0.45, 1)
    v.inputs["Density"].default_value = 0.12
    nt.links.new(v.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs["Volume"])
    m["flat"] = (0.5, 0.5, 0.5)
    return m


def campfire_small(at, energy=60):
    f = Vector(at)
    flame = mat("flame", (1, 0.5, 0.1), flat=(1.0, 0.62, 0.10), rough=1, emit=(1.0, 0.45, 0.08), strength=25.0)
    char = mat("charred", (0.03, 0.02, 0.02), flat=(0.20, 0.12, 0.08))
    for a in (0, 90):
        cyl(0.04, 0.45, (f.x, f.y, f.z + 0.04), char, rot=(math.pi / 2, 0, math.radians(a)), verts=8, name="fire_log")
    cone(0.09, 0, 0.35, (f.x, f.y, f.z + 0.2), flame, name="flame").visible_shadow = False
    bpy.ops.object.light_add(type="POINT", location=(f.x, f.y, f.z + 0.35))
    li = bpy.context.object
    li.name, li.data.energy, li.data.color = "small_fire_light", energy, (1.0, 0.5, 0.2)


def botanical():
    """Botanichesky Sad, abandoned (scenes 9, 11): dark column station (real: 169 m, square columns at 6.5 m),
    no lamps. North end: an opening 5.6 m wide in the end wall; rusty sliding doors sliding_door_L / _R in front
    of it at y = 83.6 (open them with prop_move, e.g. L to x = -3.6, R to x = 3.6); the blast door raised above the opening
    (open); the wired lever beside the doors at (3.2, 83.4); the escalator rises beyond from y = 86.5."""
    station("column", length=169, light=(0.5, 0.5, 0.5), energy=0, north_opening=5.6)
    rng = _rng(9)
    scatter_debris(rng, ((-4.5, 4.5), (-80, 78)), 160, z=PLAT_H)
    scatter_crates(rng, ((-4, 4), (-40, 40)), 6, z=PLAT_H)
    rust = mat("rust_door", (0.20, 0.10, 0.06), flat=(0.62, 0.38, 0.25), rough=0.7, metal=0.6)
    for side, x in (("L", -1.3), ("R", 1.3)):  # rusty sliding doors just in front of the opening; animate x with prop_move
        box((2.6, 0.12, 3.4), (x, 83.6, PLAT_H + 1.7), rust, name=f"sliding_door_{side}")
    box((5.5, 0.5, 4.3), (0, 85.6, PLAT_H + 6.6), mat("blast_door", (0.12, 0.12, 0.11), flat=(0.40, 0.42, 0.40), rough=0.5, metal=0.7), name="blast_door")  # raised: open
    box((0.08, 0.08, 0.9), (3.2, 83.4, PLAT_H + 0.9), rust, rot=(math.radians(25), 0, 0), name="lever")  # beside the doors, wrapped in wire
    # T-handle at the top of the lever: wide enough for three children's hands side by side (scene 9, 9.17)
    box((0.9, 0.06, 0.06), (3.2, 83.4 - 0.45 * math.sin(math.radians(25)), PLAT_H + 0.9 + 0.45 * math.cos(math.radians(25))), rust, name="lever_bar")
    box((5.6, 2.6, 0.3), (0, 85.9, PLAT_H - 0.15), mat("granite_floor", (0.20, 0.14, 0.12), flat=(0.55, 0.42, 0.38), rough=0.5),
        name="escalator_landing")  # floor from the doors to the first step (the shaft bottom lies below it)
    steps = mat("rotten_steps", (0.08, 0.06, 0.05), flat=(0.35, 0.28, 0.20))
    gear = mat("esc_gear", (0.06, 0.05, 0.04), flat=(0.22, 0.20, 0.18), rough=0.5, metal=0.8)
    for i in range(40):  # escalator beyond the blast door: 30 degrees up toward the vestibule; gaps show the gears
        y, z = 86.5 + i * 0.35, PLAT_H + 0.2 + i * 0.2
        if rng.random() < 0.22:
            cyl(0.3, 1.2, (0, y, z - 0.45), gear, rot=(0, math.pi / 2, 0), verts=16, name="esc_gear")
            continue
        box((1.4, 0.4, 0.06), (0, y, z), steps, name="esc_step")
    for sx in (-1, 1):  # balustrades along the incline
        box((0.12, 16.0, 0.9), (sx * 0.8, 86.5 + 7.0, PLAT_H + 0.2 + 4.0 + 0.5), rust, rot=(math.radians(29.7), 0, 0), name="esc_balustrade")
    bpy.ops.mesh.primitive_cylinder_add(radius=2.2, depth=17, location=(0, 93.5, PLAT_H + 4.2), rotation=(math.radians(-60), 0, 0),
                                        vertices=32, end_fill_type="NOTHING")  # open tube along the 30-degree incline
    put(bpy.context.object, mat("concrete", (0.20, 0.18, 0.16), flat=(0.33, 0.32, 0.30)), "escalator_shaft")
    axis = Vector((0, math.sin(math.radians(60)), math.cos(math.radians(60))))  # the tube's axis after the -60 degree tilt
    top = Vector((0, 93.5, PLAT_H + 4.2)) + axis * 8.5
    cyl(2.2, 0.05, top.to_tuple(), mat("dark_inside", (0.01, 0.01, 0.01), flat=(0.1, 0.1, 0.1)), rot=(math.radians(-60), 0, 0), verts=32,
        name="escalator_top")  # the far end is dark (the vestibule above is not modelled here), not open background


def botanical_vestibule():
    """Ruined surface vestibule at night (scene 10): the real south vestibule of Botanichesky Sad is a rotunda in a
    park (ru.wikipedia). Round hall r = 9 m, wall height 5 m, the dome half fallen in (open to the north-west sky),
    the escalator descent as a dark opening at (0, -6), the doorway to the park facing north (y = +9)."""
    conc = mat("concrete", (0.20, 0.18, 0.16), flat=(0.33, 0.32, 0.30))
    cyl(9.4, 0.3, (0, 0, -0.15), conc, verts=48, name="floor")
    for i in range(36):  # round wall from segments, with a doorway to the north
        a0 = math.radians(i * 10 + 5)
        if abs(math.degrees(a0) - 90) < 9:
            continue
        box((0.4, 1.7, 5.0), (9.0 * math.cos(a0), 9.0 * math.sin(a0), 2.5), conc, rot=(0, 0, a0), name="rotunda_wall")
    # the surviving south half of the dome (a real dome, not a barrel vault): the sky shows only over the fallen north half
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=9.2)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.01 or v.co.y > 0.5], context="VERTS")
    me = bpy.data.meshes.new("dome_half")
    bm.to_mesh(me)
    bm.free()
    dome = bpy.data.objects.new("dome_half", me)
    bpy.context.scene.collection.objects.link(dome)
    dome.location = (0, 0, 5.0)
    dome.scale.z = 0.6
    put(dome, conc)
    box((3.0, 6.0, 0.05), (0, -6.0, 0.01), mat("dark_inside", (0.01, 0.01, 0.01), flat=(0.1, 0.1, 0.1)), name="escalator_opening")
    rng = _rng(10)
    scatter_debris(rng, ((-7, 7), (-7, 7)), 150)
    star = mat("star", (1, 1, 1), flat=(1, 1, 1), emit=(0.9, 0.92, 1.0), strength=30)
    for i in range(250):  # stars on a dome above the hole
        a, e = rng.uniform(0, 6.28), rng.uniform(0.3, 1.4)
        sphere(0.12, (60 * math.cos(e) * math.cos(a), 60 * math.cos(e) * math.sin(a) + 20, 60 * math.sin(e)), star, name="star").visible_shadow = False
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), 0, math.radians(30)))
    li = bpy.context.object
    li.name, li.data.energy, li.data.color = "night_sky", 0.15, (0.55, 0.65, 1.0)
    nt = bpy.context.scene.world.node_tree
    nt.nodes["Background"].inputs[0].default_value = (0.02, 0.035, 0.09, 1)  # night sky, not void
    nt.nodes.remove(nt.nodes["haze"])  # outdoors: EEVEE's world volume would black out the sky


def sukhoi_tent():
    """Inside Sukhoi's tent (scenes 8, 12, 13, 14, 16, 17, 22): 3 x 4 m, entrance at y = -2, cots along both
    walls, crate shelf with books at the back (y = +1.8), crate seat, small table, warm lamp."""
    from kit import crate
    canvas = mat("canvas_in", (0.22, 0.20, 0.14), flat=(0.50, 0.55, 0.40), rough=0.95)
    box((3.2, 4.2, 0.05), (0, 0, -0.025), mat("tarp_floor", (0.10, 0.09, 0.07), flat=(0.35, 0.33, 0.28)), name="tent_floor")
    for x in (-1.6, 1.6):
        box((0.04, 4.2, 1.5), (x, 0, 0.75), canvas, name="tent_wall")
    for x, r in ((-0.8, -28), (0.8, 28)):  # ridge in the middle, low at the walls
        box((1.82, 4.2, 0.04), (x, 0, 1.95), canvas, rot=(0, math.radians(r), 0), name="tent_roof")
    box((3.2, 0.04, 2.4), (0, 2.1, 1.2), canvas, name="tent_back")
    box((1.2, 0.04, 2.2), (-1.0, -2.1, 1.1), canvas, name="tent_front_L")
    box((1.2, 0.04, 2.2), (1.0, -2.1, 1.1), canvas, name="tent_front_R")
    box((0.8, 0.04, 0.48), (0, -2.1, 2.16), canvas, name="tent_front_lintel")  # doorway 1.92 m: a tall man stoops
    cot = mat("cot", (0.20, 0.22, 0.15), flat=(0.45, 0.52, 0.35))
    for x in (-1.15, 1.15):
        box((0.7, 1.9, 0.08), (x, 0.3, 0.42), cot, name="cot")
    books = mat("books", (0.35, 0.30, 0.15), flat=(0.85, 0.75, 0.40))
    for i, (x, z) in enumerate(((-0.4, 0.25), (0.4, 0.25), (0, 0.75))):
        wood = mat("crate_wood", (0.12, 0.09, 0.06), flat=(0.55, 0.40, 0.25))
        for size, off in (((0.75, 0.03, 0.5), (0, 0.185, 0)), ((0.03, 0.4, 0.5), (-0.36, 0, 0)), ((0.03, 0.4, 0.5), (0.36, 0, 0)),
                          ((0.75, 0.4, 0.03), (0, 0, -0.235)), ((0.75, 0.4, 0.03), (0, 0, 0.235))):  # crate on its side, open to the tent
            box(size, (x + off[0], 1.85 + off[1], z + off[2]), wood, name="shelf_crate")
        trng = _rng(30 + i)
        bx = x - 0.33
        while bx < x + 0.3:  # 8-10 tomes standing side by side, spines to the tent
            tw, th = trng.uniform(0.05, 0.085), trng.uniform(0.2, 0.32)
            box((tw, 0.24, th), (bx + tw / 2, 1.85, z - 0.22 + th / 2),
                mat(f"book_{i}_{round(bx, 2)}", trng.choice(((0.35, 0.30, 0.15), (0.28, 0.12, 0.08), (0.18, 0.2, 0.12), (0.4, 0.36, 0.25))),
                    flat=(0.85, 0.75, 0.40)), name="book")
            bx += tw + 0.006
    crate("seat_crate", (0.0, -0.4), 0)
    box((0.8, 0.6, 0.05), (0.0, 0.6, 0.7), mat("door_table", (0.18, 0.15, 0.11), flat=(0.60, 0.52, 0.40)), name="table")
    bpy.ops.object.light_add(type="POINT", location=(0, 0.6, 1.6))
    li = bpy.context.object
    li.name, li.data.energy, li.data.color, li.data.shadow_soft_size = "tent_lamp", 120, (1.0, 0.75, 0.45), 0.1
    box((0.01, 0.01, 0.55), (0, 0.6, 2.075), mat("cable", (0.03, 0.03, 0.03), flat=(0.12, 0.12, 0.12), rough=0.5), name="tent_lamp_cord")  # 714
    glow = mat("tent_lamp_glow", (1, 0.8, 0.5), flat=(1, 0.9, 0.6), emit=(1, 0.75, 0.45), strength=8)
    box((0.12, 0.12, 0.16), (0, 0.6, 1.72), glow, name="tent_lamp_bulb").visible_shadow = False  # the lamp itself, under the ridge
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.008, 0.006, 1)  # red station glow through canvas


def vdnkh_office():
    """Station chief's office (scene 23): 4 x 5 m service room, door at y = -2.5, desk and lamp, map on the wall."""
    plaster = mat("plaster", (0.30, 0.28, 0.24), flat=(0.62, 0.60, 0.55))
    box((4, 5, 0.1), (0, 0, -0.05), plaster, name="floor")
    for x in (-2, 2):
        box((0.1, 5, 3), (x, 0, 1.5), plaster, name="wall")
    box((4, 0.1, 3), (0, 2.5, 1.5), plaster, name="wall")
    box((1.5, 0.1, 3), (-1.25, -2.5, 1.5), plaster, name="wall")
    box((1.5, 0.1, 3), (1.25, -2.5, 1.5), plaster, name="wall")
    box((1.6, 0.8, 0.05), (0, 1.3, 0.70), mat("door_table", (0.18, 0.15, 0.11), flat=(0.60, 0.52, 0.40)), name="desk")  # 708
    box((1.4, 0.02, 1.0), (0, 2.44, 1.7), mat("paper_map", (0.55, 0.50, 0.38), flat=(0.95, 0.90, 0.75)), name="wall_map")
    bpy.ops.object.light_add(type="POINT", location=(0.4, 1.3, 1.2))
    li = bpy.context.object
    li.name, li.data.energy, li.data.color = "desk_lamp", 35, (1.0, 0.8, 0.55)


def white_room():
    """Vision (scene 21): empty white room lit evenly from everywhere, no shadows."""
    white = mat("white_room", (0.9, 0.9, 0.9), flat=(1, 1, 1), emit=(1, 1, 1), strength=1.5)
    for o in (box((10, 10, 0.1), (0, 0, -0.05), white), box((10, 0.1, 6), (0, 5, 3), white),
              box((0.1, 10, 6), (-5, 0, 3), white), box((0.1, 10, 6), (5, 0, 3), white), box((10, 10, 0.1), (0, 0, 6), white)):
        o.visible_shadow = False
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)


LOCATIONS = {"tunnel_250": tunnel_250, "north_cordon": north_cordon, "peregon_savelovskaya": peregon_savelovskaya,
             "timiryazevskaya": timiryazevskaya, "vdnkh": vdnkh, "botanical": botanical,
             "botanical_vestibule": botanical_vestibule, "sukhoi_tent": sukhoi_tent, "vdnkh_office": vdnkh_office,
             "white_room": white_room}


# Camera bounds per location ((x0, x1), (y0, y1), (z0, z1)): auto cameras are pulled in so they never sit
# inside a wall. Default views are used for wide/dark shots that have no character to frame.
BOUNDS = {
    "tunnel_250": ((-1.9, 1.9), (-100, 100), (0.3, 2.9)), "north_cordon": ((-1.9, 1.9), (-44, 44), (0.3, 2.9)),
    "peregon_savelovskaya": ((-1.9, 1.9), (-38, 98), (0.3, 2.9)), "timiryazevskaya": ((-7.8, 7.8), (-80, 80), (0.4, 8.5)),
    "vdnkh": ((-11.2, 11.2), (-80, 80), (0.4, 7.8)), "botanical": ((-8.0, 8.0), (-84, 100), (0.4, 5.2)),
    "botanical_vestibule": ((-8.5, 8.5), (-8.5, 8.5), (0.3, 5.5)), "sukhoi_tent": ((-1.45, 1.45), (-2.0, 2.0), (0.25, 2.15)),
    "vdnkh_office": ((-1.85, 1.85), (-2.4, 2.4), (0.3, 2.8)), "white_room": ((-4.8, 4.8), (-4.8, 4.8), (0.3, 5.5)),
}
VIEWS = {  # name: (camera, target, lens)
    "tunnel_250": {"wide": ((0.25, -8.5, 1.55), (-0.7, 2.5, 0.7), 24), "dark": ((-0.3, 4.2, 1.5), (-0.3, 25, 1.0), 35)},
    "north_cordon": {"wide": ((0.5, -5, 1.7), (0, 3, 1.0), 24), "dark": ((0, 1.0, 1.6), (0, 25, 1.4), 35)},
    "peregon_savelovskaya": {"wide": ((0.3, 45, 1.6), (0, 62, 1.0), 24), "dark": ((0, 20, 1.6), (0, -10, 1.0), 35)},
    "timiryazevskaya": {"wide": ((-3, -60, 4.0), (0, 10, 2.5), 20), "dark": ((-6.4, 70, 1.6), (-6.4, 90, 1.6), 35)},
    "vdnkh": {"wide": ((0, -50, 3.5), (0, 0, 2.5), 20), "dark": ((9.85, 70, 1.6), (9.85, 95, 2.0), 35)},
    "botanical": {"wide": ((0, 66, 2.8), (0, 87, 2.2), 24), "dark": ((0, 70, 2.2), (0, 20, 1.8), 35)},
    "botanical_vestibule": {"wide": ((-8, -7, 1.7), (3, 4, 3.0), 20), "dark": ((0, 0, 1.6), (5, 20, 25), 24)},
    "sukhoi_tent": {"wide": ((-1.4, -1.9, 1.7), (0.5, 1.5, 0.6), 16), "dark": ((0, -1.8, 1.4), (0, 1.8, 1.0), 20)},
    "vdnkh_office": {"wide": ((-1.7, -2.2, 1.7), (0.3, 1.5, 0.9), 18), "dark": ((0, -2.2, 1.6), (0, 2.4, 1.6), 24)},
    "white_room": {"wide": ((0, -4.5, 1.6), (0, 0, 1.5), 24), "dark": ((0, -4.5, 1.6), (0, 0, 1.5), 24)},
}
