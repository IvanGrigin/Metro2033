"""Overview renders of every location (flat pass) for a quick visual check.
    blender -b -P storyboard/3d/tools_location_preview.py -- OUT_DIR [name,...]"""
import bpy, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import kit
from locations import LOCATIONS
args = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(args[0])
names = args[1].split(",") if len(args) > 1 else list(LOCATIONS)
VIEWS = {  # (camera, target, lens) per location
    "tunnel_250": ((0.3, -8, 1.6), (-0.8, 2, 0.6), 24), "north_cordon": ((0.5, -5, 1.7), (0, 3, 1.0), 24),
    "peregon_savelovskaya": ((0.3, 45, 1.6), (0, 62, 1.0), 24), "timiryazevskaya": ((2.0, 50, 2.9), (-8, 73, 1.6), 24),
    "vdnkh": ((-1.5, -40, 1.9), (5.5, -31, 2.6), 22), "botanical": ((1.0, -83, 2.8), (0, 0, 2.7), 24),
    "botanical_vestibule": ((-5, -6, 1.7), (2, 5, 3.5), 18), "sukhoi_tent": ((-1.4, -1.9, 1.7), (0.5, 1.5, 0.6), 16),
    "vdnkh_office": ((-1.7, -2.2, 1.7), (0.3, 1.5, 0.9), 18), "white_room": ((0, -4.5, 1.6), (0, 0, 1.5), 24),
}
os.makedirs(out, exist_ok=True)
for n in names:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    kit._mats.clear()
    kit.setup_render(960, 540)
    LOCATIONS[n]()
    loc, tgt, lens = VIEWS[n]
    bpy.context.scene.camera = kit.camera("cam", loc, tgt, lens)
    for kind in ("flat", "lit"):
        kit.render_pass(kind, os.path.join(out, f"{n}_{kind}.png"))
    print("LOC", n, flush=True)
