"""Subtitles (SRT) for a scene from its storyboard: each «Реплика» line is shown during its shot (several lines in one
shot share it evenly). Shot starts come from the board durations — the same timeline run_scene.py uses.
    python3 storyboard/tools/make_srt.py 1 > s001.srt"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ts(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def unquote(text):
    """The board writes a line as «text». or «text»: drop the outer guillemets wherever the closing one sits."""
    t = text.strip()
    if t.startswith("«"):
        t = t[1:]
        i = t.rfind("»")
        if i >= 0:
            t = t[:i] + t[i + 1:]
    return t.strip()


def srt(n):
    f = glob.glob(os.path.join(ROOT, f"*/{n:03d}-*.md"))[0]
    board = open(f, encoding="utf-8").read().split("## Раскадровка", 1)[1]
    t, out, k = 0.0, [], 1
    for head, body in re.findall(r"^\*\*\d+\.\d\d · ([\d,]+) с · .+?\*\*$(.*?)(?=^\*\*\d+\.\d\d · |\Z)", board, re.M | re.S):
        dur = float(head.replace(",", "."))
        lines = re.findall(r"^Реплика([^:]*): ([^:\n]+): (.+)$", body, re.M)
        for i, (note, who, text) in enumerate(lines):
            a, b = t + dur * i / len(lines), t + dur * (i + 1) / len(lines)
            who = who.strip() + (" (за кадром)" if "за кадром" in note else "")
            out.append(f"{k}\n{ts(a)} --> {ts(b - 0.05)}\n{who}: {unquote(text)}\n")
            k += 1
        t += dur
    return "\n".join(out)


if __name__ == "__main__":
    sys.stdout.write(srt(int(sys.argv[1])))
