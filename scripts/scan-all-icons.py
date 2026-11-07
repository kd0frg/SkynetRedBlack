#!/usr/bin/env python3
"""v1.0.39 (+v1.0.41 fixes): scan icon roots for *.svg files and tint
missing ones into SkynetRedBlack, PRESERVING their source context
(status/actions/panel/places/... -> matching theme dirs), so widget
and tray lookups actually find them.

Previously tint-breeze.py only covered /usr/share/icons/breeze.
Now we scan every icon root and tint anything not already in the theme.
This includes user themes, third-party icon packs, custom icons,
flatpak icons, etc.

Rules (theme convention):
  - apps context               -> dark red (luminance -> 40-140, G=B=0)
  - actions/symbolic/status/panel/tray/indicator/media -> bright #ff0000
  - *-symbolic names           -> bright red
  Existing theme icons are NEVER overwritten (kept as-is).

Progress bar: prints "Tinting icons: 0/12345 (0%)" and updates in place.

Usage: python3 scripts/scan-all-icons.py [--bright] [--full]
  --bright  tint everything bright red
  --full    ignore the icon-db and scan everything (default with a DB
            present is incremental: only new/changed SVGs vs the DB)
Called from install.sh AFTER tint-breeze.py (so we skip icons the user
already has) and from retint-new-icons.py's full pipeline.
"""
import pathlib, re, subprocess, sys, os, sqlite3
try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import redtint as _redtint
except ImportError:
    _redtint = None

HOME = pathlib.Path.home()
OUT = HOME / ".local/share/icons/SkynetRedBlack"
BRIGHT_MODE = "--bright" in sys.argv
FORCE_FULL = "--full" in sys.argv  # ignore the icon-db, scan everything
DB_PATH = pathlib.Path(os.environ.get(
    "SKYNET_ICON_DB",
    HOME / ".local/share/SkynetRedBlack" / "icon-db.sqlite3"))


def load_known_icons():
    """{(path, size, mtime)} from the icon-db, or None if no DB.
    With a DB present the scan is INCREMENTAL by default: only SVG
    files that are new or changed since the install-time snapshot get
    read/tinted, instead of every SVG on the system. --full opts out."""
    if FORCE_FULL or not DB_PATH.exists():
        return None
    try:
        con = sqlite3.connect(DB_PATH)
        known = {(r[0], r[1], r[2]) for r in con.execute(
            "SELECT path,size,mtime FROM icons")}
        con.close()
        return known
    except Exception:
        return None

# Directories to skip (not icon locations)
SKIP_PREFIXES = (
    "/proc/", "/sys/", "/dev/", "/run/", "/sysroot/", "/snap/",
    "/.snapshots/", "/boot/", "/efi/", "/media/", "/mnt/",
)

# Icon search roots — ordered priority
ICON_ROOTS = [
    pathlib.Path("/usr/share/icons"),
    HOME / ".local/share/icons",
    pathlib.Path("/usr/share/pixmaps"),
    pathlib.Path("/var/lib/flatpak/exports/share/icons"),
    HOME / ".local/share/flatpak/exports/share/icons",
]

# Also scan user home for custom icon installations
HOME_ICON_PATHS = [
    HOME / ".icons",
    HOME / ".local/share/icons",
]

SIZES = {"16", "22", "24", "32", "48", "64", "96", "128", "256", "512"}
# Widget/system contexts that are bright red. NOTE: "apps" is deliberately
# NOT here — app icons are dark red (one-intensity convention); including
# it made every scanned app icon bright red, contradicting the theme.
BRIGHT_CONTEXTS = {"actions", "symbolic", "status", "panel", "tray", "indicator", "media", "system-status"}
# Theme dir layout mirrors Breeze: <size>/<context>. Source paths may be
# <context>/<size>/ (Breeze) or <size>/<context>/ (hicolor) or
# scalable/<context>/ — extract (size, context) from either layout.
CONTEXTS = {"apps", "actions", "status", "panel", "places", "devices",
            "emblems", "mimetypes", "categories", "preferences",
            "applets", "symbolic", "media", "tray", "indicator", "menu",
            "launcher", "kickoff", "system-status"}
CONTEXT_MAP = {"apps": "Applications", "actions": "Actions", "status": "Status",
               "panel": "Status", "places": "Places", "devices": "Devices",
               "emblems": "Emblems", "mimetypes": "MimeTypes",
               "categories": "Categories", "preferences": "Applications",
               "applets": "Applications", "symbolic": "Status",
               "media": "Status", "tray": "Status", "indicator": "Status",
               "menu": "Applications", "launcher": "Applications",
               "kickoff": "Applications", "system-status": "Status"}


