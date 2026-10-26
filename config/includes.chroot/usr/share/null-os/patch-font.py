#!/usr/bin/env python3
"""Build "Null Mono": JetBrains Mono plus the Null mark at U+E900.

Usage: patch-font.py <input.ttf> <output.ttf>
Works on static and variable TTFs. Run at image build time.
"""
import os
import sys

from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util

spec = importlib.util.spec_from_file_location(
    "null_mark", os.path.join(os.path.dirname(os.path.abspath(__file__)), "null-mark.py"))
mark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mark)

NEW_FAMILY = "Null Mono"


def patch(src, dst):
    font = TTFont(src)
    # Decompile glyph-indexed tables before the glyph order changes.
    for t in ("glyf", "hmtx", "gvar", "cmap"):
        if t in font:
            font[t]
    adv = font["hmtx"]["zero"][0] if "zero" in font["hmtx"].metrics else font["hmtx"].metrics[font.getGlyphOrder()[1]][0]

    # Scale the 600-unit design to this font's cell width.
    s = adv / mark.CELL_W
    ttpen = TTGlyphPen(None)
    pen = Cu2QuPen(TransformPen(ttpen, (s, 0, 0, s, 0, 0)), max_err=1.0, reverse_direction=False)
    mark.draw(pen)
    glyph = ttpen.glyph()

    name = mark.GLYPH_NAME
    order = font.getGlyphOrder()
    if name not in order:
        order.append(name)
        font.setGlyphOrder(order)
    font["glyf"][name] = glyph
    glyph.recalcBounds(font["glyf"])
    font["hmtx"][name] = (adv, glyph.xMin)
    for table in font["cmap"].tables:
        if table.isUnicode():
            table.cmap[mark.CODEPOINT] = name

    # Variable fonts: the mark doesn't vary, and drop optional tables that
    # would need per-glyph entries.
    if "gvar" in font:
        font["gvar"].variations[name] = []
    for t in ("HVAR", "VVAR", "hdmx", "LTSH", "DSIG"):
        if t in font:
            del font[t]
    font["maxp"].numGlyphs = len(order)

    # Rename the family so it never clashes with the stock font.
    for rec in font["name"].names:
        text = rec.toUnicode()
        if "JetBrains Mono" in text:
            rec.string = text.replace("JetBrains Mono", NEW_FAMILY)
        elif "JetBrainsMono" in text:
            rec.string = text.replace("JetBrainsMono", NEW_FAMILY.replace(" ", ""))
    font.save(dst)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    patch(sys.argv[1], sys.argv[2])
    print(f"wrote {sys.argv[2]}")
