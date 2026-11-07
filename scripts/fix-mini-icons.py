#!/usr/bin/env python3
"""v1.0.31: tint mini (titlebar) app icons to the theme's dark red.
KWin window titlebar icons (upper-left, 16px) are looked up by app-ID /
desktop-file basename (org.kde.konsole, brave-browser, gimp, ...), many of
which were NOT in SkynetRedBlack, so they fell back to Tela-red-dark /
Breeze originals (grey Konsole, bright Brave, ...), mismatching the dark
red large icons. This finds every desktop Icon= name + app-ID alias that
is missing from the theme's apps dirs, tints its source icon with the
theme mapping (luminance -> 40-140, G=B=0, same as retint-new-icons.py),
and writes it in all sizes. Idempotent: existing icons are left alone.
"""
import pathlib, re, shutil, subprocess, sys
try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import redtint as _redtint
except ImportError:
    _redtint = None
from PIL import Image

HOME = pathlib.Path.home()
OUT = HOME / ".local/share/icons/SkynetRedBlack"
STD_DIRS = ["16/apps", "22/apps", "24/apps", "32/apps", "48/apps", "64/apps", "128/apps", "256/apps", "scalable/apps"]
ROOTS = [
    OUT,  # theme's own icons as source for aliases (e.g. DaVinciResolve -> davinci-resolve)
    pathlib.Path("/usr/share/icons/Tela-red-dark"),
    pathlib.Path("/usr/share/icons/Tela"),
    pathlib.Path("/usr/share/icons/breeze"),
    pathlib.Path("/usr/share/icons/breeze-dark"),
    pathlib.Path("/usr/share/icons/hicolor"),
    pathlib.Path("/usr/share/icons/Papirus"),
    pathlib.Path("/usr/share/icons/Papirus-Dark"),
    pathlib.Path("/usr/share/icons/char-white"),
    HOME / ".local/share/icons/YAMIS",
    pathlib.Path("/usr/share/pixmaps"),
    pathlib.Path("/var/lib/flatpak/exports/share/icons/hicolor"),
    HOME / ".local/share/icons/hicolor",
]

def dark_rgb(r, g, b):
    lum = int(0.299 * r + 0.587 * g + 0.114 * b)
    return (40 + int(lum * 100 / 255), 0, 0)

def tint_svg(txt, bright=False):
    """Handle EVERY hex form (#RGB/#RGBA/#RRGGBB/#RRGGBBAA, alpha kept)
    plus rgb()/rgba() and currentColor (symbolic silhouettes)."""
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

def tint_png(src, name):
    if _redtint is not None:
        first = None
        for d in STD_DIRS:
            dst = OUT / d / name
            if first is None:
                _redtint.write_tinted_png(src, dst, bright=False)
                first = dst
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(first, dst)
        return
    im = Image.open(src).convert("RGBA")
    if max(im.size) > 512:
        im.thumbnail((512, 512))
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a and max(r, g, b) > 0:
                px[x, y] = (*dark_rgb(r, g, b), a)
    first = None
    for d in STD_DIRS:
        dst = OUT / d / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if first is None:
            im.save(dst)
            first = dst
        else:
            shutil.copy(first, dst)

def tint_svg_file(src, name):
    txt = tint_svg(src.read_text(errors="ignore"))
    first = None
    # v1.0.46: SVGs ship lean (16/22/scalable — the loader scales
    # them), matching the slim release tarball.
    for d in ["16/apps", "22/apps", "scalable/apps"]:
        dst = OUT / d / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if first is None:
            dst.write_text(txt)
            first = dst
        else:
            shutil.copy(first, dst)

# collect names: desktop Icon= + desktop basenames (KWin app-ID aliases)
names = set()
for d in ["/usr/share/applications", str(HOME / ".local/share/applications"), "/var/lib/flatpak/exports/share/applications"]:
    for p in pathlib.Path(d).glob("*.desktop"):
        names.add(p.stem)
        m = re.search(r"^Icon=(.+)$", p.read_text(errors="ignore"), re.M)
        if m and not m.group(1).strip().startswith("/"):
            names.add(m.group(1).strip())
