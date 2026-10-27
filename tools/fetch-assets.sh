#!/bin/bash
# Download third-party assets at build time and stage them into the image.
# Called by build.sh. Needs: curl, git, python3, jq.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
INC=config/includes.chroot
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

fetch() { curl -fsSL --retry 3 --max-time 120 "$@"; }

echo ">> Fonts: Silkscreen and VT323 (OFL, same as the Null Grid browser)"
FONTS=$INC/usr/share/fonts/truetype/null-os-ui
mkdir -p "$FONTS"
G=https://raw.githubusercontent.com/google/fonts/main/ofl
fetch -o "$FONTS/Silkscreen-Regular.ttf" "$G/silkscreen/Silkscreen-Regular.ttf"
fetch -o "$FONTS/Silkscreen-Bold.ttf"    "$G/silkscreen/Silkscreen-Bold.ttf"
fetch -o "$FONTS/OFL-Silkscreen.txt"     "$G/silkscreen/OFL.txt"
fetch -o "$FONTS/VT323-Regular.ttf"      "$G/vt323/VT323-Regular.ttf"
fetch -o "$FONTS/OFL-VT323.txt"          "$G/vt323/OFL.txt"

echo ">> Icons: NullLine (BeautyLine, GPL, recolored white)"
git clone -q --depth 1 https://gitlab.com/garuda-linux/themes-and-settings/artwork/beautyline.git "$WORK/bl" \
  || git clone -q --depth 1 https://github.com/gvolpe/BeautyLine "$WORK/bl"
BL=$(find "$WORK/bl" -maxdepth 2 -name index.theme -path '*BeautyLine/index.theme' -printf '%h\n' | head -1)
[ -n "$BL" ] || BL=$(dirname "$(find "$WORK/bl" -maxdepth 2 -name index.theme | head -1)")
python3 tools/make-icons.py "$BL" "$INC/usr/share/icons/NullLine"
cp "$WORK/bl/LICENSE"* "$INC/usr/share/icons/NullLine/" 2>/dev/null || true

echo ">> VSCodium apt repo key"
mkdir -p config/archives
fetch -o config/archives/vscodium.key.chroot \
  https://gitlab.com/paulcarroll/vscodium-deb-rpm-repo/raw/master/pub.gpg
cp config/archives/vscodium.key.chroot config/archives/vscodium.key.binary
echo "deb https://download.vscodium.com/debs vscodium main" > config/archives/vscodium.list.chroot
cp config/archives/vscodium.list.chroot config/archives/vscodium.list.binary

echo ">> Null Grid browser: latest release .deb"
mkdir -p config/packages.chroot
rm -f config/packages.chroot/null-grid*.deb config/packages.chroot/node-grid*.deb
URL=$(fetch https://api.github.com/repos/Null0Grid/node-grid/releases/latest \
  | jq -r '.assets[] | select(.name | test("(amd64|x86_64).*\\.deb$")) | .browser_download_url' | head -1)
if [ -n "$URL" ]; then
  fetch -o "config/packages.chroot/$(basename "$URL")" "$URL"
  echo "   $(basename "$URL")"
else
  echo "   WARNING: no amd64 .deb found in the latest node-grid release; building without it"
fi