def dark_rgb(r, g, b):
    """Map luminance to dark red range (40-140), G=B=0."""
    lum = int(0.299 * r + 0.587 * g + 0.114 * b)
    return (40 + int(lum * 100 / 255), 0, 0)


def is_svg_bright(src_path, filename, ctx=None):
    """Determine if an SVG should be bright red based on context."""
    if "-symbolic" in filename:
        return True
    if ctx is not None:
        return ctx in BRIGHT_CONTEXTS
    parts = src_path.parts
    for part in parts:
        if part in BRIGHT_CONTEXTS:
            return True
    return False


def tint_svg(txt, bright):
    """Replace all color tokens in SVG with red variant.
    Handles #RGB/#RGBA/#RRGGBB/#RRGGBBAA, rgb()/rgba() and currentColor
    (symbolic silhouettes use currentColor — leaving it keeps them white)."""
    magenta = "#ff0000" if bright else "#8c0000"
    txt = txt.replace("currentColor", magenta)
    def repl(m):
        h = m.group(1)
        if len(h) not in (3, 4, 6, 8):
            return m.group(0)
        if len(h) in (3, 4):
            r, g, b = (int(c * 2, 16) for c in h[:3])
            alpha = h[3] * 2 if len(h) == 4 else ""
        elif len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            alpha = ""
        else:  # len(h) == 8
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            alpha = h[6:8]
        if max(r, g, b) == 0:
            return m.group(0)  # pure black, keep as-is
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
            return (f"rgba(255,0,0,{m.group(4)})" if m.group(4) else "rgb(255,0,0)")
        nr, ng, nb = dark_rgb(r, g, b)
        return f"rgba({nr},{ng},{nb},{m.group(4)})" if m.group(4) else f"rgb({nr},{ng},{nb})"
    return re.sub(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([\d.]+)\s*)?\)", rgb_repl, txt)


def split_size_context(src_path):
    """Extract (size, context) from a source icon path in either layout:
    Breeze <context>/<size>/name.svg, hicolor <size>/<context>/name.svg,
    or scalable/<context>/name.svg. Defaults to (None, 'apps')."""
    parts = src_path.parts
    size = None
    ctx = None
    for i, part in enumerate(parts):
        # hicolor sizes look like "48x48" / "128x128"
        sizelook = part.split("x")[0] if "x" in part and part.split("x")[0].isdigit() else part
        if sizelook in SIZES:
            size = sizelook
            if i + 1 < len(parts) and parts[i + 1] in CONTEXTS:
                ctx = parts[i + 1]
            elif i - 1 >= 0 and parts[i - 1] in CONTEXTS:
                ctx = parts[i - 1]
        if part == "scalable" and i + 1 < len(parts) and parts[i + 1] in CONTEXTS:
            ctx = parts[i + 1]
            size = size or "scalable"
    return size, ctx or "apps"


def write_tinted_to_theme(name, tinted_text, size_dirs, ctx="apps"):
    """Write tinted SVG into the theme PRESERVING its context.
    Apps icons go to the standard apps dirs (all sizes, so any lookup
    finds them); widget/system icons go to their own <size>/<ctx> dir
    (e.g. status, actions, panel) where tray/widget lookups find them.
    Returns the list of newly created theme dirs for index.theme."""
    import shutil
    new_dirs = []
    if ctx == "apps":
        # Lean app sizes: SVGs scale cleanly from 16/scalable, and
        # writing 9 sizes x thousands of scanned names is bloat.
        # (retint/tint-breeze still write the full 9-size set for the
        # curated app/Breeze icons they own.)
        targets = [f"{s}/apps" for s in ("16", "22", "48", "scalable")]
    else:
        # Lean sizes only for widget/system contexts: the loader scales
        # SVGs cleanly, and writing 9 sizes x thousands of icons is pure
        # bloat (tint-breeze.py already ships the complete Breeze set).
        targets = [f"{s}/{ctx}" for s in ("16", "22", "scalable")]
    first_written = None
    for d in targets:
        dst = OUT / d / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if first_written is None:
            dst.write_text(tinted_text)
            first_written = dst
        else:
            shutil.copy(first_written, dst)
        new_dirs.append(d)
    return new_dirs


def register_dirs(new_dirs):
    """Ensure index.theme lists every created dir with correct Context."""
    idx = OUT / "index.theme"
    if not idx.exists():
        return
    t = idx.read_text()
    changed = False
    for d in sorted(set(new_dirs)):
        if d not in t:
            if d.startswith("scalable/"):
                size, typ = "scalable", "Scalable"
            else:
                size, typ = d.split("/")[0], "Fixed"
            ctx = CONTEXT_MAP.get(d.split("/")[-1], "Applications")
            t = t.replace("Directories=", f"Directories={d},", 1)
            t = t.rstrip() + f"\n\n[{d}]\nContext={ctx}\nSize={size}\nType={typ}\n"
            changed = True
    if changed:
        idx.write_text(t)


