# Debian Remix

A Debian 13 (trixie) remix built with `live-build`. It produces one hybrid ISO that boots as a live system and also contains the Debian installer. It stays 100% compatible with Debian: no packages are modified, so security updates come straight from Debian.

## What's in it

- **Base:** Debian trixie, amd64, `main contrib non-free non-free-firmware`, firmware and microcode for real hardware
- **Network toolkit:** nmap, tcpdump, tshark, iperf3, mtr, dnsutils, lldpd, ethtool, nftables, wireguard-tools, arp-scan, ipcalc, snmp, minicom and picocom for console cables
- **Ops:** Docker plus Compose, SSH (root login disabled), chrony, unattended security upgrades, tmux, btop, smartmontools
- **Branding:** custom `os-release` (diverted so upgrades don't overwrite it), login banner, MOTD, and a `remix-info` command
- **Installer:** a text-mode Debian installer with a partial preseed. Locale, timezone and repos are pre-answered, but **disk partitioning is always manual**.
- **Optional:** set `DESKTOP="1"` for XFCE, Firefox, Wireshark and Remmina

Live session login: `user` / `live`. Don't boot the live image on an untrusted network with SSH up. Installed systems use the user you create in the installer.

## Customize

| Want to change | Edit |
|---|---|
| Name, version, Debian release, desktop on/off | `remix.conf` |
| Packages | `config/package-lists/*.list.chroot` |
| Files baked into the system | `config/includes.chroot/` (mirrors `/`) |
| Build-time scripts | `config/hooks/live/*.hook.chroot` |
| Installer answers | `config/includes.installer/preseed.cfg` |

## Build

Pick one option.

**1. Debian host (fastest)**
```
sudo ./build.sh
```

**2. Any Linux box with Docker** (Ubuntu, Proxmox host, WSL2)
```
./docker-build.sh
```

**3. GitHub Actions (no local machine needed)**
Push this folder to a GitHub repo. Every push to `main` builds the ISO and attaches it as a workflow artifact. Pushing a tag like `v0.1` also publishes it as a GitHub Release.

Expect a build to take 20–60 minutes and need about 10 GB of free disk. The ISO is about 1.2 GB for the server build and about 2 GB with the desktop. The output is `remix-0.1-trixie-amd64.iso` plus a `.sha256` file.

## Test

```
qemu-system-x86_64 -enable-kvm -m 4096 -cdrom remix-0.1-trixie-amd64.iso
# UEFI:
qemu-system-x86_64 -enable-kvm -m 4096 -bios /usr/share/ovmf/OVMF.fd -cdrom remix-*.iso
```
Or upload it to Proxmox as an ISO image and boot a VM from it. To write it to USB, use `dd if=remix-*.iso of=/dev/sdX bs=4M status=progress conv=fsync`.

## Troubleshooting

- **"Unable to locate package X"**: a package name changed between Debian releases. Remove it from the list, or look it up on packages.debian.org.
- **Build fails mid-way**: run `sudo lb clean --purge` and then rebuild. `build.log` has the full output.
- **Docker build fails on mounts**: the container needs `--privileged`, which `docker-build.sh` already passes.

## Next steps toward a real derivative

1. Move customizations into your own `.deb` packages, such as `remix-branding` and `remix-netops` metapackages.
2. Host them in your own apt repo using `aptly` or `reprepro`, signed with your GPG key.
3. Add the repo to the image so installed systems get your updates through `apt upgrade`.
