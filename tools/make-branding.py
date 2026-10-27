#!/usr/bin/env python3
"""Generate Null OS branding images from the mark geometry.

Writes:
  branding/null-mark.svg                                   logo source
  config/includes.chroot/usr/share/null-os/null-mark-256.png
  config/includes.chroot/usr/share/backgrounds/null-os/wallpaper.svg/.png
  config/includes.chroot/usr/share/backgrounds/null-os/grub.png

Requires: pip install cairosvg
Run from the repo root: python3 tools/make-branding.py
"""
import importlib.util
import os
import random

import cairosvg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "null_mark", os.path.join(ROOT, "config/includes.chroot/usr/share/null-os/null-mark.py"))
mark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mark)

# Neon Lab palette
BG = "#0a0a0f"
BG2 = "#121821"
GRID = "#1c2633"
CYAN = "#00e5ff"
PINK = "#ff2e88"
GREEN = "#3dff7a"
TEXT = "#c9d4e3"
DIM = "#4a5a70"

# Mark in a 600x720 box (y flipped for SVG). Glyph spans y ~ 30..690.
MARK_BOX_H = 720
MARK_PATH = mark.svg_path(flip_height=MARK_BOX_H)


def out(*parts):
    p = os.path.join(ROOT, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def mark_group(x, y, size, color, glow=None):
    """The mark scaled so its 600-unit width becomes `size` px, top-left at x,y."""
    s = size / mark.CELL_W
    g = ""
    if glow:
        g += (f'<g transform="translate({x},{y}) scale({s})" filter="url(#glow)" opacity="0.85">'
              f'<path d="{MARK_PATH}" fill="{glow}" fill-rule="nonzero"/></g>')
    g += (f'<g transform="translate({x},{y}) scale({s})">'
          f'<path d="{MARK_PATH}" fill="{color}" fill-rule="nonzero"/></g>')
    return g


def logo_svg():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 720" width="600" height="720">'
            f'<path d="{MARK_PATH}" fill="{CYAN}" fill-rule="nonzero"/></svg>')


def avatar_svg():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">'
            f'<rect width="256" height="256" rx="40" fill="{BG}"/>'
            f'<rect x="4" y="4" width="248" height="248" rx="36" fill="none" stroke="{GRID}" stroke-width="2"/>'
            + mark_group(48, 28, 160, CYAN) + '</svg>')


def defs():
    return f'''<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{BG}"/><stop offset="1" stop-color="{BG2}"/>
  </linearGradient>
  <radialGradient id="halo" cx="0.5" cy="0.45" r="0.35">
    <stop offset="0" stop-color="{CYAN}" stop-opacity="0.10"/>
    <stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
  </radialGradient>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="18"/>
  </filter>
</defs>'''


def rain(w, h, n, seed):
    rnd = random.Random(seed)
    lines = []
    for _ in range(n):
        x = rnd.uniform(0, w)
        y = rnd.uniform(-h * 0.1, h)
        L = rnd.uniform(30, 140)
        op = rnd.uniform(0.05, 0.22)
        col = CYAN if rnd.random() < 0.85 else PINK
        lines.append(f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x - L * 0.08:.0f}" y2="{y + L:.0f}" '
                     f'stroke="{col}" stroke-opacity="{op:.2f}" stroke-width="1.5"/>')
    return "".join(lines)


def floor_grid(w, h, horizon):
    """Perspective grid on the lower part, like a wet neon street."""
    g = []
    cx = w / 2
    for i in range(-14, 15):
        x2 = cx + i * w / 9
        g.append(f'<line x1="{cx:.0f}" y1="{horizon}" x2="{x2:.0f}" y2="{h}" stroke="{GRID}" stroke-width="1.5"/>')
    y = horizon
    step = 6
    while y < h:
        g.append(f'<line x1="0" y1="{y:.0f}" x2="{w}" y2="{y:.0f}" stroke="{GRID}" stroke-width="1.5"/>')
        y += step
        step *= 1.35
    return "".join(g)


def wallpaper_svg(w=1920, h=1080, text=True):
    size = 300
    mx, my = (w - size) / 2, h * 0.42 - size * 0.62
    horizon = int(h * 0.72)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
             defs(),
             f'<rect width="{w}" height="{h}" fill="url(#sky)"/>',
             floor_grid(w, h, horizon),
             f'<line x1="0" y1="{horizon}" x2="{w}" y2="{horizon}" stroke="{PINK}" stroke-opacity="0.55" stroke-width="2"/>',
             f'<rect width="{w}" height="{h}" fill="url(#halo)"/>',
             rain(w, h, 260, seed=7),
             mark_group(mx, my, size, CYAN, glow=CYAN)]
    if text:
        ty = my + size * 1.2 + 70
        parts.append(f'<text x="{w / 2}" y="{ty:.0f}" text-anchor="middle" font-family="Silkscreen, JetBrains Mono, monospace" '
                     f'font-size="46" letter-spacing="14" fill="{TEXT}">NULL OS</text>')
        parts.append(f'<text x="{w / 2}" y="{ty + 44:.0f}" text-anchor="middle" font-family="VT323, JetBrains Mono, monospace" '
                     f'font-size="28" letter-spacing="4" fill="{DIM}">debian based  //  neon lab</text>')
    parts.append("</svg>")
    return "".join(parts)


def grub_svg(w=1920, h=1080):
    """Darker, quieter version so menu text stays readable."""
    size = 160
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            + defs() +
            f'<rect width="{w}" height="{h}" fill="{BG}"/>'
            + rain(w, h, 120, seed=3) +
            mark_group(w - size - 90, h - size * 1.2 - 70, size, CYAN, glow=CYAN) +
            '</svg>')


