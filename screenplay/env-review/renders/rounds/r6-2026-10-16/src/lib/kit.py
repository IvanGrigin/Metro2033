"""Shared 3D kit for every scene: materials with flat 'ID' colours, props, jointed mannequins
with poses and walking, cameras, and the render passes. Imported by run_scene.py inside Blender."""
import bpy, math, random
from mathutils import Vector

FPS = 24
# Flat colours for the Workbench passes: people by character, everything else by kind.
CHAR_COLORS = {"Artyom": (0.10, 0.35, 0.95), "Pyotr": (0.95, 0.50, 0.10), "Andrei": (0.10, 0.75, 0.25),
               "Kirill": (0.95, 0.85, 0.10), "Hunter": (0.90, 0.10, 0.10), "Sukhoi": (0.60, 0.20, 0.85),
               "Mother": (0.95, 0.45, 0.70), "ArtyomChild": (0.45, 0.85, 1.00), "Black": (0.85, 0.05, 0.85),
               "Extra": (0.60, 0.58, 0.52), "Zhenya": (0.30, 0.90, 0.75), "Vitalik": (0.55, 0.30, 0.10),
               "Commander": (0.10, 0.40, 0.10), "Nikita": (0.50, 0.50, 0.95), "Alexander": (0.10, 0.65, 0.65),
               "OldWorker": (0.85, 0.30, 0.45)}
CHAR_LEGEND = {"Artyom": "BLUE", "Pyotr": "ORANGE", "Andrei": "GREEN", "Kirill": "YELLOW", "Hunter": "RED", "Sukhoi": "PURPLE",
               "Mother": "PINK", "ArtyomChild": "LIGHT BLUE", "Black": "MAGENTA", "Extra": "BEIGE", "Zhenya": "MINT",
               "Vitalik": "BROWN", "Commander": "DARK GREEN", "Nikita": "PERIWINKLE", "Alexander": "TEAL", "OldWorker": "RASPBERRY"}
_mats = {}


def mat(name, rgb, flat=None, rough=0.85, metal=0.0, emit=None, strength=0.0):
    """Material reused by name; `flat` is the colour objects get in the flat/ID passes."""
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    m["flat"] = flat or rgb
    _mats[name] = m
    return m


def put(obj, m, name=None, flat=None):
    obj.data.materials.clear()
    obj.data.materials.append(m)
    obj.color = (*(flat or m["flat"]), 1)
    if name:
        obj.name = name
    return obj


