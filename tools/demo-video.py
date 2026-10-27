#!/usr/bin/env python3
"""Record and edit the Null OS demo video.

  demo-video.py record <iso> <workdir>   boot the ISO in QEMU, grab the guest
                                         screen ~8 fps while driving a scripted
                                         tour; writes raw.mkv + scenes.json
  demo-video.py edit <workdir> <out.mp4> cut, speed up, caption and add an
                                         intro and outro; writes the final mp4

record needs: qemu-system-x86_64 and ffmpeg. Frames come straight from the
guest framebuffer (QEMU screendump), so no display server is needed. edit needs: ffmpeg (drawtext), Pillow, Silkscreen and VT323
TTFs in $DEMO_FONTS (default ./demo-fonts).
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time

W, H, FPS = 1280, 800, 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MON = "/tmp/null-demo-monitor.sock"      # keys
CAP = "/tmp/null-demo-capture.sock"      # screendumps (separate monitor)

KEYS = {" ": "spc", "-": "minus", "/": "slash", ".": "dot", "\n": "ret",
        "_": "shift-minus", "~": "shift-grave_accent", "|": "shift-backslash",
        "=": "equal", ":": "shift-semicolon", ">": "shift-dot", ";": "semicolon",
        "*": "shift-8", "'": "apostrophe", ",": "comma", "^": "shift-6",
        "$": "shift-4", "!": "shift-1", "#": "shift-3", "\\": "backslash"}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- record

def monitor(cmd):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(MON)
        try:
            s.recv(4096)
        except socket.timeout:
            pass
        s.sendall((cmd + "\n").encode())
        time.sleep(0.12)
        try:
            s.recv(4096)
        except socket.timeout:
            pass


def key(name, pause=0.06):
    monitor(f"sendkey {name}")
    time.sleep(pause)


def type_text(text):
    for ch in text:
        if ch in KEYS:
            key(KEYS[ch])
        elif ch.isupper():
            key("shift-" + ch.lower())
        else:
            key(ch)


class Capture(threading.Thread):
    """Grab the guest framebuffer through a dedicated QEMU monitor, at full
    guest resolution, no window or display server involved. Uses PNG
    screendumps when QEMU supports them, otherwise PPM converted to JPEG."""

    def __init__(self, outdir, t0):
        super().__init__(daemon=True)
        self.outdir, self.t0 = outdir, t0
        self.frames = []          # (path, t)
        self.running = True
        self.paused = False
        self.fmt = "png"
        self.errors = []
        os.makedirs(outdir, exist_ok=True)

    def run(self):
        try:
            self._run()
        except Exception as e:  # never kill the tour; report instead
            self.errors.append(f"capture crashed: {e!r}")

    def _run(self):
        from PIL import Image
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(15)
        for _ in range(50):
            try:
                s.connect(CAP)
                break
            except OSError:
                time.sleep(0.2)
        buf = b""

        def until_prompt():
            nonlocal buf
            while b"(qemu)" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    raise OSError("monitor closed")
                buf += chunk
            reply, buf = buf.split(b"(qemu)", 1)
            return reply.decode(errors="replace")

        until_prompt()
        n = 0
        while self.running:
            if self.paused:
                time.sleep(0.2)
                continue
            t = time.time() - self.t0
            if self.fmt == "png":
                path = os.path.join(self.outdir, f"{n:06d}.png")
                cmd = f"screendump -f png {path}"
            else:
                path = os.path.join(self.outdir, f"{n:06d}.ppm")
                cmd = f"screendump {path}"
            try:
                s.sendall((cmd + "\n").encode())
                reply = until_prompt()
            except (socket.timeout, OSError) as e:
                self.errors.append(f"monitor: {e!r}")
                time.sleep(0.5)
                continue
            # The reply echoes the command; anything else is an error message
            extra = reply.replace(cmd, "").strip()
            if extra and len(self.errors) < 5:
                self.errors.append(f"{cmd.split()[0]} {self.fmt}: {extra[:200]}")
            if not os.path.exists(path):
                if self.fmt == "png":
                    self.fmt = "ppm"   # QEMU without PNG screendump support
                time.sleep(0.1)
                continue
            if self.fmt == "ppm":
                jpg = path[:-4] + ".jpg"
                try:
                    Image.open(path).convert("RGB").save(jpg, quality=92)
                    os.remove(path)
                    path = jpg
                except Exception as e:
                    self.errors.append(f"ppm convert: {e!r}")
                    continue
            self.frames.append((path, round(t, 3)))
            n += 1
            time.sleep(0.03)
        s.close()


class Scenes:
    def __init__(self, t0):
        self.t0 = t0
        self.items = []
        self.cur = None

    def now(self):
        return round(time.time() - self.t0, 2)

    def start(self, name, caption, sub="", speed=1.0, skip_start=0.0):
        self.end()
        self.cur = {"name": name, "caption": caption, "sub": sub, "speed": speed,
                    "start": self.now() + skip_start}
        log(f"scene {name} @ {self.cur['start']}")

    def end(self, trim_end=0.0):
        if self.cur:
            self.cur["end"] = self.now() - trim_end
            self.items.append(self.cur)
            self.cur = None


def record(iso, work):
    os.makedirs(work, exist_ok=True)
    framedir = os.path.join(work, "frames")
    shutil.rmtree(framedir, ignore_errors=True)
    t0 = time.time()
    sc = Scenes(t0)

    for p in (MON, CAP):
        if os.path.exists(p):
            os.remove(p)
    kvm = os.access("/dev/kvm", os.R_OK | os.W_OK)
    cmd = ["qemu-system-x86_64", "-m", "4096", "-smp", "2", "-cdrom", iso, "-boot", "d",
           "-vga", "virtio", "-display", "none",
           "-monitor", f"unix:{MON},server,nowait", "-monitor", f"unix:{CAP},server,nowait",
           "-nic", "user,model=virtio-net-pci"]
    if kvm:
        cmd += ["-enable-kvm", "-cpu", "host"]
    log(f"starting QEMU (kvm={kvm})")
    vm = subprocess.Popen(cmd)
    cap = Capture(framedir, t0)
    try:
        for _ in range(50):
            if os.path.exists(MON) and os.path.exists(CAP):
                break
            time.sleep(0.2)
        cap.start()

        time.sleep(4)
        sc.start("boot-menu", "BOOT MENU", "null os 0.2 / live usb")
        time.sleep(4)
        key("ret")
        time.sleep(5)
        sc.start("startup", "GLITCH STARTUP", "plymouth / built from the null mark", speed=1.8)
        time.sleep(15)
        sc.end()

        log("waiting for the desktop")
        cap.paused = True
        time.sleep(95)
        cap.paused = False
        time.sleep(1)
        sc.start("desktop", "KDE PLASMA / NEON LAB", "null lab colors / nullline icons")
        time.sleep(4.5)

        sc.start("start-menu", "START MENU", "null grid browser pinned first")
        key("meta_l")
        time.sleep(2.5)
        type_text("node")
        time.sleep(1.5)
        key("ret")
        sc.start("browser", "NULL GRID BROWSER", "null search by default", speed=1.6)
        time.sleep(10)
        key("esc")          # close the first-run welcome
        time.sleep(1)
        key("esc")
        time.sleep(1)
        key("ctrl-l")
        time.sleep(0.6)
        type_text("search.nullgrid.dev\n")
        time.sleep(9)
        sc.end()
        key("alt-f4")
        time.sleep(3)

        sc.start("terminal", "TWO-LINE PROMPT", "zsh / null mono / network toolkit", speed=1.9)
        key("ctrl-alt-t")
        time.sleep(4)
        type_text("null-info\n")
        time.sleep(2)
        type_text("nmap -sn 10.0.2.0/28\n")
        time.sleep(7)
        type_text("curl -sI https://search.nullgrid.dev | head -n 1\n")
        time.sleep(3)
        type_text("nope\n")
        time.sleep(1.5)
        sc.start("root", "ROOT MODE", "the frame turns red", speed=1.3)
        type_text("sudo -i\n")
        time.sleep(3)
        type_text("exit\n")
        time.sleep(1)
        sc.end()
        key("alt-f4")
        time.sleep(2)

        sc.start("discover", "DISCOVER + FLATHUB", "apps in one click", speed=2.0)
        key("meta_l")
        time.sleep(1.5)
        type_text("discover")
        time.sleep(1.2)
        key("ret")
        time.sleep(11)
        sc.end()
        key("alt-f4")
        time.sleep(2)

        sc.start("files", "FILES", "dolphin for now / null files is coming", speed=1.3)
        key("meta_l")
        time.sleep(1.5)
        type_text("dolphin")
        time.sleep(1.2)
        key("ret")
        time.sleep(6)
        sc.end()
        key("alt-f4")
        time.sleep(2)

        sc.start("shutdown", "SHUTDOWN", "see you on the grid")
        key("ctrl-alt-t")
        time.sleep(3)
        type_text("sudo poweroff\n")
        time.sleep(5)
        sc.end()
    finally:
        sc.end()
        time.sleep(1)
        cap.running = False
        cap.join(timeout=15)
        vm.terminate()
        try:
            vm.wait(timeout=30)
        except subprocess.TimeoutExpired:
            vm.kill()
    # Frames -> constant-rate raw video on the same clock as the scenes.
    # Each frame lasts until the next one; paused stretches simply hold.
    frames = cap.frames
    log(f"captured {len(frames)} frames ({cap.fmt})")
    # Visible in the run's annotations even when logs can't be downloaded
    print(f"::notice title=capture::{len(frames)} frames, format {cap.fmt}", flush=True)
    for e in cap.errors[:5]:
        print(f"::warning title=capture-error::{e}", flush=True)
    if not frames:
        sys.exit("no frames captured")
    lst = os.path.join(work, "frames.txt")
    with open(lst, "w") as f:
        f.write("ffconcat version 1.0\n")
        if frames:
            f.write(f"file '{frames[0][0]}'\nduration {frames[0][1]:.3f}\n")  # lead-in
        for (p, t), nxt in zip(frames, frames[1:] + [(None, frames[-1][1] + 0.5)] if frames else []):
            f.write(f"file '{p}'\nduration {max(0.01, nxt[1] - t):.3f}\n")
        if frames:
            f.write(f"file '{frames[-1][0]}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0a0a0f,fps={FPS},format=yuv420p",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", os.path.join(work, "raw.mkv")], check=True)
    with open(os.path.join(work, "scenes.json"), "w") as f:
        json.dump(sc.items, f, indent=2)
    log(f"recorded {len(sc.items)} scenes -> {raw}")


# ---------------------------------------------------------------- edit

def fonts():
    d = os.environ.get("DEMO_FONTS", "demo-fonts")
    title = next((os.path.join(d, f) for f in os.listdir(d) if "silkscreen" in f.lower()), None)
    sub = next((os.path.join(d, f) for f in os.listdir(d) if "vt323" in f.lower()), None)
    if not title or not sub:
        sys.exit(f"Silkscreen/VT323 TTFs not found in {d}")
    return title, sub


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace(",", "\\,").replace("%", "\\%")


def caption_filter(cap, sub, ftitle, fsub):
    a = "if(lt(t\\,0.35)\\,t/0.35\\,1)"
    f = [f"drawbox=x=36:y=ih-122:w=8:h=74:color=0x00e5ff@1:t=fill:enable='gte(t\\,0.1)'",
         f"drawtext=fontfile='{ftitle}':text='{esc(cap)}':fontsize=34:fontcolor=0xffffff:"
         f"x=60:y=h-120:alpha='{a}':shadowcolor=0x0a0a0f@0.9:shadowx=2:shadowy=2"]
    if sub:
        f.append(f"drawtext=fontfile='{fsub}':text='{esc(sub)}':fontsize=30:fontcolor=0x00e5ff:"
                 f"x=62:y=h-78:alpha='{a}':shadowcolor=0x0a0a0f@0.9:shadowx=2:shadowy=2")
    return ",".join(f)


def card(path, lines, wallpaper):
    """Title card: Null OS wallpaper cropped to the frame, dimmed, with text."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageFont
    ftitle, fsub = fonts()
    img = Image.open(wallpaper).convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * scale), int(img.height * scale)))
    l, t = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((l, t, l + W, t + H))
    if lines:
        img = ImageEnhance.Brightness(img).enhance(0.55)
    d = ImageDraw.Draw(img)
    y = H - 210
    for text, size, color, font in lines:
        f = ImageFont.truetype(ftitle if font == "title" else fsub, size)
        w = d.textlength(text, font=f)
        d.text(((W - w) / 2, y), text, font=f, fill=color)
        y += size + 18
    img.save(path)


