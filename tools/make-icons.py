#!/usr/bin/env python3
"""Build the NullLine icon theme: BeautyLine recolored to pure white.

Usage: make-icons.py <BeautyLine-dir> <output-dir>
Every colour (fills, strokes, gradient stops) becomes #ffffff; opacity
and shapes are untouched. Symlinks are kept as symlinks.
"""
import os
import re
import shutil
import sys

COLOR = r'(#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\))'
PATTERN = re.compile(r'((?:fill|stroke|stop-color|color|flood-color)\s*[:=]\s*["\']?)' + COLOR)

INDEX = """[Icon Theme]
Name=NullLine
Comment=Null OS white line icons, based on BeautyLine (GPL)
Inherits=breeze-dark,hicolor
"""


def whiten(text):
    return PATTERN.sub(r'\1#ffffff', text)


def main(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True)
    count = 0
    for root, _, files in os.walk(dst):
        for name in files:
            path = os.path.join(root, name)
            if os.path.islink(path) or not name.endswith(".svg"):
                continue
            with open(path, encoding="utf-8", errors="surrogateescape") as f:
                text = f.read()
            new = whiten(text)
            if new != text:
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
                    f.write(new)
                count += 1
    # Rewrite the theme header, keep BeautyLine's directory list
    idx = os.path.join(dst, "index.theme")
    with open(idx, encoding="utf-8") as f:
        lines = f.read().splitlines()
    out, in_header = [], False
    for line in lines:
        if line.strip() == "[Icon Theme]":
            in_header = True
            out.append(INDEX.rstrip())
            continue
        if in_header and line.split("=")[0] in ("Name", "Comment", "Inherits", "Example"):
            continue
        if line.startswith("["):
            in_header = False
        out.append(line)
    with open(idx, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    # The Null mark as the start-menu button and distro logo
    mark = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "branding", "start-here.svg")
    if os.path.exists(mark):
        apps = os.path.join(dst, "apps", "scalable")
        os.makedirs(apps, exist_ok=True)
        names = ("start-here", "start-here-symbolic", "start-here-kde", "start-here-kde-symbolic",
                     "start-here-kde-plasma", "start-here-kde-plasma-symbolic", "start-here-debian",
                     "distributor-logo", "distributor-logo-symbolic", "debian-logo", "null-os")
        # Drop BeautyLine's own versions in fixed-size dirs (panel/22 etc.),
        # which Plasma would otherwise prefer at small sizes
        for root, _, files in os.walk(dst):
            for f in files:
                if os.path.splitext(f)[0] in names and os.path.join(root, f) != os.path.join(apps, f):
                    os.remove(os.path.join(root, f))
        for name in names:
            target = os.path.join(apps, name + ".svg")
            if os.path.lexists(target):
                os.remove(target)
            shutil.copy(mark, target)
        print("NullLine: start-menu button set to the Null mark")
    cache = os.path.join(dst, "icon-theme.cache")
    if os.path.exists(cache):
        os.remove(cache)
    print(f"NullLine: recolored {count} icons into {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
