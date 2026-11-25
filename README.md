# Dirt Gear v1.2.1

A local Windows editor for MX Bikes rider gear. Open a creator's gear PSD, choose colourways, add your logos, name and number beneath the shading, check it on the 3D rider, and pack a game-ready paint. No Photoshop, PaintHub or PaintEd needed. Dirt Gear is the successor to Moto Gear v1.3.

## Install

Run **Dirt-Gear-Setup-1.2.1.exe** and choose **Yes**. It installs for your Windows account in `%LOCALAPPDATA%\Programs\Dirt Gear` (no admin needed), adds Desktop and Start menu shortcuts, and lists Dirt Gear in **Settings > Apps > Installed apps**. Microsoft Edge WebView2 Runtime is required (already on Windows 10/11 in most cases).

The setup isn't code-signed yet, so Windows SmartScreen may say it's from an unknown publisher: choose **More info > Run anyway**. Each release is built by GitHub Actions from the public source, and its SHA-256 is in the release's signed `update.json`.

## Uninstall

**Settings > Apps > Installed apps > Dirt Gear > Uninstall** (or run `Dirt Gear.exe --uninstall`). It removes the program folder, the shortcuts and the Installed apps entry, then asks whether to delete your saved projects, logos, layouts and settings in `%LOCALAPPDATA%\Dirt Gear` too. Paints you packed into MX Bikes are never removed. `--uninstall --quiet` removes the app without questions and keeps your saved work (add `--remove-data` to delete it).

## Setup options

The setup also accepts these, mainly for testing and the in-app updater: `--quiet` installs without asking, `--target <folder>` installs somewhere else, `--no-shortcuts` skips the shortcuts, `--no-register` skips the Installed apps entry, and `--update --wait-pid <id> [--no-launch]` is what the updater uses to replace the installed copy after Dirt Gear closes and then reopen it.

If you used Moto Gear, your saved projects, logos and layouts are copied into Dirt Gear the first time it opens. Moto Gear's own folder isn't changed, so both apps can live side by side.

## Updates

Dirt Gear asks GitHub for the latest release a few seconds after it opens and, if there's a newer one, offers **Download and install** or **Skip this version**. Nothing is downloaded or installed until you click. To turn the check off, click the version label (top left) and untick **Check for updates when Dirt Gear starts**: opening that box doesn't contact GitHub, only **Check for updates** does. An update installs only if its `update.json` carries a valid Ed25519 signature from the key built into the app and the download matches the size and SHA-256 it lists. Release setup is in `docs/UPDATES.md`.

## What it sends and stores

