#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "== SkynetRedBlack installer =="

# --pack: rebuild the release tarballs from this checkout and exit.
# (README says tarballs are "built by install.sh --pack or manually".)
if [ "${1:-}" = "--pack" ]; then
  echo "Packing release tarballs..."
  mkdir -p releases
  tar -czf releases/SkynetRedBlack-lookandfeel.tar.gz -C look-and-feel com.skynetredblack
  tar -czf releases/SkynetRedBlack-colorscheme.tar.gz -C colorschemes SkynetRedBlack.colors
  tar -czf releases/SkynetRedBlack-konsole.tar.gz -C konsole SkynetRedBlack.colorscheme SkynetRedBlack.profile
  tar -czf releases/SkynetRedBlack-cursor.tar.gz -C cursors Breeze_Dark_Red
  tar -czf releases/SkynetRedBlack-wallpaper.tar.gz -C wallpaper skynet-wallpaper.jpg
  if [ -d icons/SkynetRedBlack ]; then
    _icons_src="icons/SkynetRedBlack"
  else
    # Full-checkout icons are gitignored; pack the live installed theme.
    _icons_src="$HOME/.local/share/icons/SkynetRedBlack"
  fi
  # v1.0.46: pack the SLIM theme (SVGs once in scalable/, largest PNG
  # only — 81 MB -> ~21 MB). scripts/slim-icons.py, with a plain-tar
  # fallback if it is unavailable.
  _slim_tmp="$(mktemp -d)"
  if [ -f scripts/slim-icons.py ]; then
    python3 scripts/slim-icons.py "$_icons_src" "$_slim_tmp/SkynetRedBlack" --report
    tar -czf releases/SkynetRedBlack-icons.tar.gz -C "$_slim_tmp" SkynetRedBlack
  else
    tar -czf releases/SkynetRedBlack-icons.tar.gz -C "$(dirname "$_icons_src")" "$(basename "$_icons_src")"
  fi
  rm -rf "$_slim_tmp"
  echo "Packed:"; ls -la releases/*.tar.gz
  echo "Look-and-feel version:"; tar -xzOf releases/SkynetRedBlack-lookandfeel.tar.gz com.skynetredblack/metadata.json | grep '"Version"'
  sha256sum releases/*.tar.gz
  rm -rf /tmp/testroot && mkdir -p /tmp/testroot
  kpackagetool6 --type Plasma/LookAndFeel --packageroot /tmp/testroot --install look-and-feel/com.skynetredblack
  exit 0
fi

# icons (from icons/ dir in a full checkout, or the release tarball)
# v1.0.29: stage to a temp dir and copy IN PLACE - never rm -rf the live
# theme dir. Deleting it made running apps (Dolphin, Plasma) briefly lose
# the theme mid-install and fall back to blue Breeze folders/icons, and
# they never recovered until restarted.
mkdir -p "$HOME/.local/share/icons"
_tmp_icons="$(mktemp -d)"
trap 'rm -rf "$_tmp_icons"' EXIT
if [ -d icons/SkynetRedBlack ]; then
  cp -a icons/SkynetRedBlack "$_tmp_icons/"
elif [ -f releases/SkynetRedBlack-icons.tar.gz ]; then
  tar -xzf releases/SkynetRedBlack-icons.tar.gz -C "$_tmp_icons/"
else
  echo "ERROR: icons not found - download the icons tarball from Releases" >&2; exit 1
fi
mkdir -p "$HOME/.local/share/icons/SkynetRedBlack"
cp -a "$_tmp_icons/SkynetRedBlack/." "$HOME/.local/share/icons/SkynetRedBlack/"
rm -rf "$_tmp_icons"; trap - EXIT
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/SkynetRedBlack" || true

echo "Tinting icons..."
echo "[1/10] Copy icons..."

# Copy icon visible dark red (v1.0.24, was v1.0.21): even with the v1.0.20 DisabledEffect=colorize
# settings, Konsole's disabled Copy squares still rendered dark grey
# (43,43,43) while the "Copy" text went maroon — symbolic/disabled pixmap
# rendering doesn't reliably run the per-app KIconEffect. Fix at the source:
# recolour every *copy* action icon (edit-copy etc.) from bright #ff0000 to
# #8c0000 (140,0,0). v1.0.21 used #3c0000 (60,0,0) to match the disabled
# text, but at luminance ~18 on black the squares were effectively
# invisible - darker to the eye than the grey they replaced. #8c0000 has
# luminance ~42 (as visible as the old grey, top of the theme's dark-red
# range) and stays dark red in every rendering path. Also adds the missing
# 32/actions + scalable/actions sizes so KDE can't fall back to grey Breeze.
echo "[2/10] Visible copy icons..."
if [ -f scripts/fix-copy-icon.py ]; then
  python3 scripts/fix-copy-icon.py "$HOME/.local/share/icons/SkynetRedBlack" || true
fi

# DaVinci icon cleanup (v1.0.23): regenerate davinci-resolve PNGs from the
# clean dark-red SVG (removes salmon-pink #ff5959 highlight / white dot in
# the hicolor fallback) and add black symlink emblems at 32/48px (previously
# only 16/22/scalable existed, so desktop-size lookups fell back to light
# inherited emblems - the white dot / pink symlink overlay).
echo "[3/10] DaVinci icons..."
if [ -f scripts/fix-davinci-icon.py ]; then
  python3 scripts/fix-davinci-icon.py || true
fi

# Complete places index (v1.0.28): [96/128/256/places] were missing from
# index.theme, so KDE ignored those dirs. Idempotent; rebuilds the cache.
echo "[4/10] Folder index..."
if [ -f scripts/fix-folder-index.py ]; then
  python3 scripts/fix-folder-index.py "$HOME/.local/share/icons/SkynetRedBlack" || true
fi

# Mini titlebar icons (v1.0.31): tint every app-ID/Icon= name that was
# missing from the theme (org.kde.konsole, brave-browser, gimp, ...) to
# the theme dark red, so 16px window titlebar icons match the large ones.
echo "[5/10] Titlebar mini icons..."
if [ -f scripts/fix-mini-icons.py ]; then
  python3 scripts/fix-mini-icons.py || true
fi

# Whole Breeze set tinted in (v1.0.33): every Breeze icon missing from the
# theme is tinted red and bundled, so nothing falls back to Breeze colours
# at any size (48/128/256/512 included). Idempotent - existing theme
# icons are kept. NOTE: this adds ~16k files; the icons tarball grows.
echo "[6/10] Breeze widget/system icons..."
if [ -f scripts/tint-breeze.py ]; then
  python3 scripts/tint-breeze.py || true
fi

# Bright-red tray icons (v1.0.35): cachy-update normal (checkmark) dark
# red, cachy-update updates-available biggest red alert (V-map 255),
# steam + steam_tray_mono + all audio-volume icons bright #ff0000.
# Previously crushed to near-black (#280000-#8c0000, avg 68-91) so the
# update alert was invisible and audio/steam looked disabled.
echo "[7/10] Tray icons..."
if [ -f scripts/fix-tray-icons.py ]; then
  python3 scripts/fix-tray-icons.py "$HOME/.local/share/icons/SkynetRedBlack" || true
fi

# Normalize preferences icons (v1.0.34): stale bright #ff0000 copies in
# <size>/preferences/ (incl. #fff gradient stops) won lookup order over
# the dark <size>/apps/ copies, making e.g. DLSS5VKLayer Helper and
# Emoji Selector render bright red/white in the Kickoff menu.
echo "[8/10] Preferences icons..."
if [ -f scripts/normalize-preferences.py ]; then
  python3 scripts/normalize-preferences.py || true
fi

# System-wide SVG icon scan (v1.0.39): scan ALL *.svg files across / and
# /home for icons not already in the theme. This catches user themes,
# third-party icon packs, custom icons, flatpak icons, etc. that
# tint-breeze.py alone misses. Progress bar shows real-time count.
# v1.0.44: incremental when an icon-db exists (only new/changed SVGs).
if [ -f scripts/scan-all-icons.py ]; then
  echo "[9/10] Scanning all SVG icons on the system..."
  python3 scripts/scan-all-icons.py || true
fi

# Icon/app database (v1.0.44): snapshot every icon + installed app NOW,
# at install time, so future retints are diffs instead of full rescans.
# Filename+stat walk only (no file contents read) -- cheap relative to
# the tint scan above. cyberdyne-retint diffs the start-menu app list
# (.desktop files) against this snapshot and only tints new/changed
# apps, and scan-all-icons.py only processes new/changed SVGs.
echo "[10/10] Building icon database..."
if [ -f scripts/icon-db.py ]; then
  python3 scripts/icon-db.py build || true
fi

# cursor theme (Breeze_Dark_Red - bundled; see Credits in README for attribution)
mkdir -p "$HOME/.icons"
rm -rf "$HOME/.icons/Breeze_Dark_Red"
if [ -d cursors/Breeze_Dark_Red ]; then
  cp -a cursors/Breeze_Dark_Red "$HOME/.icons/"
elif [ -f releases/SkynetRedBlack-cursor.tar.gz ]; then
  tar -xzf releases/SkynetRedBlack-cursor.tar.gz -C "$HOME/.icons/"
fi

# colour scheme (checkout file, else the release tarball)
mkdir -p "$HOME/.local/share/color-schemes"
if [ -f colorschemes/SkynetRedBlack.colors ]; then
  cp colorschemes/SkynetRedBlack.colors "$HOME/.local/share/color-schemes/"
elif [ -f releases/SkynetRedBlack-colorscheme.tar.gz ]; then
  tar -xzf releases/SkynetRedBlack-colorscheme.tar.gz -C "$HOME/.local/share/color-schemes/"
else
  echo "ERROR: colour scheme not found" >&2; exit 1
fi

# konsole (checkout files, else the release tarball)
mkdir -p "$HOME/.local/share/konsole"
if [ -f konsole/SkynetRedBlack.colorscheme ]; then
  cp konsole/SkynetRedBlack.colorscheme konsole/"SkynetRedBlack.profile" "$HOME/.local/share/konsole/"
elif [ -f releases/SkynetRedBlack-konsole.tar.gz ]; then
  tar -xzf releases/SkynetRedBlack-konsole.tar.gz -C "$HOME/.local/share/konsole/"
else
  echo "ERROR: Konsole scheme not found" >&2; exit 1
fi

# wallpaper (checkout file, else the release tarball)
mkdir -p "$HOME/.local/share/wallpapers/SkynetRedBlack"
if [ -f wallpaper/skynet-wallpaper.jpg ]; then
  cp wallpaper/skynet-wallpaper.jpg "$HOME/.local/share/wallpapers/SkynetRedBlack/"
elif [ -f releases/SkynetRedBlack-wallpaper.tar.gz ]; then
  tar -xzf releases/SkynetRedBlack-wallpaper.tar.gz -C "$HOME/.local/share/wallpapers/SkynetRedBlack/"
else
  echo "ERROR: wallpaper not found" >&2; exit 1
fi

# fastfetch greeting (v1.0.45: guarded — the old unconditional `cp`
# aborted tarball-only installs under `set -e` when fastfetch/ was absent)
mkdir -p "$HOME/fastfetch" "$HOME/.config/fish"
if [ -f fastfetch/skynet.txt ] && [ -f fastfetch/skynet.json ]; then
  cp fastfetch/skynet.txt fastfetch/skynet.json "$HOME/fastfetch/"
fi
if [ -f fish/config-fragment.fish ] && ! grep -q "fastfetch/skynet.json" "$HOME/.config/fish/config.fish" 2>/dev/null; then
  cat fish/config-fragment.fish >> "$HOME/.config/fish/config.fish"
  echo "fish greeting appended to ~/.config/fish/config.fish"
fi

# DaVinci menu category + app shadows (absolute icon paths - bypass theme fallback)
# ONLY if the user actually has DaVinci Resolve installed (v1.0.23): a theme
# must never plaster a broken menu entry on a machine without the app, and it
# must NEVER copy anything to ~/Desktop - the desktop belongs to the user.
mkdir -p "$HOME/.local/share/desktop-directories" "$HOME/.local/share/applications"
if [ -x /opt/resolve/bin/resolve ]; then
  cp desktop-directories/DaVinciResolve.directory "$HOME/.local/share/desktop-directories/"
  cp applications/DaVinciResolve.desktop "$HOME/.local/share/applications/"
else
  rm -f "$HOME/.local/share/desktop-directories/DaVinciResolve.directory" "$HOME/.local/share/applications/DaVinciResolve.desktop"
  echo "DaVinci Resolve not installed - skipped its menu shadows (no desktop copy is ever made)"
fi
rm -f "$HOME/Desktop/DaVinciResolve.desktop"

# hicolor override (DaVinci PNG fallback)
if [ -d hicolor-override ]; then
  mkdir -p "$HOME/.local/share/icons/hicolor"
  cp -a hicolor-override/. "$HOME/.local/share/icons/hicolor/"
  gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" || true
fi

# Triangle launcher icon + bright Hermes/Kate/Keet icons (v1.0.2)
mkdir -p "$HOME/.local/share/icons/SkynetRedBlack/scalable/apps" "$HOME/.local/share/icons/SkynetRedBlack/48/apps" "$HOME/.local/share/icons/SkynetRedBlack/22/apps"
for d in "$HOME/.local/share/icons/SkynetRedBlack/scalable/apps" "$HOME/.local/share/icons/SkynetRedBlack/48/apps" "$HOME/.local/share/icons/SkynetRedBlack/22/apps"; do
  cp icons-overlay/cyberdyne-triangle.svg "$d/" 2>/dev/null || true
  cp icons-overlay/SkynetRedBlack.png "$d/" 2>/dev/null || true
  cp icons-overlay/kate.svg "$d/" 2>/dev/null || true
  cp icons-overlay/steam.svg "$d/" 2>/dev/null || true
  cp icons-overlay/io.keet.Keet.png "$d/" 2>/dev/null || true
done
# Set Kickoff (start menu) button to the triangle instead of the red circle
python3 - "$HOME/.config/plasma-org.kde.plasma.desktop-appletsrc" << 'PYEOF'
import pathlib, re, sys
f=pathlib.Path(sys.argv[1])
if f.exists():
    t=f.read_text()
    # dedupe duplicate icon= lines left by earlier installs, keep the first
    seen=False; kept=[]
    for ln in t.split(chr(10)):
        if ln.strip()=='icon=cyberdyne-triangle':
            if seen: continue
            seen=True
        kept.append(ln)
    t=chr(10).join(kept)
    if 'icon=cyberdyne-triangle' not in t:
        t=re.sub(r'(plugin=org\.kde\.plasma\.kickoff.*?\[Configuration\]\[General\])', r'\g<1>' + chr(10) + 'icon=cyberdyne-triangle', t, count=1, flags=re.S)
    f.write_text(t)
PYEOF

# Plasma style (SkynetRedBlack desktoptheme - black base, bright-red active highlight)
if [ -d plasma-style/SkynetRedBlack ]; then
  mkdir -p "$HOME/.local/share/plasma/desktoptheme"
  cp -a plasma-style/SkynetRedBlack "$HOME/.local/share/plasma/desktoptheme/"
fi

# Window buttons bright red (v1.0.37): minimize/maximize/close were white.
# Two layers: (1) SSD windows - the Darkly decoration library hardcodes
# white buttons and ignores the desktoptheme, so point KWin at the Breeze
# library + SkynetRedBlack desktoptheme, whose [WM] active/inactive
# foregrounds are 255,0,0. (2) Brave/Chromium draws its own client-side
# white glyphs on the tab bar; only the system title bar (KWin SSD)
# makes those red too - scripts/set-brave-system-titlebar.py sets
# browser.custom_chrome_frame=false, but only when Brave is closed.
if command -v kwriteconfig6 >/dev/null; then
  kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key library org.kde.breeze
  kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme SkynetRedBlack
  qdbus6 org.kde.KWin /KWin reconfigure 2>/dev/null || true
fi
if [ -f scripts/set-brave-system-titlebar.py ]; then
  python3 scripts/set-brave-system-titlebar.py || echo "note: Brave is running - close it and re-run scripts/set-brave-system-titlebar.py so its buttons use the red system title bar"
fi

# Desktop-containment plasmoid override (v1.0.14): upstream FolderItemDelegate.qml
# hardcodes desktop icon label text to "white" on the root view, ignoring the
# colour scheme entirely. This user-level plasmoid copy ships bright clock
# red #ff0000 instead. Plasma searches ~/.local/share/plasma/plasmoids first.
if [ -d plasmoids/org.kde.desktopcontainment ]; then
  mkdir -p "$HOME/.local/share/plasma/plasmoids"
  cp -a plasmoids/org.kde.desktopcontainment "$HOME/.local/share/plasma/plasmoids/"
fi

# Clear stale inline kdeglobals overrides (v1.0.12): old Darkly-derived pink /
# white / purple values in kdeglobals override the desktoptheme and made the
# active-task highlight pink/purple. Force them to clock red 255,0,0.
python3 - "$HOME/.config/kdeglobals" << 'PYEOF'
import pathlib, sys
f = pathlib.Path(sys.argv[1])
if f.exists():
    t = f.read_text()
    for a, b in {
        "AccentColor=255,255,255": "AccentColor=255,0,0",
        "175,35,57": "255,0,0",
        "ForegroundLink=249,176,181": "ForegroundLink=255,0,0",
        "BackgroundAlternate=122,24,39": "BackgroundAlternate=255,0,0",
        "BackgroundNormal=122,24,39": "BackgroundNormal=255,0,0",
        "BackgroundAlternate=178,0,0": "BackgroundAlternate=255,0,0",
        "BackgroundNormal=178,0,0": "BackgroundNormal=255,0,0",
    }.items():
        t = t.replace(a, b)
    f.write_text(t)
PYEOF

# Dolphin has its own per-app icon theme (v1.0.13): a stale CyberKDE override
# in dolphinrc made Dolphin's toolbar icons white (CyberKDE/Breeze-Dark
# fallbacks are #fcfcfc). Point it at SkynetRedBlack like the global theme.
python3 - "$HOME/.config/dolphinrc" << 'PYEOF'
import pathlib, sys
f = pathlib.Path(sys.argv[1])
if f.exists():
    t = f.read_text()
    if "Theme=" in t:
        import re
        t = re.sub(r"Theme=\S+", "Theme=SkynetRedBlack", t, count=1)
    else:
        t += "\n[Icons]\nTheme=SkynetRedBlack\n"
    f.write_text(t)
PYEOF

# Disabled icon effect (v1.0.20): KIconEffect defaults every group's Disabled
# state to grey (togray). KDE reads the effect per-app from each app's own rc
# file (konsolerc, dolphinrc, ...), so write maroon colorize sections there
# and into kdeglobals. This makes greyed-out icons (e.g. Konsole Copy with
# no selection) dark maroon 60,0,0 instead of grey.
python3 - << 'PYEOF'
import pathlib, re
groups = ["DesktopIcons","ToolbarIcons","MainToolbarIcons","SmallIcons","PanelIcons","DialogIcons"]
block = "".join(
    f"\n[{g}]\nDisabledEffect=colorize\nDisabledValue=0.7\nDisabledColor=60,0,0\nDisabledSemiTransparent=false\n"
    for g in groups
)
home = pathlib.Path.home()
for name in ["kdeglobals","konsolerc","dolphinrc","katerc","gwenviewrc","arkrc"]:
    p = home/".config"/name
    if not p.exists():
        continue
    t = p.read_text()
    for g in groups:
        t = re.sub(rf"\n\[{g}\][^\[]*", "\n", t)
    p.write_text(t.rstrip() + "\n" + block)
PYEOF

# global theme
if command -v kpackagetool6 >/dev/null; then
  kpackagetool6 --type Plasma/LookAndFeel --install look-and-feel/com.skynetredblack || \
  kpackagetool6 --type Plasma/LookAndFeel --upgrade look-and-feel/com.skynetredblack || true
fi

kbuildsycoca6 --noincremental || true

# Restart the Plasma shell so all changes take effect immediately:
# icon theme, colour scheme, desktop theme, global theme, kwin settings, etc.
echo ""
echo "Restarting Plasma shell to apply all changes..."
systemctl --user restart plasma-plasmashell.service 2>/dev/null || \
  killall plasmashell 2>/dev/null || true

echo ""
echo "Done. The shell has been restarted."
echo "If anything looks off, restart Dolphin too: dolphin --replace &"

# --- optional auto-retint for future apps (v1.0.7) ---
# Installs scripts/retint-new-icons.py as ~/.local/bin/cyberdyne-retint and
# (with --with-auto-retint) enables a weekly systemd user timer that runs it.
# A Plasma global theme cannot auto-tint future icons by itself - this script
# is the mechanism. Manual run anytime:  cyberdyne-retint [--force]
# It runs the FULL icon pipeline (mini/tray/preferences/breeze/scan/...),
# so install every icon script alongside it — otherwise the installed
# copy cannot find its siblings and only the apps step would run.
mkdir -p "$HOME/.local/bin"
cp scripts/retint-new-icons.py "$HOME/.local/bin/cyberdyne-retint" 2>/dev/null || true # already installed (e.g. symlinked to repo copy)
chmod +x "$HOME/.local/bin/cyberdyne-retint"
for _s in fix-mini-icons.py tint-breeze.py fix-tray-icons.py normalize-preferences.py \
          fix-copy-icon.py fix-folder-index.py fix-davinci-icon.py scan-all-icons.py \
          detint-remove.py auto-retint.py \
          icon-db.py set-brave-system-titlebar.py redtint.py; do
  # v1.0.45: redtint.py is the shared library the tinters import —
  # install it alongside them or the installed copies lose the fast path.
  # v1.0.52: detint-remove.py (cyberdyne-detint) + auto-retint.py
  # (cyberdyne-auto) ship alongside retint for the same reason.
  cp "scripts/$_s" "$HOME/.local/bin/$_s" 2>/dev/null || true
  chmod +x "$HOME/.local/bin/$_s" 2>/dev/null || true
done
# v1.0.52: detint + auto-toggle command names, exactly like cyberdyne-retint.
cp scripts/detint-remove.py "$HOME/.local/bin/cyberdyne-detint" 2>/dev/null || true
chmod +x "$HOME/.local/bin/cyberdyne-detint" 2>/dev/null || true
cp scripts/auto-retint.py "$HOME/.local/bin/cyberdyne-auto" 2>/dev/null || true
chmod +x "$HOME/.local/bin/cyberdyne-auto" 2>/dev/null || true
if [ "${1:-}" = "--with-auto-retint" ]; then
  mkdir -p "$HOME/.config/systemd/user"
  cp systemd/cyberdyne-retint.service systemd/cyberdyne-retint.timer systemd/cyberdyne-retint.path "$HOME/.config/systemd/user/"
  systemctl --user daemon-reload
  systemctl --user enable --now cyberdyne-retint.timer cyberdyne-retint.path
  echo "auto-retint enabled: .path watcher (instant, on app install) + weekly timer safety net"
fi
