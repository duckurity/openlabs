"""Create disposable, fictional ParcelPoint state for one lab generation."""
from pathlib import Path
from contextlib import closing
import hashlib
import json
import os
import secrets
import sqlite3
from werkzeug.security import generate_password_hash

DEFAULT_STATE = Path(os.environ.get('PARCELPOINT_STATE_DIR', '/run/parcelpoint'))


def initialize(state_dir: Path = DEFAULT_STATE) -> Path:
    """Create fresh state. Operators stop the service before reinitializing."""
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    database = state_dir / 'parcelpoint.sqlite'
    if database.exists():
        database.unlink()
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.executescript((Path(__file__).parent.parent / 'database/schema.sql').read_text(encoding='utf-8'))
        flags = {key: 'duck{' + secrets.token_hex(16) + '}' for key in ('flag', 'checkpoint_flag')}
        connection.executemany('INSERT INTO runtime VALUES (?, ?)', flags.items())
        for name, email in [('Mira Vale', 'mira.vale@parcelpoint.test'), ('Jules Reed', 'jules.reed@parcelpoint.test')]:
            connection.execute('INSERT INTO users(name,email,password_hash,role) VALUES (?,?,?,?)',
                               (name, email, generate_password_hash(secrets.token_urlsafe(32)), 'courier'))
        connection.executemany('INSERT INTO routes VALUES (?,?,?,?)', [
            ('RT-NORTH', 'North loop', 1, ''),
            ('RT-SOUTH', 'South loop', 2,
             'Handoff for PP-407: Mira Vale (mira.vale@parcelpoint.test), North loop. '
             'She owns the held locker; contact her for the release review.'),
        ])
        fixtures = [
            ('PP-104', 'Aster arcade', 'Northbank', 'available', 6),
            ('PP-118', 'Copper square', 'Northbank', 'in_transit', 9),
            ('PP-206', 'Fern concourse', 'Eastmere', 'available', 4),
            ('PP-233', 'Willow exchange', 'Eastmere', 'available', 11),
            ('PP-305', 'Lantern walk', 'Southreach', 'in_transit', 7),
            ('PP-322', 'Orchard court', 'Southreach', 'available', 3),
            ('PP-407', 'Cobalt depot', 'Westhaven', 'held', 1),
            ('PP-418', 'Juniper passage', 'Westhaven', 'available', 8),
        ]
        timestamp = '2026-01-12T09:30:00Z'
        for index, (locker_id, name, district, status, parcels) in enumerate(fixtures):
            courier_id = 1 if index in (0, 1, 2, 6) else 2
            events = json.dumps([{'time': timestamp, 'text': 'Dispatch review required.' if status == 'held' else 'Bank status synchronized.'}])
            connection.execute('INSERT INTO lockers VALUES (?,?,?,?,?,?,?,?,?,?)',
                               (locker_id, name, district, status, parcels, 24,
                                f'{index + 10} Simulation Way, {district}', timestamp, courier_id, events))
            connection.execute('INSERT INTO route_lockers VALUES (?,?)',
                               ('RT-NORTH' if courier_id == 1 else 'RT-SOUTH', locker_id))
        connection.execute('INSERT INTO manifests VALUES (?,?,?,?)',
                           ('PP-407', 'PP-MANIFEST-407', 'Aster Research Cooperative', 'Sealed prototype transit case'))
    database.chmod(0o600)
    metadata = {'generation_id': secrets.token_hex(16)}
    metadata.update({key + '_hash': hashlib.sha256(value.encode()).hexdigest() for key, value in flags.items()})
    digest_path = state_dir / 'digest.json'
    descriptor = os.open(digest_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        json.dump(metadata, handle)
    digest_path.chmod(0o600)
    return database


def digest(state_dir: Path = DEFAULT_STATE) -> dict:
    """Return operator hashes, never flag plaintext."""
    return json.loads((Path(state_dir) / 'digest.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    os.umask(0o077)
    initialize()
