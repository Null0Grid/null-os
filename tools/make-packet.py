#!/usr/bin/env python3
"""Packet, the Null Grid mascot, as pixel PNGs for Null OS.

Follows the mascot sheet (project doc null-grid/mascot-packet.md): 12x14
front grid with 1 px padding (viewBox -1 -1 14 16), half-pixel details,
whole-step scaling, mood only through visor and antenna, a soft cyan glow.

  happy-wave  installer finished page (install worked)
  error       installer finished page (install failed)

Usage: python3 tools/make-packet.py   (writes config/includes.chroot/usr/share/null-os/packet-*.png)
"""
import os

from PIL import Image, ImageDraw, ImageFilter

BODY, TRIM, VISOR = "#323c54", "#4a5677", "#0b0e15"
CYAN, PINK, RED, GREEN, STEM = "#00e5ff", "#ff2e88", "#ff3b4e", "#39ff88", "#8b92a8"

# (x, y, w, h, color) in sprite pixels
BASE = [
    (5, 0, 2, 1, PINK), (5.5, 1, 1, 1, STEM),                       # antenna
    (2, 2, 8, 5, BODY), (2, 2, 8, 1, TRIM),                         # head + highlight
    (3, 3, 6, 3, VISOR),                                            # visor
    (1, 4, 1, 2, TRIM), (10, 4, 1, 2, TRIM),                        # ears
    (3, 7, 6, 4, BODY),                                             # body
    (4, 8, 1, 2, CYAN), (5, 8, 1, 2, CYAN), (6, 9, 1, 1, GREEN),    # chest lights
    (2, 8, 1, 2, TRIM),                                             # left arm
    (4, 11, 1, 2, TRIM), (7, 11, 1, 2, TRIM),                       # legs
    (3, 13, 2, 1, CYAN), (7, 13, 2, 1, CYAN),                       # feet
]
ARM_DOWN = [(9, 8, 1, 2, TRIM)]
ARM_WAVE = [(9, 8, 1, 1, TRIM), (10, 7, 1, 1, TRIM), (11, 6, 1, 1, TRIM), (12, 5, 1, 1, TRIM), (12, 4, 1, 1, TRIM)]
EYES_HAPPY = [(x, y, .5, .5, CYAN) for x, y in
              ((3.5, 4.5), (4, 4), (4.5, 4), (5, 4.5), (6.5, 4.5), (7, 4), (7.5, 4), (8, 4.5))]
EYES_ERROR = [(x, y, .5, .5, PINK) for cx in (3.5, 7) for x, y in
              ((cx, 3.5), (cx + 1, 3.5), (cx + .5, 4), (cx, 4.5), (cx + 1, 4.5))]
SPARKLES = [(-0.5, 1, .5, .5, CYAN), (0, 0.5, .5, .5, CYAN), (11.5, 1.5, .5, .5, GREEN),
            (12.5, 2.5, .5, .5, CYAN), (11, 3, .5, .5, STEM), (11.5, 4, .5, .5, STEM), (-0.5, 10, .5, .5, PINK), (12, 11, .5, .5, CYAN)]

SPRITES = {
    "happy-wave": BASE + ARM_WAVE + EYES_HAPPY + SPARKLES,
    "error": [(x, y, w, h, RED if c == PINK and y < 1 else c) for x, y, w, h, c in BASE]
             + ARM_DOWN + EYES_ERROR + [(11, 0, .5, 1.5, RED), (11, 2, .5, .5, RED)],
}


def render(rects, scale=16, glow=True):
    pad = 1                                   # viewBox -1 -1 14 16
    w, h = int(14 * scale), int(16 * scale)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for x, y, rw, rh, c in rects:
        x0, y0 = round((x + pad) * scale), round((y + pad) * scale)
        x1, y1 = round((x + pad + rw) * scale), round((y + pad + rh) * scale)
        d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=c)
    if not glow:
        return img
    # drop-shadow(0 0 8px rgba(0,229,255,.4)), scaled: cyan halo from the silhouette
    m = 24
    out = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    alpha = Image.new("L", out.size, 0)
    alpha.paste(img.split()[3], (m, m))
    halo = Image.new("RGBA", out.size, (0, 229, 255, 0))
    halo.putalpha(alpha.filter(ImageFilter.GaussianBlur(scale * 0.9)).point(lambda a: int(a * 0.4)))
    out.alpha_composite(halo)
    out.alpha_composite(img, (m, m))
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "..", "config", "includes.chroot", "usr", "share", "null-os")
    os.makedirs(dest, exist_ok=True)
    for name, rects in SPRITES.items():
        p = os.path.join(dest, f"packet-{name}.png")
        render(rects).save(p)
        print("wrote", os.path.relpath(p))


if __name__ == "__main__":
    main()
