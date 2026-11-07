#!/usr/bin/env python3
"""Make Brave/Chromium use the system (KWin) title bar, so its
minimize/maximize/close buttons are drawn by the window decoration
(red, via the SkynetRedBlack desktoptheme) instead of Chromium's own
client-side white glyphs.

Chromium pref: browser.custom_chrome_frame = false
("Use system title bar and borders", IDC_USE_SYSTEM_TITLE_BAR).

Safe to run only when Brave is NOT running: Brave rewrites its
Preferences on exit, so editing while it runs is silently discarded.
Exits 2 with a clear message if Brave is running.
"""
import json
import pathlib
import subprocess
import sys


def brave_running() -> bool:
    # Exact process name only: pgrep -f "brave-bin/brave" also matches
    # the shell that happens to contain that string in its command line.
    return subprocess.run(
        ["pgrep", "-x", "brave"], capture_output=True
    ).returncode == 0


def main() -> int:
    prefs = (
        pathlib.Path.home()
        / ".config/BraveSoftware/Brave-Browser/Default/Preferences"
    )
    if not prefs.exists():
        print(f"no Brave Preferences at {prefs}; nothing to do")
        return 0
    if brave_running():
        print(
            "Brave is running — close it first, then re-run this script. "
            "Editing Preferences while Brave runs is discarded on exit."
        )
        return 2
    data = json.loads(prefs.read_text())
    browser = data.setdefault("browser", {})
    if browser.get("custom_chrome_frame") is False:
        print("already using system title bar")
        return 0
    browser["custom_chrome_frame"] = False
    prefs.write_text(json.dumps(data))
    print("set browser.custom_chrome_frame=false (use system title bar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