# only valid icon-name characters (skip Steam game titles with spaces etc.)
names = {n for n in names if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", n)}

existing = {p.stem for p in OUT.rglob("*") if p.is_file() and "apps" in p.parts}
todo = sorted(n for n in names if n not in existing)
print(f"icon names: {len(names)} total, {len(todo)} missing in theme")

# alias map: desktop basename -> Icon= value (for app-ID aliases whose
# Icon= already resolves inside the theme, e.g. Hermes -> SkynetRedBlack)
icon_of = {}
for d in ["/usr/share/applications", str(HOME / ".local/share/applications"), "/var/lib/flatpak/exports/share/applications"]:
    for p_ in pathlib.Path(d).glob("*.desktop"):
        m = re.search(r"^Icon=(.+)$", p_.read_text(errors="ignore"), re.M)
        if m:
            icon_of[p_.stem] = m.group(1).strip()

def alias_source(name):
    # Hermes special case (v1.0.32): the Hermes app rewrites its own
    # .desktop file with Icon=hermes, and hicolor hermes.png is the
    # black/white original. The theme's Hermes icon by design is
    # SkynetRedBlack.png (v1.0.17) - use it verbatim (plain copy).
    if name in ("hermes", "com.nousresearch.hermes"):
        src = OUT / "scalable/apps/SkynetRedBlack.png"
        return src if src.exists() else None
    icon = icon_of.get(name)
    if not icon:
        return None
    if icon.startswith("/"):
        pp = pathlib.Path(icon)
        return pp if pp.exists() else None
    hits = [h for h in OUT.rglob(f"{icon}.*") if "apps" in h.parts]
    return hits[0] if hits else None

done, skipped = 0, []
for name in todo:
    src = alias_source(name)
    if src is not None:
        # already tinted in theme (or absolute file): PLAIN COPY only.
        # Re-tinting an already-red icon double-darkens it (v1.0.31 bug:
        # Hermes bg 140->56, silhouette 40->44, contrast crushed).
        try:
            ext = src.suffix.lower()
            first = None
            for d in STD_DIRS:
                dst = OUT / d / (name + ext)
                dst.parent.mkdir(parents=True, exist_ok=True)
                if first is None:
                    shutil.copy(src, dst)
                    first = dst
                else:
                    shutil.copy(first, dst)
            done += 1
            print(f"  aliased {name} from {src}")
            continue
        except Exception as e:
            skipped.append(f"{name} ({e})")
            continue
    src = None
    for root in ROOTS:
        if not root.exists():
            continue
        hits = [p for p in root.rglob("*") if p.is_file() and p.stem == name and p.suffix.lower() in (".svg", ".png", ".jpg", ".jpeg")]
        if hits:
            svgs = [p for p in hits if p.suffix.lower() == ".svg"]
            src = svgs[0] if svgs else sorted(hits, key=lambda p: p.stat().st_size, reverse=True)[0]
            break
    if not src:
        skipped.append(name)
        continue
    try:
        if src.suffix.lower() == ".svg" and "data:image/" in src.read_text(errors="ignore")[:200000]:
            subprocess.run(["rsvg-convert", "-w", "512", "-h", "512", str(src), "-o", "/tmp/_mini.png"], check=True)
            tint_png("/tmp/_mini.png", name + ".png")
        elif src.suffix.lower() == ".svg":
            tint_svg_file(src, name + ".svg")
        else:
            tint_png(src, name + ".png")
        done += 1
        print(f"  tinted {name} from {src}")
    except Exception as e:
        skipped.append(f"{name} ({e})")

print(f"tinted {done}, skipped {len(skipped)}: {skipped[:20]}")
subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(OUT)])
print("icon cache updated - restart Dolphin/Plasma shell/Konsole to see mini icons")
