#!/usr/bin/env python3
"""Render the Null OS Plymouth theme: glitch startup + CRT shutdown.

Writes frames and the theme files into
config/includes.chroot/usr/share/plymouth/themes/null/

Requires: pip install cairosvg pillow; Silkscreen and VT323 installed
(fc-list) or passed with --fonts DIR. Deterministic (seeded), so rebuilds
produce identical frames.
"""
import importlib.util
import io
import os
import random
import shutil
import sys

import cairosvg
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "null_mark", os.path.join(ROOT, "config/includes.chroot/usr/share/null-os/null-mark.py"))
mark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mark)

OUT = os.path.join(ROOT, "config/includes.chroot/usr/share/plymouth/themes/null")
W, H = 960, 540
BG = (10, 10, 15)
CYAN = (0, 229, 255)
PINK = (255, 46, 136)
TEXT = (201, 212, 227)
DIM = (74, 90, 112)
WHITE = (255, 255, 255)
MARK_W = 150
FPS = 25            # Plymouth refresh ~50 Hz, theme advances every 2 ticks
BOOT_LOOP = 40      # last N boot frames loop until boot finishes


def find_font(names, size):
    dirs = [os.path.expanduser("~/.fonts"), "/usr/share/fonts", os.path.join(ROOT, "config/includes.chroot/usr/share/fonts")]
    for d in dirs:
        for root, _, files in os.walk(d):
            for f in files:
                if any(n.lower() in f.lower() for n in names) and f.lower().endswith(".ttf"):
                    return ImageFont.truetype(os.path.join(root, f), size)
    return ImageFont.load_default()


TITLE = find_font(["silkscreen-regular", "silkscreen"], 34)
SUB = find_font(["vt323"], 26)


def mark_sprite(color):
    path = mark.svg_path(flip_height=720)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 720" width="600" height="720">'
           f'<path d="{path}" fill="rgb{color}" fill-rule="nonzero"/></svg>')
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=MARK_W, output_height=int(MARK_W * 1.2))
    return Image.open(io.BytesIO(png)).convert("RGBA")


M_CYAN = mark_sprite(CYAN)
M_PINK = mark_sprite(PINK)
M_W, M_H = M_CYAN.size
MX, MY = (W - M_W) // 2, int(H * 0.40) - M_H // 2


def glow(sprite, radius=10, strength=1.0):
    g = Image.new("RGBA", (sprite.width + 80, sprite.height + 80), (0, 0, 0, 0))
    g.alpha_composite(sprite, (40, 40))
    g = g.filter(ImageFilter.GaussianBlur(radius))
    if strength != 1.0:
        a = g.getchannel("A").point(lambda v: min(255, int(v * strength)))
        g.putalpha(a)
    return g


GLOW = glow(M_CYAN, 12, 1.4)


def blank():
    return Image.new("RGBA", (W, H), BG + (255,))


def put_mark(img, sprite, dx=0, dy=0, with_glow=False, alpha=1.0, blend_screen=False):
    if with_glow:
        img.alpha_composite(GLOW, (MX - 40 + dx, MY - 40 + dy))
    s = sprite
    if alpha < 1.0:
        s = sprite.copy()
        s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    if blend_screen:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        layer.alpha_composite(s, (MX + dx, MY + dy))
        rgb = ImageChops.screen(img.convert("RGB"), layer.convert("RGB"))
        img.paste(rgb.convert("RGBA"))
    else:
        img.alpha_composite(s, (MX + dx, MY + dy))