def box(size, loc, m, rot=(0, 0, 0), name=None, flat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = size
    return put(o, m, name, flat)


def cyl(r, depth, loc, m, rot=(0, 0, 0), verts=16, name=None, flat=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    return put(bpy.context.object, m, name, flat)


def sphere(r, loc, m, name=None, flat=None, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=16, ring_count=8)
    o = put(bpy.context.object, m, name, flat)
    o.scale = scale
    return o


def cone(r1, r2, depth, loc, m, rot=(0, 0, 0), name=None, flat=None):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rot, vertices=12)
    return put(bpy.context.object, m, name, flat)


def empty(name, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.empty_display_size = 0.05
    if parent:
        o.parent = parent
    o.location = loc
    return o


def attach(o, parent, loc=(0, 0, 0), rot=None):
    """Parent with identity inverse, so `loc` is in the parent's local space."""
    o.parent = parent
    o.location = loc
    if rot is not None:
        o.rotation_euler = rot
    return o


def key_visible(o, frame, visible):
    for obj in [o, *o.children_recursive]:
        obj.hide_render = obj.hide_viewport = not visible
        obj.keyframe_insert("hide_render", frame=frame)
        obj.keyframe_insert("hide_viewport", frame=frame)


# ---------------------------------------------------------------- props

def mug(name):
    root = empty(name)
    e = mat("enamel", (0.80, 0.80, 0.76), flat=(0.95, 0.95, 0.95), rough=0.3)
    attach(cyl(0.045, 0.10, (0, 0, 0), e, name=f"{name}.body"), root, (0, 0, 0.05))
    attach(cyl(0.04, 0.005, (0, 0, 0), mat("tea", (0.02, 0.01, 0.005), rough=0.1), name=f"{name}.tea"), root, (0, 0, 0.09))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.03, minor_radius=0.007)
    attach(put(bpy.context.object, e, f"{name}.handle"), root, (0.06, 0, 0.05), (math.pi / 2, 0, 0))  # exactly one handle
    return root


def rifle(name):
    """AK silhouette, barrel along +Y: receiver, barrel, gas tube, curved magazine, wooden stock."""
    root = empty(name)
    g = mat("gunmetal", (0.03, 0.03, 0.03), flat=(0.05, 0.05, 0.05), rough=0.4, metal=0.7)
    w = mat("gun_wood", (0.18, 0.08, 0.03), flat=(0.45, 0.22, 0.08))
    attach(box((0.05, 0.32, 0.08), (0, 0, 0), g, name=f"{name}.receiver"), root, (0, 0, 0))
    attach(cyl(0.011, 0.42, (0, 0, 0), g, (math.pi / 2, 0, 0), 8, f"{name}.barrel"), root, (0, 0.37, 0.015))
    attach(cyl(0.013, 0.22, (0, 0, 0), w, (math.pi / 2, 0, 0), 8, f"{name}.gastube"), root, (0, 0.27, 0.045))
    attach(box((0.04, 0.07, 0.19), (0, 0, 0), g, name=f"{name}.magazine"), root, (0, 0.06, -0.12), (math.radians(-22), 0, 0))
    attach(box((0.045, 0.30, 0.07), (0, 0, 0), w, name=f"{name}.stock"), root, (0, -0.30, -0.02))
    return root


def crate(name, loc, facing=0.0):
    z = loc[2] if len(loc) > 2 else 0.0  # floor height (1.1 on a station platform)
    c = box((0.45, 0.40, 0.42), (loc[0], loc[1], z + 0.21), mat("crate_wood", (0.12, 0.09, 0.06), flat=(0.55, 0.40, 0.25)),
            rot=(0, 0, math.radians(-facing)), name=name)
    return c


# ---------------------------------------------------------------- mannequins

JOINTS_REST = {}  # name -> rest local location, filled by person()
CHAR_OBJECTS = set()  # mesh names belonging to people: coloured in the id pass, everything else grey


def person(name, height=1.75, coat=False, beret=False, bald=False, role=None, costume=None):
    """Jointed mannequin facing +Y. Joints are empties named '<name>.<joint>'; animate their rotations.
    Every part takes the character's flat colour; nose and boots show where the person faces."""
    k = height / 1.75
    role = role or name  # palette key: several extras or soldiers share one colour
    col = CHAR_COLORS.get(role, CHAR_COLORS["Extra"])
    if role == "Black":  # the Dark Ones: naked, black skin glossy like oil
        cloth = skin = mat("black_skin", (0.01, 0.01, 0.012), flat=col, rough=0.12, metal=0.3)
    else:
        cloth = mat(f"{name}_cloth" if costume else f"{role}_cloth", tuple(costume) if costume else (0.15, 0.15, 0.14), flat=col)
        skin = mat("skin", (0.45, 0.33, 0.27), rough=0.6)
    boot = mat("boot", (0.05, 0.04, 0.03))
    J = {}
    J["root"] = empty(name)
    J["pelvis"] = empty(f"{name}.pelvis", J["root"], (0, 0, 0.95 * k))
    J["chest"] = empty(f"{name}.chest", J["pelvis"])
    J["head"] = empty(f"{name}.head", J["chest"], (0, 0, 0.62 * k))
    J["eyes"] = empty(f"{name}.eyes", J["head"], (0, 0.05 * k, 0.13 * k))
    J["torso"] = empty(f"{name}.torso", J["chest"], (0, 0, 0.40 * k))  # chest height: medium shots aim here
    for s, sx in (("L", -1), ("R", 1)):
        J[f"shoulder_{s}"] = empty(f"{name}.shoulder_{s}", J["chest"], (sx * 0.23 * k, 0, 0.55 * k))
        J[f"elbow_{s}"] = empty(f"{name}.elbow_{s}", J[f"shoulder_{s}"], (0, 0, -0.30 * k))
        J[f"hand_{s}"] = empty(f"{name}.hand_{s}", J[f"elbow_{s}"], (0, 0, -0.28 * k))
        J[f"hip_{s}"] = empty(f"{name}.hip_{s}", J["pelvis"], (sx * 0.10 * k, 0, 0))
        J[f"knee_{s}"] = empty(f"{name}.knee_{s}", J[f"hip_{s}"], (0, 0, -0.45 * k))
        J[f"ankle_{s}"] = empty(f"{name}.ankle_{s}", J[f"knee_{s}"], (0, 0, -0.45 * k))
        attach(cyl(0.055 * k, 0.30 * k, (0, 0, 0), cloth, flat=col), J[f"shoulder_{s}"], (0, 0, -0.15 * k))
        attach(cyl(0.048 * k, 0.28 * k, (0, 0, 0), cloth, flat=col), J[f"elbow_{s}"], (0, 0, -0.14 * k))
        attach(sphere(0.045 * k, (0, 0, 0), skin, flat=col), J[f"hand_{s}"], (0, 0, -0.03 * k))
        attach(cyl(0.075 * k, 0.45 * k, (0, 0, 0), cloth, flat=col), J[f"hip_{s}"], (0, 0, -0.225 * k))
        attach(cyl(0.065 * k, 0.45 * k, (0, 0, 0), cloth, flat=col), J[f"knee_{s}"], (0, 0, -0.225 * k))
        attach(box((0.10 * k, 0.26 * k, 0.08 * k), (0, 0, 0), boot, flat=(0.1, 0.1, 0.1)), J[f"ankle_{s}"], (0, 0.07 * k, -0.01 * k))
    attach(cyl(0.18 * k, 0.58 * k, (0, 0, 0), cloth, flat=col), J["chest"], (0, 0, 0.29 * k))
    if coat:
        attach(cone(0.30 * k, 0.19 * k, 0.70 * k, (0, 0, 0), mat(f"{name}_leather", (0.02, 0.02, 0.02), flat=col, rough=0.35)),
               J["chest"], (0, 0, -0.25 * k))
    attach(sphere(0.11 * k, (0, 0, 0), skin, flat=col, scale=(0.95, 1.0, 1.15)), J["head"], (0, 0, 0.13 * k))
    attach(cone(0.03 * k, 0.0, 0.08 * k, (0, 0, 0), skin, flat=(1, 1, 1)), J["head"], (0, 0.12 * k, 0.13 * k), (-math.pi / 2, 0, 0))
    if beret:
        attach(sphere(0.12 * k, (0, 0, 0), mat("beret", (0.01, 0.01, 0.01), flat=(0.05, 0.05, 0.05)), scale=(1.1, 1.1, 0.35)),
               J["head"], (0.02 * k, 0, 0.22 * k))
    for j, o in J.items():
        JOINTS_REST[o.name] = tuple(o.location)
    CHAR_OBJECTS.update(o.name for o in J["root"].children_recursive if o.type == "MESH")
    J["k"] = k
    return J


# Pose = joint rotations in degrees (X: + swings a limb forward; chest X: - leans forward) and pelvis height.
SIT = {"pelvis_z": 0.47, "hip_L": (90, 0, 0), "hip_R": (90, 0, 0), "knee_L": (-90, 0, 0), "knee_R": (-90, 0, 0)}
POSES = {
    "stand": {"shoulder_L": (5, 0, 0), "shoulder_R": (5, 0, 0)},
    "stand_rifle": {"shoulder_L": (45, 0, 15), "elbow_L": (50, 0, 0), "shoulder_R": (20, 0, 0), "elbow_R": (60, 0, 0), "rifle": "hip"},
    "aim": {"chest": (-5, 0, 0), "shoulder_L": (80, 0, 25), "elbow_L": (15, 0, 0), "shoulder_R": (70, 0, -10),
            "elbow_R": (70, 0, 0), "rifle": "shoulder"},
    "sit": {**SIT, "shoulder_L": (40, 0, 0), "shoulder_R": (40, 0, 0), "elbow_L": (10, 0, 0), "elbow_R": (10, 0, 0)},
    "sit_rifle": {**SIT, "shoulder_L": (40, 0, 0), "shoulder_R": (40, 0, 0), "elbow_L": (25, 0, 0), "elbow_R": (25, 0, 0), "rifle": "lap"},
    "sit_feed": {**SIT, "chest": (-20, 0, 0), "shoulder_R": (65, 0, 0), "elbow_R": (0, 0, 0), "shoulder_L": (40, 0, 0), "elbow_L": (10, 0, 0)},
    "sit_pour": {**SIT, "chest": (-15, 0, 0), "shoulder_R": (60, 0, 0), "elbow_R": (25, 0, 0), "shoulder_L": (50, 0, 0), "elbow_L": (40, 0, 0)},
    "sit_mug": {**SIT, "shoulder_R": (30, 0, 0), "elbow_R": (95, 0, 0), "shoulder_L": (40, 0, 0), "elbow_L": (10, 0, 0)},
    "offer": {"shoulder_R": (80, 0, 0), "elbow_R": (5, 0, 0), "shoulder_L": (5, 0, 0)},
    "flashlight": {"shoulder_R": (55, 0, 0), "elbow_R": (25, 0, 0), "shoulder_L": (5, 0, 0)},
    "hold_light": {"shoulder_L": (70, 0, 10), "elbow_L": (20, 0, 0), "shoulder_R": (70, 0, -10), "elbow_R": (20, 0, 0)},
    "carry_child": {"shoulder_L": (55, 0, 20), "elbow_L": (70, 0, 0), "shoulder_R": (55, 0, -20), "elbow_R": (70, 0, 0)},
    "sit_carry": {**SIT, "shoulder_L": (55, 0, 20), "elbow_L": (70, 0, 0), "shoulder_R": (55, 0, -20), "elbow_R": (70, 0, 0)},
    "reach_out": {"chest": (-15, 0, 0), "shoulder_L": (85, 0, 10), "elbow_L": (5, 0, 0), "shoulder_R": (85, 0, -10), "elbow_R": (5, 0, 0)},
    "prone": {"pelvis_z": 0.16, "pelvis_rot": (-88, 0, 0), "shoulder_L": (150, 0, 15), "shoulder_R": (150, 0, -15),
              "elbow_L": (20, 0, 0), "elbow_R": (20, 0, 0)},
    "fallen": {"pelvis_z": 0.14, "pelvis_rot": (88, 0, 0), "shoulder_L": (20, 0, 40), "shoulder_R": (20, 0, -40)},
    "kneel_up": {"pelvis_z": 0.55, "hip_L": (80, 0, 0), "knee_L": (-80, 0, 0), "hip_R": (10, 0, 0), "knee_R": (-100, 0, 0),
                 "shoulder_L": (40, 0, 0), "shoulder_R": (40, 0, 0)},
    "floor_ears": {"pelvis_z": 0.13, "hip_L": (75, 0, 10), "hip_R": (75, 0, -10), "knee_L": (-125, 0, 0), "knee_R": (-125, 0, 0),
                   "chest": (-25, 0, 0), "shoulder_L": (150, 0, 40), "elbow_L": (130, 0, 0), "shoulder_R": (150, 0, -40), "elbow_R": (130, 0, 0)},
    "flame": {"shoulder_L": (75, 0, 15), "elbow_L": (10, 0, 0), "shoulder_R": (60, 0, -10), "elbow_R": (40, 0, 0)},
    "stoop": {"chest": (-35, 0, 0), "head": (15, 0, 0), "shoulder_L": (20, 0, 0), "shoulder_R": (20, 0, 0)},
    "bend_over": {"chest": (-45, 0, 0), "head": (20, 0, 0), "shoulder_L": (60, 0, 10), "elbow_L": (10, 0, 0),
                  "shoulder_R": (60, 0, -10), "elbow_R": (10, 0, 0)},
    "tap_temple": {"shoulder_R": (110, 0, -25), "elbow_R": (125, 0, 0), "shoulder_L": (5, 0, 0)},
    "sit_tap_temple": {**SIT, "shoulder_R": (110, 0, -25), "elbow_R": (125, 0, 0), "shoulder_L": (40, 0, 0), "elbow_L": (10, 0, 0)},
    "kneel_touch": {"pelvis_z": 0.55, "hip_L": (80, 0, 0), "knee_L": (-80, 0, 0), "hip_R": (10, 0, 0), "knee_R": (-100, 0, 0),
                    "chest": (-20, 0, 0), "shoulder_R": (75, 0, 0), "elbow_R": (15, 0, 0), "shoulder_L": (20, 0, 0)},
    "sit_rifle_beside": {**SIT, "shoulder_L": (40, 0, 0), "elbow_L": (10, 0, 0), "rifle": "beside_R"},
    "sit_reach_rifle": {**SIT, "chest": (0, 30, 0), "shoulder_R": (15, -30, 0), "elbow_R": (0, 0, 0), "shoulder_L": (40, 0, 0), "elbow_L": (10, 0, 0)},  # 4.04 (critic)
    "sit_chop": {**SIT, "chest": (-15, 0, 0), "shoulder_R": (60, 0, 0), "elbow_R": (60, 0, 0), "shoulder_L": (60, 0, 0), "elbow_L": (60, 0, 0)},  # knives on the table (19)
    "pump": {"chest": (-10, 0, 0), "shoulder_L": (35, 0, -25), "elbow_L": (0, 0, 0), "shoulder_R": (35, 0, 25), "elbow_R": (0, 0, 0)},  # handcar levers (24)
    "look_up": {"head": (35, 0, 0), "shoulder_L": (5, 0, 0), "shoulder_R": (5, 0, 0)},  # head back to the sky (10.01)
    "raise_belt": {"shoulder_R": (110, 0, 0), "shoulder_L": (5, 0, 0)},  # belt raised under the tent roof (12)
    "offer_low": {"shoulder_R": (68, 0, 0), "elbow_R": (5, 0, 0), "shoulder_L": (5, 0, 0)},  # handshake height (6.04)
    "strike": {"chest": (-10, 0, 0), "shoulder_R": (60, 0, 0), "elbow_R": (10, 0, 0), "shoulder_L": (5, 0, 0)},  # belt blow (12)
    "reach_up": {"shoulder_L": (155, 0, 10), "elbow_L": (15, 0, 0), "shoulder_R": (155, 0, -10), "elbow_R": (15, 0, 0)},  # hanging laundry
    "wave": {"shoulder_R": (150, 0, -20), "elbow_R": (30, 0, 0), "shoulder_L": (5, 0, 0)},
    "sit_wave": {**SIT, "shoulder_R": (120, 0, -20), "elbow_R": (30, 0, 0), "shoulder_L": (40, 0, 0), "elbow_L": (10, 0, 0)},
}
RIFLE_HOLD = {  # rifle transform in chest space for each way of holding it
    "lap": ((0.0, 0.40, 0.13), (0, 0, math.radians(80))),  # on the thighs, clear of the shins (critic, round 4)
    "hip": ((0.08, 0.30, 0.10), (math.radians(25), 0, math.radians(-10))),
    "shoulder": ((0.13, 0.20, 0.47), (0, 0, 0)),
    "sling": ((0.05, -0.26, 0.40), (math.radians(90), math.radians(20), math.radians(180))),  # on the back, clear of the body in 11 poses (critic)
    "beside_R": ((0.45, 0.15, -0.27), (0, 0, math.radians(10))),  # seated: lying on the floor at the right hip
}
JOINT_NAMES = ["pelvis", "chest", "head", "shoulder_L", "elbow_L", "hip_L", "knee_L", "shoulder_R", "elbow_R", "hip_R", "knee_R"]


class Actor:
    """Keeps the current state of a mannequin and writes keyframes for actions over time."""

    def __init__(self, name, J, rifle_obj=None):
        self.name, self.J, self.k, self.rifle = name, J, J["k"], rifle_obj
        self.pos, self.facing, self.pose, self.head_yaw = Vector((0, 0, 0)), 0.0, "stand", 0.0

    def _apply(self, pose_name, frame, walk=None, rifle=None):
        p = POSES[pose_name]
        J, k = self.J, self.k
        J["pelvis"].location = (0, 0, p.get("pelvis_z", 0.95 * k))
        J["pelvis"].keyframe_insert("location", frame=frame)
        J["pelvis"].rotation_euler = tuple(math.radians(a) for a in p.get("pelvis_rot", (0, 0, 0)))  # lying poses
        J["pelvis"].keyframe_insert("rotation_euler", frame=frame)
        for j in JOINT_NAMES[1:]:
            rot = (walk or {}).get(j, p.get(j, (0, 0, 0)))
            if j == "head":
                rot = (rot[0], rot[1], rot[2] - self.head_yaw)
            J[j].rotation_euler = tuple(math.radians(a) for a in rot)
            J[j].keyframe_insert("rotation_euler", frame=frame)
        if self.rifle:  # a pose that does not use the rifle: seated -> it lies by the right hip, otherwise slung on the back
            hold = rifle or p.get("rifle", "beside_R" if p.get("pelvis_z") == SIT["pelvis_z"] else "sling")
            loc, rot = RIFLE_HOLD[hold]
            self.rifle.location, self.rifle.rotation_euler = loc, rot
            self.rifle.keyframe_insert("location", frame=frame)
            self.rifle.keyframe_insert("rotation_euler", frame=frame)

    def _key_root(self, frame):
        r = self.J["root"]
        r.location = self.pos
        r.rotation_euler = (0, 0, math.radians(-self.facing))
        r.keyframe_insert("location", frame=frame)
        r.keyframe_insert("rotation_euler", frame=frame)

    def place(self, frame, pos, facing, pose):
        """pos = [x, y] or [x, y, z]; z is the floor the person stands on (1.1 on a station platform)."""
        self.pos, self.facing, self.pose = Vector((pos[0], pos[1], pos[2] if len(pos) > 2 else 0)), facing, pose
        self._key_root(frame)
        self._apply(pose, frame)

    def set_pose(self, frame, pose, dur=0.6):
        self._apply(self.pose, frame)
        self._seat_step(frame, pose, dur)
        self.pose = pose
        self._apply(pose, frame + int(dur * FPS))

    def _seat_step(self, frame, new_pose, dur):
        """Getting up from a seat moves the body 0.45 k forward (off the crate); sitting down moves it back onto it,
        so the shins never stay inside the crate."""
        seated = lambda name: POSES[name].get("pelvis_z") == SIT["pelvis_z"]
        if seated(self.pose) == seated(new_pose):
            return
        fwd = Vector((math.sin(math.radians(self.facing)), math.cos(math.radians(self.facing)), 0)) * 0.45 * self.k
        self._key_root(frame)
        self.pos = self.pos + (fwd if seated(self.pose) else -fwd)
        self._key_root(frame + int(dur * FPS))

    def turn(self, frame, facing, dur=0.5):
        self._key_root(frame)
        self.facing = _near_angle(self.facing, facing)
        self._key_root(frame + int(dur * FPS))

    def look(self, frame, yaw, dur=0.4):
        self._apply(self.pose, frame)
        self.head_yaw = yaw
        self._apply(self.pose, frame + int(dur * FPS))

    def walk(self, frame, to, facing=None, speed=1.2, pose_after="stand"):
        """Turn toward the goal, stride there with swinging legs and arms, then face `facing`."""
        to = Vector((to[0], to[1], to[2] if len(to) > 2 else self.pos.z))
        d = to - self.pos
        if d.length < 0.01:
            return frame
        heading = math.degrees(math.atan2(d.x, d.y))
        self._apply(self.pose, frame)
        self._key_root(frame)
        f = frame + int(0.3 * FPS)
        self._seat_step(frame, "stand", 0.3)  # getting up off a seat (forward, the way he sat) before the first step
        self.facing = _near_angle(self.facing, heading)
        self.pose = "stand"
        held = POSES[pose_after].get("rifle")  # walking: carry the rifle the way the pose after the walk holds it
        carry = held if held in ("hip", "shoulder") else "sling"
        self._apply("stand", f, rifle=carry)
        self._key_root(f)
        steps = max(2, round(d.length / (speed * 0.5)))
        start = self.pos.copy()
        for i in range(1, steps + 1):
            fi = f + int(i * 0.5 * FPS)
            amp = 40 if speed > 2.2 else 25  # running strides are wider
            sw = amp if i % 2 else -amp
            gait = {"hip_L": (sw, 0, 0), "hip_R": (-sw, 0, 0), "knee_L": (0 if sw > 0 else -25, 0, 0),
                    "knee_R": (-25 if sw > 0 else 0, 0, 0), "shoulder_L": (-sw * 0.6, 0, 0), "shoulder_R": (sw * 0.6, 0, 0)}
            if self.name == "Andrei":  # keeps the flashlight up while walking
                gait.pop("shoulder_R")
            self.pos = start + d * (i / steps)
            self._key_root(fi)
            self._apply("flashlight" if self.name == "Andrei" else "stand", fi, walk=gait, rifle=carry)
        end = f + int(steps * 0.5 * FPS)
        self._apply(pose_after, end + int(0.3 * FPS))
        self.pose = pose_after
        if facing is not None:
            self.turn(end, facing, 0.4)
        return end


    def move(self, frame, to, dur, facing=None, pose=None):
        """Slide to `to` in `dur` seconds without stepping: riding a handcar, being carried, sliding a body.
        dur < one frame is a cut: the actor is simply somewhere else from `frame` on (no flight in between)."""
        cut = int(dur * FPS) < 1
        self._key_root(frame - 1 if cut else frame)
        if pose:
            self._apply(self.pose, frame)
        self.pos = Vector((to[0], to[1], to[2] if len(to) > 2 else self.pos.z))
        if facing is not None:
            self.facing = _near_angle(self.facing, facing)
        end = frame + max(int(dur * FPS), 0)
        self._key_root(end)
        if pose:
            self.pose = pose
            self._apply(pose, end)
        return end


def _near_angle(cur, target):
    """Equivalent of `target` closest to `cur`, so turns take the short way round."""
    return cur + ((target - cur + 180) % 360 - 180)


# ---------------------------------------------------------------- cameras and passes

def camera(name, loc, target, lens):
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object
    c.name = name
    c.data.lens = lens
    c.data.clip_start = 0.02
    aim(c, loc, target)
    return c


def aim(c, loc, target):
    c.location = loc
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def setup_render(width=1344, height=756):
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.view_settings.view_transform = "AgX"
    sc.eevee.taa_render_samples = 12  # enough for a lighting reference; more barely changes it
    w = bpy.data.worlds.new("dark")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.0008, 0.0008, 0.001, 1)
    # Dusty air: makes flashlight and searchlight beams visible as shafts (the metro is never clean air).
    nt = w.node_tree
    haze = nt.nodes.new("ShaderNodeVolumeScatter")
    haze.name = "haze"
    haze.inputs["Density"].default_value = 0.012
    nt.links.new(haze.outputs[0], nt.nodes["World Output"].inputs["Volume"])
    sc.eevee.volumetric_tile_size, sc.eevee.volumetric_end = "8", 60.0
    w.color = (0.03, 0.03, 0.035)  # Workbench background
    w.mist_settings.start, w.mist_settings.depth = 0.3, 25
    sc.world = w
    sc.view_layers[0].use_pass_mist = True
    sh = sc.display.shading
    sh.color_type = "OBJECT"


