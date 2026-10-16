"""Multi-shot sequences for Kling 4.0 (omni_ref_video, prefer_multi_shots): consecutive shots of a scene joined at their
cuts into chunks of at most MAX seconds, up to a total budget. Each chunk = one reference clip (the shots' own Kling
frames, handles cut off, so 视频1 cuts exactly where the film cuts) + one prompt that lists the shots with their times.
    python3 storyboard/tools/kling_seq.py 1 storyboard/3d/out-r6/s001 storyboard/kling/s001/seq 1.02 1.37 15"""
import json, math, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kling_pack import FPS, REPO, ROOT, TIME, characters

RULES = ("Photorealistic live-action film, 35 mm, post-apocalyptic Moscow metro in 2033: soot, grime, damp, worn clothes. "
         "Follow 视频1 exactly: the same shots in the same order, hard cuts only where 视频1 cuts and nowhere else; in every "
         "shot keep its camera position, framing, movement and timing, and where each person is and what they do. "
         "Replace the grey mannequins with real people (the cone on a head marks the nose: where the face looks); the same "
         "person keeps the same face and clothes in every shot. Light only from the sources visible in 视频1 (fire, lamps, "
         "flashlights), everything else stays dark. No text, letters or numbers on screen except painted marks that exist "
         "in 视频1; no extra people or objects.")


def main(n, render_dir, out_dir, first, last, cap):
    spec = json.load(open(os.path.join(REPO, f"storyboard/3d/scenes/s{n:03d}.json")))
    board = open(os.path.join(REPO, spec["storyboard"]), encoding="utf-8").read().split("## Раскадровка", 1)[1]
    en = {sid: re.search(r"^EN: (.+)$", body, re.M).group(1)
          for sid, body in re.findall(r"^\*\*(\d+\.\d\d) · [^\n]*\*\*$(.*?)(?=^\*\*\d+\.\d\d · |\Z)", board, re.M | re.S)
          if re.search(r"^EN: (.+)$", body, re.M)}
    kinfo = json.load(open(os.path.join(render_dir, "kling", "shots.json")))
    env = json.load(open(os.path.join(ROOT, "kling", "environment.json")))[spec["location"]]
    word = next((w for w in TIME if w in os.path.basename(spec["storyboard"])), None)
    chars = characters()
    ids = [s["id"] for s in spec["shots"]]
    shots = [s for s in spec["shots"][ids.index(first):ids.index(last) + 1] if s.get("cam")]
    chunks, cur = [], []
    for s in shots:  # greedy: close a chunk at the cut before it would pass the cap
        if cur and sum(x["dur"] for x in cur) + s["dur"] > cap:
            chunks.append(cur)
            cur = []
        cur.append(s)
    chunks.append(cur)
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for ci, ch in enumerate(chunks, 1):
        name = f"seq{ci:02d}_{ch[0]['id']}-{ch[-1]['id']}"
        lst = os.path.join(out_dir, name + ".txt")
        with open(lst, "w") as f:  # each shot's own frames inside its handles, joined: the cuts land where the film cuts
            for s in ch:
                k = kinfo[s["id"]]
                a = int(round(k["shot_from"] * FPS))
                for i in range(a, a + int(round(s["dur"] * FPS))):
                    f.write(f"file '{os.path.abspath(os.path.join(render_dir, 'kling', s['id'], f'{i:05d}.png'))}'\n"
                            f"duration {1 / FPS:.6f}\n")
        clip = os.path.join(out_dir, name + ".mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-r", "24",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", clip], check=True)
        os.remove(lst)
        t, lines, vis = 0.0, [], []
        for i, s in enumerate(ch, 1):
            lines.append(f"Shot {i} ({t:g}–{t + s['dur']:g} s): {en[s['id']]}.")
            t += s["dur"]
            vis += [v for v in kinfo[s["id"]]["visible"] if v in chars and v not in vis]
        who = [chars[c] for c in vis]
        prompt = " ".join([f"A sequence of {len(ch)} shots, {t:g} seconds."] + lines + who +
                          ["The place (only what 视频1 shows of it is in frame): " + env["full"], TIME.get(word, ""), RULES])
        sec = max(3, math.ceil(t - 0.01))
        rows.append({"chunk": name, "clip": os.path.basename(clip), "shots": [s["id"] for s in ch], "seconds": t,
                     "duration": sec, "chars": len(prompt), "prompt": prompt,
                     "note": f"generate {sec} s, keep 0–{t:g} s" if sec != t else ""})
    json.dump(rows, open(os.path.join(out_dir, "prompts.json"), "w"), ensure_ascii=False, indent=1)
    for r in rows:
        print(r["chunk"], r["seconds"], "s", r["chars"], "chars", r["note"])
    print("total", sum(r["seconds"] for r in rows), "s video,", sum(r["duration"] for r in rows), "s billed output")


if __name__ == "__main__":
    a = sys.argv
    main(int(a[1]), a[2], a[3], a[4], a[5], float(a[6]))
