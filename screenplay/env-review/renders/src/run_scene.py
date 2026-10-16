"""Build, animate and render one scene from its JSON spec.

    blender -b -P storyboard/3d/run_scene.py -- storyboard/3d/scenes/s001.json OUT_DIR [--shots 1.02,1.05] [--no-stills] [--no-animatic] [--preview]

Shot timing comes from the storyboard durations; events are pinned to a shot start ("at") plus "dt" seconds.
Per shot it renders stills at the first frame, every whole second and the last frame, each in four passes:
<shot>_<t>s_lit.png, _flat.png, _id.png, _depth.png. The animatic is the flat pass of every shot in order,
written as numbered frames (assembled into MP4 outside Blender).
"""
import bpy, json, math, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import kit
from kit import FPS
from locations import LOCATIONS, BOUNDS, VIEWS, PLAT_H as PLAT_H_VDNKH

args = sys.argv[sys.argv.index("--") + 1:]
spec_path, out = os.path.abspath(args[0]), os.path.abspath(args[1])
only = args[args.index("--shots") + 1].split(",") if "--shots" in args else None
spec = json.load(open(spec_path, encoding="utf-8"))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
kit.setup_render()
LOCATIONS[spec["location"]]()
# Scene state controlled by the scene, not baked into the location (env-critic rule E): clock time and how bright
# the location's own lights are ("night" at a station dims them).
if "clock_digits" in bpy.data.objects:  # a station clock is in this location: the scene must say what it shows
    assert "clock" in spec, f'{spec["id"]}: location {spec["location"]} has a clock, set "clock": "HH:MM" in the scene'
    bpy.data.objects["clock_digits"].data.body = spec["clock"]
for o in list(bpy.context.scene.objects):
    if o.type == "LIGHT":
        o.data.energy *= spec.get("light_scale", 1.0)
        if "light_color" in spec and "fire" not in o.name:  # e.g. the "almost brown" VDNKh night instead of its red
            o.data.color = spec["light_color"]

# timeline: shot starts from storyboard durations
t, starts = 0.0, {}
for s in spec["shots"]:
    starts[s["id"]] = t
    t += s["dur"]
total = t
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, int(total * FPS) + 1


def frame_of(at, dt=0.0):
    return int(round((starts[at] + dt) * FPS)) + 1


# cast, props, lights
actors = {}
for name, c in spec["cast"].items():
    J = kit.person(name, c.get("height", 1.75), coat=c.get("coat", False), beret=c.get("beret", False), role=c.get("role"), costume=c.get("costume"))
    rifle = None
    if c.get("rifle"):
        rifle = kit.attach(kit.rifle(f"{name}.rifle"), J["chest"], *kit.RIFLE_HOLD["sling"])
    actors[name] = kit.Actor(name, J, rifle)
    kit.key_visible(J["root"], 1, True)  # so a later 'hide' only hides from that moment on
if spec["location"] == "vdnkh":  # ~200 people live here; at night most are inside their tents
    busy = [tuple(e.get("pos") or e.get("to"))[:2] for e in spec["events"] if e["do"] in ("place", "walk")]
    busy += [tuple(c[:2]) for c in spec.get("crates", [])]
    for sh in spec["shots"]:  # keep the first 6 m in front of every hand-placed lens clear of extras
        c = sh.get("cam", {})
        if isinstance(c.get("pos"), list) and isinstance(c.get("at"), list):
            p0, d = Vector(c["pos"][:2]), (Vector(c["at"][:2]) - Vector(c["pos"][:2])).normalized()
            busy += [tuple(p0 + d * k) for k in range(0, 7)]
    kit.crowd(spec.get("crowd", 60 if spec.get("light_scale", 1) >= 1 else 12),
              [((-3.7, 3.7), (-72, 58))], PLAT_H_VDNKH, busy)
for i, c in enumerate(spec.get("crates", [])):  # [x, y, facing] or [x, y, facing, floor_z]
    kit.crate(f"crate_{i}", (c[0], c[1], c[3] if len(c) > 3 else 0.0), c[2])