def render_pass(kind, path):
    """lit = EEVEE with the scene's own lights (+ depth via mist); flat = object colours under even studio
    light with shadows and cavity; id = pure flat object colours."""
    sc = bpy.context.scene
    sh = sc.display.shading
    sc.view_settings.view_transform = "AgX" if kind == "lit" else "Standard"  # flat colours stay exact
    if kind == "lit":
        engines = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
        sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"  # 4.2 / 5.x
        sc.use_nodes = True
        nt = sc.node_tree
        nt.nodes.clear()
        rl = nt.nodes.new("CompositorNodeRLayers")
        comp = nt.nodes.new("CompositorNodeComposite")
        nt.links.new(rl.outputs["Image"], comp.inputs["Image"])
        fo = nt.nodes.new("CompositorNodeOutputFile")
        fo.base_path = path.rsplit("/", 1)[0]
        fo.file_slots[0].path = path.rsplit("/", 1)[1].replace("_lit.png", "_depth_")
        nt.links.new(rl.outputs["Mist"], fo.inputs[0])
    else:
        sc.render.engine = "BLENDER_WORKBENCH"
        sc.use_nodes = False
        sh.light = "STUDIO" if kind == "flat" else "FLAT"
        sh.show_shadows = sh.show_cavity = kind == "flat"
    sc.render.filepath = path
    saved = {}
    if kind == "id":  # only people keep their colour
        for o in sc.objects:
            if o.type in ("MESH", "FONT") and o.name not in CHAR_OBJECTS:
                saved[o.name] = tuple(o.color)
                o.color = (0.35, 0.35, 0.35, 1)
    for o in sc.objects:  # smoke volumes only exist for the lit pass; in Workbench they would be solid boxes
        if o.get("lit_only"):
            o.hide_render = kind != "lit"
    bpy.ops.render.render(write_still=True)
    for n, c in saved.items():
        sc.objects[n].color = c