def is_in_skip_tree(path):
    """Check if path is under a filesystem tree we should skip."""
    pstr = str(path)
    for skip in SKIP_PREFIXES:
        if pstr.startswith(skip):
            return True
    return False


def progress_bar(current, total, label="Tinting icons"):
    """Print a simple in-place progress bar."""
    if total == 0:
        pct = 100
    else:
        pct = int(current * 100 / total)
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"\r{label}: [{bar}] {current}/{total} ({pct}%)", end="", flush=True)
    if current >= total:
        print()  # newline when done


# Files that are NOT icons — skip them immediately to avoid hours of processing
NON_ICON_PATTERNS = [
    "/doc/", "/docs/", "README", "readme", "CHANGELOG", "changelog",
    "CONTRIBUTING", "contributing", "LICENSE", "license",
    "/drawio/", "/diagrams/", "/diagram/", "/uml/",
]
NON_ICON_EXT = {".svgz"}


def is_likely_icon(path):
    """Fast heuristic: is this SVG likely an actual icon?"""
    if path.suffix.lower() in NON_ICON_EXT:
        return False
    for pat in NON_ICON_PATTERNS:
        if pat.lower() in str(path).lower():
            return False
    return True


def sanitize_name(name):
    """Icon names with spaces (or leading spaces) make
    gtk-update-icon-cache abort with 'The generated cache was invalid',
    leaving the old cache in place. Rename spaces to hyphens."""
    import re as _re
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    stem = _re.sub(r"[ ]+", "-", stem.strip())
    stem = _re.sub(r"-{2,}", "-", stem)
    return stem + ("." + ext if ext else "")


def collect_svg_files():
    """Walk all icon roots and collect (path, name) tuples for *.svg files."""
    files = []
    seen_paths = set()

    for root in ICON_ROOTS:
        if not root.exists():
            continue
        # Never scan the theme itself: it holds ~700k tinted copies
        # (every size/context), all already in theme by definition, and
        # walking it dominates the scan time for zero new icons.
        if root.resolve() == OUT.resolve() or OUT in root.resolve().parents:
            continue
        if OUT.resolve() in root.resolve().parents and root.resolve() != OUT.resolve():
            # root is an ancestor of OUT (e.g. ~/.local/share/icons):
            # prune OUT during the walk below via seen check.
            pass
        for svg in root.rglob("*.svg"):
            # Prune the theme directory itself out of ancestor roots.
            try:
                if OUT.resolve() in svg.resolve().parents:
                    continue
            except Exception:
                pass
            if is_in_skip_tree(svg):
                continue
            if not is_likely_icon(svg):
                continue
            real = svg.resolve()
            if real in seen_paths:
                continue
            seen_paths.add(real)
            files.append(svg)

    # v1.0.45: no second walk of ~/.local/share/icons — ICON_ROOTS
    # already includes it (the old code rglobbed it twice).

    return files


