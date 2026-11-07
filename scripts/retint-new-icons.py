#!/usr/bin/env python3
"""Cyberdyne Skynet Red/Black - retint NEW app icons dark red.
Run after installing a new app:  python3 scripts/retint-new-icons.py
Scans all .desktop files (incl Flatpak), finds Icon= names not yet in
SkynetRedBlack, tints their source icons dark red (lum -> 40-140, pure red),
writes them into the theme in all sizes, rebuilds caches.
Existing icons are left untouched unless --force is given.

Widget icons (panel, system tray, desktop, launcher) are always tinted
BRIGHT RED (#ff0000) regardless of the dark-red mapping, because the
theme convention for widget/symbolic icons is bright red since v1.0.13.

Usage:
  python3 scripts/retint-new-icons.py          # full pipeline (all icon scripts)
  python3 scripts/retint-new-icons.py --apps-only  # app Icon= names only
  python3 scripts/retint-new-icons.py --bright  # everything bright red (widget retint)
  python3 scripts/retint-new-icons.py --force   # re-tint even existing icons
  python3 scripts/retint-new-icons.py --skip-db # ignore/skip the icon-db diff+refresh

With an icon-db present (built by install.sh), the app step diffs the
current start-menu apps (.desktop files) against the DB snapshot and
only tints NEW/CHANGED apps; source icons are found by indexed DB
lookup. The DB is refreshed at the end of the run. No DB -> full audit
once (old behaviour), then the DB is built for next time.
"""
import pathlib, re, shutil, sqlite3, subprocess, sys, os, time
from PIL import Image
# v1.0.45: shared fast tint library (C-speed PNG tinting, one copy of
# the SVG regex). Falls back gracefully if redtint.py is missing.
try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import redtint as _redtint
except ImportError:
    _redtint = None
HOME=pathlib.Path.home(); OUT=HOME/".local/share/icons/SkynetRedBlack"
DB_PATH=pathlib.Path(os.environ.get("SKYNET_ICON_DB",
    HOME/".local/share/SkynetRedBlack/icon-db.sqlite3"))
SKIP_DB="--skip-db" in sys.argv
STD_DIRS=["16/apps","22/apps","24/apps","32/apps","48/apps","64/apps","128/apps","256/apps","scalable/apps"]
FORCE="--force" in sys.argv
BRIGHT="--bright" in sys.argv

# Widget icon name patterns — Plasma looks up these names for:
#   - Panel applets (system tray, clock, task manager, etc.)
#   - Desktop icons (via FolderItemDelegate)
#   - Kickoff launcher icons
#   - System status icons (volume, network, battery, etc.)
# These should always be bright red, never dark.
# Matching is by normalized PREFIX (hyphens/underscores/dots removed,
# then startswith) — never substring-anywhere, which misclassifies
# ordinary app icons (e.g. a generic word like "folder" or "add"
# appearing inside an app name) as widgets and breaks the one-intensity
# dark-red app convention.
WIDGET_PATTERNS = [
    "system-panel", "system-status", "system-controls",
    "audio-volume", "network", "battery", "power", "display",
    "media-player", "media-control", "media-stop", "media-play",
    "media-pause", "media-next", "media-previous", "media-record",
    "system-search", "system-settings", "system-software",
    "dialog-", "panel-", "tray", "status-notifier", "SNI",
    "indicator-", "appmenu", "kicker", "kickoff", "launcher",
    "bluetooth", "wifi", "ethernet", "network-connect",
    "input-keyboard", "input-mouse", "input-touchpad",
    "brightness", "contrast", "display-settings",
    "power-button", "shutdown", "reboot", "lock", "logout",
    "edit-copy", "edit-paste", "edit-cut", "edit-delete",
    "edit-find", "edit-save", "edit-undo", "edit-redo",
    "view-refresh", "view-fullscreen", "view-list", "view-grid",
    "go-home", "go-up", "go-previous", "go-next",
    "folder-new", "drive-harddisk", "drive-removable",
    "dialog-close", "dialog-ok",
    "screenshot", "input-keyboard", "input-mouse",
    "xsettings", "kcm", "kde", "plasma",
    "bluedevil", "ksmserver", "kwin", "kded",
    "plasmashell", "krunner", "knotify",
    "akonadi", "kmail", "kontact",
    "system-file-manager", "file-manager", "dolphin",
]

def normalize(name):
    """Normalize for widget matching: remove hyphens/underscores/dots.
    (Never replace with spaces — that breaks standard KDE patterns.)"""
    return name.lower().replace("-", "").replace("_", "").replace(".", "")

def is_widget_icon(name):
    """Check if an icon name is a widget/panel/system icon that should be bright red."""
    if BRIGHT:
        return True  # --bright mode: everything bright
    lower = normalize(name)
    for pattern in WIDGET_PATTERNS:
        p = normalize(pattern)
        if lower.startswith(p):
            return True
    return False

