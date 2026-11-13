"""Premium tests: daily limit, friend codes, Lemon Squeezy licences (against a
fake licence server) and the export routes. Run: python tests/test_premium.py"""
import io, json, os, subprocess, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
TMP = Path(tempfile.mkdtemp())


def ok(c, m):
    if not c:
        raise SystemExit('FAIL ' + m)
    print('PASS', m)


# -- fake Lemon Squeezy ---------------------------------------------------------
KEYS = {'GOOD-KEY': {'status': 'active', 'store': 111, 'product': 222},
        'OTHER-STORE': {'status': 'active', 'store': 999, 'product': 222},
        'OLD-KEY': {'status': 'expired', 'store': 111, 'product': 222}}
CALLS = []
OFFLINE = {'on': False}


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        if OFFLINE['on']:
            self.send_response(503); self.end_headers(); return
        fields = {k: v[0] for k, v in parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode()).items()}
        endpoint = self.path.rsplit('/', 1)[-1]
        CALLS.append((endpoint, fields))
        key = KEYS.get(fields.get('license_key'))
        if not key:
            body, code = {'activated': False, 'valid': False, 'error': 'license_key not found.', 'license_key': None, 'meta': None}, 404
        else:
            lk = {'status': key['status'], 'key': fields['license_key']}
            meta = {'store_id': key['store'], 'product_id': key['product'], 'customer_email': 'rider@example.com'}
            if endpoint == 'activate':
                body, code = {'activated': key['status'] == 'active', 'error': None if key['status'] == 'active' else 'expired',
                              'license_key': lk, 'instance': {'id': 'inst-1'}, 'meta': meta}, 200
            elif endpoint == 'validate':
                body, code = {'valid': key['status'] == 'active', 'error': None, 'license_key': lk, 'instance': {'id': fields.get('instance_id')}, 'meta': meta}, 200
            else:
                body, code = {'deactivated': True, 'error': None, 'license_key': lk, 'meta': meta}, 200
        data = json.dumps(body).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(data)


server = ThreadingHTTPServer(('127.0.0.1', 0), Fake)
threading.Thread(target=server.serve_forever, daemon=True).start()

config = TMP/'premium_config.json'
config.write_text(json.dumps({'enabled': True, 'daily_limit': 5, 'store_id': 111, 'product_ids': [222],
                              'checkout_url': 'https://example.lemonsqueezy.com/buy/x'}))
os.environ.update(DIRT_GEAR_LICENSE_API=f'http://127.0.0.1:{server.server_port}', DIRT_GEAR_PREMIUM_CONFIG=str(config),
                  DIRT_GEAR_FRIEND_CODES=str(TMP/'friend_codes.txt'), LOCALAPPDATA=str(TMP/'appdata'))
sys.path.insert(0, str(ROOT/'source'))
import premium  # noqa: E402

FRIEND = 'DGF-TEST-0000-TEST-0001'
(TMP/'friend_codes.txt').write_text('# test\n' + premium.friend_hash(FRIEND) + '\n')
premium.setup(TMP/'appdata'/'Dirt Gear')

# -- daily limit ----------------------------------------------------------------
for i in range(5):
    premium.check(f'Gear {i}'); premium.record(f'Gear {i}')
st = premium.status()
ok(st['used'] == 5 and st['remaining'] == 0 and not st['premium'], 'five gear sets use up the free day')
premium.check('gear 0 '); premium.check('GEAR 4')
ok(True, 'the same gear name again (any case/spacing) is still allowed')
try:
    premium.check('Gear 6'); ok(False, 'sixth set blocked')
except premium.LimitReached as e:
    ok('5 gear sets' in str(e), 'a sixth new gear set is blocked with a clear message')
usage = json.loads((TMP/'appdata/Dirt Gear/usage.json').read_text())
usage['date'] = '2000-01-01'; (TMP/'appdata/Dirt Gear/usage.json').write_text(json.dumps(usage))
premium.check('Gear 6')
ok(premium.status()['used'] == 0, 'the limit resets on a new day')
for i in range(5):
    premium.record(f'Gear {i}')

# -- disabled config means no limit ---------------------------------------------
config.write_text(json.dumps({'enabled': False}))
premium.check('Anything'); st = premium.status()
ok(not st['enabled'] and st['remaining'] is None, 'with Premium switched off there is no limit')
config.write_text(json.dumps({'enabled': True, 'daily_limit': 5, 'store_id': 111, 'product_ids': [222],
                              'checkout_url': 'https://example.lemonsqueezy.com/buy/x'}))

# -- friend codes ------------------------------------------------------------------
for bad in ('DGF-TEST-0000-TEST-0002', 'hello', ''):
    try:
        premium.activate(bad); ok(False, 'bad code ' + bad)
    except ValueError:
        pass