# ---------------------------------------------------------------- props for chapter 1

def handcar(name):
    """Track handcar: deck on four wheels, pump lever on a post. Its origin sits on the rails, +Y forward."""
    root = empty(name)
    iron = mat("handcar_iron", (0.08, 0.07, 0.06), flat=(0.30, 0.30, 0.34), rough=0.5, metal=0.7)
    wood = mat("old_wood", (0.13, 0.08, 0.05), flat=(0.45, 0.30, 0.15))
    attach(box((1.9, 2.4, 0.08), (0, 0, 0), wood, name=f"{name}.deck"), root, (0, 0, 0.62))
    for x in (-0.795, 0.795):  # on the rail heads (0.29 above the origin), gauge 1520
        for y in (-0.8, 0.8):
            attach(cyl(0.22, 0.08, (0, 0, 0), iron, (0, math.pi / 2, 0), 16, f"{name}.wheel"), root, (x, y, 0.51))
    attach(cyl(0.05, 0.9, (0, 0, 0), iron, name=f"{name}.post"), root, (0, 0, 1.1))
    attach(box((0.06, 1.4, 0.06), (0, 0, 0), iron, name=f"{name}.lever"), root, (0, 0, 1.58))
    return root


def sandbags(name, width=4.0, height=1.2, depth=0.6):
    """Wall of stacked sandbags across X, centred on the origin."""
    root = empty(name)
    sack = mat("sandbag", (0.30, 0.26, 0.18), flat=(0.72, 0.64, 0.45))
    rows = int(height / 0.2)
    for r in range(rows):
        off = 0.25 if r % 2 else 0.0
        n = int(width / 0.5)
        for i in range(n):
            x = -width / 2 + 0.25 + i * 0.5 + off
            if x > width / 2 - 0.2:
                continue
            o = sphere(0.25, (0, 0, 0), sack, name=f"{name}.bag", scale=(1.0, depth / 0.5, 0.42))
            attach(o, root, (x, 0, 0.1 + r * 0.2))
    return root


