# Null OS

A Debian 13 (trixie) remix built for a USB stick: a light XFCE desktop in the Neon Lab style, zsh with a Kali-style two-line prompt, and a network engineer's toolkit preinstalled. It's still 100% Debian underneath, with no modified packages, so security updates come straight from Debian.

```
┌──(luc⦻null)-[~/homelab]-[main]
└─$
```
*(The real prompt uses the Null mark, a ring with two parallel slashes, from the bundled Null Mono font. Over SSH or on the text console it falls back to `@`.)*

Screenshots from the latest build are on the [`screenshots` branch](../../tree/screenshots).

## What's in it

- **Desktop:** XFCE with Adwaita-dark, Papirus icons and Neon Lab accents. It includes Firefox ESR, Thunar, Wireshark, Remmina and NetworkManager.
- **Terminal:** zsh by default with autosuggestions and syntax highlighting. The xfce4-terminal uses the Neon Lab palette and the **Null Mono** font.
- **Prompt:** `┌──(user<mark>host)-[path]-[git branch]-[✗ exit code]` / `└─$`. The frame turns red as root.
- **Network toolkit:** nmap, tcpdump, tshark, iperf3, mtr, dnsutils, lldpd, ethtool, nftables, wireguard-tools, arp-scan, ipcalc, snmp, minicom and picocom.
- **Ops:** Docker plus Compose, SSH (root login disabled), chrony and unattended security upgrades.
- **USB-first:** live boot with **persistence**, so your files and settings survive reboots. The Debian installer is included if you want it on disk.
- **Branding:** wallpaper, login screen, GRUB background, `os-release` and `null-info`.

Live session login: `user` / `live`, with passwordless sudo. Installed systems use the account you create in the installer.

## Get the ISO

Every push to `main` builds it on GitHub Actions:

1. Open **Actions → Build Null OS → latest run**.
2. Download the **null-os-iso** artifact.

Tagging a release (`git tag v0.1 && git push --tags`) also attaches the ISO to a GitHub Release.

## Put it on a USB stick

```
sudo tools/make-usb.sh nullos-0.1-trixie-amd64.iso /dev/sdX
```
This writes the ISO and adds a `persistence` partition in the leftover space. A plain `dd` or balenaEtcher also works, but without persistence.

## Build it yourself

| Host | Command |
|---|---|
| Debian 12/13 | `sudo ./build.sh` |
| Any Linux with Docker | `./docker-build.sh` |

A build takes 30–60 minutes and needs about 15 GB of free disk.

## Customize

| Want to change | Edit |
|---|---|
| Name, version, Debian release, desktop on/off | `null-os.conf` |
| Packages | `config/package-lists/*.list.chroot`, `config/package-lists-optional/desktop.list.chroot` |
| Prompt and shell | `config/includes.chroot/etc/skel/.zshrc` |
| Terminal colors and font | `config/includes.chroot/etc/skel/.config/xfce4/terminal/terminalrc` |
| Desktop defaults | `config/includes.chroot/etc/xdg/xfce4/xfconf/` |
| The Null mark | `config/includes.chroot/usr/share/null-os/null-mark.py` (single source for the font glyph and all images) |
| Wallpaper, logo, GRUB image | `python3 tools/make-branding.py` (needs `pip install cairosvg`) |
| Build-time scripts | `config/hooks/live/` |

## How the Null mark works

The mark is defined once, as geometry, in `null-mark.py`. At image build time `patch-font.py` adds it to JetBrains Mono at the private-use code point **U+E900** and renames the result **Null Mono**. The prompt prints `` in local graphical terminals and `@` elsewhere. Force either with `NULL_GLYPH=1` or `NULL_GLYPH=0` in `~/.zshrc`.

## Roadmap

- [ ] First successful CI build and screenshot review
- [ ] Plymouth boot splash with the mark
- [ ] Custom GTK/xfwm4 theme (currently Adwaita-dark with accent overrides)
- [ ] Null apps (Null Search, Null Notes) as optional packages
- [ ] Own signed apt repo for Null OS packages
