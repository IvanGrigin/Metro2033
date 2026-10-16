"""Reference pack for a video model (Kling) from one scene: a clean clip per shot (the lit animatic frames — no
subtitles, no title cards, no overlays), plus one prompt per shot: the board's EN line, the same character
descriptions from characters.md for everyone named in it, and the fixed rules. Shots without a camera (title
cards) are skipped and listed. Shots longer than MAX_SEC are cut into parts at even lengths and marked.
    python3 storyboard/tools/kling_pack.py 1 storyboard/3d/out-r6/s001 storyboard/kling/s001"""
import json, os, re, subprocess, sys

FPS, MAX_SEC = 12, 10.0
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
RULES = ("Photorealistic live-action film shot, 35 mm, post-apocalyptic Moscow metro in 2033: soot, grime, damp, worn "
         "clothes. Keep exactly the camera position, framing, movement and timing of the reference video, and where each "
         "person is and what they do. Replace the grey mannequins with real people (the cone on a head marks the nose: "
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


def main(n, render_dir, out_dir):
    spec = json.load(open(os.path.join(REPO, f"storyboard/3d/scenes/s{n:03d}.json")))
    board = open(os.path.join(REPO, spec["storyboard"]), encoding="utf-8").read().split("## Раскадровка", 1)[1]
    en = {}  # shot id -> its own EN line: split the board into shot blocks first, then look inside each block only
    for sid, body in re.findall(r"^\*\*(\d+\.\d\d) · [^\n]*\*\*$(.*?)(?=^\*\*\d+\.\d\d · |\Z)", board, re.M | re.S):
        m = re.search(r"^EN: (.+)$", body, re.M)
        if m:
            en[sid] = m.group(1)
    starts = dict(l.split("\t") for l in open(os.path.join(render_dir, "animatic_shots.txt")).read().split("\n") if l)
    chars = characters()
    os.makedirs(out_dir, exist_ok=True)
    rows, skipped = [], []
    for s in spec["shots"]:
        if s["id"] not in starts:
            skipped.append(s["id"])
            continue
        frames = int(round(s["dur"] * FPS))
        parts = max(1, -(-frames // int(MAX_SEC * FPS)))
        line = en.get(s["id"], "").strip()
        assert line, f'{s["id"]}: no EN line in the storyboard'  # a prompt without the shot description is useless
        who = [chars[name] for name in chars if re.search(rf"\b{re.escape(name)}\b", line)]
        prompt = " ".join([line[:1].upper() + line[1:] + "."] + who + [RULES])
        for p in range(parts):
            a = int(starts[s["id"]]) + p * frames // parts
            b = int(starts[s["id"]]) + (p + 1) * frames // parts
            name = s["id"] + (f"_part{p + 1}" if parts > 1 else "")
            clip = os.path.join(out_dir, f"{name}.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-start_number", str(a),
                            "-i", os.path.join(render_dir, "animatic", "%05d.png"), "-frames:v", str(b - a),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", clip], check=True)
            rows.append({"shot": name, "clip": os.path.basename(clip), "seconds": round((b - a) / FPS, 2), "prompt": prompt,
                         "note": f"part {p + 1}/{parts} of {s['id']}" if parts > 1 else ""})
    json.dump(rows, open(os.path.join(out_dir, "prompts.json"), "w"), ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "manifest.md"), "w", encoding="utf-8") as m:
        m.write(f"# Kling: сцена {n} — референсы по планам\n\nКлип = чистый проход со светом (без текста), {FPS} кадров/с, "
                f"полный хронометраж плана. Планы без камеры (титры) пропущены: {', '.join(skipped) or 'нет'}.\n\n"
                "| План | Клип | с | Промпт |\n|---|---|---|---|\n")
        for r in rows:
            m.write(f"| {r['shot']} | {r['clip']} | {r['seconds']} | {r['prompt']} |\n")
    print(out_dir, len(rows), "clips, skipped", skipped)


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], sys.argv[3])
