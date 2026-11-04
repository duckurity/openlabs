"""The evaluator solver must complete both stages against the real HTTP app."""
from contextlib import closing
from pathlib import Path
import hashlib
import sqlite3
import tempfile
import threading
import unittest

from werkzeug.serving import make_server


class SolverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        from app import create_app
        from app.seed import initialize
        self.state = Path(self.temporary.name)
        self.database = initialize(self.state)
        self.server = make_server('127.0.0.1', 0, create_app(self.database), threaded=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def test_solver_obtains_both_runtime_flags_over_the_http_interface(self):
        from solver.solve import solve
        flags = solve(f'http://127.0.0.1:{self.server.server_port}')
        self.assertEqual(set(flags), {'checkpoint', 'final'})
        expected = __import__('app.seed', fromlist=['digest']).digest(self.state)
        self.assertEqual(hashlib.sha256(flags['checkpoint'].encode()).hexdigest(), expected['checkpoint_flag_hash'])
        self.assertEqual(hashlib.sha256(flags['final'].encode()).hexdigest(), expected['flag_hash'])

    def test_solver_refuses_non_loopback_targets(self):
        from solver.solve import solve
        with self.assertRaises(ValueError):
            solve('https://example.com')


if __name__ == '__main__':
    unittest.main()
