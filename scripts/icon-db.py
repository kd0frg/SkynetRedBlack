#!/usr/bin/env python3
"""SkynetRedBlack icon/app database (v1.0.44).

A fast, indexed snapshot of the system so retint is a DIFF, not a full
rescan:

  icons(stem, path, ext, size, mtime, ctx)  -- every image icon on `/`
  apps(desktop_id, icon, name, path, mtime) -- every installed app
                                               (start-menu .desktop files)
  meta(key, value)                          -- version / build time / counts

Built ONCE at install time (`./install.sh` runs `icon-db.py build` after
the tint pipeline). On retint, `retint-new-icons.py` and
`scan-all-icons.py --incremental` compare the CURRENT app/icon lists
against this DB and only process what is new or changed -- a handful of
`.desktop` files + a filename-only walk, instead of reading/tinting every
SVG on the system. The DB is refreshed at the end of each retint.

Format: SQLite (stdlib) -- indexed lookups `WHERE stem = ?` are O(log n)
vs. a filesystem glob per icon name. The live DB lives at
~/.local/share/SkynetRedBlack/icon-db.sqlite3 (override with --db or
$SKYNET_ICON_DB). It's a local cache only; it is NOT shipped in any
tarball, and deleting it is safe (next retint rebuilds it).

Usage:
  icon-db.py build [--db PATH] [--root DIR ...]   full scan (install time)
  icon-db.py check [--apps-only]                  print new/changed vs DB
  icon-db.py update                               alias for build
  icon-db.py lookup STEM                          print known paths for STEM
  icon-db.py stats                                row counts + meta
Exit codes: build/update 0; check 0 (even when empty); lookup 1 if absent.
"""
import argparse
import json
import os
import pathlib
import re
import sqlite3
import sys
import time

HOME = pathlib.Path.home()
DEFAULT_DB = HOME / ".local/share/SkynetRedBlack" / "icon-db.sqlite3"
VERSION = "1.0.50"

IMAGE_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".xpm", ".svgz"}
# Trees that are never icon locations / are huge and irrelevant. Pruned
# during the walk (in-place) so a full `/` scan stays a filename walk.
SKIP_PREFIXES = (
    "/proc/", "/sys/", "/dev/", "/run/", "/boot/", "/snap/",
    "/.snapshots/", "/media/", "/mnt/", "/var/cache/", "/var/lib/snapd/",
    "/sysroot/",
)
SKIP_DIRNAMES = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules",
    ".cache", ".rustup", ".cargo", ".npm", ".local/share/Trash",
}
# The theme itself holds ~38k tinted copies; indexing them is pure bloat
# and walking it dominates scan time.
THEME_DIR = HOME / ".local/share/icons/SkynetRedBlack"

CONTEXTS = {"apps", "actions", "status", "panel", "places", "devices",
            "emblems", "mimetypes", "categories", "preferences",
            "applets", "symbolic", "media", "tray", "indicator", "menu",
            "launcher", "kickoff", "system-status"}
SIZES = {"16", "22", "24", "32", "48", "64", "96", "128", "256", "512"}

# Full-system scan roots: walk `/` conceptually, but only the trees that
# can hold icons, with system/cache trees pruned. Dedupe by realpath.
def default_roots():
    # v1.0.45: only icon-bearing trees. The old list walked bare
    # /usr/share AND /usr/share/icons AND /usr/share/pixmaps (3x the
    # same subtree, plus /usr/share/doc/man images that are not icons),
    # which is why the DB reached 715k rows / 172 MB. Doc/man/diagram
    # images are never referenced as app icons.
    return [
        pathlib.Path("/usr/share/icons"),
        pathlib.Path("/usr/local/share/icons"),
        pathlib.Path("/usr/share/pixmaps"),
        pathlib.Path("/usr/local/share/pixmaps"),
        pathlib.Path("/opt"),
        pathlib.Path("/var/lib/flatpak/exports/share/icons"),
        HOME / ".local/share/icons",
        HOME / ".icons",
        HOME / ".local/share/flatpak/exports/share/icons",
        HOME / ".local/share/applications",
    ]

