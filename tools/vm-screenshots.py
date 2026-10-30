#!/usr/bin/env python3
"""Boot a Null OS ISO in QEMU and take screenshots of it.

Usage: vm-screenshots.py <iso> <out-dir>
Needs: qemu-system-x86_64, python3-pil. Uses KVM when /dev/kvm is usable.

Shots taken:
  01-boot-menu        ISO boot menu
  02-boot-NN          every 3 s during boot (Plymouth startup animation)
  03-desktop          Plasma live desktop
  04-start-menu       start menu open
  04b-null-file       Null File, the default file manager
  05-terminal         Konsole: two-line prompt, null-info, a failed command
  05b-fastfetch       fastfetch with the Null OS logo
  05c-shortcut-offer  "Add to desktop?" notification after an app install
  05c2-show-in-folder Null File answering "Show in folder" (FileManager1 D-Bus)
  05e-installer-password  cracklib dictionary present, weak-password option on
  05f-extras-app      Null OS Extras: pick page
  05f2-extras-installing  the app installing Homelab, Network, Firewall
  05f3-extras-done    the app's summary
  05g-extras-homelab  homelab, network and firewall groups installed from the internet
  06b-lock-screen     lock screen (Super+L)
  06c-unlocked        unlocked again with the live password
  06-root             root prompt (red frame)
  07-console-prompt   text console: prompt with the @ fallback
  08-shutdown-NN      Plymouth shutdown, every 0.4 s
With NULL_VM_DEBUG=1: a root debug shell on tty9 and 9x-debug-* shots
(live user, journal, theme, shutdown splash run by hand).
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
# ARM64 ISOs boot in an emulated (or KVM) ARM "virt" machine with UEFI
ARM = os.environ.get("NULL_VM_ARCH") == "arm64" or "arm64" in os.path.basename(sys.argv[1] if len(sys.argv) > 1 else "")
# Without KVM a full desktop tour takes too long: QUICK = boot, desktop,
# start menu, terminal, fastfetch, then power off
QUICK = os.environ.get("NULL_VM_QUICK") == "1" or (ARM and not KVM)
if ARM and not KVM:
    SLOW = 6       # an emulated ARM CPU is slower still
DEBUG = os.environ.get("NULL_VM_DEBUG") == "1"  # extra root-shell diagnostics

# Character -> QEMU sendkey name
KEYS = {" ": "spc", "-": "minus", "/": "slash", ".": "dot", "\n": "ret",
        "_": "shift-minus", "~": "shift-grave_accent", "|": "shift-backslash",
        "=": "equal", ":": "shift-semicolon", ">": "shift-dot",
        ";": "semicolon", "*": "shift-8", "'": "apostrophe", ",": "comma",
        "^": "shift-6", "$": "shift-4", "!": "shift-1", "#": "shift-3",
        "&": "shift-7", "\\": "backslash", "\"": "shift-apostrophe",
        "(": "shift-9", ")": "shift-0", "[": "bracket_left", "]": "bracket_right",
        "?": "shift-slash", "<": "shift-comma", "{": "shift-bracket_left", "}": "shift-bracket_right"}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def monitor(cmd):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(10)  # never hang the job on a stuck monitor
        s.connect(MON)
        try:
            s.recv(4096)
        except socket.timeout:
            pass
        s.sendall((cmd + "\n").encode())
        time.sleep(0.15)
        try:
            s.recv(4096)
        except socket.timeout:
            log(f"monitor timeout on: {cmd}")


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
    if ARM:
        fw = next((f for f in ("/usr/share/qemu-efi-aarch64/QEMU_EFI.fd", "/usr/share/AAVMF/AAVMF_CODE.fd")
                   if os.path.exists(f)), None)
        cmd = ["qemu-system-aarch64", "-M", "virt", "-m", "4096", "-smp", str(os.cpu_count() or 4),
               "-bios", fw,
               "-device", "virtio-gpu-pci", "-display", "none",
               "-device", "qemu-xhci", "-device", "usb-kbd", "-device", "usb-tablet",
               "-device", "virtio-scsi-pci", "-drive", f"file={ISO},if=none,id=cd,media=cdrom,readonly=on",
               "-device", "scsi-cd,drive=cd",
               "-monitor", f"unix:{MON},server,nowait",
               "-nic", "user,model=virtio-net-pci"]
        cmd += ["-enable-kvm", "-cpu", "host"] if KVM else ["-cpu", "max", "-accel", "tcg,thread=multi"]
    else:
        cmd = ["qemu-system-x86_64", "-m", "4096", "-smp", "2",
               "-cdrom", ISO, "-boot", "d",
               "-vga", "virtio", "-display", "none",
               "-monitor", f"unix:{MON},server,nowait",
               "-nic", "user,model=virtio-net-pci"]
        if KVM:
            cmd += ["-enable-kvm", "-cpu", "host"]
    log(f"starting QEMU (arm={ARM}, kvm={KVM}, quick={QUICK})")
    vm = subprocess.Popen(cmd)
    try:
        for _ in range(50):
            if os.path.exists(MON):
                break
            time.sleep(0.2)

        wait(8, "boot menu")
        shot("01-boot-menu")
        if DEBUG:
            # Append a root debug shell on tty9 to the kernel line
            # (only this VM boot; the ISO is unchanged)
            key("tab")
            time.sleep(1)
            type_text(" systemd.debug-shell=1")
        key("ret")

        for n in range(12):
            time.sleep(3 * SLOW)
            shot(f"02-boot-{n:02d}")

        wait(120, "live boot into Plasma")
        shot("03-desktop")

        key("meta_l")
        time.sleep(4 * SLOW)
        shot("04-start-menu")
        if QUICK:
            key("esc")
            time.sleep(2 * SLOW)
            key("ctrl-alt-t")
            wait(10, "Konsole")
            type_text("null-info\n")
            time.sleep(4 * SLOW)
            shot("05-terminal")
            type_text("clear; fastfetch; uname -m\n")
            time.sleep(6 * SLOW)
            shot("05b-fastfetch")
            type_text("clear; null-extras list\n")
            time.sleep(4 * SLOW)
            shot("05g-extras-list")
            type_text("sudo poweroff\n")
            for n in range(6):
                time.sleep(2 * SLOW)
                shot(f"08-shutdown-{n:02d}")
            return
        key("esc")
        time.sleep(2)

        # Null File, the default file manager
        key("meta_l")
        time.sleep(2)
        type_text("null file")
        time.sleep(2)
        key("ret")
        time.sleep(8)
        shot("04b-null-file")
        key("alt-f4")
        time.sleep(2)

        key("ctrl-alt-t")
        wait(8, "Konsole to open")
        type_text("null-info\n")
        time.sleep(2)
        type_text("cd /etc\n")
        time.sleep(1)
        type_text("nope\n")
        time.sleep(2)
        shot("05-terminal")
        type_text("clear; fastfetch\n")
        time.sleep(3)
        shot("05b-fastfetch")
        # Simulate installing an app: the shortcut helper should offer it
        type_text("mkdir -p ~/.local/share/applications; cp /usr/share/applications/org.kde.konsole.desktop ~/.local/share/applications/demo-app.desktop\n")
        time.sleep(7)
        shot("05c-shortcut-offer")
        # "Show in folder": what browsers and editors ask the file manager
        type_text("clear; dbus-send --session --print-reply --dest=org.freedesktop.FileManager1 "
                  "/org/freedesktop/FileManager1 org.freedesktop.FileManager1.ShowItems "
                  "array:string:file:///etc/hostname string:; sleep 12; pkill -f null-file\n")
        time.sleep(9)
        shot("05c2-show-in-folder")
        time.sleep(6)
        # Installer password check: cracklib dictionary + weak-password option
        type_text("clear; ls /var/cache/cracklib/; grep -i weak /etc/calamares/modules/users.conf; "
                  "echo Tr0ub4dor-Lab-77 | /usr/sbin/cracklib-check; grep -A2 Daemon ~/.config/kscreenlockerrc; "
                  "perl -e 'print crypt(\"live\", $ARGV[0]) eq $ARGV[0] ? \"PASSWORD-IS-live\\n\" : \"PASSWORD-NOT-live\\n\"' "
                  "\"$(sudo getent shadow user | cut -d: -f2)\"\n")
        time.sleep(3)
        shot("05e-installer-password")
        # Null OS Extras: pick page, then the app installing three groups
        type_text("clear; null-extras gui &\n")
        time.sleep(8)
        shot("05f-extras-app")
        key("esc")
        time.sleep(2)
        type_text("clear; null-extras gui --select homelab,network,firewall --start &\n")
        time.sleep(70)
        shot("05f2-extras-installing")
        time.sleep(200)
        shot("05f3-extras-done")
        key("esc")
        time.sleep(2)
        type_text("clear; grep -E 'finished|sources-final' -A1 /etc/calamares/settings.conf; ls /etc/calamares/branding/debian/;  kubectl version --client | head -n 1; "
                  "terraform -version | head -n 1; nmap --version | head -n 1; sudo ufw status | head -n 1; null-extras list\n")
        time.sleep(8)
        shot("05g-extras-homelab")
        type_text("sudo -i\n")
        time.sleep(3)
        shot("06-root")
        type_text("exit\n")
        time.sleep(1)

        # Live password: lock the screen, unlock with "live"
        key("meta_l-l")
        time.sleep(5)
        shot("06b-lock-screen")
        key("esc")
        time.sleep(3)
        type_text("live")
        time.sleep(1)
        key("ret")
        time.sleep(5)
        shot("06c-unlocked")

        # Text console: the prompt with the @ fallback
        key("ctrl-alt-f3")
        time.sleep(4)
        type_text("null-info\n")
        time.sleep(2)
        type_text("nope\n")
        time.sleep(2)
        shot("07-console-prompt")

        if DEBUG:
            key("ctrl-alt-f9")
            time.sleep(3)
            type_text("clear; getent passwd user; id user; tail -n 15 /var/log/live/config.log\n")
            time.sleep(4)
            shot("90-debug-user")
            type_text("clear; journalctl -b --no-pager | grep -iE 'pam|login|sddm|user-setup|live-config' | tail -n 30\n")
            time.sleep(5)
            shot("91-debug-journal")
            type_text("clear; head -n 3 /etc/os-release; ls /usr/share/plasma/look-and-feel; "
                      "grep -hE 'LookAndFeel|ColorScheme|^Theme' /etc/xdg/kdeglobals /home/user/.config/kdeglobals\n")
            time.sleep(3)
            shot("92-debug-theme")
            # Shutdown splash while the system is still up
            type_text("clear; plymouthd --mode=shutdown; plymouth --show-splash; sleep 7; plymouth --quit\n")
            for n in range(14):
                time.sleep(0.4)
                shot(f"93-splash-test-{n:02d}")
            time.sleep(4)
            key("ctrl-alt-f3")
            time.sleep(1)

        type_text("sudo poweroff\n")
        for n in range(15):
            time.sleep(0.4)
            shot(f"08-shutdown-{n:02d}")
        time.sleep(5)
    finally:
        vm.terminate()
        try:
            vm.wait(timeout=30)
        except subprocess.TimeoutExpired:
            vm.kill()


if __name__ == "__main__":
    main()
