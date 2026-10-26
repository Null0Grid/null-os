#!/bin/bash
# Write Null OS to a USB stick and add a persistence partition, so files,
# settings and installed packages survive reboots.
#
# Usage: sudo tools/make-usb.sh nullos-0.1-trixie-amd64.iso /dev/sdX
# WARNING: erases everything on the target device.
set -euo pipefail
ISO=${1:?usage: make-usb.sh <iso> <device>}
DEV=${2:?usage: make-usb.sh <iso> <device>}
[ "$(id -u)" -eq 0 ] || { echo "Run as root"; exit 1; }
[ -b "$DEV" ] || { echo "$DEV is not a block device"; exit 1; }
case "$DEV" in *[0-9]) echo "Give the whole disk (e.g. /dev/sdb), not a partition"; exit 1;; esac

lsblk -o NAME,SIZE,MODEL,MOUNTPOINTS "$DEV"
read -r -p "ERASE everything on $DEV? Type YES to continue: " ok
[ "$ok" = YES ] || { echo "Aborted"; exit 1; }

umount "${DEV}"?* 2>/dev/null || true
echo ">> Writing ISO"
dd if="$ISO" of="$DEV" bs=4M status=progress conv=fsync

echo ">> Adding persistence partition in the free space"
echo ',,L' | sfdisk --append --no-reread "$DEV"
partprobe "$DEV"; sleep 2
PART=$(lsblk -lnpo NAME "$DEV" | tail -1)
mkfs.ext4 -q -F -L persistence "$PART"
MNT=$(mktemp -d)
mount "$PART" "$MNT"
echo "/ union" > "$MNT/persistence.conf"
umount "$MNT"; rmdir "$MNT"
sync
echo ">> Done. Boot from $DEV; changes now persist across reboots."