- **Network:** only the update check above (`api.github.com`, then GitHub's release downloads when you click Download and install). No account, no analytics, no ads. Your PSDs, designs and paints never leave your PC.
- **Files:** the program folder, your saved work in `%LOCALAPPDATA%\Dirt Gear`, and the files you choose to save or pack. Pack & install writes `<name>.pnt` into the chosen rider model's `paints` folder, and asks before replacing one with the same name.
- **Registry:** one key, `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\DirtGear`, for the Installed apps entry. Uninstalling deletes it.
- The window is a page served by Dirt Gear itself on `127.0.0.1` (a random port). Every request, including the page and its static files, must carry a random token made at each start: the window's first page load passes it in the address, and that load sets an HttpOnly, SameSite=Strict cookie for the page's own files. Requests without it are refused (`tests/test_token.py`).
- `source/premium.py` holds code for a possible future Premium version. It's switched off (`source/premium_config.json`), so it never limits anything or contacts anyone.

## Using it

1. **Open PSD** (top bar or the start screen). Dirt Gear finds the Norm and Spec maps itself. If there's no Spec, it makes a black one.
2. **Layers** (left): click the eye to show or hide a layer. Lock icons mark Norm/Spec map layers, which are used automatically for export. Tags show SHADE, NORM, SPEC and ART (smart objects).
3. **Add to your gear** (right): add a logo or image (PNG, JPG, SVG), paste with Ctrl+V, drag files onto the canvas, or add a **Name** or **Number** in any bundled BYD/MX font, with an outline, a gradient and **letter spacing** if you want them. Recolour any added logo with **Colour overlay** (one colour or a gradient, with strength).
4. **Place it**: drag to move, drag a corner to resize (hold Shift to stretch), and use the round handle to rotate (snaps to 15°, Shift for free rotation). Alt-drag pans, the scroll wheel zooms, arrow keys nudge, Ctrl+Z / Ctrl+Shift+Z undo and redo, and Delete removes.
5. **Under the shading**: drag the green **Your added layers** strip onto a PSD layer to put all your artwork below it. Reorder your own layers by dragging them or using the arrows.
6. **Check it**: Diffuse / Norm / Spec tabs, **3D preview** on the rider, and **Check final rendering** for the exact export image.
7. **Finish & ride** (bottom right): name the gear, pick the rider model and click **Pack & install in MX Bikes**. Restart MX Bikes to see it. **Export .pnt** (top bar) or **3 TGAs (.zip)** let you save the files anywhere.
8. **Save for later** keeps an editable project in your library on this PC (with a private copy of the PSD so it reopens offline), and **Continue** is offered on the start screen. **Portable project** saves a `.dirtgear` file you can move to another PC. It holds your design and artwork but **never the creator's PSD**: whoever opens it chooses their own copy of the template, and Dirt Gear checks it's the same file (old `.motogear` files still open).

## Use templates fairly

Please only use PSD templates you've bought or been given permission to use by their creator. Dirt Graphic Studios doesn't support or endorse using templates that weren't legitimately obtained. Support the creators who make this community possible.

Saved logos, logo layouts and HEX colour swatches work as they did in Moto Gear v1.3.

## Export contract (unchanged from Moto Gear)

| File | Format | Alpha |
| --- | --- | --- |
| `rider.tga` | 24-bit RGB | none |
| `rider_n.tga` | 32-bit RGBA | every byte 0 |
| `rider_r.tga` | 32-bit RGBA | every byte 0 |

`.pnt` files use Dirt Gear's own independent writer (`source/packing.py`).

## Licence and credits

Dirt Gear is © 2026 Dirt Graphic Studios, **all rights reserved**: the source is public so anyone can read and check it, but it isn't open source (see `LICENSE.txt`). Bundled fonts and their licences are listed in `source/fonts/FONTS.md`. Each build includes `THIRD-PARTY-NOTICES.txt` with the licences of Python, Pillow, pywebview, pythonnet, aggdraw, psd-tools, NumPy, SciPy and every other bundled package (made by `tools/third_party_notices.py`). The About box links to all three. Dirt Gear is a fan-made tool and isn't affiliated with MX Bikes or PiBoSo.

## Limits

8-bit RGB PSDs up to 8192 × 8192. PSD rendering uses psd-tools, not Photoshop, so complex effects can differ, so check the final rendering. Existing PSD text and smart objects can't be edited as text or vectors. The 3D preview uses studio lighting, not the MX Bikes shader.

## Building (developers)

Releases are built automatically: changing `VERSION.txt` on main (or running the workflow from the Actions tab) runs `.github/workflows/release.yml` on a GitHub Windows machine. It installs the exact package versions in `source/requirements.txt` and `build/requirements-build.txt` (actions are pinned to commit SHAs), builds the app and installer, clean-installs it, runs the backend tests against the installed copy, tests the self-update and the uninstaller, and then publishes `Dirt-Gear-Setup-X.exe` on the Releases page. If a build fails, its log is saved to the `ci-logs` branch.

To build locally instead:

Requires Windows and Python 3.12. From this folder:

```powershell
powershell -ExecutionPolicy Bypass -File build\build.ps1
```

This creates a `.venv`, builds `dist\Dirt Gear\`, then `release\Dirt-Gear-Setup-1.2.1.exe`. To run from source instead: `pip install -r source\requirements.txt` then `python source\app.py`.

Tests: `tests/test_backend.py` (exports, black alpha, PNT, projects, library migration) and `tests/test_ui.cjs` (Playwright walkthrough). Start the app with `python source/app.py --no-browser --session-file <dir>/session.json`, create `<dir>/fixtures/test-gear.psd` with `tests/make_test_psd.py`, then pass `<dir>` to either test. The old Moto Gear suites are kept in `tests/legacy-moto-gear/` for reference.

See `CLAUDE-HANDOVER.md` for the full technical handover.