def dark_rgb(r,g,b):
    lum=int(0.299*r+0.587*g+0.114*b); return (40+int(lum*100/255),0,0)

def tint_svg(txt, bright):
    # v1.0.45: delegate to the shared library (identical mapping).
    if _redtint is not None:
        return _redtint.tint_svg(txt, bright=bright)
    # Handle EVERY hex form: #RGB, #RGBA, #RRGGBB, #RRGGBBAA, plus rgb()/rgba()
    # and currentColor (symbolic silhouettes use it; leaving it keeps them white).
    txt = txt.replace("currentColor", "#ff0000" if bright else "#8c0000")
    def repl(m):
        h=m.group(1); a=None
        if len(h) in (3,4):
            r,g,b=(int(c*2,16) for c in h[:3])
            if len(h)==4: a=h[3]*2
        elif len(h)==6:
            r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
        elif len(h)==8:
            r,g,b,a=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16),h[6:8]
        else: return m.group(0)
        if max(r,g,b)==0: return m.group(0)
        if bright:
            return "#ff0000"+(a or "")
        nr,ng,nb=dark_rgb(r,g,b)
        return f"#{nr:02x}0000"+(a or "")
    txt=re.sub(r'#([0-9a-fA-F]{3,8})\b',repl,txt)
    def rgb_repl(m):
        r,g,b=int(m.group(1)),int(m.group(2)),int(m.group(3))
        if max(r,g,b)==0: return m.group(0)
        if bright:
            return (f"rgba(255,0,0,{m.group(4)})" if m.group(4) else "rgb(255,0,0)")
        nr,ng,nb=dark_rgb(r,g,b)
        return f"rgba({nr},{ng},{nb},{m.group(4)})" if m.group(4) else f"rgb({nr},{ng},{nb})"
    return re.sub(r'rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([\d.]+)\s*)?\)',rgb_repl,txt)

def tint_png(src, name, bright):
    if _redtint is not None:
        first = None
        for d in STD_DIRS:
            dst = OUT / d / name
            if first is None:
                _redtint.write_tinted_png(src, dst, bright=bright)
                first = dst
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(first, dst)
        return
    im=Image.open(src).convert("RGBA")
    if max(im.size)>512: im.thumbnail((512,512))
    px=im.load()
    for y in range(im.height):
        for x in range(im.width):
            r,g,b,a=px[x,y]
            if a and max(r,g,b)>0:
                if bright:
                    px[x,y]=(255,0,0,a)
                else:
                    px[x,y]=(*dark_rgb(r,g,b),a)
    first=None
    for d in STD_DIRS:
        dst=OUT/d/name; dst.parent.mkdir(parents=True,exist_ok=True)
        if first is None: im.save(dst); first=dst
        else: shutil.copy(first,dst)

def tint_svg_file(src, name, bright):
    txt=tint_svg(src.read_text(errors="ignore"), bright); first=None
    # v1.0.46: SVGs ship lean (16/22/scalable — the loader scales
    # them), matching the slim release tarball.
    for d in ["16/apps","22/apps","scalable/apps"]:
        dst=OUT/d/name; dst.parent.mkdir(parents=True,exist_ok=True)
        if first is None: dst.write_text(txt); first=dst
        else: shutil.copy(first,dst)

def load_db_apps():
    """{desktop_id: icon} from the install-time DB, or None if no DB.
    A missing DB means: fall back to the old full behaviour (and the DB
    gets built at the end of this run for next time)."""
    if SKIP_DB or not DB_PATH.exists():
        return None
    try:
        con=sqlite3.connect(DB_PATH)
        apps={did: icon for did, icon in con.execute(
            "SELECT desktop_id,icon FROM apps")}
        con.close()
        return apps
    except Exception:
        return None

_db_con = None
def db_lookup(name):
    """Indexed source-icon lookup via the DB (O(log n) vs globbing every
    theme root per name). Returns pathlib.Path or None.
    v1.0.45: one cached connection (was: connect+close per name)."""
    global _db_con
    if SKIP_DB or not DB_PATH.exists():
        return None
    try:
        if _db_con is None:
            _db_con = sqlite3.connect(DB_PATH)
        rows = _db_con.execute(
            "SELECT path FROM icons WHERE stem=? ORDER BY "
            "CASE ext WHEN '.svg' THEN 0 ELSE 1 END, path", (name,)).fetchall()
    except Exception:
        return None
    for (p,) in rows:
        if pathlib.Path(p).exists():
            return pathlib.Path(p)
    return None