def machine_gun(name):
    """Heavy machine gun on a tripod mount, barrel along +Y."""
    root = empty(name)
    g = mat("gunmetal", (0.03, 0.03, 0.03), flat=(0.05, 0.05, 0.05), rough=0.4, metal=0.7)
    for a in (0, 120, 240):
        leg = cyl(0.02, 0.8, (0, 0, 0), g, (math.radians(-30), 0, math.radians(a)), 6, f"{name}.leg")  # feet splayed outward
        attach(leg, root, (0.18 * math.sin(math.radians(a)), -0.18 * math.cos(math.radians(a)), 0.35))
    attach(box((0.14, 0.6, 0.16), (0, 0, 0), g, name=f"{name}.body"), root, (0, 0, 0.75))
    attach(cyl(0.025, 0.9, (0, 0, 0), g, (math.pi / 2, 0, 0), 10, f"{name}.barrel"), root, (0, 0.75, 0.77))
    attach(box((0.12, 0.12, 0.12), (0, 0, 0), mat("ammo_box", (0.12, 0.14, 0.08), flat=(0.35, 0.40, 0.20)), name=f"{name}.ammo"), root, (0.14, 0.05, 0.72))
    return root


def searchlight(name, handheld=False):
    """Searchlight housing (cylinder with a glowing lens) facing +Y; pair it with a spot light in the spec."""
    root = empty(name)
    shell = mat("lamp_shell", (0.05, 0.05, 0.05), flat=(0.25, 0.25, 0.25), rough=0.4, metal=0.6)
    lens = mat("lamp_lens", (1, 1, 0.95), flat=(1, 1, 0.8), emit=(1, 0.97, 0.9), strength=20)
    r = 0.09 if handheld else 0.22
    attach(cyl(r, r * 1.6, (0, 0, 0), shell, (math.pi / 2, 0, 0), 16, f"{name}.shell"), root)
    attach(cyl(r * 0.9, 0.01, (0, 0, 0), lens, (math.pi / 2, 0, 0), 16, f"{name}.lens"), root, (0, r * 0.8, 0)).visible_shadow = False
    if not handheld:
        g = mat("gunmetal", (0.03, 0.03, 0.03), flat=(0.05, 0.05, 0.05), rough=0.4, metal=0.7)
        attach(cyl(0.03, 1.2, (0, 0, 0), g, name=f"{name}.stand"), root, (0, 0, -0.75))
    return root


