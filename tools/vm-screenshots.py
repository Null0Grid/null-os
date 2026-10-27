#!/usr/bin/env python3
"""Boot a Null OS ISO in QEMU and take screenshots of it.

Usage: vm-screenshots.py <iso> <out-dir>
Needs: qemu-system-x86_64, python3-pil. Uses KVM when /dev/kvm is usable.

Shots taken:
  01-boot-menu      ISO boot menu
  02-startup-glitch Plymouth startup, mid-glitch
  03-startup-ready  Plymouth startup, loading
  04-desktop        Plasma live desktop
  05-start-menu     start menu open
  06-terminal       Konsole: two-line prompt, null-info, a failed command
  07-root           root prompt (red frame)
  08-shutdown       Plymouth shutdown animation
"""
import os
import socket
import subprocess
import sys
import time

from PIL import Image

ISO, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
MON = "/tmp/null-qemu-monitor.sock"
KVM = os.access("/dev/kvm", os.R_OK | os.W_OK)
SLOW = 1 if KVM else 4  # TCG emulation is much slower

# Character -> QEMU sendkey name
KEYS = {" ": "spc", "-": "minus", "/": "slash", ".": "dot", "\n": "ret",
        "_": "shift-minus", "~": "shift-grave_accent", "|": "shift-backslash",
        "=": "equal", ":": "shift-semicolon", ">": "shift-dot"}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def monitor(cmd):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(MON)
        s.recv(4096)
        s.sendall((cmd + "\n").encode())
        time.sleep(0.15)
        s.recv(4096)


def key(name):
    monitor(f"sendkey {name}")
    time.sleep(0.08)


def type_text(text):
    for ch in text:
        if ch in KEYS:
            key(KEYS[ch])
        elif ch.isupper():
            key("shift-" + ch.lower())
        else:
            key(ch)


def shot(name):
    ppm = f"/tmp/{name}.ppm"
    try:
        monitor(f"screendump {ppm}")
        time.sleep(1)
        Image.open(ppm).save(os.path.join(OUT, f"{name}.png"))
        log(f"saved {name}.png")
    except Exception as e:  # VM may already be off (shutdown shot)
        log(f"could not take {name}: {e}")


def wait(seconds, why):
    log(f"waiting {seconds * SLOW}s: {why}")
    time.sleep(seconds * SLOW)


def main():
    if os.path.exists(MON):
        os.remove(MON)
    cmd = ["qemu-system-x86_64", "-m", "4096", "-smp", "2",
           "-cdrom", ISO, "-boot", "d",
           "-vga", "virtio", "-display", "none",
           "-monitor", f"unix:{MON},server,nowait",
           "-nic", "user,model=virtio-net-pci"]
    if KVM:
        cmd += ["-enable-kvm", "-cpu", "host"]
    log(f"starting QEMU (kvm={KVM})")
    vm = subprocess.Popen(cmd)
    try:
        for _ in range(50):
            if os.path.exists(MON):
                break
            time.sleep(0.2)

        wait(8, "boot menu")
        shot("01-boot-menu")
        key("ret")

        time.sleep(4 * SLOW)
        shot("02-startup-glitch")
        time.sleep(4 * SLOW)
        shot("03-startup-ready")

        wait(150, "live boot into Plasma")
        shot("04-desktop")

        key("meta_l")
        time.sleep(4)
        shot("05-start-menu")
        key("esc")
        time.sleep(2)

        key("ctrl-alt-t")
        wait(8, "Konsole to open")
        type_text("null-info\n")
        time.sleep(2)
        type_text("cd /etc\n")
        time.sleep(1)
        type_text("nope\n")
        time.sleep(2)
        shot("06-terminal")

        type_text("sudo -i\n")
        time.sleep(3)
        shot("07-root")

        type_text("poweroff\n")
        time.sleep(3)
        shot("08-shutdown")
        time.sleep(5)
    finally:
        vm.terminate()
        vm.wait(timeout=30)


if __name__ == "__main__":
    main()
