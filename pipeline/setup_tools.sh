#!/usr/bin/env bash
# Installs the tools a job needs - fast, and never stuck for long. Ubuntu's package mirrors are sometimes very slow
# (a plain "apt-get update && apt-get install" once took 33 minutes), so:
#   - Blender's system libraries are only installed if Blender can't start without them
#   - ffmpeg comes from pip (imageio-ffmpeg, a ready-made static build), no apt at all
#   - apt is tried without "update" first, and every apt call has a time limit
# Usage: bash pipeline/setup_tools.sh blender-libs ffmpeg fluidsynth fonts
set -u
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_SUSPEND=1 NEEDRESTART_MODE=l
APT_OPTS="-y -qq --no-install-recommends -o Acquire::Retries=2 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20"

apt_install() {
  timeout 240 sudo -E apt-get install $APT_OPTS "$@" > /dev/null 2>&1 && return 0
  echo "apt: refreshing package lists"
  timeout 240 sudo -E apt-get update -qq -o Acquire::Retries=2 -o Acquire::http::Timeout=20 > /dev/null 2>&1
  timeout 300 sudo -E apt-get install $APT_OPTS "$@" > /dev/null 2>&1
}

for want in "$@"; do
  case "$want" in
    blender-libs)
      if [ -x bl/blender ] && timeout 120 ./bl/blender -b --factory-startup --python-expr "import bpy" > /dev/null 2>&1; then
        echo "blender libs: already there"
      else
        apt_install libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libegl1 libxkbcommon0 libsm6 \
          && echo "blender libs: installed" || echo "::warning::blender libs: install failed or timed out"
      fi ;;
    ffmpeg)
      if command -v ffmpeg > /dev/null; then
        echo "ffmpeg: already there"
      else
        PY=$(command -v python || command -v python3)
        "$PY" -m pip install -q imageio-ffmpeg > /dev/null 2>&1 || "$PY" -m pip install -q --break-system-packages imageio-ffmpeg > /dev/null 2>&1
        exe=$("$PY" -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())" 2> /dev/null)
        if [ -n "$exe" ]; then
          sudo ln -sf "$exe" /usr/local/bin/ffmpeg && echo "ffmpeg: ready ($exe)"
        else
          apt_install ffmpeg && echo "ffmpeg: installed with apt" || echo "::warning::ffmpeg: not available"
        fi
      fi ;;
    fluidsynth)
      if command -v fluidsynth > /dev/null; then
        echo "fluidsynth: already there"
      else
        apt_install fluidsynth && echo "fluidsynth: installed" || echo "::warning::fluidsynth: install failed or timed out (no music)"
      fi ;;
    fonts)
      if fc-list 2> /dev/null | grep -qi dejavu; then echo "fonts: already there"; else apt_install fonts-dejavu-core; fi ;;
  esac
done
exit 0