props = {}
for name, p in spec.get("props", {}).items():
    extra = {k: v for k, v in p.items() if k not in ("type", "attach", "loc", "rot", "hidden", "note")}  # e.g. size/color, handheld; "note" is a comment
    o = getattr(kit, p["type"])(name, **extra)
    parent = bpy.data.objects[p["attach"]] if "attach" in p else None
    rot = p.get("rot")
    if rot is None and p["type"] == "searchlight" and p.get("attach", "").split(".")[-1] in ("hand_R", "hand_L"):
        rot = (-math.pi / 2, 0, 0)  # housing faces +Y; in a hand it points along the arm (-Z)
    kit.attach(o, parent, p.get("loc", (0, 0, 0)), rot)
    kit.key_visible(o, 1, not p.get("hidden", False))
    props[name] = o
hidden_props = {n for n, p in spec.get("props", {}).items() if p.get("hidden")}
lights = {}
for name, l in spec.get("lights", {}).items():
    bpy.ops.object.light_add(type=l.get("type", "SPOT"))
    li = bpy.context.object
    li.name = name
    li.data.color = l.get("color", (1.0, 0.92, 0.8))
    if li.data.type == "SPOT":
        li.data.spot_size, li.data.spot_blend = math.radians(l.get("angle", 35)), 0.4
    in_hand = l["attach"].split(".")[-1] in ("hand_R", "hand_L")
    # beam along +Y of the parent; a hand's arm runs along its -Z, which is a spot light's own direction
    kit.attach(li, bpy.data.objects[l["attach"]], l.get("loc", (0, 0, 0)), (0, 0, 0) if in_hand else (math.pi / 2, 0, 0))
    li.data.energy = l.get("energy", 0)
    li.data.keyframe_insert("energy", frame=1)
    lights[name] = li

# events
for e in sorted(spec["events"], key=lambda e: frame_of(e["at"], e.get("dt", 0))):
    f = frame_of(e["at"], e.get("dt", 0))
    do = e["do"]
    if do in ("place", "pose", "walk", "turn", "look", "move"):
        a = actors[e["actor"]]
        if do == "place":
            a.place(f, e["pos"], e.get("facing", 0), e.get("pose", "stand"))
        elif do == "pose":
            a.set_pose(f, e["pose"], e.get("dur", 0.6))
        elif do == "walk":
            a.walk(f, e["to"], e.get("facing"), e.get("speed", 1.2), e.get("pose_after", "stand"))
        elif do == "turn":
            a.turn(f, e["facing"], e.get("dur", 0.5))
        elif do == "move":
            a.move(f, e["to"], e.get("dur", 1.0), e.get("facing"), e.get("pose"))
        else:
            a.look(f, e["yaw"], e.get("dur", 0.4))
    elif do in ("show", "hide"):
        target = actors[e["actor"]].J["root"] if "actor" in e and "prop" not in e else props[e["prop"]]
        kit.key_visible(target, f, do == "show")
        if "prop" in e:
            hidden_props.discard(e["prop"]) if do == "show" else hidden_props.add(e["prop"])
        elif do == "show":  # showing a person must not reveal the hidden props in their hands (mug before it is handed)
            for n in hidden_props:
                if props[n] in target.children_recursive:
                    kit.key_visible(props[n], f, False)
    elif do in ("prop_move", "prop_scale"):  # slide or grow a prop over dur seconds (handcar, rat flood)
        o = props.get(e["prop"]) or bpy.data.objects[e["prop"]]  # scene prop or a location object (doors)
        attr = "location" if do == "prop_move" else "scale"
        o.keyframe_insert(attr, frame=f)
        setattr(o, attr, e["to"])
        o.keyframe_insert(attr, frame=f + int(e.get("dur", 1.0) * FPS))
    elif do == "light":
        li = lights.get(e["light"]) or bpy.data.objects[e["light"]]  # spec light or a location light (e.g. tent_lamp)
        li.data.keyframe_insert("energy", frame=f - 1)
        li.data.energy = e["energy"]
        li.data.keyframe_insert("energy", frame=f)
        bulb = bpy.data.objects.get(f'{e["light"]}_bulb')  # a visible lamp body goes dark with its light
        if bulb:
            kit.key_visible(bulb, f, e["energy"] > 0)


