#!/bin/zsh
cd -- "${0:A:h}" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  print "未找到 Python 3。请先安装 Python 3，或直接打开当前目录的 local.html。"
  exit 1
fi
exec python3 scripts/launch_studio.py "$@"
