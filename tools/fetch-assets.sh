#!/bin/bash
# Download third-party assets at build time and stage them into the image.
# Called by build.sh. Needs: curl, git, jq, python3, python3-fonttools, python3-brotli.
# Required assets (fonts, icons) fail the build; optional ones warn and skip.
set -euo pipefail
cd "$(dirname "$0")/.."
INC=config/includes.chroot
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# fetch OUT URL [URL...] : try each URL until one works
fetch() {
  local out=$1; shift
  for url in "$@"; do
    echo "   GET $url"
    if curl -fsSL --retry 3 --max-time 120 -o "$out" "$url"; then return 0; fi
    echo "   (failed)"
  done
  return 1
}

echo ">> Fonts: Silkscreen and VT323 (the Null Grid browser's own files, OFL)"
FONTS=$INC/usr/share/fonts/truetype/null-os-ui
mkdir -p "$FONTS"
git clone -q --depth 1 https://github.com/Null0Grid/node-grid "$WORK/ng"
python3 - "$WORK/ng/fonts" "$FONTS" <<'PY'
import sys, os
from fontTools.ttLib import TTFont
src, dst = sys.argv[1], sys.argv[2]
for name, out in (("silkscreen.woff2", "Silkscreen-Regular.ttf"), ("vt323.woff2", "VT323-Regular.ttf")):
    f = TTFont(os.path.join(src, name)); f.flavor = None
    f.save(os.path.join(dst, out)); print("   ", out)
PY

echo ">> Icons: NullLine (BeautyLine, GPL, recolored white)"
git clone -q --depth 1 https://gitlab.com/garuda-linux/themes-and-settings/artwork/beautyline.git "$WORK/bl" \
  || git clone -q --depth 1 https://github.com/gvolpe/BeautyLine "$WORK/bl"
BL=$(dirname "$(find "$WORK/bl" -maxdepth 3 -name index.theme -path '*BeautyLine/index.theme' | head -1)")
[ -f "$BL/index.theme" ] || BL=$(dirname "$(find "$WORK/bl" -maxdepth 2 -name index.theme | head -1)")
python3 tools/make-icons.py "$BL" "$INC/usr/share/icons/NullLine"
cp "$WORK/bl/LICENSE"* "$INC/usr/share/icons/NullLine/" 2>/dev/null || true

echo ">> VSCodium apt repo (optional)"
mkdir -p config/archives
rm -f config/archives/vscodium.*
if fetch "$WORK/vscodium.gpg" \
    https://gitlab.com/paulcarroll/vscodium-deb-rpm-repo/raw/master/pub.gpg \
    https://gitlab.com/paulcarroll/vscodium-deb-rpm-repo/-/raw/master/pub.gpg; then
  cp "$WORK/vscodium.gpg" config/archives/vscodium.key.chroot
  cp "$WORK/vscodium.gpg" config/archives/vscodium.key.binary
  echo "deb https://download.vscodium.com/debs vscodium main" > config/archives/vscodium.list.chroot
  cp config/archives/vscodium.list.chroot config/archives/vscodium.list.binary
else
  echo "   WARNING: VSCodium repo key unavailable; building without VSCodium"
  sed -i '/^codium$/d' config/package-lists/desktop.list.chroot 2>/dev/null || true
fi

echo ">> Null Grid browser: latest release .deb (optional)"
mkdir -p config/packages.chroot
rm -f config/packages.chroot/*.deb
if fetch "$WORK/rel.json" https://api.github.com/repos/Null0Grid/node-grid/releases/latest; then
  URL=$(jq -r '.assets[] | select(.name | test("(amd64|x86_64).*\\.deb$")) | .browser_download_url' "$WORK/rel.json" | head -1)
  if [ -n "$URL" ] && fetch "config/packages.chroot/$(basename "$URL")" "$URL"; then
    echo "   $(basename "$URL")"
  else
    echo "   WARNING: no amd64 .deb in the latest node-grid release; building without it"
  fi
else
  echo "   WARNING: GitHub API unavailable; building without the Null Grid browser"
fi