ok(not premium.status()['premium'], 'wrong friend codes are rejected')
CALLS.clear()
st = premium.activate(' dgf test 0000 test 0001 ')
ok(st['premium'] and st['kind'] == 'friend' and not CALLS, 'a friend code unlocks Premium offline (any case/spacing)')
premium.check('Gear 99'); premium.record('Gear 99')
ok(premium.status()['remaining'] is None, 'Premium has no daily limit')
(TMP/'friend_codes.txt').write_text('# revoked\n')
ok(not premium.status()['premium'], 'removing a code’s hash revokes it')
(TMP/'friend_codes.txt').write_text(premium.friend_hash(FRIEND) + '\n')
premium.remove()
ok(not premium.status()['premium'], 'Remove from this PC clears the friend code')
ok(FRIEND.replace('-', '') not in (ROOT/'source/friend_codes.txt').read_text().upper(), 'the shipped list has hashes, not codes')

# -- Lemon Squeezy licences --------------------------------------------------------
for key, why in (('NOPE', 'unknown'), ('OTHER-STORE', 'another store'), ('OLD-KEY', 'expired')):
    try:
        premium.activate(key); ok(False, why)
    except ValueError as e:
        print('   ', why, '->', e)
ok(not premium.status()['premium'], 'unknown, other-store and expired keys are rejected')
ok(any(c[0] == 'deactivate' for c in CALLS), 'a key from another store is released again')
st = premium.activate('GOOD-KEY')
ok(st['premium'] and st['kind'] == 'license' and st['email'] == 'rider@example.com', 'an active subscription key unlocks Premium')
saved = json.loads((TMP/'appdata/Dirt Gear/premium.json').read_text())
ok(saved['instance_id'] == 'inst-1' and CALLS[-1][1]['instance_name'], 'activation stores the instance for this PC')

saved['checked_at'] = time.time() - 2*86400; (TMP/'appdata/Dirt Gear/premium.json').write_text(json.dumps(saved))
OFFLINE['on'] = True
premium.revalidate()
ok(premium.status()['premium'], 'offline re-check keeps Premium during the grace period')
saved = json.loads((TMP/'appdata/Dirt Gear/premium.json').read_text())
saved['checked_at'] = time.time() - 8*86400; (TMP/'appdata/Dirt Gear/premium.json').write_text(json.dumps(saved))
st = premium.status()
ok(not st['premium'] and 'week' in st['lapsed'], 'more than a week offline pauses Premium')
OFFLINE['on'] = False
premium.revalidate()
ok(premium.status()['premium'], 'coming back online restores Premium')

KEYS['GOOD-KEY']['status'] = 'expired'
premium.revalidate()
st = premium.status()
ok(not st['premium'] and 'expired' in st['lapsed'], 'a cancelled/expired subscription removes Premium at the next check')
KEYS['GOOD-KEY']['status'] = 'active'
premium.activate('GOOD-KEY'); premium.remove()
ok(CALLS[-1][0] == 'deactivate' and not premium.status()['premium'], 'Remove from this PC frees the activation')

# -- through the app ---------------------------------------------------------------
import app  # noqa: E402
client = app.app.test_client()
H = {'X-Dirt-Token': app.TOKEN}
st = client.get('/api/premium/status', headers=H, base_url='http://127.0.0.1').get_json()
ok(st['enabled'] and st['remaining'] == 0 and st['can_buy'], '/api/premium/status reports the limit')
psd = TMP/'test-gear.psd'
subprocess.run([sys.executable, str(ROOT/'tests/make_test_psd.py'), str(psd)], check=True)
app.DOC = app.Document(psd, 'test-gear.psd')
state = dict(app.DOC.state); state['name'] = 'Brand New Gear'
r = client.post('/api/export/pnt', json=state, headers=H, base_url='http://127.0.0.1')
body = r.get_json()
ok(r.status_code == 402 and body['limit'] and body['premium']['remaining'] == 0, 'export of a new set at the limit returns 402 + limit')
state['name'] = 'Gear 2'
r = client.post('/api/export/pnt', json=state, headers=H, base_url='http://127.0.0.1')
ok(r.status_code == 200 and len(r.data) > 1000, 're-exporting a gear set already finished today still works')
r = client.post('/api/premium/activate', json={'key': FRIEND}, headers=H, base_url='http://127.0.0.1')
ok(r.get_json()['premium'], '/api/premium/activate accepts a friend code')
state['name'] = 'Brand New Gear'
r = client.post('/api/export/tga', json=state, headers=H, base_url='http://127.0.0.1')
ok(r.status_code == 200, 'Premium exports a new set past the limit')
server.shutdown()
print('ALL PREMIUM TESTS PASSED')
