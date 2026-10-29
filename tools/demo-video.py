#!/usr/bin/env python3
"""Record and edit the Null OS demo video.

  demo-video.py record <iso> <workdir> [install]
                                         boot the ISO in QEMU, grab the guest
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
        "$": "shift-4", "!": "shift-1", "#": "shift-3", "\\": "backslash",
        "&": "shift-7", "(": "shift-9", ")": "shift-0", "\"": "shift-apostrophe"}


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
            # The reply is the monitor echoing the typed command (with
            # line-editing escape codes); only real error text matters
            import re
            extra = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", reply)
            extra = extra.replace(cmd, "").strip()
            extra = "" if not extra or cmd.startswith(extra) or extra in cmd else extra
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


def record(iso, work, kind="demo"):
    os.makedirs(work, exist_ok=True)
    with open(os.path.join(work, "kind.txt"), "w") as f:
        f.write(kind)
    framedir = os.path.abspath(os.path.join(work, "frames"))   # concat lists resolve relative to themselves
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
    if kind == "install":
        disk = os.path.abspath(os.path.join(work, "disk.qcow2"))
        subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", disk, "25G"], check=True)
        cmd = [c if c != "d" else "once=d" for c in cmd]          # CD first, then the installed disk
        cmd += ["-drive", f"file={disk},if=virtio,format=qcow2"]
    log(f"starting QEMU (kvm={kvm})")
    vm = subprocess.Popen(cmd)
    cap = Capture(framedir, t0)
    try:
        for _ in range(50):
            if os.path.exists(MON) and os.path.exists(CAP):
                break
            time.sleep(0.2)
        cap.start()
        (tour_install if kind == "install" else tour_demo)(sc, cap, work)
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
    log(f"recorded {len(sc.items)} scenes -> {os.path.join(work, 'raw.mkv')}")


def tour_demo(sc, cap, work):

    time.sleep(4)
    sc.start("boot-menu", "BOOT MENU", "null os 1.2.0 / live usb")
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

    sc.start("start-menu", "START MENU", "the null mark / null grid pinned first")
    key("meta_l")
    time.sleep(4)
    key("esc")
    time.sleep(1.5)
    sc.start("browser", "NULL GRID BROWSER", "null search by default", speed=1.8)
    key("meta_l-3")      # browser: 3rd taskbar pin (settings, files, browser)
    time.sleep(14)
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

    sc.start("terminal", "TWO-LINE PROMPT", "zsh / null mono", speed=1.9)
    key("ctrl-alt-t")
    time.sleep(4)
    type_text("null-info\n")
    time.sleep(2)
    type_text("ip -br addr\n")
    time.sleep(2)
    type_text("nope\n")
    time.sleep(1.5)
    sc.start("root", "ROOT MODE", "the frame turns red", speed=1.3)
    type_text("sudo -i\n")
    time.sleep(3)
    type_text("exit\n")
    time.sleep(1)
    sc.start("fastfetch", "FASTFETCH", "null os 1.2.0 on a debian 13 base", speed=1.2)
    type_text("clear; fastfetch\n")
    time.sleep(4)
    sc.start("shortcuts", "NEW APP? PIN IT", "every install asks: add to desktop", speed=2.6)
    type_text("clear; mkdir -p ~/.local/share/applications; "
              "cp /usr/share/applications/org.kde.konsole.desktop ~/.local/share/applications/demo-app.desktop\n")
    time.sleep(7)
    sc.end()
    key("alt-f4")
    time.sleep(2)

    sc.start("extras", "MINIMAL OR FULL", "null os extras: add the full package any time", speed=1.2)
    key("meta_l")
    time.sleep(2)
    type_text("extras")
    time.sleep(2.5)
    key("ret")
    time.sleep(7)
    sc.end()
    key("esc")
    time.sleep(2)

    sc.start("files", "NULL FILE", "the null grid file manager", speed=4.0)
    key("meta_l-2")
    time.sleep(16)
    sc.start("files2", "NULL FILE", "grid / list / graph views", speed=1.0)
    time.sleep(5)
    sc.end()
    key("alt-f4")
    time.sleep(2)

    sc.start("shutdown", "SHUTDOWN", "see you on the grid")
    key("ctrl-alt-t")
    time.sleep(3)
    type_text("sudo poweroff\n")
    time.sleep(5)
    sc.end()


def step(work, name):
    """Debug still for each installer step (published next to the video)."""
    d = os.path.join(work, "steps")
    os.makedirs(d, exist_ok=True)
    monitor(f"screendump {os.path.join(d, name)}.ppm")


def finished_page():
    """True when most of the screen is the finished page's #0a0e14."""
    from PIL import Image
    probe = "/tmp/null-probe.ppm"
    try:
        os.remove(probe)
    except OSError:
        pass
    monitor(f"screendump {probe}")
    time.sleep(1.5)
    try:
        im = Image.open(probe).convert("RGB").resize((160, 100))
    except Exception:
        return False
    px = list(im.getdata())
    dark = sum(1 for r, g, b in px if abs(r - 10) < 8 and abs(g - 14) < 8 and abs(b - 20) < 8)
    return dark / len(px) > 0.45