def flame_jet(name, length=6.0, width0=0.08):
    """Flamethrower jet along +Y: an emissive cone with a strong light inside; toggle it with show/hide."""
    root = empty(name)
    # a wall of orange fire that widens to fill the tunnel, not a white needle (emission kept low so AgX keeps the colour)
    fire = mat("flame_jet", (0, 0, 0), flat=(1.0, 0.55, 0.05), rough=1, emit=(1.0, 0.22, 0.02), strength=0.9)
    core = mat("flame_core", (0, 0, 0), flat=(1.0, 0.75, 0.2), rough=1, emit=(1.0, 0.45, 0.06), strength=2.0)
    for m, r, n in ((fire, 1.8, "cone"), (core, 0.7, "core")):
        c = cone(width0 * r / 1.8, r, length, (0, 0, 0), m, (math.pi / 2, 0, math.pi), f"{name}.{n}")  # width0: radius at the nozzle end
        c.visible_shadow = False
        attach(c, root, (0, length / 2, 0))
    bpy.ops.object.light_add(type="POINT")
    li = bpy.context.object
    li.name = f"{name}.light"
    li.data.energy, li.data.color, li.data.shadow_soft_size = 800, (1.0, 0.42, 0.1), 1.5
    attach(li, root, (0, length * 0.5, 0))
    return root