DESKTOP_DIRS = [
    "/usr/share/applications", "/usr/local/share/applications",
    str(HOME / ".local/share/applications"),
    "/var/lib/flatpak/exports/share/applications",
    str(HOME / ".local/share/flatpak/exports/share/applications"),
]


def extract_ctx(path):
    parts = path.parts
    ctx = "apps"
    for i, part in enumerate(parts):
        if part == "scalable" and i + 1 < len(parts) and parts[i + 1] in CONTEXTS:
            ctx = parts[i + 1]
        elif part in CONTEXTS and i + 1 < len(parts):
            nxt = parts[i + 1]
            if nxt in SIZES or nxt in ("scalable",) or nxt in CONTEXTS:
                ctx = part
        elif part in SIZES and i + 1 < len(parts) and parts[i + 1] in CONTEXTS:
            ctx = parts[i + 1]
    return ctx


def walk_icons(roots):
    """Yield (path, stat) for every image file under roots.

    Filename + stat only -- file CONTENTS are never read here, which is
    what makes the build cheap relative to a tint scan.
    """
    seen = set()
    theme_real = None
    try:
        theme_real = str(THEME_DIR.resolve())
    except Exception:
        pass
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # prune in place
            dirnames[:] = [d for d in dirnames
                           if d not in SKIP_DIRNAMES
                           and not (dirpath + "/" + d).startswith(SKIP_PREFIXES)]
            # v1.0.45: compare unresolved path strings — resolve() per
            # directory costs a syscall each and dominates the walk.
            if theme_real and dirpath == theme_real:
                dirnames[:] = []
                continue
            for fn in filenames:
                if pathlib.PurePath(fn).suffix.lower() not in IMAGE_EXTS:
                    continue
                p = pathlib.Path(dirpath) / fn
                # v1.0.45: dedupe on the RESOLVED path (as pre-1.0.45).
                # /usr/share/icons holds ~519k symlinks (breeze @2x/@3x
                # sizes etc.); deduping on the unresolved path would
                # inflate the DB with one row per symlink and break
                # diff-compatibility with existing DBs.
                try:
                    real = str(p.resolve())
                except Exception:
                    real = str(p)
                if real in seen:
                    continue
                seen.add(real)
                try:
                    st = p.stat()
                except OSError:
                    continue
                yield pathlib.Path(real), st


def scan_desktop():
    """Return {desktop_id: (icon_name_or_None, display_name, path, mtime)}.

    User shadows system by Desktop ID (same rule as retint). This is the
    start-menu app list -- new apps appear here first, long before any
    desktop icon is created.
    """
    apps = {}
    for d in DESKTOP_DIRS:
        base = pathlib.Path(d)
        if not base.exists():
            continue
        for p in base.rglob("*.desktop"):
            try:
                txt = p.read_text(errors="ignore")
            except OSError:
                continue
            icon = None
            m = re.search(r"^Icon=(.+)$", txt, re.M)
            if m and not m.group(1).strip().startswith("/"):
                icon = m.group(1).strip()
            name = None
            nm = re.search(r"^Name=(.+)$", txt, re.M)
            if nm:
                name = nm.group(1).strip()
            try:
                mt = int(p.stat().st_mtime)
            except OSError:
                mt = 0
            apps[p.name] = (icon, name, str(p), mt)
    return apps