def tour_install(sc, cap, work):
    time.sleep(4)
    sc.start("boot-menu", "BOOT MENU", "null os 1.2.0 / live usb")
    time.sleep(3)
    key("ret")
    time.sleep(5)
    sc.start("startup", "GLITCH STARTUP", "booting the live usb", speed=1.8)
    time.sleep(12)
    sc.end()
    log("waiting for the live desktop")
    cap.paused = True
    time.sleep(95)

    # Off camera: preselect "erase disk" and fill in the names, so the
    # keyboard-driven run is predictable (people choose these themselves)
    key("ctrl-alt-t")
    time.sleep(5)
    type_text("printf 'efiSystemPartition: /boot/efi\\ninitialPartitioningChoice: erase\\ninitialSwapChoice: small\\n"
              "defaultFileSystemType: ext4\\n' | sudo tee /etc/calamares/modules/partition.conf; "
              "printf 'presets:\\n  fullName:\\n    value: Null User\\n    editable: true\\n  loginName:\\n"
              "    value: null\\n    editable: true\\n' | sudo tee -a /etc/calamares/modules/users.conf; clear\n")
    time.sleep(3)
    key("meta_l-d")          # show the desktop for the shot
    time.sleep(2)
    cap.paused = False
    sc.start("desktop", "LIVE DESKTOP", "try it, then install null os", speed=1.0)
    time.sleep(3)
    key("meta_l-d")
    time.sleep(1)
    type_text("sudo -E calamares > /tmp/calamares.log 2>&1 &\n")
    sc.start("welcome", "THE INSTALLER", "calamares, in null os colors", speed=1.4)
    time.sleep(16)
    step(work, "1-welcome")
    key("alt-n")
    sc.start("location", "LOCATION + KEYBOARD", "", speed=1.6)
    time.sleep(5)
    step(work, "2-location")
    key("alt-n")
    time.sleep(4)
    step(work, "3-keyboard")
    key("alt-n")
    sc.start("partitions", "PARTITIONS", "erase disk, ext4", speed=1.4)
    time.sleep(6)
    step(work, "4-partitions")
    key("alt-n")
    sc.start("users", "YOUR ACCOUNT", "name, login, password", speed=1.4)
    time.sleep(4)
    for _ in range(3):
        key("tab")
    type_text("Tr0ub4dor-Lab-77")
    key("tab")
    type_text("Tr0ub4dor-Lab-77")
    time.sleep(2)
    step(work, "5-users")
    key("alt-n")
    sc.start("apps", "MINIMAL OR FULL", "tick null os full for everything; minimal here", speed=1.0)
    time.sleep(6)
    step(work, "6-apps")
    key("alt-n")
    sc.start("summary", "SUMMARY", "last look before it writes the disk", speed=1.2)
    time.sleep(5)
    step(work, "7-summary")
    key("alt-i")
    sc.start("install", "INSTALLING", "copying null os to the disk", speed=24)
    # Wait for the finished page: its background is the Neon Lab #0a0e14
    for i in range(80):                       # up to ~13 min
        time.sleep(10)
        if i % 6 == 0:
            step(work, f"8-install-{i:02d}")
        if i >= 6 and finished_page():
            log(f"finished page after ~{(i + 1) * 10} s")
            break
    sc.start("finished", "ALL DONE", "packet says hi", speed=1.0)
    time.sleep(8)
    step(work, "9-finished")
    # Close the installer (Done), then restart from the terminal behind it
    key("alt-d")
    time.sleep(3)
    type_text("sudo reboot\n")
    sc.start("reboot", "FIRST BOOT", "from the disk", speed=2.5)
    time.sleep(70)
    step(work, "10-login")
    sc.start("login", "LOG IN", "the account you just made", speed=1.2)
    type_text("Tr0ub4dor-Lab-77\n")
    time.sleep(20)
    sc.start("installed", "NULL OS, INSTALLED", "minimal: just the desktop", speed=1.0)
    time.sleep(6)
    step(work, "11-desktop")
    sc.end()


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
    kind_file = os.path.join(work, "kind.txt")
    kind = open(kind_file).read().strip() if os.path.exists(kind_file) else "demo"
    tagline = "installing null os 1.2.0" if kind == "install" else "debian based // neon lab // v1.2.0"
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
                 f"drawtext=fontfile='{fsub}':text='{tagline}':fontsize=34:fontcolor=0x00e5ff:"
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

    if kind != "install":               # the install video ends on the installed desktop
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
    if len(sys.argv) in (4, 5) and sys.argv[1] == "record":
        try:
            record(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) == 5 else "demo")
        except BaseException as e:
            print(f"::error title=record-failed::{e!r}"[:900], flush=True)
            raise
    elif len(sys.argv) == 4 and sys.argv[1] == "edit":
        edit(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
