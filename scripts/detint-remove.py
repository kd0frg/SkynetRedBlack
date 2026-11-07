#!/usr/bin/env python3
"""Cyberdyne Skynet Red/Black - detint / uninstall the red icon tint.

This is the reverse of scripts/retint-new-icons.py (installed as
~/.local/bin/cyberdyne-detint). It runs like retint does: by default it
runs the FULL detint, the same way a bare `cyberdyne-retint` runs the
full retint pipeline; narrow it with --apps-only.

What detint does (default, in-place detint):
  Removes every tinted icon file from the SkynetRedBlack icon theme
  (~/.local/share/icons/SkynetRedBlack). Tinting is lossy (original
  colours are not stored), so detint does NOT try to un-tint pixels -
  it deletes the tinted red copies. The icon loader then falls back
  through the theme's Inherits chain (Tela-red-dark/Breeze/hicolor) to
  the original, untinted icons, which is exactly the pre-tint look.
  Then it rebuilds the icon cache and, if anything changed, restarts
  the Plasma shell (unless shell-restart is disabled - see
  cyberdyne-auto shell-restart disable).

Usage:
  cyberdyne-detint                    # full in-place detint (all contexts)
  cyberdyne-detint --apps-only        # detint the apps context only
  cyberdyne-detint --dry-run          # report what would go, change nothing
  cyberdyne-detint --no-shell-restart # detint but never restart plasmashell
  cyberdyne-detint --total            # TOTAL uninstall (see below)

--total / --uninstall goes further than detinting: after detinting it
also removes the whole SkynetRedBlack icon theme directory, the
icon/app database (~/.local/share/SkynetRedBlack/), the installed
retint/detint/auto scripts in ~/.local/bin, and the systemd auto-scan
units (cyberdyne-retint.timer/.path/.service, disabled + stopped),
and switches the active icon theme in ~/.config/kdeglobals back to
Breeze if it was SkynetRedBlack. Colour scheme, wallpaper, cursor and
Konsole files are NOT touched - this is the icon/retint uninstaller.

Optional first argument: a theme root other than the default
(e.g. for testing on a copy of the theme).
"""
import pathlib
import shutil
import subprocess
import sys

HOME = pathlib.Path.home()
OUT = HOME / ".local/share/icons/SkynetRedBlack"
DB_DIR = HOME / ".local/share/SkynetRedBlack"
BIN_DIR = HOME / ".local/bin"
SYSTEMD_DIR = HOME / ".config/systemd/user"
KDEGLOBALS = HOME / ".config/kdeglobals"
SHELL_RESTART_CFG = HOME / ".config/SkynetRedBlack/shell-restart"

ARGS = sys.argv[1:]
APPS_ONLY = "--apps-only" in ARGS
TOTAL = "--total" in ARGS or "--uninstall" in ARGS
DRY_RUN = "--dry-run" in ARGS
NO_SHELL = "--no-shell-restart" in ARGS

# Optional positional theme root (first non-flag argument).
_theme_arg = next((a for a in ARGS if not a.startswith("--")), None)
if _theme_arg:
    OUT = pathlib.Path(_theme_arg).expanduser()


def shell_restart_enabled():
    """Shell restart is on by default; cyberdyne-auto can turn it off
    by writing 'disabled' to ~/.config/SkynetRedBlack/shell-restart.
    (Same check retint-new-icons.py uses - keep them in sync.)"""
    if NO_SHELL:
        return False
    try:
        return SHELL_RESTART_CFG.read_text().strip().lower() != "disabled"
    except OSError:
        return True


def detint_files():
    """Yield every tinted icon file that a detint would remove."""
    if not OUT.exists():
        return []
    if APPS_ONLY:
        files = []
        for d in OUT.rglob("apps"):
            if d.is_dir():
                files += [p for p in d.rglob("*") if p.is_file()]
        return sorted(set(files))
    return sorted(p for p in OUT.rglob("*") if p.is_file())


def rebuild_cache_and_refresh():
    subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(OUT)],
                   capture_output=True)
    subprocess.run(["kbuildsycoca6", "--noincremental"], capture_output=True)


