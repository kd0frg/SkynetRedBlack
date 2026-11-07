#!/usr/bin/env python3
"""v1.0.35: bright-red tray icons for Steam, audio-volume, and Cachy updater.

Root cause: SkynetRedBlack's dark-red mapping (luminance -> 40-140) left:
 - cachy-update-blue crushed to near-black (#280000-#6c0000, avg 91) and
   cachy-update_updates-available-blue the same, so the update alert was
   indistinguishable from the normal state (both ~black).
 - steam at #450000/#8c0000 (avg 87) - darkest dock icon, unreadable.
 - audio-volume-* symbolic files at #450000 (R=69, avg 68) - black-red,
   far darker than the bright-red tray outline theme.

Fix (only 3 icon families, all other icons untouched):
 - Cachy updater: normal `cachy-update-blue` (checkmark) -> dark red
   luminance mapping `R'=40+lum*100/255` from the hicolor original
   (avg 91, max 108, darker state). Updates available -> bright red
   V-mapping `out=(max(R,G,B),0,0)` from the hicolor original
   (avg 208, max 255, brightest red). Matches user spec: normal darker,
   updates-available brightest / red alert, only the down-arrow/check
   changes state.
 - Steam: bright red V-mapping from Tela-red-dark original
   (#144477 -> #770000, #122d60 -> #600000, #fff -> #ff0000, avg 133,
   max 255). `steam_tray_mono*` (SNI tray) -> solid #ff0000 silhouette.
 - Audio: every `audio-volume-*` icon (status/panel/actions/symbolic,
   all sizes incl. rtl variants) -> solid bright #ff0000 (avg 255).

Idempotent, upgrade-safe: if hicolor/Tela originals are present the
script regenerates the SVG from them (never re-tints already-tinted
files, which would double-darken); otherwise it remaps the installed
tinted files to #ff0000 silhouettes where applicable and leaves
already-bright files alone. No system/theme edits beyond the icon
directory; no .desktop edits.

Usage: python3 scripts/fix-tray-icons.py [theme-root]
Default: ~/.local/share/icons/SkynetRedBlack
"""
import pathlib, re, sys, glob

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path.home() / ".local/share/icons/SkynetRedBlack")
TILING = {
    "HICOLOR": "/usr/share/icons/hicolor/scalable/apps",
    "TELA": "/usr/share/icons/Tela-red-dark/scalable/apps",
}

def hex_to_rgb(h):
    if len(h) == 3:
        return tuple(int(c*2, 16) for c in h)
    if len(h) >= 6:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return None

def dark_map(r, g, b):
    if r < 12 and g < 12 and b < 12:
        return (r, g, b)
    lum = 0.299*r + 0.587*g + 0.114*b
    return (int(round(40 + lum*100/255)), 0, 0)

def v_map(r, g, b):
    if r < 12 and g < 12 and b < 12:
        return (r, g, b)
    return (max(r, g, b), 0, 0)

def transform(text, mapper):
    def repl(m):
        h = m.group(1)
        alpha = ""
        if len(h) == 8:
            rgb = hex_to_rgb(h[:6]); alpha = h[6:8].lower()
        else:
            rgb = hex_to_rgb(h)
        if rgb is None:
            return m.group(0)
        nr, ng, nb = mapper(*rgb)
        return f"#{nr:02x}{ng:02x}{nb:02x}{alpha}"
    return re.sub(r'#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b', repl, text)

def write_if(p, content):
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists() and p.read_text(errors="ignore") == content:
        return False
    p.write_text(content)
    return True

changed = 0

# --- Cachy updater (normal dark, updates-available bright) ---
cachy_pairs = [
    ("cachy-update-blue.svg", dark_map, f"{TILING['HICOLOR']}/cachy-update-blue.svg"),
    ("cachy-update_updates-available-blue.svg", v_map, f"{TILING['HICOLOR']}/cachy-update_updates-available-blue.svg"),
    ("cachy-update-dark.svg", dark_map, f"{TILING['HICOLOR']}/cachy-update-dark.svg"),
    ("cachy-update-light.svg", dark_map, f"{TILING['HICOLOR']}/cachy-update-light.svg"),
    ("cachy-update_updates-available-dark.svg", v_map, f"{TILING['HICOLOR']}/cachy-update_updates-available-dark.svg"),
    ("cachy-update_updates-available-light.svg", v_map, f"{TILING['HICOLOR']}/cachy-update_updates-available-light.svg"),
    ("cachy-update_updates-available-blue-cb.svg", v_map, f"{TILING['HICOLOR']}/cachy-update_updates-available-blue-cb.svg"),
    ("cachy-update_updates-available-dark-cb.svg", v_map, f"{TILING['HICOLOR']}/cachy-update_updates-available-dark-cb.svg"),
    ("cachy-update_updates-available-light-cb.svg", v_map, f"{TILING['HICOLOR']}/cachy-update_updates-available-light-cb.svg"),
]
for name, mapper, src in cachy_pairs:
    if not pathlib.Path(src).exists():
        continue
    tinted = transform(pathlib.Path(src).read_text(errors="ignore"), mapper)
    for p in glob.glob(f"{ROOT}/**/{name}", recursive=True):
        try:
            if write_if(pathlib.Path(p), tinted):
                print(f"fixed {p}"); changed += 1
        except Exception as e:
            print(f"skip {p}: {e}")
print(f"cachy: {changed} files regenerated from originals")

# --- Steam (bright V from Tela) ---
tela_steam = f"{TILING['TELA']}/steam.svg"
if pathlib.Path(tela_steam).exists():
    steam_tinted = transform(pathlib.Path(tela_steam).read_text(errors="ignore"), v_map)
    # also map any leftover #fff already handled (255 -> #ff0000)
    c = 0
    for p in glob.glob(f"{ROOT}/**/steam.svg", recursive=True):
        try:
            if write_if(pathlib.Path(p), steam_tinted):
                print(f"steam {p} -> bright"); c += 1
        except Exception as e:
            print(f"skip {p}: {e}")
    print(f"steam: {c} files brightened")

# --- Steam tray + Audio: solid bright #ff0000 silhouette ---
SILHOUETTE_OLDS = ("#330000", "#8c0000", "#450000", "#280000", "#2f0000")
for pattern in ["**/steam_tray*.svg", "**/audio-volume*.svg"]:
    n = 0
    for p in glob.glob(f"{ROOT}/{pattern}", recursive=True):
        try:
            t = pathlib.Path(p).read_text(errors="ignore")
            nt = t
            for old in SILHOUETTE_OLDS:
                nt = re.sub(re.escape(old), "#ff0000", nt, flags=re.I)
            nt = nt.replace("color:#330000", "color:#ff0000").replace("color:#8c0000", "color:#ff0000")
            nt = nt.replace("color:#450000", "color:#ff0000")
            if nt != t:
                pathlib.Path(p).write_text(nt)
                n += 1
        except Exception as e:
            print(f"skip {p}: {e}")
    print(f"{pattern}: {n} files brightened to #ff0000")

import subprocess
subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(ROOT)], check=False)
print("icon cache updated")
