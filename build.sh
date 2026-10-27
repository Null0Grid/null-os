#!/bin/bash
# Build the Null OS ISO. Run as root on Debian 12/13 (or via docker-build.sh).
set -euo pipefail
cd "$(dirname "$0")"
. ./null-os.conf

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo ./build.sh)"; exit 1; }
grep -qi debian /etc/os-release || echo "WARNING: not a Debian host; use ./docker-build.sh if this fails."

echo ">> Installing build tools"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  live-build debootstrap squashfs-tools xorriso isolinux syslinux-common \
  grub-efi-amd64-bin grub-pc-bin mtools dosfstools ca-certificates \
  curl git jq python3 python3-fonttools python3-brotli >/dev/null

echo ">> Writing release info from null-os.conf"
cat > config/includes.chroot/etc/null-os-release <<REL
NULL_NAME="$DISTRO_NAME"
NULL_ID="$DISTRO_ID"
NULL_VERSION="$DISTRO_VERSION"
REL

if [ "$DESKTOP" = "1" ]; then
  cp config/package-lists-optional/desktop.list.chroot config/package-lists/desktop.list.chroot
else
  rm -f config/package-lists/desktop.list.chroot
fi

echo ">> Fetching fonts, icons, VSCodium key and the Null Grid browser"
./tools/fetch-assets.sh

echo ">> Cleaning previous build"
lb clean --purge >/dev/null 2>&1 || true

echo ">> Configuring ($DEBIAN_SUITE/$ARCH, desktop=$DESKTOP)"
lb config

echo ">> Null OS boot menu (replaces the Debian splash)"
mkdir -p config/bootloaders
for src in /usr/share/live/build/bootloaders/*/; do
  d=$(basename "$src")
  rm -rf "config/bootloaders/$d"
  cp -a "$src" "config/bootloaders/$d"
done
# live-build looks for a custom splash at the top of config/bootloaders
cp branding/boot-splash.svg config/bootloaders/splash.svg
cp branding/boot-splash.svg config/bootloaders/splash.svg.in
cp branding/boot-splash.png config/bootloaders/splash.png
# Every splash variant, whatever live-build calls it
find config/bootloaders -iname 'splash*.svg*' -exec cp branding/boot-splash.svg {} \;
find config/bootloaders -iname 'splash*.png'  -exec cp branding/boot-splash.png {} \;
# Menu highlight in Null cyan
find config/bootloaders -name 'stdmenu.cfg' -exec sed -i \
  -e 's/#76a1d0ff/#ff00e5ff/g' -e 's/^\(menu color sel \* \)#ffffffff/\1#ff0a0a0f/' {} \;
# Visible in the CI run summary, to check what got replaced
echo "::notice title=bootloader-splash::$(cd config/bootloaders && find . -iname '*splash*' | tr '\n' ' ')"
echo "::notice title=bootloader-dirs::$(ls config/bootloaders | tr '\n' ' ')"
echo "::notice title=splash-files::$(find /usr/share/live /usr/lib/live -iname '*splash*' 2>/dev/null | tr '\n' ' ')"
grep -rn "splash" /usr/lib/live/build/binary_syslinux 2>/dev/null | head -6 | while IFS= read -r l; do echo "::notice title=binary_syslinux::${l:0:400}"; done || true

echo ">> Building (30-60 min depending on mirror speed)"
lb build

ISO_OUT="${DISTRO_ID}-${DISTRO_VERSION}-${DEBIAN_SUITE}-${ARCH}.iso"
mv -f live-image-*.hybrid.iso "$ISO_OUT"
sha256sum "$ISO_OUT" > "$ISO_OUT.sha256"
echo ">> Done: $(pwd)/$ISO_OUT ($(du -h "$ISO_OUT" | cut -f1))"
