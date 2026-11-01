#!/bin/bash
# MuJoCo 原生交互 viewer（环绕视角/Ctrl 拖拽扰动/F1 快捷键）
cd "$(dirname "$0")"
exec .venv/bin/python -m mujoco.viewer --mjcf=menagerie-so101/scene_box.xml
