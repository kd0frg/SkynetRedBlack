#!/usr/bin/env python3
"""v1.0.24 (was v1.0.21): make Copy (edit-copy) squares VISIBLE dark red.
v1.0.21 set them to #3c0000 (60,0,0) to match the disabled 'Copy' text -
but at luminance ~18 on a black background they are effectively invisible
(darker to the eye than the grey 43,43,43 they replaced). Now #8c0000
(140,0,0): luminance ~42, as visible as the old grey, still dark red, and
the top of the theme's dark-red app-icon range (40-140). Handles upgrades
from both #ff0000 (pre-1.0.21) and #3c0000 (1.0.21-1.0.23).
Also adds missing 32/actions + scalable/actions sizes so KDE can't fall
back to grey Breeze icons.
"""
import pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path.home() / ".local/share/icons/SkynetRedBlack")
OLDS = ("#ff0000", "#3c0000")
NEW = "#8c0000"

targets = []
for p in ROOT.rglob("*"):
    if p.is_file() and p.suffix.lower() == ".svg" and "copy" in p.name.lower():
        # action icons only (not folders/files that happen to mention copy)
        if "actions" in p.parts:
            targets.append(p)

changed = 0
for p in sorted(targets):
    t = p.read_text(errors="ignore")
    nt = t
    for old in OLDS:
        nt = re.sub(re.escape(old), NEW, nt, flags=re.I)
    if nt != t:
        p.write_text(nt)
        changed += 1
        print(f"recoloured {p.relative_to(ROOT)}")
print(f"recoloured {changed}/{len(targets)} copy action icons")

# --- add missing sizes from the 16px file (SVG scales cleanly) ---
src16 = ROOT / "16/actions"
for name in ["edit-copy.svg", "editcopy.svg", "edit-copy-symbolic.svg", "edit-copy-path.svg"]:
    src = src16 / name
    if not src.exists():
        continue
    txt = src.read_text()
    for size, dest_dir in [(32, ROOT / "32/actions"), (48, ROOT / "48/actions")]:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / name
        if dest.exists():
            continue
        m = re.sub(r'(width=")\d+(")', rf"\g<1>{size}\g<2>", txt, count=1)
        m = re.sub(r'(height=")\d+(")', rf"\g<1>{size}\g<2>", m, count=1)
        dest.write_text(m)
        print(f"added {dest.relative_to(ROOT)}")
    # scalable/actions
    dest_dir = ROOT / "scalable/actions"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    if not dest.exists():
        shutil.copy(src, dest)
        print(f"added {dest.relative_to(ROOT)}")

# --- index.theme: register new dirs ---
idx = ROOT / "index.theme"
t = idx.read_text()
for d in ["32/actions", "48/actions", "scalable/actions"]:
    if d not in t:
        t = t.replace("Directories=", f"Directories={d},", 1)
        if d == "32/actions":
            size = 32
        elif d == "48/actions":
            size = 48
        else:
            size = 48
        typ = "Fixed" if "scalable" not in d else "Scalable"
        extra = "\nMinSize=16\nMaxSize=512" if typ == "Scalable" else ""
        t = t.rstrip() + f"\n\n[{d}]\nContext=Actions\nSize={size}\nType={typ}{extra}\n"
        print(f"index.theme: added [{d}]")
idx.write_text(t)

subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(ROOT)])
print("icon cache updated")
