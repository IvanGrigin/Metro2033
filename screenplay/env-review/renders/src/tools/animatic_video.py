"""Animatic MP4 of one scene with subtitles burned in: frames from run_scene.py (12 fps), shots without a camera
(title cards) as black frames with their text, subtitles from the storyboard «Реплика» lines (make_srt.py timing).
Also writes the .srt next to the video and muxes it as a soft subtitle track (no libass needed).
    python3 storyboard/tools/animatic_video.py 1 storyboard/3d/out-r6/s001 out.mp4"""
import json, os, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_srt import srt

FPS = 12
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def cues(text):
    out = []
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        a, b = [sum(float(x) * m for x, m in zip(re.split("[:,]", t)[:3], (3600, 60, 1))) + int(t.split(",")[1]) / 1000
                for t in lines[1].split(" --> ")]
        out.append((a, b, " ".join(lines[2:])))
    return out


def wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = test
    return lines + [cur] if cur else lines


def main(n, render_dir, out_mp4):
    spec = json.load(open(os.path.join(REPO, f"storyboard/3d/scenes/s{n:03d}.json")))
    board = open(spec["storyboard"] if os.path.isabs(spec["storyboard"]) else os.path.join(REPO, spec["storyboard"]), encoding="utf-8").read()
    starts = dict(l.split("\t") for l in open(os.path.join(render_dir, "animatic_shots.txt")).read().split("\n") if l)
    srt_text = srt(n)
    cs = cues(srt_text)
    tmp = tempfile.mkdtemp()
    size = Image.open(os.path.join(render_dir, "animatic", "00000.png")).size
    font = ImageFont.truetype(FONT, max(18, size[1] // 22))
    k = 0
    t = 0.0
    for s in spec["shots"]:
        n_frames = int(round(s["dur"] * FPS))
        for i in range(n_frames):
            if s["id"] in starts:
                src = os.path.join(render_dir, "animatic", f"{int(starts[s['id']]) + i:05d}.png")
                im = Image.open(src).convert("RGB") if os.path.exists(src) else Image.new("RGB", size)
            else:  # no camera: a title card on black, text from the board («Кадр: «...»»)
                im = Image.new("RGB", size)
                m = re.search(rf"\*\*{re.escape(s['id'])} ·[^\n]*\n(?:Кадр: )?«?([^»\n]*)", board)
                if m:
                    d = ImageDraw.Draw(im)
                    tt = m.group(1).strip("«» ")
                    d.text(((size[0] - d.textlength(tt, font=font)) / 2, size[1] / 2 - font.size), tt, font=font, fill=(235, 235, 235))
            now = t + i / FPS
            line = next((c[2] for c in cs if c[0] <= now < c[1]), None)
            if line:
                d = ImageDraw.Draw(im)
                rows = wrap(d, line, font, size[0] * 0.86)
                y = size[1] - (len(rows) + 0.6) * font.size * 1.25
                for r in rows:
                    x = (size[0] - d.textlength(r, font=font)) / 2
                    d.text((x, y), r, font=font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
                    y += font.size * 1.25
            im.save(os.path.join(tmp, f"{k:05d}.png"))
            k += 1
        t += s["dur"]
    srt_path = os.path.splitext(out_mp4)[0] + ".srt"
    open(srt_path, "w", encoding="utf-8").write(srt_text)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "%05d.png"), "-i", srt_path,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:s", "mov_text", "-metadata:s:s:0", "language=rus",
                    out_mp4], check=True)
    print(out_mp4, k, "frames", f"{k / FPS:.1f} s", len(cs), "subtitles")


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], sys.argv[3])