SCHEMA = """
CREATE TABLE IF NOT EXISTS icons(
  stem TEXT NOT NULL, path TEXT NOT NULL, ext TEXT NOT NULL,
  size INTEGER NOT NULL, mtime INTEGER NOT NULL, ctx TEXT NOT NULL,
  PRIMARY KEY(path));
CREATE INDEX IF NOT EXISTS idx_icons_stem ON icons(stem);
CREATE TABLE IF NOT EXISTS apps(
  desktop_id TEXT PRIMARY KEY, icon TEXT, name TEXT,
  path TEXT NOT NULL, mtime INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def connect(db_path):
    db_path = pathlib.Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    return con


def cmd_build(args):
    roots = [pathlib.Path(r) for r in args.root] if args.root else default_roots()
    con = connect(args.db)
    cur = con.cursor()
    cur.execute("DELETE FROM icons")
    cur.execute("DELETE FROM apps")
    t0 = time.time()
    n = 0
    rows = []
    for p, st in walk_icons(roots):
        rows.append((p.stem, str(p), p.suffix.lower(),
                     st.st_size, int(st.st_mtime), extract_ctx(p)))
        n += 1
        if n % 20000 == 0:
            print(f"  indexed {n} icons...", flush=True)
    cur.executemany(
        "INSERT OR REPLACE INTO icons(stem,path,ext,size,mtime,ctx)"
        " VALUES(?,?,?,?,?,?)", rows)
    apps = scan_desktop()
    cur.executemany(
        "INSERT OR REPLACE INTO apps(desktop_id,icon,name,path,mtime)"
        " VALUES(?,?,?,?,?)",
        [(did, icon, name, path, mt) for did, (icon, name, path, mt) in apps.items()])
    elapsed = time.time() - t0
    for k, v in [("version", VERSION), ("built_at", str(int(time.time()))),
                 ("icons", str(len(rows))), ("apps", str(len(apps))),
                 ("build_seconds", f"{elapsed:.1f}"),
                 ("roots", ",".join(str(r) for r in roots))]:
        cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (k, v))
    con.commit()
    # v1.0.45: DELETE+INSERT rebuilds leave the file at its high-water
    # mark forever; VACUUM reclaims it (172 MB -> ~160 MB measured).
    con.execute("VACUUM")
    con.commit()
    con.close()
    print(f"icon-db built: {len(rows)} icons, {len(apps)} apps "
          f"in {elapsed:.1f}s -> {args.db}")
    return 0


def cmd_update(args):
    """Incremental refresh: apply only new/changed/vanished rows.

    v1.0.45: `update` used to be an alias for `build` — a full
    DELETE+INSERT of 715k rows (~72s) at the end of EVERY retint.
    Now it diffs (path,size,mtime) against the DB and only touches
    what changed (~1-2s in steady state). `build` stays the full
    rebuild for install time / explicit --full runs.
    """
    db = pathlib.Path(args.db)
    if not db.exists():
        return cmd_build(args)
    con = connect(args.db)
    t0 = time.time()
    known = {(r[0], r[1], r[2]) for r in con.execute("SELECT path,size,mtime FROM icons")}
    known_paths = {k[0] for k in known}
    roots = [pathlib.Path(r) for r in args.root] if args.root else default_roots()
    seen_paths = set()
    upserts, n = [], 0
    for p, st in walk_icons(roots):
        key = (str(p), st.st_size, int(st.st_mtime))
        seen_paths.add(str(p))
        if key not in known:
            upserts.append((p.stem, str(p), p.suffix.lower(),
                            st.st_size, int(st.st_mtime), extract_ctx(p)))
            n += 1
    vanished = known_paths - seen_paths
    con.executemany(
        "INSERT OR REPLACE INTO icons(stem,path,ext,size,mtime,ctx)"
        " VALUES(?,?,?,?,?,?)", upserts)
    con.executemany("DELETE FROM icons WHERE path=?",
                    [(p,) for p in vanished])
    known_apps = _load_known_apps(con)
    apps = scan_desktop()
    con.executemany(
        "INSERT OR REPLACE INTO apps(desktop_id,icon,name,path,mtime)"
        " VALUES(?,?,?,?,?)",
        [(did, icon, name, path, mt) for did, (icon, name, path, mt) in apps.items()])
    con.executemany("DELETE FROM apps WHERE desktop_id=?",
                    [(did,) for did in set(known_apps) - set(apps)])
    for k, v in [("version", VERSION), ("built_at", str(int(time.time()))),
                 ("icons", str(con.execute("SELECT COUNT(*) FROM icons").fetchone()[0])),
                 ("apps", str(len(apps))),
                 ("build_seconds", f"{time.time() - t0:.1f}")]:
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (k, v))
    con.commit()
    if n or vanished:
        con.execute("VACUUM")
        con.commit()
    con.close()
    print(f"icon-db updated incrementally: {n} new/changed, "
          f"{len(vanished)} vanished icons in {time.time() - t0:.1f}s -> {args.db}")
    return 0


def _load_known_apps(con):
    return {r[0]: (r[1], r[2], r[3], r[4])
            for r in con.execute("SELECT desktop_id,icon,name,path,mtime FROM apps")}


def cmd_check(args):
    db = pathlib.Path(args.db)
    if not db.exists():
        print(json.dumps({"db_exists": False, "new_apps": [], "changed_apps": [],
                          "new_icons": [], "changed_icons": []}))
        return 0
    con = connect(db)
    known_apps = _load_known_apps(con)
    known_icons = {(r[0], r[1], r[2]) for r in con.execute(
        "SELECT path,size,mtime FROM icons")}
    con.close()

    current_apps = scan_desktop()
    new_apps, changed_apps = [], []
    for did, (icon, name, path, mt) in current_apps.items():
        if did not in known_apps:
            new_apps.append({"desktop_id": did, "icon": icon, "name": name})
        elif known_apps[did] != (icon, name, path, mt):
            changed_apps.append({"desktop_id": did, "icon": icon, "name": name})

    new_icons, changed_icons = [], []
    if not args.apps_only:
        roots = [pathlib.Path(r) for r in args.root] if args.root else default_roots()
        # v1.0.45: path -> (size, mtime) dict. The old code did
        # `any(k[0] == str(p) for k in known_icons)` per new icon —
        # O(n) per icon, O(n^2) overall (715k rows = hours after an
        # update lands hundreds of new icons).
        known_by_path = {k[0]: k for k in known_icons}
        for p, st in walk_icons(roots):
            if (str(p), st.st_size, int(st.st_mtime)) in known_icons:
                continue
            entry = {"stem": p.stem, "path": str(p), "ext": p.suffix.lower()}
            (changed_icons if str(p) in known_by_path else new_icons).append(entry)

    out = {"db_exists": True, "new_apps": new_apps, "changed_apps": changed_apps,
           "new_icons": new_icons, "changed_icons": changed_icons}
    print(json.dumps(out))
    return 0


def cmd_lookup(args):
    con = connect(args.db)
    rows = con.execute(
        "SELECT path,ext,ctx FROM icons WHERE stem=? ORDER BY "
        "CASE ext WHEN '.svg' THEN 0 ELSE 1 END, path", (args.stem,)).fetchall()
    con.close()
    for r in rows:
        print(r[0])
    return 0 if rows else 1


def cmd_stats(args):
    db = pathlib.Path(args.db)
    if not db.exists():
        print(f"no DB at {db} (run: icon-db.py build)")
        return 0
    con = connect(db)
    icons = con.execute("SELECT COUNT(*) FROM icons").fetchone()[0]
    apps = con.execute("SELECT COUNT(*) FROM apps").fetchone()[0]
    meta = dict(con.execute("SELECT key,value FROM meta"))
    con.close()
    print(f"DB: {db}")
    print(f"icons: {icons}, apps: {apps}")
    for k in sorted(meta):
        print(f"{k}: {meta[k]}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="SkynetRedBlack icon/app database")
    ap.add_argument("--db", default=os.environ.get("SKYNET_ICON_DB", str(DEFAULT_DB)))
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--root", action="append")
    u = sub.add_parser("update"); u.add_argument("--root", action="append")
    c = sub.add_parser("check"); c.add_argument("--apps-only", action="store_true")
    c.add_argument("--root", action="append")
    l = sub.add_parser("lookup"); l.add_argument("stem")
    sub.add_parser("stats")
    args = ap.parse_args(argv)
    if args.cmd == "build":
        return cmd_build(args)
    if args.cmd == "update":
        return cmd_update(args)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "lookup":
        return cmd_lookup(args)
    if args.cmd == "stats":
        return cmd_stats(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
