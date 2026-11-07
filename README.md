# SkynetRedBlack

A red-on-black Cyberdyne / Skynet themed **global theme for KDE Plasma 6** —
colour scheme, redscale icon theme, Papirus-Folders, Konsole profile,
wallpaper, and a triforce fastfetch greeting, all in one package.

## Screenshots

![Desktop](docs/screenshot-desktop.png)

## What's inside

| Component | Source in this repo | Installs to |
|---|---|---|
| Global theme (Look-and-Feel) | `look-and-feel/com.skynetredblack/` | `~/.local/share/plasma/look-and-feel/` |
| Icon theme `SkynetRedBlack` | `icons/SkynetRedBlack/` | `~/.local/share/icons/` |
| Colour scheme `SkynetRedBlack` | `colorschemes/SkynetRedBlack.colors` | `~/.local/share/color-schemes/` |
| Konsole colour scheme `SkynetRedBlack` | `konsole/SkynetRedBlack.colorscheme` | `~/.local/share/konsole/` |
| Konsole profile `SkynetRedBlack` | `konsole/SkynetRedBlack.profile` | `~/.local/share/konsole/` |
| Cursor theme `Breeze_Dark_Red` | `cursors/Breeze_Dark_Red/` | `~/.icons/` |
| Wallpaper | `wallpaper/skynet-wallpaper.jpg` | `~/.local/share/wallpapers/SkynetRedBlack/` |
| Login wallpaper (3840×2160) | `wallpaper/login.jpg` (+ `login.png` source) | `~/.local/share/wallpapers/SkynetRedBlack/login.jpg`, then `/usr/share/wallpapers/SkynetRedBlack/login.jpg` for the login screen |
| Sound theme — Cyberdyne System Sounds (42 sounds) | `sounds/Cyberdyne-System-Sounds/` | `~/.local/share/sounds/Cyberdyne-System-Sounds/` |
| fastfetch triforce logo | `fastfetch/skynet.txt`, `skynet.json` | `~/fastfetch/` |
| fish greeting fragment | `fish/config-fragment.fish` | `~/.config/fish/config.fish` (append) |
| Panel/desktop layout (optional) | `extras/layouts/org.kde.plasma.desktop-layout.js` | `look-and-feel/.../contents/layouts/` (already included) |
| Desktop containment override (red labels) | `plasmoids/org.kde.desktopcontainment/` | `~/.local/share/plasma/plasmoids/` |
| Retint (tint new app icons red) | `scripts/retint-new-icons.py` | `~/.local/bin/cyberdyne-retint` (+ icon helpers) |
| Detint / uninstall the tint | `scripts/detint-remove.py` | `~/.local/bin/cyberdyne-detint` |
| Auto-scan + shell-restart toggle | `scripts/auto-retint.py` | `~/.local/bin/cyberdyne-auto` |

The icon theme is a redscale tint of the user's installed app icons
(luminance → muted red, symbolic/system icons → bright red) plus
Tela red folders (`#ef5350`) shoehorned into `folder`, `inode-directory`,
drive, and trash icons. The colour scheme is pure black backgrounds
with bright red foregrounds. The Konsole profile is red-on-black
with a bright red cursor. **Cyberdyne System Sounds** ships 42 sound
effects (Ogg Vorbis, in `sounds/Cyberdyne-System-Sounds/stereo/`),
covering every KDE notification event from `dialog-error` through
`desktop-login` — select it in System Settings → Sound, or it's set
for you by `install.sh` / the global-theme defaults.

## Quick install (whole shabang)

```bash
git clone https://github.com/kd0frg/SkynetRedBlack.git
cd SkynetRedBlack
./install.sh
```

`install.sh` asks first: **`Tint all icons red? [Y/n]`** — the
default is **Y** (press Enter, or type `Y`/`y`/`yes` in any case).
Answer `N`/`n`/`no` (also case-insensitive) to skip icon tinting
entirely: the icon theme is not copied, the tint pipeline and the
icon database build do not run. Everything else (colour scheme,
wallpaper, cursor, Konsole, global theme) installs as normal, and
the icon theme is set to `breeze` instead of pointing at a theme
that was never installed. Retint/detint/auto are still installed,
so tinting stays optional and can be done later:

```bash
cyberdyne-retint   # tints on demand - on its first run it creates the
                   # SkynetRedBlack icon theme (incl. index.theme) and
                   # builds the icon database itself, no installer needed
```

