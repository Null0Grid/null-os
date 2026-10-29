**Null OS 1.2.0: Minimal or Full.** Debian 13 (trixie), KDE Plasma 6, Neon Lab.

## New
- **Minimal or Full, like Ubuntu.** The installer has a new **Apps** page. Leave **Null OS Full** unticked for Minimal (just the Null OS desktop), tick it for everything, or tick only the parts you want. Full downloads during install, so it needs internet.
- **Null OS Extras** app (start menu): add any part of Full later, with progress and a summary. Also works in the live session. Terminal: `null-extras list`, `null-extras install <group>`.
- **Full groups:** Desktop apps (VLC, Gwenview, Okular), Discover + Flathub, VSCodium, Remote desktop (Remmina RDP/VNC), Network toolkit (Wireshark, nmap, tcpdump, mtr, iperf3, WireGuard...), Firewall (ufw), Office (LibreOffice), Docker + Podman, QEMU/KVM + virt-manager, VirtualBox 7.2, VS Code, Claude (Claude Desktop + Claude Code), NULL // PLAY, Homelab (Ansible, kubectl, Terraform), Programming (build tools, Python, Node.js, Go, Rust, Java, GitHub CLI).
- **Packet** on the installer's finished page.
- Installer password check fixed (missing dictionary); optional "accept weak password".
- No automatic screen lock in the live session. Live login: user `user`, password `live`.

## Changed
- Minimal ships without the apps above, the network toolkit and the firewall; the ISO is 1.76 GB.
- Taskbar pins: Settings, Null File, Null Grid, Konsole.

## VirtualBox
Linux / Debian (64-bit), 4 GB RAM, 2+ CPUs, Graphics **VBoxSVGA**, 128 MB video memory, 3D off, 25 GB disk for the installer.
