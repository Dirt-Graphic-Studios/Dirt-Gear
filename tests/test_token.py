"""Every request to Dirt Gear's local server needs this run's token, the page
and its static files included. Run: python tests/test_token.py"""
import os, sys, tempfile
from pathlib import Path
os.environ['LOCALAPPDATA'] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'source'))
import app  # noqa: E402


def ok(c, m):
    if not c:
        raise SystemExit('FAIL ' + m)
    print('PASS', m)


B = 'http://127.0.0.1:5555'
c = app.app.test_client()
for path in ['/', '/static/app.js', '/static/style.css', '/static/rider.json', '/static/icon.svg', '/api/fonts', '/favicon.ico', '/nope']:
    ok(c.get(path, base_url=B).status_code == 403, f'{path} without the token is refused')
ok(c.get('/?token=wrong', base_url=B).status_code == 403, 'a wrong token is refused')
ok(c.get('/static/app.js', base_url='http://evil.example:5555', headers={'X-Dirt-Token': app.TOKEN}).status_code == 403, 'other host names are refused')
r = c.get('/?token=' + app.TOKEN, base_url=B)
cookie = r.headers.get('Set-Cookie', '')
ok(r.status_code == 200 and 'dirt_token_5555=' in cookie and 'HttpOnly' in cookie and 'SameSite=Strict' in cookie,
   'the window’s first page load sets an HttpOnly, SameSite=Strict cookie')
ok(c.get('/static/app.js', base_url=B).status_code == 200, 'the page’s own files load with that cookie')
c2 = app.app.test_client(); c2.set_cookie('dirt_token_5555', 'wrong', domain='127.0.0.1')
ok(c2.get('/static/app.js', base_url=B).status_code == 403, 'a wrong cookie is refused')
c3 = app.app.test_client(); c3.set_cookie('dirt_token_6666', app.TOKEN, domain='127.0.0.1')
ok(c3.get('/static/app.js', base_url=B).status_code == 403, 'another port’s cookie doesn’t count')
ok(app.app.test_client().get('/api/fonts', base_url=B, headers={'X-Dirt-Token': app.TOKEN}).status_code == 200, 'the API works with the token header')
ok(app.app.test_client().post('/api/heartbeat', base_url=B, headers={'X-Dirt-Token': app.TOKEN, 'Origin': 'http://evil.example'}).status_code == 403, 'API calls from another origin are refused')
print('ALL TOKEN TESTS PASSED')
