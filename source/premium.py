"""Dirt Gear Premium: a daily limit for free users, lifted by a licence.

Free users can finish `daily_limit` gear sets per local day. A gear set is
one gear name: Pack & install, Export .pnt and Export TGAs for a name that has
already been used today don't use another slot, so re-packing while testing in
game is free.

Premium comes from either:
  * a Lemon Squeezy licence key, sold as a $5 USD/month subscription. It is
    activated once per PC with the Lemon Squeezy License API and re-checked
    once a day. When the subscription ends, Lemon Squeezy marks the key
    expired and the next check removes Premium. Without internet, Premium
    keeps working for GRACE_DAYS after the last successful check.
  * a friend code (DGF-XXXX-XXXX-XXXX-XXXX) for unlimited use for free. Only
    SHA-256 hashes of the codes ship in the app (friend_codes.txt), so the
    public source doesn't reveal them. Delete a hash to revoke that code in
    the next release.

Everything is controlled by premium_config.json. When "enabled" is false
there is no limit at all.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import platform
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = os.environ.get('DIRT_GEAR_LICENSE_API', 'https://api.lemonsqueezy.com').rstrip('/')
TIMEOUT = 15
RECHECK_SECONDS = 24 * 3600
GRACE_DAYS = 7
FRIEND_SALT = 'dirt-gear-friend:'
FRIEND_RE = re.compile(r'^DGF[0-9A-Z]{16}$')
DEFAULT_CONFIG = {'enabled': False, 'daily_limit': 5, 'price': '$5 USD / month',
                  'store_id': None, 'product_ids': [], 'checkout_url': ''}

_lock = threading.RLock()
_folder: Path | None = None
_checking = False


class LimitReached(Exception):
    code = 402


def _root() -> Path:
    return Path(getattr(sys, '_MEIPASS', Path(__file__).parent))


def config() -> dict:
    path = Path(os.environ.get('DIRT_GEAR_PREMIUM_CONFIG') or _root()/'premium_config.json')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        data = {}
    merged = DEFAULT_CONFIG | (data if isinstance(data, dict) else {})
    merged['daily_limit'] = max(1, int(merged.get('daily_limit') or 5))
    merged['product_ids'] = [int(p) for p in merged.get('product_ids') or []]
    url = str(merged.get('checkout_url') or '')
    merged['checkout_url'] = url if url.startswith('https://') else ''
    return merged


def setup(folder: Path):
    global _folder
    _folder = Path(folder)


def _path(name: str) -> Path:
    if _folder is None:
        raise RuntimeError('premium.setup() was not called')
    return _folder/name


def _load(name: str) -> dict:
    try:
        data = json.loads(_path(name).read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(name: str, data: dict | None):
    path = _path(name)
    if data is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(data, indent=1), encoding='utf-8')
    temporary.replace(path)


def today() -> str:
    return _dt.date.today().isoformat()


# -- friend codes ------------------------------------------------------------
def normalise_code(text: str) -> str:
    return re.sub(r'[^0-9A-Z]', '', (text or '').upper())


def friend_hash(code: str) -> str:
    return hashlib.sha256((FRIEND_SALT+normalise_code(code)).encode()).hexdigest()


def friend_hashes() -> set[str]:
    path = Path(os.environ.get('DIRT_GEAR_FRIEND_CODES') or _root()/'friend_codes.txt')
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except OSError:
        return set()
    return {line.strip().lower() for line in lines
            if re.fullmatch(r'[0-9a-fA-F]{64}', line.strip())}


def is_friend_code(text: str) -> bool:
    return bool(FRIEND_RE.match(normalise_code(text)))


# -- Lemon Squeezy -----------------------------------------------------------
def _post(endpoint: str, fields: dict) -> dict:
    body = urllib.parse.urlencode(fields).encode()
    request = urllib.request.Request(f'{API}/v1/licenses/{endpoint}', data=body, method='POST',
                                     headers={'Accept': 'application/json',
                                              'Content-Type': 'application/x-www-form-urlencoded',
                                              'User-Agent': 'Dirt-Gear'})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read(256 * 1024)
    except urllib.error.HTTPError as exc:  # Lemon Squeezy answers errors with JSON too
        raw = exc.read(256 * 1024)
        if not raw:
            raise
    data = json.loads(raw or b'{}')
    if not isinstance(data, dict):
        raise ValueError('Unexpected licence server reply.')
    return data


def _ours(meta: dict, cfg: dict) -> bool:
    """A key from another Lemon Squeezy store or product must not unlock Premium."""
    meta = meta or {}
    if cfg.get('store_id') is None or not cfg.get('product_ids'):
        return False
    try:
        return int(meta.get('store_id')) == int(cfg['store_id']) and int(meta.get('product_id')) in cfg['product_ids']
    except (TypeError, ValueError):
        return False


def _key_problem(data: dict, cfg: dict) -> str:
    key = data.get('license_key') or {}
    if not _ours(data.get('meta') or {}, cfg):
        return 'This licence key isn’t for Dirt Gear Premium.'
    status = key.get('status')
    if status == 'expired':
        return 'This licence has expired. Renew your subscription to keep Premium.'
    if status == 'disabled':
        return 'This licence key has been disabled.'
    return ''


def instance_name() -> str:
    return (platform.node() or 'PC')[:60]


def activate(text: str) -> dict:
    text = (text or '').strip()
    if not text:
        raise ValueError('Paste your licence key or friend code.')
    if is_friend_code(text):
        if friend_hash(text) not in friend_hashes():
            raise ValueError('That friend code isn’t valid.')
        with _lock:
            _save('premium.json', {'kind': 'friend', 'code_hash': friend_hash(text), 'since': today()})
        return status()
    cfg = config()
    if len(text) > 100:
        raise ValueError('That doesn’t look like a licence key.')
    try:
        data = _post('activate', {'license_key': text, 'instance_name': instance_name()})
    except (OSError, ValueError) as exc:
        raise ValueError('Couldn’t reach the licence server. Check your internet connection and try again.') from exc
    problem = _key_problem(data, cfg) if data.get('license_key') else ''
    if problem:
        instance = (data.get('instance') or {}).get('id')
        if instance:  # don't use up an activation on a key we won't accept
            try:
                _post('deactivate', {'license_key': text, 'instance_id': instance})
            except (OSError, ValueError):
                pass
        raise ValueError(problem)
    if not data.get('activated'):
        error = str(data.get('error') or '')
        if not data.get('license_key') or 'not found' in error.lower():
            error = 'That licence key isn’t valid. Check it matches the one in your email.'
        elif 'limit' in error.lower():
            error = 'This licence key is already active on the maximum number of PCs. Remove it from another PC first.'
        raise ValueError(error or 'That licence key couldn’t be activated.')
    key = data.get('license_key') or {}
    with _lock:
        _save('premium.json', {'kind': 'license', 'key': text, 'instance_id': (data.get('instance') or {}).get('id'),
                               'status': key.get('status'), 'checked_at': time.time(),
                               'email': (data.get('meta') or {}).get('customer_email', '')})
    return status()


def remove() -> dict:
    with _lock:
        saved = _load('premium.json')
        if saved.get('kind') == 'license' and saved.get('instance_id'):
            try:
                _post('deactivate', {'license_key': saved['key'], 'instance_id': saved['instance_id']})
            except (OSError, ValueError):
                pass  # still remove it here; the seat can be freed from the Lemon Squeezy page
        _save('premium.json', None)
    return status()


def revalidate() -> dict:
    """Ask Lemon Squeezy whether the saved licence is still active."""
    with _lock:
        saved = _load('premium.json')
    if saved.get('kind') != 'license':
        return saved
    try:
        data = _post('validate', {'license_key': saved['key'], 'instance_id': saved.get('instance_id') or ''})
    except (OSError, ValueError):
        return saved  # offline: keep it until the grace period runs out
    with _lock:
        current = _load('premium.json')
        if current.get('key') != saved.get('key'):
            return current
        problem = _key_problem(data, config()) if data.get('license_key') else ''
        if not data.get('valid') or problem:
            current['revoked'] = problem or str(data.get('error') or 'This licence is no longer active.')
        else:
            current.pop('revoked', None)
            current['status'] = (data.get('license_key') or {}).get('status')
            current['checked_at'] = time.time()
        _save('premium.json', current)
        return current


def _recheck_soon(saved: dict):
    global _checking
    if saved.get('kind') != 'license' or time.time() - float(saved.get('checked_at') or 0) < RECHECK_SECONDS:
        return
    with _lock:
        if _checking:
            return
        _checking = True

    def run():
        global _checking
        try:
            revalidate()
        finally:
            _checking = False
    threading.Thread(target=run, daemon=True).start()


def premium_state() -> tuple[bool, dict, str]:
    """(is premium, saved licence, message about a lapsed licence)."""
    with _lock:
        saved = _load('premium.json')
    kind = saved.get('kind')
    if kind == 'friend':
        return saved.get('code_hash') in friend_hashes(), saved, ''
    if kind == 'license':
        if saved.get('revoked'):
            return False, saved, saved['revoked']
        _recheck_soon(saved)
        age = time.time() - float(saved.get('checked_at') or 0)
        if age > GRACE_DAYS * 86400:
            return False, saved, 'Dirt Gear couldn’t check your licence for a week. Connect to the internet to keep Premium.'
        return True, saved, ''
    return False, {}, ''


# -- daily limit -------------------------------------------------------------
def set_key(name: str) -> str:
    return re.sub(r'\s+', ' ', (name or '').strip()).casefold() or 'untitled'


def _usage() -> dict:
    data = _load('usage.json')
    if data.get('date') != today():
        data = {'date': today(), 'sets': []}
    data['sets'] = [s for s in data.get('sets', []) if isinstance(s, str)]
    return data


def status() -> dict:
    cfg = config()
    is_premium, saved, lapsed = premium_state()
    usage = _usage()
    used = len(usage['sets'])
    limit = cfg['daily_limit']
    return {'enabled': bool(cfg['enabled']), 'premium': is_premium,
            'kind': saved.get('kind') if is_premium else None,
            'email': saved.get('email', '') if is_premium else '',
            'lapsed': lapsed, 'limit': limit, 'used': used,
            'remaining': None if (is_premium or not cfg['enabled']) else max(0, limit-used),
            'price': cfg['price'], 'can_buy': bool(cfg['checkout_url'])}


def check(name: str):
    """Raise LimitReached if this gear set can't be finished today."""
    cfg = config()
    if not cfg['enabled'] or premium_state()[0]:
        return
    with _lock:
        usage = _usage()
        if set_key(name) in usage['sets'] or len(usage['sets']) < cfg['daily_limit']:
            return
    raise LimitReached(f'You’ve finished {cfg["daily_limit"]} gear sets today, the free daily limit. '
                       'Get Dirt Gear Premium for unlimited gear sets, or come back tomorrow.')


def record(name: str):
    cfg = config()
    if not cfg['enabled'] or premium_state()[0]:
        return
    with _lock:
        usage = _usage()
        key = set_key(name)
        if key not in usage['sets']:
            usage['sets'].append(key)
            _save('usage.json', usage)
