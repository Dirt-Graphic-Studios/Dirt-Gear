"""Make Dirt Gear friend codes (free unlimited Premium).

    python tools/make_friend_codes.py 10 codes.txt

Writes the plain codes to the file you name (keep it private and hand codes
out one per friend) and appends their hashes to source/friend_codes.txt,
which is what ships in the app. Never commit the plain codes.
"""
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'source'))
import premium  # noqa: E402

ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'  # Crockford base32: no I, L, O, U


def make():
    body = ''.join(secrets.choice(ALPHABET) for _ in range(16))
    return 'DGF-' + '-'.join(body[i:i+4] for i in range(0, 16, 4))


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    out = Path(sys.argv[2] if len(sys.argv) > 2 else 'friend-codes-PRIVATE.txt')
    codes = [make() for _ in range(count)]
    hashes = Path(__file__).resolve().parents[1]/'source'/'friend_codes.txt'
    with hashes.open('a', encoding='utf-8') as f:
        for code in codes:
            f.write(premium.friend_hash(code)+'\n')
    with out.open('a', encoding='utf-8') as f:
        f.write('\n'.join(codes)+'\n')
    print(f'{count} codes written to {out}; hashes added to {hashes}')


if __name__ == '__main__':
    main()
