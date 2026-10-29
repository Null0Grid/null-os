# Null OS — Design

The decisions behind Null OS 1.2.1. Change this file first, then the build.

## Identity

| | |
|---|---|
| Name | **Null OS**, part of the Null Grid family |
| Base | Debian 13 "trixie" (stable), stock Debian kernel |
| Target | Daily-driver desktop that runs well from a USB stick (live + persistence), installable to disk |
| Look | **Neon Lab**: near-black `#0a0a0f`, cyan `#00e5ff` primary neon, pink `#ff2e88` secondary, lab green `#3dff7a`, amber/red for alerts only |
| Neon rule | Neon only where it means something. Everything is quiet white or grey at rest; cyan marks what's live, hovered or selected |
| Theme | Dark only (no light mode), like the other Null Grid apps |

## The Null mark

A ring crossed by two parallel slashes (echoes the Null Grid `//` family mark).

- Defined once as geometry in `config/includes.chroot/usr/share/null-os/null-mark.py`
- Patched into **Null Mono** (JetBrains Mono) at **U+E900** at build time
- Used in: the shell prompt, wallpaper, login avatar, boot menu, Plymouth startup and shutdown

## Desktop

| Area | Choice |
|---|---|
| Desktop | **KDE Plasma 6** |
| Layout | **Windows style**: bottom taskbar with start menu (Kickoff, Null mark button), tray, clock |
| Window theme | Breeze, with a custom **Null Lab** color scheme (cyan selection and hover) |
| Icons | **NullLine**: BeautyLine (GPL) recolored to pure white line icons; hover and selection glow cyan |
| Fonts | **Silkscreen** for titles (window titles, login, splash), **VT323** for accents, **Inter** for body text, **Null Mono** for terminals and code. Silkscreen and VT323 match the Null Grid browser |
| Login | SDDM with the Null OS background |
| Startup | Plymouth: static burst, RGB split (cyan/pink), tear lines, sliced half-render, mark snaps in, "NULL OS" flickers pink/cyan, cyan loading bar |
| Shutdown | Plymouth: short glitch, then CRT collapse to a white line and a dot. "powering down // see you on the grid" |
| Boot menu (ISO) | Null OS splash instead of the Debian helmet |

## Terminal and shell

| | |
|---|---|
| Terminal | **Konsole** with a Null Lab color scheme and Null Mono; **fastfetch** with the Null mark logo and a Base line showing Debian |
| Shell | **zsh** for every user, autosuggestions and syntax highlighting |
| Prompt | Kali-style two lines: `┌──(user<mark>host)-[path]-[branch]-[✗ code]` / `└─$` |
| Fallback | `@` instead of the mark over SSH or on the text console |
| Root | Frame turns red, prompt char `#` |

## Apps

| Role | App |
|---|---|
| Web browser | **Null Grid** (NODE_GRID), latest `.deb` from Null0Grid/node-grid releases; Null Search default |
| App store | **Discover** with Flathub enabled |
| File manager | **Null File** (Null Grid app, Tauri), latest `.deb` from Null0Grid/null-file releases; default for folders; updates through its signed apt repo |
| Gamer Mode | **NULL // PLAY**, not on the ISO; part of **Full** (latest .deb from Null0Grid/null-play releases). Its package brings its own entry points |
| Code editor | **VSCodium** (VS Code without Microsoft branding or telemetry; bundling Microsoft's build isn't allowed by its license) |
| Office | Not preinstalled (keeps the ISO under 2 GB); part of **Full** |
| Media | **VLC** |
| Images / PDF | Gwenview, Okular |
| Network toolkit | nmap, tcpdump, Wireshark, iperf3, mtr, dnsutils, lldpd, ethtool, nftables, wireguard-tools, arp-scan, ipcalc, snmp, minicom, picocom, Remmina |
| Containers | Not preinstalled; part of **Full** (Docker, Compose, Podman) |
| Minimal / Full | Like Ubuntu. **Minimal** (the default) is the Null OS desktop only: Plasma, Konsole, Null Grid, Null File, Ark, Spectacle, the zsh prompt and fastfetch. **Full** is ticked on the installer's **Apps** page (Calamares netinstall, downloads during install so the ISO stays small) or added later with **Null OS Extras** (`null-extras`), also in the live session. Full groups: Desktop apps (VLC, Gwenview, Okular), Discover + Flathub, VSCodium, Remote desktop (Remmina RDP/VNC), Network toolkit (Wireshark, nmap, tcpdump, mtr, iperf3, WireGuard...), Firewall (ufw), Office (LibreOffice), Docker + Podman, QEMU/KVM, VirtualBox 7.2, VS Code, Claude (Claude Desktop + Claude Code), NULL // PLAY, Homelab (Ansible, kubectl, Terraform), Programming (build tools, Python, Node.js, Go, Rust, Java, gh). One script defines the groups for both |
| Null apps | Browser only for now (Notes, Drive, Scribe later) |
| Desktop shortcuts | `null-shortcuts` asks "Add to desktop?" when a new app is installed (apt, Flatpak, Steam games); **Null OS Settings** picks Original or NullLine icons and turns the prompt on or off |

## System

| | |
|---|---|
| Installer | **Calamares** (graphical), Null OS branding |
| Firewall | **On**: block incoming except SSH, allow outgoing (ufw, plasma-firewall for the GUI) |
| SSH | Installed, root login disabled |
| Updates | Unattended security upgrades |
| USB | Live persistence (`tools/make-usb.sh` adds the partition) |
| Live session | User `user` / `live`, auto-login straight into Plasma |

## Status (1.2.1, verified in a VM on every build)

Working: Null OS boot menu, glitch startup animation, live auto-login into
Plasma, Null OS wallpaper / colors / NullLine icons / Silkscreen titles,
Null Grid browser as the default, Konsole two-line prompt with the Null
mark, `@` fallback on the console, red root prompt, "Install Null OS"
launcher, Null OS login screen and logo, `null-info` reports Null OS.

Known issues:
- **Shutdown animation freezes on its first frame during a real shutdown
  in the VM.** Run by hand it plays fully (glitch, CRT collapse), so the
  theme works; the freeze looks like the VM's graphics handoff at power-off.
  Needs a test on real hardware.
- Calamares installer and the firewall's first-boot setup aren't exercised by
  the VM test yet.

## Open

- Optional startup/shutdown sounds
- Null Notes, Drive and Scribe as preinstalled apps
- Fully custom SDDM theme and Calamares slideshow
- [done in 0.2] Start-menu button shows the Null mark
- Own signed apt repo for Null OS packages