desktop_ids={}
# Recursive: wine entries live in applications/wine/Programs/... subdirs and
# would otherwise be silently missed. User shadows system by Desktop ID.
for d in ["/usr/share/applications",str(HOME/".local/share/applications"),
          "/var/lib/flatpak/exports/share/applications",
          str(HOME/".local/share/flatpak/exports/share/applications")]:
    for p in pathlib.Path(d).rglob("*.desktop"): desktop_ids[p.name]=p
named=set()
did_icon={}  # desktop_id -> Icon= name (for the DB diff below)
for did, p in desktop_ids.items():
    m=re.search(r'^Icon=(.+)$',p.read_text(errors="ignore"),re.M)
    if m and not m.group(1).strip().startswith("/"):
        named.add(m.group(1).strip()); did_icon[did]=m.group(1).strip()

# Only apps-context files count as "already tinted": a same-named file in
# preferences/status/etc. does not satisfy an apps lookup.
existing=set()
for d in STD_DIRS:
    existing|={p.stem for p in (OUT/d).glob("*") if p.is_file()}

db_apps=load_db_apps()
if db_apps is not None and not FORCE:
    # DB diff (v1.0.44): only apps that are NEW or whose Icon= changed
    # since the install-time snapshot get tinted. This is the whole
    # point of the DB -- retint after installing one app touches one
    # app's icons instead of re-auditing every installed app. New apps
    # show up in the start menu (.desktop dirs) first, so they are
    # caught here even with no desktop icon.
    new_ids={did for did in desktop_ids
             if did not in db_apps or db_apps[did]!=did_icon.get(did)}
    new_named={did_icon[did] for did in new_ids if did in did_icon}
    todo=sorted(n for n in new_named if n not in existing)
    print(f"icon-db diff: {len(db_apps)} known apps, "
          f"{len(new_ids)} new/changed, {len(todo)} new icons to tint")
else:
    if db_apps is None:
        print("icon-db: no DB found - full audit this run, DB will be built at the end")
    todo=sorted(n for n in named if n not in existing or FORCE)
    print(f"app icons: {len(named)} total, {len(todo)} new/missing")

# ONE canonical source per name, /apps/ context only, fixed priority.
# Searching every theme/context by stem returns wrong artwork on collisions
# (e.g. a generic 'record' icon for steam) and rglob misses symlink dirs.
roots=[pathlib.Path("/usr/share/icons/Tela-red-dark"),pathlib.Path("/usr/share/icons/breeze"),
       pathlib.Path("/usr/share/icons/breeze-dark"),pathlib.Path("/usr/share/icons/hicolor"),
       pathlib.Path("/usr/share/icons/Papirus-Dark"),pathlib.Path("/usr/share/icons/Papirus"),
       pathlib.Path("/usr/share/icons/char-white"), HOME/".local/share/icons/YAMIS",
       pathlib.Path("/usr/share/pixmaps"),pathlib.Path("/var/lib/flatpak/exports/share/icons/hicolor"),
       HOME/".local/share/icons/hicolor"]

def find_source(name):
    hit = db_lookup(name)  # DB first (indexed); glob fallback below
    if hit is not None:
        return hit
    for root in roots:
        if not root.exists(): continue
        cands=[]
        for sub in ("scalable/apps","*-hires/apps","*x*/apps","apps"):
            cands+= [p for p in root.glob(sub+"/*") if p.is_file() and p.stem==name and p.suffix.lower() in (".svg",".png",".jpg",".jpeg")]
        if root.name=="pixmaps":  # pixmap-only apps have no apps/ context
            cands+= [p for p in root.glob("*") if p.is_file() and p.stem==name and p.suffix.lower() in (".svg",".png",".jpg",".jpeg")]
        if cands:
            svgs=[p for p in cands if p.suffix==".svg"]
            return svgs[0] if svgs else sorted(cands,key=lambda p:p.stat().st_size,reverse=True)[0]
    return None

_tinted_apps = 0
for name in todo:
    src=find_source(name)
    if not src:
        print(f"  SKIP {name}: no source icon found"); continue
    _tinted_apps += 1

    bright = is_widget_icon(name)
    if bright and not BRIGHT:
        print(f"  [BRIGHT] {name} (widget icon -> bright red)")
    elif BRIGHT:
        print(f"  [BRIGHT] {name} (--bright mode)")
    else:
        print(f"  tinted {name} from {src} (dark red)")

    if src.suffix.lower()==".svg" and "data:image/" in src.read_text(errors="ignore")[:200000]:
        subprocess.run(["rsvg-convert","-w","512","-h","512",str(src),"-o","/tmp/_r.png"],check=True)
        tint_png("/tmp/_r.png",name+".png", bright)
    elif src.suffix.lower()==".svg":
        tint_svg_file(src,name+".svg", bright)
    else:
        tint_png(src,name+".png", bright)

