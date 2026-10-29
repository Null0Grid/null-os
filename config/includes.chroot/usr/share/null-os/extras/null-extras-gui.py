#!/usr/bin/env python3
"""Null OS Extras: add the Full package, group by group (Ubuntu-style).

The groups, repos and install steps all live in /usr/local/bin/null-extras;
this window only picks groups and shows progress. Options (for tests):
  --select a,b,c   preselect groups      --start   begin installing at once
"""
import argparse
import os
import subprocess
import sys

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QPlainTextEdit, QProgressBar, QPushButton,
                             QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

BACKEND = os.environ.get("NULL_EXTRAS_BIN", "/usr/local/bin/null-extras")

# Theme icon per group (first one the icon theme has wins)
ICONS = {
    "apps": ["applications-multimedia", "vlc"],
    "appstore": ["plasmadiscover", "system-software-install"],
    "vscodium": ["vscodium", "codium", "applications-development"],
    "remote": ["org.remmina.Remmina", "preferences-desktop-remote-desktop", "krdc"],
    "network": ["org.wireshark.Wireshark", "network-wired", "network-workgroup"],
    "firewall": ["security-high", "firewall-config", "preferences-system-firewall"],
    "office": ["libreoffice-startcenter", "applications-office"],
    "containers": ["docker", "application-x-executable", "package-x-generic"],
    "qemu": ["virt-manager", "computer", "preferences-system"],
    "virtualbox": ["virtualbox", "computer"],
    "vscode": ["vscode", "com.visualstudio.code", "applications-development"],
    "claude": ["claude-desktop", "claude", "im-user", "dialog-messages"],
    "null-play": ["null-play", "applications-games", "input-gaming"],
    "homelab": ["network-server", "server-database", "applications-system"],
    "programming": ["utilities-terminal", "text-x-script", "applications-development"],
}

# Neon Lab
CYAN, PINK, GREEN = "#00e5ff", "#ff2e88", "#3dff7a"
QSS = f"""
QWidget {{ background: #0a0e14; color: #d7e2ee; font-family: Inter, "Noto Sans", sans-serif; font-size: 10.5pt; }}
#title {{ font-family: Silkscreen; font-size: 19pt; color: #ffffff; letter-spacing: 2px; }}
#subtitle, #muted {{ color: #7f8fa6; }}
#mono {{ font-family: VT323, monospace; font-size: 14pt; color: {CYAN}; }}
QFrame#card, QFrame#mode {{ background: #111823; border: 1px solid #1f2a37; border-radius: 12px; }}
QFrame#card:hover, QFrame#mode:hover {{ border-color: #2e4256; }}
QFrame#card[checked="true"], QFrame#mode[checked="true"] {{ border: 2px solid {CYAN}; background: #0f1d26; }}
QFrame#card[installed="true"] {{ background: #0d131b; border-color: #18222e; }}
#cardTitle {{ font-weight: 600; font-size: 11pt; color: #ffffff; background: transparent; }}
#cardDesc {{ color: #93a3b8; background: transparent; }}
#badge {{ color: {GREEN}; font-family: Silkscreen; font-size: 7.5pt; background: transparent; }}
#modeTitle {{ font-family: Silkscreen; font-size: 12pt; color: #ffffff; background: transparent; }}
QLabel {{ background: transparent; }}
QCheckBox {{ background: transparent; }}
QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 6px; border: 2px solid #3a4b5e; background: #0a0e14; }}
QCheckBox::indicator:checked {{ background: {CYAN}; border-color: {CYAN}; }}
QCheckBox::indicator:disabled {{ border-color: #1f2a37; background: #18222e; }}
QPushButton {{ background: #151e2a; border: 1px solid #263547; border-radius: 9px; padding: 9px 22px; color: #d7e2ee; }}
QPushButton:hover {{ border-color: {CYAN}; }}
QPushButton#primary {{ background: {CYAN}; color: #001218; border: none; font-weight: 700; }}
QPushButton#primary:hover {{ background: #5ff0ff; }}
QPushButton#primary:disabled {{ background: #1f2a37; color: #5b6b7f; }}
QPushButton#link {{ background: transparent; border: none; color: {CYAN}; padding: 4px 0; text-align: left; }}
QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: #263547; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QProgressBar {{ background: #111823; border: 1px solid #1f2a37; border-radius: 8px; height: 16px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {CYAN}, stop:1 {PINK}); border-radius: 7px; }}
QPlainTextEdit {{ background: #070a0f; border: 1px solid #1f2a37; border-radius: 8px; font-family: "Null Mono", "JetBrains Mono", monospace; font-size: 9pt; color: #9fb0c3; }}
"""


def theme_icon(names):
    for n in names:
        ic = QIcon.fromTheme(n)
        if not ic.isNull():
            return ic
    return QIcon.fromTheme("package-x-generic")


