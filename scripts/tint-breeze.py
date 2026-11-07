#!/usr/bin/env python3
"""v1.0.33: tint the whole Breeze icon set into SkynetRedBlack.
Previously, any icon not already in the theme fell back to Breeze original
colours (blue folders, grey/bright icons at large sizes). Now every
Breeze icon missing from the theme is tinted and bundled:
  - actions + symbolic icons -> bright red #ff0000 (theme convention, v1.0.13)
  - everything else          -> dark red (luminance -> 40-140, G=B=0)
Breeze layout is <context>/<size>/ (plus @2x/@3x HiDPI, skipped); the
theme layout is <size>/<context>/. Symlinks are resolved to real files.
Existing theme icons are never overwritten. Idempotent.
Also completes index.theme with any missing size/context sections.
"""
import pathlib, re, subprocess, sys
try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import redtint as _redtint
except ImportError:
    _redtint = None

HOME = pathlib.Path.home()
OUT = HOME / ".local/share/icons/SkynetRedBlack"
BREEZE = pathlib.Path("/usr/share/icons/breeze")
SIZES = {"16", "22", "24", "32", "48", "64", "96", "128", "256", "512"}
BRIGHT_CONTEXTS = {"actions"}

def dark_rgb(r, g, b):
    lum = int(0.299 * r + 0.587 * g + 0.114 * b)
    return (40 + int(lum * 100 / 255), 0, 0)

def tint(txt, bright):
    magenta = "#ff0000" if bright else "#8c0000"
    txt = txt.replace("currentColor", magenta)
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
        return f"#{nr:02x}0000" + alpha
    txt = re.sub(r"#([0-9a-fA-F]{3,8})\b", repl, txt)
    def rgb_repl(m):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if max(r, g, b) == 0:
            return m.group(0)
        if bright:
            return (f"rgba(255,0,0,{m.group(4)})" if m.group(4) else "rgb(255,0,0)")
        nr, ng, nb = dark_rgb(r, g, b)
        return f"rgba({nr},{ng},{nb},{m.group(4)})" if m.group(4) else f"rgb({nr},{ng},{nb})"
    return re.sub(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([\d.]+)\s*)?\)", rgb_repl, txt)

added = skipped = 0
new_dirs = set()
for ctx_dir in sorted(BREEZE.iterdir()):
    if not ctx_dir.is_dir() or ctx_dir.name.startswith("."):
        continue
    ctx = ctx_dir.name
    # symbolic/ handled as its own context
    for size_dir in sorted(ctx_dir.iterdir()):
        if not size_dir.is_dir():
            continue
        size = size_dir.name
        if size not in SIZES:
            continue  # skips @2x/@3x and anything else
        bright = ctx in BRIGHT_CONTEXTS
        for src in sorted(size_dir.glob("*.svg")):
            name = src.name
            if "-symbolic" in name:
                bright = True
            # v1.0.46: SVGs ship lean (16/22/scalable — the loader
            # scales them), matching the slim release tarball; writing
            # all 9 sizes regrew the theme tarball ~11x.
            dst = OUT / size / ctx / name
            lean_dsts = [OUT / d / ctx / name for d in ("16", "22", "scalable")]
            if dst.exists() or any(d.exists() for d in lean_dsts):
                skipped += 1
                continue
            try:
                txt = src.read_text(errors="ignore")  # follows symlinks
            except Exception:
                skipped += 1
                continue
            # Embedded-raster SVGs (data:image/png;base64) have no vector
            # fills to regex-tint — render to PNG, tint pixels, ship .png.
            if "data:image/" in txt[:200000]:
                try:
                    from PIL import Image as _Image
                    tmp = "/tmp/_breeze_raster.png"
                    subprocess.run(["rsvg-convert", "-w", "256", "-h", "256",
                                    str(src), "-o", tmp], check=True,
                                   capture_output=True)
                    if _redtint is not None:
                        dst_png = dst.with_suffix(".png")
                        _redtint.write_tinted_png(tmp, dst_png, bright=bright)
                    else:
                        im = _Image.open(tmp).convert("RGBA")
                        px = im.load()  # type: ignore[union-attr]
                        for y in range(im.height):
                            for x in range(im.width):
                                r, g, b, a = px[x, y]  # type: ignore[index]
                                if a and max(r, g, b) > 0:
                                    px[x, y] = ((255, 0, 0, a) if bright
                                                else (*dark_rgb(r, g, b), a))
                        dst_png = dst.with_suffix(".png")
                        dst_png.parent.mkdir(parents=True, exist_ok=True)
                        im.save(dst_png)
                    new_dirs.add(f"{size}/{ctx}")
                    added += 1
                except Exception:
                    skipped += 1
                continue
            tinted = tint(txt, bright)
            first = None
            for d in lean_dsts:
                d.parent.mkdir(parents=True, exist_ok=True)
                if first is None:
                    d.write_text(tinted)
                    first = d
                else:
                    import shutil as _sh
                    _sh.copy(first, d)
                new_dirs.add(f"{d.parent.name}/{ctx}")
            added += 1
print(f"tinted {added} breeze icons ({skipped} already in theme, kept)")

# complete index.theme for any new size/context combos
# Context MUST match the directory's real context — writing
# Context=Applications everywhere makes the loader skip status/
# actions/etc. dirs for tray/widget lookups entirely.
CONTEXT_MAP = {"apps": "Applications", "actions": "Actions", "status": "Status",
               "panel": "Status", "places": "Places", "devices": "Devices",
               "emblems": "Emblems", "mimetypes": "MimeTypes",
               "categories": "Categories", "preferences": "Applications",
               "applets": "Applications", "symbolic": "Status"}
idx = OUT / "index.theme"
t = idx.read_text()
for d in sorted(new_dirs):
    if d not in t:
        size = d.split("/")[0]
        ctx = CONTEXT_MAP.get(d.split("/")[1] if "/" in d else "", "Applications")
        t = t.replace("Directories=", f"Directories={d},", 1)
        t = t.rstrip() + f"\n\n[{d}]\nContext={ctx}\nSize={size}\nType=Fixed\n"
        print(f"index.theme: added [{d}] as {ctx}")
idx.write_text(t)

subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(OUT)])
print("icon cache updated - restart Dolphin/Plasma shell to see them")
