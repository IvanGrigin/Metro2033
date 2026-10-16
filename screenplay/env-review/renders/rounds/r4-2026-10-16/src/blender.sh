#!/bin/sh
# Gentle Blender: one at a time across all agents (lock), utility QoS (may use both performance and efficiency cores,
# yields to interactive apps), low CPU priority, 4 render threads — the Mac stays responsive while scenes build and render.
#   sh storyboard/3d/blender.sh -b -P storyboard/3d/run_scene.py -- scene.json OUT --preview
# A crashed run can leave the lock behind: remove /tmp/metro_blender.lock if nothing is running.
LOCK=/tmp/metro_blender.lock
while ! mkdir "$LOCK" 2>/dev/null; do sleep 3; done
trap 'rmdir "$LOCK"' EXIT INT TERM
nice -n 10 taskpolicy -c utility /Applications/Blender.app/Contents/MacOS/Blender -t 4 "$@"