def rat_flood(name, width=6.0, length=10.0):
    """Grey seething mass of rats: a lumpy carpet (displaced plane) spanning width x length from its origin
    toward +Y. Animate its spread with the 'prop' event (scale Y from ~0 to 1)."""
    root = empty(name)
    fur = mat("rat_fur", (0.12, 0.11, 0.10), flat=(0.50, 0.48, 0.46), rough=0.9)
    bpy.ops.mesh.primitive_plane_add(size=1)
    p = put(bpy.context.object, fur, f"{name}.carpet")
    p.scale = (width, length, 1)
    bpy.ops.object.transform_apply(scale=True)
    sub = p.modifiers.new("sub", "SUBSURF")
    sub.subdivision_type, sub.levels, sub.render_levels = "SIMPLE", 6, 6
    tex = bpy.data.textures.new(f"{name}_noise", "CLOUDS")
    tex.noise_scale = 0.08
    d = p.modifiers.new("lumps", "DISPLACE")
    d.texture, d.strength, d.mid_level = tex, 0.18, 0.2
    attach(p, root, (0, length / 2, 0.06))
    return root


def puppy(name):
    """Small dog, facing +Y."""
    root = empty(name)
    fur = mat("puppy_fur", (0.20, 0.15, 0.10), flat=(0.85, 0.70, 0.45))
    attach(sphere(0.09, (0, 0, 0), fur, name=f"{name}.body", scale=(0.8, 1.4, 0.8)), root, (0, 0, 0.12))
    attach(sphere(0.06, (0, 0, 0), fur, name=f"{name}.head"), root, (0, 0.14, 0.2))
    return root