def text_center(img, text, font, y, color, dx=0, spacing=8):
    d = ImageDraw.Draw(img)
    widths = [d.textlength(ch, font=font) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = (W - total) / 2 + dx
    for ch, w in zip(text, widths):
        d.text((x, y), ch, font=font, fill=color)
        x += w + spacing


TITLE_Y = MY + M_H + 34
SUB_Y = TITLE_Y + 46
BAR_W, BAR_Y = 180, H - 70


def noise(img, rnd, amount):
    d = ImageDraw.Draw(img)
    for _ in range(int(amount * 140)):
        y = rnd.randrange(H)
        x = rnd.randrange(-200, W)
        L = rnd.randrange(20, 400)
        v = rnd.randrange(40, 200)
        d.line([(x, y), (x + L, y)], fill=(v, v, v, int(120 * amount)), width=1)


def tear(img, rnd, color, alpha):
    d = ImageDraw.Draw(img)
    y = rnd.randrange(int(H * 0.2), int(H * 0.75))
    h = rnd.choice([3, 5, 8, 12])
    off = rnd.randrange(-W // 3, W // 3)
    d.rectangle([off, y, off + W, y + h], fill=color + (alpha,))


def slice_shift(img, rnd, n=4, maxshift=24):
    """Displace horizontal bands, like a corrupted video signal."""
    out = img.copy()
    for _ in range(n):
        y0 = rnd.randrange(int(H * 0.25), int(H * 0.7))
        h = rnd.randrange(6, 30)
        band = img.crop((0, y0, W, y0 + h))
        shift = rnd.randrange(-maxshift, maxshift)
        out.paste(blank().crop((0, 0, W, h)), (0, y0))
        out.paste(band, (shift, y0))
    return out


def half_render(sprite, top_half):
    s = sprite.copy()
    a = s.getchannel("A")
    cut = Image.new("L", s.size, 0)
    d = ImageDraw.Draw(cut)
    if top_half:
        d.rectangle([0, 0, s.width, int(s.height * 0.45)], fill=255)
    else:
        d.rectangle([0, int(s.height * 0.4), s.width, s.height], fill=255)
    s.putalpha(ImageChops.multiply(a, cut))
    return s


def bar(img, pos):
    """Indeterminate cyan sweep, pos in [0,1)."""
    d = ImageDraw.Draw(img)
    x0 = (W - BAR_W) // 2
    d.rectangle([x0, BAR_Y, x0 + BAR_W, BAR_Y + 1], fill=(28, 38, 51, 255))
    seg = 54
    start = x0 + int((BAR_W + seg) * pos) - seg
    a, b = max(x0, start), min(x0 + BAR_W, start + seg)
    if b > a:
        d.rectangle([a, BAR_Y, b, BAR_Y + 1], fill=CYAN + (255,))


def boot_frames():
    rnd = random.Random(404)
    frames = []
    # 0-9: static burst
    for i in range(10):
        img = blank()
        noise(img, rnd, 1.0 - i * 0.07)
        frames.append(img)
    # 10-55: RGB split, tears, sliced half-renders
    for i in range(46):
        t = i / 45
        img = blank()
        noise(img, rnd, max(0, 0.4 - t * 0.5))
        amp = int(18 * (1 - t) ** 1.5) + 1
        show = rnd.random() > 0.18 or t > 0.8
        if show:
            dxc, dxp = -rnd.randrange(1, amp + 1), rnd.randrange(1, amp + 1)
            dy = rnd.randrange(-2, 3) if t < 0.6 else 0
            put_mark(img, M_CYAN, dxc, dy, blend_screen=True)
            put_mark(img, M_PINK, dxp, -dy, blend_screen=True)
        if t > 0.35 and rnd.random() < 0.45:
            put_mark(img, half_render(M_CYAN, rnd.random() < 0.5), rnd.randrange(-6, 7), 0, with_glow=False)
        for _ in range(rnd.choice([0, 1, 1, 2, 3]) if t < 0.85 else 0):
            tear(img, rnd, rnd.choice([CYAN, PINK, WHITE]), rnd.randrange(60, 170))
        if t < 0.7 and rnd.random() < 0.5:
            img = slice_shift(img, rnd, n=rnd.randrange(2, 6))
        frames.append(img)
    # 56-70: mark locks in with neon flicker; title glitches pink/cyan
    flick = [1, 0.3, 1, 1, 0.5, 1, 1, 1, 0.8, 1, 1, 1, 1, 1, 1]
    for i, f in enumerate(flick):
        img = blank()
        put_mark(img, M_CYAN, 0, 0, with_glow=f > 0.9, alpha=f)
        if i >= 6:
            c = [PINK, CYAN, None, PINK, TEXT, CYAN, TEXT, TEXT, TEXT][min(i - 6, 8)]
            if c:
                text_center(img, "NULL OS", TITLE, TITLE_Y, c + (255,), dx=rnd.choice([-6, -3, 0, 3, 5]) if c != TEXT else 0)
        frames.append(img)
    # 71-80: subtitle fades in
    for i in range(10):
        img = blank()
        put_mark(img, M_CYAN, with_glow=True)
        text_center(img, "NULL OS", TITLE, TITLE_Y, TEXT + (255,))
        a = (i + 1) / 10
        col = tuple(int(BG[k] + (DIM[k] - BG[k]) * a) for k in range(3))
        text_center(img, "debian based // neon lab", SUB, SUB_Y, col + (255,), spacing=2)
        frames.append(img)
    # 81-120: loop with the loading sweep and a rare flicker
    for i in range(BOOT_LOOP):
        img = blank()
        dim = 0.75 if i in (17, 29) else 1.0
        put_mark(img, M_CYAN, with_glow=dim == 1.0, alpha=dim)
        text_center(img, "NULL OS", TITLE, TITLE_Y, TEXT + (255,))
        text_center(img, "debian based // neon lab", SUB, SUB_Y, DIM + (255,), spacing=2)
        bar(img, i / BOOT_LOOP)
        frames.append(img)
    return frames


def shutdown_scene(dx=0, pink=False):
    img = blank()
    put_mark(img, M_PINK if pink else M_CYAN, dx, 0, with_glow=not pink)
    text_center(img, "NULL OS", TITLE, TITLE_Y, TEXT + (255,), dx=dx)
    text_center(img, "powering down // see you on the grid", SUB, SUB_Y, DIM + (255,), dx=dx, spacing=2)
    return img


def crt(img, sx, sy):
    """Squash the frame around its centre, CRT power-off style."""
    w, h = max(1, int(W * sx)), max(1, int(H * sy))
    small = img.resize((w, h), Image.BILINEAR)
    if sy < 0.06:  # brighten as it collapses into a line
        small = Image.blend(small, Image.new("RGBA", small.size, WHITE + (255,)), 0.7)
    out = blank()
    out.alpha_composite(small, ((W - w) // 2, (H - h) // 2))
    return out


def shutdown_frames():
    rnd = random.Random(1337)
    frames = []
    # 0-22: glitch jitter
    for i in range(23):
        dx = rnd.choice([-6, 5, -3, 4, -2, 0, 0]) if i < 18 else 0
        img = shutdown_scene(dx, pink=(i in (3, 4, 9)))
        if i < 16 and rnd.random() < 0.4:
            img = slice_shift(img, rnd, n=2, maxshift=14)
        frames.append(img)
    base = shutdown_scene()
    # 23-35: collapse to a bright line
    steps = 13
    for i in range(steps):
        t = (i + 1) / steps
        frames.append(crt(base, 1 + 0.2 * t, max(0.004, 1 - t * 0.996)))
    # 36-50: line shrinks to a dot and fades
    for i in range(15):
        t = (i + 1) / 15
        img = blank()
        d = ImageDraw.Draw(img)
        half = int((W * 0.6) * (1 - t) ** 2) + 2
        a = 255 if t < 0.75 else int(255 * (1 - (t - 0.75) / 0.25))
        d.rectangle([W // 2 - half, H // 2 - 1, W // 2 + half, H // 2 + 1], fill=WHITE + (a,))
        frames.append(img)
    frames.append(blank())
    return frames


SCRIPT = r'''# Null OS Plymouth theme — generated by tools/make-plymouth.py
Window.SetBackgroundTopColor(0.039, 0.039, 0.059);
Window.SetBackgroundBottomColor(0.039, 0.039, 0.059);

mode = Plymouth.GetMode();
if (mode == "shutdown" || mode == "reboot") {
  prefix = "down-"; count = %(down)d; loop = 0;
} else {
  prefix = "boot-"; count = %(boot)d; loop = 1;
}
loop_len = %(loop)d;

for (i = 0; i < count; i++)
  frames[i] = Image(prefix + i + ".png");

sprite = Sprite();
sprite.SetX(Window.GetX() + Window.GetWidth() / 2 - frames[0].GetWidth() / 2);
sprite.SetY(Window.GetY() + Window.GetHeight() / 2 - frames[0].GetHeight() / 2);
sprite.SetImage(frames[0]);

tick = 0;
fun refresh_callback() {
  idx = Math.Int(tick / 2);
  if (idx >= count) {
    if (loop) idx = count - loop_len + ((idx - count) %% loop_len);
    else idx = count - 1;
  }
  sprite.SetImage(frames[idx]);
  tick++;
}
Plymouth.SetRefreshFunction(refresh_callback);

# Disk-unlock password prompt (encrypted installs)
prompt_sprite = Sprite();
bullets_sprite = Sprite();
fun display_password_callback(prompt, bullets) {
  t = Image.Text(prompt, 0.79, 0.83, 0.89);
  prompt_sprite.SetImage(t);
  prompt_sprite.SetX(Window.GetWidth() / 2 - t.GetWidth() / 2);
  prompt_sprite.SetY(Window.GetHeight() * 0.78);
  s = "";
  for (i = 0; i < bullets; i++) s += "*";
  b = Image.Text(s + " ", 0.0, 0.9, 1.0);
  bullets_sprite.SetImage(b);
  bullets_sprite.SetX(Window.GetWidth() / 2 - b.GetWidth() / 2);
  bullets_sprite.SetY(Window.GetHeight() * 0.78 + 28);
}
fun display_normal_callback() {
  prompt_sprite.SetImage(Image.Text("", 1, 1, 1));
  bullets_sprite.SetImage(Image.Text("", 1, 1, 1));
}
Plymouth.SetDisplayPasswordFunction(display_password_callback);
Plymouth.SetDisplayNormalFunction(display_normal_callback);

fun message_callback(text) {}
Plymouth.SetMessageFunction(message_callback);
'''

PLYMOUTH = '''[Plymouth Theme]
Name=Null OS
Description=Glitch startup and CRT shutdown for Null OS
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/null
ScriptFile=/usr/share/plymouth/themes/null/null.script
'''


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    boot = boot_frames()
    down = shutdown_frames()
    for i, f in enumerate(boot):
        f.convert("RGB").save(os.path.join(OUT, f"boot-{i}.png"), optimize=True)
    for i, f in enumerate(down):
        f.convert("RGB").save(os.path.join(OUT, f"down-{i}.png"), optimize=True)
    with open(os.path.join(OUT, "null.script"), "w") as f:
        f.write(SCRIPT % {"boot": len(boot), "down": len(down), "loop": BOOT_LOOP})
    with open(os.path.join(OUT, "null.plymouth"), "w") as f:
        f.write(PLYMOUTH)
    # Preview strips/GIFs for review (not shipped)
    prev = os.path.join(ROOT, "branding", "preview")
    os.makedirs(prev, exist_ok=True)
    small = lambda fr: [x.convert("RGB").resize((480, 270)) for x in fr]
    sb = small(boot)
    sb[0].save(os.path.join(prev, "startup.gif"), save_all=True, append_images=sb[1:] + sb[-BOOT_LOOP:],
               duration=int(1000 / FPS), loop=0)
    sd = small(down) + [small([blank()])[0]] * 10
    sd[0].save(os.path.join(prev, "shutdown.gif"), save_all=True, append_images=sd[1:],
               duration=int(1000 / FPS), loop=0)
    print(f"plymouth: {len(boot)} boot + {len(down)} shutdown frames -> {OUT}")


if __name__ == "__main__":
    main()