subprocess.run(["gtk-update-icon-cache","-f","-t",str(OUT)])
subprocess.run(["kbuildsycoca6","--noincremental"])

# --- Full retint pipeline: run EVERY icon script, not just app icons. ---
# A new app install can add titlebar minis, tray variants, preferences
# entries, Breeze widget icons and folder-index gaps too; tinting only
# the apps context leaves those original-coloured. All scripts below
# are idempotent, so running the whole pipeline is safe.
def _scripts_dir():
    here = pathlib.Path(__file__).resolve().parent
    if (here / "fix-mini-icons.py").exists():
        return here
    repo = HOME / "SkynetRedBlack" / "scripts"
    if (repo / "fix-mini-icons.py").exists():
        return repo
    return here

PIPELINE = [
    ("fix-mini-icons.py", []),          # titlebar app-ID aliases
    ("tint-breeze.py", []),              # all Breeze widget/system contexts
    ("fix-tray-icons.py", [str(OUT)]),  # steam/audio/cachy bright red
    ("normalize-preferences.py", []),   # preferences context dark red
    ("fix-copy-icon.py", [str(OUT)]),   # copy icons visible dark red
    ("fix-folder-index.py", [str(OUT)]),# index.theme places sections
    ("fix-davinci-icon.py", []),        # DaVinci PNGs + black emblems (skips if absent)
    ("scan-all-icons.py", []),          # any other SVG icon packs/widgets
]

def _theme_changed_since(t0):
    """True if any file under OUT has mtime > t0 (pipeline wrote something)."""
    for p in OUT.rglob("*"):
        try:
            if p.is_file() and p.stat().st_mtime > t0:
                return True
        except OSError:
            continue
    return False

def run_pipeline():
    sdir = _scripts_dir()
    t0 = time.time()
    print(f"Running full retint pipeline from {sdir} ...")
    # v1.0.45: scan-all-icons refreshes the DB itself; suppress that
    # here so retint refreshes ONCE at the end (was: two full icon-db
    # builds per retint, ~2.5 min wasted).
    env = dict(os.environ, SKYNET_SKIP_DB_REFRESH="1")
    for script, args in PIPELINE:
        path = sdir / script
        if not path.exists():
            print(f"  [skip] {script}: not found in {sdir}")
            continue
        print(f"  [run] {script}")
        r = subprocess.run([sys.executable, str(path), *args], env=env)
        if r.returncode != 0:
            print(f"  [warn] {script} exited {r.returncode} (continuing)")
    subprocess.run(["gtk-update-icon-cache","-f","-t",str(OUT)])
    subprocess.run(["kbuildsycoca6","--noincremental"])
    # v1.0.45: restart the shell ONLY if the pipeline actually wrote
    # icons. The old code restarted plasmashell on every run — via the
    # weekly systemd timer that means an unasked-for shell restart
    # (lost widget state/clipboard) even when nothing changed.
    # v1.0.52: the restart can be switched off entirely with
    # `cyberdyne-auto shell-restart disable` (writes "disabled" to
    # ~/.config/SkynetRedBlack/shell-restart). Default is enabled.
    shell_off = False
    try:
        shell_off = (HOME / ".config/SkynetRedBlack/shell-restart"
                     ).read_text().strip().lower() == "disabled"
    except OSError:
        pass
    if _tinted_apps or _theme_changed_since(t0):
        if shell_off:
            print("done - icons changed; Plasma shell left running "
                  "(shell-restart disabled - enable it with "
                  "'cyberdyne-auto shell-restart enable')")
        else:
            subprocess.run(["systemctl","--user","restart","plasma-plasmashell.service"],
                           capture_output=True)
            print("done - Plasma shell restarted; running apps need a restart to pick up new mini icons")
    else:
        print("done - no new icons; Plasma shell left running")

def refresh_db():
    """Rebuild the install-time snapshot after a retint, so the NEXT
    retint diffs against the new state. Best-effort: a missing
    icon-db.py must never fail a retint that already did its work."""
    if SKIP_DB:
        return
    sdir = _scripts_dir()
    script = sdir / "icon-db.py"
    if not script.exists():
        alt = HOME / ".local/bin" / "icon-db.py"
        script = alt if alt.exists() else script
    if not script.exists():
        print("  [skip] icon-db.py not found - DB not refreshed")
        return
    print("Refreshing icon-db (next retint will diff against this) ...")
    r = subprocess.run([sys.executable, str(script), "update"],
                       capture_output=True, text=True)
    print("  " + (r.stdout.strip().splitlines()[-1] if r.stdout.strip()
                  else f"[warn] icon-db update exited {r.returncode}"))

if "--apps-only" not in sys.argv:
    run_pipeline()
else:
    print("done - restart Plasma shell to see new icons")
refresh_db()
