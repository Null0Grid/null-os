**Null OS 1.2.1: installing works.** Debian 13 (trixie), KDE Plasma 6, Neon Lab.

Use this instead of 1.2.0: on 1.2.0 and earlier, installing to a disk failed at the copy step ("Failed to find unsquashfs"). Trying Null OS live from the USB was fine.

## Fixed
- **Installing to a disk.** The installer now has the tools it needs: squashfs-tools (copies the system) and GRUB for BIOS and UEFI (Debian's installer fetches GRUB from a package pool on Debian's own ISO, which Null OS doesn't have). Encrypted installs get their initramfs support too. Tested end to end in a VM: install, reboot, log in.
- Installed systems boot with the Null OS splash and show "Null OS" in the boot menu.
- The installer's logo, welcome picture and slideshow are Null OS, not Debian.

## Everything from 1.2.0
- **Minimal or Full, like Ubuntu:** the installer's **Apps** page. Minimal is just the Null OS desktop; tick **Null OS Full** (or parts of it) to download apps during install. **Null OS Extras** in the start menu adds them later.
- Full: Desktop apps (VLC, Gwenview, Okular), Discover + Flathub, VSCodium, Remote desktop (Remmina RDP/VNC), Network toolkit (Wireshark, nmap, tcpdump, mtr, iperf3, WireGuard...), Firewall (ufw), Office (LibreOffice), Docker + Podman, QEMU/KVM + virt-manager, VirtualBox 7.2, VS Code, Claude (Claude Desktop + Claude Code), NULL // PLAY, Homelab (Ansible, kubectl, Terraform), Programming (build tools, Python, Node.js, Go, Rust, Java, GitHub CLI).
- **Packet** on the installer's finished page.

## Known
- Secure Boot isn't supported yet: turn it off in the firmware settings to install on a PC.

## VirtualBox
Linux / Debian (64-bit), 4 GB RAM, 2+ CPUs, Graphics **VBoxSVGA**, 128 MB video memory, 3D off, 25 GB disk. Live login: user `user`, password `live`.
