#!/usr/bin/env python3
"""v1.0.34: normalize preferences-context icons to dark red.
Stale bright #ff0000 copies in <size>/preferences/ (22/24px) were winning
over the dark copies in <size>/apps/ in KDE lookup order, making e.g.
DLSS5VKLayer Helper (preferences-desktop) and Emoji Selector
(preferences-desktop-emoticons) render bright red with white remnants in
the Kickoff menu while everything else was dark maroon. Re-tints every
preferences file that is not already all-red, from the Breeze source when
available. Also rewrites index.theme Directories in alphabetical
(size, context) order so apps/ consistently wins over preferences/.
"""
import pathlib, re, subprocess

HOME = pathlib.Path.home()
OUT = HOME / ".local/share/icons/SkynetRedBlack"
BREEZE = pathlib.Path("/usr/share/icons/breeze")

def dark_rgb(r, g, b):
    lum = int(0.299 * r + 0.587 * g + 0.114 * b)
    return (40 + int(lum * 100 / 255), 0, 0)

def _expand(h):
    if len(h) == 3:
        return "".join(c * 2 for c in h), ""
    if len(h) == 4:
        return "".join(c * 2 for c in h[:3]), h[3] * 2
    if len(h) == 6:
        return h, ""
    if len(h) == 8:
        return h[:6], h[6:8]
    return None, ""

def tint(txt):
    def repl(m):
        h = m.group(1)
        hex6, alpha = _expand(h)
        if hex6 is None:
            return m.group(0)
        r, g, b = int(hex6[0:2], 16), int(hex6[2:4], 16), int(hex6[4:6], 16)
        if max(r, g, b) == 0:
            return m.group(0)
        nr, ng, nb = dark_rgb(r, g, b)
        return f"#{nr:02x}0000" + alpha
    txt = re.sub(r"#([0-9a-fA-F]{3,8})\b", repl, txt)
    def rgb_repl(m):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if max(r, g, b) == 0:
            return m.group(0)
        nr, ng, nb = dark_rgb(r, g, b)
        return f"rgba({nr},{ng},{nb},{m.group(4)})" if m.group(4) else f"rgb({nr},{ng},{nb})"
    return re.sub(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([\d.]+)\s*)?\)", rgb_repl, txt)

def needs_fix(txt):
    """True if any strong colour is not dark red: either colourful
    (G or B > 30) or bright (R > 200, e.g. stale #ff0000 copies)."""
    for m in re.finditer(r"#([0-9a-fA-F]{3,8})", txt):
        hex6, _ = _expand(m.group(1))
        if hex6 is None:
            continue
        r, g, b = int(hex6[0:2], 16), int(hex6[2:4], 16), int(hex6[4:6], 16)
        if max(r, g, b) > 30 and (g > 30 or b > 30 or r > 200):
            return True
    for m in re.finditer(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", txt):
        r, g, b = (int(m.group(i)) for i in (1, 2, 3))
        if max(r, g, b) > 30 and (g > 30 or b > 30 or r > 200):
            return True
    return False

fixed = 0
for dst in sorted((OUT).glob("*/preferences/*.svg")):
    txt = dst.read_text(errors="ignore")
    if not needs_fix(txt):
        continue
    size = dst.parent.parent.name
    src = BREEZE / "preferences" / size / dst.name
    base = src.read_text(errors="ignore") if src.exists() else txt
    dst.write_text(tint(base))
    fixed += 1
print(f"re-tinted {fixed} preferences icons to dark red")

# rewrite Directories alphabetically by (size, context): apps before preferences
idx = OUT / "index.theme"
t = idx.read_text()
m = re.search(r"^Directories=(.*)$", t, re.M)
dirs = [d for d in m.group(1).split(",") if d]
def key(d):
    parts = d.split("/")
    return (parts[0], parts[1] if len(parts) > 1 else "")
dirs_sorted = sorted(set(dirs), key=key)
t = t[: m.start(1)] + ",".join(dirs_sorted) + t[m.end(1):]
idx.write_text(t)
print(f"Directories rewritten: {len(dirs_sorted)} entries, apps now precedes preferences per size")

subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(OUT)])
print("icon cache updated - restart Plasma shell to see Kickoff menu icons")
