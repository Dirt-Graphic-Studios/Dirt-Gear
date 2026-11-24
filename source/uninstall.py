"""Uninstall Dirt Gear: `Dirt Gear.exe --uninstall`.

Windows runs this from Settings > Apps > Installed apps (the installer adds the
entry). It removes the Desktop and Start menu shortcuts and the Installed apps
entry, then deletes the program folder once Dirt Gear has closed. Your saved
projects, logos, layouts and settings (%LOCALAPPDATA%\\Dirt Gear) are kept
unless you choose to remove them. Paints you packed into MX Bikes are never
touched.
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\DirtGear'
TITLE = 'Uninstall Dirt Gear'
YES = 6


def _message(text: str, flags: int) -> int:
    if os.name != 'nt':
        print(text)
        return YES
    user32 = ctypes.windll.user32
    user32.MessageBoxW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
    user32.MessageBoxW.restype = ctypes.c_int
    return user32.MessageBoxW(None, text, TITLE, flags | 0x00010000)


def _ps_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def _folder(name: str) -> Path | None:
    try:
        out = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                              f"[Environment]::GetFolderPath('{name}')"],
                             capture_output=True, text=True, timeout=30, creationflags=0x08000000).stdout.strip()
        return Path(out) if out else None
    except Exception:
        return None


def shortcut_paths() -> list[Path]:
    paths = []
    for name in ('DesktopDirectory', 'Programs'):
        folder = _folder(name)
        if folder:
            paths.append(folder/'Dirt Gear.lnk')
    for desktop in (Path(os.environ.get('OneDrive', str(Path.home()/'OneDrive')))/'Desktop', Path.home()/'Desktop'):
        paths.append(desktop/'Dirt Gear.lnk')
    return paths


def remove_entry() -> None:
    if os.name != 'nt':
        return
    import winreg
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except FileNotFoundError:
        pass


def is_program_folder(folder: Path) -> bool:
    """Only ever delete a folder that is clearly a Dirt Gear install."""
    return ((folder/'Dirt Gear.exe').is_file() and (folder/'_internal').is_dir()
            and (folder/'_internal/static/app.js').is_file() and len(folder.parts) > 2)


def delete_after_exit(folder: Path) -> None:
    """Dirt Gear can't delete its own running files, so a hidden PowerShell
    waits for this process to close, then removes the program folder."""
    script = (f'Wait-Process -Id {os.getpid()} -ErrorAction SilentlyContinue; Start-Sleep -Seconds 1; '
              f'Remove-Item -LiteralPath {_ps_quote(folder)} -Recurse -Force -ErrorAction SilentlyContinue')
    subprocess.Popen(['powershell.exe', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command', script],
                     creationflags=0x08000000 | 0x00000008 | 0x00000200, close_fds=True)


def run(data_folder: Path, quiet: bool = False, remove_data: bool = False) -> int:
    folder = Path(sys.executable).resolve().parent
    if not getattr(sys, 'frozen', False) or not is_program_folder(folder):
        _message('This copy of Dirt Gear wasn’t installed by the Dirt Gear installer, so there is nothing to uninstall.', 0x30)
        return 1
    if not quiet:
        if _message('Remove Dirt Gear from this PC?\n\nPaints you packed into MX Bikes are not removed.', 0x04 | 0x20) != YES:
            return 0
        remove_data = _message(f'Also delete your saved projects, logos, layouts and settings?\n\n{data_folder}\n\n'
                               'Choose No to keep them for if you install Dirt Gear again.', 0x04 | 0x20 | 0x100) == YES
    for link in shortcut_paths():
        try:
            link.unlink(missing_ok=True)
        except OSError:
            pass
    remove_entry()
    if remove_data and data_folder.name == 'Dirt Gear' and data_folder.is_dir():
        shutil.rmtree(data_folder, ignore_errors=True)
    delete_after_exit(folder)
    if not quiet:
        _message('Dirt Gear has been removed.' + ('' if remove_data else f'\n\nYour saved work is still in:\n{data_folder}'), 0x40)
    return 0
