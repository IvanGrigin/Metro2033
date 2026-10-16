"""Contact sheet of a scene's --preview frames: python3 preview_sheet.py PREVIEW_DIR OUT.png"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
# shot frames only ("1.02.png" or the lit pass "1.02_lit.png"); depth maps are skipped
files = sorted((p for p in Path(sys.argv[1]).glob("*.png") if "_depth" not in p.stem),
               key=lambda p: [int(x) for x in p.stem.split("_")[0].split(".")])
W, H, cols = 320, 180, 6
sheet = Image.new("RGB", (W * cols, H * ((len(files) + cols - 1) // cols)))
for i, f in enumerate(files):
    im = Image.open(f).convert("RGB").resize((W, H))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 44, 16], fill=(0, 0, 0))
    d.text((4, 3), f.stem, fill=(255, 255, 255))
    sheet.paste(im, ((i % cols) * W, (i // cols) * H))
sheet.save(sys.argv[2])