def edit(work, out):
    ftitle, fsub = fonts()
    scenes = json.load(open(os.path.join(work, "scenes.json")))
    raw = os.path.join(work, "raw.mkv")
    # Text-free wallpaper (the login background), so titles don't double up
    wallpaper = os.path.join(ROOT, "branding/login-background.png")
    frames = os.path.join(ROOT, "config/includes.chroot/usr/share/plymouth/themes/null")

    intro = os.path.join(work, "intro.png")
    outro = os.path.join(work, "outro.png")
    card(intro, [], wallpaper)
    card(outro, [("github.com/Null0Grid/null-os", 30, (0, 229, 255), "sub"),
                 ("SEE YOU ON THE GRID", 36, (255, 255, 255), "title")], wallpaper)

    # CRT shutdown: the theme's own frames (the VM freezes at power-off)
    crt = os.path.join(work, "crt.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "25",
                    "-start_number", "0", "-i", os.path.join(frames, "down-%d.png"),
                    "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0a0a0f,fps={FPS},format=yuv420p",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", crt], check=True)

    inputs = ["-i", raw,
              "-loop", "1", "-t", "3.2", "-framerate", str(FPS), "-i", intro,
              "-i", crt,
              "-loop", "1", "-t", "4.0", "-framerate", str(FPS), "-i", outro]
    norm = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0a0a0f,fps={FPS},format=yuv420p,setsar=1"
    parts, labels = [], []

    # Intro: wallpaper with a slow push-in and the title fading up
    parts.append(f"[1:v]{norm},zoompan=z='min(zoom+0.0007\\,1.08)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
                 f"drawtext=fontfile='{ftitle}':text='NULL OS':fontsize=72:fontcolor=0xffffff:"
                 f"x=(w-text_w)/2:y=h-200:alpha='if(lt(t\\,0.6)\\,0\\,min(1\\,(t-0.6)/0.6))',"
                 f"drawtext=fontfile='{fsub}':text='debian based // neon lab // v0.2':fontsize=34:fontcolor=0x00e5ff:"
                 f"x=(w-text_w)/2:y=h-118:alpha='if(lt(t\\,1.1)\\,0\\,min(1\\,(t-1.1)/0.6))',"
                 f"fade=t=in:st=0:d=0.5,fade=t=out:st=2.8:d=0.4[intro]")
    labels.append("[intro]")

    for i, s in enumerate(scenes):
        a, b = max(0.0, s["start"]), s["end"]
        if b - a < 0.5:
            continue
        sp = s.get("speed", 1.0)
        lab = f"[s{i}]"
        parts.append(f"[0:v]trim=start={a}:end={b},setpts=(PTS-STARTPTS)/{sp},{norm},"
                     f"{caption_filter(s['caption'], s.get('sub', ''), ftitle, fsub)}{lab}")
        labels.append(lab)

    parts.append(f"[2:v]{norm}[crt]")
    labels.append("[crt]")
    parts.append(f"[3:v]{norm},fade=t=in:st=0:d=0.6,fade=t=out:st=3.4:d=0.6[outro]")
    labels.append("[outro]")
    parts.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[v]")

    fc = os.path.join(work, "filter.txt")
    with open(fc, "w") as f:
        f.write(";\n".join(parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex_script", fc,
                    "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], check=True)
    # Poster frame from the desktop scene
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "12", "-i", out,
                    "-frames:v", "1", os.path.splitext(out)[0] + "-poster.png"], check=False)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip()
    log(f"wrote {out} ({dur} s)")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "record":
        try:
            record(sys.argv[2], sys.argv[3])
        except BaseException as e:
            print(f"::error title=record-failed::{e!r}"[:900], flush=True)
            raise
    elif len(sys.argv) == 4 and sys.argv[1] == "edit":
        edit(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