def boot_splash_svg(w=640, h=480):
    """ISO boot menu background (isolinux, 640x480). Menu sits in the middle,
    so the mark and name go top-left like Debian's layout."""
    size = 92
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            + defs() +
            f'<rect width="{w}" height="{h}" fill="{BG}"/>'
            + rain(w, h, 70, seed=11) +
            mark_group(46, 18, size, CYAN, glow=CYAN) +
            f'<text x="170" y="74" font-family="Silkscreen, monospace" font-size="34" letter-spacing="6" fill="{TEXT}">NULL OS</text>'
            f'<text x="172" y="104" font-family="VT323, monospace" font-size="22" letter-spacing="2" fill="{DIM}">debian based // neon lab</text>'
            f'<line x1="0" y1="{h - 60}" x2="{w}" y2="{h - 60}" stroke="{PINK}" stroke-opacity="0.5" stroke-width="1.5"/>'
            '</svg>')


def embed_png_svg(png_path, w, h):
    """An SVG that only wraps a PNG, so renderers need no fonts."""
    import base64
    data = base64.b64encode(open(png_path, "rb").read()).decode()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<image width="{w}" height="{h}" xlink:href="data:image/png;base64,{data}"/></svg>')


def desktop_base_theme(wallpaper_png, login_png):
    """Debian desktop-base theme: Plasma's default wallpaper, lock screen and
    the SDDM login background all follow /usr/share/desktop-base/active-theme."""
    import json
    import shutil
    base = ("config", "includes.chroot", "usr", "share", "desktop-base", "nullos-theme")
    meta = {"KPlugin": {"Id": "NullOS", "Name": "Null OS", "License": "GPL-3.0+",
                        "Authors": [{"Name": "Null Grid"}]}}
    for part in ("wallpaper", "lockscreen"):
        shutil.copy(wallpaper_png, out(*base, part, "contents", "images", "1920x1080.png"))
        with open(out(*base, part, "metadata.json"), "w") as f:
            json.dump(meta, f, indent=2)
    svg = embed_png_svg(login_png, 1920, 1080)
    for name in ("background.svg", "background-nologo.svg"):
        with open(out(*base, "login", name), "w") as f:
            f.write(svg)
    shutil.copy(login_png, out(*base, "login", "background.png"))


def sddm_logo_svg(w=420, h=110):
    """Logo for the SDDM login and idle screen: mark + NULL OS, transparent."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            + mark_group(6, 2, 88, CYAN) +
            f'<text x="112" y="70" font-family="Silkscreen, monospace" font-size="40" letter-spacing="8" fill="#ffffff">NULL OS</text>'
            '</svg>')


def main():
    logo = logo_svg()
    open(out("branding", "null-mark.svg"), "w").write(logo)
    cairosvg.svg2png(bytestring=avatar_svg().encode(),
                     write_to=out("config/includes.chroot/usr/share/null-os/null-mark-256.png"))
    wp = wallpaper_svg()
    bgdir = ("config", "includes.chroot", "usr", "share", "backgrounds", "null-os")
    open(out(*bgdir, "wallpaper.svg"), "w").write(wp)
    cairosvg.svg2png(bytestring=wp.encode(), write_to=out(*bgdir, "wallpaper.png"))
    cairosvg.svg2png(bytestring=grub_svg().encode(), write_to=out(*bgdir, "grub.png"))
    # Login background: wallpaper without the big centred mark text clash
    login_png = out("branding", "login-background.png")
    cairosvg.svg2png(bytestring=wallpaper_svg(text=False).encode(), write_to=login_png)
    desktop_base_theme(out(*bgdir, "wallpaper.png"), login_png)
    # ISO boot menu
    splash_png = out("branding", "boot-splash.png")
    cairosvg.svg2png(bytestring=boot_splash_svg().encode(), write_to=splash_png)
    with open(out("branding", "boot-splash.svg"), "w") as f:
        f.write(embed_png_svg(splash_png, 640, 480))
    # Plasma wallpaper package (default wallpaper of the Null OS look-and-feel)
    import json, shutil
    wp_dir = ("config", "includes.chroot", "usr", "share", "wallpapers", "NullOS")
    shutil.copy(out(*bgdir, "wallpaper.png"), out(*wp_dir, "contents", "images", "1920x1080.png"))
    cairosvg.svg2png(bytestring=wallpaper_svg().encode(), output_width=400, output_height=225,
                     write_to=out(*wp_dir, "contents", "screenshot.png"))
    with open(out(*wp_dir, "metadata.json"), "w") as f:
        json.dump({"KPlugin": {"Id": "NullOS", "Name": "Null OS", "License": "GPL-3.0+",
                               "Authors": [{"Name": "Null Grid"}]}}, f, indent=2)
    # Distro logo icon (os-release LOGO=null-os, About this System, menus)
    for size in (48, 64, 128, 256):
        cairosvg.svg2png(bytestring=avatar_svg().encode(), output_width=size, output_height=size,
                         write_to=out("config/includes.chroot/usr/share/icons/hicolor", f"{size}x{size}", "apps", "null-os.png"))
    with open(out("config/includes.chroot/usr/share/icons/hicolor/scalable/apps/null-os.svg"), "w") as f:
        f.write(avatar_svg())
    cairosvg.svg2png(bytestring=sddm_logo_svg().encode(),
                     write_to=out("config/includes.chroot/usr/share/null-os/sddm-logo.png"))
    print("branding written")


if __name__ == "__main__":
    main()
