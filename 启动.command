#!/bin/bash
# 小犀·网页示教台：双击启动（不依赖 node，dist 已入库）
cd "$(dirname "$0")"
exec .venv/bin/python -m xiaoxi --open
