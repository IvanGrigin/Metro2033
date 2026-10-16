#!/bin/sh
# Render stills (4 passes, every second of every shot) for the given scenes, one after another.
#   sh storyboard/3d/render_batch.sh s002 s003 ...
cd "$(dirname "$0")/../.."
for s in "$@"; do
  python3 storyboard/tools/make_scene.py storyboard/3d/scenes/$s.block.json >/dev/null 2>&1 || true
  start=$(date +%s)
  sh storyboard/3d/blender.sh -b -P storyboard/3d/run_scene.py -- storyboard/3d/scenes/$s.json storyboard/3d/out/$s --no-animatic 2>&1 \
    | grep -E "Error|Traceback" | head -3
  echo "$s done in $(( $(date +%s) - start )) s, $(ls storyboard/3d/out/$s/stills 2>/dev/null | wc -l | tr -d ' ') files"
done