def load_groups():
    out = subprocess.run([BACKEND, "list", "--tsv"], capture_output=True, text=True, check=False).stdout
    groups = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 4:
            groups.append({"id": parts[0], "title": parts[1], "desc": parts[2], "installed": parts[3] == "1"})
    return groups


def repolish(w):
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


class ClickFrame(QFrame):
    clicked = pyqtSignal()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(e)


class ModeCard(ClickFrame):
    def __init__(self, title, text, icon):
        super().__init__()
        self.setObjectName("mode")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(14)
        ic = QLabel()
        ic.setPixmap(theme_icon(icon).pixmap(36, 36))
        lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(4)
        t = QLabel(title)
        t.setObjectName("modeTitle")
        d = QLabel(text)
        d.setObjectName("cardDesc")
        d.setWordWrap(True)
        col.addWidget(t)
        col.addWidget(d)
        lay.addLayout(col, 1)

    def set_checked(self, on):
        self.setProperty("checked", "true" if on else "false")
        repolish(self)


class GroupCard(ClickFrame):
    toggled = pyqtSignal()

    def __init__(self, g):
        super().__init__()
        self.g = g
        self.setObjectName("card")
        self.setProperty("installed", "true" if g["installed"] else "false")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)
        ic = QLabel()
        ic.setPixmap(theme_icon(ICONS.get(g["id"], [])).pixmap(34, 34))
        lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        top = QHBoxLayout()
        t = QLabel(g["title"])
        t.setObjectName("cardTitle")
        top.addWidget(t)
        if g["installed"]:
            b = QLabel("INSTALLED")
            b.setObjectName("badge")
            top.addWidget(b)
        top.addStretch(1)
        col.addLayout(top)
        d = QLabel(g["desc"])
        d.setObjectName("cardDesc")
        d.setWordWrap(True)
        col.addWidget(d)
        lay.addLayout(col, 1)
        self.box = QCheckBox()
        self.box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lay.addWidget(self.box, 0, Qt.AlignmentFlag.AlignVCenter)
        if g["installed"]:
            self.box.setChecked(True)
            self.box.setEnabled(False)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.clicked.connect(lambda: self.box.setChecked(not self.box.isChecked()))
        self.box.toggled.connect(self._changed)

    def _changed(self):
        self.setProperty("checked", "true" if (self.box.isChecked() and not self.g["installed"]) else "false")
        repolish(self)
        self.toggled.emit()

    def selected(self):
        return self.box.isChecked() and not self.g["installed"]


