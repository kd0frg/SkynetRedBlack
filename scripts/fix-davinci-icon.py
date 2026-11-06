#!/usr/bin/env python3
"""v1.0.23: DaVinci Resolve icon cleanup.
1. Regenerate every davinci-resolve PNG (theme + hicolor, live + repo) from
   the clean dark-red SVG - removes the salmon-pink (#ff5959) highlight and
   any white specular dot.
2. Add black symlink emblems at 32/48px (theme only had 16/22/scalable, so
   desktop-size lookups fell back to light/pink inherited emblems).
"""
import pathlib, re, subprocess, sys

HOME = pathlib.Path.home()
THEME = HOME / ".local/share/icons/SkynetRedBlack"
# Repo root derived from this script's location — never hardcode
# /home/<user>/... (breaks other users and relocated checkouts).
REPO = pathlib.Path(__file__).resolve().parents[1]

SRC_SVG = THEME / "scalable/apps/davinci-resolve.svg"
if not SRC_SVG.exists():
    print("davinci-resolve.svg not in theme — nothing to do (DaVinci not installed?)")
    sys.exit(0)
svg_txt = SRC_SVG.read_text()
cols = sorted(set(re.findall(r"#[0-9a-fA-F]{6}", svg_txt)))
print("source SVG colours:", cols)
assert all(c.lower().endswith("0000") for c in cols), f"non dark-red in source: {cols}"

def render(size):
    out = f"/tmp/davinci_{size}.png"
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), str(SRC_SVG), "-o", out], check=True)
    return pathlib.Path(out)

# 1. regenerate PNGs in theme (all sizes that have one) + hicolor + repo hicolor
rendered = {s: render(s) for s in (48, 64, 128, 256)}
targets = []
for root in [THEME, HOME / ".local/share/icons/hicolor", REPO / "hicolor-override"]:
    for p in root.rglob("davinci-resolve.png"):
        targets.append(p)
    # also the panels-setup variant in theme: regenerate from its own svg? keep separate - skip
for p in sorted(set(targets)):
    size = 128
    m = re.search(r"(\d+)x\d+", str(p))
    if m:
        size = int(m.group(1))
    elif "scalable" in str(p):
        size = 128
    # pick closest rendered size >= requested, else largest
    pick = min([s for s in rendered if s >= size], default=256)
    import shutil
    shutil.copy(rendered[pick], p)
    print(f"regenerated {p} (from {pick}px render)")

# panels-setup PNGs in theme: check for pink/white, regenerate from its svg if present
for p in sorted(THEME.rglob("davinci-resolve-panels-setup.png")):
    svg = p.with_suffix(".svg")
    if svg.exists():
        subprocess.run(["rsvg-convert", "-w", "128", "-h", "128", str(svg), "-o", str(p)], check=True)
        print(f"regenerated {p} from {svg.name}")

# also overwrite hicolor SVG with the clean theme SVG (was pink-tinted)
clean_svg = SRC_SVG.read_bytes()
for dest in [HOME / ".local/share/icons/hicolor/scalable/apps/davinci-resolve.svg",
             REPO / "hicolor-override/scalable/apps/davinci-resolve.svg"]:
    if dest.exists():
        dest.write_bytes(clean_svg)
        print(f"replaced pink hicolor SVG: {dest}")

# 2. black symlink emblems at missing sizes 32/48 (+ emblem-new)
for size in (32, 48):
    src_dir = THEME / "22/emblems"
    dst_dir = THEME / f"{size}/emblems"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in ["emblem-link.svg", "link_overlay.svg", "symlink.svg", "emblem-new.svg", "emblem-symbolic-link.svg"]:
        src = src_dir / name
        if not src.exists():
            continue
        dst = dst_dir / name
        if dst.exists():
            continue
        txt = src.read_text()
        txt = re.sub(r'(width=")\d+(")', rf"\g<1>{size}\g<2>", txt, count=1)
        txt = re.sub(r'(height=")\d+(")', rf"\g<1>{size}\g<2>", txt, count=1)
        dst.write_text(txt)
        print(f"added black emblem {dst.relative_to(THEME)}")

# register new emblem dirs in index.theme
idx = THEME / "index.theme"
t = idx.read_text()
for size in (32, 48):
    d = f"{size}/emblems"
    if d not in t:
        t = t.replace("Directories=", f"Directories={d},", 1)
        t = t.rstrip() + f"\n\n[{d}]\nContext=Emblems\nSize={size}\nType=Fixed\n"
        print(f"index.theme: added [{d}]")
idx.write_text(t)

subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(THEME)])
subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(HOME / ".local/share/icons/hicolor")])
print("caches updated")
