#!/usr/bin/env python3
"""Shared fast red-tint library for SkynetRedBlack (v1.0.45).

One canonical implementation of the theme's two tint mappings, used by
retint-new-icons.py, fix-mini-icons.py, tint-breeze.py and
scan-all-icons.py (which previously carried four near-identical copies
of the same regex + per-pixel loops):

  dark (apps/folders/preferences): luminance -> 40..140, G=B=0
      R' = 40 + lum*100/255,  lum = 0.299R + 0.587G + 0.114B
  bright (widgets/tray/status): solid #ff0000

PNG tinting uses PIL's C-level operations instead of a Python
per-pixel loop (~50-100x faster on large icons):
  dark   = convert("L")  (PIL uses the same 601-2 luma weights)
           -> 256-entry point() LUT -> merge with black G/B
  bright = solid #ff0000 (every visible pixel; widget/tray convention)
Fully transparent pixels keep their original RGB (old loops skipped
alpha==0 pixels); partial-alpha pixels are tinted like the old code.
"""
import pathlib
import re

from PIL import Image, ImageChops

DARK_MAX = 140  # top of the theme's dark-red app-icon range


def dark_rgb(r, g, b):
    lum = int(0.299 * r + 0.587 * g + 0.114 * b)
    return (40 + int(lum * 100 / 255), 0, 0)


# 256-entry LUT matching dark_rgb()'s R output for every luma value.
_DARK_LUT = [40 + int(i * 100 / 255) for i in range(256)]


def tint_svg(txt, bright=False):
    """Replace every colour token in an SVG with its red variant.

    Handles #RGB/#RGBA/#RRGGBB/#RRGGBBAA (alpha preserved),
    rgb()/rgba() and currentColor (symbolic silhouettes).
    Pure black (0,0,0) is kept as-is.
    """
    txt = txt.replace("currentColor", "#ff0000" if bright else "#8c0000")

    def repl(m):
        h = m.group(1)
        if len(h) in (3, 4):
            r, g, b = (int(c * 2, 16) for c in h[:3])
            alpha = h[3] * 2 if len(h) == 4 else ""
        elif len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            alpha = ""
        elif len(h) == 8:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            alpha = h[6:8]
        else:
            return m.group(0)
        if max(r, g, b) == 0:
            return m.group(0)
        if bright:
            return "#ff0000" + alpha
        nr, ng, nb = dark_rgb(r, g, b)
        return f"#{nr:02x}{ng:02x}{nb:02x}" + alpha

    txt = re.sub(r"#([0-9a-fA-F]{3,8})\b", repl, txt)

    def rgb_repl(m):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if max(r, g, b) == 0:
            return m.group(0)
        if bright:
            return (f"rgba(255,0,0,{m.group(4)})" if m.group(4)
                    else "rgb(255,0,0)")
        nr, ng, nb = dark_rgb(r, g, b)
        return (f"rgba({nr},{ng},{nb},{m.group(4)})" if m.group(4)
                else f"rgb({nr},{ng},{nb})")

    return re.sub(
        r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})"
        r"\s*(?:,\s*([\d.]+)\s*)?\)", rgb_repl, txt)


def tint_png_image(im, bright=False):
    """Return a tinted copy of an RGBA PIL image (C-speed, no pixels loop)."""
    im = im.convert("RGBA")
    r, g, b, a = im.split()
    if bright:
        red = Image.new("L", im.size, 255)  # solid #ff0000 silhouette
    else:
        red = im.convert("L").point(_DARK_LUT)
    black = Image.new("L", im.size, 0)
    tinted = Image.merge("RGBA", (red, black, black, a))
    # Keep fully-transparent pixels' original RGB (old loops skipped
    # alpha==0); tint everything with any visibility. composite() blends
    # by mask value, so threshold the alpha to 0/255 first — a partial
    # alpha must still get the fully-tinted RGB, like the old loops.
    mask = a.point(lambda v: 255 if v > 0 else 0)
    return Image.composite(tinted, im, mask)


def tint_png_file(src, bright=False, max_size=512):
    """Open src, downscale to max_size, tint, return the PIL image."""
    im = Image.open(src).convert("RGBA")
    if max(im.size) > max_size:
        im.thumbnail((max_size, max_size))
    return tint_png_image(im, bright=bright)


def write_tinted_png(src, dst, bright=False):
    """Tint PNG file src and write it to dst (creating parent dirs)."""
    dst = pathlib.Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tint_png_file(src, bright=bright).save(dst)


def write_tinted_svg(src, dst, bright=False):
    """Tint SVG file src and write it to dst (creating parent dirs)."""
    dst = pathlib.Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(tint_svg(pathlib.Path(src).read_text(errors="ignore"),
                            bright=bright))