A non-interactive run (no input) takes the default, Y.

`install.sh` copies every component to its correct location, rebuilds
the icon cache, sets the wallpaper, installs the fish greeting, and
installs the global theme with `kpackagetool6`. Then log out/in (or
restart Plasma: `systemctl --user restart plasma-plasmashell.service`).

## Install the global theme alone (KDE Store style)

```bash
kpackagetool6 --type Plasma/LookAndFeel --install SkynetRedBlack-lookandfeel.tar.gz
# or: System Settings -> Appearance -> Global Theme -> Install from File
```

Then select **SkynetRedBlack** in Global Themes.
Note: a global theme package only carries *defaults* (colour scheme
name, icon theme name, widget style). The actual colour scheme and
icon theme files must be installed too — `install.sh` does that, or
install the separate tarballs below.

## Separate tarballs (for KDE Store submission)

In `releases/` (built by `install.sh --pack` or manually):

- `SkynetRedBlack-lookandfeel.tar.gz` — Plasma/LookAndFeel package
- `SkynetRedBlack-icons.tar.gz` — icon theme (SkynetRedBlack)
- `SkynetRedBlack-colorscheme.tar.gz` — colour scheme
- `SkynetRedBlack-konsole.tar.gz` — Konsole scheme + profile
- `SkynetRedBlack-cursor.tar.gz` — Breeze_Dark_Red cursor theme
- `SkynetRedBlack-wallpaper.tar.gz` — wallpaper
- `SkynetRedBlack-sounds.tar.gz` — Cyberdyne System Sounds (42 sound effects, Ogg Vorbis)

**Can it go on KDE Store? Yes** — upload is manual (store.kde.org →
Publish). Status (verified against the Plasma look-and-feel package
spec: `KPackageStructure: Plasma/LookAndFeel` in `metadata.json`,
preview at `contents/previews/preview.png`):

- ✅ `metadata.json`: Id, Name, Category, Description, Authors
  (ProjectAIvolution <kd0frg@gmail.com>), Version, trimmed License
  (`MIT / GPL-3.0 / LGPL-3.0 (see LICENSE)`), Keywords
- ✅ Tarball structure: `com.skynetredblack/` root, installs via
  `kpackagetool6 --type Plasma/LookAndFeel`
- ✅ Preview is the real 1919x1077 desktop screenshot at
  `contents/previews/preview.png`
- ✅ `Website` set in metadata; wallpaper tarball is a
  bare JPG — KDE Store wallpapers take the image directly, OK
- ✅ Dependencies wired (v1.0.51): icons 2381288, colour scheme
  2381290, wallpaper 2381292, cursor 2381293 are listed in
  `X-KPackage-Dependencies` in the global theme's `metadata.json`,
  so it pulls its components in automatically. Konsole (2381291)
  and Cyberdyne System Sounds (2381359) are standalone listings —
  there is no Konsole or sound-theme KNewStuff type (no
  `sounds.knsrc` exists), so neither can be a dependency; sounds
  must be installed separately. Global theme itself: 2381294.

## Requirements

- KDE Plasma 6 (tested on 6.8, CachyOS)
- Breeze widget style (stock) — the defaults deliberately use Breeze,
  not a third-party Plasma style, so it works on a stock install.
  The author's own desktop also uses the Darkly Plasma style; swap
  `plasmarc`/`kwinrc` in `contents/defaults` for Darkly if you have it.
- `fastfetch` (optional, for the greeting), `fish` (optional)

## Credits — special thanks

This theme stands on the shoulders of the Linux community. Huge thanks to:

- **Breeze Dark Red cursor (the mouse this theme settled on)** — originally by **fbm224**, packaged by **Erwin-Iosef**: https://github.com/Erwin-Iosef/Breeze-Dark-Red (KDE Store: https://store.kde.org/p/2108645, GPL). It is a red recolour of the stock Breeze cursor by the **KDE Visual Design Group**: https://github.com/KDE/breeze — thank you both, this cursor is the perfect match for the red-on-black look.
- **Breeze** (Plasma style, widget style, and the base cursor artwork) — **KDE Visual Design Group**: https://github.com/KDE/breeze
- **Tela icon theme** — **Vince Liuice (vinceliuice)**: https://github.com/vinceliuice/Tela-icon-theme (GPL-3.0). Its red folder artwork is shoehorned into this theme's folders.
- **Papirus icon theme + papirus-folders** — **PapirusDevelopmentTeam**, folder-colour script by **Sergei Eremenko (SmartFinn)**: https://github.com/PapirusDevelopmentTeam/papirus-icon-theme · https://github.com/PapirusDevelopmentTeam/papirus-folders — the red Papirus folders in Dolphin come from their `papirus-folders` tool.
- **KDE Plasma 6** — the **KDE Community**: https://kde.org — desktop, Dolphin, Konsole, and KWin that make this theme possible.
- **JetBrains Mono** (Konsole profile font) — **JetBrains**: https://github.com/JetBrains/JetBrainsMono

