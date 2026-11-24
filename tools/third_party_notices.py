"""Write THIRD-PARTY-NOTICES.txt for the Windows build.

Run in the build environment, after installing the requirements:
    python tools/third_party_notices.py source/THIRD-PARTY-NOTICES.txt
It lists every installed Python package with its version, licence and the
licence files it ships, then Python's own licence (which covers the OpenSSL,
libffi and other libraries Python bundles), then notes for the Microsoft
components. The file is bundled into the app next to Dirt Gear.exe's data.
"""
import sys
from importlib import metadata
from pathlib import Path

SKIP = {'pip', 'setuptools', 'wheel'}
LICENCE_WORDS = ('licen', 'copying', 'notice', 'authors')

MICROSOFT = """\
Microsoft Edge WebView2
  Dirt Gear's window is drawn by the Microsoft Edge WebView2 Runtime that comes
  with Windows. The WebView2 SDK files bundled by pywebview
  (Microsoft.Web.WebView2.Core.dll, Microsoft.Web.WebView2.WinForms.dll,
  WebView2Loader.dll) are Copyright (C) Microsoft Corporation and are
  redistributed under the Microsoft WebView2 SDK licence:
  https://www.nuget.org/packages/Microsoft.Web.WebView2/ (License).

Microsoft Visual C++ runtime
  VCRUNTIME140.dll, VCRUNTIME140_1.dll, MSVCP140.dll, ucrtbase.dll and the
  api-ms-win-*.dll files are Copyright (C) Microsoft Corporation and are
  redistributed as part of Python under the Visual Studio redistributable terms.
"""


def licence_text(dist):
    texts = []
    for file in dist.files or []:
        name = file.name.lower()
        if any(word in name for word in LICENCE_WORDS) and not name.endswith(('.py', '.pyc')):
            try:
                texts.append((str(file), Path(file.locate()).read_text(encoding='utf-8', errors='replace').strip()))
            except (OSError, ValueError):
                continue
    return texts


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'THIRD-PARTY-NOTICES.txt')
    rule = '=' * 78
    parts = ['Dirt Gear: third-party software notices', rule,
             'Dirt Gear is (c) Dirt Graphic Studios. It includes the software below, each under its own licence.',
             'Fonts are listed in fonts/FONTS.md.', '']
    dists = {}
    for dist in metadata.distributions():
        name = (dist.metadata['Name'] or '').strip()
        if name and name.lower() not in SKIP:
            dists.setdefault(name.lower(), dist)
    for key in sorted(dists):
        dist = dists[key]
        meta = dist.metadata
        licence = meta.get('License-Expression') or (meta.get('License') or '').split('\n')[0][:200] or \
            ', '.join(c.split('::')[-1].strip() for c in meta.get_all('Classifier') or [] if c.startswith('License')) or 'see below'
        url = meta.get('Home-page') or next((u.split(',', 1)[-1].strip() for u in meta.get_all('Project-URL') or []), '')
        parts += [rule, f"{meta['Name']} {dist.version}", f'Licence: {licence}'] + ([f'Website: {url}'] if url else []) + ['']
        for path, text in licence_text(dist):
            parts += [f'--- {path} ---', text, '']
    python_licence = Path(sys.base_prefix) / 'LICENSE.txt'
    parts += [rule, f'Python {sys.version.split()[0]} (and the libraries it bundles, such as OpenSSL and libffi)', '']
    parts += [python_licence.read_text(encoding='utf-8', errors='replace').strip() if python_licence.is_file()
              else 'Python Software Foundation License: https://docs.python.org/3/license.html', '']
    parts += [rule, MICROSOFT]
    out.write_text('\n'.join(parts) + '\n', encoding='utf-8')
    print(f'Wrote {out} ({len(dists)} packages)')


if __name__ == '__main__':
    main()
