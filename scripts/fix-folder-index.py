#!/usr/bin/env python3
"""v1.0.28: complete the icon theme index for places dirs.
The SkynetRedBlack index.theme was missing [96/places], [128/places] and
[256/places] sections even though those directories exist on disk, so KDE
ignored them. Adds any missing places sections (idempotent) and rebuilds
the icon cache. NOTE: apps that were running while the cache changed
(e.g. Dolphin) can keep stale/fallback icons (blue Breeze folders) until
they are restarted - restart Dolphin/Plasma shell after installing.
"""
import pathlib, subprocess, sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path.home() / ".local/share/icons/SkynetRedBlack")
idx = ROOT / "index.theme"
t = idx.read_text()
for size in (96, 128, 256):
    d = f"{size}/places"
    if d not in t:
        t = t.replace("Directories=", f"Directories={d},", 1)
        t = t.rstrip() + f"\n\n[{d}]\nContext=Places\nSize={size}\nType=Fixed\n"
        print(f"index.theme: added [{d}]")
idx.write_text(t)
subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(ROOT)])
print("icon cache updated")
