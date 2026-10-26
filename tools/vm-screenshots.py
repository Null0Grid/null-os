#!/usr/bin/env python3
"""Boot a Null OS ISO in QEMU and take screenshots of it.

Usage: vm-screenshots.py <iso> <out-dir>
Needs: qemu-system-x86_64, python3-pil. Uses KVM when /dev/kvm is usable.

Shots taken:
  01-boot-menu   ISO boot menu
  02-desktop     XFCE live desktop
  03-terminal    terminal with the two-line prompt, null-info, an error
  04-root        root prompt (red frame)
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
    monitor(f"screendump {ppm}")
    time.sleep(1)
    Image.open(ppm).save(os.path.join(OUT, f"{name}.png"))
    log(f"saved {name}.png")


def wait(seconds, why):
    log(f"waiting {seconds * SLOW}s: {why}")
    time.sleep(seconds * SLOW)


def main():
    if os.path.exists(MON):
        os.remove(MON)
    cmd = ["qemu-system-x86_64", "-m", "4096", "-smp", "2",
           "-cdrom", ISO, "-boot", "d",
           "-vga", "std", "-display", "none",
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

        wait(110, "live boot into XFCE")
        shot("02-desktop")

        key("ctrl-alt-t")
        wait(6, "terminal to open")
        type_text("null-info\n")
        time.sleep(2)
        type_text("cd /etc\n")
        time.sleep(1)
        type_text("nope\n")
        time.sleep(2)
        shot("03-terminal")

        type_text("sudo -i\n")
        time.sleep(3)
        shot("04-root")
    finally:
        vm.terminate()
        vm.wait(timeout=30)


if __name__ == "__main__":
    main()
