#!/usr/bin/env python3
"""Cyberdyne Skynet Red/Black — turn OFF everything automatic.

One command to switch off the two automatic behaviours that sit beside
retint/detint, without touching your (already red) icons:

  1. The auto scanner — systemd user units cyberdyne-retint.timer
     (weekly safety-net, 5 min after boot) and cyberdyne-retint.path
     (inotify watcher that fires retint instantly when an app is
     installed/removed). Both run cyberdyne-retint.
  2. The Plasma shell restart — retint/detint restart plasmashell only
     when icons actually changed, gated by the plain file
     ~/.config/SkynetRedBlack/shell-restart (enabled/disabled).

`cyberdyne-off` disables + stops + removes the scanner units (so they
cannot be resurrected on the next install or on reboot) and writes
`disabled` to the shell-restart file. It does NOT detint: your red
icons stay exactly as they are; you just stop the automatic machinery
and the shell stop bouncing on boot / on a weekly schedule / when you
install an app. Re-tint anytime by hand with `cyberdyne-retint`.

Usage (installed as ~/.local/bin/cyberdyne-off):
  cyberdyne-off            # scanner OFF (units removed) + shell restart disabled
  cyberdyne-off --status   # show current scanner + shell-restart state
  cyberdyne-off --enable   # (re)install + enable the scanner and restart

With no argument, `--status` is shown.
"""
import pathlib
import shutil
import subprocess
import sys

HOME = pathlib.Path.home()
CFG_DIR = HOME / ".config/SkynetRedBlack"
SHELL_CFG = CFG_DIR / "shell-restart"
UNITS = ("cyberdyne-retint.timer", "cyberdyne-retint.path")
SERVICES = ("cyberdyne-retint.service",)
USER_DIR = HOME / ".config/systemd/user"


def find_repo():
    """Locate the SkynetRedBlack checkout so --enable can restore units."""
    for c in (HOME / "SkynetRedBlack", pathlib.Path("/home/cole/SkynetRedBlack")):
        if (c / "systemd").is_dir():
            return c
    return None


def run(*args):
    return subprocess.run(["systemctl", "--user", *args],
                          capture_output=True, text=True)


def unit_state(unit):
    enabled = run("is-enabled", unit).stdout.strip() or "unknown"
    active = run("is-active", unit).stdout.strip() or "unknown"
    return enabled, active


def scanner_on():
    return all(unit_state(u)[0] == "enabled" for u in UNITS)


def shell_restart_status():
    try:
        return SHELL_CFG.read_text().strip().lower()
    except OSError:
        return "enabled"  # default when no config file exists


def show_status():
    print("auto scanner:")
    for u in UNITS:
        en, ac = unit_state(u)
        print(f"  {u}: {en}, {ac}")
    print(f"  scanner overall: {'ON' if scanner_on() else 'OFF'}")
    print(f"shell restart after retint/detint: {shell_restart_status()}")
    print(f"  (setting file: {SHELL_CFG})")


def disable_scanner():
    """Stop + disable the units, then remove them so they can't come back."""
    run("disable", "--now", *UNITS)
    for u in SERVICES + UNITS:
        p = USER_DIR / u
        if p.exists():
            p.unlink()
    run("daemon-reload")


def enable_scanner():
    """Reinstall the units from the checkout and turn them back on."""
    repo = find_repo()
    USER_DIR.mkdir(parents=True, exist_ok=True)
    if repo is not None:
        for u in SERVICES + UNITS:
            src = repo / "systemd" / u
            if src.exists():
                shutil.copy(src, USER_DIR / u)
    run("daemon-reload")
    r = run("enable", "--now", *UNITS)
    if r.returncode:
        print(r.stderr.strip() or "(systemctl reported an error)")


def main(argv):
    if argv and argv[0] in ("status", "--status", "show"):
        show_status()
        return 0

    # No argument (or an explicit off/disable) turns everything off.
    if not argv or argv[0] in ("off", "disable", "off-all", "turn-off"):
        disable_scanner()
        CFG_DIR.mkdir(parents=True, exist_ok=True)
        SHELL_CFG.write_text("disabled\n")
        print("cyberdyne-off: scanner OFF (timer + path removed) and shell restart disabled")
        print("Red icons are untouched (no detint). Your icons stay as-is.")
        print("Re-tint by hand anytime:  cyberdyne-retint")
        print("Restore the auto scanner + restart:  cyberdyne-off --enable")
        print()
        show_status()
        return 0

    if argv[0] == "enable":
        enable_scanner()
        CFG_DIR.mkdir(parents=True, exist_ok=True)
        SHELL_CFG.write_text("enabled\n")
        print("cyberdyne-off: scanner enabled + shell restart re-enabled")
        print()
        show_status()
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