def inherited_names():
    """Icon names already resolvable via the theme's Inherits chain
    (Tela/Breeze/hicolor/Papirus/char-white/YAMIS). The icon loader finds
    these through inheritance, so copying tinted copies of them into
    SkynetRedBlack is pure bloat (a full scan once wrote ~230k files /
    >1 GB). The Breeze set is already tinted in-theme by tint-breeze.py;
    the scan only needs names NO inherited theme provides."""
    names = set()
    roots = [
        pathlib.Path("/usr/share/icons/Tela-red-dark"),
        pathlib.Path("/usr/share/icons/Tela"),
        pathlib.Path("/usr/share/icons/breeze"),
        pathlib.Path("/usr/share/icons/breeze-dark"),
        pathlib.Path("/usr/share/icons/hicolor"),
        pathlib.Path("/usr/share/icons/Papirus"),
        pathlib.Path("/usr/share/icons/Papirus-Dark"),
        pathlib.Path("/usr/share/icons/char-white"),
        HOME / ".local/share/icons/YAMIS",
    ]
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".svg", ".png"):
                names.add(p.stem)
    return names


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inherited = inherited_names()
    print(f"{len(inherited)} icon names available via inheritance (skipped)")

    # Collect all SVG icon files on the system
    all_svgs = collect_svg_files()
    total = len(all_svgs)
    known = load_known_icons()
    if known is not None:
        fresh = []
        for src in all_svgs:
            try:
                st = src.stat()
                key = (str(src), st.st_size, int(st.st_mtime))
            except OSError:
                continue
            if key not in known:
                fresh.append(src)
        print(f"icon-db incremental scan: {len(fresh)} new/changed "
              f"of {total} SVG files ({total - len(fresh)} unchanged, skipped)")
        all_svgs = fresh
        total = len(all_svgs)
    else:
        print(f"Found {total} SVG icon files on the system (full scan)")

    added = skipped = 0
    size_dirs = [
        "16/apps", "22/apps", "24/apps", "32/apps",
        "48/apps", "64/apps", "128/apps", "256/apps", "scalable/apps"
    ]
    # Context dirs already present in the theme (only dirs that exist
    # count as "already in theme" — a same-named apps file must not
    # satisfy a status lookup and vice versa).
    theme_dirs = set()
    if OUT.exists():
        for p in OUT.rglob("*"):
            if p.is_dir():
                theme_dirs.add(p.relative_to(OUT).as_posix())
    new_dirs = set()

    for i, src in enumerate(all_svgs):
        if i % 500 == 0 or i == total - 1:
            progress_bar(i, total)

        filename = src.name
        name = sanitize_name(filename)
        # Skip names the loader already resolves via inheritance —
        # tinting copies of them in-theme is bloat, not coverage.
        if src.stem in inherited:
            skipped += 1
            continue
        _, ctx = split_size_context(src)
        # Determine brightness from the SOURCE context (apps = dark).
        if BRIGHT_MODE:
            bright = True
        else:
            bright = is_svg_bright(src, filename, ctx)

        # Check if already in theme for THIS context: apps icons must
        # exist in an apps dir, widget icons in their own context dir.
        if ctx == "apps":
            check_dirs = size_dirs
        else:
            check_dirs = [f"{s}/{ctx}" for s in
                          ("16", "22", "24", "32", "48", "64", "128", "256", "scalable")]
        already = any((OUT / d / name).exists() for d in check_dirs if d in theme_dirs or (OUT / d).exists())
        if already:
            skipped += 1
            continue

        # Quick file size check — icon SVGs are typically < 200KB
        try:
            if src.stat().st_size > 200_000:
                skipped += 1
                continue
            txt = src.read_text(errors="ignore")
        except Exception:
            continue

        # Embedded-raster SVGs (data:image/png;base64) have no vector
        # fills to regex-tint — render to PNG, tint pixels, ship .png.
        if "data:image/" in txt[:200000]:
            try:
                tmp = "/tmp/_scan_raster.png"
                subprocess.run(["rsvg-convert", "-w", "256", "-h", "256",
                                str(src), "-o", tmp], check=True,
                               capture_output=True)
                if _redtint is not None:
                    im = _redtint.tint_png_file(tmp, bright=bright)
                else:
                    from PIL import Image as _Image
                    im = _Image.open(tmp).convert("RGBA")
                    px = im.load()  # type: ignore[union-attr]
                    for y in range(im.height):
                        for x in range(im.width):
                            r, g, b, a = px[x, y]  # type: ignore[index]
                            if a and max(r, g, b) > 0:
                                px[x, y] = ((255, 0, 0, a) if bright
                                            else (*dark_rgb(r, g, b), a))
                png_name = sanitize_name(src.stem) + ".png"
                first = None
                write_dirs = check_dirs if ctx == "apps" else [f"{s}/{ctx}" for s in ("16", "22", "scalable")]
                for d in write_dirs:
                    dst = OUT / d / png_name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if first is None:
                        im.save(dst)
                        first = dst
                    else:
                        import shutil as _sh
                        _sh.copy(first, dst)
                    new_dirs.add(d)
                added += 1
                continue
            except Exception:
                skipped += 1
                continue

        tinted = tint_svg(txt, bright)
        new_dirs.update(write_tinted_to_theme(name, tinted, size_dirs, ctx))
        added += 1

    register_dirs(new_dirs)
    progress_bar(total, total)  # ensure final newline
    print(f"\nScan complete: {added} new icons tinted, {skipped} already in theme")

    # Rebuild icon cache
    subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(OUT)], check=False)
    print("Icon cache updated")

    # Refresh the icon-db snapshot so the next scan/retint diffs against
    # the state including whatever this run just tinted. Best-effort.
    # v1.0.45: retint sets SKYNET_SKIP_DB_REFRESH=1 for the pipeline
    # and refreshes once itself at the end (was: 2 full DB builds).
    if os.environ.get("SKYNET_SKIP_DB_REFRESH"):
        return
    here = pathlib.Path(__file__).resolve().parent
    for cand in (here / "icon-db.py",
                 HOME / "SkynetRedBlack" / "scripts" / "icon-db.py",
                 HOME / ".local/bin" / "icon-db.py"):
        if cand.exists():
            print("Refreshing icon-db ...")
            subprocess.run([sys.executable, str(cand), "update"],
                           capture_output=True)
            break


if __name__ == "__main__":
    main()