def shotgun(name):
    """Double-barrelled shotgun, barrels along +Y."""
    root = empty(name)
    g = mat("gunmetal", (0.03, 0.03, 0.03), flat=(0.05, 0.05, 0.05), rough=0.4, metal=0.7)
    w = mat("gun_wood", (0.18, 0.08, 0.03), flat=(0.45, 0.22, 0.08))
    for x in (-0.012, 0.012):
        attach(cyl(0.012, 0.75, (0, 0, 0), g, (math.pi / 2, 0, 0), 8, f"{name}.barrel"), root, (x, 0.30, 0.0))
    attach(box((0.045, 0.40, 0.08), (0, 0, 0), w, name=f"{name}.stock"), root, (0, -0.25, -0.03))
    return root


def block(name, size=(0.3, 0.3, 0.3), color=(0.5, 0.5, 0.5)):
    """Generic stand-in prop (backpack, books, bench, table...): a coloured box resting on its origin."""
    root = empty(name)
    m = mat(f"block_{tuple(color)}", tuple(c * 0.4 for c in color), flat=tuple(color))
    attach(box(size, (0, 0, 0), m, name=f"{name}.box"), root, (0, 0, size[2] / 2))
    return root


def crowd(n, zones, z, avoid, seed=1):
    """Background residents: n simple standing/sitting figures (body + head) scattered over `zones`
    [((x0, x1), (y0, y1)), ...] on floor z, kept 1.5 m from every point in `avoid` (where the cast acts).
    Beige in the flat pass, counted as people in the id pass."""
    rng = random.Random(seed)
    cloth = [mat(f"crowd_cloth_{i}", c, flat=CHAR_COLORS["Extra"]) for i, c in
             enumerate(((0.10, 0.09, 0.08), (0.07, 0.08, 0.06), (0.12, 0.10, 0.07), (0.06, 0.06, 0.07)))]
    skin = mat("crowd_skin", (0.45, 0.32, 0.25), flat=CHAR_COLORS["Extra"])
    placed = 0
    for _ in range(n * 20):
        if placed == n:
            break
        (x0, x1), (y0, y1) = rng.choice(zones)
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if any((x - a) ** 2 + (y - b) ** 2 < 2.25 for a, b in avoid):
            continue
        h = rng.uniform(1.0, 1.15) if rng.random() < 0.35 else rng.uniform(1.55, 1.85)  # sitting or standing
        body = cyl(0.19, h - 0.25, (x, y, z + (h - 0.25) / 2), rng.choice(cloth), verts=8, name=f"crowd_{placed}.body")
        head = sphere(0.11, (x, y, z + h - 0.12), skin, name=f"crowd_{placed}.head")
        CHAR_OBJECTS.update((body.name, head.name))
        avoid = [*avoid, (x, y)]
        placed += 1
    return placed


def muzzle_flash(name, size=0.35):
    """Muzzle flash along +Y: three crossed flat flame cones and a short-range hot light; show/hide it per shot."""
    root = empty(name)
    hot = mat("muzzle_fire", (1, 0.7, 0.3), flat=(1.0, 0.85, 0.3), rough=1, emit=(1.0, 0.65, 0.25), strength=60)
    for a in (0, 60, 120):
        c = cone(size * 0.04, size * 0.35, size, (0, 0, 0), hot, (-math.pi / 2, math.radians(a), 0), f"{name}.cone")
        c.scale.x = 0.25
        c.visible_shadow = False
        attach(c, root, (0, size / 2, 0))
    bpy.ops.object.light_add(type="POINT")
    li = bpy.context.object
    li.name = f"{name}.light"
    li.data.energy, li.data.color, li.data.shadow_soft_size = 600, (1.0, 0.7, 0.35), 0.1
    attach(li, root, (0, size * 0.3, 0))
    return root


def lantern(name):
    """Homemade lantern: a small glowing box. Add a light in the spec attached to it to make it shine."""
    root = empty(name)
    glow = mat("lantern_glow", (1, 0.85, 0.5), flat=(1, 0.9, 0.6), emit=(1, 0.8, 0.45), strength=10)
    attach(box((0.1, 0.1, 0.14), (0, 0, 0), glow, name=f"{name}.box"), root).visible_shadow = False
    return root
