#!/usr/bin/env bash
# Free CC0 assets (no credit needed, OK for monetised videos):
#   Poly Haven sky photos (HDRIs) for soft realistic lighting  - polyhaven.com
#   Kenney toy-style 3D kits (food, nature, furniture, holiday, toy cars, space, pirate, pets) - kenney.nl
# Usage: bash pipeline/get_assets.sh [folder]   (the workflows cache the folder between runs)
set -u
A=${1:-assets}
mkdir -p "$A/hdri" "$A/kenney"
for id in farm_field_puresky citrus_orchard_puresky autumn_field_puresky belfast_sunset_puresky brown_photostudio_02; do
  f="$A/hdri/$id.hdr"
  [ -s "$f" ] || curl -fsSL "https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/${id}_1k.hdr" -o "$f" || rm -f "$f"
done
get() {
  [ -d "$A/kenney/$1" ] && return 0
  if curl -fsSL "$2" -o "/tmp/k_$1.zip"; then
    mkdir -p "$A/kenney/$1" && python3 -m zipfile -e "/tmp/k_$1.zip" "$A/kenney/$1"
    rm -f "/tmp/k_$1.zip"
  else
    echo "kenney $1 unavailable"
  fi
}
get food "https://kenney.nl/media/pages/assets/food-kit/83086fa91c-1719418518/kenney_food-kit.zip"
get nature "https://kenney.nl/media/pages/assets/nature-kit/37ac38a37b-1677698939/kenney_nature-kit.zip"
get furniture "https://kenney.nl/media/pages/assets/furniture-kit/440e0608a4-1677580847/kenney_furniture-kit.zip"
get holiday "https://kenney.nl/media/pages/assets/holiday-kit/3976a6496a-1733923970/kenney_holiday-kit.zip"
get toycar "https://kenney.nl/media/pages/assets/toy-car-kit/42e19cc426-1736346027/kenney_toy-car-kit.zip"
get space "https://kenney.nl/media/pages/assets/space-kit/20874c75ac-1677698978/kenney_space-kit.zip"
get pirate "https://kenney.nl/media/pages/assets/pirate-kit/e6d4bb1525-1771333093/kenney_pirate-kit.zip"
get pets "https://kenney.nl/media/pages/assets/cube-pets/44e58e945f-1774520254/kenney_cube-pets_1.0.zip"
echo "assets: $(ls "$A/hdri" | wc -l) skies, $(find "$A/kenney" -name '*.glb' | wc -l) models"