def point(ref, frame):
    """World point: [x,y,z] or 'Actor.joint' evaluated at `frame`."""
    if isinstance(ref, str):
        sc.frame_set(frame)
        return bpy.data.objects[ref].matrix_world.translation.copy()
    return Vector(ref)


# one camera per shot; 'rel' places the camera relative to its target; 'push' dollies toward it
SIZE_BY_JOINT = {"eyes": 0.65, "chest": 1.5, "torso": 1.5, "rifle": 0.45, "hand_L": 0.4, "hand_R": 0.4}  # close-up, medium, detail
cams = {}
AUTO = {  # shot size -> (target joint, framed height in metres, lens)
    "xcu": ("eyes", 0.28, 85), "cu": ("eyes", 0.65, 70), "mcu": ("eyes", 0.95, 50), "med": ("torso", 1.5, 40),
    "ots": ("torso", 1.3, 40), "wide": ("torso", 5.0, 24), "detail": ("hand_R", 0.4, 60), "pov": ("eyes", 1, 28),
}


def inside(p, bounds):
    return all(lo <= v <= hi for v, (lo, hi) in zip(p, bounds))


def auto_camera(c, f0):
    """Camera from the storyboard: shot size + subject. Placed in front of the subject (from where they face),
    swung by `side` x 35 degrees, then pulled toward the subject until it is inside the location bounds."""
    joint, size, lens = AUTO[c["auto"]]
    subj = c.get("subject")
    if not subj or c["auto"] in ("dark",):
        return VIEWS[spec["location"]][c.get("view", "wide")]
    root = bpy.data.objects[subj]
    sc.frame_set(f0)
    tgt = bpy.data.objects[f"{subj}.{c.get('joint', joint)}"].matrix_world.translation.copy()
    face = root.matrix_world.to_3x3() @ Vector((0, 1, 0))
    if c["auto"] == "pov":  # through the subject's eyes, along where they face
        eyes = bpy.data.objects[f"{subj}.eyes"].matrix_world.translation.copy()
        return eyes + face * 0.15, eyes + face * 12 + Vector((0, 0, -0.3)), c.get("lens", 28)
    ang = math.radians(35 * c.get("side", 1) + (180 if c.get("behind") else 0))
    d = Vector((face.x * math.cos(ang) - face.y * math.sin(ang), face.x * math.sin(ang) + face.y * math.cos(ang), 0)).normalized()
    if c["auto"] == "ots":  # over the shoulder of `partner`, looking at subject
        partner = bpy.data.objects[f"{c['partner']}.eyes"].matrix_world.translation.copy() if c.get("partner") else None
        if partner:
            d = (partner - tgt).normalized()
            d.z = 0
    dz = {"low": -0.35, "high": 0.45}.get(c.get("angle"), 0.05)
    dist0 = size * c.get("lens", lens) / 20.25
    bounds = BOUNDS[spec["location"]]
    dg = bpy.context.evaluated_depsgraph_get()

    def place(direction):
        """Pull inside the bounds, then check the line of sight; returns (pos, clear, free distance)."""
        direction = direction.normalized()
        dist = dist0
        pos = tgt + direction * dist
        while not inside(pos, bounds) and dist > 0.3:
            dist *= 0.85
            pos = tgt + direction * dist
        start = tgt + direction * 0.3  # step out of the subject's own head/body
        hit, loc, _, _, obj, _ = sc.ray_cast(dg, start, direction, distance=max(dist - 0.3, 0.01))
        own = obj is not None and (obj.name.startswith(subj + ".") or (obj.parent and obj.parent.name.startswith(subj)))
        return pos, (not hit) or own, (loc - tgt).length if hit else dist

    base = math.atan2(d.y, d.x)
    best = None
    for off in (0, -2 * 35 * c.get("side", 1), 35, -35, 70, -70, 10, -10):  # first choice, then alternatives
        a = base + math.radians(off) if off else base
        cand = Vector((math.cos(a), math.sin(a), dz))
        pos, clear, free = place(cand)
        if clear:
            return pos, tgt, c.get("lens", lens)
        if best is None or free > best[1]:
            best = (cand, free)
    cand, free = best  # every angle is blocked: come in closer than the obstacle
    pos = tgt + cand.normalized() * max(free - 0.25, 0.35)
    return pos, tgt, c.get("lens", lens)


