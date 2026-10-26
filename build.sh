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
  grub-efi-amd64-bin grub-pc-bin mtools dosfstools ca-certificates >/dev/null

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

echo ">> Cleaning previous build"
lb clean --purge >/dev/null 2>&1 || true

echo ">> Configuring ($DEBIAN_SUITE/$ARCH, desktop=$DESKTOP)"
lb config

echo ">> Building (30-60 min depending on mirror speed)"
lb build

ISO_OUT="${DISTRO_ID}-${DISTRO_VERSION}-${DEBIAN_SUITE}-${ARCH}.iso"
mv -f live-image-*.hybrid.iso "$ISO_OUT"
sha256sum "$ISO_OUT" > "$ISO_OUT.sha256"
echo ">> Done: $(pwd)/$ISO_OUT ($(du -h "$ISO_OUT" | cut -f1))"
