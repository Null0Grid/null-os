# Null OS

A Debian 13 (trixie) desktop for a USB stick or a disk: KDE Plasma in the Neon Lab style, the Null Grid browser, zsh with a Kali-style two-line prompt, and a network engineer's toolkit preinstalled. It's still Debian underneath, with no modified packages, so security updates come straight from Debian.

```
┌──(luc⦻null)-[~/homelab]-[main]
└─$
```
*(The real prompt uses the Null mark, a ring with two parallel slashes, from the bundled Null Mono font. Over SSH or on the text console it falls back to `@`.)*

Every design decision is in **[DESIGN.md](DESIGN.md)**. Screenshots from the latest build are on the [`screenshots` branch](../../tree/screenshots).

## What's in it

- **Desktop:** KDE Plasma 6, Windows-style taskbar, Null Lab color scheme, **NullLine** white line icons (BeautyLine recolored), Silkscreen titles and Inter text.
- **Startup and shutdown:** a glitchy Plymouth startup and a CRT power-off shutdown. Previews are in `branding/preview/`.
- **Apps:** Null Grid browser, Null File (file manager), Discover with Flathub, Konsole, VSCodium, LibreOffice, VLC, Gwenview, Okular.
- **Terminal:** zsh with autosuggestions and syntax highlighting, the two-line prompt, and Null Mono in Konsole.
- **Network toolkit:** nmap, tcpdump, Wireshark, iperf3, mtr, dnsutils, lldpd, ethtool, nftables, wireguard-tools, arp-scan, ipcalc, snmp, minicom, picocom and Remmina.
- **System:** Calamares graphical installer, firewall on (incoming blocked except SSH), Docker plus Compose, unattended security upgrades, live persistence for USB.

Live session login: `user` / `live`, with passwordless sudo. Installed systems use the account you create in the installer.

## Get the ISO

Every push to `main` builds it on GitHub Actions:

1. Open **Actions → Build Null OS → latest run**.
2. Download the **null-os-iso** artifact.

Tagging a release (`git tag v0.1 && git push --tags`) also attaches the ISO to a GitHub Release.

## Put it on a USB stick

```
sudo tools/make-usb.sh nullos-0.2-trixie-amd64.iso /dev/sdX
```
This writes the ISO and adds a `persistence` partition in the leftover space. A plain `dd` or balenaEtcher also works, but without persistence.

## Build it yourself

| Host | Command |
|---|---|
| Debian 12/13 | `sudo ./build.sh` |
| Any Linux with Docker | `./docker-build.sh` |

A build takes 30–60 minutes and needs about 15 GB of free disk.

## Testing

Every build boots the ISO in a QEMU VM on GitHub Actions and publishes screenshots to the `screenshots` branch (`tools/vm-screenshots.py`). To re-test an existing ISO without rebuilding, run **Actions → Screenshots only** with the build's run ID. Set `debug` to `1` for a root debug shell and diagnostics shots.

## Customize

| Want to change | Edit |
|---|---|
| Name, version, Debian release, desktop on/off | `null-os.conf` |
| Packages | `config/package-lists/*.list.chroot`, `config/package-lists-optional/desktop.list.chroot` |
| Prompt and shell | `config/includes.chroot/etc/skel/.zshrc` |
| Terminal colors and font | `config/includes.chroot/usr/share/konsole/` (NullOS.profile, NullLab.colorscheme) |
| Desktop defaults | `config/includes.chroot/etc/xdg/kdeglobals`, `usr/share/color-schemes/NullLab.colors` |
| Startup and shutdown animation | `python3 tools/make-plymouth.py` |
| Icons | `tools/make-icons.py` (run at build time by `tools/fetch-assets.sh`) |
| The Null mark | `config/includes.chroot/usr/share/null-os/null-mark.py` (single source for the font glyph and all images) |
| Wallpaper, logo, GRUB image | `python3 tools/make-branding.py` (needs `pip install cairosvg`) |
| Build-time scripts | `config/hooks/live/` |

## How the Null mark works

The mark is defined once, as geometry, in `null-mark.py`. At image build time `patch-font.py` adds it to JetBrains Mono at the private-use code point **U+E900** and renames the result **Null Mono**. The prompt prints `` in local graphical terminals and `@` elsewhere. Force either with `NULL_GLYPH=1` or `NULL_GLYPH=0` in `~/.zshrc`.

## Roadmap

- [x] First successful CI build and screenshot review
- [x] Plymouth startup and shutdown animations
- [ ] Custom GTK/xfwm4 theme (currently Adwaita-dark with accent overrides)
- [ ] Null apps (Null Search, Null Notes) as optional packages
- [ ] Own signed apt repo for Null OS packages

## Gamer Mode (optional)

NULL // PLAY isn't preinstalled. After installing Null OS, download `null-play_<version>_amd64.deb` from the [null-play releases](https://github.com/Null0Grid/null-play/releases) and run `sudo apt install ./null-play_*_amd64.deb`. Null OS asks whether to put it on the desktop.