for s in spec["shots"]:
    if s.get("title"):
        continue
    c = s["cam"]
    f0, f1 = frame_of(s["id"]), frame_of(s["id"], s["dur"]) - 1
    if "auto" in c or "view" in c:
        pos, tgt, lens = auto_camera(c, f0) if "auto" in c else VIEWS[spec["location"]][c["view"]]
        pos, tgt = Vector(pos), Vector(tgt)
        cam = kit.camera(f"cam_{s['id']}", pos, tgt, lens)
        if c.get("push"):
            cam.keyframe_insert("location", frame=f0)
            cam.location = pos + (tgt - pos) * c["push"]
            cam.keyframe_insert("location", frame=f1)
        cams[s["id"]] = (cam, f0, f1)
        continue
    tgt = point(c["at"], f0)
    if "rel" in c:  # distance from framing: subject height in metres that fills the frame height at this lens
        size = c.get("size", SIZE_BY_JOINT.get(str(c["at"]).split(".")[-1], 0.5))
        pos = tgt + Vector(c["rel"]).normalized() * (size * c.get("lens", 35) / 20.25)
    else:
        pos = Vector(c["pos"])
    cam = kit.camera(f"cam_{s['id']}", pos, tgt, c.get("lens", 35))
    if c.get("push"):
        cam.keyframe_insert("location", frame=f0)
        cam.location = pos + (tgt - pos) * c["push"]
        cam.keyframe_insert("location", frame=f1)
    cams[s["id"]] = (cam, f0, f1)

os.makedirs(out, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, f"{spec['id']}.blend"))

shots = [s for s in spec["shots"] if s["id"] in cams and (only is None or s["id"] in only)]
if "--preview" in args:  # quick camera check: flat pass of each shot's first frame only
    bpy.context.scene.render.resolution_percentage = 50  # half size: enough to judge framing, a quarter of the GPU work
    pv = os.path.join(out, "preview")
    os.makedirs(pv, exist_ok=True)
    for s in shots:
        cam, f0, f1 = cams[s["id"]]
        sc.camera = cam
        sc.frame_set(f0)
        kit.render_pass("flat", os.path.join(pv, f"{s['id']}.png"))
    print("PREVIEW", len(shots), flush=True)
    sys.exit(0)
if "--no-stills" not in args:
    st = os.path.join(out, "stills")
    os.makedirs(st, exist_ok=True)
    for s in shots:
        cam, f0, f1 = cams[s["id"]]
        sc.camera = cam
        frames = sorted({*range(f0, f1, FPS), f1})
        for f in frames:
            sc.frame_set(f)
            stem = os.path.join(st, f"{s['id']}_{(f - f0) / FPS:.1f}s")
            for kind in ("lit", "flat", "id"):
                kit.render_pass(kind, f"{stem}_{kind}.png")
            src = f"{stem}_depth_{f:04d}.png"
            if os.path.exists(src):
                os.replace(src, f"{stem}_depth.png")
        print("STILLS", s["id"], len(frames), flush=True)

if "--no-animatic" not in args:
    an = os.path.join(out, "animatic")
    os.makedirs(an, exist_ok=True)
    sc.render.resolution_percentage = 50
    n = 0
    with open(os.path.join(out, "animatic_shots.txt"), "w") as log:
        for s in shots:
            cam, f0, f1 = cams[s["id"]]
            sc.camera = cam
            log.write(f"{s['id']}\t{n}\n")
            for f in range(f0, f1 + 1, 2):  # 12 fps
                sc.frame_set(f)
                kit.render_pass("flat", os.path.join(an, f"{n:05d}.png"))
                n += 1
    sc.render.resolution_percentage = 100
    print("ANIMATIC frames", n, flush=True)
print("DONE", spec["id"], flush=True)
