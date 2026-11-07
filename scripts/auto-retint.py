#!/usr/bin/env python3
"""Cyberdyne Skynet Red/Black - auto-scan & shell-restart toggle.

Controls the two automatic behaviours that sit alongside retint/detint:

1. The auto scanner: systemd user units cyberdyne-retint.timer
   (a weekly safety-net run of cyberdyne-retint) and
   cyberdyne-retint.path (an inotify watcher that runs it instantly
   whenever an app is installed/removed). Together they are the
   "auto scanner" - new apps get their icons tinted without you
   running retint by hand.

2. The Plasma shell restart: retint/detint restart plasmashell after
   a run, but ONLY when icons actually changed. You can turn that
   restart off (e.g. if you never want a run to bounce your shell)
   while leaving the scanner on, or vice versa. It is stored as a
   plain file at ~/.config/SkynetRedBlack/shell-restart containing
   "enabled" (the default) or "disabled", which retint-new-icons.py
   and detint-remove.py both read. No date/time scheduling is built
   in - enable/disable is the whole control, and the timer's own
   weekly schedule is the only clock involved.

Usage (installed as ~/.local/bin/cyberdyne-auto):
  cyberdyne-auto enable                  # scanner on (timer + path watcher)
  cyberdyne-auto disable                 # scanner off (units disabled + stopped)
  cyberdyne-auto status                  # show scanner + shell-restart state
  cyberdyne-auto shell-restart enable    # retint/detint may restart plasmashell
  cyberdyne-auto shell-restart disable   # retint/detint never restart it
  cyberdyne-auto shell-restart status    # show the shell-restart setting

With no argument, `status` is shown.
"""
import pathlib
import subprocess
import sys

HOME = pathlib.Path.home()
CFG_DIR = HOME / ".config/SkynetRedBlack"
SHELL_CFG = CFG_DIR / "shell-restart"
UNITS = ("cyberdyne-retint.timer", "cyberdyne-retint.path")


def run(*args):
    return subprocess.run(["systemctl", "--user", *args],
                          capture_output=True, text=True)


def unit_state(unit):
    enabled = run("is-enabled", unit).stdout.strip() or "unknown"
    active = run("is-active", unit).stdout.strip() or "unknown"
    return enabled, active


def scanner_status():
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
    print(f"  scanner overall: {'ON' if scanner_status() else 'OFF'}")
    print(f"shell restart after retint/detint: {shell_restart_status()}")
    print(f"  (setting file: {SHELL_CFG})")


def main(argv):
    if not argv or argv[0] == "status":
        show_status()
        return 0

    if argv[0] == "enable":
        r = run("enable", "--now", *UNITS)
        print("auto scanner enabled: weekly timer + instant app-install watcher")
        if r.returncode:
            print(r.stderr.strip() or "(systemctl reported an error)")
        return r.returncode

    if argv[0] == "disable":
        r = run("disable", "--now", *UNITS)
        print("auto scanner disabled: timer + path watcher stopped")
        if r.returncode:
            print(r.stderr.strip() or "(systemctl reported an error)")
        return r.returncode

    if argv[0] == "shell-restart" and len(argv) == 2:
        if argv[1] == "status":
            print(f"shell restart: {shell_restart_status()}")
            return 0
        if argv[1] in ("enable", "disable"):
            CFG_DIR.mkdir(parents=True, exist_ok=True)
            # retint/detint check for exactly "disabled" - write that form.
            SHELL_CFG.write_text(
                ("disabled" if argv[1] == "disable" else "enabled") + "\n")
            print(f"shell restart {argv[1]}d (written to {SHELL_CFG})")
            return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
