#!/bin/bash
cd "$(dirname "$0")"
exec .venv/bin/python -m mujoco.viewer --mjcf=menagerie-so101/scene_box.xml
