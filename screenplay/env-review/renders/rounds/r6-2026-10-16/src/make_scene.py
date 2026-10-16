"""Build a scene spec for run_scene.py from a hand-written blocking file and the storyboard.

    python3 storyboard/tools/make_scene.py storyboard/3d/scenes/s004.block.json

The blocking file holds what only a person can decide: location, cast, crates, props, lights, events, and a
map from names used in the storyboard's EN prompts to cast ids ("names"). Shots, durations and cameras come
from the storyboard: shot size, subject (first cast name in the EN line), 'from behind', low/high angle,
push-in/pull-out, point of view, darkness. Per-shot overrides go in "cams". Writes sNNN.json next to it.
"""
import json, re, sys
from pathlib import Path

SB = Path(__file__).resolve().parents[1]
blk_path = Path(sys.argv[1]).resolve()
blk = json.loads(blk_path.read_text(encoding="utf-8"))
num = int(blk["id"][1:])
board_file = next(SB.glob(f"[0-9][0-9]-*/{num:03d}-*.md"))
board = board_file.read_text(encoding="utf-8").split("## Раскадровка", 1)[1]
blocks = re.split(r"^\*\*(?=\d+\.\d\d · )", board, flags=re.M)[1:]
names = blk.get("names", {})  # EN name -> cast id, longest first so 'young Artyom' wins over 'Artyom'
order = sorted(names, key=len, reverse=True)

SIZES = [("сверхкрупн", "xcu"), ("крупн", "cu"), ("через плечо", "ots"), ("средн", "med"), ("двое", "med"),
         ("общ", "wide"), ("детал", "detail"), ("точка зрения", "pov"), ("тьма", "dark")]


def camera(head, en, last_subject, side):
    h = head.lower()
    kind = next((k for key, k in SIZES if key in h), "med")
    subject, pos = None, 10 ** 9
    for n in order:  # the name mentioned first in the EN line is the subject
        m = re.search(rf"\b{re.escape(n)}\b", en, re.I)
        if m and m.start() < pos:
            subject, pos = names[n], m.start()
    cam = {"auto": kind}
    if kind == "dark" or not subject:
        cam = {"view": "dark" if kind in ("dark", "pov") or "тьм" in h or "darkness" in en.lower() else "wide"}
    else:
        cam["subject"] = subject
        cam["side"] = side
    if "со спины" in h or "from behind" in en.lower():
        cam["behind"] = True
    if "нижн" in h or "низк" in h or "low angle" in en.lower():
        cam["angle"] = "low"
    elif "верхн" in h or "high angle" in en.lower():
        cam["angle"] = "high"
    if "наезд" in h or "push in" in en.lower():
        cam["push"] = 0.15
    elif "отъезд" in h or "отступает" in h:
        cam["push"] = -0.15
    return cam, subject


shots, last, side = [], None, 1
for b in blocks:
    m = re.match(r"(\d+\.\d\d) · ([\d,]+) с · (.+?)\*\*", b)
    sid, dur, head = m.group(1), float(m.group(2).replace(",", ".")), m.group(3)
    en = (re.search(r"^EN: (.+)$", b, re.M) or [None, ""])[1]
    cam, subject = camera(head, en, last, side)
    if subject and subject != last:
        side = -side  # alternate sides on a change of subject: shot / reverse shot
        cam["side"] = side
    last = subject or last
    over = blk.get("cams", {}).get(sid, {})
    if any(k in over for k in ("pos", "rel", "view", "attach")):
        cam = dict(over)  # a hand-placed or view camera replaces the derived one entirely
    else:
        cam.update(over)
    shots.append({"id": sid, "dur": dur, "cam": cam})

spec = {k: blk[k] for k in ("id", "location", "cast") if k in blk}
spec["title"] = board_file.read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
spec["storyboard"] = str(board_file.relative_to(SB.parent))
for k in ("crates", "props", "lights", "events", "clock", "light_scale", "light_color", "crowd"):
    if k in blk:
        spec[k] = blk[k]
spec["shots"] = shots
out = blk_path.with_name(blk_path.name.replace(".block.json", ".json"))
out.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
print(out.name, len(shots), "shots", round(sum(s["dur"] for s in shots), 1), "s")