The cursor theme is bundled in `cursors/Breeze_Dark_Red/` (and as `SkynetRedBlack-cursor.tar.gz`) under its GPL terms, with attribution retained. All other assets are tinted derivatives of the above, redistributed under their respective licenses — check each project's license before commercial use.

## License

The full license is posted in this repository as `LICENSE` (root) with
verbatim third-party license texts under `LICENSES/` — see that file
for the authoritative wording. Summary:

- **Your own code/scripts/colour scheme/Konsole/defaults — MIT**
  (install.sh, scripts/, colourschemes/, konsole/, look-and-feel/
  metadata/defaults, plasma-style/ colors, plasmoid override,
  fastfetch/fish fragments, wallpaper). Full MIT text is in LICENSE.
- **Tinted icon artwork — NOT MIT.** This package redistributes
  tinted derivatives under their upstream licenses:
  - Tela icon theme (folders, Steam) — **GPL-3.0**, © vinceliuice
  - Papirus icon theme + papirus-folders (red folders) — **GPL-3.0**,
    © PapirusDevelopmentTeam / Sergei Eremenko
  - Breeze icons (all status/actions/panel/symbolic/apps tints) —
    **LGPL-3.0**, © KDE Community
  - Breeze_Dark_Red cursor (GPL, fbm224/Erwin-Iosef) — **GPL**,
    attribution retained
  - JetBrains Mono (Konsole font) — SIL OFL (referenced, not bundled)

  Because the icon tarball as shipped contains GPL/LGPL
  derivatives, it cannot be covered by a blanket MIT grant.
  The MIT grant above applies only to the author's original
  material; the GPL/LGPL parts remain under GPL-3.0 / LGPL-3.0
  (verbatim texts in `LICENSES/GPL-3.0.txt` and
  `LICENSES/LGPL-3.0.txt`). Check each upstream project's
  license before commercial use.

## Login screen (Plasma Login Manager)

Your login screen is **not** SDDM — CachyOS ships
**Plasma Login Manager** (`plasmalogin`), which unlike SDDM does
**not** support custom QML themes at all. Its greeter is a fixed
Breeze shell; the only things you can customise are the **wallpaper**
and the **colour scheme**. So the SkynetRedBlack login screen is:

- the **login wallpaper** (`wallpaper/login.jpg`, resized to
  3840×2160 from the `login.png` source), and
- the **SkynetRedBlack colour scheme** (already applied by the
  global theme).

`install.sh` installs the login wallpaper to
`~/.local/share/wallpapers/SkynetRedBlack/login.jpg`, and — since
the login user can't read inside your home directory — (with
passwordless sudo) also copies it to the world-readable
`/usr/share/wallpapers/SkynetRedBlack/login.jpg` and sets it as the
plasmalogin wallpaper with `kwriteconfig6`. Without passwordless
sudo it prints the manual steps instead of failing:

```bash
sudo mkdir -p /usr/share/wallpapers/SkynetRedBlack
sudo cp ~/.local/share/wallpapers/SkynetRedBlack/login.jpg /usr/share/wallpapers/SkynetRedBlack/
# then: System Settings -> Login Screen -> Background -> pick
# /usr/share/wallpapers/SkynetRedBlack/login.jpg
```

On SDDM-based systems the same `login.jpg` can be used as the
background of any SDDM theme (`theme.conf`: `background=login.jpg`).

## Retint, detint and the auto scanner

A global theme is a static package — it cannot tint icons for apps
that don't exist yet. SkynetRedBlack ships three commands for that,
installed to `~/.local/bin` by `install.sh`:

| Command | What it does |
|---|---|
| `cyberdyne-retint` | Tint new/changed app icons (and every other icon context) red — the **full pipeline**: titlebar minis, Breeze widgets, tray, preferences, copy icons, folder index, DaVinci, system-wide scan. Restarts the Plasma shell only if icons actually changed. |
| `cyberdyne-detint` | **Reverse of retint**: removes the red tint from every icon (see below). |
| `cyberdyne-auto` | Turn the auto scanner and/or the shell restart on and off (see below). |

