"""Portable projects don't contain the creator's PSD; library saves do.
Run: python tests/test_portable_project.py"""
import io, json, os, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = Path(tempfile.mkdtemp())
os.environ['LOCALAPPDATA'] = str(TMP/'lad')
sys.path.insert(0, str(ROOT/'source'))
import app  # noqa: E402


def ok(c, m):
    if not c:
        raise SystemExit('FAIL ' + m)
    print('PASS', m)


psd = TMP/'Creator Template.psd'
subprocess.run([sys.executable, str(ROOT/'tests/make_test_psd.py'), str(psd)], check=True)
other = TMP/'Other Template.psd'
subprocess.run([sys.executable, str(ROOT/'tests/make_test_psd.py'), str(other)], check=True)
with open(other, 'ab') as f:  # same layers, different bytes (like an updated template)
    f.write(b'\0')
psd_bytes = psd.read_bytes()

c = app.app.test_client()
H = {'X-Dirt-Token': app.TOKEN}
B = 'http://127.0.0.1'


def post(path, **kw):
    r = c.post('/api/'+path, headers=H, base_url=B, **kw)
    return r


info = post('open', data={'file': (io.BytesIO(psd_bytes), psd.name)}, content_type='multipart/form-data').get_json()
art = post('artwork', data={'file': (io.BytesIO(open(ROOT/'source/static/icon.svg', 'rb').read()), 'icon.png')},
           content_type='multipart/form-data')
state = dict(app.DOC.state); state['name'] = 'Portable Test'

# -- portable project: no PSD inside -------------------------------------------------
r = post('project/save', json=state)
ok(r.status_code == 200, 'portable project saves')
project = r.data
with zipfile.ZipFile(io.BytesIO(project)) as z:
    names = z.namelist(); cfg = json.loads(z.read('project.json'))
ok('template.psd' not in names and not any(n.endswith('.psd') for n in names), 'portable project contains no PSD')
ok(psd_bytes[:4] == b'8BPS' and psd_bytes[200:4000] not in project, 'no PSD bytes hidden in the file')
ok(cfg['version'] == 2 and len(cfg['psd']['sha256']) == 64 and cfg['psd']['filename'] == psd.name, 'it records the PSD name and SHA-256')

app.DOC = None
r = post('project/open', data={'file': (io.BytesIO(project), 'Portable Test.dirtgear')}, content_type='multipart/form-data').get_json()
ok(r.get('needs_psd') and r['filename'] == psd.name and app.DOC is None, 'opening it asks for your own copy of the PSD')

r = post('project/attach-psd', data={'file': (io.BytesIO(other.read_bytes()), other.name)}, content_type='multipart/form-data').get_json()
ok(r.get('mismatch') and r['expected'] == psd.name and app.DOC is None, 'a different PSD is flagged before opening')
r2 = post('project/attach-psd', json={'upload_id': 'nope', 'force': True})
ok(r2.status_code == 400, 'forcing needs the upload that was checked')
r = post('project/attach-psd', json={'upload_id': r['upload_id'], 'force': True}).get_json()
ok(app.DOC is not None and app.DOC.state['name'] == 'Portable Test', 'you can still open it with a different version if you choose')

app.DOC = None
post('project/open', data={'file': (io.BytesIO(project), 'Portable Test.dirtgear')}, content_type='multipart/form-data')
r = post('project/attach-psd', data={'file': (io.BytesIO(psd_bytes), 'renamed.psd')}, content_type='multipart/form-data').get_json()
ok(not r.get('mismatch') and app.DOC is not None and len(app.DOC.assets) == len(cfg['assets']), 'the matching PSD (any file name) opens the design with its artwork')
ok(post('project/attach-psd', json={'upload_id': 'x'}).status_code == 400, 'nothing is pending afterwards')

# -- library save keeps a private copy so it reopens on this PC -------------------
r = post('project/quick-save', json=state).get_json()
saved = Path(r['saved'])
ok(saved.is_file() and saved.is_relative_to(TMP/'lad'), 'Save for later stays in your own app folder')
with zipfile.ZipFile(saved) as z:
    ok('template.psd' in z.namelist(), 'Save for later keeps the PSD so Continue works offline')
app.DOC = None
r = post('project/reopen', json={'id': saved.name}).get_json()
ok(not r.get('needs_psd') and app.DOC is not None, 'Continue reopens it without asking for the PSD')

# -- old projects with the PSD inside still open ------------------------------------
old = io.BytesIO()
with zipfile.ZipFile(old, 'w') as z:
    z.writestr('template.psd', psd_bytes)
    z.writestr('project.json', json.dumps({'version': 1, 'filename': psd.name, 'state': state, 'assets': {}}))
app.DOC = None
r = post('project/open', data={'file': (io.BytesIO(old.getvalue()), 'old.motogear')}, content_type='multipart/form-data').get_json()
ok(not r.get('needs_psd') and app.DOC is not None, 'older .dirtgear/.motogear files still open')
shutil.rmtree(TMP, ignore_errors=True)
print('ALL PORTABLE PROJECT TESTS PASSED')
