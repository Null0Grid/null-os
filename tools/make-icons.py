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
    cache = os.path.join(dst, "icon-theme.cache")
    if os.path.exists(cache):
        os.remove(cache)
    print(f"NullLine: recolored {count} icons into {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