### Retint — how to use

```bash
cyberdyne-retint            # full pipeline (recommended after installing an app)
cyberdyne-retint --apps-only # app Icon= names only, skip the rest of the pipeline
cyberdyne-retint --force     # re-tint even icons that already exist in the theme
cyberdyne-retint --bright    # tint everything bright red #ff0000 (widget retint)
cyberdyne-retint --skip-db   # ignore/skip the icon-db diff + refresh
```

With an icon database present (built by `install.sh`), retint diffs
the start-menu app list against the snapshot and only tints
new/changed apps; the DB is refreshed at the end of the run. No DB
means a full audit once, then the DB is built for next time.

**First run without the installer:** if `install.sh` was answered
`N` at the tint prompt (or the DB/theme were deleted), retint
bootstraps itself — it creates the `SkynetRedBlack` icon theme
(including `index.theme`) if it doesn't exist, and the end-of-run
DB refresh builds the icon database when it's missing
(`icon-db.py update` falls back to a full build). So
`cyberdyne-retint` alone is enough to start tinting from scratch.

### Detint — how to use, and what it does

Tinting is lossy: the clone of an icon stored in this theme does not
keep its original colours, so detint does **not** try to un-tint
pixels. Instead it **deletes the tinted red copies** from
`~/.local/share/icons/SkynetRedBlack`, and the icon loader falls back
through the theme's inheritance (`Tela-red-dark`/`Breeze`/`hicolor`)
to the original, untinted icons — exactly the pre-tint look. The
icon cache is rebuilt and the Plasma shell is restarted only if
anything actually changed (and only if shell-restart is enabled).

```bash
cyberdyne-detint                     # full detint: every tinted icon, all contexts
cyberdyne-detint --apps-only         # detint the apps context only, leave the rest
cyberdyne-detint --dry-run           # show what would be removed, change nothing
cyberdyne-detint --no-shell-restart  # detint, but never restart plasmashell
```

**Total uninstall** (`--total`) goes further: after detinting it also
removes the whole `SkynetRedBlack` icon theme directory, the icon/app
database (`~/.local/share/SkynetRedBlack/`), the installed
retint/detint/auto scripts in `~/.local/bin`, and the systemd
auto-scan units, and switches the active icon theme in
`~/.config/kdeglobals` back to `breeze` if it was `SkynetRedBlack`.
Colour scheme, wallpaper, cursor and Konsole files are **not**
touched — this is the icon/retint uninstaller.

```bash
cyberdyne-detint --total             # total uninstall of icons + retint system
cyberdyne-detint --total --dry-run   # preview a total uninstall first
```

### Auto scanner + shell restart — enable / disable

The auto scanner is two systemd user units that run retint for you:

- `cyberdyne-retint.path` — an inotify watcher that runs retint
  **instantly** whenever an app is installed/removed (a `.desktop`
  file appears/changes in the applications dirs). Zero daemon
  footprint, no polling.
- `cyberdyne-retint.timer` — a **weekly** safety-net run (5 minutes
  after boot, then every 7 days) for icon changes that don't touch
  those dirs.

`install.sh --with-auto-retint` enables both; use `cyberdyne-auto`
to change it later:

```bash
cyberdyne-auto enable                  # scanner ON  (timer + path watcher)
cyberdyne-auto disable                 # scanner OFF (units disabled + stopped)
cyberdyne-auto status                  # show scanner + shell-restart state
```

Retint/detint restart the Plasma shell after a run, but only when
icons actually changed. If you never want a run to bounce your shell,
turn the restart off — independent of the scanner:

```bash
cyberdyne-auto shell-restart disable   # retint/detint never restart plasmashell
cyberdyne-auto shell-restart enable    # restore the restart (the default)
cyberdyne-auto shell-restart status    # show the current setting
```

The setting is a plain file,
`~/.config/SkynetRedBlack/shell-restart` (`enabled`/`disabled`),
read by both retint and detint. There is no date/time scheduling
built in — enable/disable is the control, and the weekly timer is
the only clock involved.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) — newest version at the top.

<p align="center"><a href="https://buymeacoffee.com/projectaivolution"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="I'm fueled by coffee — Buy Me a Coffee" height="24"></a></p>