class Extras(QWidget):
    def __init__(self, preselect=(), start=False):
        super().__init__()
        self.setWindowTitle("Null OS Extras")
        self.setWindowIcon(QIcon.fromTheme("null-os"))
        self.resize(940, 720)
        self.proc = None
        self.failed = []
        self.buf = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(16)

        head = QHBoxLayout()
        head.setSpacing(14)
        logo = QLabel()
        logo.setPixmap(QIcon.fromTheme("null-os").pixmap(48, 48))
        head.addWidget(logo)
        hcol = QVBoxLayout()
        hcol.setSpacing(2)
        title = QLabel("NULL OS EXTRAS")
        title.setObjectName("title")
        self.subtitle = QLabel("Choose what to add to your system. Everything downloads from the internet.")
        self.subtitle.setObjectName("subtitle")
        hcol.addWidget(title)
        hcol.addWidget(self.subtitle)
        head.addLayout(hcol, 1)
        root.addLayout(head)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.stack.addWidget(self._pick_page())
        self.stack.addWidget(self._progress_page())
        self.stack.addWidget(self._done_page())

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self._escape)

        for c in self.cards:
            if c.g["id"] in preselect:
                c.box.setChecked(True)
        if not preselect:
            self._set_mode("full")
        self._update()
        if start:
            QTimer.singleShot(1500, self._install)

    # ---- page 1: pick ----
    def _pick_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        modes = QHBoxLayout()
        modes.setSpacing(14)
        self.mode_full = ModeCard("FULL", "Everything below: apps, app store, network and dev tools, homelab, office, Claude and NULL // PLAY.", ["null-os", "starred"])
        self.mode_pick = ModeCard("PICK APPS", "Choose just the groups you want. Add the rest any time from this app.", ["checkbox", "view-list-details"])
        self.mode_full.clicked.connect(lambda: self._set_mode("full"))
        self.mode_pick.clicked.connect(lambda: self._set_mode("pick"))
        modes.addWidget(self.mode_full)
        modes.addWidget(self.mode_pick)
        lay.addLayout(modes)

        self.groups = load_groups()
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 6, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        self.cards = []
        for i, g in enumerate(self.groups):
            c = GroupCard(g)
            c.toggled.connect(self._card_toggled)
            grid.addWidget(c, i // 2, i % 2)
            self.cards.append(c)
        grid.setRowStretch(len(self.groups) // 2 + 1, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(grid_host)
        lay.addWidget(scroll, 1)

        foot = QHBoxLayout()
        self.count = QLabel()
        self.count.setObjectName("mono")
        foot.addWidget(self.count, 1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.close)
        self.install_btn = QPushButton("Install")
        self.install_btn.setObjectName("primary")
        self.install_btn.clicked.connect(self._install)
        foot.addWidget(cancel)
        foot.addWidget(self.install_btn)
        lay.addLayout(foot)
        return page

    def _set_mode(self, mode):
        self._setting_mode = True
        if mode == "full":
            for c in self.cards:
                if not c.g["installed"]:
                    c.box.setChecked(True)
        self._setting_mode = False
        self.mode = mode
        self.mode_full.set_checked(mode == "full")
        self.mode_pick.set_checked(mode == "pick")
        self._update()

    def _card_toggled(self):
        if getattr(self, "_setting_mode", False):
            return
        todo = [c for c in self.cards if not c.g["installed"]]
        full = bool(todo) and all(c.box.isChecked() for c in todo)
        self.mode = "full" if full else "pick"
        self.mode_full.set_checked(full)
        self.mode_pick.set_checked(not full)
        self._update()

    def _update(self):
        n = sum(c.selected() for c in self.cards)
        have = sum(c.g["installed"] for c in self.cards)
        self.count.setText(f"> {n} selected" + (f"  ·  {have} already installed" if have else ""))
        self.install_btn.setEnabled(n > 0)
        self.install_btn.setText(f"Install {n}" if n else "Install")

    # ---- page 2: progress ----
    def _progress_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 30, 0, 0)
        lay.setSpacing(12)
        self.p_title = QLabel("INSTALLING")
        self.p_title.setObjectName("modeTitle")
        self.p_step = QLabel("Starting…")
        self.p_step.setObjectName("cardTitle")
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.p_status = QLabel("")
        self.p_status.setObjectName("muted")
        self.p_status.setWordWrap(True)
        self.details_btn = QPushButton("▸ Show details")
        self.details_btn.setObjectName("link")
        self.details_btn.clicked.connect(self._toggle_details)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(4000)
        self.log.hide()
        self.queue = QFrame()
        self.queue.setObjectName("card")
        self.queue_lay = QVBoxLayout(self.queue)
        self.queue_lay.setContentsMargins(16, 12, 16, 12)
        self.queue_lay.setSpacing(6)
        self.progress_lay = lay
        for w in (self.p_title, self.p_step, self.bar, self.p_status, self.queue, self.details_btn, self.log):
            lay.addWidget(w)
        lay.addStretch(1)
        return page

    QUEUE_STYLE = {"wait": ("·", "#5b6b7f"), "now": ("▸", CYAN), "ok": ("✓", GREEN), "fail": ("✗", PINK)}

    def _queue_set(self, gid, state):
        row = self.rows.get(gid)
        if not row:
            return
        mark, color = self.QUEUE_STYLE[state]
        row[0].setText(mark)
        row[0].setStyleSheet(f"color: {color}; font-size: 13pt; font-weight: 700;")
        row[1].setStyleSheet(f"color: {'#ffffff' if state == 'now' else '#c4d0dd' if state != 'wait' else '#7f8fa6'};")
        row[2] = state

    def _toggle_details(self):
        show = not self.log.isVisible()
        self.log.setVisible(show)
        self.details_btn.setText(("▾ Hide" if show else "▸ Show") + " details")

    # ---- page 3: done ----
    def _done_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 40, 0, 0)
        lay.setSpacing(12)
        self.d_icon = QLabel()
        self.d_title = QLabel()
        self.d_title.setObjectName("title")
        self.d_text = QLabel()
        self.d_text.setObjectName("cardDesc")
        self.d_text.setWordWrap(True)
        row = QHBoxLayout()
        row.addStretch(1)
        close = QPushButton("Close")
        close.setObjectName("primary")
        close.clicked.connect(self.close)
        row.addWidget(close)
        for w in (self.d_icon, self.d_title, self.d_text):
            lay.addWidget(w)
        lay.addStretch(1)
        lay.addLayout(row)
        return page

    # ---- install ----
    def _install(self):
        ids = [c.g["id"] for c in self.cards if c.selected()]
        if not ids:
            return
        self.titles = {c.g["id"]: c.g["title"] for c in self.cards}
        self.total = len(ids)
        self.step = 0
        self.failed = []
        self.order = ids
        self.rows = {}
        for gid in ids:
            line = QHBoxLayout()
            mark, name = QLabel(), QLabel(self.titles[gid])
            mark.setFixedWidth(22)
            line.addWidget(mark)
            line.addWidget(name, 1)
            self.queue_lay.addLayout(line)
            self.rows[gid] = [mark, name, "wait"]
            self._queue_set(gid, "wait")
        self.stack.setCurrentIndex(1)
        self.subtitle.setText("Installing " + ", ".join(self.titles[i] for i in ids) + ".")
        # live session / sudo without a password: run directly; otherwise ask via polkit
        quiet = subprocess.run(["sudo", "-n", "true"], capture_output=True, check=False).returncode == 0
        cmd = ["sudo", "-n", BACKEND, "install", *ids] if quiet else ["pkexec", BACKEND, "install", *ids]
        env = QProcessEnvironment.systemEnvironment()
        env.insert("NULL_EXTRAS_PROGRESS", "1")
        self.proc = QProcess(self)
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._finished)
        self.buf = ""
        self.proc.start(cmd[0], cmd[1:])

    def _read(self):
        self.buf += bytes(self.proc.readAllStandardOutput()).decode(errors="replace")
        *lines, self.buf = self.buf.split("\n")
        for line in lines:
            self._line(line.rstrip("\r"))

    def _set_progress(self, within):
        frac = (max(self.step - 1, 0) + within) / max(self.total, 1) if self.step else 0.02 * within
        self.bar.setValue(int(1000 * min(frac, 1.0)))

    def _line(self, line):
        if line.startswith("@@STEP "):
            _, n, total, title = line.split(" ", 3)
            self.step, self.total = int(n), int(total)
            if self.step and self.step <= len(self.order):
                for gid in self.order[:self.step - 1]:
                    if self.rows[gid][2] in ("wait", "now"):
                        self._queue_set(gid, "ok")
                self._queue_set(self.order[self.step - 1], "now")
            self.p_step.setText(f"{title}  ({n} of {total})" if self.step else title)
            self._set_progress(0)
            return
        if line.startswith("@@FAIL "):
            gid = line.split(" ", 1)[1]
            self.failed.append(self.titles.get(gid, gid))
            self._queue_set(gid, "fail")
            return
        if line.startswith("@@OK "):
            self._queue_set(line.split(" ", 1)[1], "ok")
            self._set_progress(1)
            return
        if line.startswith(("pmstatus:", "dlstatus:")):
            parts = line.split(":", 3)
            if len(parts) == 4:
                try:
                    pct = float(parts[2])
                except ValueError:
                    pct = 0
                # downloads count as the first half of a group, unpacking/setup the second
                within = pct / 200 if parts[0] == "dlstatus" else 0.5 + pct / 200
                self._set_progress(within)
                self.p_status.setText(parts[3])
            return
        if line:
            self.log.appendPlainText(line)

    def _finished(self, code, _status):
        if self.proc:
            self._read()
        if self.buf:
            self._line(self.buf)
        if code == 0:
            for gid, row in getattr(self, "rows", {}).items():
                if row[2] in ("wait", "now"):
                    self._queue_set(gid, "ok")
        self.stack.widget(2).layout().insertWidget(3, self.queue)
        self.stack.setCurrentIndex(2)
        if code in (126, 127) and not self.failed:
            self.d_icon.setPixmap(QIcon.fromTheme("dialog-cancel").pixmap(56, 56))
            self.d_title.setText("CANCELLED")
            self.d_text.setText("Nothing was installed (the password prompt was closed).")
        elif self.failed or code != 0:
            self.d_icon.setPixmap(QIcon.fromTheme("dialog-warning").pixmap(56, 56))
            self.d_title.setText("ALMOST")
            names = ", ".join(self.failed) or "some packages"
            self.d_text.setText(f"These didn't install: {names}. Check your internet connection and try them again; "
                                "the details log says what went wrong.")
            self.stack.widget(2).layout().insertWidget(4, self.log)
            self.log.show()
        else:
            self.d_icon.setPixmap(QIcon.fromTheme("dialog-ok-apply").pixmap(56, 56))
            self.d_title.setText("ALL SET")
            self.d_text.setText("Your apps are in the start menu. Log out and back in once so Docker, VMs and "
                                "packet capture work without sudo.")
        self.subtitle.setText("Add more any time from this app.")

    def _escape(self):
        if self.stack.currentIndex() != 1:
            self.close()

    def closeEvent(self, e):
        if self.proc and self.proc.state() != QProcess.ProcessState.NotRunning:
            e.ignore()   # don't leave apt half done
            return
        super().closeEvent(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--select", default="")
    ap.add_argument("--start", action="store_true")
    args = ap.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Null OS Extras")
    app.setDesktopFileName("null-extras")
    app.setStyleSheet(QSS)
    f = QFont("Inter")
    f.setPointSizeF(10.5)
    app.setFont(f)
    w = Extras([s for s in args.select.split(",") if s], args.start)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
