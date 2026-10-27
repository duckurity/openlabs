"""Runtime seed contracts. State stays in the container's disposable /tmp."""
from pathlib import Path
from contextlib import closing
import tempfile
import unittest
import sqlite3
import hashlib
from werkzeug.security import check_password_hash


class SeedTests(unittest.TestCase):
    def test_seed_contains_fictional_dispatch_fixtures_and_runtime_flags(self):
        from app.seed import initialize, digest
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            database = initialize(state)
            with closing(sqlite3.connect(database)) as connection:
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertTrue({'users', 'lockers', 'routes', 'route_lockers', 'sessions', 'reset_codes', 'mailbox', 'manifests'} <= tables)
                couriers = connection.execute('SELECT id,email,password_hash,role FROM users').fetchall()
                self.assertEqual(len(couriers), 2)
                for _, email, password_hash, role in couriers:
                    self.assertTrue(email.endswith('.test'))
                    self.assertEqual(role, 'courier')
                    self.assertTrue(password_hash.startswith('scrypt:'))
                    self.assertFalse(check_password_hash(password_hash, 'password'))
                lockers = connection.execute('SELECT id,status,parcels,capacity FROM lockers').fetchall()
                self.assertEqual(len(lockers), 8)
                self.assertEqual([row[0] for row in lockers if row[1] == 'held'], ['PP-407'])
                self.assertIn('PP-104', [row[0] for row in lockers])
                self.assertTrue(all(0 <= row[2] <= row[3] for row in lockers))
                runtime = dict(connection.execute('SELECT key,value FROM runtime'))
                for key in ('flag', 'checkpoint_flag'):
                    self.assertRegex(runtime[key], r'^duck\{[a-f0-9]{32}\}$')
                    self.assertEqual(digest(state)[key + '_hash'], hashlib.sha256(runtime[key].encode()).hexdigest())
                self.assertNotEqual(runtime['flag'], runtime['checkpoint_flag'])

    def test_initialize_creates_runtime_database_and_private_digests(self):
        self.assertTrue(Path('app/seed.py').is_file(), 'seed implementation is missing')
        from app.seed import initialize, digest
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            database = initialize(state)
            self.assertEqual(database, state / 'parcelpoint.sqlite')
            self.assertTrue(database.is_file())
            metadata = digest(state)
            self.assertEqual(set(metadata), {'generation_id', 'flag_hash', 'checkpoint_flag_hash'})
            self.assertRegex(metadata['generation_id'], r'^[a-f0-9]{32}$')
            self.assertRegex(metadata['flag_hash'], r'^[a-f0-9]{64}$')
            self.assertRegex(metadata['checkpoint_flag_hash'], r'^[a-f0-9]{64}$')
            self.assertEqual((state / 'digest.json').stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