def restart_shell_if_changed(changed):
    if not changed:
        print("done - nothing to detint; Plasma shell left running")
        return
    if shell_restart_enabled():
        subprocess.run(
            ["systemctl", "--user", "restart", "plasma-plasmashell.service"],
            capture_output=True)
        print("done - Plasma shell restarted")
    else:
        print("done - Plasma shell left running (shell-restart is "
              "disabled; enable it with: cyberdyne-auto shell-restart enable)")


def total_uninstall():
    """Remove the retint system entirely. Returns True if anything went."""
    changed = False

    # systemd auto-scan units first, so nothing re-tints mid-uninstall.
    for unit in ("cyberdyne-retint.timer", "cyberdyne-retint.path",
                 "cyberdyne-retint.service"):
        p = SYSTEMD_DIR / unit
        if p.exists():
            changed = True
            if DRY_RUN:
                print(f"  [dry-run] would disable/stop + remove {p}")
            else:
                subprocess.run(
                    ["systemctl", "--user", "disable", "--now",
                     unit], capture_output=True)
                p.unlink()
                print(f"  removed {p}")
    subprocess.run(["systemctl", "--user", "daemon-reload"],
                   capture_output=True)

    # Installed retint/detint/auto scripts + their icon helpers.
    for name in ("cyberdyne-retint", "cyberdyne-detint", "cyberdyne-auto",
                 "retint-new-icons.py", "detint-remove.py",
                 "auto-retint.py", "fix-mini-icons.py", "tint-breeze.py",
                 "fix-tray-icons.py", "normalize-preferences.py",
                 "fix-copy-icon.py", "fix-folder-index.py",
                 "fix-davinci-icon.py", "scan-all-icons.py",
                 "icon-db.py", "set-brave-system-titlebar.py",
                 "redtint.py"):
        p = BIN_DIR / name
        if p.exists() or p.is_symlink():
            changed = True
            if DRY_RUN:
                print(f"  [dry-run] would remove {p}")
            else:
                p.unlink()
                print(f"  removed {p}")

    # Icon/app database.
    if DB_DIR.exists():
        changed = True
        if DRY_RUN:
            print(f"  [dry-run] would remove {DB_DIR} (icon database)")
        else:
            shutil.rmtree(DB_DIR)
            print(f"  removed {DB_DIR} (icon database)")

    # The icon theme itself.
    if OUT.exists():
        changed = True
        if DRY_RUN:
            print(f"  [dry-run] would remove icon theme {OUT}")
        else:
            shutil.rmtree(OUT)
            print(f"  removed icon theme {OUT}")

    # Switch the active icon theme back to Breeze if we were the theme.
    if KDEGLOBALS.exists():
        text = KDEGLOBALS.read_text(errors="ignore")
        if "Theme=SkynetRedBlack" in text:
            changed = True
            if DRY_RUN:
                print("  [dry-run] would set [Icons] Theme=breeze in kdeglobals")
            else:
                KDEGLOBALS.write_text(
                    text.replace("Theme=SkynetRedBlack", "Theme=breeze"))
                print("  kdeglobals: icon theme set back to breeze")
                subprocess.run(["kbuildsycoca6", "--noincremental"],
                               capture_output=True)
    return changed


def main():
    if not OUT.exists():
        print(f"no SkynetRedBlack icon theme at {OUT} - nothing to detint")
        if TOTAL:
            total_uninstall()
        return 0

    files = detint_files()
    scope = "apps context only" if APPS_ONLY else "all contexts"
    print(f"detint: {len(files)} tinted icon files in {OUT} ({scope})")
    if DRY_RUN:
        for p in files[:20]:
            print(f"  [dry-run] would remove {p}")
        if len(files) > 20:
            print(f"  [dry-run] ... and {len(files) - 20} more")
    else:
        for p in files:
            p.unlink()
        # Drop the stale cache so the loader re-reads the theme.
        (OUT / "icon-theme.cache").unlink(missing_ok=True)
        rebuild_cache_and_refresh()
        print(f"detinted: removed {len(files)} tinted files; "
              "originals now show via theme inheritance")

    if DRY_RUN:
        print("dry-run: nothing was changed and the Plasma shell was "
              "not restarted")
        if TOTAL:
            print("total uninstall: would remove retint system ...")
            total_uninstall()
        return 0

    if TOTAL:
        print("total uninstall: removing retint system ...")
        changed = total_uninstall()
        restart_shell_if_changed(bool(files) or changed)
    else:
        restart_shell_if_changed(bool(files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
