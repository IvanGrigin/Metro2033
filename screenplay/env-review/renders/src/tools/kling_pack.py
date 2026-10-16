"""Reference pack for a video model (Kling) from one scene: a clean clip per shot (the lit animatic frames — no
subtitles, no title cards, no overlays), plus one prompt per shot: the board's EN line, the same character
descriptions from characters.md for everyone named in it, and the fixed rules. Shots without a camera (title
cards) are skipped and listed. With `run_scene.py --kling MIN` the clips come from each shot's own camera with real handles
up to MIN seconds and only the people visible in them are described (the rest of the named: off-screen).
    python3 storyboard/tools/kling_pack.py 1 storyboard/3d/out-r6/s001 storyboard/kling/s001"""
import json, os, re, shutil, subprocess, sys

FPS = 12
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
RULES = ("Photorealistic live-action film shot, 35 mm, post-apocalyptic Moscow metro in 2033: soot, grime, damp, worn "
         "clothes. One continuous single shot, no cuts, no change of camera angle. Follow 视频1 exactly: keep its camera "
         "position, framing, movement and timing, and where each person is and what they do. Replace the grey mannequins with real people (the cone on a head marks the nose: "
         "where the face looks). Light only from the sources visible in the reference (fire, lamps, flashlights), "
         "everything else stays dark. No text, letters or numbers on screen except painted marks that exist in the "
         "reference; no extra people or objects.")


def characters():
    out = {}
    for line in open(os.path.join(ROOT, "characters.md"), encoding="utf-8"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and ":" in cells[2] and not cells[2].startswith("EN"):
            out[cells[2].split(":", 1)[0].strip()] = cells[2].rstrip(".") + "."
    return out


TIME = {"ночь": "It is night.", "утро": "It is morning.", "день": "It is day.", "вечер": "It is evening."}  # underground: only the hour


def camera(c):
    """The shot's camera in words, from the scene spec (lens, riding, push-in)."""
    lens = c.get("lens", 35)
    size = "wide-angle" if lens <= 28 else "normal" if lens <= 40 else "long-lens close" if lens >= 70 else "medium-long"
    how = f"camera mounted on the {c['attach']}, moving with it" if "attach" in c else \
        "slow push-in" if c.get("push") else "static camera"
    return f"Camera: {size} {lens} mm lens, {how}."


def main(n, render_dir, out_dir):
    spec = json.load(open(os.path.join(REPO, f"storyboard/3d/scenes/s{n:03d}.json")))
    env = json.load(open(os.path.join(ROOT, "kling", "environment.json")))[spec["location"]]  # {"full", "short"}
    word = next((w for w in TIME if w in os.path.basename(spec["storyboard"])), None)
    when = TIME.get(word, "")
    board = open(os.path.join(REPO, spec["storyboard"]), encoding="utf-8").read().split("## Раскадровка", 1)[1]
    en = {}  # shot id -> its own EN line: split the board into shot blocks first, then look inside each block only
    for sid, body in re.findall(r"^\*\*(\d+\.\d\d) · [^\n]*\*\*$(.*?)(?=^\*\*\d+\.\d\d · |\Z)", board, re.M | re.S):
        m = re.search(r"^EN: (.+)$", body, re.M)
        if m:
            en[sid] = m.group(1)
    kinfo_path = os.path.join(render_dir, "kling", "shots.json")
    kinfo = json.load(open(kinfo_path)) if os.path.exists(kinfo_path) else {}  # run_scene.py --kling: own camera + handles
    starts = dict(l.split("\t") for l in open(os.path.join(render_dir, "animatic_shots.txt")).read().split("\n") if l)
    chars = characters()
    os.makedirs(out_dir, exist_ok=True)
    rows, skipped = [], []
    for s in spec["shots"]:
        if s["id"] not in starts and s["id"] not in kinfo:
            skipped.append(s["id"])
            continue
        line = en.get(s["id"], "").strip()
        assert line, f'{s["id"]}: no EN line in the storyboard'  # a prompt without the shot description is useless
        k = kinfo.get(s["id"])
        named = [c for c in chars if re.search(rf"\b{re.escape(c)}\b", line)]
        if k:  # describe exactly the people the reference shows: named ones in full, the rest as background
            vis = [v for v in k["visible"] if v in chars]
            who = [chars[c] for c in named if c in vis] + [f"In the background: {chars[c]}" for c in vis if c not in named]
        else:
            who = [chars[c] for c in named]
        c = s["cam"]
        # detail shot (the board calls it a close-up, or nobody is in a close frame): no list of the place's objects to paint in
        insert = line.lower().startswith(("close-up", "extreme close-up", "insert", "detail")) or (k is not None and not k["visible"])  # critic П1: no people → short place at any lens
        place = ("The place: " + env["short"]) if insert else \
            ("The place (only what the reference shows of it is in frame): " + env["full"])
        clock = f' The clock shows {spec["clock"]}.' if spec.get("clock") and "clock" in line else ""  # only if its face is in the shot
        prompt = " ".join(x for x in [line[:1].upper() + line[1:] + ".", camera(c)] + who + [place, when + clock, RULES] if x.strip())
        assert len(prompt) <= 2400, f'{s["id"]}: prompt {len(prompt)} chars, Kling limit ~2500'  # critic: fail before upload
        clip = os.path.join(out_dir, f'{s["id"]}.mp4')
        if k:
            src, first, count = os.path.join(render_dir, "kling", s["id"], "%05d.png"), 0, k["frames"]
            start = os.path.join(render_dir, "kling", s["id"], f'{int(round(k["shot_from"] * FPS)):05d}.png')
            shutil.copy(start, os.path.join(out_dir, f'{s["id"]}_start.png'))  # first frame of the shot: image-to-video (MCP)
            trim = "" if k["shot_from"] == 0 and abs(k["shot_to"] - s["dur"]) < 0.05 else \
                f'after generation keep {k["shot_from"]:.2f}–{k["shot_to"]:.2f} s (handles for the minimum length)'
        else:
            src, first, count, trim = os.path.join(render_dir, "animatic", "%05d.png"), int(starts[s["id"]]), int(round(s["dur"] * FPS)), ""
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-start_number", str(first),
                        "-i", src, "-frames:v", str(count), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", clip], check=True)
        rows.append({"shot": s["id"], "clip": os.path.basename(clip), "seconds": round(count / FPS, 2), "prompt": prompt,
                     "note": trim, "off_screen": [c for c in named if k and c not in k["visible"]]})
    json.dump(rows, open(os.path.join(out_dir, "prompts.json"), "w"), ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "manifest.md"), "w", encoding="utf-8") as m:
        m.write(f"# Kling: сцена {n} — референсы по планам\n\nКлип = чистый проход со светом (без текста), {FPS} кадров/с, "
                f"полный хронометраж плана. Планы без камеры (титры) пропущены: {', '.join(skipped) or 'нет'}.\n\n"
                "| План | Клип | с | Обрезка после генерации | Промпт |\n|---|---|---|---|---|\n")
        for r in rows:
            m.write(f"| {r['shot']} | {r['clip']} | {r['seconds']} | {r['note']} | {r['prompt']} |\n")
    print(out_dir, len(rows), "clips, skipped", skipped)


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], sys.argv[3])
